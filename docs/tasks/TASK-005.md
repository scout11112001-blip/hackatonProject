# TASK-005: Grades, session results, debts, attendance (+ 2 schedule UI fixes)

Author: Planner. Status: ready for implementation.
Base commit: `e7aa72a`. Product context: `plan.md`. Reused: `docs/tasks/TASK-002.md` (access pattern), `docs/tasks/TASK-003.md` (occurrence identity `(weekly_lesson, original_date)`, `occurrences_between`), `docs/tasks/TASK-004.md` (validation at model/service level, non-field errors).

The user wants this **as simple as possible**: plain lists, native `<details>`, no JavaScript, no charts.

---

## 1. Goal

A student opens `/grades/` and sees "how am I doing": a status line (debts), averages, and per discipline of the selected term — assessment form, current marks, final result (with retake history), attendance summary. Staff see the same report, read-only, for students of their own faculty.

## 2. Acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | New app `academics` with `Term`, `CurriculumItem`, `CurrentMark`, `FinalResult`, `Attendance`; migrations exist; `makemigrations --check` clean. |
| AC2 | All business rules are enforced in model `clean()` with **non-field** errors and in DB constraints where possible; admin shows form errors, never 500. |
| AC3 | Retakes: several attempts per (student, curriculum item); the highest attempt number is the effective result; history is shown. |
| AC4 | Attendance references an occurrence `(weekly_lesson, original_date)`; rejected for: wrong group, no lesson on that date, cancelled occurrence, future occurrence, duplicate. Status is only present / absent / excused. |
| AC5 | Pure service functions compute: effective results, term and overall averages (2 decimals, half-up), debts (finished session, failing or missing result), attendance summary (present, absent, excused, unmarked, percent), status line. |
| AC6 | `/grades/` shows status line, overall and term averages, term selector (links), one `<details>` entry per discipline, debts marked, empty state. `/grades/<term_code>/` selects a term; unknown code → 404. No student/curriculum/grade IDs in student URLs. |
| AC7 | Staff report `/staff/students/<pk>/grades/[<term_code>/]` for own-faculty students (link from the staff student detail page); another faculty → 404; students → 403. |
| AC8 | Navigation shows "Успеваемость" for students only. |
| AC9 | Grades page and staff report run a constant number of queries. |
| AC10 | `seed_demo` (idempotent) adds a finished previous term with results (one retake, one open debt) and the current term with marks and attendance for past occurrences; students differ visibly; renders weeks later without reseeding. |
| AC11 | Schedule UI fixes: no "К списку групп" link on the student week page; change label renders without a space before the period. |

## 3. Out of scope

Teacher accounts, grade entry outside admin, notifications, rating, GPA tables, exports, charts, visual theme, other `plan.md` tech-debt items, linking attendance to curriculum items, attendance of the previous term in demo data, grade-improvement retakes (a new attempt after a positive result is rejected).

---

## 4. Design decisions

### 4.1 New app `academics`
Grades and attendance are a separate bounded context: own models, rules, services and pages. It depends on `university` (groups, disciplines), `accounts` (students, access) and `schedule` (occurrences). Nothing in those apps imports `academics` (exception: two templates link to `academics` URLs — `base.html` nav and `accounts/student_detail.html`). Notifications will later read `academics.services`.

### 4.2 One `result` field for final results
`FinalResult.result` is a single choice field: `"5"`, `"4"`, `"3"`, `"2"`, `"pass"`, `"fail"`. The assessment form decides the allowed subset (exam / graded credit → `2..5`; credit → `pass/fail`). One field is simpler than `grade` + `passed` and makes "numeric on a credit" a plain set-membership check.

### 4.3 Definitions (used everywhere)
- **Effective result** of (student, curriculum item) = the `FinalResult` with the highest `attempt`.
- **Positive** result: `5`, `4`, `3`, `pass`. **Failing**: `2`, `fail`.
- **Average** = arithmetic mean of numeric effective results (`2..5`, **including 2**), `Decimal` rounded to 2 places with `ROUND_HALF_UP`; `None` when there are no numeric results. Current marks never enter averages.
- **Session finished**: `today > term.session_end`.
- **Debt**: curriculum item of a term whose session is finished and whose effective result is missing or failing.
- **Status line**: `"Всё в порядке"` if 0 debts in all terms, else `f"Есть задолженности: {n}"`. Attendance is not part of it.
- **Attendance percent** = `present / (present + absent) * 100`, rounded half-up to an integer; `None` if `present + absent == 0`. **Excused absences are marked but excluded from the percent** (an excused absence must not lower attendance; "all excused" → `None`, shown as "—"). Counts of all three statuses are shown.
- **Past occurrence**: a happening occurrence (`ScheduleItem.is_happening`) whose displayed date `item.date < today`. **Unmarked** = past occurrence without an attendance record; shown as «не отмечено», not an absence. Today's lessons are not "past" yet but may already be marked.
- **Term of an occurrence**: `term.start_date <= item.date <= term.end_date`. Attendance is grouped by `item.lesson.discipline`; only disciplines that have a curriculum item for the student in the term are shown.
- **Current term** (`current_term(today)`): the term containing `today`; else the most recent term that ended before `today`; else the earliest future term; else `None`.

### 4.4 Validation layer
Same pattern as TASK-004: every rule is in `Model.clean()` and raises **non-field** `ValidationError`s (a field key absent from a form would cause a 500). Code writes go through `academics/mutations.save_validated()` (`full_clean()` + `save()` in a transaction). Admin uses default `ModelForm`s, so `clean()` always runs.

### 4.5 Later tasks (do not implement)
Notifications can call `student_overview(student, today).debts` and query `FinalResult` by `created_at` for "new final results".

---

## 5. Architecture

### 5.1 Files

Create:
```
academics/__init__.py
academics/apps.py
academics/models.py
academics/services.py
academics/mutations.py
academics/admin.py
academics/views.py
academics/urls.py
academics/demo.py
academics/migrations/__init__.py
academics/migrations/0001_initial.py                       (generated)
academics/templates/academics/report.html
academics/templates/academics/includes/discipline.html
academics/tests/__init__.py
academics/tests/helpers.py
academics/tests/test_models.py
academics/tests/test_services.py
academics/tests/test_views.py
academics/tests/test_demo.py
```
Change:
```
config/settings.py (INSTALLED_APPS), config/urls.py, pyproject.toml (known-first-party),
templates/base.html (nav), accounts/templates/accounts/student_detail.html (link),
accounts/management/commands/seed_demo.py, static/css/base.css,
schedule/templates/schedule/week.html, schedule/templates/schedule/includes/lesson_item.html,
schedule/tests/test_views.py (2 regression tests), README.md
```
No other files. No new dependencies. Do not change `.env.example` (no new env variables).

### 5.2 Wiring
- `INSTALLED_APPS`: add `"academics"` after `"schedule"`.
- `config/urls.py`: `path("", include("academics.urls"))` after the `schedule` include.
- `pyproject.toml`: `known-first-party = ["config", "core", "accounts", "university", "schedule", "academics"]`.
- `AcademicsConfig`: `name = "academics"`, `verbose_name = "Успеваемость"`, `default_auto_field = "django.db.models.BigAutoField"`.

### 5.3 Models (`academics/models.py`)

All models: Russian `verbose_name`s, `__str__`, ruff DJ012 order. Enums:
```python
class AssessmentForm(models.TextChoices):
    EXAM = "exam", "Экзамен"
    CREDIT = "credit", "Зачёт"
    GRADED_CREDIT = "graded_credit", "Дифференцированный зачёт"


class ResultValue(models.TextChoices):
    FIVE = "5", "Отлично (5)"
    FOUR = "4", "Хорошо (4)"
    THREE = "3", "Удовлетворительно (3)"
    TWO = "2", "Неудовлетворительно (2)"
    PASS = "pass", "Зачтено"
    FAIL = "fail", "Не зачтено"


NUMERIC_RESULTS = {"5", "4", "3", "2"}
PASS_FAIL_RESULTS = {"pass", "fail"}
POSITIVE_RESULTS = {"5", "4", "3", "pass"}


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Присутствовал"
    ABSENT = "absent", "Отсутствовал"
    EXCUSED = "excused", "Уважительная причина"
```

**`Term`**
| Field | Definition |
|---|---|
| `code` | `SlugField("код", max_length=30, unique=True)` — public, used in URLs, e.g. `2026-autumn` |
| `name` | `CharField("название", max_length=100)` |
| `start_date` | `DateField("начало")` |
| `end_date` | `DateField("окончание")` (inclusive; includes the session) |
| `session_start` | `DateField("начало сессии")` |
| `session_end` | `DateField("окончание сессии")` |
- `Meta`: `ordering = ["-start_date"]`; constraint `CheckConstraint(condition=Q(start_date__lte=F("session_start")) & Q(session_start__lte=F("session_end")) & Q(session_end__lte=F("end_date")), name="academics_term_dates_order")`.
- `__str__` → `self.name`.
- `clean()`: if all four dates set: order violated → `ValidationError("Даты должны идти по порядку: начало ≤ начало сессии ≤ конец сессии ≤ окончание.")`; overlap with another term (`Term.objects.exclude(pk=self.pk).filter(start_date__lte=self.end_date, end_date__gte=self.start_date)` exists) → `ValidationError("Семестр пересекается с семестром «<name>».")`.

**`CurriculumItem`**
| Field | Definition |
|---|---|
| `group` | `ForeignKey("university.StudyGroup", PROTECT, related_name="curriculum_items")` |
| `discipline` | `ForeignKey("university.Discipline", PROTECT, related_name="curriculum_items")` |
| `term` | `ForeignKey(Term, PROTECT, related_name="curriculum_items")` |
| `assessment_form` | `CharField("форма контроля", max_length=16, choices=AssessmentForm.choices)` |
| `credits` | `PositiveSmallIntegerField("зачётные единицы", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(30)])` |
- `Meta`: `ordering = ["term", "discipline__name"]`; `UniqueConstraint(fields=["group", "discipline", "term"], name="academics_curriculum_unique")`; `CheckConstraint(condition=Q(credits__isnull=True) | (Q(credits__gte=1) & Q(credits__lte=30)), name="academics_curriculum_credits_range")`.
- `__str__` → `f"{self.discipline} — {self.group} ({self.term})"`.
- Property `allowed_results -> set[str]`: `PASS_FAIL_RESULTS` if `CREDIT` else `NUMERIC_RESULTS`.

**`CurrentMark`**
| Field | Definition |
|---|---|
| `student` | `ForeignKey("accounts.StudentProfile", CASCADE, related_name="current_marks")` |
| `curriculum_item` | `ForeignKey(CurriculumItem, PROTECT, related_name="current_marks")` |
| `value` | `PositiveSmallIntegerField("оценка", validators=[MinValueValidator(2), MaxValueValidator(5)])` |
| `date` | `DateField("дата")` |
| `kind` | `CharField("вид работы", max_length=100)` — e.g. «Семинар», «Контрольная работа» |
| `seed_key` | `SlugField("ключ демо-данных", max_length=80, blank=True, default="", editable=False)` |
- `Meta`: `ordering = ["date", "pk"]`; `CheckConstraint(condition=Q(value__gte=2) & Q(value__lte=5), name="academics_mark_value_2_5")`; `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="academics_mark_unique_seed_key")`.
- `__str__` → `f"{self.value} ({self.date:%d.%m.%Y})"`.
- `clean()` (skip a check if a required FK/value is `None`):
  - `student.group_id != curriculum_item.group_id` → `"Студент не из группы этого учебного плана."`;
  - `date` outside `[term.start_date, term.end_date]` → `"Дата вне семестра."`;
  - `date > timezone.localdate()` → `"Дата оценки в будущем."`.

**`FinalResult`**
| Field | Definition |
|---|---|
| `student` | `ForeignKey("accounts.StudentProfile", CASCADE, related_name="final_results")` |
| `curriculum_item` | `ForeignKey(CurriculumItem, PROTECT, related_name="final_results")` |
| `attempt` | `PositiveSmallIntegerField("попытка", default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])` |
| `result` | `CharField("результат", max_length=8, choices=ResultValue.choices)` |
| `date` | `DateField("дата")` |
| `created_at` | `DateTimeField("создано", auto_now_add=True)` |
- `Meta`: `ordering = ["curriculum_item", "attempt"]`; `UniqueConstraint(fields=["student", "curriculum_item", "attempt"], name="academics_result_unique_attempt")`; `CheckConstraint(condition=Q(attempt__gte=1) & Q(attempt__lte=5), name="academics_result_attempt_1_5")`; `CheckConstraint(condition=Q(result__in=["5", "4", "3", "2", "pass", "fail"]), name="academics_result_value")`.
- Properties: `is_numeric` (`result in NUMERIC_RESULTS`), `numeric_value -> int | None`, `is_positive` (`result in POSITIVE_RESULTS`).
- `__str__` → `f"{self.get_result_display()} (попытка {self.attempt})"`.
- `clean()` (skip checks whose inputs are `None`):
  1. `result not in curriculum_item.allowed_results` → `"Для формы контроля «<form>» допустимы только: <labels>."` (labels joined by `", "`).
  2. student not in item group → same message as `CurrentMark`.
  3. `date < term.start_date` → `"Дата раньше начала семестра."`; `date > timezone.localdate()` → `"Дата результата в будущем."`.
  4. `others = FinalResult.objects.filter(student=…, curriculum_item=…).exclude(pk=self.pk)`:
     - if `attempt > 1`: `prev = others.filter(attempt=attempt - 1).first()`; `prev is None` → `"Сначала внесите попытку <attempt-1>."`; `prev.is_positive` → `"Предыдущая попытка уже успешна — пересдача не нужна."`; `date < prev.date` → `"Пересдача не может быть раньше предыдущей попытки."`;
     - if `self.is_positive` and `others.filter(attempt__gt=attempt).exists()` → `"После успешной попытки не может быть следующих попыток."`.

**`Attendance`**
| Field | Definition |
|---|---|
| `student` | `ForeignKey("accounts.StudentProfile", CASCADE, related_name="attendance_records")` |
| `weekly_lesson` | `ForeignKey("schedule.WeeklyLesson", PROTECT, related_name="attendance_records")` |
| `original_date` | `DateField("дата занятия по расписанию")` |
| `status` | `CharField("статус", max_length=10, choices=AttendanceStatus.choices)` |
- `Meta`: `ordering = ["original_date"]`; `UniqueConstraint(fields=["student", "weekly_lesson", "original_date"], name="academics_attendance_one_per_occurrence")`; `CheckConstraint(condition=Q(status__in=["present", "absent", "excused"]), name="academics_attendance_status")`; `Index(fields=["student", "original_date"], name="academics_att_student_date_idx")`.
- `__str__` → `f"{self.get_status_display()} — {self.weekly_lesson} ({self.original_date:%d.%m.%Y})"`.
- `clean()` — calls `validate_occurrence_for_student(student, weekly_lesson, original_date, today=timezone.localdate())` (6.1) and raises `ValidationError(errors)` if the list is non-empty. Duplicate (same student + occurrence): `validate_unique()` in `full_clean()` reports it (all three fields are in the admin form); `save_validated` also runs it. DB unique constraint is the last line.

### 5.4 URLs (`academics/urls.py`, `app_name = "academics"`)
| Path | View | Name |
|---|---|---|
| `grades/` | `StudentGradesView` | `my_grades` |
| `grades/<slug:term_code>/` | `StudentGradesView` | `my_grades_term` |
| `staff/students/<int:pk>/grades/` | `StaffStudentGradesView` | `staff_student_grades` |
| `staff/students/<int:pk>/grades/<slug:term_code>/` | `StaffStudentGradesView` | `staff_student_grades_term` |

`pk` = `StudentProfile.pk` (same as the existing staff student detail URL).

### 5.5 Navigation and links
- `templates/base.html`: inside `{% if user.is_student %}` (the existing schedule item block) add after the schedule item: `<li><a href="{% url 'academics:my_grades' %}">Успеваемость</a></li>`.
- `accounts/templates/accounts/student_detail.html`: before the back link add `<p><a href="{% url 'academics:staff_student_grades' student.pk %}">Успеваемость и посещаемость</a></p>`.

### 5.6 Admin (`academics/admin.py`)
Default `ModelForm`s (all fields). `TermAdmin` (`list_display = ("code", "name", "start_date", "end_date", "session_start", "session_end")`, `search_fields = ("code", "name")`); `CurriculumItemAdmin` (`list_display = ("discipline", "group", "term", "assessment_form", "credits")`, `list_filter = ("term", "group", "assessment_form")`, `list_select_related = ("discipline", "group", "term")`); `CurrentMarkAdmin` (`list_display = ("student", "curriculum_item", "value", "date", "kind")`, `list_filter = ("curriculum_item__term",)`, `readonly_fields = ("seed_key",)`, `list_select_related = ("student", "curriculum_item__discipline")`); `FinalResultAdmin` (`list_display = ("student", "curriculum_item", "attempt", "result", "date")`, `list_filter = ("curriculum_item__term", "result")`, `list_select_related`); `AttendanceAdmin` (`list_display = ("student", "weekly_lesson", "original_date", "status")`, `list_filter = ("status",)`, `date_hierarchy = "original_date"`, `list_select_related = ("student", "weekly_lesson__discipline")`). Search: `student__last_name` where a student FK exists.

---

## 6. Functions

### 6.1 `academics/services.py` — validation helper

```python
def validate_occurrence_for_student(student: StudentProfile | None, lesson: WeeklyLesson | None, original_date: date | None, today: date) -> list[str]
```
- Purpose: one place that decides whether an attendance record may reference this occurrence.
- Algorithm (return Russian messages; empty = OK):
  1. If any of `student`, `lesson`, `original_date` is `None` → `[]` (Django reports missing fields).
  2. `group_ids = set(lesson.groups.values_list("id", flat=True))`; `student.group_id not in group_ids` → `"Студент не относится к группам этого занятия."`.
  3. `original_date.weekday() != lesson.weekday` or not `lesson.valid_from <= original_date <= lesson.valid_until` → `"В эту дату этого занятия нет по расписанию."`; return immediately (later checks are meaningless).
  4. `change = LessonChange.objects.filter(weekly_lesson=lesson, original_date=original_date).first()`; `change` and `change.kind == CANCELLED` → `"Занятие отменено."`.
  5. `effective = change.new_date if change and change.kind == MOVED else original_date`; `effective > today` → `"Нельзя отметить посещение будущего занятия."`.
  6. Return the list.
- Tests: see section 7 (TP-M*).

### 6.2 `academics/services.py` — read side

Dataclasses (all `frozen=True`):
```python
class AttendanceSummary:
    present: int; absent: int; excused: int; unmarked: int
    @property marked -> int           # present + absent + excused
    @property percent -> int | None   # 4.3 rule

class AttendanceEntry:
    date: date                 # displayed date (item.date)
    original_date: date
    lesson_type: str           # item.lesson.get_lesson_type_display()
    status: str | None         # AttendanceStatus value or None (unmarked)
    status_label: str          # Russian label or "не отмечено"

class DisciplineReport:
    item: CurriculumItem
    marks: list[CurrentMark]
    attempts: list[FinalResult]        # ascending attempt
    effective: FinalResult | None
    is_debt: bool
    attendance: AttendanceSummary
    attendance_entries: list[AttendanceEntry]   # ascending date

class TermReport:
    term: Term
    session_finished: bool
    disciplines: list[DisciplineReport]         # by discipline name
    average: Decimal | None

class StudentOverview:
    debts: list[CurriculumItem]                 # across all terms, ordered by term start, discipline name
    status_text: str
    overall_average: Decimal | None
```

Pure functions (no DB, no clock):

#### `effective_results(results: Iterable[FinalResult]) -> dict[int, FinalResult]`
Key `curriculum_item_id` → result with max `attempt`. Tests: single attempt; retake (attempt 2 wins even if its `pk` is smaller); empty → `{}`.

#### `average_grade(results: Iterable[FinalResult]) -> Decimal | None`
`values = [r.numeric_value for r in results if r.is_numeric]`; empty → `None`; else `(Decimal(sum(values)) / Decimal(len(values))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. Callers pass **effective** results only. Tests: `[5, 4, 4]` → `4.33`; `[5, 4]` → `4.50`; `[4, 5, 5]` → `4.67`; half-up case `[4, 5, 4, 5, 4, 5, 4, 4]` (`4.375`) → `4.38`; only pass/fail → `None`; includes `2`.

#### `is_debt(item: CurriculumItem, effective: FinalResult | None, today: date) -> bool`
`today > item.term.session_end and (effective is None or not effective.is_positive)`. Tests: session not finished + missing → `False`; finished + missing → `True`; finished + `2` → `True`; finished + `fail` → `True`; finished + `3` → `False`; failing attempt 1 then positive attempt 2 → `False`; boundary `today == session_end` → `False`, `session_end + 1` → `True`.

#### `status_text(debt_count: int) -> str`
`0` → `"Всё в порядке"`; else `f"Есть задолженности: {debt_count}"`.

#### `summarize_attendance(occurrences: Iterable[ScheduleItem], records: Mapping[tuple[int, date], str], today: date) -> tuple[AttendanceSummary, list[AttendanceEntry]]`
- `occurrences`: happening items of one discipline (already filtered); `records`: `{(weekly_lesson_id, original_date): status}` of the student.
- Algorithm: for each item (sorted by `item.date`, `item.slot.number`): `key = (item.lesson.id, item.original_date)`; `status = records.get(key)`; if `status` → count it and add an entry; elif `item.date < today` → `unmarked += 1` and add an entry with `status=None`, label «не отмечено»; else (today/future, not marked) → skip. Build the summary.
- Tests: all present → 100; 3 present / 1 absent → 75; 2 present / 1 absent → 67 (half-up of 66.67); all excused → `percent None`, `marked == 3`; no records, 2 past → `unmarked 2`, `percent None`; future unmarked item not counted; today's marked item counted, today's unmarked not counted; record for a key not in `occurrences` is ignored.

#### `current_term(today: date) -> Term | None`  (1 query)
`terms = list(Term.objects.all())`; return per 4.3 rule. Tests: inside; between terms → previous; before all terms → earliest; no terms → `None`.

#### `student_terms(student: StudentProfile) -> list[Term]`  (1 query)
Terms with a curriculum item of the student's group or with the student's marks/results: `Term.objects.filter(Q(curriculum_items__group_id=student.group_id) | Q(curriculum_items__final_results__student=student) | Q(curriculum_items__current_marks__student=student)).distinct().order_by("-start_date")`.

#### `student_term_report(student: StudentProfile, term: Term, today: date) -> TermReport`
Query budget: constant (≤ 9 queries including `occurrences_between`'s 4).
1. `items = list(CurriculumItem.objects.filter(term=term).filter(Q(group_id=student.group_id) | Q(final_results__student=student) | Q(current_marks__student=student)).distinct().select_related("discipline", "term", "group"))`.
2. `marks = list(CurrentMark.objects.filter(student=student, curriculum_item__term=term).order_by("date", "pk"))` → group by `curriculum_item_id`.
3. `results = list(FinalResult.objects.filter(student=student, curriculum_item__term=term).order_by("attempt"))` → group by item; `eff = effective_results(results)`.
4. Attendance: if `today < term.start_date` → no occurrences; else `end = min(term.end_date, today)`; `occ = [i for i in occurrences_between(term.start_date, end, [student.group_id]) if i.is_happening]`; `records = {(a.weekly_lesson_id, a.original_date): a.status for a in Attendance.objects.filter(student=student, weekly_lesson_id__in={i.lesson.id for i in occ})}` (filter by lesson ids, not by date: a moved occurrence's `original_date` may lie outside the term).
5. For each item: `discipline_occ = [i for i in occ if i.lesson.discipline_id == item.discipline_id]`; `summary, entries = summarize_attendance(discipline_occ, records, today)`; `DisciplineReport(item, marks_by_item.get(item.id, []), results_by_item.get(item.id, []), eff.get(item.id), is_debt(item, eff.get(item.id), today), summary, entries)`.
6. Sort by `item.discipline.name`. `average = average_grade(eff.values())`. `session_finished = today > term.session_end`.
- Access: callers pass only a student they are allowed to see.

#### `student_overview(student: StudentProfile, today: date) -> StudentOverview`  (2 queries)
1. `items = list(CurriculumItem.objects.filter(Q(group_id=student.group_id) | Q(final_results__student=student)).distinct().select_related("term", "discipline"))`.
2. `eff = effective_results(FinalResult.objects.filter(student=student))`.
3. `debts = [i for i in items if is_debt(i, eff.get(i.id), today)]`, sorted by `(i.term.start_date, i.discipline.name)`.
4. `overall_average = average_grade(eff.values())`; `status_text(len(debts))`.

### 6.3 `academics/mutations.py`
```python
def save_validated(instance: models.Model) -> models.Model
```
`with transaction.atomic(): instance.full_clean(); instance.save(); return instance`. The only write path for `academics` models in code (seed, tests that test valid data).

### 6.4 Views (`academics/views.py`)

```python
class StudentGradesView(StudentRequiredMixin, TemplateView):
    template_name = "academics/report.html"
```
`get_context_data`: `today = timezone.localdate()`; `student = self.profile`; `context.update(_report_context(student, today, self.kwargs.get("term_code"), url_name="academics:my_grades_term", url_kwargs={}))`; `context["is_staff_view"] = False`.

```python
class StaffStudentGradesView(StaffRequiredMixin, TemplateView):
    template_name = "academics/report.html"
```
`get_context_data`: `student = get_object_or_404(students_visible_to(self.request.user), pk=self.kwargs["pk"])`; same `_report_context(..., url_name="academics:staff_student_grades_term", url_kwargs={"pk": student.pk})`; `context["is_staff_view"] = True`; `context["student"] = student`; `context["back_url"] = reverse("accounts:staff_student_detail", args=[student.pk])`.

```python
def _report_context(student: StudentProfile, today: date, term_code: str | None, url_name: str, url_kwargs: dict[str, Any]) -> dict[str, Any]
```
1. `terms = student_terms(student)`.
2. If `term_code`: `term = get_object_or_404(Term, code=term_code)` (any existing term is allowed; data is always filtered by `student`). Else `term = current_term(today)`.
3. `report = student_term_report(student, term, today) if term else None`.
4. Selector entries: for each `t` in `terms` (plus `term` if not in `terms`, ordered by `-start_date`): `{"term": t, "url": reverse(url_name, kwargs={**url_kwargs, "term_code": t.code}), "is_selected": t == term}`.
5. Return `{"overview": student_overview(student, today), "term": term, "report": report, "term_links": [...], "today": today}`.

### 6.5 Templates

`academics/report.html` (extends `base.html`):
```
<h1>{% if is_staff_view %}Успеваемость: {{ student.full_name }}{% else %}Моя успеваемость{% endif %}</h1>
{% if is_staff_view %}<p><a href="{{ back_url }}">← К карточке студента</a></p>{% endif %}
<p class="status {% if overview.debts %}status--debt{% else %}status--ok{% endif %}"><strong>{{ overview.status_text }}</strong></p>
{% if overview.debts %}<ul class="debt-list">{% for item in overview.debts %}<li>{{ item.discipline.name }} — {{ item.term.name }}</li>{% endfor %}</ul>{% endif %}
<p>Средний балл за всё время: {{ overview.overall_average|default:"—" }}</p>
{% if term_links %}<nav class="term-nav" aria-label="Семестры"><ul>{% for link in term_links %}<li>{% if link.is_selected %}<strong>{{ link.term.name }}</strong>{% else %}<a href="{{ link.url }}">{{ link.term.name }}</a>{% endif %}</li>{% endfor %}</ul></nav>{% endif %}
{% if not term %}<p>Семестров пока нет.</p>
{% else %}
  <h2>{{ term.name }}</h2>
  <p>Сессия: {{ term.session_start|date:"j E" }} — {{ term.session_end|date:"j E Y" }}{% if report.session_finished %} (завершена){% endif %}</p>
  <p>Средний балл за семестр: {{ report.average|default:"—" }}</p>
  {% if report.disciplines %}<ul class="discipline-list">{% for d in report.disciplines %}{% include "academics/includes/discipline.html" %}{% endfor %}</ul>
  {% else %}<p>За этот семестр данных нет.</p>{% endif %}
{% endif %}
```
`academics/includes/discipline.html` (expects `d`):
```
<li class="discipline{% if d.is_debt %} discipline--debt{% endif %}">
  <details>
    <summary>
      <strong>{{ d.item.discipline.name }}</strong> · {{ d.item.get_assessment_form_display }}
      · Итог: {% if d.effective %}{{ d.effective.get_result_display }}{% else %}нет{% endif %}
      {% if d.is_debt %}· <strong>Задолженность</strong>{% endif %}
      · Посещаемость: {% if d.attendance.percent is not None %}{{ d.attendance.percent }}%{% else %}—{% endif %}
    </summary>
    <h3>Текущие оценки</h3>
    {% if d.marks %}<ul>{% for m in d.marks %}<li>{{ m.date|date:"j E" }} — {{ m.kind }}: {{ m.value }}</li>{% endfor %}</ul>{% else %}<p>Оценок нет.</p>{% endif %}
    <h3>Итоговый результат</h3>
    {% if d.attempts %}<ul>{% for r in d.attempts %}<li>Попытка {{ r.attempt }}, {{ r.date|date:"j E Y" }}: {{ r.get_result_display }}{% if r == d.effective %} (действующий){% endif %}</li>{% endfor %}</ul>{% else %}<p>Результата пока нет.</p>{% endif %}
    <h3>Посещаемость</h3>
    <p>Присутствовал: {{ d.attendance.present }}, отсутствовал: {{ d.attendance.absent }}, по уважительной причине: {{ d.attendance.excused }}, не отмечено: {{ d.attendance.unmarked }}.</p>
    {% if d.attendance_entries %}<ul>{% for e in d.attendance_entries %}<li>{{ e.date|date:"j E" }} ({{ e.lesson_type }}) — {{ e.status_label }}</li>{% endfor %}</ul>{% endif %}
  </details>
</li>
```
(`r == d.effective` compares model instances by pk — fine.)

CSS (`static/css/base.css`, tokens only, one declaration per line): `.discipline-list { list-style: none; padding: 0; }`, `.discipline { border-top: 1px solid var(--color-border); padding: var(--space-2) 0; }`, `.discipline--debt summary, .status--debt { color: var(--color-changed); }`, `.term-nav ul { display: flex; flex-wrap: wrap; gap: var(--space-3); list-style: none; padding: 0; }`, `details summary { cursor: pointer; }`.

### 6.6 Demo data (`academics/demo.py`)

```python
@dataclass(frozen=True)
class AcademicsSeedSummary:
    terms: int; curriculum_items: int; marks: int; results: int; attendance: int

def term_bounds(day: date) -> tuple[str, str, date, date, date, date]
def seed_academics_demo(today: date) -> AcademicsSeedSummary
```
`term_bounds(day)` → `(code, name, start, end, session_start, session_end)`:
- `month >= 9` → autumn of `Y = day.year`; `month == 1` → autumn of `Y = day.year - 1`: `code=f"{Y}-autumn"`, `name=f"Осенний семестр {Y}/{Y + 1}"`, `start=date(Y, 9, 1)`, `end=date(Y + 1, 1, 31)`, session `date(Y + 1, 1, 10)`…`date(Y + 1, 1, 31)`.
- otherwise (Feb–Aug) → spring of `Y = day.year`: `code=f"{Y}-spring"`, `name=f"Весенний семестр {Y}"`, `start=date(Y, 2, 1)`, `end=date(Y, 8, 31)`, session `date(Y, 6, 1)`…`date(Y, 6, 30)`.
Terms tile the calendar without overlap. Tests: 2026-11-18 → `2026-autumn`; 2027-01-15 → `2026-autumn`; 2027-03-01 → `2027-spring`; `term_bounds(start - 1 day)` of autumn 2026 → `2026-spring`.

Seed rule: **create missing rows, never update existing ones** (idempotent; data created in admin always survives). Every row goes through `save_validated`. Lookups:
- Terms: `Term.objects.filter(code=code).first()` or create.
- Disciplines (university reference data): `Discipline.objects.get_or_create(name=..., defaults={"short_name": ...})` for 4 new ones: «История дипломатии»/«Ист. дипл.», «Математика»/«Матем.», «Основы права»/«Право», plus existing «Английский язык». Current-term disciplines come from the schedule seed (already exist).
- Curriculum: by `(group, discipline, term)`. Results: by `(student, item, attempt)`. Marks: by `seed_key`. Attendance: by `(student, weekly_lesson, original_date)`.

Data (`cur` = current term from `term_bounds(today)`, `prev` = `term_bounds(cur.start - 1 day)`):

Curriculum `prev`:
| group | discipline | form | credits |
|---|---|---|---|
| ЦД-101 | История дипломатии | exam | 5 |
| ЦД-101 | Математика | graded_credit | 4 |
| ЦД-101 | Основы права | credit | 2 |
| ЦД-101 | Английский язык | credit | 3 |
| ЭД-201 | Математика | exam | 5 |
| ЭД-201 | Основы права | credit | 2 |
| ЭД-201 | Английский язык | graded_credit | 3 |
| ЭД-201 | История дипломатии | credit | 2 |

Curriculum `cur`:
| group | discipline | form | credits |
|---|---|---|---|
| ЦД-101 | Введение в цифровую дипломатию | exam | 5 |
| ЦД-101 | Теория международных отношений | exam | 4 |
| ЦД-101 | Английский язык | graded_credit | 3 |
| ЦД-101 | Анализ данных на Python | credit | 3 |
| ЦД-101 | Философия | credit | 2 |
| ЭД-201 | Микроэкономика | exam | 5 |
| ЭД-201 | Анализ данных на Python | graded_credit | 4 |
| ЭД-201 | Английский язык | credit | 3 |
| ЭД-201 | Философия | credit | 2 |

Final results `prev` (`date = prev.session_start + offset days`; all dates are in the past for any run date inside `cur`):
| student | discipline | attempt | result | offset |
|---|---|---|---|---|
| student1 | История дипломатии | 1 | 5 | 2 |
| student1 | Математика | 1 | 5 | 5 |
| student1 | Основы права | 1 | pass | 8 |
| student1 | Английский язык | 1 | pass | 11 |
| student3 | История дипломатии | 1 | 2 | 2 |
| student3 | История дипломатии | 2 | 4 | 20 (retake) |
| student3 | Математика | 1 | 3 | 5 |
| student3 | Основы права | 1 | fail | 8 (open debt) |
| student3 | Английский язык | 1 | pass | 11 |
| student2 | Математика | 1 | 4 | 3 |
| student2 | Основы права | 1 | pass | 6 |
| student2 | Английский язык | 1 | 5 | 9 |
| student2 | История дипломатии | 1 | pass | 12 |
For the retake with offset 20: if `prev.session_start + 20 > prev.end_date`, use `prev.end_date` (spring session is 30 days, autumn 22 days, so it always fits; keep the guard).
Expected: student1 avg 5.00, no debts; student3 avg 3.50, 1 debt («Основы права»); student2 avg 4.50, no debts.

Current marks `cur`: for each student and each `cur` curriculum item of the student's group (index `d` in the table order of that group), marks `k = 0..4` with `date = cur.start + timedelta(days=10 + 14 * k + d)`, created **only if `date < today`**; `value = PATTERN[student][(k + d) % 5]`; `kind = KINDS[k]`; `seed_key = f"m-{cur.code}-{username}-{d}-{k}"`.
`PATTERN = {"student1": [5, 5, 4, 5, 5], "student3": [3, 2, 4, 3, 3], "student2": [4, 5, 4, 4, 5]}`; `KINDS = ["Семинар", "Контрольная работа", "Доклад", "Семинар", "Тест"]`.

Attendance `cur`: for each demo student, if `today - 1 day >= cur.start`: `occ = [i for i in occurrences_between(cur.start, today - timedelta(days=1), [group_id]) if i.is_happening]` (lessons exist only inside their validity range, so earlier dates simply yield nothing); for each item: `n = item.original_date.toordinal() + item.slot.number`; status:
- student1: `excused` if `n % 11 == 0` else `present`;
- student3: `absent` if `n % 3 == 0`, else `excused` if `n % 7 == 0`, else `present` (low attendance);
- student2: `absent` if `n % 8 == 0` else `present`.
Create `Attendance(student, weekly_lesson=item.lesson, original_date=item.original_date, status)` via `save_validated` if no row exists for that key.

Return the number of demo rows that exist after the run: terms 2; curriculum items 17; results 13; marks = rows with a `seed_key` starting with `m-{cur.code}-`; attendance = demo students' rows in `[cur.start, cur.end]`.

### 6.7 `seed_demo` command
Inside the existing `transaction.atomic()` block, after `seed_schedule_demo(...)`: `a = seed_academics_demo(timezone.localdate())` (call `timezone.localdate()` once and pass the same `today` to both seeds). Generalize the `ValidationError` message to `"Demo data conflicts with existing data: "`. Print a third line: `f"Academics ready: {a.terms} terms, {a.curriculum_items} curriculum items, {a.results} final results, {a.marks} marks, {a.attendance} attendance records."`.

Check before changing: `accounts/tests/test_seed_demo.py` / `schedule/tests/test_demo.py` assertions on the old message text — if any test asserts `"Schedule demo data conflicts"`, update that assertion to the new prefix.

### 6.8 Schedule UI fixes (AC11)
- `schedule/templates/schedule/week.html`: wrap the back link: `{% if back_url %}<p><a href="{{ back_url }}">← К списку групп</a></p>{% endif %}`.
- `schedule/templates/schedule/includes/lesson_item.html`: replace the `<p class="lesson-change">…</p>` block with a single line so no whitespace precedes the period:
  `<p class="lesson-change">{% if item.kind == "cancelled" %}Отменено{% elif item.kind == "moved-out" %}Перенесено на {{ item.moved_to_date|date:"j E" }}, {{ item.moved_to_slot.number }} пара ({{ item.moved_to_slot.start|time:"H:i" }}){% elif item.kind == "moved-in" %}Перенесено с {{ item.moved_from_date|date:"j E" }}, {{ item.moved_from_slot.number }} пара{% elif item.kind == "room-changed" %}Замена аудитории{% elif item.kind == "teacher-replaced" %}Замена преподавателя{% endif %}. Причина: {{ item.change.reason }}</p>`

### 6.9 README
"Grades" section: `/grades/`, staff report from the student card, definitions of average (2 decimals, half-up, numeric results incl. 2), debts, attendance percent (excused excluded), «не отмечено». "Demo data": student1 strong, student3 has a retake and an open debt and low attendance, student2 other faculty; the seed only creates missing academic rows.

---

## 7. Test plan

Helpers in `academics/tests/helpers.py` (plain functions; reuse `accounts/tests/helpers.py` and `schedule/tests/helpers.py`):
`make_term(code="t-2026-autumn", start=date(2026, 9, 1), end=date(2027, 1, 31), session_start=date(2027, 1, 10), session_end=date(2027, 1, 31)) -> Term`; `make_item(group, discipline, term, form="exam", credits=None) -> CurriculumItem`; `make_result(student_profile, item, result, attempt=1, date=...) -> FinalResult`; `make_mark(student_profile, item, value, date) -> CurrentMark`; `make_attendance(student_profile, lesson, original_date, status) -> Attendance`. All writers use `save_validated`; tests that need invalid DB rows use `objects.create` explicitly. Clock: `mock.patch("django.utils.timezone.now", return_value=aware("2026-11-18 12:00"))` (Wednesday). Reference week Monday 2026-11-16. A finished session for "debt" tests: a term `2026-spring` (`2026-02-01..2026-08-31`, session `2026-06-01..06-30`). Never use `seed_demo` data outside `test_demo.py`.

### 7.1 Traceability
| AC | Tests |
|---|---|
| AC1 | `test_models.TermModelTests.*`, `CurriculumItemModelTests.*`, migrations checked by verification command |
| AC2 | `test_models.*` (every `*_rejected` test asserts `ValidationError` from `full_clean`), `test_views.AdminFormTests.*` |
| AC3 | `test_services.EffectiveResultsTests.*`, `test_models.FinalResultModelTests.test_retake_*`, `test_views.StudentGradesViewTests.test_retake_history_shown` |
| AC4 | `test_models.AttendanceModelTests.*` |
| AC5 | `test_services.*` |
| AC6 | `test_views.StudentGradesViewTests.*` |
| AC7 | `test_views.StaffGradesViewTests.*`, access matrix 7.2 |
| AC8 | `test_views.NavigationTests.*` |
| AC9 | `test_views.QueryCountTests.*` |
| AC10 | `test_demo.AcademicsDemoTests.*` |
| AC11 | `schedule/tests/test_views.py::ScheduleUiFixTests.*` |

### 7.2 Access matrix (`academics/tests/test_views.py`, class `GradesAccessTests`)
Fixture: faculties X, Y; groups GX (X), GY (Y); students A (GX), A2 (GX), B (GY); staff SX (X), SY (Y); superuser U; term T with items for GX and GY; each student has a distinct result and mark.

| URL | anonymous | student A | staff SX (A is own faculty) | staff SY (A is other faculty) | superuser |
|---|---|---|---|---|---|
| `/grades/` | 302 login — `test_anon_my_grades` | 200, own data only — `test_student_my_grades_own` | 403 — `test_staff_my_grades_forbidden` | 403 (same test, SY) | 403 — `test_superuser_my_grades_forbidden` |
| `/grades/<T.code>/` | 302 — `test_anon_my_grades_term` | 200 own — `test_student_term_own` | 403 — `test_staff_my_grades_term_forbidden` | 403 (same) | 403 — `test_superuser_my_grades_term_forbidden` |
| `/grades/unknown-term/` | 302 — `test_anon_unknown_term` | 404 — `test_student_unknown_term_404` | 403 — (covered by role check first) `test_staff_unknown_term_403` | — | — |
| `/staff/students/<A.pk>/grades/` | 302 — `test_anon_staff_report` | 403 — `test_student_staff_report_forbidden` | 200 — `test_staff_own_faculty_report` | 404 — `test_staff_other_faculty_404` | 403 — `test_superuser_staff_report_forbidden` |
| `/staff/students/<A.pk>/grades/<T.code>/` | 302 — `test_anon_staff_report_term` | 403 — `test_student_staff_report_term_forbidden` | 200 — `test_staff_own_faculty_report_term` | 404 — `test_staff_other_faculty_term_404` | 403 — `test_superuser_staff_report_term_forbidden` |
| `/staff/students/999999/grades/` | 302 | 403 | 404 — `test_staff_nonexistent_student_404` | 404 | 403 |
Student A on another student's data: there is no student URL with an ID; `test_student_sees_only_own_data` — A's page contains A's mark kind/result and never B's or A2's values (use distinctive `kind` strings like «Работа-A», «Работа-A2», «Работа-B»); `test_term_switch_keeps_isolation` — A opens `/grades/<T.code>/` and `/grades/<T_prev.code>/`: never B's or A2's data, even when B has data in that term.

### 7.3 Model validation (`academics/tests/test_models.py`)
`TermModelTests`: `test_valid_term`; `test_dates_out_of_order_rejected` (each of the 3 inequalities); `test_overlapping_term_rejected`; `test_adjacent_terms_allowed` (end 2026-08-31 / start 2026-09-01); `test_db_constraint_dates_order` (`objects.create` → `IntegrityError`).
`CurriculumItemModelTests`: `test_duplicate_rejected` (`full_clean` → `ValidationError`, `create` → `IntegrityError`); `test_credits_range` (0 and 31 rejected; `None` ok); `test_allowed_results`.
`CurrentMarkModelTests`: `test_value_range_rejected` (1, 6); `test_student_of_other_group_rejected`; `test_date_outside_term_rejected` (day before start, day after end); `test_future_date_rejected` (with mocked clock); `test_boundary_dates_allowed` (start, end ≤ today).
`FinalResultModelTests`: `test_numeric_on_credit_rejected`; `test_pass_on_exam_rejected`; `test_pass_on_graded_credit_rejected`; `test_numeric_on_graded_credit_allowed`; `test_student_of_other_group_rejected`; `test_attempt_2_without_1_rejected`; `test_retake_after_positive_rejected`; `test_retake_earlier_date_rejected`; `test_retake_after_fail_allowed`; `test_positive_earlier_attempt_with_later_attempt_rejected` (edit attempt 1 to `5` while attempt 2 exists); `test_duplicate_attempt_rejected`; `test_future_date_rejected`; `test_db_constraint_result_value` (`create(result="7")` → `IntegrityError`).
`AttendanceModelTests` (lesson L: GX, Mon slot 2, valid 2026-09-01..2026-12-31; clock 2026-11-18 12:00):
`test_valid_record` (Mon 2026-11-16); `test_other_group_rejected` (student B); `test_wrong_weekday_rejected` (Tue 2026-11-17); `test_outside_validity_rejected` (Mon 2027-01-04); `test_cancelled_rejected`; `test_future_rejected` (Mon 2026-11-23); `test_moved_to_future_rejected` (occurrence 2026-11-16 moved to 2026-11-20); `test_moved_to_past_allowed` (2026-11-09 moved to 2026-11-11); `test_today_allowed` (lesson on Wednesday 2026-11-18); `test_duplicate_rejected` (`full_clean` → `ValidationError`; `create` → `IntegrityError`); `test_db_status_constraint` (`create(status="late")` → `IntegrityError`); `test_no_late_status_choice` (`"late" not in AttendanceStatus.values`).

### 7.4 Services (`academics/tests/test_services.py`)
`EffectiveResultsTests`, `AverageGradeTests`, `IsDebtTests`, `StatusTextTests`, `SummarizeAttendanceTests`, `CurrentTermTests`, `TermBoundsTests` (in `test_demo.py`) — every case listed in 6.2/6.6, one test method each, named `test_<case>`. Plus:
`StudentTermReportTests`: `test_report_groups_by_discipline`; `test_marks_and_attempts_attached`; `test_attendance_only_for_own_group_and_term`; `test_moved_in_occurrence_counted_under_its_discipline`; `test_unmarked_past_and_ignored_future`; `test_term_before_start_has_no_attendance`; `test_items_of_former_group_with_results_included` (student moved to another group keeps old term results); `test_empty_term` → `disciplines == []`, `average is None`.
`StudentOverviewTests`: `test_no_results_status_ok_before_session_end`; `test_missing_result_after_session_is_debt`; `test_retake_clears_debt`; `test_only_pass_fail_average_none`; `test_overall_average_across_terms`; `test_debt_count_in_status_text`.

### 7.5 Views (`academics/tests/test_views.py`)
`StudentGradesViewTests`: `test_default_term_is_current` (clock inside T); `test_term_links_and_selected`; `test_empty_state_term_without_data` («За этот семестр данных нет.»); `test_no_terms_empty_state` («Семестров пока нет.»); `test_debt_marked` («Задолженность» and status «Есть задолженности: 1»); `test_ok_status` («Всё в порядке»); `test_retake_history_shown` («Попытка 1», «Попытка 2», «(действующий)» once); `test_attendance_summary_and_unmarked` («не отмечено»); `test_details_elements_present` (`<details>` count == number of disciplines); `test_renders_weeks_later` (clock moved +3 weeks without new data → 200, more «не отмечено»); `test_urls_have_no_ids` (`reverse("academics:my_grades") == "/grades/"`, `reverse("academics:my_grades_term", kwargs={"term_code": "t"}) == "/grades/t/"`).
`StaffGradesViewTests`: `test_link_from_student_detail`; `test_report_shows_student_name_and_back_link`; `test_report_matches_student_data`.
`NavigationTests`: `test_student_nav_has_grades`; `test_staff_nav_has_no_grades`.
`AdminFormTests` (superuser client): `test_admin_numeric_on_credit_shows_error` (POST to `admin:academics_finalresult_add` → 200, error text, no row); `test_admin_attendance_cancelled_shows_error`; `test_admin_overlapping_term_shows_error`.
`QueryCountTests`: `test_student_page_constant_queries` and `test_staff_page_constant_queries` — `CaptureQueriesContext` on GET with base data (2 items, 2 marks, 1 result, 2 attendance); then add 3 items, 10 marks, 4 results (incl. a retake), 10 attendance records, 2 extra weekly lessons; second count equals the first.

### 7.6 Demo (`academics/tests/test_demo.py`, class `AcademicsDemoTests`)
Run `seed_demo_data("Demo-Pass-2026-test!")`, `seed_schedule_demo(D)`, `seed_academics_demo(D)` with `D = date(2026, 11, 18)` and the clock mocked to `D 12:00`.
`test_counts` (2 terms, 17 items, 13 results); `test_students_differ` (student1: avg 5.00, 0 debts; student3: 1 debt «Основы права», avg 3.50, attendance percent for at least one discipline < student1's; student2: avg 4.50); `test_retake_present` (student3 «История дипломатии» attempts 1 and 2, effective `4`); `test_attendance_only_past_and_valid` (all records have effective date `< D`, all pass `full_clean`); `test_idempotent` (run twice → identical counts for all 5 models); `test_admin_rows_survive` (admin-created mark and attendance for student1 survive a re-run unchanged); `test_rerun_later_adds_only_new_rows` (re-run with `D + 14 days` → more attendance/marks, no duplicates, old rows unchanged); `test_page_renders_weeks_after_seed` (seed at D, GET `/grades/` as student1 with clock `D + 21 days` → 200, contains «не отмечено»); `test_command_output` (`call_command("seed_demo")` twice → output contains «Academics ready»).
`TermBoundsTests`: cases in 6.6.

### 7.7 Schedule UI fixes (`schedule/tests/test_views.py`, class `ScheduleUiFixTests`)
`test_student_week_has_no_back_link` (student week page: `"К списку групп" not in content`); `test_staff_week_back_link_url` (staff group week contains `href="/staff/schedule/"` and «К списку групп»); `test_change_label_no_space_before_period` — one change of each kind in the reference week; content contains `"Отменено. Причина:"`, `"Замена аудитории. Причина:"`, `"Замена преподавателя. Причина:"`, a `"). Причина:"` for moved-out and `"пара. Причина:"` for moved-in; and `" . Причина"` not in content. Both tests fail on the current templates (regression).

### 7.8 Settings branches
Not applicable: no settings or DEBUG-dependent behaviour changes (only `INSTALLED_APPS`).

---

## 8. Feasibility check (performed 2026-11-13 on `e7aa72a`)
1. Clean start — `git status --short` → only ` M plan.md` (Team lead's file). OK.
2. Referenced objects exist — `accounts.access.StudentRequiredMixin/StaffRequiredMixin` (`accounts/access.py`), `accounts.selectors.students_visible_to` (`accounts/selectors.py:15`), `schedule.services.occurrences_between(start, end, group_ids)` (`schedule/services.py:102`), `ScheduleItem.is_happening/original_date/lesson/slot/date` (`schedule/services.py:25-48`), `schedule.models.LessonChange/ChangeKind/WeeklyLesson` (`schedule/models.py`), `university.models.StudyGroup/Discipline`, URL name `accounts:staff_student_detail` (`accounts/urls.py:15`), templates `schedule/week.html:6` (back link without condition — confirmed) and `includes/lesson_item.html` (multi-line change label — confirmed), helpers `accounts/tests/helpers.py` (`make_faculty`, `make_group`, `make_student`, `make_staff`) and `schedule/tests/helpers.py` (`make_room`, `make_teacher`, `make_discipline`, `make_lesson`, `aware`), seed functions `accounts.demo.seed_demo_data`, `schedule.demo.seed_schedule_demo(today)`, command `accounts/management/commands/seed_demo.py`. OK.
3. No collisions — no `academics` directory or URL `/grades/` (`ls academics` → not found; grep for `academics`, `/grades` → none); new URL names are in a new namespace; no new env variables. OK.
4. Migrations — `makemigrations --check --dry-run` → "No changes detected". New app only adds tables; no existing table changes; no data migration needed. Seed text: existing schedule rows untouched. OK.
5. Tools — `.venv` Python 3.12.16, Django 5.2.19, ruff installed (`ruff check .` → "All checks passed!"). No new dependency. OK.
6. Framework — `CheckConstraint(condition=...)`, conditional `UniqueConstraint`, `F()` in constraints, `<details>` (HTML), `ROUND_HALF_UP` (stdlib `decimal`). Verified on 5.2.19 in previous tasks. OK.
7. Environment — no new env variables; `DEMO_PASSWORD` already in `.env.example:20`. No PostgreSQL needed. OK.
8. Verification runnable — on the current tree: `check` → no issues; `makemigrations --check` → no changes; `test` → `Ran 223 tests … OK`; deploy check → "(1 silenced)", exit 0; `ruff check` / `ruff format --check` → clean; YAML → ok; `seed_demo` → success. OK.
9. Conflicts — one requirement interpretation ("present / marked") was escalated to the Team lead as A1 and confirmed: excused absences are excluded from the percent (4.3). No other conflicts.
10. Assumptions / blockers:
   - A1 (CONFIRMED by the Team lead / user, 2026-11-13): attendance percent = present / (present + absent); excused absences are counted and shown but excluded from the percent; no present/absent records (e.g. all excused) → "—". No open blockers.

## 9. Implementation order
Shell: repo root, `.venv` active, `export DEBUG=true`, `export DEMO_PASSWORD='Local-Demo-Pass-2026!'`. Never open or edit `.env`. Do not delete `db.sqlite3` or existing migrations.
1. AC11 schedule fixes + `ScheduleUiFixTests` (verify they fail before the fix, pass after).
2. `academics` skeleton, models, wiring; `makemigrations academics`; `migrate`; `test_models.py`.
3. `services.py` pure functions + tests; then `student_term_report`, `student_overview` + tests.
4. `mutations.py`, admin + `AdminFormTests`.
5. Views, URLs, templates, nav, student detail link, CSS + `test_views.py` (access matrix, query counts).
6. `demo.py`, command change + `test_demo.py`; `seed_demo` twice.
7. README. `ruff format .`; section 10; manual `/grades/` at 360 px (student1, student3, staff1 → student card → report). `REPORT` to the Reviewer. Do not commit.

## 10. Verification
```bash
source .venv/bin/activate
export DEBUG=true
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
ruff check . && ruff format --check .
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
```
In the `REPORT`: output tails, test count (was 223), the two query counts.

## 11. Risks
- **IDOR**: staff report must start from `students_visible_to(request.user)`; student views use only `self.profile`. Term codes are public; every query filters by `student`.
- **Validation bypass**: `objects.create()` skips `clean()`. Only `academics/mutations.save_validated` writes academic rows in code.
- **Time**: always `timezone.localdate()`; tests mock `django.utils.timezone.now`.
- **Group transfer**: marks/results stay with the student; the report includes curriculum items of a former group when the student has results/marks there. Attendance of a former group's lessons is shown only while the lesson's groups include the student's current group (limitation, documented).
- **Orphaned attendance**: a record whose occurrence is later cancelled is ignored by the summary (not counted, not shown).
- **Seed**: never updates existing academic rows; changed demo definitions do not overwrite old demo rows (acceptable for demo).
