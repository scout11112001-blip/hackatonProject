# TASK-012: "Night pixel" visual theme for the whole site

Assignee: **UI coder** (thr_pgcwc2dwnn). Request: Team lead, approved by the user (plan.md stage 4, "Интерфейс (пиксель-арт)").

## Goal

The whole site gets the approved "night pixel" look. It is readable and usable on a 360 px phone and on a desktop. No JavaScript is added. Behaviour stays the same, except for the student and staff home pages and the header, which this spec redesigns.

Design references (read both before you start):
- `docs/design/home-mockup.html` (open it in the browser; it is the reference for colours, frames, buttons and the header);
- `docs/design/home-mockup.jpg` (the approved screenshot, 360 px).

## Acceptance criteria

- AC1. **Tokens.** Every colour of the theme is a named custom property in `static/css/tokens.css` (list in D3). `static/css/base.css` and `static/css/theme.css` contain no colour literals (`#rgb`, `#rrggbb`, `#rrggbbaa`, `rgb(`, `rgba(`, `hsl(`, `hsla(`). Only tokens.css contains them.
- AC2. **Font.** `static/fonts/PressStart2P-Regular.ttf` and `static/fonts/OFL.txt` stay byte-identical (SHA-256 below). `theme.css` declares `@font-face` with `src: url("../fonts/PressStart2P-Regular.ttf") format("truetype")` and `font-display: swap`. The font is used only for: the site title, `h1`, `h2`, card titles, buttons (D6) and tags (D7). Body text, `h3`, nav links, form fields, tables, lists and messages use `--font-body`. `collectstatic` with `CompressedManifestStaticFilesStorage` rewrites the font URL in the processed `theme.css` to the hashed file name.
- AC3. **No external resources.** No template and no CSS file contains `https://`, `@import` or a `url(` that does not start with `../`. Templates may contain `http://` only as the exact SVG namespace `http://www.w3.org/2000/svg` (and they do not need it at all; see D9). Only `chat/student.html` and `chat/staff_dialog.html` contain `<script`. `static/js/` contains only `chat.js`, unchanged.
- AC4. **Logo and favicon.** The header shows the pixel academic cap (inline SVG of `<rect>` elements, `shape-rendering="crispEdges"`, `aria-hidden="true"`, `focusable="false"`; our own drawing, copied from the mockup) and the title "Цифровой деканат" (shown in capitals by CSS, two lines below 48rem). `static/img/favicon.svg` is the same cap. `base.html` and `500.html` link it with `<link rel="icon" href="…/img/favicon.svg" type="image/svg+xml">`.
- AC5. **Header for students.** The header has the brand, the wide nav (≥ 48rem) or the "Меню" `<details>` menu (< 48rem), and a "Уведомления" button with a yellow pixel bell. The button is visible at every width. The button shows a count chip only when the badge is not empty. The badge is computed once per page (existing test `test_badge_computed_once`). The nav lists no longer contain a "Уведомления" item (D11).
- AC6. **Header for staff, superuser and anonymous users.** There is no notifications button. Staff and superusers have the same menu and wide nav as before. Anonymous pages have no menu (existing test `test_anonymous_unchanged`).
- AC7. **Student home** (`core:home`, a student with a profile). It shows the `h1` "Сегодня", the date and the group. Then three cards in this order: "Занятия" (today's lessons: time, pair number, discipline, type, teacher, room link to the map, change mark, the "идёт" tag on the current lesson; empty state "Сегодня занятий нет."), "Дедлайны" and "Новости" (at most 3 rows each). Then two buttons on one line: "Документы" (→ `/requests/`) and "Чат" (→ `/chat/`). The titles "Дедлайны" and "Новости" are links to `/notifications/#deadlines` and `/notifications/#feed`, with an arrow "→" after the text. The old "Все уведомления" link is removed (D12).
- AC8. **Card rows.** In "Дедлайны" and "Новости", each row is one line at every width. The title is a link, cut with an ellipsis and carrying a `title` attribute with the full title. The right-hand label (relative deadline label, or the news date `dd.mm`) is never cut or wrapped.
- AC9. **Staff home.** `h1` "Деканат" and three buttons of the same style and size: "Заявки" (→ `/staff/requests/`), "Чаты" (→ `/staff/chats/`), "Объявления" (→ `/staff/announcements/`).
- AC10. **Other roles on home.** A student without a profile and a superuser see the old placeholder ("Раздел в разработке").
- AC11. **Anchors on the feed page.** `/notifications/` has `<section id="deadlines" …>` and `<section id="feed" …>`.
- AC12. **Home query count.** For a student with two lessons today (one with a room change), one deadline, one news item and one unread chat message, `GET /` makes exactly **14** queries. The count is the same with 1 and 3 lessons, and the same with 0 and 4 deadlines.
- AC13. **Error pages.** `templates/403.html` and `templates/404.html` extend `base.html` and show a themed heading, a short text and a "На главную" button. `templates/500.html` is a standalone page (it does not extend `base.html`, uses no context variables and makes no queries) with the same look.
- AC14. **All pages themed** (list in "Pages" below) without behaviour changes. Forms, inputs, selects, textareas, the file input, errors, messages, empty states, `<details>`, tables and the footer are themed. Tap targets are at least 44 px (D14). Every interactive element has a visible `:focus-visible` style.
- AC15. **Map readable.** Rooms, landmarks, service rooms and the corridor are visible on the dark background. The current room is clearly marked by stroke width, fill and label colour, not by hue alone. The map redesign itself is TASK-013.
- AC16. **Contrast.** Every text/background pair in the "Contrast" table meets WCAG AA. Coral text uses `--color-warn-text` (D4).
- AC17. **No horizontal scroll** at 320, 360 and 1024 px on every page in the "Pages" list, for a student and for staff.
- AC18. **README** has a "## Design" section: palette, font name, licence (SIL OFL 1.1, Reserved Font Name "Press Start 2P", file `static/fonts/OFL.txt`, used unmodified), and "the logo and favicon are our own pixel drawing".
- AC19. The admin site is unchanged (no `templates/admin/`). No new Python dependencies. No migrations.

## Out of scope

- Map improvements: a larger room list, the final highlight design, landmark vs service frames, the corridor label, zoom (TASK-013).
- New features, new pages, behaviour changes other than those listed in AC5–AC13.
- A light theme or a theme switcher. Any JavaScript. Transitions and animations (D15).
- Changes to `static/js/chat.js`, models, migrations, forms, URLs and permissions.

## Design decisions

- **D1. CSS layers.** `tokens.css` holds only custom properties (colours, fonts, font sizes, frame sizes). `base.css` holds layout (display, flex/grid, spacing, widths, the ellipsis rules, visibility by breakpoint, `.visually-hidden`). `theme.css` holds the look: `@font-face`, backgrounds, the gradient, stars, frames, shadows, colours via `var(--…)`, fonts, focus styles, form looks, map colours. All three files stay linked in this order (existing test `test_home_css_layers_in_order`). Keep the existing rules that tests check: `input, select, textarea, button { max-width: 100%; … }` in base.css; `.site-nav--wide { display: none; }` and the `@media (min-width: 48rem) { .site-nav--wide { display: block; } .site-nav-compact { display: none; …` block in base.css; `.chat-message--own { margin-left:` and `.chat-message--other { margin-right:` in base.css; `.map-current .map-room-label` with `var(--color-map-highlight)` in base.css. theme.css must not contain `max-width: 100%`.
- **D2. Breakpoint.** One breakpoint, `48rem`, as now. You may add `min-width: 64rem` rules for desktop font sizes if needed.
- **D3. Tokens.** Keep the existing names (base.css uses them) with new values, and add new ones. Required names and values:

  | Token | Value | Use |
  |---|---|---|
  | `--color-bg` | `#120a2a` | fallback page background |
  | `--color-sky-1` … `--color-sky-4` | `#120a2a`, `#221449`, `#3a2272`, `#4b2a86` | page gradient stops (0%, 40%, 75%, 100%) |
  | `--color-panel` | `rgba(36, 22, 78, 0.88)` | cards, panels, buttons |
  | `--color-frame` | `#5a3fa3` | pixel frame lines, heading text-shadow |
  | `--color-frame-gap` | `#170d33` | the 3 px gap between frame lines |
  | `--color-text` | `#f3ecff` | text |
  | `--color-muted` | `#b8a6e8` | secondary text |
  | `--color-heading` | `#ffd25e` | card titles, bell icon |
  | `--color-link` | `#ffc46b` | links |
  | `--color-accent` | `#ffc46b` | existing name; same value as link |
  | `--color-border` | `#5a3fa3` | existing name; dashed separators |
  | `--color-warn` | `#ff6f7d` | coral backgrounds (count chip) |
  | `--color-warn-text` | `#ff8a95` | coral text: changes, errors, deadline labels (D4) |
  | `--color-changed` | `#ff8a95` | existing name; same value as warn-text |
  | `--color-orange` | `#ff9f2e` | tags, primary buttons, logo |
  | `--color-orange-light` | `#ffc04d` | primary button gradient top |
  | `--color-orange-dark` | `#f07a1a` | primary button gradient bottom |
  | `--color-orange-edge` | `#ffd98a` | primary button border |
  | `--color-on-accent` | `#2b1300` | text on orange, on coral |
  | `--color-now-bg` | `rgba(255, 159, 46, 0.14)` | existing name; current lesson tint |
  | `--color-field-bg` | `#170d33` | inputs, selects, textareas |
  | `--color-field-border` | `#a58cf0` | input borders (3:1, D4) |
  | `--color-focus` | `#ffd25e` | focus outline |
  | `--color-star-yellow`, `--color-star-lilac` | `#ffe9a8`, `#d9c8ff` | stars |
  | `--color-map-highlight` | `#ffd25e` | existing name; current room |
  | `--color-map-highlight-fill` | `rgba(255, 210, 94, 0.22)` | current room fill |
  | `--color-map-room-fill` | `rgba(36, 22, 78, 0.88)` | room fill |
  | `--font-body` | unchanged system stack | body text |
  | `--font-pixel` | `"Press Start 2P", ui-monospace, monospace` | pixel font |
  | `--font-heading` | `var(--font-pixel)` | existing name |
  | `--font-size-title`, `--font-size-h1`, `--font-size-h2`, `--font-size-button`, `--font-size-tag` | in `rem` (D5) | pixel text sizes |
  | `--frame-width` | `3px` | frame line and gap |

  You may add more tokens (for example a slightly lighter corridor fill). Every colour stays in tokens.css.
- **D4. Contrast rules** (computed with the WCAG 2.x formula; the panel is composited over the lightest sky colour `#4b2a86`, which gives `#29184f`, the worst case):
  - On the bare sky (the page outside cards), only `--color-text`, `--color-muted`, `--color-heading`, `--color-link`, `--color-warn-text` and `--color-orange` may be used as text colours.
  - `#ff6f7d` (mockup coral) gives only 3.96:1 on `#4b2a86`. Coral **text** therefore always uses `--color-warn-text` `#ff8a95` (4.72:1 on the lightest sky, 6.87:1 on the panel).
  - The count chip is `--color-warn` background with `--color-on-accent` text (6.54:1). The mockup's white text on coral gives 2.68:1, which fails. This is a deliberate change from the mockup.
  - Input borders use `--color-field-border` `#a58cf0` (3.85:1 on the lightest sky, 5.61:1 on the panel, 6.66:1 against the field). The `#5a3fa3` frame (1.35–2.43:1) is used only for decorative frames of cards and buttons. Buttons are identified by their visible text label (WCAG 1.4.11 does not require a contrasting border then).
  - The focus outline is `--color-focus` (≥ 7.41:1 on every background).
- **D5. Pixel text sizes.** Press Start 2P is monospace: every glyph is exactly 1em wide (`unitsPerEm` 1000, all advance widths 1000; checked from the font's `hmtx` table). A word of N letters at size S is N×S px wide. Content width is 288 px at 320 px and 328 px at 360 px (16 px page padding). Inside a card, subtract 2×(padding + 2 frame widths). Constraints:
  - `h1` < 48rem: at most `1.125rem` (18 px). The longest demo word that can appear in an `h1` is "стипендиального" (15 letters, the request type "Справка для стипендиального отдела"): 15×18 = 270 ≤ 288. You may use a larger `h1` (for example `1.5rem`) at ≥ 48rem.
  - `h2` and card titles: about `0.75rem` (mockup 12 px). Site title, buttons: about `0.6875rem` (mockup 11 px). Tags and chip: about `0.625rem`.
  - Line height for pixel text: about 1.5. Long titles and button labels may wrap between words. `body { overflow-wrap: anywhere; }` stays, so no word causes horizontal scroll.
  - The font has no glyph for "≡" (U+2261). It has "→", "←", "·", "…", "–", "—", "№", "«", "»", "ё", "Ё" (checked from its `cmap`).
- **D6. Buttons.** One pixel button look:
  - Panel button (default): `.btn`, the menu `summary.site-menu-toggle`, the notifications button. It has `--color-panel` background, `--color-text` text, the pixel font, a double frame (3 px `--color-frame` border, then the gap and the outer line made with `box-shadow: 0 0 0 3px var(--color-frame-gap), 0 0 0 6px var(--color-frame)`), square corners and a minimum height of 44 px.
  - Primary button: every `<button>` in a form (`.form button`, `.action-form button`, `.chat-form button`) and `.btn--primary`. It has the orange gradient (`--color-orange-light` → `--color-orange` → `--color-orange-dark`), `--color-orange-edge` border and `--color-on-accent` text.
  - The logout button in the nav looks like a nav link (system font, link colour, underlined), not like a big button. Its tap target is still at least 44 px.
  - The box-shadow frame takes no layout space. Leave at least 6 px around every button (gap or margin) so frames do not overlap.
- **D7. Tags.** `.tag` (new) and the existing `.lesson-badge` ("Сейчас", "Следующая" on the schedule) use the pixel font, `--font-size-tag`, `--color-orange` background and `--color-on-accent` text. The text stays (information is not only colour).
- **D8. Headings.** `h1`: pixel font, `--color-text`, `text-shadow: 3px 3px 0 var(--color-frame)`. `h2` outside cards: pixel font, `--color-heading`. Card titles (`.card-title`, an `h2`): pixel font, `--color-heading`. `h3` stays in the body font, bold, because `h3` holds data (announcement titles, floor names, grade subsections). This is a deliberate reading of "headings" for readability.
- **D9. Inline SVG.** The logo and the bell are includes (`templates/includes/icon_cap.html`, `templates/includes/icon_bell.html`). Each is one `<svg>` with `viewBox`, `width`/`height`, `shape-rendering="crispEdges"`, `aria-hidden="true"`, `focusable="false"` and `<g fill="currentColor">` with the mockup's rects. Inline SVG in HTML needs no `xmlns`; do not add one. `static/img/favicon.svg` is a file, so it needs `xmlns="http://www.w3.org/2000/svg"` and a fixed fill `#ff9f2e` (an image file, not CSS, so AC1 does not apply). Use a square `viewBox` (for example `0 -1 12 12`).
- **D10. Header layout** (exact markup in F5). Order: brand, wide nav, then the actions row (`.site-nav-compact` with the `<details>` menu, then the notifications button). Below 48rem: the brand on the first line, the menu button and the notifications button on the second line, both the same height. At 320 px the two buttons may wrap to two lines; no horizontal scroll. At ≥ 48rem: the brand, the wide nav (links in the body font, wrapping as needed) and the notifications button. The open menu is a themed panel. Opening it must not move the notifications button out of view. The menu items are at least 44 px high. The "≡" icon is drawn in CSS on `summary.site-menu-toggle::before` (three 2–3 px bars made with `box-shadow` or a gradient; `content: ""`), because the font has no "≡". The `<summary>` markup stays `<summary class="site-menu-toggle">Меню</summary>`. Hide the default disclosure marker (`list-style: none` and `::-webkit-details-marker { display: none; }`).
- **D11. One entry point for notifications.** The "Уведомления" item is removed from `templates/includes/site_nav_items.html`. The header button replaces it at every width, so the page has one notifications link and one counter instead of three. The button has `aria-current="page"` on `/notifications/`.
- **D12. "Все уведомления" link removed** from the home page. Reason: the header button and both card-title links already lead to the feed. A fourth link to the same page adds a tap target and no value, and the mockup has none.
- **D13. Stars.** Pure CSS (for example `body::before` or `.site-header::before` with `box-shadow` pixels in `--color-star-yellow`/`--color-star-lilac`), `content: ""` (pseudo-elements are not exposed to assistive technology), `pointer-events: none`, below the content (`z-index`). Only in the header area and in the side margins. Never over text or controls at 320, 360 and 1024 px. You choose the positions.
- **D14. Tap targets** ≥ 44×44 px: buttons, the menu toggle, the notifications button, menu items, floor switcher links (already), card-row title links (row height ≥ 44 px), the home action buttons, the file input button, the error-page button. Links inside running text are exempt (WCAG 2.5.8 inline exception).
- **D15. No transitions or animations.** If you add any `transition` or `animation`, also add `@media (prefers-reduced-motion: reduce)` that turns them off (test T-D7).
- **D16. Forms.** Light text on a dark field: `--color-field-bg` background, `--color-text` text, 3 px `--color-field-border` border, square corners, body font, minimum height 44 px. `input[type=file]::file-selector-button` gets the panel button look. `.errorlist` and `.message--error` use `--color-warn-text`. `.form` (also used for the login form, the staff queue filter, the announcement form and the chat form) is a panel with the double frame.
- **D17. Chat.** `.chat-message--own` and `.chat-message--other` look different in more than colour. Keep the existing side margins (base.css); also use a different frame or background tint (for example `--color-now-bg` on own messages). The meta line ("Вы", "Деканат · …", the student name) stays.
- **D18. Error templates.** 403 and 404 extend `base.html`. 500 is standalone: Django renders it with an empty context and the database may be down, so it must not extend `base.html` (base runs DB-backed tags for students). It uses only `{% load static %}`, `{% static %}` and plain HTML. The button on 500 links to `/`.

## Architecture / files

Python (small context changes; no models, no migrations):
- `notifications/feed.py`: `HomeSummary` gets a `student: StudentProfile` field. `home_summary()` gets an optional `now` argument (F1).
- `schedule/services.py`: new `today_schedule()` (F2).
- `schedule/views.py`: `TodayView` uses `today_schedule()` (F3).
- `core/views.py`: `HomeView` adds the day schedule to the context (F4).

Templates:
- `templates/base.html` (F5): favicon, new header.
- `templates/includes/site_nav_items.html`: remove the student "Уведомления" `<li>` (D11). Nothing else changes in it.
- New `templates/includes/icon_cap.html`, `templates/includes/icon_bell.html` (D9).
- `core/templates/core/home.html` (F6): rewritten.
- New `schedule/templates/schedule/includes/lesson_compact.html` (F7).
- `notifications/templates/notifications/feed.html`: add `id="deadlines"` to the deadlines `<section>` and `id="feed"` to the feed `<section>`. Nothing else.
- New `templates/403.html`, `templates/404.html`, `templates/500.html` (F8).
- Other page templates (see "Pages"): you may add CSS classes and wrapper elements (`<div class="card">`, `<section class="card">`) for styling. Do not change text, links, form fields, element ids, `data-*` attributes or the order of content. Every such change is listed in the REPORT.

Static:
- `static/css/tokens.css`, `static/css/base.css`, `static/css/theme.css` (D1–D17).
- New `static/img/favicon.svg` (D9).
- `static/fonts/*`: unchanged. `static/js/chat.js`: unchanged.

Docs:
- `README.md`: new "## Design" section (AC18), placed after "## Chat".

Tests: see the Test plan.

## Functions

### F1. `notifications/feed.py`

```python
@dataclass(frozen=True)
class HomeSummary:
    student: StudentProfile
    deadlines: list[DeadlineItem]
    news: list[FeedItem]


def home_summary(
    user: AbstractBaseUser | AnonymousUser, now: datetime | None = None
) -> HomeSummary | None:
```
- Purpose: also return the student profile (with `group__program` already loaded by `student_context`), so the home page needs no extra query for the group.
- Algorithm: `ctx = student_context(user, now)`; the rest stays. Return `HomeSummary(student=ctx.student, deadlines=deadlines, news=news)`. `StudentProfile` is already imported in this module.
- Callers: `core.views.HomeView` only (checked: no other caller and no test builds `HomeSummary` directly).
- Tests: T-F1a, T-F1b.

### F2. `schedule/services.py`

```python
def today_schedule(group_id: int, now: datetime) -> tuple[DaySchedule, TodayAnnotation]:
```
- Purpose: the shared "today" computation of the "Сегодня" page and the home page.
- Input: a group id and an aware datetime. Output: the day schedule for the Moscow-local date of `now`, and its annotation at the local time of `now`.
- Algorithm: `local = timezone.localtime(now)`; `day = day_schedule(local.date(), [group_id], today=local.date())`; `return day, annotate_today(day.items, local.time())`. Import `datetime` from `datetime` and `timezone` from `django.utils`.
- Edge cases: `now` just before or after Moscow midnight gives the local date (test with `now` = `2026-11-17 21:00 UTC`, which is `2026-11-18 00:00` in Moscow).
- Tests: T-F2a, T-F2b.

### F3. `schedule/views.py` `TodayView.get_context_data`

Replace the three lines that compute `now`, `day` and `annotation` with `day, annotation = today_schedule(self.profile.group_id, timezone.now())`. The context keys stay the same. Remove imports that are no longer used (`day_schedule`, `annotate_today`) only if ruff reports them. Covered by the existing schedule view tests.

### F4. `core/views.py` `HomeView.get_context_data`

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    now = timezone.now()
    summary = home_summary(self.request.user, now)
    context["summary"] = summary
    if summary is not None:
        day, annotation = today_schedule(summary.student.group_id, now)
        context["day"] = day
        context["annotation"] = annotation
    return context
```
- One `now` for both services, so the date of the cards and the lessons is the same at midnight.
- Access: unchanged (login required by the middleware; the role switch is in the template).
- Tests: T-H*.

### F5. `templates/base.html`

Exact header structure (classes and texts are tested; you may add classes and wrappers that do not change the listed markup):

```django
{% load static notifications_tags chat_tags %}<!doctype html>
…
  <link rel="icon" href="{% static 'img/favicon.svg' %}" type="image/svg+xml">
  {# the three stylesheet links stay as they are, in the same order #}
…
  <header class="site-header">
    <a class="site-brand" href="{% url 'core:home' %}">{% include "includes/icon_cap.html" %}<span class="site-title"><span class="site-title-line">Цифровой</span> <span class="site-title-line">деканат</span></span></a>
    {% if user.is_student %}{% notifications_badge as badge %}{% chat_unread_badge as chat_badge %}{% endif %}
    <nav class="site-nav site-nav--wide" aria-label="Основная навигация">
      {% block nav %}{% if user.is_authenticated %}{% include "includes/site_nav_items.html" %}{% endif %}{% endblock %}
    </nav>
    {% if user.is_authenticated %}
    <div class="site-header-actions">
      <div class="site-nav-compact">
        <details class="site-menu">
          <summary class="site-menu-toggle">Меню</summary>
          <nav class="site-nav" aria-label="Основная навигация">
            {% include "includes/site_nav_items.html" %}
          </nav>
        </details>
      </div>
      {% if user.is_student %}{% url 'notifications:feed' as notif_url %}<a class="btn site-notif" href="{{ notif_url }}"{% if request.path == notif_url %} aria-current="page"{% endif %}>{% include "includes/icon_bell.html" %}Уведомления{% if badge %}<span class="site-notif-count"><span class="visually-hidden">, непрочитанных: </span>{{ badge }}</span>{% endif %}</a>{% endif %}
    </div>
    {% endif %}
  </header>
```
- Keep the skip link, `<main id="main" class="site-main">`, the messages block and the footer text unchanged (tests check them). You may add classes to them.
- The title text is "Цифровой деканат" in mixed case; `text-transform: uppercase` in theme.css shows it in capitals. `.site-title-line` is `display: block` below 48rem and `inline` at ≥ 48rem.
- Do not use the class names `site-menu-badge` or anything containing `site-menu` for the button (the anonymous test checks that "site-menu" is absent).
- Add `.visually-hidden` (the standard clip pattern) to base.css.
- Tests: T-N*.

### F6. `core/templates/core/home.html`

```django
{% extends "base.html" %}
{% block content %}
{% if summary %}
  <h1>Сегодня</h1>
  <p class="page-sub">{{ day.date|date:"l, j E" }} · {{ summary.student.group.name }}</p>
  <section class="card" aria-labelledby="home-lessons">
    <h2 class="card-title" id="home-lessons">Занятия</h2>
    {% if day.items %}<ol class="lesson-list lesson-list--compact">{% for row in annotation.rows %}{% include "schedule/includes/lesson_compact.html" with item=row.item row=row %}{% endfor %}</ol>
    {% else %}<p class="card-empty">Сегодня занятий нет.</p>{% endif %}
  </section>
  <section class="card" aria-labelledby="home-deadlines">
    <h2 class="card-title" id="home-deadlines"><a class="card-title-link" href="{% url 'notifications:feed' %}#deadlines">Дедлайны<span aria-hidden="true"> →</span></a></h2>
    {% if summary.deadlines %}<ul class="card-rows">{% for d in summary.deadlines %}
      <li class="card-row"><a class="card-row-title" href="{% url 'notifications:feed' %}#deadline-{{ d.public_id }}" title="{{ d.title }}">{{ d.title }}</a><time class="card-row-label card-row-label--deadline" datetime="{{ d.deadline|date:'Y-m-d' }}">{{ d.label }}</time></li>
    {% endfor %}</ul>{% else %}<p class="card-empty">Ближайших дедлайнов нет.</p>{% endif %}
  </section>
  <section class="card" aria-labelledby="home-news">
    <h2 class="card-title" id="home-news"><a class="card-title-link" href="{% url 'notifications:feed' %}#feed">Новости<span aria-hidden="true"> →</span></a></h2>
    {% if summary.news %}<ul class="card-rows">{% for item in summary.news %}
      <li class="card-row"><a class="card-row-title" href="{% url 'notifications:feed' %}#{{ item.key }}" title="{{ item.title }}">{{ item.title }}</a><time class="card-row-label" datetime="{{ item.timestamp|date:'c' }}">{{ item.timestamp|date:"d.m" }}</time></li>
    {% endfor %}</ul>{% else %}<p class="card-empty">Новостей пока нет.</p>{% endif %}
  </section>
  <div class="home-actions home-actions--two">
    <a class="btn" href="{% url 'petitions:my_list' %}">Документы</a>
    <a class="btn" href="{% url 'chat:student' %}">Чат</a>
  </div>
{% elif user.is_deanery_staff %}
  <h1>Деканат</h1>
  <div class="home-actions home-actions--three">
    <a class="btn" href="{% url 'petitions:staff_queue' %}">Заявки</a>
    <a class="btn" href="{% url 'chat:staff_list' %}">Чаты</a>
    <a class="btn" href="{% url 'notifications:staff_announcements' %}">Объявления</a>
  </div>
{% else %}
  <h1>Цифровой деканат будущего</h1>
  <p>Прототип личного кабинета студента. Раздел в разработке.</p>
{% endif %}
{% endblock %}
```
Layout rules (base.css):
- `.card-row { display: flex; align-items: baseline; gap: …; }`.
- `.card-row-title { flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }`, with a line height or min-height that gives a row of at least 44 px.
- `.card-row-label { flex: none; white-space: nowrap; }`.
- `.home-actions--two { display: grid; grid-template-columns: 1fr 1fr; }` at every width (both buttons the same size).
- `.home-actions--three`: one column below 48rem ("Объявления" is 10 glyphs, about 110 px plus padding, which does not fit three in a row at 360 px); `repeat(3, 1fr)` at ≥ 48rem.
- Theme: dashed separators between rows (`2px dashed var(--color-border)`, none before the first row), deadline label in `--color-warn-text` bold, news date in `--color-muted`. "Дедлайны" and "Новости" look identical apart from that label colour.

### F7. `schedule/templates/schedule/includes/lesson_compact.html`

```django
<li class="lesson lesson--{{ item.kind }}{% if row.is_in_progress %} lesson--now{% endif %}">
  <p class="lesson-time"><time>{{ item.slot.start|time:"H:i" }}</time>–<time>{{ item.slot.end|time:"H:i" }}</time> · {{ item.slot.number }} пара{% if row.is_in_progress %} <span class="tag">идёт</span>{% endif %}</p>
  <p class="lesson-title">{{ item.lesson.discipline.name }}</p>
  <p class="lesson-meta">{{ item.lesson.get_lesson_type_display }} · {{ item.teacher.short_name }} · {% if item.is_happening %}<a class="room" href="{% url 'campusmap:room' item.room.code %}">ауд. {{ item.room.number }}</a>{% else %}<span class="room">ауд. {{ item.room.number }}</span>{% endif %}{% if item.is_changed %} <span class="lesson-change">{% if item.kind == "cancelled" %}отменено{% elif item.kind == "moved-out" %}перенесено на {{ item.moved_to_date|date:"j E" }}{% elif item.kind == "moved-in" %}перенесено с {{ item.moved_from_date|date:"j E" }}{% elif item.kind == "room-changed" %}аудитория изменена{% elif item.kind == "teacher-replaced" %}замена преподавателя{% endif %}</span>{% endif %}</p>
</li>
```
- The existing `.lesson--cancelled .lesson-title` / `.lesson--moved-out .lesson-title` line-through rule applies.
- The theme gives `.lesson-change` `--color-warn-text` bold and `.lesson-time` `--color-muted` (mockup).

### F8. Error templates

- `templates/404.html`: `{% extends "base.html" %}`, `{% block title %}Страница не найдена{% endblock %}`, `<h1>Страница не найдена</h1>`, `<p>Проверьте адрес или вернитесь на главную.</p>`, `<p><a class="btn" href="{% url 'core:home' %}">На главную</a></p>`.
- `templates/403.html`: the same with the title and `h1` "Доступ запрещён" and the text "У вас нет доступа к этой странице."
- `templates/500.html`: standalone `<!doctype html>`, `lang="ru"`, viewport meta, `<title>Ошибка сервера</title>`, the favicon and the three stylesheet links via `{% static %}`, a header with the cap and the title (same classes as base, no nav), `<main class="site-main"><h1>Ошибка сервера</h1><p>Что-то пошло не так. Попробуйте обновить страницу позже.</p><p><a class="btn" href="/">На главную</a></p></main>`, and the footer disclaimer. The cap is included with `{% include "includes/icon_cap.html" %}` (a plain template with no tags).

## Pages (theme each, no behaviour change; check each in the browser)

| Page | URL (demo data) | Roles |
|---|---|---|
| Login | `/login/` | anonymous |
| Home | `/` | student, staff, superuser |
| Profile | `/profile/` | student, staff |
| Schedule today / week | `/schedule/`, `/schedule/week/` | student |
| Staff schedule groups / group week | `/staff/schedule/`, a group week | staff |
| Grades report with an open `<details>` | `/grades/` | student |
| Requests: list, catalog, form with the file input (submit once with an error to see `.errorlist`), detail | `/requests/`, `/requests/new/`, a form, a detail | student |
| Staff requests: queue (filter form), detail (actions, reject textarea, comment form) | `/staff/requests/`, a detail | staff |
| Notifications feed (check `#deadlines` and `#feed` anchors) | `/notifications/` | student |
| Staff announcements (form + list + unpublish button) | `/staff/announcements/` | staff |
| Chat student / staff list / staff dialog (own vs other messages) | `/chat/`, `/staff/chats/`, a dialog | student, staff |
| Map, floor, room highlight | `/map/`, `/map/floor/2/`, `/map/room/<code>/` | student |
| Staff student list / detail | `/staff/students/`, a detail | staff |
| Django messages (for example after submitting a request or posting a chat message) | — | student |
| 404 (any unknown URL), 403 (student opens `/staff/requests/`) | — | student |
| 500: render `templates/500.html` once via `python manage.py shell` (`render_to_string("500.html")`) into `$TMPDIR/ui-500.html`, open it as a file URL | — | — |

Check each at 360×780 and 1024×768 (role file). Also check the home page and the header at 320×780 (AC8, D10). Look at the home page at 360 px for a student with a long deadline title (demo data has titles up to 35 characters; also try one temporary announcement with a 150-character title on your temporary database).

## Contrast (checked pairs; WCAG 2.x relative luminance)

| Foreground | Background | Ratio | Need |
|---|---|---|---|
| text `#f3ecff` | lightest sky `#4b2a86` / panel `#29184f` / darkest sky `#120a2a` | 9.24 / 13.45 / 16.56 | 4.5 |
| muted `#b8a6e8` | lightest sky / panel | 4.89 / 7.12 | 4.5 |
| heading `#ffd25e` | lightest sky / panel | 7.41 / 10.78 | 4.5 |
| link `#ffc46b` | lightest sky / panel | 6.77 / 9.84 | 4.5 |
| warn-text `#ff8a95` | lightest sky / panel | 4.72 / 6.87 | 4.5 |
| (rejected) `#ff6f7d` as text | lightest sky | 3.96 | 4.5, fails |
| orange `#ff9f2e` (logo, large) | lightest sky / panel | 5.19 / 7.55 | 3 |
| on-accent `#2b1300` | orange `#ff9f2e` / `#ffc04d` / `#f07a1a` | 8.57 / 10.79 / 6.27 | 4.5 |
| on-accent `#2b1300` | chip `#ff6f7d` | 6.54 | 4.5 |
| (rejected) white | chip `#ff6f7d` | 2.68 | 4.5, fails |
| text / muted | field `#170d33` | 15.99 / 8.46 | 4.5 |
| field border `#a58cf0` | lightest sky / panel / field | 3.85 / 5.61 / 6.66 | 3 |
| focus `#ffd25e` | lightest sky / panel / darkest sky | 7.41 / 10.78 / 13.27 | 3 |
| text / muted | current-lesson tint (`--color-now-bg` on panel, `#472b4f`) | 10.56 / 5.59 | 4.5 |
| text / muted | own-message tint (12% link colour on panel, `#422d57`) | 10.44 / 5.52 | 4.5 |

If you introduce another text/background pair (for example a map label colour or a message success colour), compute it with the same formula and add it to the REPORT.

## Feasibility check

1. Clean starting point: `git status --short` is empty; HEAD `59481cf Design: approved mockup and Press Start 2P font (OFL) for TASK-012`.
2. Referenced objects exist: `templates/base.html` (header, `notifications_badge`/`chat_unread_badge` tags, `site-menu`), `templates/includes/site_nav_items.html` (student "Уведомления" `<li>`), `core/views.py:HomeView`, `notifications/feed.py:home_summary` (line 109) and `HomeSummary` (line 104), `notifications/feed.py:student_context(user, now=None)` (line 19), `schedule/services.py:day_schedule` (line 233) and `annotate_today` (line 253), `schedule/views.py:TodayView` (line 22), `StudentRequiredMixin.profile`, `notifications/templates/notifications/feed.html` (sections with `aria-labelledby="deadlines-title"`/`"feed-title"`), URL names `core:home`, `notifications:feed`, `notifications:staff_announcements`, `petitions:my_list`, `petitions:staff_queue`, `chat:student`, `chat:staff_list`, `campusmap:room`. `User.is_student`/`is_deanery_staff` (`accounts/models.py:36,40`). `Teacher.short_name`, `ScheduleItem.is_happening/is_changed/kind/moved_to_date/moved_from_date` (`schedule/services.py:26-49`). Mockup and font files exist (`docs/design/`, `static/fonts/`).
3. New names are free: no `templates/403.html`/`404.html`/`500.html`, no `static/img/`, no `templates/includes/icon_*.html`, no `lesson_compact.html`, no `today_schedule` in `schedule/services.py`, no `id="deadlines"`/`id="feed"` in any template, no `.visually-hidden`, `.card`, `.btn`, `.tag`, `.site-brand`, `.site-notif` in `static/css/`. No migrations are planned.
4. Data and migrations: `python manage.py makemigrations --check --dry-run`: "No changes detected". The task adds no fields.
5. Tools: Python 3.12 `.venv`, Django 5.2.19, whitenoise 6.12, ruff 0.17.4. No new dependency. Browser automation is used by the UI coder per role file.
6. Framework capabilities: Django renders `403.html`/`404.html` with the request context and `500.html` with an empty context when `DEBUG=False` (tests run with `DEBUG=False`); `django.views.defaults.server_error` can be called directly in a test. Prototype (2026-11-17): `collectstatic` with `CompressedManifestStaticFilesStorage` into a temporary `STATIC_ROOT`, with a test CSS file `css/zz-proto.css` containing `url("../fonts/PressStart2P-Regular.ttf")`, took 0.29 s and rewrote the URL to `../fonts/PressStart2P-Regular.ccb1dfce06ad.ttf`. Font facts from the TTF tables: unitsPerEm 1000, advance width 1000 for every glyph; Cyrillic, "ё", "→", "…", "№" present, "≡" (U+2261) absent. Russian date format `{{ d|date:"l, j E" }}` renders "Вторник, 17 ноября".
7. Environment: no new env variables. The browser check runs on a temporary database (role file).
8. Verification is runnable on the current tree: `python manage.py check` (no issues), `makemigrations --check --dry-run` (no changes), `ruff check .` (passed), `ruff format --check .` (186 files formatted), `python manage.py test --parallel 1`: **Ran 1002 tests, OK** (log `/tmp/claude-501/test-20261117-122840.log`, 2026-11-17 ~23:28 MSK). Home query count today (measured on a seeded temporary DB, student1): 10 queries; `day_schedule` adds 3 (lessons, lesson groups, changes) plus 1 when changes exist (change lesson groups): 14 expected for AC12.
9. Conflicts: none. D11 (the nav item removed) and D12 (the "Все уведомления" link removed) are design decisions inside the request ("choose and justify" for D12; D11 avoids two identical notification links at ≥ 48rem, where the request keeps the button visible). The count chip text colour differs from the mockup for contrast (D4).
10. Assumptions / blockers: none.

## Test plan

Test data uses the existing helpers (`accounts.tests.helpers`, `schedule.tests.helpers`, `notifications.tests.helpers`, `chat.tests.helpers`), never `seed_demo`. Time-dependent tests use `FrozenClockMixin` with `frozen_now = "2026-11-11 11:00"` (a Wednesday; slot 2 10:40–12:10 is in progress; earlier than the real date so clock leaks fail).

### Traceability

| AC | Tests |
|---|---|
| AC1 | `core/tests/test_design.py::TokenTests::test_required_tokens`, `::test_no_colour_literals_outside_tokens` |
| AC2 | `core/tests/test_design.py::FontTests::*` |
| AC3 | `core/tests/test_design.py::ExternalResourceTests::*` |
| AC4 | `core/tests/test_design.py::LogoTests::*` |
| AC5, AC6, D11 | `core/tests/test_nav.py` (updated and new tests, below) |
| AC7, AC8, AC9, AC10 | `core/tests/test_home.py::*` |
| AC11 | `notifications/tests/test_views.py::FeedViewTests::test_section_anchors` |
| AC12 | `core/tests/test_home.py::HomeQueryTests::*` |
| AC13 | `core/tests/test_errors.py::*` |
| AC14, AC15, AC17 | visual self-check (UI coder) + the Team lead's screenshots; `core/tests/test_design.py::ThemeRuleTests::*` |
| AC16 | the contrast table above; `TokenTests::test_required_tokens` checks the values |
| AC18 | `core/tests/test_design.py::ReadmeTests::test_design_section` |
| AC19 | `core/tests/test_design.py::ExternalResourceTests::test_no_admin_templates`; `makemigrations --check` |
| F1 | `notifications/tests/test_feed.py::HomeSummaryStudentTests::*` |
| F2, F3 | `schedule/tests/test_services.py::TodayScheduleTests::*` + existing `schedule/tests/test_views.py` |

### Access matrix (`GET /`, and error pages)

| Actor | `/` | unknown URL | `/staff/requests/` | `/requests/` |
|---|---|---|---|---|
| anonymous | 302 → `/login/?next=/` (existing `test_home_requires_login`) | 404 with `404.html` (`test_404_anonymous`) | 302 (not changed; not retested) | 302 (not retested) |
| student with profile | 200, student cards (`test_student_home_cards`) | 404 themed (`test_404_student`) | 403 themed (`test_403_student_on_staff_page`) | 200 (not retested) |
| student without profile | 200, placeholder (`test_student_without_profile_placeholder`) | — | — | — |
| staff | 200, staff buttons (`test_staff_home_buttons`) | — | 200 | 403 themed (`test_403_staff_on_student_page`) |
| superuser | 200, placeholder (`test_superuser_placeholder`) | — | — | — |

"Own vs other student data" does not apply: the home page shows only the logged-in student's group (`test_other_group_lessons_hidden`).

### New tests

`core/tests/test_design.py` (new; `SimpleTestCase` unless noted; read files with `Path(settings.BASE_DIR) / …`):
- `TokenTests::test_required_tokens`: every token name in D3 appears in tokens.css as `--name:`; the values of `--color-warn-text` (`#ff8a95`), `--color-field-border` (`#a58cf0`), `--color-on-accent` (`#2b1300`), `--color-text` (`#f3ecff`) are exactly as in D3.
- `TokenTests::test_no_colour_literals_outside_tokens`: base.css and theme.css have no match for `#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(`.
- `FontTests::test_font_files_unchanged`: SHA-256 of `static/fonts/PressStart2P-Regular.ttf` is `034c77f1f05ec89421e4a63f0e3a4ca1ecf852cc6d2bf611f126f275728e017d`; of `static/fonts/OFL.txt` is `705960c3281a5765ecc0b59bd4ed7ca59eed165748076bc2fc3e8fdbfeb944b0`.
- `FontTests::test_font_found_by_staticfiles`: `django.contrib.staticfiles.finders.find("fonts/PressStart2P-Regular.ttf")` and `find("fonts/OFL.txt")` are not `None`; `static/fonts/` contains exactly these two files.
- `FontTests::test_font_face_rule`: theme.css matches `@font-face\s*\{[^}]*font-family:\s*"Press Start 2P"[^}]*url\("\.\./fonts/PressStart2P-Regular\.ttf"\)[^}]*\}` and the block contains `font-display: swap`; tokens.css defines `--font-pixel` starting with `"Press Start 2P"`.
- `FontTests::test_manifest_rewrites_font_url`: with `override_settings(STATIC_ROOT=<tempdir>, STORAGES={**settings.STORAGES, "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}})`, `call_command("collectstatic", interactive=False, verbosity=0)`; read `staticfiles.json`; the processed `css/theme.css` (hashed name from the manifest) contains the hashed font name from the manifest. Remove the temp dir with `self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)` (`tempfile.mkdtemp()`; this is a temp dir created by the test, not project data).
- `ExternalResourceTests::test_css_has_no_external_urls`: for every `static/css/*.css`: no `@import`, no `https://`, no `http://`, and every `url(` matches `url\("?\.\./`.
- `ExternalResourceTests::test_templates_have_no_external_urls`: for every `*.html` under `templates/` and `*/templates/` of the project apps (not `.venv`, not `docs/`): no `https://`; `http://` appears only inside `http://www.w3.org/2000/svg`; no `fonts.googleapis`/`fonts.gstatic`.
- `ExternalResourceTests::test_scripts_only_in_chat`: the set of template paths containing `<script` is exactly `{chat/templates/chat/student.html, chat/templates/chat/staff_dialog.html}`; `sorted(os.listdir("static/js")) == ["chat.js"]`.
- `ExternalResourceTests::test_no_admin_templates`: `templates/admin` does not exist.
- `LogoTests::test_favicon_file`: `static/img/favicon.svg` exists, contains `<svg`, `shape-rendering="crispEdges"`, `<rect`, and no `<script`, `href=`, `<image`.
- `LogoTests::test_icon_includes`: `templates/includes/icon_cap.html` and `icon_bell.html` contain one `<svg`, `aria-hidden="true"`, `focusable="false"`, `shape-rendering="crispEdges"`, `fill="currentColor"`, and no `xmlns`.
- `LogoTests::test_base_links_favicon` (`TestCase`): the login page contains `<link rel="icon" href="/static/img/favicon.svg" type="image/svg+xml">` and `class="site-brand"`, `<span class="site-title-line">Цифровой</span>`.
- `ThemeRuleTests::test_focus_visible`: theme.css contains `:focus-visible` with `outline` and `var(--color-focus)`.
- `ThemeRuleTests::test_reduced_motion_if_motion`: if `transition` or `animation` occurs in any CSS file, that file contains `prefers-reduced-motion`.
- `ThemeRuleTests::test_card_row_ellipsis`: base.css has a `.card-row-title` rule with `white-space: nowrap`, `overflow: hidden`, `text-overflow: ellipsis`, `min-width: 0`; a `.card-row-label` rule with `white-space: nowrap` and `flex: none` (or `flex-shrink: 0`); `.card-row` with `display: flex`.
- `ThemeRuleTests::test_home_actions_grid`: base.css has `.home-actions--two` with `grid-template-columns: 1fr 1fr`.
- `ThemeRuleTests::test_map_highlight_not_hue_only`: theme.css has a rule whose selector contains `.map-current` and which sets `stroke-width` and uses `var(--color-map-highlight)`.
- `ThemeRuleTests::test_body_font_for_text`: tokens.css `--font-body` is unchanged (`system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`); theme.css does not set `font-family: var(--font-pixel)` (or `--font-heading`) on `body`, `p`, `li`, `input`, `select`, `textarea`, `table` or `h3` selectors (regex on each rule: a selector list containing one of these as a whole compound and a pixel font declaration → fail).
- `ReadmeTests::test_design_section`: README.md contains `## Design`, `Press Start 2P`, `SIL Open Font License`, `static/fonts/OFL.txt`, and the word `own` near "logo" (assert the exact sentence you write, for example "The logo and the favicon are our own pixel drawing").

`core/tests/test_home.py` (new; `FrozenClockMixin, TestCase`, `frozen_now = "2026-11-11 11:00"`). `setUpTestData`: faculty, group "GX", another group "GY", student `stu` in GX (with profile), staff `stf`, superuser, student `noprof` (role student, no profile); rooms `room-101`, `room-102`, `room-103`; lesson A: GX, weekday 2, slot 1, room 101, discipline "Английский язык", type seminar; lesson B: GX, weekday 2, slot 2, room 102, discipline "Микроэкономика"; a `ROOM_CHANGED` change for lesson B on 2026-11-11 to room 103 (`save_lesson_change`); lesson C: GY only, weekday 2, slot 3, discipline "Чужая дисциплина".
- `HomeStudentTests::test_student_home_cards`: 200; contains `<h1>Сегодня</h1>`, `<p class="page-sub">Среда, 11 ноября · GX</p>`, the three `id="home-lessons"`, `id="home-deadlines"`, `id="home-news"` in this order, and the two buttons `<a class="btn" href="/requests/">Документы</a>` before `<a class="btn" href="/chat/">Чат</a>`, both after `id="home-news"`.
- `::test_lessons_card`: `response.context["annotation"].rows` has 2 rows; content contains `Английский язык`, `Микроэкономика`, `<span class="tag">идёт</span>` exactly once and after "10:40"; `href="/map/room/room-103/">ауд. 103</a>`; `<span class="lesson-change">аудитория изменена</span>`.
- `::test_other_group_lessons_hidden`: "Чужая дисциплина" not in the content.
- `::test_no_lessons_empty_state` (separate class with `frozen_now = "2026-11-15 11:00"`, a Sunday): contains `<p class="card-empty">Сегодня занятий нет.</p>` and no `lesson-list--compact`.
- `::test_cancelled_lesson_not_linked`: add a `CANCELLED` change for lesson A on 2026-11-11; the lesson A row has `<span class="room">ауд. 101</span>` and `отменено`, and no link to `/map/room/room-101/`.
- `::test_card_titles_link_to_feed_anchors`: contains `<a class="card-title-link" href="/notifications/#deadlines">Дедлайны<span aria-hidden="true"> →</span></a>` and the same for `#feed` / "Новости".
- `::test_deadline_row_markup`: an announcement with deadline 2026-11-12 and a 150-character title; the row is `<li class="card-row"><a class="card-row-title" href="/notifications/#deadline-<uuid>" title="<full title>"><full title></a><time class="card-row-label card-row-label--deadline" datetime="2026-11-12">завтра</time></li>` (build the expected string from the object; the title has no characters that HTML-escape).
- `::test_news_row_markup`: a news announcement published 2026-11-10 10:00 Moscow; its row contains `title="…"` and `<time class="card-row-label" datetime="2026-11-10T10:00:00+03:00">10.11</time>`.
- `::test_empty_cards`: no announcements: `Ближайших дедлайнов нет.` and `Новостей пока нет.` each inside `<p class="card-empty">`.
- `::test_all_notifications_link_removed`: `Все уведомления` not in content.
- `::test_home_still_does_not_mark_read`: covered by the existing `HomeSummaryTests::test_home_does_not_mark_read`; no new test.
- `HomeOtherRolesTests::test_staff_home_buttons`: `<h1>Деканат</h1>` and the three `<a class="btn" href="…">` in the order Заявки, Чаты, Объявления; no `id="home-lessons"`.
- `::test_superuser_placeholder` and `::test_student_without_profile_placeholder`: "Раздел в разработке" present; no `class="btn"` inside `<main`.
- `HomeQueryTests::test_exact_queries`: student `stu` (lessons A and B with the change), one deadline announcement, one news announcement, one unread staff chat message (`chat.tests.helpers`): `with self.assertNumQueries(14): self.client.get("/")`.
- `::test_queries_constant_in_lessons`: count with lesson B only (create lesson A in the test after the first measurement) equals the count with A, B and a third lesson (slot 4) — all with the room change present.
- `::test_queries_constant_in_deadlines`: count with 0 deadlines equals the count with 4 deadlines (same lessons).

`core/tests/test_errors.py` (new; `TestCase`):
- `test_404_anonymous`: `GET /no-such-page/` → 404, `assertTemplateUsed("404.html")`, contains `<h1>Страница не найдена</h1>` and `<a class="btn" href="/">На главную</a>`.
- `test_404_student`: the same while logged in as a student; the header button `class="btn site-notif"` is present (base.html is used).
- `test_403_student_on_staff_page`: student `GET /staff/requests/` → 403, `403.html` used, `<h1>Доступ запрещён</h1>`.
- `test_403_staff_on_student_page`: staff `GET /requests/` → 403, `403.html` used.
- `test_500_standalone`: `response = server_error(RequestFactory().get("/"))` inside `assertNumQueries(0)`; status 500; content contains `<h1>Ошибка сервера</h1>`, `href="/static/css/theme.css"`, `rel="icon"`; no `{%`; and the file `templates/500.html` does not contain `{% extends`.

`core/tests/test_nav.py` (update and add; give the reason in a comment `# TASK-012: …` above each changed assertion):
- `test_student_menu`: the expected list loses `"/notifications/"` (D11).
- `test_menu_summary_unchanged`: keep the existing assertion `<summary class="site-menu-toggle">Меню</summary>` (it is in `test_student_menu`; no change).
- `NavBadgeTests::test_badge_outside_menu` → rename to `test_notifications_button_with_count`: content contains `<span class="site-notif-count"><span class="visually-hidden">, непрочитанных: </span>1</span>`; the button `<a class="btn site-notif" href="/notifications/">` is after `</details>` and outside `_wide(content)`; `"/notifications/"` is not in `_hrefs(_wide(content))` or `_hrefs(_menu(content))`.
- `test_no_badge_without_unread`: the button is present (`class="btn site-notif"`) and `site-notif-count` is absent.
- `test_no_badge_for_staff`: `site-notif` absent for staff (with an unread announcement existing).
- New `test_no_button_for_superuser_and_anonymous`: `site-notif` absent on `/profile/` for the superuser and on `/login/` for anonymous.
- New `test_button_current_on_feed`: on `/notifications/` the content contains `<a class="btn site-notif" href="/notifications/" aria-current="page">` and `aria-current="page"` occurs exactly once.
- New `test_badge_cap_label`: with `badge_for_user` patched in `notifications.templatetags.notifications_tags` to return `"50+"`, the chip shows `50+`.
- `test_anonymous_unchanged`, `test_badge_computed_once`, `test_current_page_marked`, `test_logout_form_in_both_lists`, `test_staff_menu`, `test_superuser_menu`: unchanged and must pass.

Existing tests to update (each with a `# TASK-012: …` comment):
- `chat/tests/test_views.py::NavTests::test_badge_includes_chat_reply`: assert the chip markup from `test_notifications_button_with_count` with count 1 instead of the old `site-menu-badge` link.
- `notifications/tests/test_views.py::NavTests::test_student_nav_with_count`: assert the chip with `2` instead of `Уведомления (2)`. `test_student_nav_without_count`: unchanged (it still passes: "Уведомления" is in the button, "Уведомления (" is absent).
- `notifications/tests/test_views.py::HomeSummaryTests::test_student_summary`: "Ближайшие дедлайны" → `id="home-deadlines"` and the card title text "Дедлайны".
- `notifications/tests/test_views.py::HomeSummaryTests::test_news_heading`: the expected markup becomes the `#feed` card-title link (F6); keep `assertNotIn("Новости деканата", …)`.
- `notifications/tests/test_views.py::HomeSummaryTests::test_staff_no_summary`: staff now gets the staff home; assert `<h1>Деканат</h1>` and no `id="home-deadlines"` instead of "Раздел в разработке".
- `notifications/tests/test_views.py::QueryCountTests::test_home_queries_constant` / `test_home_queries_same_with_deadlines`: unchanged and must pass.
- Any other failing test: fix the markup first; change a test only if the failure is caused by an intended markup change from this spec, and list it in the REPORT with the reason.

Other new tests:
- `notifications/tests/test_views.py::FeedViewTests::test_section_anchors`: the feed page contains `<section id="deadlines" aria-labelledby="deadlines-title">` and `<section id="feed" aria-labelledby="feed-title">`.
- `notifications/tests/test_feed.py::HomeSummaryStudentTests::test_summary_has_student` (`FrozenClockMixin, TestCase`): `home_summary(student_user).student.pk == student_user.student_profile.pk`, and accessing `.student.group.name` makes 0 queries (`assertNumQueries(0)`).
- `::test_summary_uses_given_now`: with `now = moscow("2026-11-12 10:00")` while the frozen clock is `2026-11-11 12:00`, an announcement with deadline 2026-11-11 is not in `deadlines` (it is in the past for the given `now`).
- `schedule/tests/test_services.py::TodayScheduleTests::test_matches_today_view_logic`: lessons on weekday 2; `today_schedule(group.pk, moscow("2026-11-11 11:00"))` returns a day with `date == date(2026, 11, 11)`, `is_today` True, and `annotation.in_progress` is the slot-2 item.
- `::test_uses_moscow_local_date`: `now = datetime(2026, 11, 17, 21, 0, tzinfo=UTC)` (Moscow midnight 2026-11-18) → `day.date == date(2026, 11, 18)`.

### Settings branches

`DEBUG=True` vs `False`: error templates are used only with `DEBUG=False`; tests run with `DEBUG=False` (Django's runner), which covers production. The manifest storage branch is covered by `test_manifest_rewrites_font_url`. No other settings change.

### Edge cases

- A 150-character deadline title (ellipsis, `title` attribute) — `test_deadline_row_markup` + visual check at 320/360.
- No lessons (Sunday), cancelled lesson (no map link), room change (link to the new room), current lesson tag.
- Badge "50+" chip.
- Moscow midnight in `today_schedule`.
- 500 without request context and without database.

## Implementation order

1. Read the mockup (HTML and JPG). Start the app on a temporary database (role file) and take "before" screenshots of the home page at 360 px for reference.
2. F1, F2, F3, F4 (Python). Run `python manage.py test schedule notifications core` and save the log.
3. `tokens.css` (D3) and `@font-face` + base theme (gradient, text colours, fonts, headings) in `theme.css`. Write `test_design.py::TokenTests`, `FontTests`, `ExternalResourceTests`.
4. Icons, favicon and the header (F5, D9, D10, D11). Update `test_nav.py`, the chat and notifications nav tests. Check the header at 320/360/1024 for a student and staff.
5. Home page (F6, F7), feed anchors. Write `test_home.py`, update the notifications home tests. Check at 320/360/1024.
6. Cards, buttons, tags, forms, messages, chat, schedule, grades, requests, notifications, map (D6–D17). Check every page in the "Pages" table.
7. Error templates (F8) and `test_errors.py`.
8. README "## Design" and `ReadmeTests`. `ThemeRuleTests`, `LogoTests`.
9. Full verification (below). Visual self-check of every page. REPORT.

## Verification

```bash
source .venv/bin/activate
python manage.py check
DEBUG=false ALLOWED_HOSTS=example.com ADMIN_URL=ci-staff-panel/ SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop python manage.py check --deploy --fail-level WARNING
python manage.py makemigrations --check --dry-run
python manage.py test --parallel 1 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log"
python scripts/run_tests_at.py 2026-11-18T00:00:00 2>&1 | tee "$TMPDIR/test-midnight-$(date +%Y%m%d-%H%M%S).log"
ruff check <the Python files of this task>
ruff format --check <the Python files of this task>
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
git status --short
```
- Never run `ruff format .`; never format `docs/`.
- If any test run fails or stalls, even once, put the test name, the Moscow time and the traceback excerpt into the REPORT.
- The visual self-check table (role file) covers every row of the "Pages" table at 360 and 1024 px, plus the home page and header at 320 px.

## Risks

- **Test churn.** The header and home markup change. Only the tests listed above may change, each with a `# TASK-012:` reason. Any other test change must be explained in the REPORT.
- **Contrast regressions** if a coral text uses `--color-warn` instead of `--color-warn-text`, or if text sits on an orange or coral background other than with `--color-on-accent`. Check every new pair.
- **Pixel font overflow.** Long Russian words in `h1` at 320 px (D5). `overflow-wrap: anywhere` prevents horizontal scroll; check visually.
- **500 page** must not touch the database or the request; it is standalone (D18).
- **Font licence.** The TTF is used unmodified (SHA-256 test). Do not subset, convert to WOFF2 or rename it.
- **Stars over content** on narrow screens. Check 320 and 360 px.
- **Query count.** The home page goes from 10 to 14 queries. Do not add per-lesson queries (for example `item.lesson.groups.all` in the compact include).
