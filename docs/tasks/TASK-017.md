# TASK-017: password toggle; "Заявки" → "Документы"; "Справка о поступлении"; "Тип" hint by kind

Author: Planner. Assignee: UI coder. Status: ready for implementation.
Base: HEAD 16399ea (TASK-016 committed; clean tree except the Team lead's `plan.md`; do not touch it).

## 1. Goal

Four small user-requested changes (user decisions 20.11, `plan.md`).

### Acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | Login page: a show/hide password button next to the password field. Our own pixel eye icon (inline SVG of `<rect>`, `shape-rendering="crispEdges"`, `fill="currentColor"`), two states: open eye (password hidden) and crossed eye (password shown). Tap target ≥ 44 × 44 px. Visible focus (the project focus outline). `type="button"`, `aria-controls="id_password"`, `aria-pressed` true/false, Russian accessible name. Text/icon contrast WCAG AA (tokens only). |
| AC2 | The button is in the markup with `hidden`; only `static/js/password-toggle.js` (external, `defer`) shows it and switches the input type. Without JavaScript the button stays hidden and the form works as now. The CSP of TASK-016 allows it unchanged. On submit the field is switched back to `type="password"`. `autocomplete="username"` / `"current-password"`, field names, labels and error markup stay. |
| AC3 | No user-visible "заявка" in any form remains (templates, Python strings of the apps, JS): nav, home, page titles, buttons, messages, form errors, notifications, demo chat text, admin names. Where the kind is known: "справка" (feminine) / "заявление" (neuter) with correct agreement; where kinds are mixed: "документ"/"документы" (masculine). "Заявление/Заявления" as a kind stays. URLs, URL names, Python names, model and app labels stay. |
| AC4 | Status labels agree with the noun: on pages about one document — feminine for a certificate (Подана, Готова, Выдана, Отклонена), neuter for an application (Подано, Готово, Выдано, Отклонено); in mixed lists of one kind per row the row's kind; in mixed filters/admin — masculine ("документ": Подан, Готов, Выдан, Отклонён). "В работе" is the same for all. Staff action buttons agree too ("Отметить готовой/выданной" vs "Отметить готовым/выданным"). |
| AC5 | "Справка в военкомат" becomes "Справка о поступлении" (certificate, comment optional, hint "Можно указать, куда нужна справка.", 3 working days, description "Подтверждает зачисление в университет.") by renaming the row in place (data migration 0005). After the migration on a database seeded before, there is exactly one of the two names; a fresh database after `seed_demo` has only the new type; `seed_demo` twice changes nothing. |
| AC6 | The "Тип" hint: certificate kinds «Справка о периоде обучения» (as now), application kinds «Заявление на индивидуальный учебный план». |
| AC7 | Tests (section 7) and all verification commands pass; visual check (section 8) done and reported with screenshots. |

## 2. Out of scope

- URLs (`/requests/…`, `/staff/requests/…`), URL names, Python/model/app identifiers, the `RequestKind` labels ("Справка", "Заявление"), type names other than the renamed one.
- The empty required comment still shows Django's "Обязательное поле." (TASK-014-FIX decision).
- Existing chat demo rows keep the old text (`seed_demo` never updates rows; accepted by the Team lead).
- `README.md`, `CHANGELOG.md`, `plan.md`, `docs/`. The admin login page (no toggle there).

## 3. Design decisions

- **D1. One wording module.** `petitions/wording.py` holds every kind-dependent text (status labels, action
  labels, page texts, notification titles, plural helper). Templates use two filters from
  `petitions/templatetags/petition_wording.py`: `status_for` and `kind_text`. Every text is in one place and is
  tested in one test module.
- **D2. Status labels by kind (beyond the request map, same rule "adapt grammar").** Today the labels
  "Подана/Готова/Выдана/Отклонена" agree with "заявка". After the rename they would be wrong for applications
  ("Заявление … Готова") and in mixed places ("Документы: Подана"). So: `PetitionStatus` labels become masculine
  (they appear only where kinds are mixed: staff status filter, admin, the "Нельзя перевести документ из «…»"
  error); every place about one document uses `status_label(status, kind)`. The date line "Подана: …" on both
  detail pages becomes the kind's "submitted" label ("Подана:" / "Подано:"). The Team lead is informed.
- **D3. Rename in place, not deactivate** (AC5). A deactivated old type would stay in the staff type filter
  (`RequestType.objects.all()`) next to the new one, and `seed_demo` upserts by name, so a renamed row is found
  by its new name and nothing is duplicated. Existing petitions of that type (trial database only; the final
  database is created on 22.11 after this task) then show the new name — acceptable for a demo. If a row with the
  new name already exists (only if created by hand), the old row is deactivated instead. The migration is
  reversible.
- **D4. Toggle accessible name stays "Показать пароль"; the state is `aria-pressed`.** The request lists both
  "Показать пароль" / "Скрыть пароль" and `aria-pressed`. A toggle button must not change its name when the
  state changes (WAI-ARIA APG, Button pattern): screen readers would announce "Скрыть пароль, нажата" — a double
  negation. With a fixed name: "Показать пароль, кнопка-переключатель, нажата" = the password is shown. Sighted
  users see the state by the icon (open vs crossed eye). The Team lead is informed.
- **D5. The toggle is a panel button**, not the orange primary: `.form button` styles every button in the form,
  so `.form .password-toggle` (higher specificity) restores the panel look (`--color-panel`, frame). It sits in a
  flex row right of the input (`.password-field`), so the input keeps its full height and the toggle is a 44 px
  square-ish target. `.password-toggle[hidden] { display: none; }` is required because `display: inline-flex`
  would otherwise override the `hidden` attribute.
- **D6. Icons:** `templates/includes/icon_eye.html` and `icon_eye_off.html`, viewBox 12 × 8, `<rect>` only,
  like `icon_bell.html`. The reference drawings below passed the tests and work in Chrome; you may redraw them
  for readability (keep: rects only, crispEdges, currentColor, aria-hidden, focusable="false", 12 × 8 grid or a
  multiple, rendered at least 24 × 16 CSS px).
- **D7. "У вас уже N документа этого вида в работе."** N is `MAX_OPEN_PER_TYPE` (3); the noun comes from
  `plural_ru(n, ("документ", "документа", "документов"))`, so a future limit stays correct.
- **D8. The comment-required message by kind** is used by `submit_petition` and `PetitionForm.clean_comment`.
  In the form an empty comment is caught first by Django's required check, so the message is visible through the
  service path (tests use the service).
- **D9. Notifications:** the type name is the subject ("«Справка об обучении» взята в работу"); tag
  "Документы"; the comment title "Комментарий деканата: «{name}»". `PetitionStatusSource.related` already
  selects `petition__request_type`, so no extra queries.
- **D10. Queries:** templates read `petition.request_type.kind`; every view that lists or shows petitions
  already loads `request_type` (`select_related` in `petitions_visible_to`/views; the existing `QueryCountTests`
  pass unchanged). History rows use the parent `petition`, not `change.petition`.

## 4. Files and functions

Create: `petitions/wording.py`, `petitions/templatetags/__init__.py` (empty),
`petitions/templatetags/petition_wording.py`, `petitions/migrations/0004_documents_wording.py` (generate:
`python manage.py makemigrations petitions --name documents_wording` after F3), 
`petitions/migrations/0005_admission_certificate.py` (by hand, F5), `static/js/password-toggle.js`,
`templates/includes/icon_eye.html`, `templates/includes/icon_eye_off.html`, tests (section 7).
Change: the files in F2–F12. The code is the exact code that passed all checks in section 5 (diffs against HEAD
16399ea; edit files by hand, no git commands). Keep comments as written.

### F1. `petitions/wording.py` (new)

````python
"""Russian wording that agrees with the kind of a document (TASK-017).

A certificate is "справка" (feminine), an application is "заявление" (neuter).
Where kinds are mixed the generic noun is "документ" (masculine): the plain
``PetitionStatus`` labels.
"""

from petitions.models import PetitionStatus, RequestKind

CERTIFICATE = RequestKind.CERTIFICATE.value
APPLICATION = RequestKind.APPLICATION.value

STATUS_LABELS = {
    CERTIFICATE: {
        "submitted": "Подана",
        "in_progress": "В работе",
        "ready": "Готова",
        "issued": "Выдана",
        "rejected": "Отклонена",
    },
    APPLICATION: {
        "submitted": "Подано",
        "in_progress": "В работе",
        "ready": "Готово",
        "issued": "Выдано",
        "rejected": "Отклонено",
    },
}

ACTION_LABELS = {
    CERTIFICATE: {
        "in_progress": "Взять в работу",
        "ready": "Отметить готовой",
        "issued": "Отметить выданной",
        "rejected": "Отклонить",
    },
    APPLICATION: {
        "in_progress": "Взять в работу",
        "ready": "Отметить готовым",
        "issued": "Отметить выданным",
        "rejected": "Отклонить",
    },
}

TEXTS = {
    CERTIFICATE: {
        "noun": "Справка",
        "submit": "Заказать справку",
        "submitted_title": "Справка заказана",
        "back_link": "К справке",
        "comment_required": "Для этой справки комментарий обязателен.",
        "subject_example": "Справка о периоде обучения",
    },
    APPLICATION: {
        "noun": "Заявление",
        "submit": "Подать заявление",
        "submitted_title": "Заявление подано",
        "back_link": "К заявлению",
        "comment_required": "Для этого заявления комментарий обязателен.",
        "subject_example": "Заявление на индивидуальный учебный план",
    },
}

NOTIFICATION_TITLES = {
    CERTIFICATE: {
        "in_progress": "«{name}» взята в работу",
        "ready": "«{name}» готова — заберите её в деканате",
        "issued": "«{name}» выдана",
        "rejected": "«{name}» отклонена",
    },
    APPLICATION: {
        "in_progress": "«{name}» взято в работу",
        "ready": "«{name}» готово — заберите его в деканате",
        "issued": "«{name}» выдано",
        "rejected": "«{name}» отклонено",
    },
}

DOCUMENT_FORMS = ("документ", "документа", "документов")


def _kind(kind: str) -> str:
    return kind if kind in TEXTS else CERTIFICATE


def status_label(status: str, kind: str) -> str:
    labels = STATUS_LABELS.get(kind)
    if labels is not None and status in labels:
        return labels[status]
    return dict(PetitionStatus.choices).get(status, status)


def action_label(status: str, kind: str) -> str:
    return ACTION_LABELS[_kind(kind)][status]


def text(kind: str, key: str) -> str:
    return TEXTS[_kind(kind)][key]


def notification_title(status: str, kind: str, name: str) -> str:
    template = NOTIFICATION_TITLES[_kind(kind)].get(status)
    if template is None:
        return f"«{name}»: статус «{status_label(status, kind)}»"
    return template.format(name=name)


def plural_ru(n: int, forms: tuple[str, str, str]) -> str:
    """Russian plural: (1 документ, 2 документа, 5 документов)."""
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]
````

`petitions/templatetags/petition_wording.py` (new):

````python
"""Template filters for kind-aware wording (TASK-017)."""

from django import template

from petitions import wording

register = template.Library()


@register.filter
def status_for(status: str, kind: str) -> str:
    """{{ petition.status|status_for:petition.request_type.kind }}"""
    return wording.status_label(status, kind)


@register.filter
def kind_text(kind: str, key: str) -> str:
    """{{ request_type.kind|kind_text:"submit" }}"""
    return wording.text(kind, key)
````

### F2. Templates: nav, home, petitions pages

````diff
--- a/templates/includes/site_nav_items.html
+++ b/templates/includes/site_nav_items.html
@@ -4,12 +4,12 @@
   {% url 'schedule:today' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Расписание</a></li>
   {% url 'campusmap:map' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Карта</a></li>
   {% url 'academics:my_grades' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Успеваемость</a></li>
-  {% url 'petitions:my_list' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Заявки</a></li>
+  {% url 'petitions:my_list' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Документы</a></li>
   {% url 'chat:student' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Чат{% if chat_badge %} ({{ chat_badge }}){% endif %}</a></li>
   {% elif user.is_deanery_staff %}
   {% url 'schedule:staff_groups' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Расписание</a></li>
   {% url 'campusmap:map' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Карта</a></li>
-  {% url 'petitions:staff_queue' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Заявки</a></li>
+  {% url 'petitions:staff_queue' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Документы</a></li>
   {% url 'chat:staff_list' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Чаты</a></li>
   {% url 'notifications:staff_announcements' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Объявления</a></li>
   {% endif %}
````

````diff
--- a/core/templates/core/home.html
+++ b/core/templates/core/home.html
@@ -27,7 +27,7 @@
 {% elif user.is_deanery_staff %}
   <h1>Деканат</h1>
   <div class="home-actions home-actions--three">
-    <a class="btn" href="{% url 'petitions:staff_queue' %}">Заявки</a>
+    <a class="btn" href="{% url 'petitions:staff_queue' %}">Документы</a>
     <a class="btn" href="{% url 'chat:staff_list' %}">Чаты</a>
     <a class="btn" href="{% url 'notifications:staff_announcements' %}">Объявления</a>
   </div>
````

````diff
--- a/petitions/templates/petitions/catalog.html
+++ b/petitions/templates/petitions/catalog.html
@@ -1,6 +1,6 @@
 {% extends "base.html" %}
 {% block content %}
-  <h1>Подать заявку</h1>
+  <h1>Оформить документ</h1>
   <h2>Справки</h2>
   {% for type in certificates %}
     <div class="catalog-item">
````

````diff
--- a/petitions/templates/petitions/my_list.html
+++ b/petitions/templates/petitions/my_list.html
@@ -1,17 +1,18 @@
 {% extends "base.html" %}
+{% load petition_wording %}
 {% block content %}
-  <h1>Мои заявки</h1>
-  <p class="page-actions"><a href="{% url 'petitions:catalog' %}">Подать заявку</a></p>
+  <h1>Мои документы</h1>
+  <p class="page-actions"><a href="{% url 'petitions:catalog' %}">Оформить документ</a></p>
   {% if petitions %}
     <ul class="petition-list">
       {% for petition in petitions %}
         <li class="petition">
           <a class="petition-title" href="{% url 'petitions:detail' petition.public_id %}">{{ petition.display_name }}</a>
-          <p class="petition-meta"><span class="meta-item">№ {{ petition.short_id }}&nbsp;·</span> <span class="meta-item">{{ petition.created_at|date:"j E Y" }}&nbsp;·</span> <span class="meta-item"><span class="status status--{{ petition.status }}">{{ petition.get_status_display }}</span>&nbsp;·</span> <span class="meta-item">готовность: {{ petition.expected_ready_date|date:"j E Y" }}</span></p>
+          <p class="petition-meta"><span class="meta-item">№ {{ petition.short_id }}&nbsp;·</span> <span class="meta-item">{{ petition.created_at|date:"j E Y" }}&nbsp;·</span> <span class="meta-item"><span class="status status--{{ petition.status }}">{{ petition.status|status_for:petition.request_type.kind }}</span>&nbsp;·</span> <span class="meta-item">готовность: {{ petition.expected_ready_date|date:"j E Y" }}</span></p>
         </li>
       {% endfor %}
     </ul>
   {% else %}
-    <p>Заявок пока нет.</p>
+    <p>Документов пока нет.</p>
   {% endif %}
 {% endblock %}
````

````diff
--- a/petitions/templates/petitions/form.html
+++ b/petitions/templates/petitions/form.html
@@ -1,4 +1,5 @@
 {% extends "base.html" %}
+{% load petition_wording %}
 {% block content %}
   <h1>{{ request_type.name }}</h1>
   {% if request_type.description %}<p>{{ request_type.description }}</p>{% endif %}
@@ -6,6 +7,6 @@
     {% csrf_token %}
     {{ form.non_field_errors }}
     {{ form.as_p }}
-    <button type="submit">Отправить заявку</button>
+    <button type="submit">{{ request_type.kind|kind_text:"submit" }}</button>
   </form>
 {% endblock %}
````

````diff
--- a/petitions/templates/petitions/submitted.html
+++ b/petitions/templates/petitions/submitted.html
@@ -1,9 +1,10 @@
 {% extends "base.html" %}
+{% load petition_wording %}
 {% block content %}
-  <h1>Заявка подана</h1>
+  <h1>{{ petition.request_type.kind|kind_text:"submitted_title" }}</h1>
   <p>{{ petition.display_name }}</p>
   <p>№ {{ petition.short_id }}</p>
   <p>Ожидаемая дата готовности: {{ petition.expected_ready_date|date:"j E Y" }}</p>
-  <p><a href="{% url 'petitions:detail' petition.public_id %}">К заявке</a></p>
-  <p><a href="{% url 'petitions:my_list' %}">Мои заявки</a></p>
+  <p><a href="{% url 'petitions:detail' petition.public_id %}">{{ petition.request_type.kind|kind_text:"back_link" }}</a></p>
+  <p><a href="{% url 'petitions:my_list' %}">Мои документы</a></p>
 {% endblock %}
````

````diff
--- a/petitions/templates/petitions/detail.html
+++ b/petitions/templates/petitions/detail.html
@@ -1,9 +1,10 @@
 {% extends "base.html" %}
+{% load petition_wording %}
 {% block content %}
   <h1>{{ petition.display_name }}</h1>
-  <p class="status status--{{ petition.status }}">{{ petition.get_status_display }}</p>
+  <p class="status status--{{ petition.status }}">{{ petition.status|status_for:petition.request_type.kind }}</p>
   <p>№ {{ petition.short_id }}</p>
-  <p>Подана: {{ petition.created_at|date:"j E Y H:i" }}</p>
+  <p>{{ "submitted"|status_for:petition.request_type.kind }}: {{ petition.created_at|date:"j E Y H:i" }}</p>
   <p>Ожидаемая дата готовности: {{ petition.expected_ready_date|date:"j E Y" }}</p>
   {% if petition.comment %}<p>{{ petition.comment }}</p>{% endif %}
   {% include "petitions/includes/attachments.html" %}
````

````diff
--- a/petitions/templates/petitions/staff_detail.html
+++ b/petitions/templates/petitions/staff_detail.html
@@ -1,14 +1,15 @@
 {% extends "base.html" %}
+{% load petition_wording %}
 {% block content %}
-  <h1>Заявка № {{ petition.short_id }}</h1>
+  <h1>{{ petition.request_type.kind|kind_text:"noun" }} № {{ petition.short_id }}</h1>
   <h2>Студент</h2>
   <p>{{ petition.student.full_name }}</p>
   <p>{{ petition.student.group.name }}</p>
   <p>№ зачётной книжки: {{ petition.student.record_number }}</p>
-  <h2>Заявка</h2>
+  <h2>Документ</h2>
   <p>{{ petition.display_name }}</p>
-  <p class="status status--{{ petition.status }}">{{ petition.get_status_display }}</p>
-  <p>Подана: {{ petition.created_at|date:"j E Y H:i" }}</p>
+  <p class="status status--{{ petition.status }}">{{ petition.status|status_for:petition.request_type.kind }}</p>
+  <p>{{ "submitted"|status_for:petition.request_type.kind }}: {{ petition.created_at|date:"j E Y H:i" }}</p>
   <p>Ожидаемая дата готовности: {{ petition.expected_ready_date|date:"j E Y" }}</p>
   {% if petition.comment %}<p>{{ petition.comment }}</p>{% endif %}
   {% include "petitions/includes/attachments.html" %}
````

````diff
--- a/petitions/templates/petitions/staff_queue.html
+++ b/petitions/templates/petitions/staff_queue.html
@@ -1,6 +1,7 @@
 {% extends "base.html" %}
+{% load petition_wording %}
 {% block content %}
-  <h1>Заявки</h1>
+  <h1>Документы</h1>
   <form method="get" class="form">
     <p>
       <label for="status">Статус</label>
@@ -11,7 +12,7 @@
       </select>
     </p>
     <p>
-      <label for="type">Вид заявки</label>
+      <label for="type">Вид документа</label>
       <select name="type" id="type">
         <option value="">Все</option>
         {% for t in types %}
@@ -27,11 +28,11 @@
         <li class="petition">
           <a class="petition-title" href="{% url 'petitions:staff_detail' petition.public_id %}">{{ petition.student.full_name }}</a>
           <p class="petition-subject">{{ petition.display_name }}</p>
-          <p class="petition-meta"><span class="meta-item">{{ petition.student.group.name }}&nbsp;·</span> <span class="meta-item">{{ petition.created_at|date:"j E Y" }}&nbsp;·</span> <span class="meta-item"><span class="status status--{{ petition.status }}">{{ petition.get_status_display }}</span>&nbsp;·</span> <span class="meta-item">файлов: {{ petition.attachment_count }}</span></p>
+          <p class="petition-meta"><span class="meta-item">{{ petition.student.group.name }}&nbsp;·</span> <span class="meta-item">{{ petition.created_at|date:"j E Y" }}&nbsp;·</span> <span class="meta-item"><span class="status status--{{ petition.status }}">{{ petition.status|status_for:petition.request_type.kind }}</span>&nbsp;·</span> <span class="meta-item">файлов: {{ petition.attachment_count }}</span></p>
         </li>
       {% endfor %}
     </ul>
   {% else %}
-    <p>Заявок нет.</p>
+    <p>Документов нет.</p>
   {% endif %}
 {% endblock %}
````

````diff
--- a/petitions/templates/petitions/includes/history.html
+++ b/petitions/templates/petitions/includes/history.html
@@ -1,7 +1,7 @@
-{% if petition.history.all %}
+{% load petition_wording %}{% if petition.history.all %}
   <ol>
     {% for change in petition.history.all %}
-      <li>{{ change.created_at|date:"j E Y H:i" }}&nbsp;· {% if change.from_status %}{{ change.get_from_status_display }} → {% endif %}{{ change.get_to_status_display }}&nbsp;· {% if change.actor.role == "staff" %}{{ change.actor.staff_profile.full_name }}{% elif change.actor.role == "student" %}Студент{% else %}Администратор{% endif %}{% if change.comment %}<br>{{ change.comment }}{% endif %}</li>
+      <li>{{ change.created_at|date:"j E Y H:i" }}&nbsp;· {% if change.from_status %}{{ change.from_status|status_for:petition.request_type.kind }} → {% endif %}{{ change.to_status|status_for:petition.request_type.kind }}&nbsp;· {% if change.actor.role == "staff" %}{{ change.actor.staff_profile.full_name }}{% elif change.actor.role == "student" %}Студент{% else %}Администратор{% endif %}{% if change.comment %}<br>{{ change.comment }}{% endif %}</li>
     {% endfor %}
   </ol>
 {% else %}
````

### F3. `petitions/models.py`, `petitions/apps.py` (labels only), then generate migration 0004

````diff
--- a/petitions/models.py
+++ b/petitions/models.py
@@ -22,11 +22,13 @@
 
 
 class PetitionStatus(models.TextChoices):
-    SUBMITTED = "submitted", "Подана"
+    # Generic labels agree with "документ" (mixed kinds: filters, admin). Pages about one
+    # document use petitions.wording.status_label() (TASK-017).
+    SUBMITTED = "submitted", "Подан"
     IN_PROGRESS = "in_progress", "В работе"
-    READY = "ready", "Готова"
-    ISSUED = "issued", "Выдана"
-    REJECTED = "rejected", "Отклонена"
+    READY = "ready", "Готов"
+    ISSUED = "issued", "Выдан"
+    REJECTED = "rejected", "Отклонён"
 
 
 STATUS_VALUES = [s.value for s in PetitionStatus]
@@ -44,7 +46,7 @@
         "подсказка к комментарию", max_length=255, blank=True, default=""
     )
     subject_required = models.BooleanField("нужно поле «Тип»", default=False)
-    is_active = models.BooleanField("доступна для подачи", default=True)
+    is_active = models.BooleanField("доступен для подачи", default=True)
 
     class Meta:
         ordering = ["kind", "name"]
@@ -58,8 +60,8 @@
                 name="petitions_type_subject_needs_comment",
             ),
         ]
-        verbose_name = "вид заявки"
-        verbose_name_plural = "виды заявок"
+        verbose_name = "вид документа"
+        verbose_name_plural = "виды документов"
 
     def __str__(self) -> str:
         return self.name
@@ -87,14 +89,17 @@
         verbose_name="студент",
     )
     request_type = models.ForeignKey(
-        RequestType, on_delete=models.PROTECT, related_name="petitions", verbose_name="вид заявки"
+        RequestType,
+        on_delete=models.PROTECT,
+        related_name="petitions",
+        verbose_name="вид документа",
     )
     subject = models.CharField("тип", max_length=SUBJECT_MAX_LENGTH, blank=True, default="")
     comment = models.TextField("комментарий", blank=True, default="", max_length=MAX_COMMENT_LENGTH)
     status = models.CharField(
         "статус", max_length=16, choices=PetitionStatus.choices, default=PetitionStatus.SUBMITTED
     )
-    created_at = models.DateTimeField("подана", default=now)
+    created_at = models.DateTimeField("дата подачи", default=now)
     status_changed_at = models.DateTimeField("статус изменён", default=now)
     expected_ready_date = models.DateField("ожидаемая дата готовности")
     seed_key = models.SlugField(max_length=40, blank=True, default="", editable=False)
@@ -114,8 +119,8 @@
                 name="petitions_unique_seed_key",
             ),
         ]
-        verbose_name = "заявка"
-        verbose_name_plural = "заявки"
+        verbose_name = "документ"
+        verbose_name_plural = "документы"
 
     def __str__(self) -> str:
         return f"{self.request_type} — {self.student} ({self.get_status_display()})"
@@ -134,7 +139,7 @@
 class PetitionAttachment(models.Model):
     public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
     petition = models.ForeignKey(
-        Petition, on_delete=models.CASCADE, related_name="attachments", verbose_name="заявка"
+        Petition, on_delete=models.CASCADE, related_name="attachments", verbose_name="документ"
     )
     file = models.FileField(
         upload_to=attachment_upload_to, storage=get_private_storage, max_length=100, unique=True
@@ -145,8 +150,8 @@
 
     class Meta:
         ordering = ["uploaded_at", "pk"]
-        verbose_name = "приложение к заявке"
-        verbose_name_plural = "приложения к заявкам"
+        verbose_name = "файл к документу"
+        verbose_name_plural = "файлы к документам"
 
     def __str__(self) -> str:
         return self.original_name
@@ -154,7 +159,7 @@
 
 class PetitionStatusChange(models.Model):
     petition = models.ForeignKey(
-        Petition, on_delete=models.CASCADE, related_name="history", verbose_name="заявка"
+        Petition, on_delete=models.CASCADE, related_name="history", verbose_name="документ"
     )
     from_status = models.CharField(
         max_length=16, choices=PetitionStatus.choices, blank=True, default=""
@@ -181,7 +186,7 @@
 
 class PetitionComment(models.Model):
     petition = models.ForeignKey(
-        Petition, on_delete=models.CASCADE, related_name="staff_comments", verbose_name="заявка"
+        Petition, on_delete=models.CASCADE, related_name="staff_comments", verbose_name="документ"
     )
     author = models.ForeignKey(
         settings.AUTH_USER_MODEL,
````

````diff
--- a/petitions/apps.py
+++ b/petitions/apps.py
@@ -4,4 +4,4 @@
 class PetitionsConfig(AppConfig):
     default_auto_field = "django.db.models.BigAutoField"
     name = "petitions"
-    verbose_name = "Заявки"
+    verbose_name = "Документы"
````

The generated `0004_documents_wording.py` must contain only `AlterModelOptions` / `AlterField` operations
(verbose names and choices; 12 operations); check with `sqlmigrate petitions 0004` that SQLite rebuilds only
tables (no data change) — choices and verbose names do not change the PostgreSQL schema.

### F4. `petitions/services.py`, `petitions/forms.py`, `petitions/views.py`, `petitions/workflow.py`

````diff
--- a/petitions/services.py
+++ b/petitions/services.py
@@ -10,6 +10,7 @@
 from accounts.models import StudentProfile, User
 from core import clock
 from core.storage import get_private_storage
+from petitions import wording
 from petitions.files import store_attachment, validate_attachments
 from petitions.models import (
     MAX_COMMENT_LENGTH,
@@ -25,7 +26,7 @@
 
 
 class StaleStatusError(ValidationError):
-    default_message = "Заявка уже изменена, обновите страницу."
+    default_message = "Документ уже изменён, обновите страницу."
 
 
 def _status_label(status: str) -> str:
@@ -63,11 +64,11 @@
     subject = " ".join((subject or "").split()) if request_type.subject_required else ""
     errors: list[str] = []
     if not request_type.is_active:
-        errors.append("Этот вид заявки сейчас недоступен.")
+        errors.append("Этот вид документа сейчас недоступен.")
     if len(comment) > MAX_COMMENT_LENGTH:
         errors.append("Комментарий слишком длинный.")
     if request_type.comment_required and not comment:
-        errors.append("Для этой заявки комментарий обязателен.")
+        errors.append(wording.text(request_type.kind, "comment_required"))
     if request_type.subject_required and not subject:
         errors.append("Укажите, что именно нужно.")
     if len(subject) > SUBJECT_MAX_LENGTH:
@@ -88,8 +89,9 @@
             ).count()
             if open_count >= MAX_OPEN_PER_TYPE:
                 raise ValidationError(
-                    f"У вас уже {MAX_OPEN_PER_TYPE} открытые заявки этого вида. "
-                    "Дождитесь их выполнения."
+                    f"У вас уже {MAX_OPEN_PER_TYPE} "
+                    f"{wording.plural_ru(MAX_OPEN_PER_TYPE, wording.DOCUMENT_FORMS)} "
+                    "этого вида в работе. Дождитесь их выполнения."
                 )
             now = clock.now()
             petition = Petition.objects.create(
@@ -140,7 +142,7 @@
             raise StaleStatusError(StaleStatusError.default_message)
         if not can_transition(locked.status, new_status):
             raise ValidationError(
-                f"Нельзя перевести заявку из «{_status_label(locked.status)}» "
+                f"Нельзя перевести документ из «{_status_label(locked.status)}» "
                 f"в «{_status_label(new_status)}»."
             )
         if new_status in COMMENT_REQUIRED_FOR and not comment:
````

````diff
--- a/petitions/forms.py
+++ b/petitions/forms.py
@@ -3,6 +3,7 @@
 from django import forms
 from django.utils.html import escape
 
+from petitions import wording
 from petitions.files import validate_attachments
 from petitions.models import MAX_COMMENT_LENGTH, SUBJECT_MAX_LENGTH, PetitionStatus, RequestType
 
@@ -46,7 +47,10 @@
         self.fields["comment"].required = request_type.comment_required
         # Django renders help_text without escaping; the hint is admin-entered text.
         self.fields["comment"].help_text = escape(request_type.comment_hint)
-        if not request_type.subject_required:
+        if request_type.subject_required:
+            example = wording.text(request_type.kind, "subject_example")
+            self.fields["subject"].help_text = f"Что именно нужно, например: «{example}»."
+        else:
             del self.fields["subject"]
 
     def clean_subject(self):
@@ -58,7 +62,7 @@
     def clean_comment(self):
         comment = (self.cleaned_data.get("comment") or "").strip()
         if self.request_type.comment_required and not comment:
-            raise forms.ValidationError("Для этой заявки комментарий обязателен.")
+            raise forms.ValidationError(wording.text(self.request_type.kind, "comment_required"))
         return comment
 
     def clean_files(self):
````

````diff
--- a/petitions/views.py
+++ b/petitions/views.py
@@ -25,7 +25,8 @@
 )
 from petitions.selectors import attachments_visible_to, petitions_visible_to
 from petitions.services import add_staff_comment, change_status, submit_petition
-from petitions.workflow import ACTION_LABELS, OPEN_STATUSES, allowed_transitions
+from petitions.wording import action_label, status_label
+from petitions.workflow import OPEN_STATUSES, allowed_transitions
 
 logger = logging.getLogger(__name__)
 
@@ -176,7 +177,8 @@
         context = super().get_context_data(**kwargs)
         petition = self.object
         context["actions"] = [
-            (status, ACTION_LABELS[status]) for status in allowed_transitions(petition.status)
+            (status, action_label(status, petition.request_type.kind))
+            for status in allowed_transitions(petition.status)
         ]
         context["transition_form"] = TransitionForm(initial={"expected_status": petition.status})
         context["comment_form"] = StaffCommentForm()
@@ -209,7 +211,8 @@
         except ValidationError as exc:
             messages.error(request, " ".join(exc.messages))
             return redirect("petitions:staff_detail", public_id=petition.public_id)
-        messages.success(request, f"Статус изменён: {dict(PetitionStatus.choices)[new.status]}.")
+        label = status_label(new.status, new.request_type.kind)
+        messages.success(request, f"Статус изменён: {label}.")
         return redirect("petitions:staff_detail", public_id=petition.public_id)
 
 
````

`ACTION_LABELS` moves from `workflow.py` to `wording.py` (per kind):

````diff
--- a/petitions/workflow.py
+++ b/petitions/workflow.py
@@ -18,12 +18,6 @@
 
 OPEN_STATUSES = frozenset({SUBMITTED, IN_PROGRESS})
 COMMENT_REQUIRED_FOR = frozenset({REJECTED})
-ACTION_LABELS = {
-    IN_PROGRESS: "Взять в работу",
-    READY: "Отметить готовой",
-    ISSUED: "Отметить выданной",
-    REJECTED: "Отклонить",
-}
 
 
 def allowed_transitions(status: str) -> tuple[str, ...]:
````

### F5. `petitions/migrations/0005_admission_certificate.py` (new, by hand) and `petitions/demo.py`

````python
"""TASK-017: "Справка в военкомат" becomes "Справка о поступлении" (rename in place)."""

from django.db import migrations

OLD = {
    "name": "Справка в военкомат",
    "comment_required": True,
    "comment_hint": "Укажите военкомат.",
    "description": "Справка для военного комиссариата.",
}
NEW = {
    "name": "Справка о поступлении",
    "comment_required": False,
    "comment_hint": "Можно указать, куда нужна справка.",
    "description": "Подтверждает зачисление в университет.",
}


def _rename(apps, source: dict, target: dict) -> None:
    RequestType = apps.get_model("petitions", "RequestType")
    row = RequestType.objects.filter(name=source["name"]).first()
    if row is None:
        return
    if RequestType.objects.filter(name=target["name"]).exists():
        # The target name is taken (created by hand): hide the source type instead.
        row.is_active = False
        row.save(update_fields=["is_active"])
        return
    for field, value in target.items():
        setattr(row, field, value)
    row.kind = "certificate"
    row.processing_days = 3
    row.subject_required = False
    row.save()


def forwards(apps, schema_editor):
    _rename(apps, OLD, NEW)


def backwards(apps, schema_editor):
    _rename(apps, NEW, OLD)


class Migration(migrations.Migration):
    dependencies = [("petitions", "0004_documents_wording")]

    operations = [migrations.RunPython(forwards, backwards)]
````

````diff
--- a/petitions/demo.py
+++ b/petitions/demo.py
@@ -68,12 +68,12 @@
         False,
     ),
     (
-        "Справка в военкомат",
+        "Справка о поступлении",
         "certificate",
         3,
-        True,
-        "Укажите военкомат.",
-        "Справка для военного комиссариата.",
+        False,
+        "Можно указать, куда нужна справка.",
+        "Подтверждает зачисление в университет.",
         False,
     ),
     (
````

### F6. `notifications/sources.py`

````diff
--- a/notifications/sources.py
+++ b/notifications/sources.py
@@ -19,6 +19,7 @@
 from chat.constants import FEED_PREVIEW_CHARS
 from chat.models import AuthorRole, Message
 from petitions.models import PetitionComment, PetitionStatusChange
+from petitions.wording import notification_title
 from schedule.models import LessonChange
 
 from .constants import LESSON_CHANGE_HORIZON_DAYS
@@ -26,14 +27,7 @@
 from .models import Announcement
 from .selectors import announcements_for_student
 
-STATUS_TITLES = {
-    "in_progress": "Заявка «{name}» взята в работу",
-    "ready": "Заявка «{name}» готова — заберите документ в деканате",
-    "issued": "Заявка «{name}» выдана",
-    "rejected": "Заявка «{name}» отклонена",
-}
 
-
 @dataclass(frozen=True)
 class FeedContext:
     user_id: int
@@ -131,7 +125,7 @@
 
 class PetitionStatusSource(FeedSource):
     kind = "petition_status"
-    tag = "Заявка"
+    tag = "Документы"
     event_field = "created_at"
     related = ("petition__request_type",)
 
@@ -141,10 +135,8 @@
         )
 
     def to_item(self, obj: PetitionStatusChange, ctx: FeedContext) -> FeedItem:
-        name = obj.petition.request_type.name
-        title = STATUS_TITLES.get(obj.to_status, "").format(name=name)
-        if not title:
-            title = f"Заявка «{name}»: статус «{obj.get_to_status_display()}»"
+        request_type = obj.petition.request_type
+        title = notification_title(obj.to_status, request_type.kind, request_type.name)
         return FeedItem(
             key=f"petition-status-{obj.pk}",
             kind=self.kind,
@@ -158,7 +150,7 @@
 
 class PetitionCommentSource(FeedSource):
     kind = "petition_comment"
-    tag = "Заявка"
+    tag = "Документы"
     event_field = "created_at"
     related = ("petition__request_type",)
 
@@ -174,7 +166,7 @@
             kind=self.kind,
             tag=self.tag,
             timestamp=obj.created_at,
-            title=f"Комментарий деканата к заявке «{name}»",
+            title=f"Комментарий деканата: «{name}»",
             body=obj.text,
             url=reverse("petitions:detail", kwargs={"public_id": obj.petition.public_id}),
         )
````

### F7. `chat/demo.py`

````diff
--- a/chat/demo.py
+++ b/chat/demo.py
@@ -49,7 +49,8 @@
         "c-1-4",
         "staff1",
         3,
-        "Да, можно. Подайте заявку «Справка об обучении» и укажите это в комментарии.",
+        "Да, можно. Закажите справку об обучении в разделе «Документы» "
+        "и укажите это в комментарии.",
     ),
     ChatSeed(
         "student3",
````

### F8. Login page `accounts/templates/accounts/login.html` (whole file)

````django
{% extends "base.html" %}
{% load static %}
{% block title %}Вход — Цифровой деканат будущего{% endblock %}
{% block extra_head %}<script src="{% static 'js/password-toggle.js' %}" defer></script>{% endblock %}
{% block content %}
  <h1>Вход</h1>
  <form method="post" class="form">
    {% csrf_token %}
    {{ form.non_field_errors }}
    <div>{{ form.username.as_field_group }}</div>
    <div>
      {{ form.password.label_tag }}
      {{ form.password.errors }}
      <div class="password-field">
        {{ form.password }}
        <button type="button" class="password-toggle" data-password-toggle aria-controls="{{ form.password.id_for_label }}" aria-pressed="false" aria-label="Показать пароль" hidden>{% include "includes/icon_eye.html" %}{% include "includes/icon_eye_off.html" %}</button>
      </div>
    </div>
    <input type="hidden" name="next" value="{{ next }}">
    <button type="submit">Войти</button>
  </form>
{% endblock %}
````

### F9. `static/js/password-toggle.js` (new)

````javascript
/* Show/hide password on the login page (TASK-017). Progressive enhancement:
   without this script the toggle stays hidden and the form works as before. */
(function () {
  "use strict";
  var buttons = document.querySelectorAll("[data-password-toggle]");
  Array.prototype.forEach.call(buttons, function (button) {
    var input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) {
      return;
    }
    function setShown(shown) {
      input.type = shown ? "text" : "password";
      button.setAttribute("aria-pressed", shown ? "true" : "false");
    }
    button.addEventListener("click", function () {
      setShown(input.type === "password");
    });
    if (input.form) {
      // Submit as a password field so browsers and password managers treat it as one.
      input.form.addEventListener("submit", function () {
        setShown(false);
      });
    }
    button.hidden = false;
  });
})();
````

No `innerHTML`, no `eval`, no storage, no network; the accessible name is not changed by the script (D4).

### F10. Icons (new; reference drawings, D6)

`templates/includes/icon_eye.html`:

````html
<svg class="icon-eye" viewBox="0 0 12 8" width="24" height="16" shape-rendering="crispEdges" aria-hidden="true" focusable="false"><g fill="currentColor"><rect x="3" y="0" width="6" height="1"/><rect x="1" y="1" width="2" height="1"/><rect x="9" y="1" width="2" height="1"/><rect x="0" y="2" width="1" height="4"/><rect x="11" y="2" width="1" height="4"/><rect x="4" y="2" width="4" height="4"/><rect x="1" y="6" width="2" height="1"/><rect x="9" y="6" width="2" height="1"/><rect x="3" y="7" width="6" height="1"/></g></svg>
````

`templates/includes/icon_eye_off.html`:

````html
<svg class="icon-eye-off" viewBox="0 0 12 8" width="24" height="16" shape-rendering="crispEdges" aria-hidden="true" focusable="false"><g fill="currentColor"><rect x="3" y="0" width="6" height="1"/><rect x="1" y="1" width="2" height="1"/><rect x="0" y="2" width="1" height="4"/><rect x="11" y="2" width="1" height="3"/><rect x="5" y="2" width="2" height="2"/><rect x="4" y="4" width="1" height="1"/><rect x="1" y="6" width="2" height="1"/><rect x="3" y="7" width="5" height="1"/><rect x="11" y="0" width="1" height="1"/><rect x="10" y="1" width="1" height="1"/><rect x="9" y="2" width="1" height="1"/><rect x="8" y="3" width="1" height="1"/><rect x="7" y="4" width="1" height="1"/><rect x="6" y="5" width="1" height="1"/><rect x="5" y="6" width="1" height="1"/><rect x="4" y="7" width="1" height="1"/><rect x="9" y="6" width="2" height="1"/></g></svg>
````

### F11. CSS (append; you may tune values in the visual check, but keep the selectors the tests check and use tokens only)

`static/css/base.css`:

````diff
--- a/static/css/base.css
+++ b/static/css/base.css
@@ -934,4 +934,38 @@
 
 p > .btn {
   margin-inline: 6px;
+}
+
+/* Password field with the show/hide toggle (TASK-017). */
+.password-field {
+  display: flex;
+  gap: var(--space-2);
+  align-items: stretch;
+}
+
+.password-field input {
+  flex: 1 1 auto;
+}
+
+.password-toggle {
+  display: inline-flex;
+  align-items: center;
+  justify-content: center;
+  flex: 0 0 auto;
+  min-width: 2.75rem;
+  min-height: 2.75rem;
+  padding: 0;
 }
+
+.password-toggle[hidden] {
+  display: none;
+}
+
+.password-toggle .icon-eye-off,
+.password-toggle[aria-pressed="true"] .icon-eye {
+  display: none;
+}
+
+.password-toggle[aria-pressed="true"] .icon-eye-off {
+  display: block;
+}
````

`static/css/theme.css`:

````diff
--- a/static/css/theme.css
+++ b/static/css/theme.css
@@ -693,3 +693,14 @@
     background: var(--color-scroll-thumb-hover);
   }
 }
+
+/* Password toggle: panel button, not the orange primary (TASK-017). */
+.form .password-toggle {
+  border: var(--frame-width) solid var(--color-frame);
+  background: var(--color-panel);
+  color: var(--color-text);
+}
+
+.form .password-toggle:hover {
+  border-color: var(--color-field-border);
+}
````

### F12. Existing tests to update

See section 7, "Changed existing tests".

## 5. Feasibility check

1. **Baseline** — HEAD 16399ea: 1181 tests OK (TASK-016 count, `docs/tasks/TASK-016.md` §5).
2. **Code without new tests** on a copy (`git archive HEAD`, no `.env`): 12 existing tests failed, each only on a
   changed text (list in section 7, "Changed existing tests") — no logic broke. Note: under `--parallel` a
   failing test can crash the runner with `TypeError: cannot pickle 'traceback' object`; run the failing module
   without `--parallel` to see the real failure.
3. **Full change applied** (copy `$TMPDIR/t017`): `manage.py test --parallel` → `Ran 1212 tests … OK`
   (`$TMPDIR/test-t017-full-20261120-143253.log`, 01:33 MSK 21.11); `--parallel 2` → 1212 OK
   (`$TMPDIR/test-t017-p2-20261120-143401.log`); `run_tests_at.py 2027-03-01T12:00:00` → 1212 OK
   (`$TMPDIR/test-t017-frozen-20261120-143521.log`, 01:37 MSK). `ruff check .`, `ruff format --check .` clean.
   `makemigrations --check` → No changes detected.
4. **New tests fail on HEAD** — `petitions.tests.test_wording` cannot import `petitions.wording`;
   `accounts.tests.test_login_page`: 7 of 8 fail (no toggle, no script, no icons, no CSS); the one that passes on
   HEAD is the guard `test_fields_keep_autocomplete` (`$TMPDIR/test-t017-newtests-on-head-20261120-143756.log`).
5. **Migrations on a database seeded with HEAD** (7 types incl. "Справка в военкомат", 8 petitions): `migrate`
   → `0004_documents_wording… OK`, `0005_admission_certificate… OK`; types after: the same 7 rows, the 5th renamed
   to "Справка о поступлении" (`comment_required=False`), no "Справка в военкомат"; `seed_demo` twice → no error,
   still 7 types, 8 petitions. The migration tests (`TransactionTestCase` with `MigrationExecutor`) also cover
   backwards, the "new name already taken" branch and an empty database; they pass under `--parallel`.
6. **Toggle in Chrome** (runserver on that database, 360 × 780 and 1024 × 768): the button is visible with JS,
   44 px high; Space and Enter on the focused button switch `type` password ↔ text, `aria-pressed` false ↔ true,
   icon eye ↔ crossed eye; the name stays "Показать пароль"; login with the real password then works (redirect to
   `/profile/`); zero CSP violations (console). At 360 px the 24 × 16 icon is readable but small — tune it in the
   visual check.
7. **Grep for the old word** — after the change `[Зз]аявк|[Зз]аявок` occurs in no template, no Python string of
   the apps (tests and migrations excluded) and no JS; the test `NoOldWordTests` enforces it (it parses Python
   with `ast`, > 500 strings checked).
8. **CSP** — the new script is external and same-origin; `TemplatesFitPolicyTests` (TASK-016) passes: no inline
   script/style/handlers in the new templates.
9. **Queries** — the existing `QueryCountTests` (petitions pages) pass unchanged: `request_type` is already
   loaded where statuses are shown.
10. **Safety** — no `.env` read; temporary databases only; the project tree was not modified by this check.

## 6. Implementation order

1. F1 (wording + filters) and `petitions/tests/test_wording.py` unit part.
2. F3 + generate 0004; F4; F2 templates; F6; F7.
3. F5 (data migration, demo) + `petitions/tests/test_migrations.py`.
4. F8–F11 (login toggle) + `accounts/tests/test_login_page.py`.
5. Update the existing tests (section 7); `ruff format` on changed Python files (never on `docs/`); `ruff check .`.
6. Verification and visual check (section 8).

## 7. Test plan

### Traceability

| AC | Tests |
|---|---|
| AC1 | `accounts/tests/test_login_page.py::LoginToggleMarkupTests::test_toggle_button_attributes`, `::test_two_pixel_icons`, `LoginToggleStaticTests::test_css`, `::test_icons`; visual check |
| AC2 | `LoginToggleMarkupTests::test_script_external_and_deferred`, `::test_fields_keep_autocomplete`, `::test_errors_still_shown`, `LoginToggleStaticTests::test_script`; `core/tests/test_design.py::ExternalResourceTests::test_scripts_only_where_expected`; `core/tests/test_middleware.py::TemplatesFitPolicyTests` (unchanged); existing login/throttling tests |
| AC3 | `petitions/tests/test_wording.py::NoOldWordTests` (3), `WordingUnitTests::test_admin_names`, `PagesWordingTests::test_nav_and_titles`, `::test_submit_buttons_by_kind`, `::test_submitted_page_by_kind`, `::test_notifications_by_kind`; `core/tests/test_home.py::HomeOtherRolesTests::test_staff_home_buttons` |
| AC4 | `WordingUnitTests::test_generic_status_labels_masculine`, `::test_status_label_by_kind`, `::test_status_label_unknown_kind_is_generic`, `::test_action_labels`; `PagesWordingTests::test_student_list_and_detail_status_by_kind`, `::test_staff_pages_by_kind`, `::test_flash_message_by_kind`; `petitions/tests/test_workflow.py::…::test_every_target_has_label` |
| AC5 | `petitions/tests/test_migrations.py::AdmissionCertificateMigrationTests` (4); `petitions/tests/test_demo.py::PetitionsDemoTests::test_types_exact`, `::test_idempotent` |
| AC6 | `PagesWordingTests::test_subject_hint_by_kind` |
| Messages | `WordingUnitTests::test_plural`, `::test_notification_titles`; `PagesWordingTests::test_comment_required_error_by_kind`; changed service/view tests below |

### Access matrix

No access rule changes. Pages checked per role: student (nav, my list, catalog, form, submitted, detail,
notifications), staff (nav, home, queue, detail, flash message), anonymous (login page).

### Edge cases

Plural for 1, 2–4, 5, 11–14, 21, 22, 25, 111; unknown kind → generic labels; the "new name taken" migration
branch; backwards migration; empty database migration; the error re-render of the login form keeps the toggle and
`aria-describedby`; the form is submitted with `type="password"` after showing the password.

### Changed existing tests (with reason)

| Test | Change |
|---|---|
| `core/tests/test_home.py::HomeOtherRolesTests::test_staff_home_buttons` | button text "Заявки" → "Документы" |
| `core/tests/test_design.py::ExternalResourceTests::test_scripts_only_in_chat` | renamed `test_scripts_only_where_expected`; + `accounts/templates/accounts/login.html`; `static/js` = `chat.js`, `password-toggle.js` |
| `petitions/tests/test_demo.py::PetitionsDemoTests::test_types_exact` | "Справка в военкомат", required → "Справка о поступлении", optional |
| `petitions/tests/test_services.py::SubmitTests::test_limit_three_open_per_type` | exact new message |
| `petitions/tests/test_services.py::TransitionTests::test_stale_expected_status_rejected` | "Документ уже изменён, обновите страницу." |
| `petitions/tests/test_views.py::FormTests::test_limit_message_shown` | "3 документа этого вида в работе" |
| `petitions/tests/test_views.py::StudentPagesTests::test_my_list_empty_state`, `::test_catalog_link_on_list_with_requests`, `::test_catalog_link_on_empty_list` | "Документов пока нет", "Оформить документ" |
| `petitions/tests/test_views.py::StaffPagesTests::test_queue_empty_state` | "Документов нет" |
| `petitions/tests/test_views.py::StaffActionTests::test_invalid_transition_message`, `::test_stale_message_shown` | "Нельзя перевести документ", "Документ уже изменён, обновите страницу" |
| `petitions/tests/test_workflow.py::…::test_every_target_has_label` | imports `ACTION_LABELS` from `petitions.wording`; checks both kinds |

Test count: 1181 → 1212 (+31).

### F13. Test code (exact)

`petitions/tests/test_wording.py` (new):

````python
"""TASK-017: "Документы" wording that agrees with the kind of a document."""

import ast
import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.testing import FrozenClockMixin
from petitions import wording
from petitions.models import (
    Petition,
    PetitionAttachment,
    PetitionComment,
    PetitionStatus,
    PetitionStatusChange,
    RequestType,
)
from petitions.services import change_status, submit_petition
from petitions.tests.helpers import make_petition, make_type

OLD_WORD = re.compile(r"[Зз]аявк|[Зз]аявок")
BASE = Path(settings.BASE_DIR)
APPS = (
    "accounts",
    "academics",
    "campusmap",
    "chat",
    "core",
    "notifications",
    "petitions",
    "schedule",
    "university",
)


class WordingUnitTests(SimpleTestCase):
    def test_generic_status_labels_masculine(self):
        self.assertEqual(
            dict(PetitionStatus.choices),
            {
                "submitted": "Подан",
                "in_progress": "В работе",
                "ready": "Готов",
                "issued": "Выдан",
                "rejected": "Отклонён",
            },
        )

    def test_status_label_by_kind(self):
        cases = {
            "certificate": ["Подана", "В работе", "Готова", "Выдана", "Отклонена"],
            "application": ["Подано", "В работе", "Готово", "Выдано", "Отклонено"],
        }
        statuses = ["submitted", "in_progress", "ready", "issued", "rejected"]
        for kind, labels in cases.items():
            for status, label in zip(statuses, labels, strict=True):
                self.assertEqual(wording.status_label(status, kind), label, (kind, status))

    def test_status_label_unknown_kind_is_generic(self):
        self.assertEqual(wording.status_label("ready", "other"), "Готов")

    def test_action_labels(self):
        self.assertEqual(wording.action_label("ready", "certificate"), "Отметить готовой")
        self.assertEqual(wording.action_label("issued", "certificate"), "Отметить выданной")
        self.assertEqual(wording.action_label("ready", "application"), "Отметить готовым")
        self.assertEqual(wording.action_label("issued", "application"), "Отметить выданным")
        self.assertEqual(wording.action_label("in_progress", "application"), "Взять в работу")
        self.assertEqual(wording.action_label("rejected", "application"), "Отклонить")

    def test_plural(self):
        forms = wording.DOCUMENT_FORMS
        expected = {
            1: "документ",
            2: "документа",
            3: "документа",
            4: "документа",
            5: "документов",
            11: "документов",
            12: "документов",
            14: "документов",
            21: "документ",
            22: "документа",
            25: "документов",
            111: "документов",
        }
        for n, form in expected.items():
            self.assertEqual(wording.plural_ru(n, forms), form, n)

    def test_notification_titles(self):
        cert = {
            "in_progress": "«Х» взята в работу",
            "ready": "«Х» готова — заберите её в деканате",
            "issued": "«Х» выдана",
            "rejected": "«Х» отклонена",
            "submitted": "«Х»: статус «Подана»",
        }
        appl = {
            "in_progress": "«Х» взято в работу",
            "ready": "«Х» готово — заберите его в деканате",
            "issued": "«Х» выдано",
            "rejected": "«Х» отклонено",
            "submitted": "«Х»: статус «Подано»",
        }
        for status, title in cert.items():
            self.assertEqual(wording.notification_title(status, "certificate", "Х"), title)
        for status, title in appl.items():
            self.assertEqual(wording.notification_title(status, "application", "Х"), title)

    def test_admin_names(self):
        self.assertEqual(apps.get_app_config("petitions").verbose_name, "Документы")
        self.assertEqual(Petition._meta.verbose_name, "документ")
        self.assertEqual(Petition._meta.verbose_name_plural, "документы")
        self.assertEqual(RequestType._meta.verbose_name, "вид документа")
        self.assertEqual(RequestType._meta.verbose_name_plural, "виды документов")
        self.assertEqual(PetitionAttachment._meta.verbose_name, "файл к документу")
        self.assertEqual(PetitionAttachment._meta.verbose_name_plural, "файлы к документам")
        for model in (PetitionAttachment, PetitionStatusChange, PetitionComment):
            self.assertEqual(model._meta.get_field("petition").verbose_name, "документ")
        self.assertEqual(Petition._meta.get_field("request_type").verbose_name, "вид документа")


class NoOldWordTests(SimpleTestCase):
    """No user-visible "заявка" is left; "заявление" (a kind) stays."""

    def test_templates(self):
        paths = sorted(BASE.glob("templates/**/*.html")) + sorted(
            BASE.glob("*/templates/**/*.html")
        )
        self.assertGreater(len(paths), 30)
        for path in paths:
            self.assertIsNone(OLD_WORD.search(path.read_text(encoding="utf-8")), path)

    def test_python_strings(self):
        checked = 0
        for app in APPS:
            for path in sorted((BASE / app).rglob("*.py")):
                if "tests" in path.parts or "migrations" in path.parts:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        checked += 1
                        self.assertIsNone(OLD_WORD.search(node.value), f"{path}: {node.value}")
        self.assertGreater(checked, 500)

    def test_static_js(self):
        for path in sorted((BASE / "static" / "js").glob("*.js")):
            self.assertIsNone(OLD_WORD.search(path.read_text(encoding="utf-8")), path)


class PagesWordingTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.staff = make_staff("sx", self.fac)
        self.cert = make_type(name="Справка Х")
        self.appl = make_type(name="Заявление Х", kind="application", days=5)
        self.p_cert = make_petition(self.student, self.cert)
        self.p_appl = make_petition(self.student, self.appl)

    def _student_get(self, url):
        self.client.force_login(self.student.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        return response.content.decode()

    def _staff_get(self, url):
        self.client.force_login(self.staff)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        return response.content.decode()

    def test_nav_and_titles(self):
        content = self._student_get(reverse("petitions:my_list"))
        self.assertIn('aria-current="page">Документы</a>', content)
        self.assertIn("<h1>Мои документы</h1>", content)
        self.assertIn(">Оформить документ</a>", content)
        content = self._student_get(reverse("petitions:catalog"))
        self.assertIn("<h1>Оформить документ</h1>", content)
        content = self._staff_get(reverse("petitions:staff_queue"))
        self.assertIn('aria-current="page">Документы</a>', content)
        self.assertIn("<h1>Документы</h1>", content)
        self.assertIn('<label for="type">Вид документа</label>', content)

    def test_submit_buttons_by_kind(self):
        content = self._student_get(reverse("petitions:submit", args=[self.cert.pk]))
        self.assertIn('<button type="submit">Заказать справку</button>', content)
        content = self._student_get(reverse("petitions:submit", args=[self.appl.pk]))
        self.assertIn('<button type="submit">Подать заявление</button>', content)

    def test_submitted_page_by_kind(self):
        content = self._student_get(reverse("petitions:submitted", args=[self.p_cert.public_id]))
        self.assertIn("<h1>Справка заказана</h1>", content)
        self.assertIn(">К справке</a>", content)
        self.assertIn(">Мои документы</a>", content)
        content = self._student_get(reverse("petitions:submitted", args=[self.p_appl.public_id]))
        self.assertIn("<h1>Заявление подано</h1>", content)
        self.assertIn(">К заявлению</a>", content)

    def test_student_list_and_detail_status_by_kind(self):
        change_status(self.p_appl, self.staff, "submitted", "in_progress")
        change_status(self.p_appl, self.staff, "in_progress", "ready")
        content = self._student_get(reverse("petitions:my_list"))
        self.assertIn('status--submitted">Подана</span>', content)
        self.assertIn('status--ready">Готово</span>', content)
        content = self._student_get(reverse("petitions:detail", args=[self.p_appl.public_id]))
        self.assertIn('<p class="status status--ready">Готово</p>', content)
        self.assertIn("<p>Подано: ", content)
        self.assertIn("Подано → В работе", content)
        self.assertIn("В работе → Готово", content)
        content = self._student_get(reverse("petitions:detail", args=[self.p_cert.public_id]))
        self.assertIn("<p>Подана: ", content)

    def test_staff_pages_by_kind(self):
        content = self._staff_get(reverse("petitions:staff_queue"))
        self.assertIn('<option value="submitted">Подан</option>', content)
        self.assertIn('<option value="rejected">Отклонён</option>', content)
        self.assertIn('status--submitted">Подано</span>', content)
        self.assertIn('status--submitted">Подана</span>', content)
        content = self._staff_get(reverse("petitions:staff_detail", args=[self.p_cert.public_id]))
        self.assertIn(f"<h1>Справка № {self.p_cert.short_id}</h1>", content)
        self.assertIn("<h2>Документ</h2>", content)
        change_status(self.p_appl, self.staff, "submitted", "in_progress")
        content = self._staff_get(reverse("petitions:staff_detail", args=[self.p_appl.public_id]))
        self.assertIn(f"<h1>Заявление № {self.p_appl.short_id}</h1>", content)
        self.assertIn(">Отметить готовым</button>", content)
        change_status(self.p_cert, self.staff, "submitted", "in_progress")
        content = self._staff_get(reverse("petitions:staff_detail", args=[self.p_cert.public_id]))
        self.assertIn(">Отметить готовой</button>", content)

    def test_flash_message_by_kind(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("petitions:staff_transition", args=[self.p_appl.public_id]),
            {"expected_status": "submitted", "new_status": "in_progress"},
            follow=True,
        )
        self.assertIn("Статус изменён: В работе.", response.content.decode())
        response = self.client.post(
            reverse("petitions:staff_transition", args=[self.p_appl.public_id]),
            {"expected_status": "in_progress", "new_status": "ready"},
            follow=True,
        )
        self.assertIn("Статус изменён: Готово.", response.content.decode())

    def test_comment_required_error_by_kind(self):
        # The form shows Django's "Обязательное поле." (TASK-014-FIX); the service message
        # (also used by PetitionForm.clean_comment) agrees with the kind.
        cert = make_type(name="Справка К", comment_required=True, hint="Причина")
        appl = make_type(name="Заявление К", kind="application", comment_required=True, hint="П")
        with self.assertRaises(ValidationError) as cm:
            submit_petition(self.student, cert, "", [])
        self.assertIn("Для этой справки комментарий обязателен.", cm.exception.messages)
        with self.assertRaises(ValidationError) as cm:
            submit_petition(self.student, appl, "", [])
        self.assertIn("Для этого заявления комментарий обязателен.", cm.exception.messages)

    def test_subject_hint_by_kind(self):
        cert = make_type(name="Другая С", comment_required=True, hint="h", subject_required=True)
        appl = make_type(
            name="Другое З",
            kind="application",
            comment_required=True,
            hint="h",
            subject_required=True,
        )
        content = self._student_get(reverse("petitions:submit", args=[cert.pk]))
        self.assertIn("Что именно нужно, например: «Справка о периоде обучения».", content)
        content = self._student_get(reverse("petitions:submit", args=[appl.pk]))
        self.assertIn(
            "Что именно нужно, например: «Заявление на индивидуальный учебный план».", content
        )
        self.assertNotIn("Справка о периоде обучения", content)

    def test_notifications_by_kind(self):
        change_status(self.p_cert, self.staff, "submitted", "in_progress")
        change_status(self.p_appl, self.staff, "submitted", "in_progress")
        change_status(self.p_appl, self.staff, "in_progress", "ready")
        content = self._student_get(reverse("notifications:feed"))
        self.assertIn("«Справка Х» взята в работу", content)
        self.assertIn("«Заявление Х» взято в работу", content)
        self.assertIn("«Заявление Х» готово — заберите его в деканате", content)
        self.assertIn("Документы&nbsp;·", content)
````

`petitions/tests/test_migrations.py` (new):

````python
"""TASK-017: data migration 0005 renames "Справка в военкомат" in place."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [("petitions", "0004_documents_wording")]
AFTER = [("petitions", "0005_admission_certificate")]


class AdmissionCertificateMigrationTests(TransactionTestCase):
    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(target)
        return executor.loader.project_state(target).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def _make_old(self, apps, **extra):
        RequestType = apps.get_model("petitions", "RequestType")
        values = {
            "name": "Справка в военкомат",
            "kind": "certificate",
            "processing_days": 3,
            "comment_required": True,
            "comment_hint": "Укажите военкомат.",
            "description": "Справка для военного комиссариата.",
            "subject_required": False,
            "is_active": True,
        }
        values.update(extra)
        return RequestType.objects.create(**values)

    def test_rename_in_place(self):
        old_apps = self._migrate(BEFORE)
        old = self._make_old(old_apps)
        new_apps = self._migrate(AFTER)
        RequestType = new_apps.get_model("petitions", "RequestType")
        row = RequestType.objects.get(pk=old.pk)
        self.assertEqual(row.name, "Справка о поступлении")
        self.assertFalse(row.comment_required)
        self.assertEqual(row.comment_hint, "Можно указать, куда нужна справка.")
        self.assertEqual(row.description, "Подтверждает зачисление в университет.")
        self.assertEqual(row.processing_days, 3)
        self.assertEqual(row.kind, "certificate")
        self.assertTrue(row.is_active)
        self.assertFalse(RequestType.objects.filter(name="Справка в военкомат").exists())

    def test_backwards(self):
        old_apps = self._migrate(BEFORE)
        old = self._make_old(old_apps)
        self._migrate(AFTER)
        back_apps = self._migrate(BEFORE)
        row = back_apps.get_model("petitions", "RequestType").objects.get(pk=old.pk)
        self.assertEqual(row.name, "Справка в военкомат")
        self.assertTrue(row.comment_required)

    def test_new_name_taken_hides_old(self):
        old_apps = self._migrate(BEFORE)
        old = self._make_old(old_apps)
        self._make_old(
            old_apps, name="Справка о поступлении", comment_required=False, comment_hint=""
        )
        new_apps = self._migrate(AFTER)
        RequestType = new_apps.get_model("petitions", "RequestType")
        self.assertFalse(RequestType.objects.get(pk=old.pk).is_active)
        self.assertEqual(RequestType.objects.filter(name="Справка о поступлении").count(), 1)

    def test_no_old_type_is_noop(self):
        self._migrate(BEFORE)
        new_apps = self._migrate(AFTER)
        RequestType = new_apps.get_model("petitions", "RequestType")
        self.assertFalse(RequestType.objects.filter(name__startswith="Справка").exists())
````

`accounts/tests/test_login_page.py` (new):

````python
"""TASK-017: show/hide password toggle on the login page."""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

BASE = Path(settings.BASE_DIR)


class LoginToggleMarkupTests(TestCase):
    def _content(self, **post):
        if post:
            return self.client.post(reverse("accounts:login"), post).content.decode()
        return self.client.get(reverse("accounts:login")).content.decode()

    def _button(self, content):
        match = re.search(r"<button [^>]*data-password-toggle[^>]*>", content)
        self.assertIsNotNone(match)
        return match.group(0)

    def test_toggle_button_attributes(self):
        button = self._button(self._content())
        for attr in (
            'type="button"',
            'class="password-toggle"',
            'aria-controls="id_password"',
            'aria-pressed="false"',
            'aria-label="Показать пароль"',
            " hidden",
        ):
            self.assertIn(attr, button)

    def test_two_pixel_icons(self):
        content = self._content()
        start = content.index("data-password-toggle")
        end = content.index("</button>", start)
        inner = content[start:end]
        self.assertEqual(inner.count("<svg"), 2)
        self.assertIn('class="icon-eye"', inner)
        self.assertIn('class="icon-eye-off"', inner)
        self.assertEqual(inner.count('shape-rendering="crispEdges"'), 2)
        self.assertEqual(inner.count('aria-hidden="true"'), 2)
        self.assertEqual(inner.count('focusable="false"'), 2)
        self.assertNotIn("<path", inner)

    def test_script_external_and_deferred(self):
        content = self._content()
        self.assertIn('<script src="/static/js/password-toggle.js" defer></script>', content)
        self.assertNotIn("<script>", content)

    def test_fields_keep_autocomplete(self):
        content = self._content()
        self.assertRegex(content, r'<input type="text" name="username"[^>]*autocomplete="username"')
        self.assertRegex(
            content, r'<input type="password" name="password"[^>]*autocomplete="current-password"'
        )
        self.assertEqual(content.count('name="password"'), 1)
        self.assertIn('<label for="id_password">', content)
        self.assertIn('<label for="id_username">', content)

    def test_errors_still_shown(self):
        content = self._content(username="nobody", password="")
        self.assertIn('id="id_password_error"', content)
        self.assertIn('aria-describedby="id_password_error"', content)
        content = self._content(username="nobody", password="wrong")
        self.assertIn('class="errorlist nonfield"', content)
        self.assertIn("data-password-toggle", content)


class LoginToggleStaticTests(SimpleTestCase):
    def test_script(self):
        js = (BASE / "static/js/password-toggle.js").read_text(encoding="utf-8")
        for fragment in (
            "[data-password-toggle]",
            'getAttribute("aria-controls")',
            'setAttribute("aria-pressed"',
            '"text" : "password"',
            '"submit"',
            "button.hidden = false",
        ):
            self.assertIn(fragment, js)
        for forbidden in ("innerHTML", "eval(", "aria-label", "fetch(", "localStorage"):
            self.assertNotIn(forbidden, js)

    def test_css(self):
        base = (BASE / "static/css/base.css").read_text(encoding="utf-8")
        self.assertRegex(base, r"\.password-toggle\[hidden\]\s*\{\s*display:\s*none;")
        self.assertRegex(base, r"\.password-toggle\s*\{[^}]*min-width:\s*2\.75rem")
        self.assertRegex(base, r"\.password-toggle\s*\{[^}]*min-height:\s*2\.75rem")
        self.assertRegex(
            base,
            r'\.password-toggle\[aria-pressed="true"\]\s*\.icon-eye-off\s*\{\s*display:\s*block',
        )

    def test_icons(self):
        for name in ("icon_eye.html", "icon_eye_off.html"):
            svg = (BASE / "templates/includes" / name).read_text(encoding="utf-8")
            self.assertIn('shape-rendering="crispEdges"', svg)
            self.assertIn('fill="currentColor"', svg)
            self.assertIn("<rect", svg)
            for forbidden in ("style=", "<path", "<script", "href="):
                self.assertNotIn(forbidden, svg)
````

Changed existing tests:

````diff
--- a/core/tests/test_home.py
+++ b/core/tests/test_home.py
@@ -223,7 +223,7 @@
         self.client.force_login(self.staff)
         content = self.client.get("/").content.decode()
         self.assertIn("<h1>Деканат</h1>", content)
-        requests = content.index('<a class="btn" href="/staff/requests/">Заявки</a>')
+        requests = content.index('<a class="btn" href="/staff/requests/">Документы</a>')
         chats = content.index('<a class="btn" href="/staff/chats/">Чаты</a>')
         ann = content.index('<a class="btn" href="/staff/announcements/">Объявления</a>')
         self.assertLess(requests, chats)
````

````diff
--- a/core/tests/test_design.py
+++ b/core/tests/test_design.py
@@ -190,7 +190,7 @@
                 self.assertNotIn("fonts.googleapis", text)
                 self.assertNotIn("fonts.gstatic", text)
 
-    def test_scripts_only_in_chat(self):
+    def test_scripts_only_where_expected(self):
         with_script = {
             str(path.relative_to(BASE))
             for path in _project_templates()
@@ -198,9 +198,13 @@
         }
         self.assertEqual(
             with_script,
-            {"chat/templates/chat/student.html", "chat/templates/chat/staff_dialog.html"},
+            {
+                "chat/templates/chat/student.html",
+                "chat/templates/chat/staff_dialog.html",
+                "accounts/templates/accounts/login.html",  # TASK-017: password toggle
+            },
         )
-        self.assertEqual(sorted(os.listdir(BASE / "static/js")), ["chat.js"])
+        self.assertEqual(sorted(os.listdir(BASE / "static/js")), ["chat.js", "password-toggle.js"])
 
     def test_no_admin_templates(self):
         self.assertFalse((BASE / "templates/admin").exists())
````

````diff
--- a/petitions/tests/test_demo.py
+++ b/petitions/tests/test_demo.py
@@ -48,7 +48,7 @@
             ("Справка для стипендиального отдела", "certificate", 3, True, False),
             ("Заявление на повторную промежуточную аттестацию", "application", 10, True, False),
             ("Заявление на академический отпуск", "application", 15, True, False),
-            ("Справка в военкомат", "certificate", 3, True, False),
+            ("Справка о поступлении", "certificate", 3, False, False),
             ("Другая справка", "certificate", 5, True, True),
             ("Другое заявление", "application", 5, True, True),
         }
````

````diff
--- a/petitions/tests/test_services.py
+++ b/petitions/tests/test_services.py
@@ -178,7 +178,10 @@
             submit_petition(self.student, self.type, "", [])
         with self.assertRaises(ValidationError) as cm:
             submit_petition(self.student, self.type, "", [])
-        self.assertTrue(any("открытые заявки" in m for m in cm.exception.messages))
+        self.assertIn(
+            "У вас уже 3 документа этого вида в работе. Дождитесь их выполнения.",
+            cm.exception.messages,
+        )
         other = make_type(name="Заявление", kind="application", days=5)
         submit_petition(self.student, other, "", [])
         p = Petition.objects.filter(student=self.student, request_type=self.type).first()
@@ -297,7 +300,7 @@
         change_status(self.petition, self.staff_x, "submitted", "in_progress")
         with self.assertRaises(StaleStatusError) as cm:
             change_status(self.petition, self.staff_x, "submitted", "ready")
-        self.assertIn("Заявка уже изменена, обновите страницу.", cm.exception.messages)
+        self.assertIn("Документ уже изменён, обновите страницу.", cm.exception.messages)
         self.petition.refresh_from_db()
         self.assertEqual(self.petition.status, "in_progress")
         self.assertEqual(self.petition.history.count(), 2)
````

````diff
--- a/petitions/tests/test_views.py
+++ b/petitions/tests/test_views.py
@@ -254,7 +254,7 @@
             self.client.post(self.url, {"comment": ""})
         resp = self.client.post(self.url, {"comment": ""})
         self.assertEqual(resp.status_code, 200)
-        self.assertIn("открытые заявки", resp.content.decode())
+        self.assertIn("3 документа этого вида в работе", resp.content.decode())
 
     def test_csrf_enforced(self):
         client = Client(enforce_csrf_checks=True)
@@ -297,14 +297,14 @@
         self.petition.delete()
         self.client.force_login(self.student.user)
         resp = self.client.get(reverse("petitions:my_list"))
-        self.assertIn("Заявок пока нет", resp.content.decode())
+        self.assertIn("Документов пока нет", resp.content.decode())
 
     def test_catalog_link_on_list_with_requests(self):
         self.client.force_login(self.student.user)
         resp = self.client.get(reverse("petitions:my_list"))
         content = resp.content.decode()
         self.assertEqual(content.count('href="/requests/new/"'), 1)
-        self.assertIn("Подать заявку", content)
+        self.assertIn("Оформить документ", content)
 
     def test_catalog_link_on_empty_list(self):
         self.petition.delete()
@@ -312,7 +312,7 @@
         resp = self.client.get(reverse("petitions:my_list"))
         content = resp.content.decode()
         self.assertEqual(content.count('href="/requests/new/"'), 1)
-        self.assertIn("Заявок пока нет.", content)
+        self.assertIn("Документов пока нет.", content)
 
     def test_detail_shows_history_comments_attachments(self):
         store_attachment(self.petition, ContentFile(b"%PDF-1.4\n%%EOF"), "a.pdf", 12)
@@ -396,7 +396,7 @@
         Petition.objects.all().delete()
         self.client.force_login(self.staff)
         resp = self.client.get(reverse("petitions:staff_queue"))
-        self.assertIn("Заявок нет", resp.content.decode())
+        self.assertIn("Документов нет", resp.content.decode())
 
     def test_detail_shows_student_info_and_actions(self):
         self.client.force_login(self.staff)
@@ -476,7 +476,7 @@
             {"expected_status": "submitted", "new_status": "issued"},
             follow=True,
         )
-        self.assertIn("Нельзя перевести заявку", resp.content.decode())
+        self.assertIn("Нельзя перевести документ", resp.content.decode())
         self.petition.refresh_from_db()
         self.assertEqual(self.petition.status, "submitted")
 
@@ -488,7 +488,7 @@
             {"expected_status": "submitted", "new_status": "ready"},
             follow=True,
         )
-        self.assertIn("Заявка уже изменена, обновите страницу", resp.content.decode())
+        self.assertIn("Документ уже изменён, обновите страницу", resp.content.decode())
         self.petition.refresh_from_db()
         self.assertEqual(self.petition.status, "in_progress")
 
````

````diff
--- a/petitions/tests/test_workflow.py
+++ b/petitions/tests/test_workflow.py
@@ -1,7 +1,7 @@
 from django.test import SimpleTestCase
 
+from petitions.wording import ACTION_LABELS
 from petitions.workflow import (
-    ACTION_LABELS,
     OPEN_STATUSES,
     TRANSITIONS,
     allowed_transitions,
@@ -53,8 +53,10 @@
 
     def test_every_target_has_label(self):
         targets = {t for ts in TRANSITIONS.values() for t in ts}
-        for t in targets:
-            self.assertIn(t, ACTION_LABELS)
+        # TASK-017: the labels live in petitions.wording, one set per kind.
+        for labels in ACTION_LABELS.values():
+            for t in targets:
+                self.assertIn(t, labels)
 
     def test_open_statuses_exact(self):
         self.assertEqual(OPEN_STATUSES, frozenset({"submitted", "in_progress"}))
````

## 8. Verification (UI coder, then Reviewer)

```bash
.venv/bin/python manage.py test --parallel 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/python manage.py test --parallel 2 2>&1 | tee "$TMPDIR/test-p2-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/python scripts/run_tests_at.py 2027-03-01T12:00:00 2>&1 | tee "$TMPDIR/test-frozen-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
grep -rnE "[Зз]аявк|[Зз]аявок" --include='*.html' --include='*.js' templates */templates static/js || echo NO_OLD_WORD
git status --short
```

Migrations on a database seeded **before** the change (never on the project `db.sqlite3`):

```bash
mkdir -p "$TMPDIR/t017-before" && git archive HEAD | tar -x -C "$TMPDIR/t017-before"
export DATABASE_URL="sqlite:///$TMPDIR/t017.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/t017-media" DEMO_PASSWORD=Local-Demo-Pass-2026 DEBUG=true SECRET_KEY=dummy-local
(cd "$TMPDIR/t017-before" && ~/hackatonproject/.venv/bin/python manage.py migrate -v0 && ~/hackatonproject/.venv/bin/python manage.py seed_demo)
.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo && .venv/bin/python manage.py seed_demo
.venv/bin/python manage.py shell -c "from petitions.models import RequestType as R; print(sorted(R.objects.values_list('name', flat=True)))"
unset DATABASE_URL PRIVATE_MEDIA_ROOT DEMO_PASSWORD
```

(`git archive HEAD` is read-only and exports the base commit, because nothing is committed.) Expected: 7 names,
"Справка о поступлении" present, "Справка в военкомат" absent.

**Visual check** (temporary database above, `runserver`, headless browser; report screenshots):
- Login at 360 × 780 and 1024 × 768: toggle in both states (hidden / shown password), keyboard: Tab to the
  toggle (focus outline visible), Space and Enter switch; with JavaScript disabled the toggle is not shown; the
  icon is readable at 360 px (redraw/resize if not, D6); no CSP violation in the console.
- Student (`student1`) at 360 and 1024: nav "Документы", "Мои документы", "Оформить документ" (catalog), a
  certificate form ("Заказать справку") and an application form ("Подать заявление", hint «Заявление на
  индивидуальный учебный план» for "Другое заявление"), the submitted page, a detail page of each kind (status
  and date line agree), notifications feed (tag "Документы", titles by kind).
- Staff (`staff1`) at 360 and 1024: home button "Документы", queue (h1, "Вид документа", status filter
  masculine, row statuses by kind), detail of each kind (h1 "Справка № …" / "Заявление № …", h2 "Документ",
  action buttons by kind, flash message).
- Admin (superuser): app "Документы", models "Документы", "Виды документов", "Файлы к документам" — one look.

Report test counts, log paths and Moscow times; report every failing run with the test name and a traceback
excerpt. Never read `.env`; do not touch `plan.md`.

## 9. Risks

- **Wording outside the map** (D2 status labels, D4 fixed name): both follow the user's grammar rule; the Team
  lead is informed and may override — then only `petitions/wording.py`, the login template and their tests change.
- **Renamed type on the trial database**: existing petitions of the old type show the new name (D3).
- **Icon readability**: the reference icon is small; the visual check decides the final drawing and size.
