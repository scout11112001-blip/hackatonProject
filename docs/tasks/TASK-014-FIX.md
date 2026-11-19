# TASK-014-FIX: A separator dot never starts a line in request lists (and other lists, amendment 1)

Assignee: **UI coder** (thr_pgcwc2dwnn). Request: Team lead, approved by the user (found at 360 px on 19.11).

## Goal

In the request pages, a separator "·" never starts a line, at any width and any title length. Rows stay readable at 360 px and 1024 px. No JavaScript.

Problem (screenshot `docs/process/screenshots/2026-11-19_68_my-requests-subject_student1.jpg`): `my_list.html` and `staff_queue.html` write each part on its own template line as `· part`, so the HTML has a normal space (newline + indentation) right before every dot. The browser may break there, and the next line starts with "· № 399ee6e5 · …".

## Acceptance criteria

- AC1. **Separator rule** for every row this task touches: the dot is the last character of the preceding part, glued to it with a no-break space (`&nbsp;·`), and is followed by one normal space. There is never a normal space, tab or newline directly before a "·". Result: a line may end with "·" but never starts with it.
- AC2. **Student list** (`petitions/templates/petitions/my_list.html`): each row has the title link on its own line (block), then one details line: `№ <short id>&nbsp;· <created date>&nbsp;· <status>&nbsp;· готовность: <date>`.
- AC3. **Staff queue** (`petitions/templates/petitions/staff_queue.html`): each row has the student name link on its own line, then the request title (`petition.display_name`) on its own line, then one details line: `<group>&nbsp;· <created date>&nbsp;· <status>&nbsp;· файлов: N`.
- AC4. **Catalog** (`petitions/templates/petitions/catalog.html`): no separators at all. Each type is one block: the name link, the description (if any) on its own line, then "Срок: до N рабочих дней" on its own line. The em dash "— description" and "· Срок" are removed.
- AC5. **Request detail includes** (same pattern, same pages): `petitions/templates/petitions/includes/history.html` and `includes/comments.html` follow the rule of AC1 (`date&nbsp;· status&nbsp;· actor`, `author&nbsp;· date&nbsp;· text`).
- AC6. Short bounded details (the number, dates, status, "готовность: …", "файлов: N", the group) may be kept on one line with `white-space: nowrap` (D3); unbounded text (titles, names, comment text) wraps normally. No horizontal scroll at 320, 360 and 1024 px, even with a 150-character subject.
- AC7. Screen readers read the same words in the same order as today (the dots stay in the text; no `aria-hidden` needed; nothing is moved into CSS `content`).
- AC8. The information shown and the links are unchanged (same hrefs, same texts apart from the removed "— " and the separators' spacing). Existing tests pass; new tests guard AC1–AC4.

## Amendment 1 (Team lead, approved by the user, 19.11)

The same rule (AC1: `&nbsp;·` + one normal space, never whitespace before "·") applies to every "·" in these templates too:
- `chat/templates/chat/staff_list.html` (row: name link, group, time, "новых: N")
- `chat/templates/chat/_message.html` (`chat-meta`: "Деканат · <short name>" and " · <time>")
- `accounts/templates/accounts/student_list.html` (row: name link · group, course)
- `schedule/templates/schedule/staff_group_list.html` (row: group link · programme, course)
- `notifications/templates/notifications/feed.html` and `notifications/templates/notifications/staff_list.html` (`feed-meta`)
- `academics/templates/academics/includes/discipline.html` (the `<summary>` line)
- `schedule/templates/schedule/includes/lesson_compact.html` (`lesson-time` and `lesson-meta`)

See "Amendment 1: markup" below. `_message.html` is also the fragment returned to the chat polling (`static/js/chat.js`, unchanged): keep the `<li>` element, its classes, `id="m-<pk>"` and `data-message-id`; change only the text separators inside `chat-meta`. The JS selects only `li[data-message-id]` and `#chat-messages` (checked: `static/js/chat.js:4-54`).

## Out of scope

- Templates not listed in this spec. Short lines that do not wrap at 360 px stay as they are: `schedule/templates/schedule/today.html` (date · group), `core/templates/core/home.html` (`page-sub`, asserted exactly by `core/tests/test_home.py:84`), `schedule/templates/schedule/includes/lesson_item.html` (time line), `chat/templates/chat/staff_dialog.html` (name · group under the `h1`).
- The form's "Обязательное поле." for an empty comment (accepted by the user).
- New features, colours, fonts.

## Design decisions

- **D1. Fix in the text, not in CSS pseudo-elements.** A dot drawn by `::before` of the next part would still start the line when that part wraps; `::after` of the previous part cannot be glued to it across a wrap of a long part. A no-break space before the dot glues the dot to the end of the previous part in the line-breaking algorithm (also across inline element boundaries), and the normal space after the dot remains the only break point. It works for any length and needs no extra CSS.
- **D2. Titles on their own line.** The request title can be 170 characters ("Другая справка: " + 150). Putting it on its own line (block link) makes the details line short and scannable; the link keeps the 44 px tap height (existing rule `.petition > a { display: inline-block; min-height: 2.75rem; … }` — change it to `display: block` for these rows, see Architecture).
- **D3. Optional nowrap for bounded parts.** Wrap each bounded part in `<span class="meta-item">…</span>` with `.meta-item { white-space: nowrap; }` (base.css), so "19 ноября 2026" or "готовность: 26 ноября 2026" do not split. The dot and the no-break space stay *inside* the preceding `meta-item` span (`<span class="meta-item">№ 399ee6e5&nbsp;·</span> <span class="meta-item">…`). The longest bounded part ("готовность: 26 сентября 2026", 28 characters) fits the 360 px card. Do not use `meta-item` for unbounded text.
- **D4. Catalog without separators.** Three short blocks read better on a phone than one long sentence, and there is nothing to separate.

## Architecture / files

Templates (exact structure; class names are tested):

`petitions/templates/petitions/my_list.html`, row:
```django
<li class="petition">
  <a class="petition-title" href="{% url 'petitions:detail' petition.public_id %}">{{ petition.display_name }}</a>
  <p class="petition-meta"><span class="meta-item">№ {{ petition.short_id }}&nbsp;·</span> <span class="meta-item">{{ petition.created_at|date:"j E Y" }}&nbsp;·</span> <span class="meta-item"><span class="status status--{{ petition.status }}">{{ petition.get_status_display }}</span>&nbsp;·</span> <span class="meta-item">готовность: {{ petition.expected_ready_date|date:"j E Y" }}</span></p>
</li>
```

`petitions/templates/petitions/staff_queue.html`, row:
```django
<li class="petition">
  <a class="petition-title" href="{% url 'petitions:staff_detail' petition.public_id %}">{{ petition.student.full_name }}</a>
  <p class="petition-subject">{{ petition.display_name }}</p>
  <p class="petition-meta"><span class="meta-item">{{ petition.student.group.name }}&nbsp;·</span> <span class="meta-item">{{ petition.created_at|date:"j E Y" }}&nbsp;·</span> <span class="meta-item"><span class="status status--{{ petition.status }}">{{ petition.get_status_display }}</span>&nbsp;·</span> <span class="meta-item">файлов: {{ petition.attachment_count }}</span></p>
</li>
```

`petitions/templates/petitions/catalog.html`, each type (both sections; keep the `{% empty %}` texts):
```django
<div class="catalog-item">
  <a class="catalog-title" href="{% url 'petitions:submit' type.pk %}">{{ type.name }}</a>
  {% if type.description %}<p class="catalog-desc">{{ type.description }}</p>{% endif %}
  <p class="catalog-term">Срок: {{ type.term_label }}</p>
</div>
```

`petitions/templates/petitions/includes/history.html`, item:
```django
<li>{{ change.created_at|date:"j E Y H:i" }}&nbsp;· {% if change.from_status %}{{ change.get_from_status_display }} → {% endif %}{{ change.get_to_status_display }}&nbsp;· {% if change.actor.role == "staff" %}{{ change.actor.staff_profile.full_name }}{% elif change.actor.role == "student" %}Студент{% else %}Администратор{% endif %}{% if change.comment %}<br>{{ change.comment }}{% endif %}</li>
```

`petitions/templates/petitions/includes/comments.html`, item:
```django
<li>{% if comment.author.role == "staff" %}{{ comment.author.staff_profile.full_name }}{% else %}Сотрудник{% endif %}&nbsp;· {{ comment.created_at|date:"j E Y H:i" }}&nbsp;· {{ comment.text }}</li>
```
Keep each `<li>` on one template line (a template line break before "·" would reintroduce a normal space).

CSS (`static/css/base.css`, layout only; colours unchanged):
- `.meta-item { white-space: nowrap; }`
- `.petition-title`, `.catalog-title`: `display: block;` (replace `display: inline-block` for `.petition > a` in the existing rule at `base.css:761`, or add a more specific rule after it), keep `min-height: 2.75rem` and the padding so the tap target stays ≥ 44 px.
- `.petition-meta`, `.petition-subject`, `.catalog-desc`, `.catalog-term`: `margin: 0;` (the existing `.petition p { margin: 0; }` already covers rows); small spacing between catalog items (`.catalog-item + .catalog-item { margin-top: var(--space-3); }`).
- You may give `.petition-meta` and `.catalog-term` the muted colour via an existing token in theme.css (optional; check contrast: `--color-muted` on the panel is 7.12:1).

No Python changes.

### Amendment 1: markup

Keep each changed line as one template line (no newline or indentation before "·"). Unbounded parts (names, programme names, tags, audience labels, discipline names) wrap normally; you may wrap short bounded parts (dates, "новых: N", "N курс", percent) in `<span class="meta-item">` with the dot inside the span, as in D3.

- `chat/staff_list.html` row:
  `<li><a href="…">{{ d.student.full_name }}</a>&nbsp;· {{ d.student.group.name }}&nbsp;· {{ d.last_message_at|date:"d.m.Y H:i" }}{% if d.unread %}&nbsp;· <strong>новых: {{ d.unread }}</strong>{% endif %}</li>`
- `chat/_message.html` meta:
  `<p class="chat-meta"><strong>{% if m.author_role == "staff" %}Деканат&nbsp;· {{ m.author.staff_profile.short_name }}{% elif viewer_is_student %}Вы{% else %}{{ student_name }}{% endif %}</strong>&nbsp;· <time …>…</time></p>`
- `accounts/student_list.html` row (one line inside `<li>`):
  `<li><a href="…">{{ student.full_name }}</a>&nbsp;· {{ student.group.name }}, {{ student.course }} курс</li>`
- `schedule/staff_group_list.html` row:
  `<li><a href="…">{{ group.name }}</a>&nbsp;· {{ group.program.name }}, {{ group.course }} курс</li>`
- `notifications/feed.html` meta:
  `<p class="feed-meta">{% if item.is_new %}<strong>Новое</strong>&nbsp;· {% endif %}{{ item.tag }}&nbsp;· <time …>…</time>{% if item.audience_label %}&nbsp;· {{ item.audience_label }}{% endif %}</p>`
- `notifications/staff_list.html` meta:
  `<p class="feed-meta">{{ a.audience_label }}&nbsp;· {{ a.published_at|date:"d.m.Y H:i" }}&nbsp;· {% if a.is_published %}Опубликовано{% else %}Снято с публикации {{ a.unpublished_at|date:"d.m.Y H:i" }}{% endif %}</p>`
- `academics/includes/discipline.html` summary (one template line inside `<summary>`):
  `<summary><strong>{{ d.item.discipline.name }}</strong>&nbsp;· {{ d.item.get_assessment_form_display }}&nbsp;· Итог: {% if d.effective %}{{ d.effective.get_result_display }}{% else %}нет{% endif %}{% if d.is_debt %}&nbsp;· <strong>Задолженность</strong>{% endif %}&nbsp;· Посещаемость: {% if d.attendance.percent is not None %}{{ d.attendance.percent }}%{% else %}—{% endif %}</summary>`
- `schedule/includes/lesson_compact.html`: in `lesson-time` replace ` · {{ item.slot.number }} пара` with `&nbsp;· {{ item.slot.number }} пара`; in `lesson-meta` replace both ` · ` with `&nbsp;· `. Nothing else in the line changes (the room link, `lesson-change` span and the "идёт" tag stay exactly as they are; `core/tests/test_home.py` asserts them).

## Feasibility check

1. Clean starting point: `git status --short` shows only ` M plan.md` (Team lead). HEAD `1414de1 TASK-014: …`.
2. Referenced objects exist: the five templates above (current markup read on 19.11; `my_list.html:9-13` and `staff_queue.html:28-33` put "·" at the start of template lines; `catalog.html` uses "— description · Срок: {{ type.term_label }}"; `includes/history.html:5-7` and `includes/comments.html:5-7` the same pattern), `Petition.display_name`, `short_id`, `RequestType.term_label`, CSS rules `base.css:189-202` (`.petition-list`, `.petition`, `.petition p`), `base.css:761` (`.petition > a { display: inline-block; min-height: 2.75rem; padding-block: 0.625rem; }`), theme panels `theme.css:313`.
3. New names are free: `.meta-item`, `.petition-title`, `.petition-meta`, `.petition-subject`, `.catalog-item`, `.catalog-title`, `.catalog-desc`, `.catalog-term` (no match in `static/css/` or templates).
4. Data and migrations: none; `makemigrations --check`: "No changes detected".
5. Tools: no new dependency; headless Chromium via `bb browser-automation` for the visual check (role file).
6. Framework: Django autoescaping is unchanged; `&nbsp;` is a literal entity in the template. CSS line breaking treats U+00A0 as non-breaking, also across inline element boundaries (UAX #14; the existing chat and lesson markup already rely on NBSP in `Teacher.short_name`).
7. Environment: none.
8. Verification on the current tree: `check` (no issues), `makemigrations --check` (no changes), `ruff check .` (passed), `ruff format --check .` (193 files formatted), `python manage.py test --parallel 1`: **Ran 1122 tests, OK** (log `/tmp/claude-501/test-20261119-043501.log`, 2026-11-19 ~15:35 MSK). Existing tests that read these pages assert only substrings that stay (escaped display names, "Срок: до N …", "не больше 3 файлов"); none asserts the old " · " joins (checked with `grep` in `petitions/tests/`).
9. Conflicts: none. Amendment 1 (19.11): the 8 added templates were read; every "·" in them is listed above. Tests that assert these separators: only `chat/tests/test_views.py:294` (`assertIn("Деканат ·", content)`) — update it (see Test plan). `academics/tests/test_views.py:209` asserts "Задолженность" (stays). `core/tests/test_home.py` asserts the room link and `lesson-change` span (unchanged by the edit). `static/js/chat.js` uses only `[data-chat-poll-url]`, `#chat-messages`, `[data-chat-status]`, `li[data-message-id]`.
10. Assumptions / blockers: none.

## Test plan

### Traceability

| AC | Tests |
|---|---|
| AC1 | `petitions/tests/test_views.py::SeparatorTests::test_no_space_before_dot_in_lists`, `::test_no_space_before_dot_in_detail` |
| AC2 | `SeparatorTests::test_student_row_structure` |
| AC3 | `SeparatorTests::test_staff_row_structure` |
| AC4 | `SeparatorTests::test_catalog_blocks` |
| AC5 | `SeparatorTests::test_no_space_before_dot_in_detail` |
| AC6 | `core/tests/test_css.py::BaseCssTests::test_meta_item_nowrap`; visual check |
| AC7, AC8 | existing petitions tests unchanged; `SeparatorTests::test_texts_and_links_kept` |

### Access matrix

No view or permission changes; the existing petitions access tests must pass unchanged.

### Tests (`petitions/tests/test_views.py`, new class `SeparatorTests(FrozenClockMixin, TestCase)`)

Setup: faculty, group "GX", student A (+ staff of the same faculty), an ordinary type, a catch-all type (`make_type(name="Другая справка", days=5, comment_required=True, hint="h", subject_required=True)`), petition P1 of the ordinary type, petition P2 of the catch-all type with `subject` = 150 × "а"; for P1 one staff status change (via `change_status`) and one staff comment (`add_staff_comment`). Helper `_part(content, start_marker, end_marker)` slices the HTML.

- `test_no_space_before_dot_in_lists`: for `my_list` (student) and `staff_queue` (staff), inside `<ul class="petition-list">…</ul>`: `re.search(r"[ \t\n]·", part)` is None, and every row (`<li class="petition">…</li>`) contains the literal entity `&nbsp;·` exactly 3 times (Django outputs the template's `&nbsp;` unchanged).
- `test_no_space_before_dot_in_detail`: student detail and staff detail of P1: inside the history `<ol>` and the comments `<ul>`, no `[ \t\n]·`.
- `test_student_row_structure`: `my_list` contains `<a class="petition-title" href="/requests/<P2 uuid>/">Другая справка: ааа…</a>` (full 150 characters) followed by `<p class="petition-meta">`, and the meta contains `<span class="meta-item">№ <short id>&nbsp;·</span>`.
- `test_staff_row_structure`: `staff_queue` row of P2 has `<a class="petition-title" …>`, then `<p class="petition-subject">Другая справка: ааа…</p>`, then `<p class="petition-meta">` with `файлов: 0`.
- `test_catalog_blocks`: the catalog contains `<p class="catalog-term">Срок: до 5 рабочих дней</p>` and `<a class="catalog-title"`; no " — " and no "·" in the page's `main`.
- `test_texts_and_links_kept`: the student list still has the detail href, the status text, "готовность:"; the staff queue still has the staff detail href, the group name, "файлов:".

Amendment 1 tests:
- `core/tests/test_design.py::SeparatorRuleTests::test_no_whitespace_before_separator`: for each template of this task (the 5 petitions templates and the 8 of Amendment 1; a module-level tuple of paths), the file text has no match for `re.compile(r"\s·")` (any whitespace, including a newline, directly before "·"), and contains at least one "&nbsp;·". subTest per file.
- `chat/tests/test_views.py` line 294: `self.assertIn("Деканат ·", content)` → `self.assertIn("Деканат&nbsp;· ", content)` with the comment `# TASK-014-FIX: separator glued with a no-break space`.
- `chat/tests/test_views.py::PollTests` (or the class that tests the polling fragment; find it with `grep -n "X-Chat-Fragment" chat/tests/test_views.py`): new `test_fragment_meta_separator`: the polled fragment of a staff message contains `Деканат&nbsp;· ` and `li` with `data-message-id` (the JS contract).
- `notifications/tests/test_views.py::FeedViewTests::test_meta_separator_glued`: the feed of a student with one new announcement contains `<strong>Новое</strong>&nbsp;· ` and no `[ \t\n]·` inside `<p class="feed-meta">…</p>`.
- `academics/tests/test_views.py` (class with the report view): new `test_summary_separator_glued`: the report page's `<summary>` contains `&nbsp;· Итог:` and no `[ \t\n]·`.
- `core/tests/test_home.py::HomeStudentTests::test_lesson_meta_separator_glued`: the home page contains `&nbsp;· ` inside `<p class="lesson-meta">` and no `[ \t\n]·` there.

`core/tests/test_css.py::BaseCssTests::test_meta_item_nowrap`: base.css has a `.meta-item` rule with `white-space: nowrap`, and a rule for `.petition-title` with `display: block` and `min-height: 2.75rem` (directly or via a shared selector list).

### Visual check (UI coder; screenshots and numbers in the REPORT)

Temporary DB with `seed_demo` (it has the demo request "Другая справка: Справка о периоде обучения" for student1); add one request with a 150-character subject for student1 (via `submit_petition` in `manage.py shell`, or the form).
- Student "Мои заявки" and staff "Заявки" (staff1) at 360 × 780 and 1024 × 768; catalog at 360 × 780; one request detail (with history and a staff comment) at 360 × 780.
- For each row, check that no line starts with "·". In the browser: for every text node, `Range.getClientRects()` per character is heavy; instead, take screenshots and also run: `[...document.querySelectorAll('.petition-meta, .petition li, ol li')].every(e => !/[\s]·/.test(e.innerHTML.replace(/&nbsp;/g,' ')))` (structure check), and look at the screenshots.
- `document.documentElement.scrollWidth === innerWidth` on every page (also at 320 × 780 for the student list).
- Amendment 1 pages at 360 × 780 (screenshot each; no line starts with "·"; no horizontal scroll): staff "Чаты" list (`/staff/chats/`, staff1), student chat (`/chat/`, student1, with a staff message) and a staff dialog (staff1), staff "Студенты" (`/staff/students/`), staff "Расписание групп" (`/staff/schedule/`), student "Уведомления" (`/notifications/`, with a "Новое" item), staff "Объявления" (`/staff/announcements/`), student "Успеваемость" (`/grades/`, one `<details>` open) and the staff view of a student's grades, student home "Занятия" card (`/`). Also check that chat polling still adds a new message without reload (send a message from the other role and wait one poll interval).

### Edge cases

150-character subject; the shortest row (ordinary type); a status with two words ("В работе"); a request with no attachments ("файлов: 0"); the catalog type without a description.

## Implementation order

1. Templates (five files). Run `python manage.py test petitions --parallel 1` (log).
2. CSS. Visual check at 360 and 1024.
3. New tests. Full verification. REPORT.

## Verification

```bash
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --parallel 1 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log"
ruff check petitions/tests/test_views.py core/tests/test_css.py
ruff format --check petitions/tests/test_views.py core/tests/test_css.py
git status --short
```
If any run fails or stalls, even once, put the test name, the Moscow time and the traceback excerpt into the REPORT.

## Risks

- **Template whitespace.** A newline or indentation before "·" in a template brings the bug back; the regex tests catch it.
- **Long staff names** wrap inside the title line (fine: no separator there).
- **Other pages** keep the old pattern (out of scope); listed for a possible later task.
