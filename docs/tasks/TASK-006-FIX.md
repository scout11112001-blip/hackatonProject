# TASK-006-FIX: request list link, 360 px overflow, duplicate hint, missing file 404, README

Author: Planner. Status: ready for implementation.
Base commit: `783ba76`. Related spec: `docs/tasks/TASK-006.md`. Screenshots: `docs/process/screenshots/2026-11-14_08..12_*.jpg`.

No new features. Each fix is minimal and has a regression test that fails without it.

---

## 1. Acceptance criteria
| ID | Criterion |
|---|---|
| AC1 | «Мои заявки» always shows a «Подать заявку» link to `petitions:catalog` at the top (with and without requests); the empty state text stays. |
| AC2 | `static/css/base.css` caps all form controls at their container width (`input`, `select`, `textarea`, `button`: `max-width: 100%`); layout layer only. |
| AC3 | On the request form the hint for `comment_required` types appears exactly once (as the comment field's help text). |
| AC4 | `download_attachment` returns 404 (not 500) when the DB row exists but the file is missing; logs one WARNING without file path, original file name or personal data. |
| AC5 | README: `seed_demo` runs once on the server on 2026-11-22 (no cron); deployment notes say `PRIVATE_MEDIA_ROOT` is backed up together with the database. |

## 2. Out of scope
`seed_demo` console summary wording, new features, visual theme (incl. native file input styling), notifications.

## 3. Files
Change only: `petitions/templates/petitions/my_list.html`, `petitions/templates/petitions/form.html`, `petitions/views.py`, `static/css/base.css`, `README.md`, `petitions/tests/test_views.py`, `petitions/tests/test_downloads.py`, `core/tests/test_css.py` (new). No migrations, no settings, no new dependencies.

---

## 4. Fixes

### 4.1 AC1 — `my_list.html`
Directly after `<h1>Мои заявки</h1>` and **outside** the `{% if petitions %}` block:
```html
<p class="page-actions"><a href="{% url 'petitions:catalog' %}">Подать заявку</a></p>
```
Empty state becomes `<p>Заявок пока нет.</p>` (remove the second link so the page has exactly one catalog link).

### 4.2 AC2 — `static/css/base.css`
Append (layout layer; tokens only, no colors):
```css
input,
select,
textarea,
button {
  max-width: 100%;
  min-width: 0;
}

.page-actions {
  margin: var(--space-2) 0 var(--space-3);
}
```
`box-sizing: border-box` is already global (`base.css:1-5`, `*, *::before, *::after`); do not duplicate it. `min-width: 0` lets controls shrink inside flex containers. Do not change `tokens.css` or `theme.css`. Keep the existing `.form input` rule.

### 4.3 AC3 — `form.html`
Remove the line `{% if request_type.comment_required %}<p class="hint">{{ request_type.comment_hint }}</p>{% endif %}`. The hint is already set as the comment field's `help_text` (`petitions/forms.py:40`) and rendered by `{{ form.as_p }}` under the field. Do not change `forms.py`.

### 4.4 AC4 — `petitions/views.py` `download_attachment`
Add at module level `logger = logging.getLogger(__name__)` (`import logging`). Replace the `att.file.open("rb")` call with:
```python
try:
    handle = att.file.open("rb")
except FileNotFoundError:
    logger.warning("Attachment file is missing on disk (attachment %s).", att.public_id)
    raise Http404("Файл не найден.") from None
```
and pass `handle` to `FileResponse`. Log only the attachment's UUID (`public_id`): no path, no `original_name`, no student data. Access checks stay before this step (unchanged), so a missing file of another student's request is still a 404 from the lookup, without a log line.

### 4.5 AC5 — README
- "Known limitations", second bullet: replace «run it daily on the server to keep the demo fresh» with: «On the server it is run once, on 2026-11-22 (submission day); there is no scheduled re-run.»
- Add a section `## Deployment notes` right before `## Known limitations`:
  - `python manage.py seed_demo` once on 2026-11-22 after `migrate` (needs `DEMO_PASSWORD`).
  - Back up `PRIVATE_MEDIA_ROOT` together with the database (attachments are referenced by DB rows; restoring one without the other breaks downloads).
  - nginx must not serve `PRIVATE_MEDIA_ROOT`; `client_max_body_size 20m;` (reference to the "Requests" section).

---

## 5. Test plan

All new view tests use existing fixtures/helpers in `petitions/tests/helpers.py` and `FrozenClockMixin`.

### 5.1 Traceability and regression evidence
| AC | Test (file::class::method) | Fails before fix because |
|---|---|---|
| AC1 | `petitions/tests/test_views.py::StudentPagesTests::test_catalog_link_on_list_with_requests` | link is only in the empty state |
| AC1 | `…::StudentPagesTests::test_catalog_link_on_empty_list` | (passes before; guards the empty state: link present exactly once, «Заявок пока нет.» present) |
| AC2 | `core/tests/test_css.py::BaseCssTests::test_form_controls_capped` | rule does not exist |
| AC3 | `petitions/tests/test_views.py::FormTests::test_hint_rendered_once` | hint rendered twice |
| AC3 | `…::FormTests::test_no_hint_for_optional_type` | (guard: type with `comment_required=False` and a hint → hint shown at most once, no `class="hint"`) |
| AC4 | `petitions/tests/test_downloads.py::MissingFileTests::test_missing_file_returns_404` | `FileNotFoundError` → 500 |
| AC4 | `…::MissingFileTests::test_missing_file_log_has_no_personal_data` | no log before |
| AC4 | `…::MissingFileTests::test_missing_file_of_other_faculty_is_404_without_log` | (guard: access check still first) |
| AC5 | manual README review by the Reviewer | — |

### 5.2 Test details
- `test_catalog_link_on_list_with_requests`: student with 1 petition; GET `/requests/` → `content.count('href="/requests/new/"') == 1`, link text «Подать заявку».
- `test_catalog_link_on_empty_list`: student without petitions → link count 1, «Заявок пока нет.» present.
- `test_form_controls_capped`: read `settings.BASE_DIR / "static/css/base.css"`; assert a rule whose selector list contains `input`, `select`, `textarea`, `button` and whose body contains `max-width: 100%` (regex `r"input,\s*select,\s*textarea,\s*button\s*\{[^}]*max-width:\s*100%"`). Also assert `tokens.css` and `theme.css` do not contain `max-width` (layout stays in `base.css`).
- `test_hint_rendered_once`: type with `comment_required=True`, hint «Обязательно укажите причину обращения.»; GET form → `content.count(hint) == 1`.
- `test_no_hint_for_optional_type`: `comment_required=False`, hint «Можно указать, куда нужна справка.» → `content.count(hint) <= 1` and `'class="hint"' not in content`.
- `MissingFileTests(FrozenClockMixin, TestCase)`: petition of student A (faculty X) with one stored attachment; delete the file via `get_private_storage().delete(att.file.name)`.
  - `test_missing_file_returns_404`: as A and as staff SX → 404 each.
  - `test_missing_file_log_has_no_personal_data`: `with self.assertLogs("petitions.views", level="WARNING") as logs:` GET as A → exactly one record; message contains `str(att.public_id)`; does not contain `att.file.name`, `att.original_name`, the student's last name, username, or `str(settings.PRIVATE_MEDIA_ROOT)`.
  - `test_missing_file_of_other_faculty_is_404_without_log`: as staff SY → 404 and `assertNoLogs("petitions.views", level="WARNING")`.
- Existing `test_hint_shown_for_required_comment` and `test_my_list_empty_state` must still pass; if `test_my_list_empty_state` asserts the old link inside the empty-state paragraph, adjust only that assertion to the new markup and say so in the `REPORT`.

### 5.3 Access matrix
No access rules change. The download view keeps the TASK-006 matrix (`petitions/tests/test_downloads.py::DownloadAccessTests`); the new missing-file tests add: owner student → 404, own-faculty staff → 404, other-faculty staff → 404 without log.

### 5.4 Settings branches / query count
Not applicable (no settings, no list query changes; the list template only gains a static link).

---

## 6. Feasibility check (2026-11-14 on `783ba76`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — `my_list.html` (catalog link only in the empty state, confirmed), `form.html` line 5 (`<p class="hint">` duplicate, confirmed), `forms.py:40` (`help_text = request_type.comment_hint`), `download_attachment` in `petitions/views.py` (calls `att.file.open("rb")` without handling a missing file; no logger in the module), `base.css` (global `box-sizing` at lines 1-5; only `.form input` capped at line 72; no rule for `select`), README "Known limitations" (line 130, "run it daily"), no "Deployment notes" section, test classes `StudentPagesTests`, `FormTests` (`petitions/tests/test_views.py`), `DownloadHeadersTests` (`test_downloads.py`), `get_private_storage` (`core/storage.py`). OK.
3. No collisions — `core/tests/test_css.py`, class `MissingFileTests`, CSS class `page-actions` do not exist. OK.
4. Migrations — none; `makemigrations --check` → "No changes detected". OK.
5. Tools — unchanged (Python 3.12.16, Django 5.2.19, ruff 0.17.4). OK.
6. Framework — `TestCase.assertLogs` / `assertNoLogs` (Python 3.10+), `Http404`, `FieldFile.open` raises `FileNotFoundError` for a missing file on `FileSystemStorage`. OK.
7. Environment — no new env variables. OK.
8. Verification runnable — current tree: `test` → `Ran 559 tests … OK`; `scripts/run_tests_at.py 2026-11-18T00:00:00` → 559 OK; ruff check → clean; ruff format → 122 files formatted; makemigrations clean. OK.
9. Conflicts — none.
10. Assumptions / blockers — none.

## 7. Implementation order
1. Write the regression tests (5.1) and confirm the ones marked "fails before fix" fail.
2. Fixes 4.1–4.4. 3. README 4.5. 4. `ruff format` on changed Python files only; section 8. `REPORT` to the Reviewer with the regression evidence. Do not commit.

## 8. Verification
```bash
source .venv/bin/activate
export DEBUG=true
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python scripts/run_tests_at.py 2026-11-17T23:59:59
python scripts/run_tests_at.py 2026-11-18T00:00:00
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
ruff check . && ruff format --check .
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
export DATABASE_URL="sqlite:///$TMPDIR/task006fix.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task006fix-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
git status --short
```
`REPORT`: output tails, test count (was 559), `git status`.

## 9. Risks
- Capping `button`/`input` widths globally could change existing pages; `max-width` only shrinks controls wider than their container, so normal-width controls are unaffected. The Team lead re-checks 360 px visually.
- The missing-file log line must stay free of personal data (asserted by a test).
