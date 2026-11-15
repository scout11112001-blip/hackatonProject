# TASK-007-FIX: home news without shown deadlines, short labels, non-breaking teacher initials, clock-safe petition timestamps

Author: Planner. Status: ready for implementation.
Base commit: `4608e59`. Related specs: `docs/tasks/TASK-007.md` (D5 = clock-safe defaults), `docs/tasks/TASK-006.md`. Screenshots: `docs/process/screenshots/2026-11-15_16..19_*.jpg`.

No new features. Each fix is minimal and has a regression test that fails without it (except item 6, a style change).

---

## 1. Acceptance criteria
| ID | Criterion |
|---|---|
| AC1 | Home page (student): the news heading is «Новости». The news block excludes ONLY the announcements shown in the home deadlines block at that moment (the `HOME_ITEMS` nearest deadlines). Other announcements, including deadlines not shown there (4th nearest, past), stay eligible. Up to `HOME_ITEMS` news, newest first. `/notifications/` is unchanged. Home query count does not grow. |
| AC2 | Staff form: the faculty option label is «Весь факультет». Group options stay «Группа <name>». |
| AC3 | Audience label for a faculty announcement is the faculty name only (e.g. «Факультет цифровой дипломатии»); «Для всех студентов» and «Группа <name>» unchanged. One place builds it: `Announcement.audience_label`. |
| AC4 | `Teacher.short_name` uses U+00A0 (no-break space) between the last name and the first initial and between the initials. Pages render it unchanged (Django's `escape` does not touch U+00A0). |
| AC5 | Petition services take the time from `core.clock.now()` and pass it explicitly: `submit_petition`, `change_status`, `add_staff_comment`. Model defaults of `Petition.created_at`, `Petition.status_changed_at`, `PetitionStatusChange.created_at`, `PetitionComment.created_at`, `PetitionAttachment.uploaded_at` are `core.clock.now`. Migration `petitions/0002` is generated. Production behaviour is unchanged (`core.clock.now()` returns `timezone.now()`). |
| AC6 | `notifications/feed.py`: `relative_day_label` is imported at module level (no import cycle, see 6.2). |

## 2. Out of scope
New features, visual theme, room map (TASK-008), chat (TASK-009). Accepted limitations (do not fix): existing lesson changes appear as «Новое» once after `schedule/0004`; a home `#news-<uuid>` link may point to nothing if the item is outside the feed.

## 3. Files
Change only:
- `notifications/feed.py` (items 1, 6), `core/templates/core/home.html` (item 1)
- `notifications/forms.py`, `notifications/views.py` (item 2)
- `notifications/models.py` (item 3)
- `university/models.py` (item 4)
- `petitions/models.py`, `petitions/services.py`, new `petitions/migrations/0002_alter_petition_created_at_and_more.py` (generated) (item 5)
- tests: `notifications/tests/test_views.py`, `notifications/tests/test_models.py`, `university/tests/test_models.py`, `schedule/tests/test_views.py`, `petitions/tests/test_services.py`

No settings, no new dependencies, no other migrations.

---

## 4. Fixes

### 4.1 Item 1 — home news (`notifications/feed.py::home_summary`, `core/home.html`)
Replace the body of `home_summary` after `ctx` is built:
```python
deadlines = upcoming_deadlines(ctx, HOME_ITEMS)
shown = {f"news-{d.public_id}" for d in deadlines}
candidates = NewsSource().latest(ctx, HOME_ITEMS + len(shown))
news = [item for item in candidates if item.key not in shown][:HOME_ITEMS]
return HomeSummary(deadlines=deadlines, news=news)
```
Why `HOME_ITEMS + len(shown)`: at most `len(shown)` candidates are dropped, so at least `HOME_ITEMS` remain when that many exist. Still one query for news (same count as before). The key format `news-<public_id>` is the one `NewsSource.to_item` builds (`notifications/sources.py`); do not build another format.
`core/home.html`: `<h2 id="home-news">Новости деканата</h2>` → `<h2 id="home-news">Новости</h2>`. Nothing else changes in the template.

### 4.2 Item 2 — form label (`notifications/forms.py`, `notifications/views.py`)
- `AnnouncementForm.__init__`: remove the `faculty: Faculty` keyword argument (it becomes unused) and its import if unused; the first choice becomes `(TARGET_FACULTY, "Весь факультет")`.
- `StaffAnnouncementsView._form`: remove `faculty=self.profile.faculty`.
- Existing `AnnouncementFormTests` construct the form with `faculty=…`: remove that argument in each call (mechanical change, list it in the `REPORT`).

### 4.3 Item 3 — audience label (`notifications/models.py`)
`Announcement.audience_label`, faculty branch: `return self.faculty.name`. The templates already use this property only (`feed.html`, `_deadlines.html`, `staff_list.html`, via `FeedItem.audience_label` / `DeadlineItem.audience_label`); do not build the label anywhere else. Update `notifications/tests/test_models.py::…::test_str_and_audience_label` expected value to `"Факультет FX"`.

### 4.4 Item 4 — teacher short name (`university/models.py`)
```python
NBSP = " "
...
@property
def short_name(self) -> str:
    middle = f"{NBSP}{self.middle_name[0]}." if self.middle_name else ""
    return f"{self.last_name}{NBSP}{self.first_name[0]}.{middle}"
```
`NBSP` is a module-level constant in `university/models.py`. Update `university/tests/test_models.py::…::test_teacher_short_name` to `"Лебедев А. С."` and `"Фомин П."`. No other test or template depends on the plain-space form (checked, see 6.2).

### 4.5 Item 5 — petition timestamps (`petitions/models.py`, `petitions/services.py`)
- `petitions/models.py`: `from core.clock import now`; the five defaults listed in AC5 become `default=now`. Remove `from django.utils import timezone` if it becomes unused (it does on the current tree).
- `python manage.py makemigrations petitions` → `petitions/migrations/0002_alter_petition_created_at_and_more.py` (5 `AlterField`, default only). On PostgreSQL this changes no SQL; on SQLite Django rebuilds the five tables and copies the data (checked on a seeded copy: 7 petitions and 3 attachments kept).
- `petitions/services.py`: `from core import clock`.
  - `submit_petition`: `now = clock.now()` (instead of `timezone.now()`); `expected_ready_date=add_working_days(timezone.localdate(now), …)` (same Moscow date as `now`).
  - `change_status`: `now = clock.now()`.
  - `add_staff_comment`: `return PetitionComment.objects.create(petition=petition, author=actor, text=text, created_at=clock.now())`.
  - Keep `from django.utils import timezone` (still used by `localdate`).
- `store_attachment` (`petitions/files.py`) is not changed: `uploaded_at` takes the new clock-safe default.

### 4.6 Item 6 — import (`notifications/feed.py`)
Delete `from .dates import relative_day_label` inside `upcoming_deadlines`; add it to the module imports (`from .dates import relative_day_label`, isort order between `.constants` and `.models`).

---

## 5. Test plan

### 5.1 Rules
- New test classes use `FrozenClockMixin` with `frozen_now = "2026-11-11 12:00"` (before the real date, so a timestamp from the real clock is detected at once), and the existing helpers (`make_world`, `make_announcement`, `make_faculty`, `make_group`, `make_student`, `make_staff`, `make_type`, `make_petition`, `pdf_upload`, `make_lesson`, `make_room`, `make_teacher`).
- Save full output of every test run to a file; report any failed run by test name, Moscow time and traceback excerpt.

### 5.2 Traceability and regression evidence
| AC | Test (file::class::method) | Fails before fix because |
|---|---|---|
| AC1 | `notifications/tests/test_views.py::HomeSummaryTests::test_news_exclude_shown_deadlines` | shown deadlines fill the news block, the 4th deadline and plain news are hidden |
| AC1 | `…::HomeSummaryTests::test_news_without_deadlines_unchanged` | (guard) |
| AC1 | `…::HomeSummaryTests::test_news_heading` | heading is «Новости деканата» |
| AC1 | `…::QueryCountTests::test_home_queries_same_with_deadlines` | (guard: count does not grow) |
| AC2 | `notifications/tests/test_views.py::AnnouncementFormTests::test_faculty_option_label` | label contains the faculty name |
| AC3 | `notifications/tests/test_views.py::AudienceLabelRenderTests::test_feed_shows_faculty_name_only`, `test_staff_list_shows_faculty_name_only`; updated `test_models.py::…::test_str_and_audience_label` | «Факультет: » prefix |
| AC4 | `university/tests/test_models.py::…::test_teacher_short_name` (updated), `schedule/tests/test_views.py::TeacherShortNameRenderTests::test_week_page_has_no_break_spaces` | plain spaces |
| AC5 | `petitions/tests/test_services.py::ServiceClockTests::test_staff_comment_gets_frozen_time`, `test_attachment_gets_frozen_time` | real time from `default=timezone.now` |
| AC5 | `…::ServiceClockTests::test_submit_gets_frozen_time`, `test_status_change_gets_frozen_time`, `test_model_defaults_are_clock_now` | (guards; `timezone.now()` call was already patched; the last one fails before: default is `timezone.now`) |
| AC6 | none (style); Reviewer checks `grep -n "import" notifications/feed.py` | — |

### 5.3 Test details
- `HomeSummaryTests` (existing class, `frozen_now = NOW` of the module):
  - `test_news_exclude_shown_deadlines`: university announcements: `d1..d4` with deadlines `D+1..D+4` and `published_at = now - 1h, -2h, -3h, -4h`; plain news `p` with `published_at = now - 5h`. GET `/` as `ax`. Split the content at `id="home-news"` and use the part after it: contains `#news-{p.public_id}` and `#news-{d4.public_id}`; contains none of `#news-{d1/d2/d3.public_id}`. The part before contains `#deadline-{d1..d3.public_id}`.
  - `test_news_without_deadlines_unchanged`: 4 plain news (published now - 1h … now - 4h) → news part contains exactly the 3 newest (`#news-` count 3, oldest absent).
  - `test_news_heading`: `'<h2 id="home-news">Новости</h2>'` in content; «Новости деканата» absent.
  - The existing `test_limits_to_three` must still pass unchanged.
- `QueryCountTests::test_home_queries_same_with_deadlines`: count A = GET `/` with 1 plain news; then add 4 deadline announcements and 3 more news; count B; `assertEqual(A, B)`.
- `AnnouncementFormTests::test_faculty_option_label`: `dict(form.fields["target"].choices)["faculty"] == "Весь факультет"`; group label `f"Группа {gx1.name}"` unchanged.
- `AudienceLabelRenderTests(FrozenClockMixin, TestCase)` (new class in `notifications/tests/test_views.py`, world from `make_world`, faculty name is «Факультет FX»):
  - `test_feed_shows_faculty_name_only`: FX faculty announcement; GET `/notifications/` as `ax` → «Факультет FX» in content; `"Факультет: "` not in content.
  - `test_staff_list_shows_faculty_name_only`: same item; GET `/staff/announcements/` as `sx` → same assertions.
- `TeacherShortNameRenderTests(FrozenClockMixin, TestCase)` (new class in `schedule/tests/test_views.py`, `frozen_now = "2026-11-11 12:00"`): a student's group has a Wednesday lesson with teacher `Teacher(last_name="Шестакова", first_name="Людмила", middle_name="Петровна")`; GET `schedule:week_of` for 2026-11-11 → content contains `"Шестакова Л. П."` and does not contain `"Шестакова Л."`.
- `ServiceClockTests(FrozenClockMixin, TestCase)` (new class in `petitions/tests/test_services.py`, `frozen_now = "2026-11-11 12:00"`, expected `moscow("2026-11-11 12:00")`):
  - `test_submit_gets_frozen_time`: `submit_petition(...)` → `petition.created_at`, `status_changed_at` and the history row `created_at` equal the frozen time.
  - `test_attachment_gets_frozen_time`: `submit_petition(..., [pdf_upload()])` → `attachment.uploaded_at` equals the frozen time.
  - `test_status_change_gets_frozen_time`: `change_status(...)` → new history row and `status_changed_at` equal the frozen time.
  - `test_staff_comment_gets_frozen_time`: `add_staff_comment(...)` → `created_at` equals the frozen time.
  - `test_model_defaults_are_clock_now`: for the five fields, `Model._meta.get_field(name).default is core.clock.now`.

### 5.4 Access matrix
No access rules change. Existing access tests of `core:home`, `notifications:feed`, `notifications:staff_announcements` and the petitions views must keep passing.

### 5.5 Settings branches / query count
No settings change. Query count: 5.3 (`test_home_queries_same_with_deadlines`); existing `test_home_queries_constant` and `test_badge_exactly_three_queries` must keep passing.

---

## 6. Feasibility check (2026-11-15 13:43 MSK on `4608e59`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — `home_summary`, `upcoming_deadlines` (function-local import at `notifications/feed.py` inside `upcoming_deadlines`), `NewsSource.to_item` key `news-<public_id>`, `HOME_ITEMS`; `core/home.html:12` heading «Новости деканата»; `AnnouncementForm.__init__(…, faculty, groups, today)` label `f"Весь факультет: {faculty.name}"` (`notifications/forms.py:37`), used by `notifications/views.py:41-44` and 7 calls in `notifications/tests/test_views.py`; `Announcement.audience_label` (`notifications/models.py:104-109`) — the only builder, used by `sources.py:125`, `feed.py:98`, templates `feed.html`, `_deadlines.html`, `staff_list.html`; `Teacher.short_name` (`university/models.py:126-128`), used by `schedule/templates/schedule/includes/lesson_item.html:9` and `notifications/sources.py:204`; tests on its text: only `university/tests/test_models.py:51-55` (grep for `short_name`, `[А-Я]\. [А-Я]\.` in all tests); petitions defaults `petitions/models.py:81,82,122,147,170` (`default=timezone.now`); services `submit_petition` (`timezone.now()` line 86), `change_status` (line 139), `add_staff_comment` (no `created_at`, line ~163); `core/clock.py::now`. OK.
3. No collisions — `NBSP` not defined in `university/models.py`; test classes `AudienceLabelRenderTests`, `TeacherShortNameRenderTests`, `ServiceClockTests` and the new method names do not exist; latest petitions migration is `0001_initial`. OK.
4. Migrations — `makemigrations --check --dry-run` → «No changes detected». On a temporary copy of `HEAD` with the item-5 defaults: `makemigrations petitions --dry-run` → `0002_alter_petition_created_at_and_more.py` (5 AlterField); applied on a seeded temp DB (`migrate petitions 0001` → `seed_demo` → `migrate`) → 7 petitions and 3 attachments kept. No other app gets a migration (`short_name` is a property). OK.
5. Tools — unchanged (Python 3.12, Django 5.2.19, ruff 0.17.4). OK.
6. Framework — Django template autoescape leaves U+00A0 as the raw character (`Template("{{ x }}")` with `"Фомин П."` renders `'Фомин\xa0П.'`), so tests assert the raw character. `default=timezone.now` is not patched by `FrozenClockMixin`, a call-time lookup is (TASK-007 feasibility 6). No import cycle for item 6: `notifications/dates.py` imports only `datetime`, and `notifications/sources.py` already imports `relative_day_label` at module level. OK.
7. Environment — no new env variables. OK.
8. Verification runnable — current tree, logs `$TMPDIR/test-20261115-134337-t007fix-feas*.log`: results in 6a below.
9. Conflicts — none.
10. Assumptions / blockers — none.

### 6a. Verification results on the current tree
- `check` → no issues; `makemigrations --check --dry-run` → «No changes detected».
- `test` → `Ran 735 tests … OK`; `run_tests_at.py 2026-11-17T23:59:59` → 735 OK; `run_tests_at.py 2026-11-18T00:00:00` → 735 OK. No failed runs.
- `check --deploy --fail-level WARNING` → no issues (1 silenced); `ruff check .` → all passed; `ruff format --check .` → 149 files already formatted; CI YAML ok.
- `seed_demo` twice on a temporary DB and PRIVATE_MEDIA_ROOT → OK (second run: «Notifications ready: 0 announcements.», «0 requests»).

## 7. Implementation order
1. Write the tests in 5.2/5.3 and run them: the ones marked "fails before fix" must fail.
2. Fixes 4.1–4.6 (4.5: models → `makemigrations petitions` → services).
3. `ruff format` on changed Python files only (not migrations); section 8; `REPORT` to the Reviewer with the regression evidence (which tests failed before the fix). Do not commit.

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
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
export DATABASE_URL="sqlite:///$TMPDIR/task007fix.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task007fix-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
rm -f "$TMPDIR/task007fix.sqlite3"
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
git status --short
```
`REPORT`: output tails, test count (was 735), log file names, any failed run by test name and Moscow time, `git status`.

## 9. Risks
- Non-breaking spaces make the short name one unit. It is short (last name + 2 initials) and `body` already has `overflow-wrap: anywhere` (`static/css/base.css:14`), so an extremely long name still cannot overflow 360 px. The Team lead re-checks the schedule page at 360 px.
- The SQLite table rebuild in `petitions/0002` copies data; run it only through `migrate` (never by hand). The local `db.sqlite3` is migrated by the Team lead, not by the Coder.
