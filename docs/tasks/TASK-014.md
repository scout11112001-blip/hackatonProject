# TASK-014: New request types, the "Тип" field, term wording "до N рабочих дней"

Assignee: **Coder** (DeepSeek, thr_ng6cbgatm6). Request: Team lead, approved by the user (decisions of 18.11).

## Goal

1. Add the certificate type "Справка в военкомат" (comment required, hint "Укажите военкомат.", 3 days).
2. Add two catch-all types "Другая справка" (certificate) and "Другое заявление" (application), 5 days each. For them the student must fill a one-line field "Тип" (what exactly is needed, ≤ 150 characters) and a comment.
3. Show the term as a maximum for every type: "Срок: до N рабочих дней" with the correct Russian form.
4. Show "Тип" as "Другая справка: <Тип>" / "Другое заявление: <Тип>" in the student's list and detail, the staff queue and detail, and the "Заявка подана" page.

## Acceptance criteria

- AC1. `RequestType.subject_required` (bool, default False) exists, is editable in the admin and shown in the admin list. A type with `subject_required=True` must have `comment_required=True`: `RequestType.clean()` raises a `ValidationError` and a DB check constraint `petitions_type_subject_needs_comment` forbids the combination.
- AC2. `Petition.subject` (`CharField`, max 150, blank, default "") exists. It is empty for every type without the flag (the form has no such field and the service ignores any value).
- AC3. The submit form of a type with the flag shows a required one-line field "Тип" before "Комментарий". An empty value, spaces only, or more than 150 characters (after trimming) is an error; leading/trailing spaces are removed and inner runs of whitespace (including newlines and tabs) become one space. The comment is required with the type's hint. Types without the flag do not render the field (`name="subject"` absent).
- AC4. `submit_petition(..., subject="")` validates the same rules (defence in depth) and stores the normalised subject.
- AC5. The catalog shows "Срок: до N рабочих дней" for every type: N with `N % 10 == 1 and N % 100 != 11` → "до N рабочего дня" (1, 21, 31, 41, 51); otherwise "до N рабочих дней" (3, 5, 11, 12, 15, 60…). The string "раб. дн." no longer appears in any template. Within each catalog section the catch-all type is last.
- AC6. `Petition.display_name` is "<type name>: <subject>" when the subject is not empty, otherwise the type name. It is used in: `my_list.html` (link text), `detail.html` (`h1`), `staff_queue.html` (item), `staff_detail.html` (the "Заявка" paragraph), `submitted.html`. Django autoescaping stays on (no `|safe`). Long values wrap at 360 px (no horizontal scroll).
- AC7. `seed_demo` creates the 3 new types (7 in total), stays idempotent (run twice), keeps the 7 existing demo requests valid, and creates one demo request `p-8` of "Другая справка" with subject "Справка о периоде обучения" for `student1`. Seed output: "Requests ready: 7 types, …".
- AC8. Access rules and the query counts of the lists and details are unchanged.

## Out of scope

- New workflow or statuses, file rules, visual redesign, new CSS.
- The notifications feed titles ("Заявка «…»") keep the type name only (the user listed the five pages above).
- Editing the subject after submission.

## Design decisions

- **D1. Names.** Field `RequestType.subject_required` ("нужно поле «Тип»"), field `Petition.subject` ("тип"), constant `SUBJECT_MAX_LENGTH = 150` in `petitions/models.py`, form field label "Тип".
- **D2. Term wording** lives in a small pure module `petitions/terms.py` (`term_label(days)`) and is exposed as `RequestType.term_label` (property), so templates need no custom tag. "до" takes the genitive: singular "рабочего дня" for 1, 21, 31…, plural "рабочих дней" otherwise (including 11).
- **D3. Display.** One property `Petition.display_name`, used by every template. No new query: `petitions_visible_to` already `select_related("request_type")`; `submitted.html` uses the same queryset.
- **D4. Normalisation.** `" ".join(value.split())` in both the form and the service: one line, no leading/trailing or repeated whitespace. Max length is checked on the normalised value in the service and on the stripped value in the form (Django `CharField` strips before `MaxLengthValidator`); test both 150 (OK) and 151 (error).
- **D5. Catalog order.** `RequestType.objects.filter(is_active=True).order_by("subject_required", "name")`, so the catch-all types come last in their section.
- **D6. Seeds.** `REQUEST_TYPES` tuples get a 7th element `subject_required`; the 3 new tuples are appended at the end of the list. The seed upserts by name (existing behaviour), so a second run changes nothing. The 7 existing demo requests are never updated (existing rule) and keep `subject=""`.

## Architecture / files

- `petitions/terms.py` (new): F1.
- `petitions/models.py`: `SUBJECT_MAX_LENGTH`, `RequestType.subject_required`, the new check constraint, `RequestType.clean()` rule, `RequestType.term_label`, `Petition.subject`, `Petition.display_name` (F2).
- `petitions/migrations/0003_subject.py` (new): `python manage.py makemigrations petitions --name subject` (F3).
- `petitions/forms.py`: `PetitionForm.subject` (F4).
- `petitions/services.py`: `submit_petition(..., subject: str = "")` (F5).
- `petitions/views.py`: `SubmitPetitionView.form_valid` passes `subject`; `CatalogView` order (F6).
- `petitions/admin.py`: `RequestTypeAdmin.list_display` adds `"subject_required"`; `PetitionAdmin.list_display` adds `"subject"` after `"request_type"`.
- Templates: `catalog.html`, `my_list.html`, `detail.html`, `staff_queue.html`, `staff_detail.html`, `submitted.html` (F7).
- `petitions/demo.py`: F8.
- `petitions/tests/helpers.py`: `make_type(..., subject_required=False)` (new keyword, passed to `create`).
- Tests: see the Test plan.
- `README.md` "## Requests": one paragraph: the 7 request types, the "Тип" field for "Другая справка"/"Другое заявление", the term shown as "до N рабочих дней".

## Functions

### F1. `petitions/terms.py`

```python
"""Russian wording of processing terms."""


def term_label(days: int) -> str:
    if days % 10 == 1 and days % 100 != 11:
        return f"до {days} рабочего дня"
    return f"до {days} рабочих дней"
```
Input: 1–60 (the model limits it). Tests T-F1.

### F2. `petitions/models.py`

- After `MAX_COMMENT_LENGTH = 2000` add `SUBJECT_MAX_LENGTH = 150`. Import `from petitions.terms import term_label` (with the other imports).
- `RequestType`: after `comment_hint` add
  `subject_required = models.BooleanField("нужно поле «Тип»", default=False)`.
- `RequestType.Meta.constraints`: append
  ```python
  models.CheckConstraint(
      condition=~models.Q(subject_required=True, comment_required=False),
      name="petitions_type_subject_needs_comment",
  ),
  ```
- `RequestType.clean()`: after the existing check add
  ```python
  if self.subject_required and not self.comment_required:
      raise ValidationError(
          "Если нужно поле «Тип», комментарий тоже должен быть обязательным."
      )
  ```
- `RequestType.term_label` property: `return term_label(self.processing_days)`.
- `Petition`: before `comment` add
  `subject = models.CharField("тип", max_length=SUBJECT_MAX_LENGTH, blank=True, default="")`.
- `Petition.display_name` property (above `short_id`):
  ```python
  @property
  def display_name(self) -> str:
      if self.subject:
          return f"{self.request_type.name}: {self.subject}"
      return self.request_type.name
  ```

### F3. Migration `petitions/0003_subject`

Expected operations (prototype): `AddField petition.subject`, `AddField requesttype.subject_required`, `AddConstraint petitions_type_subject_needs_comment`; dependency `0002_alter_petition_created_at_and_more`. Existing rows get `subject=""`, `subject_required=False` (constraint holds). Run `ruff format` on this file only.

### F4. `petitions/forms.py` `PetitionForm`

- Import `SUBJECT_MAX_LENGTH`.
- First field of the class (before `comment`):
  ```python
  subject = forms.CharField(
      label="Тип",
      max_length=SUBJECT_MAX_LENGTH,
      help_text="Что именно нужно, например: «Справка о периоде обучения».",
      error_messages={"required": "Укажите, что именно нужно."},
  )
  ```
- In `__init__`, after the comment settings: `if not request_type.subject_required: del self.fields["subject"]`.
- New method:
  ```python
  def clean_subject(self):
      subject = " ".join((self.cleaned_data.get("subject") or "").split())
      if not subject:
          raise forms.ValidationError("Укажите, что именно нужно.")
      return subject
  ```
  (Django calls `clean_subject` only if the field exists.)

### F5. `petitions/services.py` `submit_petition`

- New keyword parameter at the end: `subject: str = ""` (all existing callers keep working).
- After `comment = …`: `subject = " ".join((subject or "").split()) if request_type.subject_required else ""`.
- In the error block, after the comment check:
  ```python
  if request_type.subject_required and not subject:
      errors.append("Укажите, что именно нужно.")
  if len(subject) > SUBJECT_MAX_LENGTH:
      errors.append("Поле «Тип» слишком длинное.")
  ```
- `Petition.objects.create(..., subject=subject, ...)`. Import `SUBJECT_MAX_LENGTH`.

### F6. `petitions/views.py`

- `SubmitPetitionView.form_valid`: add `subject=form.cleaned_data.get("subject", ""),` to the `submit_petition` call.
- `CatalogView.get_context_data`: `types = RequestType.objects.filter(is_active=True).order_by("subject_required", "name")`.

### F7. Templates

- `catalog.html` (both sections): `· Срок: {{ type.processing_days }} раб. дн.` → `· Срок: {{ type.term_label }}`.
- `my_list.html`: link text `{{ petition.request_type.name }}` → `{{ petition.display_name }}`.
- `detail.html`: `<h1>{{ petition.request_type.name }}</h1>` → `<h1>{{ petition.display_name }}</h1>`.
- `staff_queue.html`: `· {{ petition.request_type.name }}` → `· {{ petition.display_name }}`.
- `staff_detail.html`: `<p>{{ petition.request_type.name }}</p>` → `<p>{{ petition.display_name }}</p>`.
- `submitted.html`: `<p>{{ petition.request_type.name }}</p>` → `<p>{{ petition.display_name }}</p>`.
- `form.html`: unchanged (`{{ form.as_p }}` renders the new field first).
- Nothing else changes (no CSS: `body { overflow-wrap: anywhere; }` already wraps long values).

### F8. `petitions/demo.py`

- Add a 7th element `False` to each of the 4 existing `REQUEST_TYPES` tuples, then append:
  ```python
  ("Справка в военкомат", "certificate", 3, True, "Укажите военкомат.",
   "Справка для военного комиссариата.", False),
  ("Другая справка", "certificate", 5, True, "Опишите, что нужно и для чего.",
   "Если нужной справки нет в списке.", True),
  ("Другое заявление", "application", 5, True, "Опишите, что нужно и для чего.",
   "Если нужного заявления нет в списке.", True),
  ```
  (format with ruff).
- Loop: `for name, kind, days, required, hint, description, subject_required in REQUEST_TYPES:` and add `"subject_required": subject_required` to `defaults`.
- Append to `PETITIONS`:
  ```python
  {
      "seed_key": "p-8",
      "student": "student1",
      "type": "Другая справка",
      "subject": "Справка о периоде обучения",
      "age": 3,
      "path": ["submitted", "in_progress"],
      "comment": "Нужна для оформления визы, с указанием дат начала и окончания обучения.",
  },
  ```
- In `Petition.objects.create(...)` add `subject=seed.get("subject", ""),`.
- Update the module docstring if it states the number of types (it does not today).

## Feasibility check

1. Clean starting point: re-checked on 2026-11-19 ~02:30 MSK after the TASK-013-FIX2 commit `ca9f30b`: `git status --short` shows only `?? docs/tasks/TASK-014.md`. The commits since the prototype (`8f469b2..ca9f30b`) touch no `petitions` file.
2. Referenced objects exist: `petitions/models.py` (`RequestType` with `comment_required`, `comment_hint`, `clean()`, constraint `petitions_type_days_1_60`; `Petition.comment`, `short_id`; `MAX_COMMENT_LENGTH`), `petitions/forms.py:PetitionForm` (`__init__(*, request_type)`, `clean_comment`), `petitions/services.py:submit_petition(student, request_type, comment, uploads)` (22 call sites in code and tests use 4 positional args), `petitions/views.py` (`CatalogView`, `SubmitPetitionView.form_valid`), `petitions/selectors.py:petitions_visible_to` (`select_related("request_type", …)`), templates (`catalog.html:9,19` "раб. дн."; `my_list.html:9`, `detail.html:3`, `staff_queue.html:30`, `staff_detail.html:9`, `submitted.html:4` show `request_type.name`), `petitions/demo.py` (`REQUEST_TYPES` 6-tuples, `PETITIONS` p-1…p-7, upsert by name), `petitions/admin.py`, `petitions/tests/helpers.py:make_type`, `accounts/management/commands/seed_demo.py:61` ("Requests ready: {p.types} types…"). "раб. дн." appears only in `catalog.html`.
3. New names are free: `subject_required`, `subject`, `SUBJECT_MAX_LENGTH`, `display_name`, `term_label`, `petitions/terms.py`, constraint `petitions_type_subject_needs_comment`, migration `0003_subject` (latest is `0002_alter_petition_created_at_and_more`), seed key `p-8`, type names "Справка в военкомат", "Другая справка", "Другое заявление".
4. Data and migrations: `makemigrations --check` clean before. Prototype in a temporary copy of HEAD (`$TMPDIR/t014/proj`, 2026-11-19 ~01:47 MSK): `makemigrations petitions --name subject` produced the three operations of F3; a database seeded with HEAD code ("Requests ready: 4 types, 7 requests, 3 attachments.") migrated OK; `seed_demo` then printed "7 types, 1 requests" and on the second run "7 types, 0 requests"; 7 old requests kept `subject=""`; `p-8` showed "Другая справка: Справка о периоде обучения"; `term_label` gave "до 3/5/10/15 рабочих дней"; `makemigrations --check` clean after.
5. Tools: Python 3.12 `.venv`, Django 5.2.19, ruff 0.17.4. No new dependency.
6. Framework: `forms.CharField(strip=True)` strips before `max_length` validation; `CheckConstraint(condition=~Q(a=True, b=False))` works on SQLite and PostgreSQL (same pattern as existing constraints).
7. Environment: no new env variables.
8. Verification on the clean tree (HEAD `ca9f30b`, 2026-11-19 ~02:28 MSK): `check` (no issues), `makemigrations --check` (no changes), `ruff check .` (passed), `ruff format --check .` (190 files formatted), `python manage.py test --parallel 1`: **Ran 1095 tests, OK** (log `/tmp/claude-501/test-20261118-152758.log`). Prototype full run with all of F1–F8 on the previous HEAD (log `/tmp/claude-501/test-t014-proto-20261118-144322.log`, ~01:46 MSK): the only failure is `petitions.tests.test_demo.PetitionsDemoTests.test_types_exact` (expects 4 types) — expected, updated below. The lists' query-count tests passed unchanged.
9. Conflicts: none.
10. Assumptions / blockers: none.

## Test plan

### Traceability

| AC | Tests |
|---|---|
| AC1 | `petitions/tests/test_models.py::RequestTypeSubjectTests::test_clean_requires_comment`, `::test_db_constraint`, `::test_admin_shows_flag` |
| AC2 | `petitions/tests/test_views.py::SubjectFormTests::test_subject_ignored_for_other_types` |
| AC3 | `SubjectFormTests::test_field_shown_only_with_flag`, `::test_subject_required_errors` (empty, spaces only, 151), `::test_subject_150_ok_and_normalised`, `::test_comment_required_for_catch_all`, `::test_military_comment_required` |
| AC4 | `petitions/tests/test_services.py::SubmitSubjectTests::*` |
| AC5 | `petitions/tests/test_terms.py::TermLabelTests::*`; `petitions/tests/test_views.py::CatalogTermTests::*` |
| AC6 | `petitions/tests/test_views.py::SubjectDisplayTests::*` |
| AC7 | `petitions/tests/test_demo.py::PetitionsDemoTests::test_types_exact` (updated), `::test_demo_subject_request`, `::test_idempotent` (unchanged), `::test_command_output` (updated) |
| AC8 | existing access tests and `QueryCountTests` (unchanged) + `QueryCountTests::test_lists_constant_with_subject` |

`petitions/tests/test_models.py` and `test_terms.py` are new files if they do not exist (check first; add the classes to an existing module only if it already holds model tests).

### Access matrix (unchanged views; existing tests cover each cell)

| Actor | catalog / form / submit | my list / detail | staff queue / detail |
|---|---|---|---|
| anonymous | 302 to login | 302 | 302 |
| student, own data | 200 | 200 | 403 |
| student, another student's petition | — | 404 (detail) | 403 |
| staff, own faculty | 403 | 403 | 200 |
| staff, other faculty | 403 | 403 | 404 (detail), not listed (queue) |
| superuser | 403 | 403 | 403 |

New: `SubjectDisplayTests::test_other_student_cannot_see_subject` — student B gets 404 on student A's "Другая справка" detail, and A's subject text is absent from B's list.

### Tests (file, class, method)

`petitions/tests/test_terms.py` — `TermLabelTests(SimpleTestCase)`:
- `test_singular_genitive`: 1, 21, 31, 51 → "до N рабочего дня".
- `test_plural_genitive`: 2, 3, 4, 5, 10, 11, 12, 14, 15, 20, 22, 60 → "до N рабочих дней".

`petitions/tests/test_models.py` — `RequestTypeSubjectTests(TestCase)`:
- `test_clean_requires_comment`: `RequestType(name="X", kind="certificate", processing_days=5, subject_required=True, comment_required=False).full_clean()` raises; with `comment_required=True, comment_hint="h"` it passes.
- `test_db_constraint`: `RequestType.objects.create(..., subject_required=True, comment_required=False)` inside `transaction.atomic()` raises `IntegrityError`.
- `test_term_label_property`: a type with `processing_days=21` → `term_label == "до 21 рабочего дня"`.
- `test_display_name`: petition with subject "А" → "Справка: А"; empty subject → "Справка".
- `test_admin_shows_flag`: superuser GET `admin:petitions_requesttype_changelist` → 200 and the column header for "нужно поле «Тип»"; GET the add form contains `name="subject_required"`.

`petitions/tests/test_services.py` — `SubmitSubjectTests(FrozenClockMixin, TestCase)` (catch-all type via `make_type(name="Другая справка", days=5, comment_required=True, hint="h", subject_required=True)`):
- `test_subject_stored_normalised`: `submit_petition(student, t, "коммент", [], subject="  Справка \n о периоде  ")` → `subject == "Справка о периоде"`.
- `test_subject_required`: `subject=""` and `subject="   "` → `ValidationError` with "Укажите, что именно нужно."; nothing created.
- `test_subject_length`: 150 characters → OK; 151 → `ValidationError` "Поле «Тип» слишком длинное."
- `test_subject_ignored_without_flag`: an ordinary type with `subject="X"` → stored `subject == ""`.
- `test_existing_positional_calls_still_work`: `submit_petition(student, ordinary_type, "", [])` works (no subject).

`petitions/tests/test_views.py`:
- `SubjectFormTests(FrozenClockMixin, TestCase)` (student logged in; types: catch-all, military `make_type(name="Справка в военкомат", comment_required=True, hint="Укажите военкомат.")`, ordinary):
  - `test_field_shown_only_with_flag`: GET the catch-all form contains `name="subject"` and `maxlength="150"` and the label "Тип", and `name="subject"` comes before `name="comment"`; GET the ordinary and the military forms do not contain `name="subject"`.
  - `test_subject_required_errors` (subTest): POST with subject "" / "   " / 151 × "а", comment "к" → 200, form error shown (for "" and spaces: "Укажите, что именно нужно."), no `Petition` created.
  - `test_subject_150_ok_and_normalised`: POST subject `"  " + "а" * 150 + "  "` → 302 to "submitted"; stored subject has 150 characters.
  - `test_comment_required_for_catch_all`: POST subject "Справка о периоде обучения", empty comment → 200 with "Для этой заявки комментарий обязателен."; no petition.
  - `test_military_comment_required`: POST to the military type with an empty comment → error; the hint "Укажите военкомат." is on the GET page.
  - `test_subject_ignored_for_other_types`: POST `subject=X` to the ordinary type → 302; stored `subject == ""`.
- `CatalogTermTests(TestCase)`:
  - `test_term_wording`: types with 1, 3, 5, 21 days → the page contains "Срок: до 1 рабочего дня", "Срок: до 3 рабочих дней", "Срок: до 5 рабочих дней", "Срок: до 21 рабочего дня"; "раб. дн." absent.
  - `test_catch_all_last`: in the certificates section, "Другая справка" appears after the other certificate names; same for "Другое заявление" among applications.
- `SubjectDisplayTests(FrozenClockMixin, TestCase)` (a catch-all petition with subject `'Справка <b>о периоде</b>'` for student A in faculty FX; staff of FX):
  - `test_student_list_and_detail`: `my_list` contains `Другая справка: Справка &lt;b&gt;о периоде&lt;/b&gt;`; the detail `h1` contains the same escaped text; the raw `<b>` is absent.
  - `test_staff_queue_and_detail`: the same escaped text in the staff queue and staff detail.
  - `test_submitted_page`: after a POST submission, the "submitted" page shows the display name.
  - `test_other_student_cannot_see_subject`: see Access matrix.
  - `test_plain_type_unchanged`: an ordinary petition shows only the type name (no ": ").
- `QueryCountTests::test_lists_constant_with_subject`: like `test_my_list_constant_queries`/`test_staff_queue_constant_queries`, but the 5 added petitions are of a catch-all type with a subject; counts equal the base counts.

`petitions/tests/test_demo.py`:
- `test_types_exact` (update with `# TASK-014: 3 new types`): expected set of 7 tuples `(name, kind, days, comment_required, subject_required)`; `types.count() == 7`.
- New `test_demo_subject_request`: `Petition.objects.get(seed_key="p-8")` has type "Другая справка", subject "Справка о периоде обучения", student `student1`, `display_name == "Другая справка: Справка о периоде обучения"`; all other demo petitions have `subject == ""`; every type with `subject_required` has `comment_required`.
- `test_command_output`: assert "Requests ready: 7 types" in the output.
- `test_idempotent`: unchanged, must pass.

`petitions/tests/helpers.py`: `make_type(name="Справка", kind="certificate", days=3, comment_required=False, hint="", subject_required=False)`.

### Edge cases

Empty / spaces-only / 150 / 151 characters; newlines and tabs inside the subject; HTML in the subject (escaped); a subject posted to a type without the flag; a type flagged without a required comment (model and DB); 1, 21 and 11 days.

### Settings branches

None.

## Implementation order

1. F1 + `test_terms.py`. 2. F2, F3, helpers; `test_models.py`. 3. F4, F5, F6; service and form tests. 4. F7; display and catalog tests. 5. F8; demo tests; `seed_demo` twice on a temporary DB. 6. Admin, README. 7. Full verification.

## Verification

```bash
source .venv/bin/activate
python manage.py check
DEBUG=false ALLOWED_HOSTS=example.com ADMIN_URL=ci-staff-panel/ SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop python manage.py check --deploy --fail-level WARNING
python manage.py makemigrations --check --dry-run
python manage.py test --parallel 1 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log"
python scripts/run_tests_at.py 2026-11-20T00:00:00 2>&1 | tee "$TMPDIR/test-midnight-$(date +%Y%m%d-%H%M%S).log"
# seed twice on a fresh temporary DB, and migrate a DB seeded BEFORE the change:
export DEMO_PASSWORD='Local-Demo-Pass-2026!' PRIVATE_MEDIA_ROOT="$TMPDIR/t014-pm"
DATABASE_URL="sqlite:///$TMPDIR/t014-fresh.sqlite3" python manage.py migrate && DATABASE_URL="sqlite:///$TMPDIR/t014-fresh.sqlite3" python manage.py seed_demo && DATABASE_URL="sqlite:///$TMPDIR/t014-fresh.sqlite3" python manage.py seed_demo
mkdir -p "$TMPDIR/t014-before" && git archive HEAD | tar -x -C "$TMPDIR/t014-before"
#   in "$TMPDIR/t014-before" (no .env): DEBUG=true SECRET_KEY=<50+ char dummy> + the exports above,
#   DATABASE_URL="sqlite:///$TMPDIR/t014-before.sqlite3" python manage.py migrate && ... seed_demo
#   then in the project: DATABASE_URL="sqlite:///$TMPDIR/t014-before.sqlite3" python manage.py migrate, seed_demo twice
ruff check <the Python files of this task>
ruff format --check <the Python files of this task>
git status --short
```
- Never touch `db.sqlite3` or the project's `private_media/`. `git archive` only reads git; never run `git stash`/`checkout`/`worktree`.
- If any run fails or stalls, even once, put the test name, the Moscow time and the traceback excerpt into the REPORT.

## Risks

- **User text in a heading.** A 150-character subject makes a long pixel-font `h1` on the student detail page; it wraps (no horizontal scroll). The Team lead checks 360 px.
- **Data integrity.** The DB constraint covers the type flag; a petition's subject vs its type is enforced by the form and the service (two layers), not by the DB (cross-table).
- **Seed upsert** sets `subject_required` on existing types by name; an admin who renamed a demo type would get a new one (existing behaviour of the seed).
