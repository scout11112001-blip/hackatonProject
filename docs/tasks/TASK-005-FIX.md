# TASK-005-FIX: change deletion, attendance vs changes, real-clock test dependency

Author: Planner. Status: ready for implementation.
Base commit: `3aa61bf`. Related specs: `docs/tasks/TASK-003.md`, `TASK-004.md`, `TASK-005.md`.

No new features. Every fix is minimal, at model/service level, and has a regression test that fails without the fix.

---

## 1. Goal and acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | Deleting a `LessonChange` goes through `schedule.mutations.delete_lesson_change`, which locks (same order as `schedule/locking.py`) and rejects the delete if the restored original occurrence would collide with another happening occurrence in the same room or with a shared group. |
| AC2 | Admin single delete uses the service; an invalid delete shows an admin error message, deletes nothing, never 500. The bulk "delete selected" action is removed for `LessonChange`. |
| AC3 | A `LessonChange` cannot be saved (created or edited) as CANCELLED for an occurrence with attendance records, nor as MOVED to a date after today for such an occurrence. Deleting a MOVED change is rejected if it would return an occurrence with attendance records to a future date. Clear non-field error mentioning «отметки посещения». |
| AC4 | `schedule` still does not import `academics`: the attendance rule is registered by `academics` through a guard registry in `schedule`. |
| AC5 | Every test class that runs clock-dependent code freezes the clock for the whole class (including `setUpTestData`). The full suite passes with the global clock frozen at Moscow 23:59:59, 00:00:00 and at dates far from today. |
| AC6 | New tests run the clock-dependent code at 23:59:59 and 00:00:00 Europe/Moscow and prove the result does not depend on the machine time zone. |
| AC7 | README has a "Known limitations" section with the two accepted limitations. |

## 2. Out of scope
New features, visual theme, deployment, teacher-conflict validation, group transfers, changes to `seed_demo` behaviour (it keeps its bulk delete of demo changes; see Risks).

---

## 3. Findings (root causes)

### 3.1 Item 1 — deletion is not validated
`schedule/admin.py` `LessonChangeAdmin` uses Django's default delete (single and bulk). `schedule/mutations.py` has no delete function. Removing a CANCELLED / ROOM_CHANGED / MOVED change "restores" the original occurrence at `(original_date, lesson.slot, lesson.room)` without any conflict check. Removing a TEACHER_REPLACED change cannot create a group/room conflict (teacher conflicts are out of scope). Removing a moved-in target never creates a conflict (it only frees a slot).

### 3.2 Item 2 — which change kinds hide attendance
`academics.services.student_term_report` builds attendance from `occurrences_between(term.start_date, min(term.end_date, today), [group])`, keeps only `is_happening` items and matches records by `(weekly_lesson_id, original_date)`. Therefore:
- **CANCELLED**: the occurrence is not happening → records are hidden. **Affected.**
- **MOVED** to `new_date <= today`: the MOVED_IN item keeps the identity `(lesson, original_date)` and is inside the range → records stay visible. **Not affected.**
- **MOVED** to `new_date > today`: the MOVED_IN item is outside the range (`end = today`) and MOVED_OUT is not happening → records are hidden. **Affected.** (It is also inconsistent: the occurrence has not happened yet, but attendance exists. `validate_occurrence_for_student` already rejects marking such an occurrence.)
- **ROOM_CHANGED / TEACHER_REPLACED**: still happening, same identity → not affected.
- **Deleting a MOVED change** whose `original_date > today` while records exist → the occurrence returns to a future date → records hidden. **Affected** (same rule, delete path).
- Deleting a CANCELLED change cannot hide records (a cancelled occurrence cannot have records).

### 3.3 Item 3 — clock in tests
- All application code reads the clock through `django.utils.timezone` (`timezone.now/localdate/localtime`): `accounts/forms.py:23`, `accounts/management/commands/seed_demo.py:24`, `schedule/views.py:27,42,65`, `academics/views.py:21,42`, `academics/models.py:177` (`CurrentMark` future-date check), `:254` (`FinalResult` future-date check), `:321` (`Attendance.clean` → `today`). Tests patch `django.utils.timezone.now`, which `localdate/localtime` call internally — so the patch point is already single. `aware()` builds Moscow-aware datetimes, so the machine time zone is irrelevant **when the clock is patched**.
- The problem is tests that do **not** patch the clock while running that code. A tracing run (global wrapper around `timezone.now` recording the calling test) found unpatched clock reads in: `academics/tests/test_models.py` (`FinalResultModelTests`, `CurrentMarkModelTests`, `AttendanceModelTests` via `setUpTestData`/helpers), `academics/tests/test_services.py` (`StudentTermReportTests`, `StudentOverviewTests`), `academics/tests/test_views.py` (`AccessFixture.setUpTestData`, admin tests), `academics/tests/test_demo.py`, `accounts/tests/test_seed_demo.py` (whole `seed_demo` on the real date), `schedule/tests/test_views.py` (`test_week_shows_only_own_group` uses `/schedule/week/` = real current week), `schedule/tests/test_demo.py`, `schedule/tests/test_demo_marker.py`. (Other hits are `auto_now_add` timestamps — harmless.)
- These tests validate **fixed** dates (e.g. 2026-11-16..18) against the **real Moscow date**. Their result depends on when they run: before the Moscow date reaches the fixture date they fail ("дата в будущем"); Moscow midnight falls in the local afternoon, which matches the observed flake. Reproduction: running the full suite with the global clock frozen at `2027-03-01 12:00 MSK` fails `schedule.tests.test_views.ScheduleViewsTests.test_week_shows_only_own_group` (lessons valid only until 2026-12-31). Frozen at 2026-11-13 23:59:59, 2026-11-14 00:00:00, 2026-11-15 23:59:59, 2026-11-16 00:00:00, 2026-11-28 12:00, 2026-12-31 23:59:59 and 2027-01-01 00:00:00 the suite passes (364 tests).
- Fix: freeze the clock per test class (one mixin), and add a CI step that runs the suite with a frozen far-future clock, so any new real-clock dependency fails deterministically.

---

## 4. Architecture

### 4.1 Files
Create:
```
schedule/guards.py
core/testing.py
scripts/run_tests_at.py
schedule/tests/test_change_delete.py
academics/tests/test_change_guard.py
academics/tests/test_clock_boundaries.py
```
Change:
```
schedule/models.py (LessonChange.clean), schedule/mutations.py, schedule/admin.py,
academics/apps.py, academics/services.py (new guard function),
.github/workflows/ci.yml, README.md,
test classes listed in 5.4 (add the mixin only; no other test edits except 5.4 item 3)
```
No migrations (no model field changes). No new dependencies. No new env variables.

---

## 5. Functions

### 5.1 `schedule/guards.py` — change guard registry (AC4)
```python
ChangeGuard = Callable[["LessonChange", bool], list[str]]   # (change, deleting) -> messages

_guards: list[ChangeGuard] = []

def register_change_guard(guard: ChangeGuard) -> None
def run_change_guards(change: LessonChange, *, deleting: bool) -> list[str]
```
- `register_change_guard`: append if not already present (idempotent; `ready()` may run more than once in tests).
- `run_change_guards`: concatenate `guard(change, deleting)` results of all registered guards, in registration order.
- Purpose: lets apps that depend on `schedule` veto schedule changes without `schedule` importing them. Do not write the word `academics` anywhere in non-test `schedule` code (docstrings included) — verification greps for it.
- Tests (in `academics/tests/test_change_guard.py`): `test_academics_guard_registered` (`attendance_change_guard in guards._guards`); `test_register_is_idempotent` (register twice → present once; remove the test guard in `finally`).

### 5.2 `LessonChange.clean()` change (`schedule/models.py`)
After the existing `if errors: raise ValidationError(errors)` and **before** `change_conflicts`:
```python
from .guards import run_change_guards

guard_errors = run_change_guards(self, deleting=False)
if guard_errors:
    raise ValidationError(guard_errors)
```
(Non-field errors. Keep the existing conflict check after it.)

### 5.3 `academics/services.py` + `academics/apps.py` — attendance guard (AC3)
```python
def attendance_change_guard(change: LessonChange, deleting: bool) -> list[str]
```
- Algorithm:
  1. If `change.weekly_lesson_id is None` or `change.original_date is None` → `[]`.
  2. `count = Attendance.objects.filter(weekly_lesson_id=change.weekly_lesson_id, original_date=change.original_date).count()`; `count == 0` → `[]`.
  3. `today = timezone.localdate()`; `d = f"{change.original_date:%d.%m.%Y}"`.
  4. Not deleting:
     - `kind == CANCELLED` → `[f"Нельзя отменить занятие {d}: есть отметки посещения ({count}). Сначала удалите их."]`;
     - `kind == MOVED` and `change.new_date is not None and change.new_date > today` → `[f"Нельзя перенести занятие {d} на будущую дату: есть отметки посещения ({count}). Сначала удалите их."]`.
  5. Deleting: `kind == MOVED` and `change.original_date > today` → `[f"Нельзя удалить перенос занятия {d}: занятие вернётся на будущую дату, а отметки посещения ({count}) уже есть. Сначала удалите их."]`.
  6. Otherwise `[]`.
- `AcademicsConfig.ready()`: `from schedule.guards import register_change_guard`; `from .services import attendance_change_guard`; `register_change_guard(attendance_change_guard)`.

### 5.4 `schedule/mutations.py` — delete service (AC1)
```python
def delete_lesson_change(change: LessonChange) -> None
```
- Algorithm:
  1. `with transaction.atomic():`
  2. `errors = restored_occurrence_conflicts(change) + run_change_guards(change, deleting=True)`.
  3. If `errors` → `raise ValidationError(errors)`.
  4. `change.delete()`.

Put the helper in `schedule/validation.py` next to `change_conflicts`:
```python
def restored_occurrence_conflicts(change: LessonChange) -> list[str]
```
- Purpose: conflicts that appear when `change` is removed and its original occurrence becomes regular again.
- Algorithm:
  1. If `change.kind == TEACHER_REPLACED` → `[]`.
  2. `lesson = change.weekly_lesson`; `group_ids = set(lesson.groups.values_list("id", flat=True))`.
  3. `locking.lock_rooms_and_groups([lesson.room_id], group_ids)` (same helper and order as other writes).
  4. `items = occurrences_between(change.original_date, change.original_date, None)`.
  5. For each `item` with `item.is_happening` and `item.slot.number == lesson.slot`, **skip** the same occurrence (`item.lesson.id == lesson.id and item.original_date == change.original_date`):
     - `item.room.id == lesson.room_id` → `f"Нельзя удалить изменение: {change.original_date:%d.%m.%Y}, {lesson.slot} пара, аудитория {item.room.number} уже занята ({item.lesson.discipline.name})."`;
     - each group of `item.lesson.groups.all()` with id in `group_ids` → `f"Нельзя удалить изменение: {change.original_date:%d.%m.%Y}, {lesson.slot} пара, группа {g.name} уже занята ({item.lesson.discipline.name})."`.
  6. Return the list.
- Note: the moved-in/room-changed target of the change disappears with it; removing an occurrence never creates a conflict, so only the restored original is checked.

### 5.5 Admin (`schedule/admin.py`, AC2)
In `LessonChangeAdmin`:
```python
def get_actions(self, request):
    actions = super().get_actions(request)
    actions.pop("delete_selected", None)
    return actions


def delete_model(self, request, obj):
    delete_lesson_change(obj)


def delete_view(self, request, object_id, extra_context=None):
    try:
        with transaction.atomic():
            return super().delete_view(request, object_id, extra_context)
    except ValidationError as exc:
        self.message_user(request, " ".join(exc.messages), level=messages.ERROR)
        return HttpResponseRedirect(reverse("admin:schedule_lessonchange_change", args=[object_id]))
```
`super().delete_view` already runs in a transaction; the outer `atomic` makes the deletion log entry roll back together with the failed delete. Imports: `django.contrib.messages`, `django.core.exceptions.ValidationError`, `django.db.transaction`, `django.http.HttpResponseRedirect`, `django.urls.reverse`, `.mutations.delete_lesson_change`.
Cascade deletes (deleting a `WeeklyLesson` deletes its changes) are unchanged: removing a whole lesson removes occurrences and cannot create conflicts; lessons with attendance are protected (`on_delete=PROTECT`).

### 5.6 `core/testing.py` — frozen clock for test classes (AC5)
```python
MOSCOW = ZoneInfo("Europe/Moscow")

def moscow(dt_str: str) -> datetime        # "2026-11-18 12:00" -> aware Moscow datetime

class FrozenClockMixin:
    frozen_now: ClassVar[str] = "2026-11-18 12:00"

    @classmethod
    def setUpClass(cls) -> None
    @classmethod
    def tearDownClass(cls) -> None
```
- `setUpClass`: `cls._clock_patcher = mock.patch("django.utils.timezone.now", return_value=moscow(cls.frozen_now))`; `cls._clock_patcher.start()`; then `try: super().setUpClass()` / `except Exception: cls._clock_patcher.stop(); raise` (so `setUpTestData` runs with the frozen clock).
- `tearDownClass`: `try: super().tearDownClass()` / `finally: cls._clock_patcher.stop()`.
- Must be listed **before** `TestCase`/`SimpleTestCase` in the bases. Inner `mock.patch("django.utils.timezone.now", ...)` in single tests keeps working (it overrides and then restores the class-level mock).
- `core/testing.py` is a plain module (not a test module); it imports only `unittest.mock`, `datetime`, `zoneinfo`, `typing`.

Apply the mixin (only add it to the bases; keep `frozen_now` default unless a class's own mocks need another value) to these classes:
1. `academics/tests/test_models.py`: `ModelFixture` (base of all model test classes).
2. `academics/tests/test_services.py`: every `TestCase` class (not the `SimpleTestCase` ones).
3. `academics/tests/test_views.py`: `AccessFixture`. `academics/tests/test_demo.py`: `AcademicsDemoTests`.
4. `accounts/tests/test_seed_demo.py`: `SeedDemoTests`.
5. `schedule/tests/test_views.py`: `ScheduleViewsTests`, `ChangeRenderingTests`, `ScheduleUiFixTests`. `test_week_shows_only_own_group` then renders the week of 2026-11-18 (inside the fixture lessons' validity) — no other edit needed.
6. `schedule/tests/test_demo.py`: `ScheduleDemoTests`; `schedule/tests/test_demo_marker.py`: `DemoMarkerTests`; `schedule/tests/test_revalidation.py`, `test_locking.py`, `test_validation.py`, `test_services.py`: every `TestCase` class.
7. New test classes in this task.
`academics/tests/test_models.py` may keep its existing `_clock()` helper; it becomes redundant but harmless.

### 5.7 `scripts/run_tests_at.py` — whole-suite frozen-clock run
Usage: `python scripts/run_tests_at.py 2027-03-01T12:00:00 [test labels...]`. Algorithm:
1. Insert the repo root (parent of `scripts/`) into `sys.path`; `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")`.
2. Parse `sys.argv[1]` with `datetime.fromisoformat`, attach `ZoneInfo("Europe/Moscow")`.
3. `mock.patch("django.utils.timezone.now", return_value=when).start()` **before** `django.setup()`.
4. `django.setup()`; run `get_runner(settings)(verbosity=1).run_tests(sys.argv[2:])`; `sys.exit(1 if failures else 0)`.
Docstring: "Runs the test suite with the clock frozen at a Moscow time. Tests must not depend on the real current date."

CI (`.github/workflows/ci.yml`), after the `Tests` step:
```yaml
      - name: Tests with a frozen far-future clock
        run: python scripts/run_tests_at.py 2027-03-01T12:00:00
```

### 5.8 README — "Known limitations" (AC7)
Create section `## Known limitations` before "Environment variables":
- After a student moves to another group, attendance for the former group's lessons is not shown (group transfers are out of scope for the prototype).
- `seed_demo` never updates existing academic rows, so data edited in the admin is never overwritten. Re-running it only adds missing rows (new past occurrences); run it daily on the server to keep the demo fresh.
Also add to "Test & lint": `python scripts/run_tests_at.py 2027-03-01T12:00:00` with one line: "tests must not depend on the real date".

---

## 6. Test plan

Clock for all new tests: `FrozenClockMixin` with `frozen_now = "2026-11-18 12:00"` (Wednesday) unless stated. Reference: Monday 2026-11-16, next Monday 2026-11-23. Lessons valid `2026-09-01..2026-12-31`. Build data with `accounts/tests/helpers.py`, `schedule/tests/helpers.py`, `academics/tests/helpers.py`; changes via `save_lesson_change`. Never use `seed_demo` data (except the seed boundary test, which tests the seed).

### 6.1 Traceability
| AC | Tests |
|---|---|
| AC1 | `schedule/tests/test_change_delete.py::DeleteLessonChangeTests.*` |
| AC2 | `schedule/tests/test_change_delete.py::DeleteLessonChangeAdminTests.*` |
| AC3 | `academics/tests/test_change_guard.py::AttendanceChangeGuardTests.*` |
| AC4 | `academics/tests/test_change_guard.py::GuardRegistryTests.*`, plus `grep -rn "academics" schedule/*.py` → empty (verification) |
| AC5 | full suite + `scripts/run_tests_at.py` runs (section 8) |
| AC6 | `academics/tests/test_clock_boundaries.py::MoscowMidnightTests.*` |
| AC7 | manual check of README (Reviewer) |

### 6.2 Access matrix
Only the admin delete view changes. Admin access is unchanged (superuser only; covered by `accounts/tests/test_admin.py`). Cells: superuser → tests in 6.3 `DeleteLessonChangeAdminTests`; student/staff/anonymous → existing admin tests (redirect to admin login) — `test_non_superuser_cannot_delete_change` added: student and staff POST to the delete URL → 302 to admin login, change still exists. No new non-admin views.

### 6.3 `schedule/tests/test_change_delete.py`
`DeleteLessonChangeTests(FrozenClockMixin, TestCase)` — fixture: groups G1, G2, G3; rooms R1..R6; L_A (G1, R1, Mon s2).
1. `test_reviewer_scenario_room_conflict_rejected` — CANCEL L_A on 2026-11-23; L_B (G2, R2, Tue s1) MOVED from 2026-11-17 to 2026-11-23 s2 with `new_room=R1`; `delete_lesson_change(cancel)` → `ValidationError` whose message contains `f"аудитория {R1.number}"` and «23.11.2026»; the cancel still exists.
2. `test_group_conflict_rejected` — CANCEL L_A on 23.11; L_C (G1, R3, Tue s1) MOVED to 23.11 s2 (own room R3) → delete cancel → error mentions group G1.
3. `test_room_changed_restore_conflict_rejected` — L_A ROOM_CHANGED on 23.11 to R5; L_D (G3, R6, Mon s2) ROOM_CHANGED on 23.11 to R1 → delete L_A's room change → error (R1).
4. `test_moved_restore_conflict_rejected` — L_A MOVED from 23.11 to Wed 25.11 s4; L_E (G2, R4, Tue s1) MOVED from 17.11 to 23.11 s2 with `new_room=R1` → delete L_A's move → error.
5. `test_delete_without_conflict_allowed` — CANCEL L_A on 23.11, nothing else → deleted.
6. `test_delete_teacher_replacement_always_allowed` — even when another lesson occupies R1 that day via a move (no check for this kind) → deleted.
7. `test_delete_moved_in_target_never_conflicts` — delete L_B's MOVED change from test 1 (the moved-in one) → allowed; then L_A cancel still exists.
8. `test_delete_locks_room_and_groups` — `mock.patch("schedule.locking.lock_rooms_and_groups", wraps=...)` → called with `[L_A.room_id]` and `{G1.pk}`.
9. `test_delete_is_atomic_on_error` — after a rejected delete, `LessonChange.objects.count()` unchanged.

`DeleteLessonChangeAdminTests(FrozenClockMixin, TestCase)` (superuser client):
10. `test_admin_invalid_delete_shows_error` — scenario 1; POST `{"post": "yes"}` to `reverse("admin:schedule_lessonchange_delete", args=[cancel.pk])` → 302 to the change page; follow → message contains «Нельзя удалить изменение»; the change exists; `LogEntry.objects.filter(action_flag=DELETION).count() == 0`.
11. `test_admin_valid_delete` — scenario 5 → 302, change deleted.
12. `test_admin_bulk_delete_action_removed` — GET changelist → `"delete_selected"` not among `response.context["action_form"].fields["action"].choices` values; POST `{"action": "delete_selected", "_selected_action": [cancel.pk]}` to the changelist → the change still exists.
13. `test_non_superuser_cannot_delete_change` — see 6.2.

### 6.4 `academics/tests/test_change_guard.py`
`AttendanceChangeGuardTests(FrozenClockMixin, TestCase)` — student A in G1; L (G1, R1, Mon s2); attendance for occurrence 2026-11-16 (present).
1. `test_cancel_with_attendance_rejected` — CANCEL on 16.11 → `ValidationError` containing «отметки посещения»; nothing saved.
2. `test_cancel_without_attendance_allowed` — CANCEL on 09.11 (no records) → saved.
3. `test_edit_existing_change_to_cancel_rejected` — existing ROOM_CHANGED on 16.11 (allowed with records); edit kind to CANCELLED (clear `new_room`) → rejected.
4. `test_move_to_future_with_attendance_rejected` — MOVED 16.11 → 2026-11-20 s3 → rejected.
5. `test_move_to_past_with_attendance_allowed_and_visible` — MOVED 16.11 → 2026-11-17 s3 → saved; `student_term_report(A, term, date(2026, 11, 18))` attendance for L's discipline has `present == 1`.
6. `test_room_and_teacher_change_with_attendance_allowed`.
7. `test_edit_reason_of_allowed_move_with_attendance` — change from test 5, edit `reason` → saved.
8. `test_delete_move_returning_to_future_rejected` — L2 (G1, R2, Mon s3); MOVED 23.11 → 17.11 s4 (past); attendance for (L2, 23.11) present (effective date 17.11 is past → allowed); `delete_lesson_change(move)` → rejected with «отметки посещения».
9. `test_delete_move_returning_to_past_allowed` — MOVED 16.11 → 17.11 with record → delete → allowed (occurrence back to 16.11, past).
10. `test_admin_cancel_with_attendance_shows_form_error` — superuser POST to `admin:schedule_lessonchange_add` (CANCELLED, L, 16.11, reason) → 200, error text, no new row.
11. `test_clock_boundary_move` — MOVED 16.11 → 18.11 with records: with clock `2026-11-17 23:59:59` → rejected (future); with clock `2026-11-18 00:00:00` → allowed.
`GuardRegistryTests(SimpleTestCase)`: tests from 5.1.

### 6.5 `academics/tests/test_clock_boundaries.py`
`MoscowMidnightTests(FrozenClockMixin, TestCase)`; each test patches `django.utils.timezone.now` with `moscow("2026-11-17 23:59:59")` and `moscow("2026-11-18 00:00:00")` in turn:
1. `test_mark_future_check` — mark dated 2026-11-18: 23:59:59 → `ValidationError` «в будущем»; 00:00:00 → valid.
2. `test_final_result_future_check` — same for `FinalResult`.
3. `test_attendance_today_check` — lesson on Wednesday; occurrence 2026-11-18: 23:59:59 → rejected (future); 00:00:00 → allowed.
4. `test_today_view_date` — student GET `/schedule/`: `response.context["day"].date` is 2026-11-17, then 2026-11-18.
5. `test_unmarked_counter_switches_at_midnight` — fixture: term `2026-09-01..2027-01-31` (session `2027-01-10..01-31`), curriculum item for the lesson's discipline and the student's group, lesson on Tuesdays; occurrence on 2026-11-17 without a record: GET `/grades/` at `2026-11-17 23:59:59` → that occurrence not counted as «не отмечено» (`report` unmarked == N); at `2026-11-18 00:00:00` → `N + 1`.
6. `test_machine_timezone_does_not_matter` — inside `mock.patch.dict(os.environ, {"TZ": "America/Los_Angeles"})` + `time.tzset()` (restore with `time.tzset()` after leaving the context, in `finally`): repeat test 4 at `2026-11-18 00:00:00` → day is 2026-11-18. Skip with `unittest.skipUnless(hasattr(time, "tzset"), ...)`.
7. `test_seed_at_midnight` — `call_command("seed_demo")` with `DEMO_PASSWORD` set, at `2026-11-17 23:59:59` and again at `2026-11-18 00:00:00` → both succeed; every `Attendance` row satisfies `validate_occurrence_for_student(..., today=date(2026, 11, 18)) == []`; no `CurrentMark` / `FinalResult` dated after 2026-11-18.

### 6.6 Negative / edge cases covered
Rejected delete leaves data and log unchanged (6.3 #9, #10); same-occurrence skip (6.3 #7); midnight boundary (6.4 #11, 6.5); edit vs create (6.4 #3, #7); delete path of the guard (6.4 #8, #9).

### 6.7 Settings branches
Not applicable (no settings changes).

### 6.8 Query count
Not applicable (no list or aggregate page changes).

### 6.9 Regression tests (must fail before the fix)
6.3 #1–#4, #10, #12; 6.4 #1, #3, #4, #8, #10; `ScheduleViewsTests.test_week_shows_only_own_group` under `scripts/run_tests_at.py 2027-03-01T12:00:00` (fails before the mixin is applied). Report in the `REPORT` that you saw them fail before the fix.

---

## 7. Feasibility check (performed 2026-11-13 on `3aa61bf`)
1. Clean start — `git status --short` → only ` M plan.md` (Team lead). OK.
2. Referenced objects — `LessonChange.clean()` (`schedule/models.py`, conflicts at the end via `change_conflicts`), `schedule/mutations.py` (`save_weekly_lesson`, `save_lesson_change`; no delete function), `schedule/locking.lock_rooms_and_groups` (`schedule/locking.py`), `schedule/validation.change_conflicts`, `schedule.services.occurrences_between` (`schedule/services.py:102`), `LessonChangeAdmin` (`schedule/admin.py`, no delete overrides), `academics/apps.py` (`AcademicsConfig`, no `ready()`), `Attendance.weekly_lesson` (`related_name="attendance_records"`, `academics/models.py:286`), `academics.services.validate_occurrence_for_student` (`academics/services.py:78`), `student_term_report`, test helpers in all three apps, test classes named in 5.6 (checked with `grep -n "^class "`). OK.
3. No collisions — `schedule/guards.py`, `core/testing.py`, `scripts/` do not exist; README has no "Known limitations" section. OK.
4. Data/migrations — no model field changes, no migration; `makemigrations --check` → "No changes detected". OK.
5. Tools — `.venv` Python 3.12.16, Django 5.2.19, ruff clean. `time.tzset` exists on macOS/Linux (CI ubuntu). OK.
6. Framework — `ModelAdmin.delete_view` runs `_delete_view` inside `transaction.atomic` and calls `delete_model` (Django 5.2); `get_actions` returns a dict containing `"delete_selected"`; `AppConfig.ready()`. OK.
7. Environment — no new env variables. OK.
8. Verification runnable — current tree: `test` → `Ran 364 tests … OK`; frozen-clock runs: passes at 7 instants listed in 3.3, fails at `2027-03-01 12:00` with 1 failure (the bug to fix). check, deploy check, ruff, YAML → OK.
9. Conflicts — Item 2's MOVED question resolved by analysis (3.2): only MOVED to a future date (and deleting a MOVED change back to a future date) hides records; ROOM/TEACHER changes do not. No conflicts with the request.
10. Assumptions / blockers — none.

## 8. Implementation order
Shell: repo root, `.venv` active, `export DEBUG=true`, `export DEMO_PASSWORD='Local-Demo-Pass-2026!'`. Never open or edit `.env`. Do not delete `db.sqlite3` or migrations.
1. `core/testing.py`; `scripts/run_tests_at.py`; confirm `python scripts/run_tests_at.py 2027-03-01T12:00:00` fails (1 failure) before the next step.
2. Apply the mixin (5.6). Re-run the script at the 2027 date and at `2026-11-17T23:59:59` / `2026-11-18T00:00:00` → all pass. Add the CI step.
3. Write the new tests for items 1 and 2 first; confirm the regression tests fail.
4. `schedule/guards.py`, `LessonChange.clean()` change, `attendance_change_guard` + `ready()`.
5. `restored_occurrence_conflicts`, `delete_lesson_change`, admin changes.
6. `test_clock_boundaries.py`. README.
7. `ruff format .`; section 9; `REPORT` to the Reviewer. Do not commit.

## 9. Verification
```bash
source .venv/bin/activate
export DEBUG=true
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python scripts/run_tests_at.py 2026-11-17T23:59:59
python scripts/run_tests_at.py 2026-11-18T00:00:00
python scripts/run_tests_at.py 2027-03-01T12:00:00
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
ruff check . && ruff format --check .
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
grep -rn "academics" schedule --include='*.py' | grep -v "/tests/" ; echo "expect: no output"
DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
```
In the `REPORT`: output tails, test count (was 364), confirmation that the regression tests failed before the fix.

## 10. Risks
- **Seed bulk delete**: `schedule/demo.py` still deletes demo changes with `queryset.delete()` (bypasses `delete_lesson_change`). Conflicts it could create are caught right after by `save_weekly_lesson` (occurrence simulation from TASK-004) → `CommandError`. The attendance guard runs when the seed re-creates changes; by construction the seed creates attendance only for past happening occurrences, so its own changes do not trip the guard. If an admin-created record does, the seed stops with a clear `CommandError`.
- **Guard registry**: guards are global; tests that register a temporary guard must remove it in `finally`.
- **Frozen clock mixin**: a test class without the mixin that runs clock-dependent code becomes date-dependent again; the CI far-future run catches it.
- **`time.tzset()`** changes process state; restore it in `finally`.

---

## Amendment 1 (Team lead, approved by the user after a Reviewer ESCALATION)

Keep the current implementation. Add only what is below.

### A1. Edit path of the "restored occurrence" defect

#### A1.1 Analysis — which edits release the old occurrence
`LessonChange.clean()` validates only the new state. An edit can also **release** the old state. Identity = `(weekly_lesson_id, original_date)`. For an existing row (`pk` set) compare the stored row `old` with the edited instance `new`:

| Edit | Effect on the old occurrence | Check needed for the OLD state |
|---|---|---|
| identity changed (`weekly_lesson` or `original_date`), old kind CANCELLED / MOVED / ROOM_CHANGED | old occurrence becomes regular again | restored-occurrence conflicts **and** delete guards |
| identity changed, old kind TEACHER_REPLACED | old occurrence keeps room/slot | delete guards only (no room/group effect) |
| same identity, old kind CANCELLED / MOVED / ROOM_CHANGED → new kind TEACHER_REPLACED | occurrence returns to `lesson.room` at the original slot | restored-occurrence conflicts |
| same identity, CANCELLED/ROOM_CHANGED → MOVED, CANCELLED/MOVED → ROOM_CHANGED, any → CANCELLED, MOVED target change | the original slot stays free or the new placement is fully checked by the existing new-state checks (`change_conflicts` checks room **and** groups of the new placement) | none (a check here would give false positives: the freed room may already be used legitimately) |

The Team lead's list included "the move target changes". Analysis: changing `new_date`/`new_slot`/`new_room` of a MOVED change with the same identity frees the old target (freeing never conflicts), and the new target is checked by `change_conflicts`. So no old-state check is needed for this case.

Attendance with the same identity: the records stay with the occurrence, so the **new-state** guard must judge the new placement for **every** kind, not only MOVED (example: MOVED to a past date with records → edited to ROOM_CHANGED; the occurrence goes back to its future original date and the records disappear from the report). See A1.3.

Self-conflict found during the analysis: when the identity of a MOVED/ROOM_CHANGED change is edited, `change_conflicts` reads the DB, where the old row still produces an item (for example the old MOVED_IN item) with another `original_date`. That item is not skipped and reports a conflict with itself. Fix in A1.4.

#### A1.2 New function `schedule/validation.py`
```python
def released_occurrence_errors(old: LessonChange, new: LessonChange) -> list[str]
```
1. `identity_changed = old.weekly_lesson_id != new.weekly_lesson_id or old.original_date != new.original_date`.
2. `hides = old.kind in (CANCELLED, MOVED, ROOM_CHANGED)`.
3. `restores = hides and (identity_changed or new.kind == TEACHER_REPLACED)`.
4. If not `restores` and not `identity_changed` → `[]`.
5. Locking (one call, before any check, keeps the global order): rooms = `{old.weekly_lesson.room_id, new.weekly_lesson.room_id, new.new_room_id}`; groups = groups of `old.weekly_lesson` ∪ groups of `new.weekly_lesson`; `locking.lock_rooms_and_groups(rooms, groups)`. The later lock calls in `restored_occurrence_conflicts` / `change_conflicts` only re-lock rows that are already held.
6. `errors = []`; if `restores`: `errors += restored_occurrence_conflicts(old, prefix="Нельзя так изменить запись")`; if `identity_changed`: `errors += run_change_guards(old, deleting=True)`.
7. Return `errors`.

`restored_occurrence_conflicts(change, prefix: str = "Нельзя удалить изменение")`: add the keyword parameter and use it instead of the fixed text "Нельзя удалить изменение" in both messages. Existing callers and tests stay unchanged.

#### A1.3 `attendance_change_guard` — new-state branch (`deleting=False`) for every kind
Replace the non-deleting branch with:
1. `kind == CANCELLED` → existing message (unchanged).
2. `effective = change.new_date if change.kind == MOVED else change.original_date`; if `effective is not None and effective > today`:
   - `kind == MOVED` → existing MOVED message (unchanged);
   - otherwise → `f"Нельзя сохранить изменение занятия {d}: занятие окажется в будущем, а отметки посещения ({count}) уже есть. Сначала удалите их."`.
The deleting branch is unchanged.

#### A1.4 `change_conflicts` — skip the row being edited
In the loop, after the existing "same occurrence" skip, add: `if change.pk is not None and item.change is not None and item.change.pk == change.pk: continue` (the DB items produced by the stored version of this same change are replaced by the new state). Do the same in `restored_occurrence_conflicts` is **not** needed (it receives the stored row itself).

#### A1.5 `LessonChange.clean()` order
After the field-rule errors (unchanged) and before the new-state guards:
```python
if self.pk is not None:
    old = LessonChange.objects.select_related("weekly_lesson").filter(pk=self.pk).first()
    if old is not None:
        from .validation import released_occurrence_errors

        released = released_occurrence_errors(old, self)
        if released:
            raise ValidationError(released)
```
Then the existing `run_change_guards(self, deleting=False)` and `change_conflicts(self)`. All errors are non-field → admin shows a form error, no 500. `clean()` runs inside `save_lesson_change`'s and the admin's transaction, so locks are held until commit.

#### A1.6 Tests — `schedule/tests/test_change_edit.py` (new)
`EditLessonChangeTests(FrozenClockMixin, TestCase)`; clock `2026-11-18 12:00`; fixture as in 6.3: L_A (G1, R1, Mon s2), cancel C on 23.11; L_B (G2, R2, Tue s1) MOVED 17.11 → 23.11 s2 with `new_room=R1`. Edits go through `save_lesson_change` on the fetched row (`LessonChange.objects.get(pk=...)`, change fields, save).
1. `test_cancel_to_teacher_replaced_rejected` — C: kind → TEACHER_REPLACED, `new_teacher=T2` → `ValidationError` with `f"аудитория {R1.number}"` and «23.11.2026»; DB row still CANCELLED.
2. `test_cancel_original_date_change_rejected` — C: `original_date` → 30.11 → rejected; DB row still 23.11.
3. `test_room_changed_to_teacher_replaced_rejected` — L_A ROOM_CHANGED on 23.11 to R5 (instead of C); L_D (G3, R6, Mon s2) ROOM_CHANGED on 23.11 to R1; edit L_A's change to TEACHER_REPLACED → rejected.
4. `test_group_conflict_on_restore_rejected` — L_C (G1, R3, Tue s1) MOVED to 23.11 s2 (own room); edit C to 30.11 → rejected with group G1.
5. `test_allowed_edits` (subTests, each from a fresh C): reason change → saved; `original_date` 23.11 → 30.11 when nothing occupies 23.11 s2 (delete L_B's move first) → saved; CANCELLED → MOVED to Wed 25.11 s4 (B still in R1 on 23.11) → saved (no false positive).
6. `test_move_target_change_allowed` — L_A MOVED 23.11 → 25.11 s4; edit `new_slot` to 5 → saved.
7. `test_move_original_date_change_no_self_conflict` — L_A MOVED 23.11 → 25.11 s4; edit `original_date` → 30.11 (same target) → saved (A1.4).
8. `test_admin_edit_shows_form_error` — superuser POST to `admin:schedule_lessonchange_change` for scenario 1 → 200, error text, no 500, DB unchanged.
9. `test_edit_locks_once_in_order` — patch `schedule.locking.lock_rooms_and_groups` with `wraps`; scenario 2 → the first call receives rooms `{R1}` and groups `{G1}` (union of old/new).

`academics/tests/test_change_guard.py` — add to `AttendanceChangeGuardTests`:
10. `test_edit_move_original_date_returns_records_to_future_rejected` — L2 (G1, R2, Mon s3) MOVED 23.11 → 17.11 s4; attendance for (L2, 23.11); edit the move's `original_date` to 30.11 (new target unchanged) → rejected «отметки посещения» (old occurrence 23.11 returns to the future with records).
11. `test_edit_move_to_room_change_returns_records_to_future_rejected` — same setup; edit kind → ROOM_CHANGED (`new_date=None`, `new_slot=None`, `new_room=R3`) → rejected (A1.3).
12. `test_edit_without_releasing_records_allowed` — MOVED 16.11 → 17.11 with records on 16.11; edit `reason` → saved.

### A2. Exclude the process archive from ruff
`pyproject.toml`: `extend-exclude = ["*/migrations/*", ".venv", "staticfiles", "docs/process"]`. Never run `ruff format` on `docs/process`.
Feasibility evidence: today `ruff format --check .` → "1 file would be reformatted" (`docs/process/dialogs/03-coder-deepseek.md:148`); `ruff format --check --extend-exclude docs/process .` → "104 files already formatted".

### A3. Protocol reminder
Do not delete or recreate `db.sqlite3` (or any database) without Team lead approval. For seed checks use a temporary DB: `DATABASE_URL=sqlite:///$TMPDIR/seedcheck.sqlite3 python manage.py migrate && DATABASE_URL=sqlite:///$TMPDIR/seedcheck.sqlite3 python manage.py seed_demo` (twice).

### A4. Feasibility check (amendment, 2026-11-13, working tree of TASK-005-FIX in progress)
1. Clean start — uncommitted files are this task's own changes (listed by `git status`) plus `plan.md`. OK for an amendment of the same task.
2. Referenced objects — `restored_occurrence_conflicts(change)` and `change_conflicts(change)` (`schedule/validation.py:171, 209`), `LessonChange.clean()` guard/conflict calls (`schedule/models.py:245-253`), `attendance_change_guard(change, deleting)` (`academics/services.py:292`), `ScheduleItem.change` field, `FrozenClockMixin` (`core/testing.py`), test file `academics/tests/test_change_guard.py`. OK.
3. No collisions — `released_occurrence_errors`, `schedule/tests/test_change_edit.py` do not exist. OK.
4. Migrations — none. OK.
5–7. Tools/framework/env — unchanged. OK.
8. Verification — ruff state recorded in A2; the rest as in section 9.
9. Conflicts — "move target changes" from the request needs no old-state check (A1.1); the new-state guard is extended instead (A1.3). Not a contradiction of the requirement (every release of an occurrence is checked).
10. Assumptions / blockers — none.

### A5. Order and verification
1. A2 first (`ruff format --check .` passes). 2. Write A1.6 tests; confirm 1–4, 7, 8, 10, 11 fail. 3. Implement A1.2–A1.5. 4. Section 9 commands (seed checks with the temporary DB from A3). `REPORT` to the Reviewer with the regression evidence. Do not commit.
