# TASK-007: notifications — dean's-office announcements, deadlines, personal changes

Author: Planner. Status: ready for implementation.
Base commit: `8f7bc4f`. Related specs: `TASK-003.md` (schedule), `TASK-005.md` (academics), `TASK-006.md` (petitions).

Students get one page «Уведомления» with dean's-office news, the nearest deadlines and changes that concern them (request statuses and staff comments, schedule changes, new grades). Staff publish announcements for their own faculty or one of its groups and can unpublish them. The nav shows an unread counter.

---

## 1. Goal and acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | New app `notifications` with models `Announcement` and `NotificationState`, admin for `Announcement` (superuser), migrations. |
| AC2 | An announcement has exactly one audience: whole university (`university`, admin only), one faculty (`faculty`), or one study group (`group`). The DB enforces the audience/target combination. Lengths are named constants. |
| AC3 | Staff page «Объявления» (`/staff/announcements/`): list of their faculty's announcements (faculty- and group-addressed, published and unpublished), create form (target = own faculty or a group of own faculty, optional deadline), «Снять с публикации» button. Target and deadline are validated in the form AND in the service. A forged group (other faculty) or audience → form error, nothing created. |
| AC4 | Unpublish (`POST /staff/announcements/<uuid>/unpublish/`) is idempotent: the second call changes nothing and is not an error. Another faculty's or a university-wide announcement → 404. No edit, no hard delete on staff pages. |
| AC5 | Announcement bodies are plain text: autoescaped, line breaks kept (`linebreaksbr`), no HTML/Markdown rendering. |
| AC6 | Student page «Уведомления» (`/notifications/`): block «Ближайшие дедлайны» (deadline ≥ today, nearest first, label «сегодня» / «завтра» / «через N день/дня/дней»), then one feed (news + personal changes, newest first, last 30 days, at most 50 items), empty states. |
| AC7 | Personal changes are computed from existing records (no stored notification rows): staff status changes and staff comments on the student's requests; schedule changes of the student's group for lessons whose original or new date is in [today, today + 14]; the student's new current marks and final results. Changes made in the Django admin appear automatically. Each personal item links to its page (request detail / schedule week of the affected date / grades of the term). |
| AC8 | Unread state: per-user «seen until» timestamp. Nav shows «Уведомления (N)» for students (N = feed items newer than the last visit; «50+» above the cap). Opening `/notifications/` (GET) marks everything as read. HEAD/POST on that URL → 405. |
| AC9 | All date logic uses Moscow dates, including the midnight boundary. |
| AC10 | Access: students see only announcements addressed to the university, their faculty or their group, only published ones, and only their own personal changes; staff see and manage only their faculty's announcements (404 otherwise); students → 403 on staff pages; staff/superuser → 403 on the student page. |
| AC11 | Queries: the nav counter costs exactly 3 queries; the feed, staff list and home page have a constant number of queries (no N+1). |
| AC12 | Home page `core:home` for a student with a profile: 3 nearest deadlines and 3 latest news, each linking to «Уведомления». Other users see the current text. Login redirect unchanged. |
| AC13 | `seed_demo` (idempotent) creates 9 demo announcements: university, faculty and group news; deadlines at run day + 1…+5 (inside 23–28.11 when run on 22.11); one past deadline; one unpublished announcement per faculty; every demo student has unread items. Seeded grades get realistic `created_at` (grade date 18:00 MSK) so old grades do not flood the feed. |
| AC14 | Feed sources are a registry: TASK-009 (chat) adds a new source class without changing the feed, the counter or the templates. |
| AC15 | Nav: «Уведомления (N)» for students, «Объявления» for staff. |

## 2. Out of scope
E-mail, push, browser notifications, auto-refresh/polling, notifications for staff, attachments/images, rich text, editing announcements, per-item read state, chat (TASK-009), room map (TASK-008), visual theme, today's lessons on the home page, author name on announcement pages, re-publishing on the staff page (superuser can re-publish in the admin).

## 3. Design decisions (justification)

**D1. Computed feed, not stored notification rows.** Every personal event already has a row with a timestamp (`PetitionStatusChange.created_at`, `PetitionComment.created_at`, `LessonChange`, `CurrentMark`, `FinalResult`). Computing the feed from these rows:
- covers admin-made changes with no signals or admin hooks (the admin writes the same rows);
- cannot get out of sync (a deleted lesson change disappears from the feed; a stored row would stay);
- needs no fan-out writes (one announcement to a faculty would otherwise create one row per student).
Cost: one query per source per page (6 now) and one UNION query for the counter. Missing timestamps are added: `CurrentMark.created_at` (new), `LessonChange.updated_at` (new; an admin edit of a change makes it new again). `FinalResult.created_at` changes from `auto_now_add` to a default so the seed can set realistic values.

**D2. Read state = one timestamp per user (`NotificationState.seen_until`).** Unread = feed items with event time > `seen_until`. One row per student, no per-item rows, monotonic. Limitation: no per-item read flags (out of scope).

**D3. Marking as read happens on GET of `/notifications/`.** The requirement is "opening the page marks everything as read", so the state change is a side effect of viewing. It is safe because: (a) the effect is limited to the current user, idempotent and monotonic (`seen_until` never moves back) and destroys no data; (b) the session cookie is `SameSite=Lax` (Django default), so cross-site sub-requests (`<img>`, `<iframe>`, `fetch`) carry no session and change nothing; a cross-site top-level navigation does open the page for the user, so marking as read is then truthful; (c) `X_FRAME_OPTIONS = "DENY"` already blocks framing; (d) the view allows only GET (HEAD → 405, so link checkers using HEAD do not mark), and the response has `Cache-Control: no-store` (`never_cache`) so no proxy or browser cache serves a stale page. All real state changes (create, unpublish) are POST with CSRF.

**D4. Event clock.** All feed time comparisons use one `now` taken once per request; Moscow date `today = timezone.localdate(now)`. Feed window: `now - 30 days < event_time <= now`.

**D5. Clock-safe defaults.** `default=timezone.now` stores the original function object, so `FrozenClockMixin` (which patches `django.utils.timezone.now` after models are imported) does NOT freeze it (verified, see 9.6). New timestamp defaults use `core.clock.now`, which looks up `timezone.now` at call time. Services always pass timestamps explicitly from `timezone.now()`.

**D6. Audience storage without redundancy.** `faculty` is set only for `faculty` audience, `group` only for `group` audience. Staff scope: `faculty = F` OR `group.program.faculty = F`.

---

## 4. Architecture

### 4.1 Files

Create:
| File | Content |
|---|---|
| `core/clock.py` | `now()` (D5) |
| `notifications/__init__.py` | empty |
| `notifications/apps.py` | `NotificationsConfig` (`name = "notifications"`, `verbose_name = "Уведомления"`, `default_auto_field = "django.db.models.BigAutoField"`) |
| `notifications/constants.py` | all named constants (4.2) |
| `notifications/models.py` | `Audience`, `Announcement`, `NotificationState` |
| `notifications/migrations/__init__.py`, `notifications/migrations/0001_initial.py` | generated by `makemigrations notifications` |
| `notifications/dates.py` | `ru_plural`, `relative_day_label` |
| `notifications/selectors.py` | `announcements_for_student`, `announcements_managed_by` |
| `notifications/services.py` | `deadline_errors`, `create_announcement`, `unpublish_announcement`, `mark_seen` |
| `notifications/sources.py` | `FeedContext`, `FeedItem`, `FeedSource` + 6 sources, `get_feed_sources` |
| `notifications/feed.py` | `student_context`, `build_feed`, `unread_count`, `badge_label`, `badge_for_user`, `DeadlineItem`, `upcoming_deadlines`, `HomeSummary`, `home_summary` |
| `notifications/forms.py` | `AnnouncementForm` |
| `notifications/views.py` | `NotificationsView`, `StaffAnnouncementsView`, `StaffUnpublishView` |
| `notifications/urls.py` | 3 routes |
| `notifications/admin.py` | `AnnouncementAdmin` |
| `notifications/demo.py` | `seed_notifications_demo` |
| `notifications/templatetags/__init__.py`, `notifications/templatetags/notifications_tags.py` | `notifications_badge` tag |
| `notifications/templates/notifications/feed.html`, `staff_list.html`, `_deadlines.html` | templates |
| `notifications/tests/__init__.py`, `helpers.py`, `test_models.py`, `test_dates.py`, `test_services.py`, `test_feed.py`, `test_views.py`, `test_admin.py`, `test_demo.py` | tests (section 7) |
| `academics/migrations/0002_…py` (generated), `academics/migrations/0003_backfill_grade_created_at.py` (hand-written) | 4.4 |
| `schedule/migrations/0004_lessonchange_updated_at.py` (generated) | 4.4 |

Change:
| File | Change |
|---|---|
| `config/settings.py` | add `"notifications"` to `INSTALLED_APPS` right after `"petitions"` (before `"core"`) |
| `config/urls.py` | add `path("", include("notifications.urls")),` after the petitions include |
| `pyproject.toml` | add `"notifications"` to `known-first-party` |
| `academics/models.py` | `CurrentMark.created_at` (new), `FinalResult.created_at` (default instead of `auto_now_add`) |
| `schedule/models.py` | `LessonChange.updated_at` (new) |
| `academics/demo.py` | `recorded_at()` helper; pass `created_at` for seeded marks and results |
| `petitions/demo.py` | pass explicit `created_at` for seeded staff comments |
| `accounts/management/commands/seed_demo.py` | call `seed_notifications_demo(today)`; print one summary line |
| `templates/base.html` | nav links |
| `core/views.py`, `core/templates/core/home.html` | student summary |
| `static/css/base.css` | layout rules (4.9) |
| `README.md` | feature section + known limitations (4.10) |

Do not change any other file. No new dependencies, no new env variables.

### 4.2 Constants — `notifications/constants.py`
```python
TITLE_MAX_LENGTH = 150
BODY_MAX_LENGTH = 3000
FEED_WINDOW_DAYS = 30          # feed shows events of the last 30 days
FEED_MAX_ITEMS = 50            # feed length cap; badge shows "50+" above it
LESSON_CHANGE_HORIZON_DAYS = 14  # schedule changes for lessons in [today, today + 14]
DEADLINES_MAX_ITEMS = 10       # deadlines block on /notifications/
HOME_ITEMS = 3                 # deadlines and news on the home page
STAFF_LIST_MAX_ITEMS = 100     # newest announcements on the staff page
DEADLINE_MAX_DAYS_AHEAD = 365  # staff may set a deadline at most one year ahead
TARGET_FACULTY = "faculty"     # form value for "whole faculty"
TARGET_GROUP_PREFIX = "group-" # form value for a group: f"group-{pk}"
```

### 4.3 Models — `notifications/models.py`

```python
class Audience(models.TextChoices):
    UNIVERSITY = "university", "Весь университет"
    FACULTY = "faculty", "Факультет"
    GROUP = "group", "Группа"
```

`Announcement(models.Model)` (field order as listed):
| Field | Definition |
|---|---|
| `public_id` | `UUIDField(default=uuid.uuid4, unique=True, editable=False)` |
| `title` | `CharField("заголовок", max_length=TITLE_MAX_LENGTH)` |
| `body` | `TextField("текст", max_length=BODY_MAX_LENGTH)` |
| `audience` | `CharField("кому", max_length=16, choices=Audience.choices)` |
| `faculty` | `ForeignKey("university.Faculty", on_delete=PROTECT, null=True, blank=True, related_name="announcements", verbose_name="факультет")` |
| `group` | `ForeignKey("university.StudyGroup", on_delete=PROTECT, null=True, blank=True, related_name="announcements", verbose_name="группа")` |
| `deadline` | `DateField("срок (включительно)", null=True, blank=True)` |
| `author` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="announcements", verbose_name="автор")` |
| `published_at` | `DateTimeField("опубликовано", default=core.clock.now, editable=False)` |
| `is_published` | `BooleanField("опубликовано", default=True)` |
| `unpublished_at` | `DateTimeField("снято с публикации", null=True, blank=True, editable=False)` |
| `unpublished_by` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, null=True, blank=True, editable=False, related_name="+", verbose_name="снял с публикации")` |
| `seed_key` | `SlugField(max_length=40, blank=True, default="", editable=False)` |

`Meta`:
- `ordering = ["-published_at", "-pk"]`
- `indexes = [Index(fields=["is_published", "published_at"], name="notif_ann_published_idx"), Index(fields=["deadline"], name="notif_ann_deadline_idx")]`
- `constraints`:
  - `CheckConstraint(name="notifications_announcement_audience_target", condition=Q(audience="university", faculty__isnull=True, group__isnull=True) | Q(audience="faculty", faculty__isnull=False, group__isnull=True) | Q(audience="group", faculty__isnull=True, group__isnull=False), violation_error_message="Получатели не соответствуют аудитории: для всего университета не выбирайте ни факультет, ни группу; для факультета выберите только факультет; для группы выберите только группу.")`
  - `CheckConstraint(condition=~Q(title=""), name="notifications_announcement_title_not_empty")`
  - `CheckConstraint(condition=~Q(body=""), name="notifications_announcement_body_not_empty")`
  - `CheckConstraint(condition=Q(audience__in=["university", "faculty", "group"]), name="notifications_announcement_audience_value")`
  - `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="notifications_announcement_unique_seed_key")`
- `verbose_name = "объявление"`, `verbose_name_plural = "объявления"`

Methods (after `__str__`, ruff DJ012 order):
- `__str__` → `self.title`.
- `audience_label` (property) → `"Для всех студентов"` (university) / `f"Факультет: {self.faculty.name}"` / `f"Группа {self.group.name}"`. Callers must `select_related("faculty", "group")`.

No `clean()` on `Announcement`: the audience rule is the DB constraint above (Django's `full_clean` reports its `violation_error_message` as a non-field error, so admin errors never 500); the deadline rules are applied by the form and the service only, so the seed (past-deadline demo item) and the superuser in the admin may create past deadlines.

`NotificationState(models.Model)`:
| Field | Definition |
|---|---|
| `user` | `OneToOneField(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="notification_state", verbose_name="пользователь")` |
| `seen_until` | `DateTimeField("просмотрено до", null=True, blank=True)` |

`Meta`: `verbose_name = "состояние уведомлений"`, `verbose_name_plural = "состояния уведомлений"`. `__str__` → `f"{self.user_id}: {self.seen_until}"`. Not registered in the admin.

### 4.4 Changes to existing models and migrations

`core/clock.py`:
```python
"""Call-time clock for model defaults (test clock patches apply)."""
from datetime import datetime
from django.utils import timezone

def now() -> datetime:
    return timezone.now()
```
Never rename or move this function: migrations reference `core.clock.now`.

`academics/models.py`:
- `CurrentMark`: add after `kind` (before `seed_key`): `created_at = models.DateTimeField("внесено", default=now, editable=False)` where `from core.clock import now`.
- `FinalResult.created_at`: replace `auto_now_add=True` with `default=now, editable=False` (label stays «создано»).

`schedule/models.py`:
- `LessonChange`: add after `created_at`: `updated_at = models.DateTimeField("изменено", auto_now=True)`.

Migrations:
1. `python manage.py makemigrations academics schedule notifications` → expected files: `academics/migrations/0002_currentmark_created_at_alter_finalresult_created_at.py`, `schedule/migrations/0004_lessonchange_updated_at.py`, `notifications/migrations/0001_initial.py`. No interactive prompt is expected (`auto_now` and a callable default need no one-off default). If makemigrations prompts, stop and send a `QUESTION`.
2. Hand-write `academics/migrations/0003_backfill_grade_created_at.py`, dependency `("academics", "0002_currentmark_created_at_alter_finalresult_created_at")`:
```python
from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db import migrations
from django.utils import timezone

MOSCOW = ZoneInfo("Europe/Moscow")


def backfill(apps, schema_editor):
    now = timezone.now()
    for model_name in ("CurrentMark", "FinalResult"):
        model = apps.get_model("academics", model_name)
        rows = list(model.objects.only("pk", "date", "created_at"))
        for row in rows:
            recorded = min(datetime.combine(row.date, time(18, 0), tzinfo=MOSCOW), now)
            row.created_at = min(recorded, row.created_at)
        model.objects.bulk_update(rows, ["created_at"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [("academics", "0002_currentmark_created_at_alter_finalresult_created_at")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
```
Purpose: existing local rows (all created by an earlier seed) otherwise get "now" and flood every feed. On a fresh server DB the migration is a no-op. It uses only historical models (no app code).

### 4.5 URLs — `notifications/urls.py`
```python
app_name = "notifications"
urlpatterns = [
    path("notifications/", views.NotificationsView.as_view(), name="feed"),
    path("staff/announcements/", views.StaffAnnouncementsView.as_view(), name="staff_announcements"),
    path("staff/announcements/<uuid:public_id>/unpublish/", views.StaffUnpublishView.as_view(), name="staff_unpublish"),
]
```

### 4.6 Templates
- `base.html`, student branch, after the «Заявки» item:
  ```django
  {% notifications_badge as badge %}
  <li><a href="{% url 'notifications:feed' %}">Уведомления{% if badge %} ({{ badge }}){% endif %}</a></li>
  ```
  Staff branch, after the staff «Заявки» item: `<li><a href="{% url 'notifications:staff_announcements' %}">Объявления</a></li>`. Add `notifications_tags` to the `{% load static %}` line: `{% load static notifications_tags %}`.
- `notifications/_deadlines.html` (included by `feed.html`): `<ul class="deadline-list">` with one `<li id="deadline-{{ d.public_id }}">` per item: `<strong>{{ d.title }}</strong> — до {{ d.deadline|date:"d.m.Y" }}, {{ d.label }}` and `<span class="feed-meta">{{ d.audience_label }}</span>`; if empty: `<p>Ближайших дедлайнов нет.</p>`.
- `notifications/feed.html` (extends `base.html`, title «Уведомления»):
  ```django
  <h1>Уведомления</h1>
  <section aria-labelledby="deadlines-title">
    <h2 id="deadlines-title">Ближайшие дедлайны</h2>
    {% include "notifications/_deadlines.html" %}
  </section>
  <section aria-labelledby="feed-title">
    <h2 id="feed-title">Лента</h2>
    {% if items %}
    <ul class="feed">
      {% for item in items %}
      <li class="feed-item" id="{{ item.key }}">
        <p class="feed-meta">{% if item.is_new %}<strong>Новое</strong> · {% endif %}{{ item.tag }} · <time datetime="{{ item.timestamp|date:'c' }}">{{ item.timestamp|date:"d.m.Y H:i" }}</time>{% if item.audience_label %} · {{ item.audience_label }}{% endif %}</p>
        <h3>{% if item.url %}<a href="{{ item.url }}">{{ item.title }}</a>{% else %}{{ item.title }}{% endif %}</h3>
        {% if item.deadline %}<p>Срок: до {{ item.deadline|date:"d.m.Y" }}, {{ item.deadline_label }}</p>{% endif %}
        {% if item.body %}<p>{{ item.body|linebreaksbr }}</p>{% endif %}
      </li>
      {% endfor %}
    </ul>
    {% else %}
    <p>Уведомлений за последние 30 дней нет.</p>
    {% endif %}
  </section>
  ```
- `notifications/staff_list.html` (extends `base.html`, title «Объявления»):
  1. `<h1>Объявления</h1>`
  2. Section «Новое объявление»: `<form method="post" class="form">{% csrf_token %}{{ form.as_p }}<button type="submit">Опубликовать</button></form>` (action = same URL).
  3. Section «Объявления факультета»: `<ul class="feed">`, one `<li class="feed-item" id="announcement-{{ a.public_id }}">` per announcement: meta line `{{ a.audience_label }} · {{ a.published_at|date:"d.m.Y H:i" }} · ` + «Опубликовано» or «Снято с публикации {{ a.unpublished_at|date:"d.m.Y H:i" }}»; `<h3>{{ a.title }}</h3>`; deadline line if set; `<p>{{ a.body|linebreaksbr }}</p>`; if published: `<form method="post" action="{% url 'notifications:staff_unpublish' a.public_id %}" class="action-form">{% csrf_token %}<button type="submit">Снять с публикации</button></form>`. Empty state `<p>Объявлений пока нет.</p>`.
- `core/home.html`:
  ```django
  <h1>Цифровой деканат будущего</h1>
  {% if summary %}
    <section aria-labelledby="home-deadlines">
      <h2 id="home-deadlines">Ближайшие дедлайны</h2>
      {% if summary.deadlines %}<ul class="deadline-list">{% for d in summary.deadlines %}
        <li><a href="{% url 'notifications:feed' %}#deadline-{{ d.public_id }}">{{ d.title }}</a> — до {{ d.deadline|date:"d.m" }}, {{ d.label }}</li>
      {% endfor %}</ul>{% else %}<p>Ближайших дедлайнов нет.</p>{% endif %}
    </section>
    <section aria-labelledby="home-news">
      <h2 id="home-news">Новости деканата</h2>
      {% if summary.news %}<ul class="deadline-list">{% for item in summary.news %}
        <li><a href="{% url 'notifications:feed' %}#{{ item.key }}">{{ item.title }}</a> <span class="feed-meta">{{ item.timestamp|date:"d.m" }}</span></li>
      {% endfor %}</ul>{% else %}<p>Новостей пока нет.</p>{% endif %}
    </section>
    <p class="page-actions"><a href="{% url 'notifications:feed' %}">Все уведомления</a></p>
  {% else %}
    <p>Прототип личного кабинета студента. Раздел в разработке.</p>
  {% endif %}
  ```

### 4.7 Admin — `notifications/admin.py`
`AnnouncementAdmin(admin.ModelAdmin)`, registered for `Announcement`:
- `list_display = ("title", "audience", "faculty", "group", "deadline", "is_published", "published_at")`, `list_filter = ("audience", "is_published")`, `search_fields = ("title",)`, `list_select_related = ("faculty", "group")`.
- `fields = ("title", "body", "audience", "faculty", "group", "deadline", "is_published", "author", "published_at", "unpublished_at", "unpublished_by")` (explicit list, ruff DJ007); `readonly_fields = ("author", "published_at", "unpublished_at", "unpublished_by")`.
- `save_model(self, request, obj, form, change)`:
  1. if not change: `obj.author = request.user`.
  2. if `"is_published" in form.changed_data` or not change:
     - if `obj.is_published`: `obj.unpublished_at = None`, `obj.unpublished_by = None`;
     - else: `obj.unpublished_at = timezone.now()`, `obj.unpublished_by = request.user`.
  3. `super().save_model(...)`.
- Default delete stays (superuser only; staff pages have no delete).

### 4.8 Views — `notifications/views.py`

`NotificationsView(StudentRequiredMixin, TemplateView)`, decorated `@method_decorator(never_cache, name="dispatch")`:
- `template_name = "notifications/feed.html"`, `http_method_names = ["get"]` (HEAD/POST → 405).
- `get_context_data`: `ctx = student_context(self.request.user)`; if `None` → `raise PermissionDenied`; `context["deadlines"] = upcoming_deadlines(ctx, DEADLINES_MAX_ITEMS)`; `context["items"] = build_feed(ctx)`; then `mark_seen(ctx.user_id, ctx.now)` (after building, so `is_new` uses the old value). Return context.

`StaffAnnouncementsView(StaffRequiredMixin, TemplateView)`:
- `template_name = "notifications/staff_list.html"`, `http_method_names = ["get", "post"]`.
- `_form(self, data=None) -> AnnouncementForm`: `AnnouncementForm(data, faculty=self.profile.faculty, groups=list(groups_visible_to(self.request.user).order_by("name")), today=timezone.localdate())`.
- `_render(self, form) -> HttpResponse`: `announcements = announcements_managed_by(self.request.user).select_related("faculty", "group").order_by("-published_at", "-pk")[:STAFF_LIST_MAX_ITEMS]`; `return self.render_to_response(self.get_context_data(form=form, announcements=announcements))`.
- `get`: `return self._render(self._form())`.
- `post`: `form = self._form(request.POST)`; if valid: try `create_announcement(request.user, title=…, body=…, audience=form.cleaned_data["audience"], group=form.cleaned_data["group"], deadline=form.cleaned_data["deadline"])`; on `ValidationError as exc`: `form.add_error(None, ValidationError(exc.messages))`; else `messages.success(request, "Объявление опубликовано.")` and `return redirect("notifications:staff_announcements")`. Fall through: `return self._render(form)` (status 200).

`StaffUnpublishView(StaffRequiredMixin, View)`:
- `http_method_names = ["post"]`.
- `post(self, request, public_id)`: try `changed = unpublish_announcement(request.user, public_id)` except `Announcement.DoesNotExist` → `raise Http404`. Message: changed → `messages.success(request, "Объявление снято с публикации.")`; not changed → `messages.info(request, "Объявление уже снято с публикации.")`. `return redirect("notifications:staff_announcements")`.

`core/views.py` `HomeView.get_context_data`: `context["summary"] = home_summary(self.request.user)` (import from `notifications.feed`).

### 4.9 CSS — append to `static/css/base.css` (layout only, tokens only)
```css
.feed,
.deadline-list {
  list-style: none;
  margin: 0 0 var(--space-3);
  padding: 0;
}

.feed-item,
.deadline-list li {
  margin-bottom: var(--space-3);
  overflow-wrap: anywhere;
}

.feed-item h3 {
  margin: var(--space-1) 0;
  font-size: var(--font-size-base);
}

.feed-meta {
  margin: 0;
  font-size: 0.875rem;
}
```
Do not change `tokens.css` or `theme.css` (`core/tests/test_css.py` asserts this for `max-width`).

### 4.10 README
- New section `## Notifications` (after the requests section): what students see (deadlines block, feed of news + personal changes, 30 days / 50 items, schedule horizon 14 days), unread counter semantics (one «seen until» per account; opening the page marks all as read), staff page (faculty/group only, unpublish, no edit/delete), university-wide announcements only via the admin, demo data (9 announcements; deadlines run day +1…+5).
- "Known limitations": add two bullets: «The unread counter is per account: after one person opens «Уведомления» as `student1`, others logged in as `student1` see no new items.» and «Grades and lesson changes appear in the feed by the time they were recorded; a grade entered later for an old date still shows as new.»

---

## 5. Functions

All functions have type hints. `FeedContext` etc. are defined in `notifications/sources.py`.

### 5.1 `notifications/dates.py`

**`ru_plural(n: int, one: str, few: str, many: str) -> str`**
Purpose: Russian plural form. Algorithm: `n = abs(n)`; if `n % 10 == 1 and n % 100 != 11` → `one`; elif `n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14)` → `few`; else `many`.
Tests (`test_dates.py::RuPluralTests::test_forms`): 1 день, 2 дня, 4 дня, 5 дней, 11 дней, 12 дней, 14 дней, 21 день, 22 дня, 25 дней, 101 день, 111 дней, 112 дней, 0 дней.

**`relative_day_label(day: date, today: date) -> str`**
Purpose: label for a deadline. `delta = (day - today).days`: `< 0` → `"срок прошёл"`; `0` → `"сегодня"`; `1` → `"завтра"`; else `f"через {delta} {ru_plural(delta, 'день', 'дня', 'дней')}"`.
Tests (`RelativeDayLabelTests`): `test_past`, `test_today`, `test_tomorrow`, `test_two_days` («через 2 дня»), `test_five_days` («через 5 дней»), `test_twenty_one_days` («через 21 день»).

### 5.2 `notifications/selectors.py`

**`announcements_for_student(student: StudentProfile) -> QuerySet[Announcement]`**
Purpose: published announcements addressed to this student. Requires `student.group.program` to be loaded (uses `student.group.program.faculty_id`). Returns `Announcement.objects.filter(is_published=True).filter(Q(audience=Audience.UNIVERSITY) | Q(audience=Audience.FACULTY, faculty_id=faculty_id) | Q(audience=Audience.GROUP, group_id=student.group_id))`. No time filter, no ordering change.
Callers: feed sources and `upcoming_deadlines` only, always with the profile of `request.user`.
Tests: `test_feed.py::StudentScopeTests` (5.6).

**`announcements_managed_by(user: AbstractBaseUser | AnonymousUser) -> QuerySet[Announcement]`**
Purpose: announcements a staff member sees and manages. Algorithm: not authenticated / not active / role ≠ staff → `Announcement.objects.none()`; `profile = user.staff_profile` (`ObjectDoesNotExist` → `none()`); return `Announcement.objects.filter(Q(audience=Audience.FACULTY, faculty_id=profile.faculty_id) | Q(audience=Audience.GROUP, group__program__faculty_id=profile.faculty_id))`. Published and unpublished. University-wide never.
Tests: `test_services.py::ManagedBySelectorTests`: `test_staff_sees_faculty_and_group_items`, `test_staff_does_not_see_other_faculty`, `test_staff_does_not_see_university`, `test_student_and_superuser_get_none`, `test_staff_without_profile_gets_none`, `test_inactive_staff_gets_none`.

### 5.3 `notifications/services.py`

**`deadline_errors(deadline: date | None, today: date) -> list[str]`**
`None` → `[]`; `deadline < today` → `["Срок не может быть в прошлом."]`; `deadline > today + timedelta(days=DEADLINE_MAX_DAYS_AHEAD)` → `[f"Срок — не позже чем через {DEADLINE_MAX_DAYS_AHEAD} дней."]`; else `[]`.
Tests (`DeadlineErrorsTests`): `test_none_ok`, `test_today_ok`, `test_yesterday_error`, `test_max_ahead_ok` (today + 365), `test_beyond_max_error` (today + 366).

**`create_announcement(author: User, *, title: str, body: str, audience: str, group: StudyGroup | None, deadline: date | None) -> Announcement`**
Purpose: the only write path for staff-created announcements.
Algorithm:
1. `staff = get_profile_for_role(author, User.Role.STAFF)` (raises `PermissionDenied` for anyone else).
2. `now = timezone.now()`; `today = timezone.localdate(now)`.
3. `errors = deadline_errors(deadline, today)`.
4. If `audience == Audience.FACULTY`: `faculty, target_group = staff.faculty, None`.
   Elif `audience == Audience.GROUP`: if `group is None` → append «Выберите группу.»; elif `not groups_visible_to(author).filter(pk=group.pk).exists()` → append «Группа не относится к вашему факультету.»; `faculty, target_group = None, group`.
   Else → append «Сотрудник может адресовать объявление только своему факультету или его группе.»
5. If `errors` → `raise ValidationError(errors)` (non-field).
6. `with transaction.atomic():` build `Announcement(title=title, body=body, audience=audience, faculty=faculty, group=target_group, deadline=deadline, author=author, published_at=now, is_published=True)`, `full_clean()`, `save()`. Return it.
Edge cases: title/body too long or empty → `full_clean` raises a field-keyed `ValidationError`. The form limits lengths first, so this is a fallback. The view always adds service errors as non-field errors with `form.add_error(None, ValidationError(exc.messages))` (passing a dict-based error with a key that is not a form field would raise `ValueError` → 500).
Tests (`CreateAnnouncementTests`): `test_faculty_announcement` (fields set, `published_at == frozen now`, `author`), `test_own_group_announcement` (`faculty is None`, `group` set), `test_other_faculty_group_rejected` (ValidationError, count 0), `test_university_rejected`, `test_group_without_group_rejected`, `test_past_deadline_rejected`, `test_deadline_today_ok`, `test_too_long_title_rejected`, `test_student_author_denied` (PermissionDenied), `test_superuser_author_denied`.

**`unpublish_announcement(actor: User, public_id: UUID) -> bool`**
Purpose: idempotent unpublish. Returns `True` if the state changed, `False` if it was already unpublished.
Algorithm:
1. `get_profile_for_role(actor, User.Role.STAFF)`.
2. `with transaction.atomic():` `ann = announcements_managed_by(actor).select_for_update(of=("self",)).filter(public_id=public_id).first()`; if `None` → `raise Announcement.DoesNotExist`.
3. If not `ann.is_published` → return `False`.
4. `ann.is_published = False`, `ann.unpublished_at = timezone.now()`, `ann.unpublished_by = actor`; `ann.save(update_fields=["is_published", "unpublished_at", "unpublished_by"])`; return `True`.
Note: `of=("self",)` locks only the announcement row; without it PostgreSQL rejects `FOR UPDATE` on the nullable side of the outer join used by the group filter. SQLite ignores `select_for_update`.
Tests (`UnpublishTests`): `test_unpublish_own_faculty` (True, fields set), `test_unpublish_own_group_item`, `test_second_call_is_noop` (False, `unpublished_at` unchanged), `test_other_faculty_raises_does_not_exist`, `test_university_raises_does_not_exist`, `test_student_denied`.

**`mark_seen(user_id: int, now: datetime) -> None`**
Purpose: move `seen_until` forward to `now`; never backwards.
Algorithm: `updated = NotificationState.objects.filter(user_id=user_id).filter(Q(seen_until__isnull=True) | Q(seen_until__lt=now)).update(seen_until=now)`; if `updated == 0`: `NotificationState.objects.get_or_create(user_id=user_id, defaults={"seen_until": now})`.
Tests (`MarkSeenTests`): `test_creates_state`, `test_moves_forward`, `test_never_moves_back` (state in the future stays), `test_null_state_is_set`.

### 5.4 `notifications/sources.py`

```python
@dataclass(frozen=True)
class FeedContext:
    user_id: int
    student: StudentProfile          # loaded with select_related("group__program")
    group_id: int
    faculty_id: int
    now: datetime
    today: date                      # timezone.localdate(now)
    window_start: datetime           # now - timedelta(days=FEED_WINDOW_DAYS)
    seen_until: datetime | None

    def is_new(self, ts: datetime) -> bool:
        return self.seen_until is None or ts > self.seen_until

    @property
    def horizon_end(self) -> date:
        return self.today + timedelta(days=LESSON_CHANGE_HORIZON_DAYS)


@dataclass(frozen=True)
class FeedItem:
    key: str              # unique, used as HTML id, e.g. "news-<uuid>", "mark-<pk>"
    kind: str             # source kind
    tag: str              # Russian label shown in the meta line
    timestamp: datetime
    title: str
    body: str = ""
    url: str = ""
    deadline: date | None = None
    deadline_label: str = ""
    audience_label: str = ""
    is_new: bool = False
```

`class FeedSource` (base class; subclasses set class attributes and override two methods):
```python
    kind: ClassVar[str]
    tag: ClassVar[str]
    event_field: ClassVar[str]                 # aware DateTimeField of the model
    related: ClassVar[tuple[str, ...]] = ()     # select_related for rendering

    def base_queryset(self, ctx: FeedContext) -> QuerySet:   # rows that concern ctx.student; override
        raise NotImplementedError

    def to_item(self, obj: Any, ctx: FeedContext) -> FeedItem:  # override; is_new is set by latest()
        raise NotImplementedError

    def window_queryset(self, ctx: FeedContext) -> QuerySet:
        f = self.event_field
        return self.base_queryset(ctx).filter(**{f"{f}__gt": ctx.window_start, f"{f}__lte": ctx.now}).order_by()

    def unread_values(self, ctx: FeedContext) -> QuerySet:
        qs = self.window_queryset(ctx)
        if ctx.seen_until is not None:
            qs = qs.filter(**{f"{self.event_field}__gt": ctx.seen_until})
        return qs.values_list(self.event_field)

    def latest(self, ctx: FeedContext, limit: int) -> list[FeedItem]:
        qs = self.window_queryset(ctx).select_related(*self.related).order_by(f"-{self.event_field}", "-pk")[:limit]
        return [replace(item, is_new=ctx.is_new(item.timestamp)) for item in (self.to_item(o, ctx) for o in qs)]
```
(`replace` = `dataclasses.replace`.) One query per `latest()` call.

Sources (all in `sources.py`):

| Class | kind / tag | Model, `event_field`, `related` | `base_queryset(ctx)` |
|---|---|---|---|
| `NewsSource` | `news` / «Новость» («Дедлайн» if `deadline`) | `Announcement`, `published_at`, `("faculty", "group")` | `announcements_for_student(ctx.student)` |
| `PetitionStatusSource` | `petition_status` / «Заявка» | `PetitionStatusChange`, `created_at`, `("petition__request_type",)` | `filter(petition__student_id=ctx.student.pk).exclude(actor_id=ctx.user_id)` |
| `PetitionCommentSource` | `petition_comment` / «Заявка» | `PetitionComment`, `created_at`, `("petition__request_type",)` | `filter(petition__student_id=ctx.student.pk).exclude(author_id=ctx.user_id)` |
| `LessonChangeSource` | `lesson_change` / «Расписание» | `LessonChange`, `updated_at`, `("weekly_lesson__discipline", "new_room", "new_teacher")` | `filter(weekly_lesson__groups=ctx.group_id).filter(Q(original_date__range=(ctx.today, ctx.horizon_end)) \| Q(new_date__range=(ctx.today, ctx.horizon_end)))` |
| `CurrentMarkSource` | `mark` / «Оценка» | `CurrentMark`, `created_at`, `("curriculum_item__discipline", "curriculum_item__term")` | `filter(student_id=ctx.student.pk)` |
| `FinalResultSource` | `final_result` / «Оценка» | `FinalResult`, `created_at`, same as marks | `filter(student_id=ctx.student.pk)` |

`to_item` per source (timestamps = the `event_field` value):
- `NewsSource`: `key=f"news-{o.public_id}"`, `tag` = «Дедлайн» if `o.deadline` else «Новость», `title=o.title`, `body=o.body`, `deadline=o.deadline`, `deadline_label=relative_day_label(o.deadline, ctx.today)` if deadline else `""`, `audience_label=o.audience_label`, `url=""`.
- `PetitionStatusSource`: `key=f"petition-status-{o.pk}"`; `name = o.petition.request_type.name`; title from `STATUS_TITLES = {"in_progress": "Заявка «{name}» взята в работу", "ready": "Заявка «{name}» готова — заберите документ в деканате", "issued": "Заявка «{name}» выдана", "rejected": "Заявка «{name}» отклонена"}`, default `"Заявка «{name}»: статус «{status}»"` with `status=o.get_to_status_display()`; `body=o.comment`; `url=reverse("petitions:detail", kwargs={"public_id": o.petition.public_id})`.
- `PetitionCommentSource`: `key=f"petition-comment-{o.pk}"`, title `f"Комментарий деканата к заявке «{name}»"`, `body=o.text`, url as above.
- `LessonChangeSource`: `key=f"lesson-change-{o.pk}"`; `lesson = o.weekly_lesson`; `when = f"{lesson.discipline.name}, {o.original_date:%d.%m}, {lesson.slot} пара"`; title by kind:
  - cancelled: `f"Отмена занятия: {when}"`
  - moved: `f"Перенос занятия: {when} → {o.new_date:%d.%m}, {o.new_slot} пара"` + `f", {o.new_room}"` if `o.new_room` (Room `__str__` is «ауд. N»)
  - room_changed: `f"Замена аудитории: {when} → {o.new_room}"`
  - teacher_replaced: `f"Замена преподавателя: {when} → {o.new_teacher.short_name}"`
  `body=o.reason`; affected day = `o.original_date` if `ctx.today <= o.original_date <= ctx.horizon_end` else `o.new_date`; `url=reverse("schedule:week_of", kwargs={"day": affected_day})`.
- `CurrentMarkSource`: `key=f"mark-{o.pk}"`, title `f"Новая оценка {o.value} — {discipline.name} ({o.kind})"`, `url=reverse("academics:my_grades_term", kwargs={"term_code": term.code})`.
- `FinalResultSource`: `key=f"final-result-{o.pk}"`, title `f"Итоговый результат — {discipline.name}: {o.get_result_display()}"` + `f" (попытка {o.attempt})"` if `o.attempt > 1`; url as for marks.

**`get_feed_sources() -> tuple[FeedSource, ...]`** returns the module constant `FEED_SOURCES = (NewsSource(), PetitionStatusSource(), PetitionCommentSource(), LessonChangeSource(), CurrentMarkSource(), FinalResultSource())`. Extension point for TASK-009: add a `FeedSource` subclass and append it to `FEED_SOURCES`; nothing else changes. Add this sentence as the module docstring.

Edge cases: the student's own status change (submission) and own comments are excluded by actor/author; a lesson change of a lesson shared by two groups appears for both groups (one row per student because the filter is on one group id); a moved lesson whose original date is before today but new date is in the horizon is included and links to the new date's week.

### 5.5 `notifications/feed.py`

**`student_context(user: AbstractBaseUser | AnonymousUser, now: datetime | None = None) -> FeedContext | None`**
1. If not authenticated, not active, or `user.role != User.Role.STUDENT` → `None` (no query).
2. `student = StudentProfile.objects.select_related("group__program").filter(user_id=user.pk).first()` → `None` → return `None`. (1 query)
3. `seen = NotificationState.objects.filter(user_id=user.pk).values_list("seen_until", flat=True).first()` (1 query).
4. `now = now or timezone.now()`; return `FeedContext(user_id=user.pk, student=student, group_id=student.group_id, faculty_id=student.group.program.faculty_id, now=now, today=timezone.localdate(now), window_start=now - timedelta(days=FEED_WINDOW_DAYS), seen_until=seen)`.

**`build_feed(ctx: FeedContext) -> list[FeedItem]`**
`items = [item for source in get_feed_sources() for item in source.latest(ctx, FEED_MAX_ITEMS)]`; `items.sort(key=lambda i: (i.timestamp, i.key), reverse=True)`; return `items[:FEED_MAX_ITEMS]`. Import `get_feed_sources` by name (`from notifications.sources import get_feed_sources`) so tests patch `notifications.feed.get_feed_sources`.

**`unread_count(ctx: FeedContext) -> int`**
`querysets = [s.unread_values(ctx) for s in get_feed_sources()]`; empty → 0; return `querysets[0].union(*querysets[1:], all=True).count()` (one SQL query; every part has cleared ordering, see `window_queryset`).

**`badge_label(count: int) -> str`**: `0` → `""`; `count > FEED_MAX_ITEMS` → `f"{FEED_MAX_ITEMS}+"`; else `str(count)`.

**`badge_for_user(user) -> str`**: `ctx = student_context(user)`; `None` → `""`; return `badge_label(unread_count(ctx))`. Exactly 3 queries for a student with a profile (profile, state, union count).

**`DeadlineItem`** (frozen dataclass): `public_id: UUID`, `title: str`, `deadline: date`, `label: str`, `audience_label: str`.

**`upcoming_deadlines(ctx: FeedContext, limit: int) -> list[DeadlineItem]`**
`announcements_for_student(ctx.student).filter(deadline__gte=ctx.today, published_at__lte=ctx.now).select_related("faculty", "group").order_by("deadline", "-published_at", "pk")[:limit]` → `DeadlineItem(..., label=relative_day_label(a.deadline, ctx.today), audience_label=a.audience_label)`. Not limited by the 30-day window (an old announcement with a future deadline still shows). 1 query.

**`HomeSummary`** (frozen dataclass): `deadlines: list[DeadlineItem]`, `news: list[FeedItem]`.

**`home_summary(user) -> HomeSummary | None`**: `ctx = student_context(user)`; `None` → `None`; return `HomeSummary(deadlines=upcoming_deadlines(ctx, HOME_ITEMS), news=NewsSource().latest(ctx, HOME_ITEMS))`. Does not mark anything as read.

### 5.6 `notifications/templatetags/notifications_tags.py`
`register = template.Library()`; `@register.simple_tag(takes_context=True) def notifications_badge(context) -> str`: `request = context.get("request")`; no request → `""`; return `badge_for_user(request.user)`. Used only inside the student branch of `base.html`, so staff/superuser/anonymous pages run no extra query.

### 5.7 `notifications/forms.py` — `AnnouncementForm(forms.Form)`
Fields:
- `title = forms.CharField(label="Заголовок", max_length=TITLE_MAX_LENGTH)`
- `body = forms.CharField(label="Текст", max_length=BODY_MAX_LENGTH, widget=forms.Textarea(attrs={"rows": 6}))`
- `target = forms.ChoiceField(label="Кому")`
- `deadline = forms.DateField(label="Срок (необязательно)", required=False, help_text="Последний день, включительно.", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))`

`__init__(self, *args, faculty: Faculty, groups: Sequence[StudyGroup], today: date, **kwargs)`: store `today`; `self._groups = {f"{TARGET_GROUP_PREFIX}{g.pk}": g for g in groups}`; `self.fields["target"].choices = [(TARGET_FACULTY, f"Весь факультет: {faculty.name}")] + [(key, f"Группа {g.name}") for key, g in self._groups.items()]`.
`clean_deadline`: `errors = deadline_errors(value, self.today)`; errors → `raise forms.ValidationError(errors)`.
`clean`: `target = cleaned.get("target")`; `TARGET_FACULTY` → `cleaned["audience"] = Audience.FACULTY`, `cleaned["group"] = None`; key in `self._groups` → `Audience.GROUP` and the group. (Any other value is already rejected by `ChoiceField`.)
Tests (`test_views.py::AnnouncementFormTests`): `test_choices_only_own_faculty_groups`, `test_faculty_target`, `test_group_target`, `test_forged_group_rejected` (`"group-<other faculty pk>"`), `test_university_value_rejected`, `test_iso_date_accepted` («2026-11-20»), `test_past_deadline_field_error`.

### 5.8 Seed — `notifications/demo.py`

```python
@dataclass(frozen=True)
class AnnouncementSeed:
    key: str
    audience: str
    target: str | None        # faculty code, group name, or None for university
    author: str               # username
    title: str
    body: str
    age_hours: int            # published_at = now - age_hours
    deadline_offset: int | None
    published: bool = True

@dataclass(frozen=True)
class NotificationsSeedSummary:
    announcements: int        # created in this run
```

`ANNOUNCEMENT_SEEDS` (fictional; bodies use `\n` for line breaks):
| key | audience | target | author | title | body | age_hours | deadline_offset | published |
|---|---|---|---|---|---|---|---|---|
| n-1 | university | — | staff1 | Открыта запись в студенческие клубы | Записаться можно в студенческом совете до конца месяца.\nСписок клубов — на стенде у главного входа. | 72 | None | yes |
| n-2 | university | — | staff1 | Анкета «Качество обучения» | Пройдите анонимную анкету о качестве преподавания.\nСсылку пришлёт староста группы. | 26 | 5 | yes |
| n-3 | faculty | FDD | staff1 | Выбор темы курсовой работы | Сообщите тему и научного руководителя в деканат.\nСписок тем — на кафедре. | 50 | 1 | yes |
| n-4 | group | ЦД-101 | staff1 | Отчёт по учебной практике | Сдайте отчёт старосте группы в бумажном виде. | 5 | 3 | yes |
| n-5 | faculty | FAE | staff2 | Эссе по микроэкономике | Сдайте эссе на кафедру.\nОбъём — до 5 страниц. | 30 | 2 | yes |
| n-6 | group | ЭД-201 | staff2 | Собрание группы ЭД-201 | В четверг после третьей пары, ауд. 114. | 4 | None | yes |
| n-7 | faculty | FDD | staff1 | Запись на факультативы | Запись на факультативы весеннего семестра. | 144 | -2 | yes |
| n-8 | faculty | FDD | staff1 | Изменение графика работы деканата | График работы не изменился, объявление снято. | 48 | None | no |
| n-9 | faculty | FAE | staff2 | Консультация по стипендиям | Консультация перенесена, объявление снято. | 20 | None | no |

**`seed_notifications_demo(today: date) -> NotificationsSeedSummary`**
1. `with transaction.atomic():` `base = timezone.now()`; load `faculties` by code (`FDD`, `FAE`), `groups` by name (`ЦД-101`, `ЭД-201`), `authors` by username (`staff1`, `staff2`).
2. For each seed: skip if `Announcement.objects.filter(seed_key=seed.key).exists()` (existing rows are never updated).
3. `published_at = base - timedelta(hours=seed.age_hours)`; build `Announcement(title, body, audience, faculty=faculties[target] if faculty else None, group=groups[target] if group else None, deadline=today + timedelta(days=offset) if offset is not None else None, author=authors[seed.author], published_at=published_at, is_published=seed.published, seed_key=seed.key)`; if not published: `unpublished_at = published_at + timedelta(hours=1)`, `unpublished_by = author`.
4. `full_clean()`; `save()`; count.
5. Return the summary.

`seed_demo` command: after `p = seed_petitions_demo(today)` add `n = seed_notifications_demo(today)` (inside the same `transaction.atomic()`), and after the requests line print `self.style.SUCCESS(f"Notifications ready: {n.announcements} announcements.")`.

`academics/demo.py`: add
```python
def recorded_at(day: date) -> datetime:
    """Seeded grades look recorded on their date at 18:00 Moscow time (never in the future)."""
    return min(timezone.make_aware(datetime.combine(day, time(18, 0))), timezone.now())
```
(`timezone.make_aware` uses the current time zone, Europe/Moscow.) Pass `created_at=recorded_at(d)` to the seeded `FinalResult(...)` and `created_at=recorded_at(mark_date)` to the seeded `CurrentMark(...)`.

`petitions/demo.py`: the staff comment gets `created_at=created_at + timedelta(hours=20 * len(steps))` (after the last status step). Reason: the default `timezone.now` is not frozen in tests (D5).

---

## 6. Access rules summary
- Student feed and home summary: built only from `request.user`'s own profile; no IDs in URLs.
- Staff: `announcements_managed_by(request.user)` is the only lookup for listing and unpublishing; it never returns other faculties' or university-wide rows → 404.
- Create: the form offers only own faculty and own groups; the service re-checks with `groups_visible_to`.
- Role guards: `StudentRequiredMixin` / `StaffRequiredMixin` (403 for wrong role, superuser and missing profile); `LoginRequiredMiddleware` → 302 for anonymous.

---

## 7. Test plan

### 7.0 Rules for all new tests
- Test data via helpers only (`accounts/tests/helpers.py`, `schedule/tests/helpers.py`, `academics/tests/helpers.py`, `petitions/tests/helpers.py`, and the new `notifications/tests/helpers.py`); never depend on seed data except in `test_demo.py`.
- Every class uses `FrozenClockMixin` with `frozen_now = "2026-11-11 12:00"` (a Wednesday **before** the real current date) unless stated otherwise. Reason: any timestamp that leaks from the real clock (unfrozen default) is then later than `now`, falls outside the feed and fails the test immediately instead of after some future date.
- Create `PetitionStatusChange` / `PetitionComment` rows with an explicit `created_at` (or through `change_status` / `add_staff_comment`, which set it). Never rely on `default=timezone.now` in tests.
- For "newer than last visit" cases set `NotificationState.seen_until` directly and create rows with explicit timestamps before/after it.
- Save full test output to a file (`… 2>&1 | tee "$TMPDIR/test-<timestamp>.log"`); report any failure by test name, Moscow time and traceback excerpt.

`notifications/tests/helpers.py`:
- `make_announcement(author, *, audience, faculty=None, group=None, title="Объявление", body="Текст объявления", deadline=None, published_at=None, is_published=True) -> Announcement` — `Announcement.objects.create(...)` with `published_at=published_at or timezone.now()`; if not published, set `unpublished_at=published_at` and `unpublished_by=author`.
- `set_seen(user, when) -> None` — `NotificationState.objects.update_or_create(user=user, defaults={"seen_until": when})`.
- `make_world() -> SimpleNamespace` — two faculties `FX`, `FY`; groups `GX1`, `GX2` (FX) and `GY1` (FY); students `ax` (GX1), `bx` (GX1), `cx` (GX2), `ay` (GY1); staff `sx` (FX), `sy` (FY); superuser `root`. Returns all objects (users and profiles).

### 7.1 Traceability
| AC | Tests |
|---|---|
| AC1 | `test_models.py::AnnouncementModelTests::*`, `test_admin.py::AnnouncementAdminTests::*`; `makemigrations --check` |
| AC2 | `test_models.py::AnnouncementModelTests::test_valid_combinations`, `test_invalid_combinations_full_clean`, `test_invalid_combination_db_constraint`, `test_lengths_are_constants` |
| AC3 | `test_views.py::StaffAnnouncementsViewTests::*`, `AnnouncementFormTests::*`, `test_services.py::CreateAnnouncementTests::*`, `ManagedBySelectorTests::*` |
| AC4 | `test_views.py::StaffUnpublishViewTests::*`, `test_services.py::UnpublishTests::*` |
| AC5 | `test_views.py::FeedViewTests::test_body_escaped_and_line_breaks_kept`, `StaffAnnouncementsViewTests::test_body_escaped_on_staff_page` |
| AC6 | `test_feed.py::DeadlinesTests::*`, `FeedWindowTests::*`, `test_views.py::FeedViewTests::test_empty_state`, `test_sections_order` |
| AC7 | `test_feed.py::PetitionSourcesTests::*`, `LessonChangeSourceTests::*`, `GradeSourcesTests::*`, `test_feed.py::AdminEventsTests::*` |
| AC8 | `test_feed.py::UnreadTests::*`, `test_services.py::MarkSeenTests::*`, `test_views.py::FeedViewTests::test_get_marks_read`, `test_head_not_allowed`, `test_post_not_allowed`, `test_no_store`, `NavTests::*` |
| AC9 | `test_feed.py::BeforeMidnightTests::*`, `AfterMidnightTests::*` |
| AC10 | `test_feed.py::StudentScopeTests::*`, access matrix tests (7.2) |
| AC11 | `test_views.py::QueryCountTests::*` |
| AC12 | `test_views.py::HomeSummaryTests::*` |
| AC13 | `test_demo.py::NotificationsSeedTests::*` |
| AC14 | `test_feed.py::SourceRegistryTests::*` |
| AC15 | `test_views.py::NavTests::*` |

### 7.2 Access matrix (every cell is a test in `notifications/tests/test_views.py`)

`notifications:feed` — class `FeedAccessTests`:
| Actor | Expected | Test |
|---|---|---|
| anonymous | 302 → `/login/?next=/notifications/` | `test_anonymous_redirects` |
| student, own data | 200, own items | `test_student_ok` |
| student, another student's data | no URL with IDs; other student's items absent | `StudentScopeTests` (7.3) |
| staff (own or other faculty — role check) | 403 | `test_staff_forbidden` |
| superuser | 403 | `test_superuser_forbidden` |
| student without profile | 403 | `test_student_without_profile_forbidden` |

`notifications:staff_announcements` — class `StaffAnnouncementsAccessTests`:
| Actor | Expected | Test |
|---|---|---|
| anonymous GET / POST | 302 to login; nothing created | `test_anonymous_get_redirects`, `test_anonymous_post_creates_nothing` |
| student GET / POST | 403; nothing created | `test_student_get_forbidden`, `test_student_post_forbidden` |
| staff own faculty | 200; lists FX faculty + GX1/GX2 group items | `test_staff_sees_own_faculty` |
| staff other faculty's items | not listed (FY items and university items absent) | `test_staff_does_not_see_other_faculty_or_university` |
| superuser | 403 | `test_superuser_forbidden` |

`notifications:staff_unpublish` — class `StaffUnpublishAccessTests`:
| Actor / object | Expected | Test |
|---|---|---|
| anonymous | 302 to login; unchanged | `test_anonymous` |
| student | 403; unchanged | `test_student_forbidden` |
| staff, own faculty item | 302 → list; unpublished | `test_staff_own_faculty_item` |
| staff, own group item | 302; unpublished | `test_staff_own_group_item` |
| staff, other faculty item | 404; unchanged | `test_staff_other_faculty_404` |
| staff, university item | 404; unchanged | `test_staff_university_404` |
| staff, unknown uuid | 404 | `test_unknown_uuid_404` |
| superuser | 403; unchanged | `test_superuser_forbidden` |
| staff GET | 405 | `test_get_not_allowed` |

`core:home` — class `HomeSummaryTests` (anonymous 302 is covered by `core/tests/test_views.py::HomeViewTests::test_home_requires_login`):
| Actor | Expected | Test |
|---|---|---|
| student with profile | 200; «Ближайшие дедлайны», ≤ 3 deadlines nearest first, ≤ 3 newest news, links to `/notifications/#…` | `test_student_summary`, `test_limits_to_three` |
| student without profile | 200; old text, no summary | `test_student_without_profile` |
| staff | 200; old text, no summary | `test_staff_no_summary` |
| superuser | 200; old text | `test_superuser_no_summary` |
| home does not mark read | state unchanged after GET `/` | `test_home_does_not_mark_read` |

CSRF — class `CsrfTests` (client with `enforce_csrf_checks=True`, logged-in staff, no token): `test_create_without_token_403`, `test_unpublish_without_token_403` (nothing changes).

### 7.3 Behaviour and edge cases (`notifications/tests/test_feed.py` unless stated)

`StudentScopeTests` (world from `make_world`):
- `test_university_item_visible_to_all_students`
- `test_faculty_item_only_for_that_faculty` (FX item: ax, cx see it; ay does not)
- `test_group_item_only_for_that_group` (GX1 item: ax, bx see it; cx, ay do not)
- `test_unpublished_hidden_everywhere` (not in feed, not in deadlines, not counted, not on home)
- `test_other_students_personal_events_hidden` (bx's petition status change, comment, mark, final result do not appear for ax)
- `test_other_group_lesson_change_hidden` (GX2 change not in ax's feed)
- `test_shared_lesson_change_visible_to_both_groups` (lesson with groups GX1 + GX2 → ax and cx)

`PetitionSourcesTests`:
- `test_staff_status_change_listed_with_link` (to `ready`: title contains «готова», url = `/requests/<uuid>/`)
- `test_rejection_comment_in_body`
- `test_own_submission_not_listed` (row with `actor = student`)
- `test_staff_comment_listed` (title «Комментарий деканата…», body = text, link)
- `test_status_change_via_service_listed` (call `petitions.services.change_status` as staff)

`LessonChangeSourceTests` (frozen 2026-11-11, Wednesday; use a Wednesday lesson unless stated):
- `test_cancelled_title_and_week_link` (url = `/schedule/week/2026-11-11/` for a change on 11.11)
- `test_moved_title_mentions_new_date_and_room`
- `test_room_changed_title`, `test_teacher_replaced_title`
- `test_horizon_last_day_included` (original 2026-11-25 = today + 14)
- `test_beyond_horizon_excluded` (Wednesday 2026-12-02; and a Thursday lesson on 2026-11-26 = today + 15)
- `test_past_original_with_future_new_date_included_links_new_week`
- `test_past_change_excluded` (original 2026-11-04, cancelled)
- `test_edited_change_is_new_again` (seen at T; edit via `save_lesson_change` under `mock.patch("django.utils.timezone.now", return_value=T + 1h)`; `student_context(user, now=T + 2h)` → item `is_new`, `unread_count == 1`)

`GradeSourcesTests`:
- `test_new_mark_listed_with_term_link` (url = `/grades/<term code>/`)
- `test_new_final_result_listed`, `test_retake_title_mentions_attempt`
- `test_mark_created_via_save_validated_uses_frozen_clock` (`created_at == frozen now`; guards D5)

`AdminEventsTests` (superuser client, admin add views; proves admin-made events appear):
- `test_admin_lesson_change_appears` (POST `admin:schedule_lessonchange_add`)
- `test_admin_mark_appears` (POST `admin:academics_currentmark_add`)

`FeedWindowTests`:
- `test_window_boundary` (event at `now - 30 days` excluded; at `now - 30 days + 1 min` included)
- `test_future_item_excluded` (published_at = now + 1 min)
- `test_cap_50` (55 news → 50 items; `badge_label` → «50+»; `unread_count == 55`)
- `test_newest_first_across_sources` (news, mark and comment with interleaved timestamps → exact order)
- `test_empty_feed`

`DeadlinesTests`:
- `test_nearest_first_and_labels` (deadlines today, +1, +2, +5 → order and labels «сегодня», «завтра», «через 2 дня», «через 5 дней»)
- `test_past_deadline_leaves_block_stays_in_feed` (feed item shows «срок прошёл»)
- `test_old_announcement_with_future_deadline_in_block` (published 40 days ago, deadline +3 → in block, not in feed)
- `test_limit` (12 deadlines → 10)

`BeforeMidnightTests` (`frozen_now = "2026-11-09 23:59:59"`) and `AfterMidnightTests` (`frozen_now = "2026-11-10 00:30:00"`, which is 2026-11-09 21:30 UTC):
- `test_deadline_label` (deadline 2026-11-10: «завтра» before / «сегодня» after)
- `test_deadline_today_leaves_block_after_midnight` (deadline 2026-11-09: in block before; absent after)
- `test_lesson_today_leaves_horizon_after_midnight` (Monday lesson cancelled on 2026-11-09: listed before, absent after)

`UnreadTests`:
- `test_no_state_everything_new` (count = number of items; all `is_new`)
- `test_only_items_after_seen_are_new` (seen = now − 1 h; items at now − 2 h and now − 30 min → count 1; only the second `is_new`)
- `test_unpublish_decrements_count`
- `test_badge_label` (0 → "", 7 → "7", 50 → "50", 51 → "50+")
- `test_badge_for_staff_and_anonymous_is_empty`

`SourceRegistryTests`:
- `test_default_registry_has_six_sources`
- `test_feed_and_counter_use_registry` (patch `notifications.feed.get_feed_sources` to return `(NewsSource(),)` → only news items, count only news)

`notifications/tests/test_services.py`: classes from 5.2–5.3 (`ManagedBySelectorTests`, `DeadlineErrorsTests`, `CreateAnnouncementTests`, `UnpublishTests`, `MarkSeenTests`).

`notifications/tests/test_dates.py`: `RuPluralTests`, `RelativeDayLabelTests` (5.1).

`notifications/tests/test_models.py::AnnouncementModelTests`:
- `test_valid_combinations` (3 valid combos pass `full_clean`)
- `test_invalid_combinations_full_clean` (university + faculty; faculty without faculty; faculty + group; group without group; group + faculty → `ValidationError` with the constraint message, `NON_FIELD_ERRORS`)
- `test_invalid_combination_db_constraint` (`objects.create` with faculty audience and no faculty → `IntegrityError` inside `transaction.atomic()`)
- `test_lengths_are_constants` (`max_length` of title/body equal the constants)
- `test_str_and_audience_label`

`notifications/tests/test_admin.py::AnnouncementAdminTests` (superuser):
- `test_add_university_announcement_sets_author`
- `test_invalid_combination_shows_error_not_500` (status 200, constraint message in content)
- `test_unpublish_in_admin_sets_fields`, `test_republish_in_admin_clears_fields`

`notifications/tests/test_views.py` (besides 7.2):
- `FeedViewTests`: `test_sections_order` (deadlines heading before feed heading), `test_empty_state`, `test_body_escaped_and_line_breaks_kept` (body `"<b>жирный</b>\nвторая строка"` → `&lt;b&gt;` and `<br>` present, `<b>жирный` absent), `test_new_marker` («Новое» on unread items only), `test_get_marks_read` (state = frozen now; second GET shows no «Новое»), `test_head_not_allowed` (405, no state row), `test_post_not_allowed` (405), `test_no_store` (`no-store` in `Cache-Control`)
- `StaffAnnouncementsViewTests`: `test_create_faculty_announcement` (302, message, row with author/faculty), `test_create_group_announcement`, `test_forged_group_form_error` (200, nothing created), `test_university_target_form_error`, `test_past_deadline_form_error`, `test_service_error_shown_as_form_error` (patch `notifications.views.create_announcement` to raise `ValidationError("x")` → 200 with «x»), `test_unpublished_shown_with_status_and_no_button`, `test_body_escaped_on_staff_page`, `test_student_sees_created_announcement` (create as staff, then student of that faculty sees it in the feed — the jury flow)
- `StaffUnpublishViewTests`: `test_messages` (first «снято с публикации», second «уже снято»), `test_second_post_keeps_unpublished_at`
- `NavTests`: `test_student_nav_with_count` («Уведомления (2)»), `test_student_nav_without_count` (no unread → «Уведомления» without brackets), `test_staff_nav_has_announcements`, `test_superuser_nav_has_neither`
- `QueryCountTests` (use `CaptureQueriesContext`):
  - `test_badge_exactly_three_queries` (fetch `user = User.objects.get(pk=…)` first, then `with self.assertNumQueries(3): badge_for_user(user)`)
  - `test_feed_queries_constant` (pre-create the state with `set_seen(user, now - 1 day)` before each measured GET so `mark_seen` is one UPDATE in both runs; 1 row per source vs 5 rows per source → equal counts; and ≤ 20)
  - `test_profile_page_counter_constant` (GET `accounts:profile` with 0 vs 10 unread items → equal counts)
  - `test_staff_list_queries_constant` (1 vs 6 announcements, faculty and group mixed → equal; ≤ 10)
  - `test_home_queries_constant` (1 vs 5 news → equal)

`notifications/tests/test_demo.py::NotificationsSeedTests` (`frozen_now = "2026-11-22 12:00"`, `call_command("seed_demo", stdout=StringIO())` with `DEMO_PASSWORD` patched as in `accounts/tests/test_seed_demo.py`):
- `test_creates_nine_announcements` (9 total, 2 unpublished, audiences: 2 university, 5 faculty, 2 group)
- `test_idempotent` (second run: still 9; output contains «Notifications ready: 0 announcements.»)
- `test_deadlines_in_jury_window` (published with `deadline >= today`: every deadline in 2026-11-23…2026-11-28; at least 4)
- `test_every_demo_student_has_unread_and_deadlines` (`badge_for_user` non-empty, `upcoming_deadlines` non-empty for student1–3)
- `test_staff_lists_include_unpublished` (staff1 and staff2 each manage ≥ 1 unpublished)
- `test_seeded_marks_recorded_on_their_date` (every seeded `CurrentMark`: `localtime(created_at).date() == date`, `created_at <= now`)
- `test_previous_term_results_not_in_feed` (no `final_result` items in student1's feed)
- `test_seeded_staff_comment_time_is_explicit` (p-2 comment `created_at == petition.created_at + 40 h`)

### 7.4 Settings branches
No setting differs between DEBUG modes for this task. `check --deploy` must stay clean (verification).

### 7.5 Regression
No bug fix in this task. The existing `core/tests/test_views.py::HomeViewTests` (student without profile) and `petitions/tests/test_views.py::NavigationTests` must keep passing unchanged.

---

## 8. Implementation order
1. `core/clock.py`; model changes in `academics` and `schedule`; `makemigrations academics schedule`; hand-write `academics/0003`. Run the full suite (must stay green).
2. App skeleton: `apps.py`, settings, `pyproject.toml`, `constants.py`, `models.py`, `makemigrations notifications`, `admin.py`; tests `test_models.py`, `test_admin.py`.
3. `dates.py`, `selectors.py`, `services.py` + `test_dates.py`, `test_services.py`.
4. `sources.py`, `feed.py` + `test_feed.py`.
5. Template tag, forms, views, URLs, templates, `base.html`, home, CSS + `test_views.py`.
6. Seeds (`notifications/demo.py`, `academics/demo.py`, `petitions/demo.py`, command) + `test_demo.py`.
7. README. `ruff format` on changed/new Python files only; section 9; `REPORT` to the Reviewer with the outputs. Do not commit.

## 9. Verification
```bash
source .venv/bin/activate
export DEBUG=true
TS=$(TZ=Europe/Moscow date +%Y%m%d-%H%M%S)
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test 2>&1 | tee "$TMPDIR/test-$TS.log"
python scripts/run_tests_at.py 2026-11-17T23:59:59 2>&1 | tee "$TMPDIR/test-$TS-at-2359.log"
python scripts/run_tests_at.py 2026-11-18T00:00:00 2>&1 | tee "$TMPDIR/test-$TS-at-0000.log"
python scripts/run_tests_at.py 2027-03-01T12:00:00 2>&1 | tee "$TMPDIR/test-$TS-at-2027.log"
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
ruff check . && ruff format --check .
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
# Seed twice + backfill on existing data (temporary DB and media only)
export DATABASE_URL="sqlite:///$TMPDIR/task007.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task007-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
rm -f "$TMPDIR/task007.sqlite3"
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
python manage.py migrate academics 0001 && python manage.py migrate
python manage.py shell -c "from django.utils import timezone as tz; from academics.models import CurrentMark as M; bad=[m.pk for m in M.objects.all() if tz.localtime(m.created_at).date()!=m.date]; print('backfill ok' if not bad else bad)"
git status --short
```
`REPORT`: output tails, test count (was 567), log file names, any failed run by test name and Moscow time, `git status`.

## 10. Feasibility check (2026-11-15 00:47 MSK on `8f7bc4f`)
1. Clean start — `git status --short` → only ` M plan.md` (Team lead file). OK.
2. Referenced objects — `StudentRequiredMixin`, `StaffRequiredMixin`, `get_profile_for_role` (`accounts/access.py`); `groups_visible_to` (`accounts/selectors.py:37`); `StudentProfile.group`, `StaffProfile.faculty`, `User.is_student`/`is_deanery_staff`/`Role`; `Faculty`, `StudyGroup.program`, `Room.__str__` («ауд. N»), `Teacher.short_name` (`university/models.py`); `PetitionStatusChange.created_at/actor/comment/to_status`, `PetitionComment.created_at/author/text`, `Petition.public_id` (`petitions/models.py`); `change_status`, `add_staff_comment` set `created_at` explicitly (`petitions/services.py:92,103,145`); `LessonChange` (`created_at` auto_now_add, no `updated_at`; `schedule/models.py:129`), `save_lesson_change` (`schedule/mutations.py`); `CurrentMark` (no `created_at`), `FinalResult.created_at` auto_now_add (`academics/models.py:199`); `save_validated`; URL names `petitions:detail` (`requests/<uuid>/`), `schedule:week_of` (`schedule/week/<isodate:day>/`), `academics:my_grades_term` (`grades/<slug:term_code>/`), `accounts:profile`, `core:home`; `base.html` nav branches; `core/views.py::HomeView`; seed functions `seed_academics_demo` (marks/results via `save_validated`, lines 185–226), `seed_petitions_demo` (comment without `created_at`, line ~200), `seed_demo` command; test helpers `make_faculty`, `make_group`, `make_student`, `make_staff`, `make_lesson`, `make_room`, `make_term`, `make_item`, `make_mark`, `make_result`, `make_type`, `make_petition`; `FrozenClockMixin`, `moscow()`. OK.
3. No collisions — no `notifications` package, no `core/clock.py`, no URL `notifications/` or `staff/announcements/`, no related names `announcements`/`notification_state` on `User`, `Faculty`, `StudyGroup`, no template library `notifications_tags`. Latest migrations: `academics/0001_initial`, `schedule/0003_mark_existing_demo_rows`, `university/0002_discipline_room_teacher`, `accounts/0002_loginthrottle`. OK.
4. Migrations — `makemigrations --check --dry-run` → «No changes detected». `auto_now` AddField and a callable default need no prompt (`django/db/migrations/autodetector.py:1136-1144`: `preserve_default` is true for `auto_now` and for fields with a default). Existing rows: backfill migration 0003 (4.4). OK.
5. Tools — Python 3.12 (`.venv`), Django 5.2.19, ruff 0.17.4, PyYAML. No new dependency. OK.
6. Framework — verified on the installed Django 5.2.19 with a temporary DB: `qs.union(*others, all=True).count()` across `PetitionStatusChange`, `PetitionComment`, `LessonChange` (M2M + OR filter) and `FinalResult` value lists runs as ONE query on SQLite (`SELECT COUNT(*) FROM (… UNION ALL …)`); ordering must be cleared on each part (`.order_by()`). `DateField` with `DateInput(format="%Y-%m-%d", attrs={"type": "date"})` accepts «2026-11-25» and «25.11.2026» under `LANGUAGE_CODE="ru"` (ISO is appended to `DATE_INPUT_FORMATS`) and renders `value="2026-11-25"`. `default=timezone.now` is NOT affected by `mock.patch("django.utils.timezone.now")` after import (returned the real time), while a call-time lookup is (returned the patched time) → D5. `select_for_update(of=…)` is ignored on SQLite (no `has_select_for_update`). `View.http_method_names` without `"head"` → HEAD 405. `never_cache`, `simple_tag(takes_context=True)` with `as`. OK.
7. Environment — no new env variables. OK.
8. Verification runnable — current tree, logs in `$TMPDIR/test-20261115-004724-t007-feas*.log`: `test` → `Ran 567 tests … OK`; `run_tests_at.py 2026-11-17T23:59:59` → 567 OK; `run_tests_at.py 2026-11-18T00:00:00` → 567 OK; no failed runs. `check` and `check --deploy` → no issues; ruff check → all passed; ruff format → 123 files formatted; YAML ok; `seed_demo` twice on a temporary DB → OK (second run: 0 new requests). OK.
9. Conflicts — none. The requirement "deadlines in 23–28.11" is met by offsets +1…+5 from the run day 22.11.
10. Assumptions / blockers — none.

## 11. Risks
- **Data leak between students**: every source filters by the student's own profile / group / faculty; scope tests per source (7.3). Staff scope through one selector.
- **Clock leaks in tests** (D5): mitigated by `core.clock.now`, explicit timestamps in services, and the 2026-11-11 test clock that fails fast.
- **Counter cost on every student page**: fixed 3 queries (asserted). Staff, superuser and anonymous pages: 0 extra queries (tag only in the student branch).
- **Race between event creation and page view**: an event whose `created_at` is taken just before a commit that finishes after the student opened the page can be counted as read. Accepted for the prototype (milliseconds window).
- **GET with a side effect** (D3): limited to the user's own read marker; SameSite=Lax + no-store; HEAD excluded.
- **PostgreSQL locking**: `select_for_update(of=("self",))` required because of outer joins in the staff filter; SQLite does not check this, so keep the `of` argument exactly.
- **Backfill migration** changes `created_at` of existing grades once (to the grade date 18:00 MSK); on the server DB it runs before any data exists.
