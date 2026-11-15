# TASK-009: chat with the dean's office (polling, server-rendered fragments)

Author: Planner. Status: ready for implementation.
Base commit: `b3dcb37`. Related specs: `TASK-007.md` (feed sources, badge, D3 GET read marker, D5 clock), `TASK-008-FIX.md` (compact header, page-assertion rule), `TASK-006.md` (staff scoping, admin read-only pattern).

A student writes to the dean's office of their faculty in one dialog. Any staff member of that faculty reads and answers from «Чаты». Without JavaScript everything works with normal pages, POST forms and an «Обновить» link. With JavaScript the page asks the server every 5 seconds for new messages and appends the server-rendered HTML.

---

## 1. Acceptance criteria
| ID | Criterion |
|---|---|
| AC1 | New app `chat` with models `Dialog` and `Message`, migrations, read-only admin for the superuser. |
| AC2 | One dialog per student (DB unique), with the dean's office of the student's faculty; created on the student's first message. Staff of the student's faculty read and answer; staff cannot start dialogs. |
| AC3 | Messages are append-only plain text (autoescaped, `linebreaksbr`), `MESSAGE_MAX_LENGTH` = 2000 after normalising line breaks; empty/whitespace-only rejected; author, role and time (`core.clock.now`) stored. No edit/delete anywhere (admin read-only). |
| AC4 | Order = message `id` ascending. Inserts into one dialog are serialised by a row lock on the dialog, so id order = creation order = commit order (D3). Two concurrent staff replies are both kept. |
| AC5 | Student rate limit: at most `RATE_LIMIT_MESSAGES` = 20 messages per `RATE_LIMIT_MINUTES` = 10 minutes (service level). Double submit of one form (same `client_token`) creates one message (DB unique + idempotent service). All sends end with a redirect (PRG). |
| AC6 | Polling: `static/js/chat.js` (vanilla, deferred, no inline script, no `innerHTML`/`insertAdjacentHTML`/`outerHTML`/`document.write`/`eval`) requests the fragment view every `POLL_INTERVAL_SECONDS` = 5 s with `after=<last shown id>`, appends new messages (no duplicates), pauses while the tab is hidden, stops after `POLL_MAX_ERRORS` = 5 consecutive errors and shows a text notice. Fragment view: GET only, login + role + scope checks, `Cache-Control: no-store`, `204` when nothing is new, `400` for a bad `after`. |
| AC7 | Sending is a normal POST form (no `fetch` send, D6). The page works fully without JavaScript and shows an «Обновить» link. |
| AC8 | Student unread = staff messages after the student's read marker. They appear in «Уведомления» as source `chat_reply` («Новое сообщение от деканата», link to the chat) and in the existing badge; the nav item shows «Чат (N)». Opening the chat (page or a fragment with new messages) moves the student's read marker. |
| AC9 | Staff «Чаты»: dialogs of their faculty, unread first, then newest last message first; each with student name, group, unread count. A dialog is read for all staff of the faculty when any of them opens it (shared marker, D4). |
| AC10 | Pages: student «Чат с деканатом» (history oldest → newest, newest at the bottom right above the form, empty-state hint, form); staff list and dialog page (history, student summary with link to the staff student page, reply form). Nav: «Чат» (student), «Чаты» (staff) in both header lists. 360 px without horizontal scroll. |
| AC11 | Access: student only own dialog; staff only dialogs of students visible to them (`students_visible_to`), 404 otherwise; students → 403 on staff pages; staff/superuser → 403 on student pages; dialog URLs use a UUID. |
| AC12 | Fixed query counts for the student page, the staff list, the staff dialog page and both fragment views; the header costs exactly 4 queries for a student (feed badge 3 + chat badge 1) and 0 for staff. |
| AC13 | `seed_demo` (idempotent): a dialog for each demo student with messages from both sides; student1 has an unread reply; each faculty (FDD, FAE) has a dialog with an unread student message. |

## 2. Out of scope
WebSockets, SSE, Channels, push/e-mail, attachments, edit/delete, typing indicators, per-message read receipts, student↔student or staff↔staff chat, staff-initiated dialogs, a JSON API, sending via `fetch`, an unread count on the staff nav item, the visual theme.

## 3. Design decisions
**D1. App name `chat`.** Short, matches the nav item and `plan.md` («Чат с деканатом»); no clash with installed packages or URL names.

**D2. Dialog created on the first student message.** Lazily creating it on page open would fill the staff list with empty dialogs (no last message to sort by). The student page renders the empty state when there is no dialog; the student fragment view returns 204.

**D3. Ordering and concurrency.** `send_*` functions lock the dialog row (`select_for_update`) BEFORE inserting the message and take `created_at = clock.now()` inside the lock. Therefore, within a dialog, ids are assigned and committed in the same order, and `created_at` is non-decreasing along ids. All lists and the polling cursor use `id` (time is display only, so a server clock correction cannot reorder messages or make polling skip one). Without the lock, on PostgreSQL message 10 could commit after message 11 and a poller already at `after=11` would never show 10. SQLite serialises writes anyway.

**D4. Read markers are message ids on the dialog.** `student_read_id` (last message id the student has seen) and `staff_read_id` (shared by all staff of the faculty: it is one dean's-office inbox, as with requests; any staff member who opens the dialog has handled it). Unread for the student = staff messages with `id > student_read_id`; for staff = student messages with `id > staff_read_id`. Markers only move forward (conditional `UPDATE … WHERE field < new`). Opening the page marks up to the last shown id; a fragment response marks up to the last returned id. GET with this side effect follows TASK-007 D3 (own marker only, idempotent, monotonic, `SameSite=Lax`, `no-store`, HEAD/POST not allowed on fragment views).

**D5. Double-submit guard.** The form carries a hidden `client_token` (UUID generated when the form is rendered). `Message` has `UniqueConstraint(dialog, client_token)`; the service returns the existing message for a repeated token instead of creating one, so a double click or a browser re-POST cannot duplicate a message. PRG avoids re-POST on reload.

**D6. No `fetch` send.** One reference path (POST + redirect) is simpler to test and secure; after the redirect the page reloads at `#chat-form` (right below the newest message). Polling covers the live part (replies from the other side).

**D7. Feed integration.** `ChatReplySource` lists unread staff messages (per message) in «Уведомления» and therefore in the existing badge (which stays visible outside the collapsed menu). After the student opens the chat they leave the feed (they are read). The «Чат (N)» nav count is a separate 1-query tag.

---

## 4. Architecture

### 4.1 Files
Create:
| File | Content |
|---|---|
| `chat/__init__.py`, `chat/apps.py` | `ChatConfig` (`name = "chat"`, `verbose_name = "Чат"`, `default_auto_field = "django.db.models.BigAutoField"`) |
| `chat/constants.py` | 4.2 |
| `chat/models.py` | `AuthorRole`, `Dialog`, `Message` |
| `chat/migrations/__init__.py`, `chat/migrations/0001_initial.py` | generated |
| `chat/selectors.py`, `chat/services.py`, `chat/forms.py`, `chat/views.py`, `chat/urls.py`, `chat/admin.py`, `chat/demo.py` | 5.x |
| `chat/templatetags/__init__.py`, `chat/templatetags/chat_tags.py` | `chat_unread_badge` |
| `chat/templates/chat/student.html`, `staff_list.html`, `staff_dialog.html`, `_history.html`, `_message.html`, `_messages.html`, `_form.html` | templates |
| `static/js/chat.js` | polling (4.8) |
| `chat/tests/__init__.py`, `helpers.py`, `test_models.py`, `test_services.py`, `test_selectors.py`, `test_views.py`, `test_feed.py`, `test_static.py`, `test_demo.py` | tests |

Change:
| File | Change |
|---|---|
| `config/settings.py` | `"chat"` in `INSTALLED_APPS` after `"campusmap"` |
| `config/urls.py` | `path("", include("chat.urls")),` after the campusmap include |
| `pyproject.toml` | `"chat"` in `known-first-party` |
| `accounts/models.py` | `StaffProfile.short_name` property (same format as `Teacher.short_name`, `NBSP` imported from `university.models`) |
| `notifications/sources.py` | `ChatReplySource`, appended to `FEED_SOURCES` |
| `notifications/tests/test_feed.py` | registry test: 6 → 7 sources (rename to `test_default_registry_has_seven_sources`) |
| `templates/base.html` | `{% load … chat_tags %}`; `{% chat_unread_badge as chat_badge %}` for students |
| `templates/includes/site_nav_items.html` | «Чат (N)» / «Чаты» items |
| `core/tests/test_nav.py` | expected nav lists (4.7) |
| `accounts/management/commands/seed_demo.py` | `seed_chat_demo`, summary line |
| `static/css/base.css` | chat layout rules (4.9) |
| `README.md` | `## Chat` section; Known limitations bullets |

No new dependencies, no env variables.

### 4.2 `chat/constants.py`
```python
MESSAGE_MAX_LENGTH = 2000
RATE_LIMIT_MESSAGES = 20
RATE_LIMIT_MINUTES = 10
POLL_INTERVAL_SECONDS = 5
POLL_MAX_ERRORS = 5
HISTORY_LIMIT = 100          # messages shown on a page (newest 100)
FRAGMENT_LIMIT = 50          # messages per fragment response
STAFF_LIST_LIMIT = 200       # dialogs on the staff list
FEED_PREVIEW_CHARS = 200     # message preview in «Уведомления»
CHAT_BADGE_CAP = 99          # nav shows "99+" above it
```

### 4.3 Models — `chat/models.py`
```python
class AuthorRole(models.TextChoices):
    STUDENT = "student", "Студент"
    STAFF = "staff", "Деканат"
```
`Dialog`:
| Field | Definition |
|---|---|
| `public_id` | `UUIDField(default=uuid.uuid4, unique=True, editable=False)` |
| `student` | `OneToOneField("accounts.StudentProfile", on_delete=PROTECT, related_name="chat_dialog", verbose_name="студент")` |
| `created_at` | `DateTimeField("создан", default=core.clock.now, editable=False)` |
| `last_message_at` | `DateTimeField("последнее сообщение", null=True, blank=True, editable=False)` |
| `last_message_id` | `PositiveBigIntegerField(default=0, editable=False)` |
| `student_read_id` | `PositiveBigIntegerField(default=0, editable=False)` |
| `staff_read_id` | `PositiveBigIntegerField(default=0, editable=False)` |

`Meta`: `ordering = ["-last_message_at", "-pk"]`, `indexes = [Index(fields=["last_message_at"], name="chat_dialog_last_msg_idx")]`, `verbose_name = "диалог"`, `verbose_name_plural = "диалоги"`. `__str__` → `f"Чат: {self.student}"` (admin only; callers `select_related("student")`).

`Message`:
| Field | Definition |
|---|---|
| `dialog` | `ForeignKey(Dialog, on_delete=PROTECT, related_name="messages", verbose_name="диалог")` |
| `author` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="chat_messages", verbose_name="автор")` |
| `author_role` | `CharField("роль автора", max_length=16, choices=AuthorRole.choices)` (stored: stays correct if the user's role changes later) |
| `text` | `TextField("текст", max_length=MESSAGE_MAX_LENGTH)` |
| `created_at` | `DateTimeField("отправлено", default=core.clock.now, editable=False)` |
| `client_token` | `UUIDField(null=True, blank=True, editable=False)` |
| `seed_key` | `SlugField(max_length=40, blank=True, default="", editable=False)` |

`Meta`: `ordering = ["id"]`; `indexes = [Index(fields=["dialog", "id"], name="chat_msg_dialog_id_idx"), Index(fields=["author", "created_at"], name="chat_msg_author_time_idx")]`; constraints:
- `CheckConstraint(condition=~Q(text=""), name="chat_message_text_not_empty")`
- `CheckConstraint(condition=Q(author_role__in=["student", "staff"]), name="chat_message_author_role_value")`
- `UniqueConstraint(fields=["dialog", "client_token"], condition=Q(client_token__isnull=False), name="chat_message_unique_client_token")`
- `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="chat_message_unique_seed_key")`
`verbose_name = "сообщение"`, `verbose_name_plural = "сообщения"`. `__str__` → `f"{self.get_author_role_display()}: {self.text[:40]}"`.

`accounts/models.py`, `StaffProfile`: add after `full_name`:
```python
@property
def short_name(self) -> str:
    middle = f"{NBSP}{self.middle_name[0]}." if self.middle_name else ""
    return f"{self.last_name}{NBSP}{self.first_name[0]}.{middle}"
```
with `from university.models import NBSP` (no import cycle: `university` does not import `accounts`).

### 4.4 URLs — `chat/urls.py`
```python
app_name = "chat"
urlpatterns = [
    path("chat/", views.StudentChatView.as_view(), name="student"),
    path("chat/updates/", views.StudentChatUpdatesView.as_view(), name="student_updates"),
    path("staff/chats/", views.StaffChatListView.as_view(), name="staff_list"),
    path("staff/chats/<uuid:public_id>/", views.StaffDialogView.as_view(), name="staff_dialog"),
    path("staff/chats/<uuid:public_id>/updates/", views.StaffDialogUpdatesView.as_view(), name="staff_updates"),
]
```

### 4.5 Admin — `chat/admin.py`
`MessageInline(admin.TabularInline)`: `model = Message`, `extra = 0`, `can_delete = False`, `fields = readonly_fields = ("created_at", "author_role", "author", "text")`, `has_add_permission → False`.
`DialogAdmin`: `list_display = ("student", "last_message_at", "student_read_id", "staff_read_id")`, `list_select_related = ("student",)`, `inlines = [MessageInline]`, `has_add_permission`, `has_change_permission`, `has_delete_permission` → `False` (view-only; the change page opens read-only because `has_view_permission` stays true for the superuser).

### 4.6 Templates
- `chat/_message.html` (one message; context: `m`, `viewer_is_student`, `student_name`):
```django
<li class="chat-message chat-message--{{ m.author_role }}" id="m-{{ m.pk }}" data-message-id="{{ m.pk }}">
  <p class="chat-meta"><strong>{% if m.author_role == "staff" %}Деканат · {{ m.author.staff_profile.short_name }}{% elif viewer_is_student %}Вы{% else %}{{ student_name }}{% endif %}</strong> · <time datetime="{{ m.created_at|date:'c' }}">{{ m.created_at|date:"d.m.Y H:i" }}</time></p>
  <p class="chat-text">{{ m.text|linebreaksbr }}</p>
</li>
```
- `chat/_messages.html`: `{% for m in messages %}{% include "chat/_message.html" %}{% endfor %}` — the fragment response body (only `<li>` elements).
- `chat/_history.html` (context: `messages`, `truncated`, `poll_url`, `refresh_url`, constants):
```django
<section class="chat" data-chat-poll-url="{{ poll_url }}" data-chat-poll-ms="{{ poll_ms }}" data-chat-max-errors="{{ poll_max_errors }}">
  {% if truncated %}<p class="chat-note">Показаны последние {{ history_limit }} сообщений.</p>{% endif %}
  <ol class="chat-messages" id="chat-messages">
    {% for m in messages %}{% include "chat/_message.html" %}{% endfor %}
  </ol>
  {% if not messages %}<p class="chat-empty" id="chat-empty">{{ empty_text }}</p>{% endif %}
  <p class="chat-status" data-chat-status role="status" aria-live="polite"></p>
  <p class="page-actions"><a href="{{ refresh_url }}">Обновить</a></p>
</section>
```
- `chat/_form.html`:
```django
<form method="post" class="form chat-form" id="chat-form" action="{{ form_action }}">
  {% csrf_token %}
  {{ form.non_field_errors }}
  <input type="hidden" name="client_token" value="{{ form.client_token.value|default:client_token }}">
  <p><label for="id_text">{{ form_label }}</label>{{ form.text.errors }}{{ form.text }}</p>
  <button type="submit">Отправить</button>
</form>
```
- `chat/student.html` (extends `base.html`, title «Чат с деканатом»; `{% block extra_head %}<script src="{% static 'js/chat.js' %}" defer></script>{% endblock %}`): `<h1>Чат с деканатом</h1>`, `<p>{{ faculty_name }}</p>`, `_history.html` (empty text: «Сообщений пока нет. Напишите вопрос — ответит сотрудник деканата вашего факультета.»), `_form.html` (label «Сообщение»).
- `chat/staff_list.html` (title «Чаты»): `<h1>Чаты</h1>`; `<ul class="chat-dialogs">`, one `<li>` per dialog: `<a href="{% url 'chat:staff_dialog' d.public_id %}">{{ d.student.full_name }}</a> · {{ d.student.group.name }} · {{ d.last_message_at|date:"d.m.Y H:i" }}{% if d.unread %} · <strong>новых: {{ d.unread }}</strong>{% endif %}`; empty state «Сообщений от студентов пока нет.».
- `chat/staff_dialog.html` (title «Чат: <name>»; same script tag): `<h1>Чат со студентом</h1>`, summary `<p><a href="{% url 'accounts:staff_student_detail' dialog.student.pk %}">{{ dialog.student.full_name }}</a> · {{ dialog.student.group.name }}</p>`, `<p class="page-actions"><a href="{% url 'chat:staff_list' %}">Все чаты</a></p>`, `_history.html` (empty text unused: a dialog always has messages), `_form.html` (label «Ответ»).

### 4.7 Navigation
`templates/base.html`: line 1 `{% load static notifications_tags chat_tags %}`; replace the badge line with `{% if user.is_student %}{% notifications_badge as badge %}{% chat_unread_badge as chat_badge %}{% endif %}`.
`templates/includes/site_nav_items.html`: student branch, after «Заявки»: `{% url 'chat:student' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Чат{% if chat_badge %} ({{ chat_badge }}){% endif %}</a></li>`; staff branch, after «Заявки»: the same pattern with `chat:staff_list` and text «Чаты».
New expected lists in `core/tests/test_nav.py`: student `["/profile/", "/schedule/", "/map/", "/grades/", "/requests/", "/chat/", "/notifications/"]`; staff `["/profile/", "/staff/schedule/", "/map/", "/staff/requests/", "/staff/chats/", "/staff/announcements/", "/staff/students/"]`.

`chat/templatetags/chat_tags.py`: `@register.simple_tag(takes_context=True) def chat_unread_badge(context) -> str`: request missing → `""`; `count = student_unread_count(request.user)`; `0` → `""`; `> CHAT_BADGE_CAP` → `f"{CHAT_BADGE_CAP}+"`; else `str(count)`.

### 4.8 `static/js/chat.js`
Rules: plain ES2017 in an IIFE with `"use strict"`; no libraries, no inline scripts, no `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function`, `setInterval`. Algorithm:
1. `root = document.querySelector("[data-chat-poll-url]")`; none → return. `list = document.getElementById("chat-messages")`; `status = root.querySelector("[data-chat-status]")`; `url = root.dataset.chatPollUrl`; `interval = Number(root.dataset.chatPollMs) || 5000`; `maxErrors = Number(root.dataset.chatMaxErrors) || 5`; `errors = 0`; `timer = null`; `stopped = false`.
2. `lastId()`: the `data-message-id` of the last `li[data-message-id]` in `list`, else `"0"`.
3. `schedule()`: if `!stopped && !document.hidden` → `timer = setTimeout(poll, interval)`.
4. `poll()`: `timer = null`; `fetch(url + "?after=" + encodeURIComponent(lastId()), {credentials: "same-origin", cache: "no-store", headers: {"X-Requested-With": "XMLHttpRequest"}})`:
   - `response.redirected` or header `X-Chat-Fragment` missing on a 200 → treat as error (session expired: the login page must never be appended);
   - `204` → `errors = 0`;
   - `200` → `response.text()` → `doc = new DOMParser().parseFromString(text, "text/html")`; for each `li[data-message-id]` in `doc.body`: skip if `document.getElementById(li.id)` exists; else `list.appendChild(document.importNode(li, true))`; if anything was added: remove `#chat-empty` if present and `list.lastElementChild.scrollIntoView({block: "nearest"})`; `errors = 0`;
   - other status or network error → `errors += 1`; if `errors >= maxErrors` → `stopped = true`, `status.textContent = "Автообновление остановлено. Нажмите «Обновить»."`.
   - finally `schedule()`.
5. `document.addEventListener("visibilitychange", …)`: hidden → `clearTimeout(timer)`, `timer = null`; visible and not stopped and no pending timer → `poll()` immediately.
6. Start: `schedule()`.
The fragment is server-rendered with autoescaping, and `DOMParser` documents are inert (scripts do not run); nodes are imported, never assigned as HTML strings.

### 4.9 CSS — append to `static/css/base.css` (layout only)
```css
.chat-messages,
.chat-dialogs {
  list-style: none;
  margin: 0;
  padding: 0;
}

.chat-message {
  margin-bottom: var(--space-3);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  overflow-wrap: anywhere;
}

.chat-message--staff {
  margin-right: var(--space-4);
}

.chat-message--student {
  margin-left: var(--space-4);
}

.chat-meta,
.chat-text {
  margin: 0;
}

.chat-form textarea {
  display: block;
  width: 100%;
  min-height: 6rem;
}

.chat-dialogs li {
  margin-bottom: var(--space-3);
  overflow-wrap: anywhere;
}
```

---

## 5. Functions

### 5.1 `chat/selectors.py`
**`dialogs_visible_to(user) -> QuerySet[Dialog]`** — not authenticated/active → `none()`; staff → `Dialog.objects.filter(student__in=students_visible_to(user))`; student → `Dialog.objects.filter(student__user_id=user.pk)`; else `none()`. Tests `SelectorTests`: `test_staff_sees_own_faculty_only`, `test_student_sees_own_only`, `test_superuser_and_anonymous_none`, `test_inactive_student_dialog_hidden_from_staff` (follows `students_visible_to`).

**`staff_dialog_list(user) -> QuerySet[Dialog]`** — `dialogs_visible_to(user).select_related("student__group").annotate(unread=Count("messages", filter=Q(messages__author_role=AuthorRole.STUDENT, messages__id__gt=F("staff_read_id")))).annotate(has_unread=Case(When(unread__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())).order_by("has_unread", F("last_message_at").desc(nulls_last=True), "-pk")[:STAFF_LIST_LIMIT]`. One query (verified, 9.6). Tests: `test_unread_first_then_newest`, `test_unread_counts`, `test_one_query`.

**`student_unread_count(user) -> int`** — not a student → `0` with no query; else `Message.objects.filter(dialog__student__user_id=user.pk, author_role=AuthorRole.STAFF, id__gt=F("dialog__student_read_id")).count()` (1 query). Tests: `test_counts_only_staff_after_marker`, `test_zero_without_dialog`, `test_staff_and_anonymous_no_query` (`assertNumQueries(0)`).

### 5.2 `chat/services.py`
**`normalize_text(text: str) -> str`** — `text.replace("\r\n", "\n").replace("\r", "\n").strip()`.
**`text_errors(text: str) -> list[str]`** — empty → «Сообщение пустое.»; `len > MESSAGE_MAX_LENGTH` → f«Сообщение длиннее {MESSAGE_MAX_LENGTH} символов.».
**`send_student_message(student: StudentProfile, text: str, client_token: UUID | None) -> Message`**
1. `text = normalize_text(text)`; errors → `ValidationError(errors)`.
2. `with transaction.atomic():` `dialog, _ = Dialog.objects.get_or_create(student=student)`; `dialog = Dialog.objects.select_for_update().get(pk=dialog.pk)`.
3. `client_token` and `dialog.messages.filter(client_token=client_token).first()` exists → return it (no new row, no rate count).
4. `now = clock.now()`; `recent = Message.objects.filter(author_id=student.user_id, author_role=AuthorRole.STUDENT, created_at__gt=now - timedelta(minutes=RATE_LIMIT_MINUTES)).count()`; `recent >= RATE_LIMIT_MESSAGES` → `ValidationError(f"Можно отправить не больше {RATE_LIMIT_MESSAGES} сообщений за {RATE_LIMIT_MINUTES} минут. Подождите немного.")`.
5. `message = Message(dialog=dialog, author=student.user, author_role=AuthorRole.STUDENT, text=text, created_at=now, client_token=client_token)`; `message.full_clean()`; `message.save()`.
6. `Dialog.objects.filter(pk=dialog.pk).update(last_message_at=now, last_message_id=message.pk)`. Return `message`.
Caller: `StudentChatView.post` with `request.profile` of the logged-in student only.
**`send_staff_message(dialog: Dialog, actor: User, text: str, client_token: UUID | None) -> Message`**
1. `get_profile_for_role(actor, User.Role.STAFF)`; `normalize_text`, `text_errors` as above.
2. `with transaction.atomic():` `locked = dialogs_visible_to(actor).select_for_update(of=("self",)).filter(pk=dialog.pk).first()`; `None` → `raise PermissionDenied` (re-check of scope inside the lock).
3. Idempotency as step 3 above. No rate limit for staff.
4. `now = clock.now()`; create with `author_role=AuthorRole.STAFF`, `full_clean`, `save`; update `last_message_at`, `last_message_id`. Return.
**`mark_read(dialog_id: int, side: str, up_to_id: int) -> None`** — `field = {"student": "student_read_id", "staff": "staff_read_id"}[side]`; `up_to_id <= 0` → return; `Dialog.objects.filter(pk=dialog_id, **{f"{field}__lt": up_to_id}).update(**{field: up_to_id})`.
**`load_history(dialog: Dialog) -> tuple[list[Message], bool]`** — `rows = list(dialog.messages.select_related("author__staff_profile").order_by("-id")[:HISTORY_LIMIT + 1])`; `truncated = len(rows) > HISTORY_LIMIT`; return `(list(reversed(rows[:HISTORY_LIMIT])), truncated)`.
**`messages_after(dialog: Dialog, after_id: int) -> list[Message]`** — `list(dialog.messages.filter(id__gt=after_id).select_related("author__staff_profile").order_by("id")[:FRAGMENT_LIMIT])`.
Tests `ServiceTests` (5.x names in 6.3).

### 5.3 `chat/forms.py`
`MessageForm(forms.Form)`: `text = forms.CharField(label="Сообщение", strip=False, widget=forms.Textarea(attrs={"rows": 3, "maxlength": MESSAGE_MAX_LENGTH}))` (no `max_length` validator: the service checks the normalised length); `client_token = forms.UUIDField(required=False, widget=forms.HiddenInput)`. `clean_text`: `normalize_text`; `text_errors` → `forms.ValidationError`. Views add service `ValidationError`s with `form.add_error(None, ValidationError(exc.messages))`.

### 5.4 Views — `chat/views.py`
All views decorated `@method_decorator(never_cache, name="dispatch")`. Shared helper `_history_context(dialog, viewer_is_student, poll_url, refresh_url) -> dict` (messages, truncated, `poll_ms = POLL_INTERVAL_SECONDS * 1000`, `poll_max_errors`, `history_limit`, `student_name`, `client_token = uuid.uuid4()`).

**`StudentChatView(StudentRequiredMixin, TemplateView)`**, `http_method_names = ["get", "post"]`, template `chat/student.html`:
- GET: `dialog = Dialog.objects.filter(student=self.profile).first()`; history if dialog else empty; after building the context: if the last shown message id > 0 → `mark_read(dialog.pk, "student", last_id)`. Context also `form = MessageForm()`, `faculty_name = self.profile.group.program.faculty.name`, `form_action = reverse("chat:student")`, `poll_url = reverse("chat:student_updates")`, `refresh_url = reverse("chat:student")`.
- POST: `form = MessageForm(request.POST)`; valid → `send_student_message(self.profile, form.cleaned_data["text"], form.cleaned_data["client_token"])`; success → `redirect(reverse("chat:student") + "#chat-form")`; `ValidationError` → error; invalid → re-render 200 with the history and the bound form (no read marking on POST).
**`StudentChatUpdatesView(StudentRequiredMixin, View)`**, `http_method_names = ["get"]`:
1. `after = request.GET.get("after", "")`; not matching `^\d{1,18}$` → `HttpResponseBadRequest()`.
2. `dialog = Dialog.objects.filter(student=self.profile).first()`; `None` → `HttpResponse(status=204)`.
3. `rows = messages_after(dialog, int(after))`; empty → 204.
4. `mark_read(dialog.pk, "student", rows[-1].pk)`; render `chat/_messages.html` with `viewer_is_student=True`; response header `X-Chat-Fragment: 1`; `Content-Type: text/html; charset=utf-8`.
**`StaffChatListView(StaffRequiredMixin, TemplateView)`** — `dialogs = staff_dialog_list(self.request.user)`.
**`StaffDialogView(StaffRequiredMixin, TemplateView)`**, `http_method_names = ["get", "post"]`: `dialog = get_object_or_404(dialogs_visible_to(request.user).select_related("student__group__program__faculty"), public_id=kwargs["public_id"])` (role check first via the mixin → students get 403 before any lookup); GET as the student view with side `"staff"`, `viewer_is_student=False`, `student_name = dialog.student.full_name`; POST → `send_staff_message(dialog, request.user, …)` → `redirect(reverse("chat:staff_dialog", args=[dialog.public_id]) + "#chat-form")`.
**`StaffDialogUpdatesView(StaffRequiredMixin, View)`** — as the student updates view, dialog via `get_object_or_404(dialogs_visible_to(request.user), public_id=…)`, side `"staff"`.

### 5.5 Feed — `notifications/sources.py`
```python
class ChatReplySource(FeedSource):
    kind = "chat_reply"
    tag = "Чат"
    event_field = "created_at"
    related = ()

    def base_queryset(self, ctx):
        return Message.objects.filter(
            dialog__student_id=ctx.student.pk,
            author_role=AuthorRole.STAFF,
            id__gt=F("dialog__student_read_id"),
        )

    def to_item(self, obj, ctx):
        return FeedItem(
            key=f"chat-{obj.pk}", kind=self.kind, tag=self.tag, timestamp=obj.created_at,
            title="Новое сообщение от деканата",
            body=Truncator(obj.text).chars(FEED_PREVIEW_CHARS),
            url=reverse("chat:student"),
        )
```
Append `ChatReplySource()` at the end of `FEED_SOURCES`. Imports: `from chat.constants import FEED_PREVIEW_CHARS`, `from chat.models import AuthorRole, Message`, `from django.db.models import F`, `from django.utils.text import Truncator`. The union count stays one query (verified with an `F()` across a join, 9.6).

### 5.6 Seed — `chat/demo.py`
`@dataclass(frozen=True) class ChatSeedSummary: dialogs: int; messages: int` (created in this run).
`CHAT_SEEDS` (fictional; `hours_ago` from `timezone.now()`; listed in chronological order per student; author `"student"` = the student, otherwise the staff username):
| student | key | author | hours_ago | text |
|---|---|---|---|---|
| student1 | c-1-1 | student | 30 | Здравствуйте! Когда можно забрать справку об обучении? |
| student1 | c-1-2 | staff1 | 28 | Добрый день! Справка будет готова в пятницу, кабинет деканата на 2 этаже. |
| student1 | c-1-3 | student | 27 | Спасибо! А можно получить её в электронном виде? |
| student1 | c-1-4 | staff1 | 3 | Да, можно. Подайте заявку «Справка об обучении» и укажите это в комментарии. |
| student3 | c-3-1 | student | 6 | Добрый день! Подскажите, где посмотреть график пересдач? |
| student2 | c-2-1 | student | 50 | Здравствуйте! Нужна ли справка для социальной стипендии? |
| student2 | c-2-2 | staff2 | 48 | Да, нужна справка о составе семьи. Принесите её в деканат. |
| student2 | c-2-3 | student | 2 | Спасибо! Можно принести копию? |
Read markers for dialogs created in this run: student1 `student_read_id = id(c-1-3)` (c-1-4 unread for the student), `staff_read_id = id(c-1-3)`; student3 both 0 (c-3-1 unread for FDD staff); student2 `student_read_id = id(c-2-2)`, `staff_read_id = id(c-2-2)` (c-2-3 unread for FAE staff).
**`seed_chat_demo(today: date) -> ChatSeedSummary`**: in `transaction.atomic()`; for each student (`student1`, `student3`, `student2`): if a `Message` with the student's first seed key exists → skip the student (create-only, never update); else `dialog = Dialog.objects.get_or_create(student=…)`; create each message with explicit `created_at = base - timedelta(hours=hours_ago)`, `author_role`, `seed_key`, `full_clean()`, `save()` (direct creation, no rate limit); then set `last_message_at`, `last_message_id` and the read markers with one `update()`. Command: after notifications, `c = seed_chat_demo(today)`; print `self.style.SUCCESS(f"Chat ready: {c.dialogs} dialogs, {c.messages} messages.")`.

---

## 6. Test plan

### 6.0 Rules
- Helpers only (`accounts/tests/helpers.py`, new `chat/tests/helpers.py`: `make_dialog(student_profile)`, `add_message(dialog, author, role, text="Текст", created_at=None) -> Message` (explicit `created_at` default `timezone.now()`, updates `last_message_*`)).
- Classes with time logic use `FrozenClockMixin` with `frozen_now = "2026-11-11 12:00"` (before the real date, TASK-007 rule).
- Page assertions follow the TASK-008-FIX rule: exact markup (`data-message-id="12"`, `href="/staff/chats/<uuid>/"`) or `response.context`; never short alphanumeric needles.
- Save every test log; report any failed or stalled run by test name and Moscow time.

### 6.1 Traceability
| AC | Tests |
|---|---|
| AC1 | `test_models.py::ModelTests::*`, `test_views.py::AdminTests::*`; `makemigrations --check` |
| AC2 | `ModelTests::test_one_dialog_per_student`, `ServiceTests::test_first_message_creates_dialog`, `test_staff_cannot_write_other_faculty`, `ViewTests::test_student_page_without_dialog` |
| AC3 | `ServiceTests::test_text_normalised_and_limited`, `test_empty_rejected`, `ModelTests::test_db_rejects_empty_text`, `ViewTests::test_text_escaped_line_breaks_kept`, `AdminTests::test_admin_is_read_only` |
| AC4 | `ServiceTests::test_two_staff_replies_both_kept_in_id_order`, `test_send_locks_dialog` |
| AC5 | `ServiceTests::test_rate_limit`, `test_rate_limit_window_moves`, `test_staff_no_rate_limit`, `test_same_client_token_returns_existing`, `ViewTests::test_double_post_one_message`, `test_post_redirects_to_form_anchor` |
| AC6 | `UpdatesViewTests::*`, `test_static.py::ChatJsTests::*` |
| AC7 | `ViewTests::test_page_has_refresh_link_and_plain_form`, `test_script_is_external_and_deferred` |
| AC8 | `test_feed.py::ChatFeedTests::*`, `NavTests::test_student_chat_count`, `ViewTests::test_open_marks_student_read` |
| AC9 | `SelectorTests::test_unread_first_then_newest`, `test_unread_counts`, `ViewTests::test_staff_open_marks_read_for_all_staff` |
| AC10 | `ViewTests::test_student_page_layout`, `test_staff_dialog_summary_link`, `test_staff_list_items`, `core/tests/test_nav.py` (updated) |
| AC11 | access matrix 6.2 |
| AC12 | `QueryCountTests::*` |
| AC13 | `test_demo.py::ChatSeedTests::*` |

### 6.2 Access matrix (`chat/tests/test_views.py::AccessTests`)
World: faculties FX, FY; students `ax` (FX), `bx` (FX), `ay` (FY), each with a dialog; staff `sx` (FX), `sy` (FY); superuser `root`; student `np` without profile.
| URL | anonymous | student own | student other's dialog | staff own faculty | staff other faculty | superuser |
|---|---|---|---|---|---|---|
| GET `/chat/` | 302 login | 200 (own messages only) | n/a (no id; `bx`'s texts absent for `ax`) | 403 | 403 | 403 |
| GET `/chat/updates/?after=0` | 302 | 200 own only | n/a (no id; only own) | 403 | 403 | 403 |
| POST `/chat/` | 302, no message | 302, message in own dialog | n/a | 403, no message | 403 | 403 |
| GET `/staff/chats/` | 302 | 403 | 403 | 200, FX dialogs only | (FY dialogs absent) | 403 |
| GET `/staff/chats/<ax uuid>/` | 302 | 403 | 403 | 200 | 404 (`sy`) | 403 |
| GET `/staff/chats/<ax uuid>/updates/?after=0` | 302 | 403 | 403 | 200 | 404 | 403 |
| POST `/staff/chats/<ax uuid>/` | 302, no message | 403, no message | 403 | 302, staff message | 404, no message | 403 |
| GET unknown uuid (staff) | — | — | — | 404 | 404 | — |
Plus: `np` (student without profile) → 403 on `/chat/`; HEAD and POST on `/chat/updates/` → 405; CSRF: `Client(enforce_csrf_checks=True)` POST without token to `/chat/` and to the staff dialog → 403, no message (`CsrfTests`). Test names: `test_<url-short>_<actor>` (e.g. `test_student_page_anonymous`, `test_staff_dialog_other_faculty_404`), one method per cell.

### 6.3 Behaviour and edge cases
`test_models.py::ModelTests`: `test_one_dialog_per_student` (IntegrityError), `test_db_rejects_empty_text`, `test_db_rejects_bad_role`, `test_client_token_unique_per_dialog` (IntegrityError; same token in another dialog OK; many `None` OK), `test_ordering_by_id`, `test_staff_short_name_nbsp` (`StaffProfile.short_name`).

`test_services.py::ServiceTests` (frozen clock):
- `test_first_message_creates_dialog`, `test_second_message_same_dialog`
- `test_text_normalised_and_limited` (`"a\r\nb  "` → `"a\nb"`; 2000 chars OK; 2001 → error; 2000 chars with `\r\n` counted after normalising)
- `test_empty_rejected` (`""`, `"  \n "`)
- `test_rate_limit` (20 OK, 21st → ValidationError, still 20 rows), `test_rate_limit_window_moves` (20 messages at T−11 min → OK now), `test_staff_no_rate_limit` (25 staff replies OK)
- `test_same_client_token_returns_existing` (same object, 1 row; does not count towards the limit)
- `test_two_staff_replies_both_kept_in_id_order` (two staff users of FX reply; both rows; ids increasing; `last_message_id` = second)
- `test_send_locks_dialog` (SQLite drops `FOR UPDATE` from the SQL, so assert the call instead: `orig = QuerySet.select_for_update`; `with mock.patch.object(QuerySet, "select_for_update", autospec=True, side_effect=orig) as spy:` send one student and one staff message → `spy.call_count == 2`)
- `test_staff_cannot_write_other_faculty` (PermissionDenied, no row), `test_student_cannot_use_staff_send` (PermissionDenied)
- `test_created_at_is_frozen_clock`
- `test_mark_read_monotonic` (5 then 3 → stays 5; 0 ignored)
- `test_history_limit` (105 messages → 100 newest, oldest first, `truncated` True)
- `test_messages_after` (after id, limit 50, ascending)

`test_selectors.py::SelectorTests`: names in 5.1.

`test_views.py::ViewTests` (frozen clock):
- `test_student_page_without_dialog` (empty-state text, form, no dialog row created by GET)
- `test_student_page_layout` (messages oldest first: `data-message-id` order ascending; form after the list; labels «Вы» and «Деканат · Фамилия И.»)
- `test_text_escaped_line_breaks_kept` (`"<b>x</b>\nстрока"` → `&lt;b&gt;x&lt;/b&gt;<br>строка`)
- `test_page_has_refresh_link_and_plain_form` (`<a href="/chat/">Обновить</a>`, `<form method="post" class="form chat-form" id="chat-form" action="/chat/">`, `name="csrfmiddlewaretoken"`, `name="client_token"`)
- `test_script_is_external_and_deferred` (`<script src="/static/js/chat.js" defer></script>` present; no `<script>` without `src` on the page)
- `test_post_redirects_to_form_anchor` (302, `Location` ends with `/chat/#chat-form`)
- `test_double_post_one_message` (two POSTs with the same `client_token` → both 302, one row)
- `test_post_invalid_shows_error` (empty text → 200, form error, no row), `test_post_rate_limited_shows_error`
- `test_open_marks_student_read` (staff message unread → GET `/chat/` → `student_read_id` = last id; staff marker unchanged)
- `test_staff_open_marks_read_for_all_staff` (`sx` opens → `staff_read_id` moves; for another FX staff member the list shows no unread)
- `test_staff_dialog_summary_link` (`href="/staff/students/<pk>/"`), `test_staff_list_items` (name, group, «новых: 2»)
- `test_no_store_on_all_chat_views` (`no-store` in `Cache-Control` for the 5 views)

`test_views.py::UpdatesViewTests`:
- `test_student_204_without_dialog`, `test_student_204_nothing_new`
- `test_student_returns_only_newer_fragment` (`after=<id>` → only `<li … data-message-id="…">` items with larger ids; no `<html`, no `<nav`; header `X-Chat-Fragment: 1`)
- `test_fragment_marks_read_up_to_last_returned`
- `test_bad_after_400` (`""`, `"abc"`, `"-1"`, `"1e3"`, 19 digits)
- `test_fragment_limit_50`
- `test_staff_fragment_scope` (other-faculty uuid → 404; own → 200)
- `test_fragment_escapes_text`

`test_views.py::AdminTests`: `test_admin_list_and_change_view_ok` (200 for superuser), `test_admin_is_read_only` (no add button URL: `admin:chat_dialog_add` → 403; change POST → 403; no delete).

`test_views.py::NavTests`: `test_student_chat_count` («Чат (1)» in both header lists), `test_student_chat_without_count` (`>Чат</a>`), `test_staff_nav_has_chats`, `test_badge_includes_chat_reply` (one unread staff message, no other items → «Уведомления (1)» outside the menu).

`test_views.py::QueryCountTests` (equal counts for small vs large data, plus an upper bound):
- `test_student_page_constant` (2 vs 30 messages; ≤ 14)
- `test_staff_list_constant` (1 vs 6 dialogs; ≤ 6)
- `test_staff_dialog_constant` (2 vs 30; ≤ 10)
- `test_fragment_constant` (1 vs 10 new messages; ≤ 8)
- `test_header_student_four_queries` (`assertNumQueries(4)` around rendering both tags: `badge_for_user(user)` + `student_unread_count(user)` → 3 + 1)
- `test_header_staff_no_chat_query` (`student_unread_count(staff)` → `assertNumQueries(0)`)

`test_feed.py::ChatFeedTests` (frozen clock):
- `test_unread_staff_reply_in_feed` (title, body preview ≤ 200 chars + «…», url `/chat/`)
- `test_own_student_messages_not_in_feed`
- `test_read_reply_leaves_feed` (after `mark_read`)
- `test_reply_counts_in_badge_once` (`unread_count` +1; after visiting «Уведомления» counted 0 by the notifications marker while the chat count stays 1)
- `test_other_student_reply_not_in_feed`
- `test_badge_still_three_queries` (existing `badge_for_user` 3 queries with chat rows present)

`test_static.py::ChatJsTests` (reads `static/js/chat.js`):
- `test_no_forbidden_apis` (none of `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval(`, `new Function`, `setInterval`)
- `test_uses_required_apis` (`DOMParser`, `visibilitychange`, `X-Chat-Fragment`, `importNode`, `data-chat-poll-url` / `chatPollUrl`, `textContent`)
- `test_strict_iife` (starts with `(function () {` and contains `"use strict"`)

`test_demo.py::ChatSeedTests` (`frozen_now = "2026-11-22 12:00"`, `call_command("seed_demo")` with patched `DEMO_PASSWORD`):
- `test_dialogs_and_messages` (3 dialogs, 8 messages, both roles in each of student1/student2 dialogs)
- `test_idempotent` (second run: same counts; output «Chat ready: 0 dialogs, 0 messages.»)
- `test_student1_has_unread_reply` (`student_unread_count(student1) == 1`; the feed has a `chat_reply` item)
- `test_each_faculty_has_unread_student_message` (`staff_dialog_list(staff1)` and `(staff2)` each have a dialog with `unread >= 1`)
- `test_messages_in_past_and_ordered` (`created_at <= now`; id order = time order per dialog)

Updated existing tests: `notifications/tests/test_feed.py::SourceRegistryTests::test_default_registry_has_six_sources` → `…_seven_sources` (7); `core/tests/test_nav.py` expected lists (4.7). Report both in the `REPORT`.

### 6.4 Settings branches
None. `check --deploy` must stay clean. The JS file is served by `{% static %}` (whitenoise manifest in production; `collectstatic` already part of deployment).

---

## 7. Implementation order
1. App skeleton, settings, URLs include, `pyproject.toml`; models + `StaffProfile.short_name`; migration; `test_models.py`.
2. Selectors and services + tests.
3. Forms, views, templates, CSS, nav (+ `core/tests/test_nav.py` update) + view tests.
4. `static/js/chat.js` + `test_static.py`; run `node --check static/js/chat.js`.
5. Feed source (+ registry test update) + `test_feed.py`.
6. Admin + seed + command + `test_demo.py`; README.
7. `ruff format` on changed/new Python files only; section 8; `REPORT` to the Reviewer. Do not commit.

## 8. Verification
```bash
source .venv/bin/activate
export DEBUG=true
TS=$(TZ=Europe/Moscow date +%Y%m%d-%H%M%S)
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test 2>&1 | tee "$TMPDIR/test-$TS.log"
python scripts/run_tests_at.py 2026-11-17T23:59:59 2>&1 | tee "$TMPDIR/test-$TS-at-2359.log"
python scripts/run_tests_at.py 2026-11-18T00:00:00 2>&1 | tee "$TMPDIR/test-$TS-at-0000.log"
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
ruff check . && ruff format --check .
node --check static/js/chat.js && echo "js syntax ok"
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
export DATABASE_URL="sqlite:///$TMPDIR/task009.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task009-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
rm -f "$TMPDIR/task009.sqlite3"
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
git status --short
```
`REPORT`: output tails, test count (was 833), log file names, any failed or stalled run by test name and Moscow time, `git status`.

## 9. Feasibility check (2026-11-15 20:20 MSK on `b3dcb37`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — `students_visible_to` (`accounts/selectors.py`), `get_profile_for_role`, `StudentRequiredMixin`, `StaffRequiredMixin` (`accounts/access.py`); `StaffProfile.full_name` (no `short_name` yet), `NBSP` (`university/models.py:8`); URL `accounts:staff_student_detail` (int pk); `core.clock.now`; `FeedSource`, `FeedItem`, `FEED_SOURCES` (6 sources) and its docstring naming TASK-009 as the extension point (`notifications/sources.py:1-7, 267-278`); `badge_for_user` (3 queries); `templates/base.html` (badge line, `{% load static notifications_tags %}`), `templates/includes/site_nav_items.html` (exact item order); `core/tests/test_nav.py` exact href lists (lines 45, 52-61); `notifications/tests/test_feed.py:646-647` (6 sources); `seed_demo` command order (`notifications` last); no `static/js/`; `extra_head` block in `base.html`. OK.
3. No collisions — no `chat` package, no URL `chat/` or `staff/chats/`, no related names `chat_dialog`/`chat_messages`, no template library `chat_tags`, no `static/js/chat.js`, no CSS `chat-*`. OK.
4. Migrations — new app only (`chat/0001_initial`); no change to existing tables (`short_name` is a property). `makemigrations --check` clean (9a).
5. Tools — Python 3.12, Django 5.2.19, ruff 0.17.4; Node v26.13.0 at `/opt/homebrew/bin/node` for `node --check` (syntax only). OK.
6. Framework — on a temporary seeded DB (Django 5.2.19, SQLite): a `UNION ALL … COUNT` where one part filters `id__gt=F("petition__student_id")` (an `F()` across a join, like `ChatReplySource`) runs as ONE query; `annotate(Count(…, filter=Q(…, rel__id__gt=F("field"))))` + `Case/When` + `order_by("has_unread", F(…).desc(nulls_last=True))` + `select_related` runs as ONE query. `select_for_update(of=("self",))` is ignored on SQLite (TASK-007). `never_cache`, `http_method_names`, `simple_tag … as`. Browser APIs (`fetch`, `DOMParser`, `document.importNode`, `visibilitychange`, `response.redirected`) are standard; the JS is checked in a real browser by the Team lead. OK.
7. Environment — nothing new. OK.
8. Verification runnable — see 9a.
9. Conflicts — none.
10. Assumptions / blockers — none.

### 9a. Verification results on the current tree
Logs `$TMPDIR/test-20261115-202032-t009-feas*.log`.
- `check` → no issues; `makemigrations --check --dry-run` → «No changes detected».
- `test` → `Ran 833 tests … OK`; `run_tests_at.py 2026-11-17T23:59:59` → 833 OK; `run_tests_at.py 2026-11-18T00:00:00` → 833 OK. No failed or stalled runs.
- `check --deploy --fail-level WARNING` → no issues (1 silenced); `ruff check .` → all passed; `ruff format --check .` → 161 files already formatted; CI YAML ok.
- `seed_demo` twice on a temporary DB and PRIVATE_MEDIA_ROOT → OK (second run «Notifications ready: 0 announcements.»).

## 10. Risks
- **Data leaks**: every lookup goes through `dialogs_visible_to`; fragment views apply the same scope; access matrix covers each cell.
- **XSS**: text is autoescaped server-side; the client never assigns HTML strings; `DOMParser` documents are inert; the static test forbids `innerHTML` & co.
- **Lost messages on screen**: prevented by the dialog lock (D3) and by de-duplicating appended ids.
- **Polling load**: one request per open tab every 5 s, paused when hidden; a fragment costs a fixed small number of queries; 204 when idle.
- **Session expiry during polling**: redirected responses are errors, never appended; polling stops after 5 errors with a visible notice.
- **GET side effect** (read markers): same justification as TASK-007 D3.
