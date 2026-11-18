# TASK-013-FIX: Reason-only edits stay read; test uploads never leak with --parallel

Assignee: **Coder** (DeepSeek, thr_ng6cbgatm6). Request: Team lead, approved by the user (item 1: user decision 18.11; item 2: found by the Team lead 18.11).

## Goal

1. Since TASK-013 the reason of a lesson change is hidden from students. An edit that changes only the reason (or other fields students do not see) must not make the change "Новое" again in the feed or raise the badge.
2. `python manage.py test --parallel N` on macOS must not write test uploads into the project's `private_media/`. Every test process must use the temporary private media directory, and the directory must be removed after the run.

## Acceptance criteria

- AC1. `LessonChange` has a new field `changed_at` (`DateTimeField`, `editable=False`, default `core.clock.now`). It is set to the current time on insert and on every save that changes a field visible to students: `weekly_lesson`, `original_date`, `kind`, `new_date`, `new_slot`, `new_room`, `new_teacher`. A save that changes only `reason` (or nothing visible) keeps `changed_at`. `updated_at` (auto_now) stays as the technical "last saved" time.
- AC2. The rule holds for every write path: `schedule.mutations.save_lesson_change`, the admin change form, and any direct `save()`.
- AC3. The feed uses `changed_at`: `LessonChangeSource.event_field = "changed_at"` and the item timestamp is `obj.changed_at`. The unread count and the "Новое" mark follow `changed_at`.
- AC4. Migration `schedule/0006_lessonchange_changed_at` adds the field and copies `updated_at` into `changed_at` for every existing row. After the migration, every existing change has the same read/unread state as before.
- AC5. The test runner sets the environment variable `PRIVATE_MEDIA_ROOT` to its temporary directory before any worker starts and restores the old value (or removes the variable) at teardown. Spawned workers re-read settings and get the temporary directory. The directory is removed after the run. The serial behaviour is unchanged.
- AC6. `python manage.py test --parallel 2` on macOS passes, and the file list of the project's `private_media/` is identical before and after the run (and after a serial run).

## Out of scope

- Showing `changed_at` to students. Changing `updated_at` or removing it.
- Bulk writes (`QuerySet.update`, `bulk_update`): no application code uses them for `LessonChange` (checked: `grep -rn "bulk_create\|bulk_update\|\.update(" schedule notifications` finds none for this model). They bypass `save()`; this is documented in the model docstring comment, not handled.
- Installing `tblib` (see Risks).

## Design decisions

- **D1. A separate field instead of changing `updated_at`.** `updated_at` is `auto_now`; Django sets it on every `save()` and the admin cannot skip it. A second field with an explicit rule keeps both meanings: "last saved" for staff, "last change students can see" for the feed. The same pattern as `core.clock.now` defaults in `academics/0002`.
- **D2. The rule lives in `LessonChange.save()`**, so the admin (`ModelAdmin.save_model` → `obj.save()`), `save_lesson_change` and seeds all follow it without extra code. On update, `save()` reads the stored visible fields with one `SELECT … WHERE pk = …` and compares them. One extra query per update is acceptable: changes are edited rarely and by staff only. This is simpler and safer than a snapshot in `from_db()` (no stale state after `refresh_from_db` or after an insert).
- **D3. Visible fields** are compared by attribute name: `weekly_lesson_id`, `original_date`, `kind`, `new_date`, `new_slot`, `new_room_id`, `new_teacher_id`. `reason`, `seed_key`, `created_at`, `updated_at` are not visible. A new instance (`self._state.adding`) always gets `changed_at = now`. If the stored row is gone (deleted by another transaction), treat it as visible (set `changed_at`).
- **D4. `update_fields`.** If a caller passes `update_fields` and a visible field changed, add `"changed_at"` to it. Today only migration `0003` uses `update_fields` (on the historical model, which has no custom `save()`).
- **D5. Data migration.** `AddField` with `default=core.clock.now` fills old rows with the migration time; the `RunPython` step then sets `changed_at = updated_at` for all rows (`QuerySet.update(changed_at=F("updated_at"))`; no model `save()` runs). Reverse: `RunPython.noop` (the reverse `AddField` drops the column).
- **D6. Test runner: environment variable.** On macOS the parallel runner starts workers with `spawn`. Django's `_init_worker` then calls `django.setup()` and Django's own `setup_test_environment()` (not our runner's method), so our `override_settings` from the parent is lost. Workers inherit the parent's environment, and `config/settings.py:126` reads `PRIVATE_MEDIA_ROOT` from the environment (`django-environ` `read_env` uses `setdefault`, so the process environment wins over `.env`). Setting `os.environ["PRIVATE_MEDIA_ROOT"]` in `ProjectTestRunner.setup_test_environment` (it runs before the suite and the pool are built) fixes every worker with no subclass of Django's private `ParallelTestSuite`/`_init_worker` API. We keep the `override_settings` for the parent process (its settings are already loaded). With `fork` (Linux CI) workers copy the parent memory; nothing changes there.

## Architecture / files

- `schedule/models.py`: import `from core import clock`; module constant `STUDENT_VISIBLE_FIELDS`; field `changed_at`; methods `save()` and `_student_visible_change()` (F1, F2).
- New `schedule/migrations/0006_lessonchange_changed_at.py` (F3).
- `schedule/admin.py`: `LessonChangeAdmin.readonly_fields = ("seed_key", "changed_at")` (staff can see the student-visible time; the field is not editable).
- `notifications/sources.py`: `LessonChangeSource.event_field = "changed_at"`; `timestamp=obj.changed_at` (F4).
- `core/test_runner.py` (F5).
- Tests: `notifications/tests/test_feed.py`, new `schedule/tests/test_changed_at.py`, `core/tests/test_storage.py`.
- `README.md`: one sentence in "## Notifications" (or where lesson changes in the feed are described): "A lesson change is "new" again only when students can see the difference (date, slot, room, teacher, kind); editing the reason does not notify." and one sentence in "## Test & lint": "`--parallel` is safe: workers use the runner's temporary private media directory."

## Functions

### F1. `schedule/models.py` — constant and field

```python
from core import clock  # add after "from django.db import models", before the relative imports

STUDENT_VISIBLE_FIELDS: tuple[str, ...] = (
    "weekly_lesson_id",
    "original_date",
    "kind",
    "new_date",
    "new_slot",
    "new_room_id",
    "new_teacher_id",
)
```
Place the constant directly above `class LessonChange(models.Model):`. Add the field directly after `updated_at`:
```python
    changed_at = models.DateTimeField(
        "изменение для студентов", default=clock.now, editable=False
    )
```

### F2. `LessonChange.save()` and `LessonChange._student_visible_change()`

Place both directly above `def __str__` of `LessonChange`.

```python
    def save(self, *args, **kwargs):
        if self._student_visible_change():
            self.changed_at = clock.now()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "changed_at"}
        super().save(*args, **kwargs)

    def _student_visible_change(self) -> bool:
        if self._state.adding or self.pk is None:
            return True
        stored = (
            type(self)._default_manager.filter(pk=self.pk).values(*STUDENT_VISIBLE_FIELDS).first()
        )
        if stored is None:
            return True
        return any(stored[f] != getattr(self, f) for f in STUDENT_VISIBLE_FIELDS)
```
- Inputs: the instance. Output: `None` / `bool`. No exceptions of its own.
- `kind` compares fine: `ChangeKind` is a `TextChoices` (a `str`).
- Callers: everything that saves a `LessonChange`. Access is unchanged (admin: superuser; services: staff code paths).
- Tests: T1–T6.

### F3. `schedule/migrations/0006_lessonchange_changed_at.py`

Generate with `python manage.py makemigrations schedule --name lessonchange_changed_at`, then add the data step so the file is exactly (after `ruff format` on this one file):

```python
import core.clock
from django.db import migrations, models
from django.db.models import F


def copy_updated_at(apps, schema_editor):
    LessonChange = apps.get_model("schedule", "LessonChange")
    LessonChange.objects.update(changed_at=F("updated_at"))


class Migration(migrations.Migration):
    dependencies = [
        ("schedule", "0005_lessonchange_reason_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="lessonchange",
            name="changed_at",
            field=models.DateTimeField(
                default=core.clock.now, editable=False, verbose_name="изменение для студентов"
            ),
        ),
        migrations.RunPython(copy_updated_at, migrations.RunPython.noop),
    ]
```
(Keep the "Generated by Django" header line if makemigrations writes it.)

### F4. `notifications/sources.py` — `LessonChangeSource`

- `event_field = "updated_at"` → `event_field = "changed_at"`.
- In `to_item`: `timestamp=obj.updated_at,` → `timestamp=obj.changed_at,`.
- Nothing else changes.

### F5. `core/test_runner.py`

```python
"""Test runner that redirects private uploads to a temporary directory."""

import os
import shutil
import tempfile
from pathlib import Path

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings

PRIVATE_MEDIA_ENV = "PRIVATE_MEDIA_ROOT"


class ProjectTestRunner(DiscoverRunner):
    """Uploads go to a temporary directory in the parent and in every worker.

    Parallel workers started with "spawn" (macOS) re-import settings, so the
    directory is also passed through the environment (settings read it).
    """

    def setup_test_environment(self, **kwargs) -> None:
        super().setup_test_environment(**kwargs)
        self._private_dir = tempfile.mkdtemp(prefix="test-private-media-")
        self._old_private_env = os.environ.get(PRIVATE_MEDIA_ENV)
        os.environ[PRIVATE_MEDIA_ENV] = self._private_dir
        self._private_override = override_settings(PRIVATE_MEDIA_ROOT=Path(self._private_dir))
        self._private_override.enable()

    def teardown_test_environment(self, **kwargs) -> None:
        self._private_override.disable()
        if self._old_private_env is None:
            os.environ.pop(PRIVATE_MEDIA_ENV, None)
        else:
            os.environ[PRIVATE_MEDIA_ENV] = self._old_private_env
        shutil.rmtree(self._private_dir, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
```

## Feasibility check

1. Clean starting point: `git status --short` shows only ` M plan.md` (the Team lead's file; allowed). HEAD `8316949 TASK-013: …`.
2. Referenced objects exist: `schedule/models.py:130` `updated_at = DateTimeField("изменено", auto_now=True)`, `LessonChange.__str__` (line 195 area), `schedule/mutations.py:save_lesson_change` (full_clean + save in a transaction), `schedule/admin.py:54` `readonly_fields = ("seed_key",)` (no custom `save_model`, so the admin calls `obj.save()`), `notifications/sources.py:186` `event_field = "updated_at"` and `:216` `timestamp=obj.updated_at`, `core/clock.py:now`, `core/test_runner.py:ProjectTestRunner`, `config/settings.py:126-127` (`PRIVATE_MEDIA_ROOT` from env, default `BASE_DIR / "private_media"`), `config/settings.py:132` `TEST_RUNNER`, `core/tests/test_storage.py:38` `TestRunnerTests.test_test_runner_uses_temp_dir`, `notifications/tests/test_feed.py:332` `test_edited_change_is_new_again` (class `LessonChangeSourceTests`, `frozen_now = NOW = "2026-11-11 12:00"`), `notifications/tests/test_feed.py:382` `AdminEventsTests` (admin POST pattern), helpers `make_world`, `set_seen`, `make_lesson`, `make_room`, `moscow`.
3. New names are free: `changed_at`, `STUDENT_VISIBLE_FIELDS`, `_student_visible_change`, `PRIVATE_MEDIA_ENV`, migration `0006_lessonchange_changed_at` (latest is `0005_lessonchange_reason_optional`), `schedule/tests/test_changed_at.py`.
4. Data and migrations: `makemigrations --check --dry-run` clean before. Prototype in a temporary copy of HEAD (`git archive HEAD | tar -x`, `$TMPDIR/t013fix/proj`): `makemigrations schedule --name lessonchange_changed_at` produced the `AddField` above; with the `RunPython` step added, a migration test (migrate to 0005, create a change, set `updated_at` to 2026-11-10 09:30 MSK, migrate to 0006) gave `changed_at == updated_at`; `makemigrations --check` clean after. `core.clock.now` is already used as a migration default (`academics/migrations/0002_…`).
5. Tools: Python 3.12 `.venv`, Django 5.2.19, ruff 0.17.4. No new dependency.
6. Framework capabilities (installed Django source, `.venv/lib/python3.12/site-packages/django/test/runner.py`): `_init_worker` (line 402) calls `django.setup()` and `setup_test_environment(debug=…)` only when the start method is `spawn` (line 426); `DiscoverRunner.run_tests` calls `self.setup_test_environment()` first (line 1072), before the suite and the pool. `multiprocessing.get_start_method()` is `spawn` here (macOS, Python 3.12). `QuerySet.values("weekly_lesson_id", …)` accepts attnames.
7. Environment: no new env variables for the app; the runner sets `PRIVATE_MEDIA_ROOT` only inside the test process.
8. Verification is runnable on the current tree: `check` (no issues), `makemigrations --check` (no changes), `ruff check .` (passed), `ruff format --check .` (189 files formatted), `python manage.py test --parallel 1`: **Ran 1072 tests, OK** (log `/tmp/claude-501/test-20261118-102946.log`, 2026-11-18 ~21:30 MSK); the project's `private_media/` has 3 files before and after that run.
   Prototype results in the copy (2026-11-18 ~21:27–21:30 MSK):
   - serial `test core.tests.test_proto_t013fix notifications schedule core.tests.test_storage`: 331 tests, the only failure is the old `test_edited_change_is_new_again` (`AssertionError: 0 != 1`) — expected, it asserts the old behaviour (log `/tmp/claude-501/test-t013fix-proto-20261118-102751.log`); the new service, admin and migration tests passed; a child Python process started with the test environment printed the temporary directory as `settings.PRIVATE_MEDIA_ROOT`;
   - `--parallel 2` on `petitions core.tests.test_storage` + prototype tests **with** F5: 165 tests OK, 0 files in the copy's `private_media/` (log `/tmp/claude-501/test-t013fix-par-20261118-102909.log`);
   - the same **with the old runner**: 42 files written into the copy's `private_media/`, `test_test_runner_uses_temp_dir` failed with `PosixPath('<copy>') unexpectedly found in <PosixPath.parents>`, and the parallel run crashed with `TypeError: cannot pickle 'traceback' object` (no `tblib`) (log `/tmp/claude-501/test-t013fix-par-old-*.log`). This reproduces the Team lead's finding.
9. Conflicts: none.
10. Assumptions / blockers: none.

## Test plan

Time-dependent tests use `FrozenClockMixin` with `frozen_now = "2026-11-11 12:00"` and `mock.patch("django.utils.timezone.now", …)` for later moments (`core.clock.now` reads `timezone.now` at call time, so the patch applies).

### Traceability

| AC | Tests |
|---|---|
| AC1 | `schedule/tests/test_changed_at.py::ChangedAtTests::test_insert_sets_changed_at`, `::test_reason_only_keeps_changed_at`, `::test_each_visible_field_moves_changed_at`, `::test_updated_at_still_moves` |
| AC2 | `::test_reason_only_keeps_changed_at` (service), `::test_admin_reason_only_keeps_changed_at`, `::test_admin_visible_edit_moves_changed_at`, `::test_update_fields_includes_changed_at` |
| AC3 | `notifications/tests/test_feed.py::LessonChangeSourceTests::test_edited_change_is_new_again` (updated), `::test_reason_only_edit_stays_read`, `::test_admin_reason_only_edit_stays_read`, `::test_item_timestamp_is_changed_at` |
| AC4 | `schedule/tests/test_changed_at.py::ChangedAtMigrationTests::test_copies_updated_at` |
| AC5, AC6 | `core/tests/test_storage.py::TestRunnerTests::test_test_runner_uses_temp_dir` (unchanged; must pass serial and `--parallel 2`), `::test_env_points_to_temp_dir`, `::test_fresh_process_gets_temp_dir`, `::test_runner_restores_env`; Verification steps 5–7 |

### Access matrix

No view, URL or permission changes. The admin change view is superuser-only as today (existing admin tests). The new admin tests log in as the superuser `make_world().root`.

### Tests (file, class, method)

`schedule/tests/test_changed_at.py` (new):
- `ChangedAtTests(FrozenClockMixin, TestCase)`, `frozen_now = "2026-11-11 12:00"`; `setUpTestData`: `make_world()`, rooms `room-101`, `room-102`, teacher `make_teacher("Замена")`, a lesson `make_lesson([w.gx1], weekday=2, slot=1, room=room101)`. Helper `_cancel()` → `save_lesson_change(LessonChange(weekly_lesson=lesson, original_date=date(2026, 11, 11), kind=ChangeKind.CANCELLED, reason="Причина"))`. `T0 = moscow("2026-11-11 12:00")`, `T1 = T0 + 1 h`.
  - `test_insert_sets_changed_at`: after `_cancel()`, `changed_at == T0` (also with `LessonChange.objects.create(...)` for a second lesson date: `changed_at == T0`).
  - `test_reason_only_keeps_changed_at`: with `timezone.now` patched to `T1`, set `reason = "Новая причина"` and call `save_lesson_change`; reload: `reason` changed, `changed_at == T0`.
  - `test_updated_at_still_moves`: same edit; reload: `updated_at == T1` (the technical field still moves).
  - `test_each_visible_field_moves_changed_at` (subTest per field): start from a fresh change each time and, at `T1`, change one field: `original_date` → 2026-11-18 (cancel); `kind` → `ROOM_CHANGED` with `new_room=room102`; for a `ROOM_CHANGED` change, `new_room` → another room (create `room-103`); for a `TEACHER_REPLACED` change, `new_teacher` → another teacher; for a `MOVED` change (new_date 2026-11-12, new_slot 3), `new_date` → 2026-11-13 and separately `new_slot` → 4; `weekly_lesson` → a second lesson of the same group (weekday 2, slot 2, room 102). After each save: `changed_at == T1`. Use valid combinations (`full_clean` runs in `save_lesson_change`).
  - `test_update_fields_includes_changed_at`: at `T1`, `change.original_date = date(2026, 11, 18); change.save(update_fields=["original_date"])`; reload: `changed_at == T1`. And `change.reason = "X"; change.save(update_fields=["reason"])` at `T1 + 1 h`: `changed_at` stays `T1`.
  - `test_admin_reason_only_keeps_changed_at`: superuser `force_login`; at `T1` POST to `reverse("admin:schedule_lessonchange_change", args=[pk])` with `{"weekly_lesson": lesson.pk, "original_date": "2026-11-11", "kind": "cancelled", "new_date": "", "new_slot": "", "new_room": "", "new_teacher": "", "reason": "Из админки"}` → 302; reload: `reason == "Из админки"`, `changed_at == T0`.
  - `test_admin_visible_edit_moves_changed_at`: the same POST with `"original_date": "2026-11-18"` → 302; `changed_at == T1`.
  - `test_admin_shows_changed_at_readonly`: GET the change page → 200; the form has no input named `changed_at`; the page contains the label "Изменение для студентов" (Django capitalises the verbose name).
- `ChangedAtMigrationTests(TransactionTestCase)`:
  - `test_copies_updated_at`: `executor = MigrationExecutor(connection)`; `executor.migrate([("schedule", "0005_lessonchange_reason_optional")])`; `apps = executor.loader.project_state([("schedule", "0005_lessonchange_reason_optional")]).apps`; create with historical models `university.Room` (`code="room-101", floor=1, number="101"`), `university.Teacher` (`last_name="T", first_name="I"`), `university.Discipline` (`name="D", short_name="D"`), `schedule.WeeklyLesson` (`weekday=2, slot=1, discipline, lesson_type="lecture", teacher, room, valid_from=date(2026, 9, 1), valid_until=date(2026, 12, 31)`) and two `schedule.LessonChange` rows (cancelled on 2026-11-11 and 2026-11-18); set their `updated_at` with `.filter(pk=…).update(updated_at=moscow("2026-11-10 09:30"))` and `moscow("2026-11-10 15:00")`. Then a NEW `MigrationExecutor(connection)` migrates to `[("schedule", "0006_lessonchange_changed_at")]`; with `executor.loader.project_state(...).apps` read the rows: `changed_at == updated_at` for both. In `tearDown` (or `addCleanup` registered first): `executor = MigrationExecutor(connection); executor.loader.build_graph(); executor.migrate(executor.loader.graph.leaf_nodes())` so later tests see the full schema. This keeps the unread state: unread is `event_field > seen_until`, and the value of the event field is the same before (`updated_at`) and after (`changed_at`).

`notifications/tests/test_feed.py` (class `LessonChangeSourceTests`):
- `test_edited_change_is_new_again` — update (comment `# TASK-013-FIX: a visible edit (new date) makes the change new; a reason-only edit does not, see test_reason_only_edit_stays_read`): inside the patched block replace `change.reason = "Новая причина"` with `change.original_date = D + timedelta(days=7)`; the rest stays (`unread_count == 1`).
- New `test_reason_only_edit_stays_read`: the old scenario (reason-only edit via `save_lesson_change` at `t + 1 h`) → `unread_count(_ctx(self.w.ax, now=t + timedelta(hours=2))) == 0`, and the `lesson-change-<pk>` item from `build_feed(ctx)` is not new: `ctx.is_new(item.timestamp)` is False (`FeedContext.is_new`, `notifications/sources.py:48`; do not rely on `FeedItem.is_new`, which `to_item` does not set).
- New `test_admin_reason_only_edit_stays_read`: superuser POST as in `ChangedAtTests::test_admin_reason_only_keeps_changed_at` at `t + 1 h` → unread count stays 0.
- New `test_item_timestamp_is_changed_at`: after a reason-only edit at `t + 1 h`, the item's `timestamp == change.changed_at` (reloaded) and `!= change.updated_at`.

`core/tests/test_storage.py` (class `TestRunnerTests`):
- `test_test_runner_uses_temp_dir`: unchanged.
- New `test_env_points_to_temp_dir`: `os.environ["PRIVATE_MEDIA_ROOT"] == str(settings.PRIVATE_MEDIA_ROOT)`.
- New `test_fresh_process_gets_temp_dir` (simulates a spawned worker): `subprocess.run([sys.executable, "-c", "import django; django.setup(); from django.conf import settings; print(settings.PRIVATE_MEDIA_ROOT)"], cwd=settings.BASE_DIR, env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings"}, capture_output=True, text=True, check=True, timeout=60)`; `stdout.strip() == str(settings.PRIVATE_MEDIA_ROOT)`. (Fails on the old runner: the child falls back to `<project>/private_media` or to `.env`.)
- New `test_runner_restores_env` (`SimpleTestCase`, no real Django test environment re-setup): with `mock.patch.object(DiscoverRunner, "setup_test_environment")` and `mock.patch.object(DiscoverRunner, "teardown_test_environment")`, and `mock.patch.dict(os.environ, {"PRIVATE_MEDIA_ROOT": "/old/value"})`: `runner = ProjectTestRunner()`; `runner.setup_test_environment()`; assert `os.environ["PRIVATE_MEDIA_ROOT"] == runner._private_dir`, the directory exists, `settings.PRIVATE_MEDIA_ROOT == Path(runner._private_dir)`; `runner.teardown_test_environment()`; assert `os.environ["PRIVATE_MEDIA_ROOT"] == "/old/value"`, the directory no longer exists, and `settings.PRIVATE_MEDIA_ROOT` is back to the outer test-run value. Second case: with the variable removed from `os.environ` (`mock.patch.dict(os.environ, clear=False)` + `os.environ.pop(...)` inside), after teardown the variable is absent. Restore the outer value at the end (the `patch.dict` context does it).

### Edge cases

- Reason-only edit (service and admin); edits of each visible field; `update_fields` with and without a visible field.
- Two existing rows with different `updated_at` in the migration test.
- A user shell that already exports `PRIVATE_MEDIA_ROOT` (restored after the run).
- Serial and `--parallel 2` runs.

### Query count

No list page changes. `save()` makes one extra `SELECT` on update only (D2). The existing feed query-count tests (`notifications/tests/test_views.py::QueryCountTests`) must pass unchanged.

## Implementation order

1. F1, F2 (model), F3 (migration), admin `readonly_fields`. Run `python manage.py makemigrations --check --dry-run` and `python manage.py test schedule --parallel 1` (log).
2. F4 (feed source). Update and add the feed tests; add `schedule/tests/test_changed_at.py`. Run `python manage.py test schedule notifications --parallel 1` (log).
3. F5 (runner) and the `TestRunnerTests` tests. Run `python manage.py test core --parallel 1` (log).
4. README sentences. Full verification below.

## Verification

```bash
source .venv/bin/activate
python manage.py check
DEBUG=false ALLOWED_HOSTS=example.com ADMIN_URL=ci-staff-panel/ SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop python manage.py check --deploy --fail-level WARNING
python manage.py makemigrations --check --dry-run
# 1. File list of private_media before
find private_media -type f | sort > "$TMPDIR/pm-before.txt"
# 2. Serial run
python manage.py test --parallel 1 2>&1 | tee "$TMPDIR/test-serial-$(date +%Y%m%d-%H%M%S).log"
# 3. Parallel run (macOS uses spawn)
python manage.py test --parallel 2 2>&1 | tee "$TMPDIR/test-parallel-$(date +%Y%m%d-%H%M%S).log"
# 4. Midnight boundary run
python scripts/run_tests_at.py 2026-11-19T00:00:00 2>&1 | tee "$TMPDIR/test-midnight-$(date +%Y%m%d-%H%M%S).log"
# 5. File list after: must be identical
find private_media -type f | sort > "$TMPDIR/pm-after.txt"
diff "$TMPDIR/pm-before.txt" "$TMPDIR/pm-after.txt" && echo "private_media unchanged"
# 6. No leftover temp dirs from this run
ls -d "${TMPDIR:-/tmp}"/test-private-media-* 2>/dev/null | wc -l   # report the number before and after steps 2-4
# 7. Migration on a database seeded BEFORE the change (temporary files only)
mkdir -p "$TMPDIR/t013fix-before" && git archive HEAD | tar -x -C "$TMPDIR/t013fix-before"
#   in "$TMPDIR/t013fix-before" (no .env there): DEBUG=true SECRET_KEY=<50+ char dummy> DEMO_PASSWORD=... PRIVATE_MEDIA_ROOT="$TMPDIR/t013fix-pm"
#   DATABASE_URL="sqlite:///$TMPDIR/t013fix-before.sqlite3" python manage.py migrate && ... python manage.py seed_demo
#   then in the project: DATABASE_URL="sqlite:///$TMPDIR/t013fix-before.sqlite3" python manage.py migrate
#   check with "python manage.py shell -c": every LessonChange has changed_at == updated_at; then seed_demo twice.
ruff check <the Python files of this task>
ruff format --check <the Python files of this task>
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
git status --short
```
- `git archive HEAD | tar -x` only reads git. Never run `git stash`, `git checkout`, `git worktree`.
- Never delete files in the project's `private_media/` (it has 3 files before the change). Never touch `db.sqlite3`.
- If any run fails or stalls, even once, put the test name, the Moscow time and the traceback excerpt into the REPORT. Note: in `--parallel` mode on macOS a failing test can crash the run with `TypeError: cannot pickle 'traceback' object` (no `tblib`); if you see it, rerun the failing module with `--parallel 1` to get the real traceback and report both.

## Risks

- **Bulk updates** (`QuerySet.update`) bypass `save()` and do not move `changed_at`. No code uses them for `LessonChange` today. Add a one-line comment above `save()`: `# Bulk updates bypass this rule; use save() / save_lesson_change().`
- **Concurrency.** Two staff edits of the same change at the same time: each `save()` compares against the row it reads; the worst case is a visible edit without a `changed_at` bump if the other transaction committed the same visible values first — harmless (students already see those values). `save_lesson_change` runs inside `transaction.atomic()`.
- **`tblib` missing.** Parallel failures on macOS crash instead of reporting (see Verification). Not in scope; no new dependency.
- **CI (Linux, fork)** is unaffected by F5; the env variable is set but workers already share the parent's settings.
