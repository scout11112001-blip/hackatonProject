# TASK-004: Technical debt from TASK-001..003 reviews

Author: Planner. Status: ready for implementation.
Base commit: `a240f23`. Product context: `plan.md` section 6a. Previous specs: `docs/tasks/TASK-001.md` … `TASK-003.md`.

No new features. Every fix is minimal and has a regression test. Business rules live at model/service level; admin forms only call them.

---

## 1. Items and acceptance criteria

| # | Item | Done when |
|---|---|---|
| 1 | Login brute-force protection | (username, IP) lockout after N failures for M seconds, DB-backed, site and admin login, generic messages, proxy header only via explicit setting |
| 2 | `seed_demo` record-number collision | clear `CommandError`, nothing written |
| 3 | `<p>` inside `<ul>` in student list | valid markup, empty state kept |
| 4 | Role/profile consistency | role change with a profile of the other role → validation error (admin form error, no 500); profile/role mismatch rejected |
| 5 | Demo schedule marker | demo lessons/changes marked by `seed_key`; admin data with the same old key survives re-seeding; data migration marks existing demo rows |
| 6 | Concurrency in schedule writes | room and group rows locked (`select_for_update`) before conflict checks, in every write path |
| 7 | Re-validation against existing changes | changing weekday/slot/room/groups/range of a weekly lesson re-checks all existing changes (own and others) |

All existing verification commands pass; `seed_demo` runs twice.

## 2. Out of scope
New features, grades, visual theme, manual 360 px check, CAPTCHA, email alerts, IP-only throttling, cleanup command for throttle rows (opportunistic cleanup only, see 4.3). Reference data (rooms/teachers/disciplines) keeps the current `update_or_create` behaviour in the seed.

---

## 2a. Files

Create:
```
accounts/throttling.py
accounts/forms.py
accounts/migrations/0002_loginthrottle.py                 (generated)
accounts/tests/test_throttling.py
accounts/tests/test_role_consistency.py
schedule/locking.py
schedule/migrations/0002_<generated>.py                   (generated: seed_key fields + constraints)
schedule/migrations/0003_mark_existing_demo_rows.py       (hand-written data migration)
schedule/tests/test_locking.py
schedule/tests/test_revalidation.py
schedule/tests/test_demo_marker.py
```
Change:
```
config/settings.py, config/env_utils.py, core/tests/test_env_utils.py, core/tests/test_settings.py,
accounts/models.py, accounts/admin.py, accounts/views.py, accounts/demo.py,
accounts/templates/accounts/student_list.html, accounts/tests/test_seed_demo.py, accounts/tests/test_views.py,
schedule/models.py, schedule/validation.py, schedule/admin.py, schedule/demo.py,
.env.example, README.md
```
No other files. No new dependencies.

---

## 3. Item 1 — login brute-force protection

### 3.1 Decision: DB-backed, no new dependency
- `django-axes` was considered and rejected: it requires `request` in every `authenticate()` call (breaks `Client.login()` in tests and any helper that calls `authenticate()` without a request), adds 3 tables, a middleware, an auth backend and `django-ipware`. We have exactly two entry points (site login and admin login), both `AuthenticationForm` subclasses, so one form mixin covers all.
- Storage: one DB table `accounts.LoginThrottle`. Works with many gunicorn workers (shared DB), row lock per key avoids lost updates.
- Key: `(normalized username, client IP)`. Never username alone (would let anyone lock the jury accounts), never IP alone.

### 3.2 Settings (`config/settings.py`) and env helpers

Add after `ADMIN_URL`:
```python
LOGIN_FAILURE_LIMIT = env.int("LOGIN_FAILURE_LIMIT", default=5)
LOGIN_LOCKOUT_SECONDS = env.int("LOGIN_LOCKOUT_SECONDS", default=900)
if LOGIN_FAILURE_LIMIT < 1 or LOGIN_LOCKOUT_SECONDS < 1:
    raise ImproperlyConfigured("LOGIN_FAILURE_LIMIT and LOGIN_LOCKOUT_SECONDS must be positive.")
CLIENT_IP_HEADER = resolve_client_ip_header(env.str("CLIENT_IP_HEADER", default=""))
```
(`from django.core.exceptions import ImproperlyConfigured`.)

`config/env_utils.py`:
```python
def resolve_client_ip_header(raw: str) -> str
```
- Purpose: map the env value to a `request.META` key; empty = do not trust any proxy header.
- Algorithm: `value = raw.strip().lower()`; `""` → `""`; `"x-real-ip"` → `"HTTP_X_REAL_IP"`; `"x-forwarded-for"` → `"HTTP_X_FORWARDED_FOR"`; anything else → `ImproperlyConfigured("CLIENT_IP_HEADER must be empty, 'X-Real-IP' or 'X-Forwarded-For'.")`.
- Tests (`core/tests/test_env_utils.py`): `""` and `"  "` → `""`; `"X-Real-IP"` → `"HTTP_X_REAL_IP"`; `"x-forwarded-for"` → `"HTTP_X_FORWARDED_FOR"`; `"X-Client-IP"` → `ImproperlyConfigured`.

`core/tests/test_settings.py` add `test_login_throttle_defaults`: `LOGIN_FAILURE_LIMIT == 5`, `LOGIN_LOCKOUT_SECONDS == 900`, `CLIENT_IP_HEADER == ""` (tests run without these env vars; if the developer's `.env` sets them, the test may be skipped with `skipUnless` on `os.environ`).

`.env.example` append:
```
# Login brute-force protection: failures per (username, IP) before lockout, lockout length.
LOGIN_FAILURE_LIMIT=5
LOGIN_LOCKOUT_SECONDS=900
# Client IP header set by YOUR reverse proxy. Leave empty unless nginx overwrites it.
# Values: X-Real-IP (recommended with `proxy_set_header X-Real-IP $remote_addr;`) or X-Forwarded-For.
CLIENT_IP_HEADER=
```
README env table: add the three rows.

### 3.3 Model `accounts.LoginThrottle` (in `accounts/models.py`)
| Field | Definition |
|---|---|
| `username_key` | `CharField("логин", max_length=150)` |
| `ip_address` | `GenericIPAddressField("IP-адрес")` |
| `failures` | `PositiveIntegerField("неудачных попыток", default=0)` |
| `first_failure_at` | `DateTimeField("первая неудача")` |
| `last_failure_at` | `DateTimeField("последняя неудача")` |
| `locked_until` | `DateTimeField("заблокирован до", null=True, blank=True)` |
- `Meta`: `constraints = [UniqueConstraint(fields=["username_key", "ip_address"], name="accounts_loginthrottle_unique_key")]`; `indexes = [Index(fields=["last_failure_at"], name="accounts_throttle_last_idx")]`; verbose `"блокировка входа"` / `"блокировки входа"`.
- `__str__` → `f"{self.username_key} @ {self.ip_address}"`.
- No `auto_now` fields (times are set explicitly from `timezone.now()` so tests can mock the clock).

Admin (`accounts/admin.py`): `LoginThrottleAdmin` — `list_display = ("username_key", "ip_address", "failures", "locked_until", "last_failure_at")`, `search_fields = ("username_key", "ip_address")`, all fields read-only (`readonly_fields` = all fields), `has_add_permission` → `False`. Deleting a row unlocks the key.

### 3.4 `accounts/throttling.py`

```python
def normalize_username(username: str) -> str
```
`return username.strip().casefold()[:150]`. Test: `"  Student1 "` → `"student1"`.

```python
def get_client_ip(request: HttpRequest | None) -> str
```
- Algorithm:
  1. `request is None` → `"0.0.0.0"`.
  2. `header = settings.CLIENT_IP_HEADER`. If `header == "HTTP_X_REAL_IP"`: `candidate = request.META.get(header, "").strip()`. If `header == "HTTP_X_FORWARDED_FOR"`: take the **last** comma-separated entry, stripped (nginx `$proxy_add_x_forwarded_for` appends the address it saw; earlier entries are client-controlled). Otherwise `candidate = ""`.
  3. If `candidate` is a valid IP (`ipaddress.ip_address(candidate)` does not raise) → return it.
  4. Else `remote = request.META.get("REMOTE_ADDR", "")`; return it if valid, else `"0.0.0.0"`.
- Tests: default setting ignores `HTTP_X_FORWARDED_FOR` and `HTTP_X_REAL_IP` (returns `REMOTE_ADDR`); with `HTTP_X_REAL_IP` setting returns that header; with XFF setting and `"1.1.1.1, 2.2.2.2"` returns `"2.2.2.2"`; invalid header value falls back to `REMOTE_ADDR`; missing `REMOTE_ADDR` → `"0.0.0.0"`; `None` → `"0.0.0.0"`.

```python
def is_locked(username: str, ip: str, now: datetime) -> bool
```
`return LoginThrottle.objects.filter(username_key=normalize_username(username), ip_address=ip, locked_until__gt=now).exists()`.

```python
def register_failure(username: str, ip: str, now: datetime) -> None
```
- Algorithm (inside `transaction.atomic()`):
  1. `key = normalize_username(username)`; `window = timedelta(seconds=settings.LOGIN_LOCKOUT_SECONDS)`.
  2. Opportunistic cleanup: `LoginThrottle.objects.filter(last_failure_at__lt=now - max(window, timedelta(days=1)), locked_until__isnull=True).delete()` and the same filter with `locked_until__lt=now - timedelta(days=1)`. (Keeps the table small; IP + login are personal data, retained ≤ ~1 day.)
  3. `row, _ = LoginThrottle.objects.get_or_create(username_key=key, ip_address=ip, defaults={"first_failure_at": now, "last_failure_at": now})`.
  4. `row = LoginThrottle.objects.select_for_update().get(pk=row.pk)`.
  5. If `row.locked_until is not None and row.locked_until <= now` (expired lock) or `row.first_failure_at <= now - window` (old window): `row.failures = 0`, `row.first_failure_at = now`, `row.locked_until = None`.
  6. `row.failures += 1`; `row.last_failure_at = now`; if `row.failures >= settings.LOGIN_FAILURE_LIMIT`: `row.locked_until = now + window`.
  7. `row.save()`.

```python
def reset_failures(username: str, ip: str) -> None
```
`LoginThrottle.objects.filter(username_key=normalize_username(username), ip_address=ip).delete()`.

### 3.5 `accounts/forms.py`

```python
class ThrottledLoginFormMixin:
    error_messages = {
        **AuthenticationForm.error_messages,
        "locked": "Слишком много неудачных попыток входа. Попробуйте позже.",
    }

    @method_decorator(sensitive_variables())
    def clean(self) -> dict[str, Any]
```
- Algorithm:
  1. `username = self.cleaned_data.get("username") or ""`; `ip = get_client_ip(self.request)`; `now = timezone.now()`.
  2. If `username` and `is_locked(username, ip, now)` → `raise ValidationError(self.error_messages["locked"], code="locked")`. Do **not** call `authenticate()` while locked (no password oracle; the same message for existing and non-existing users).
  3. `try: cleaned = super().clean()` / `except ValidationError: if username: register_failure(username, ip, now); raise`.
  4. If `username`: `reset_failures(username, ip)`. Return `cleaned`.
- A failure is any `ValidationError` from `AuthenticationForm.clean()` (wrong password, unknown user, inactive user — Django already uses one generic message for all of them).
- Empty password → field error, `AuthenticationForm.clean()` does not authenticate, no failure counted.

```python
class ThrottledAuthenticationForm(ThrottledLoginFormMixin, AuthenticationForm):
    pass


class ThrottledAdminAuthenticationForm(ThrottledLoginFormMixin, AdminAuthenticationForm):
    pass
```
Wiring:
- `accounts/views.py`: `DeaneryLoginView.authentication_form = ThrottledAuthenticationForm`.
- `accounts/admin.py` (module level, after imports): `admin.site.login_form = ThrottledAdminAuthenticationForm`.

### 3.6 Tests (`accounts/tests/test_throttling.py`, `TestCase`, `@override_settings(LOGIN_FAILURE_LIMIT=3, LOGIN_LOCKOUT_SECONDS=900, CLIENT_IP_HEADER="")`)
Fixture: student `u1` with password set via `set_password` + `save` (`"Test-Pass-2026!"`). Helper `post_login(username, password, **extra)` → `self.client.post(reverse("accounts:login"), {"username": ..., "password": ...}, **extra)`. Clock: `mock.patch("django.utils.timezone.now", return_value=T0)` where needed.
1. `test_lockout_after_limit` — 3 wrong passwords; then the correct password → 200, response contains the "locked" message, user not authenticated (`"_auth_user_id" not in self.client.session`).
2. `test_lock_is_per_ip` — 3 failures from `REMOTE_ADDR="10.0.0.1"`; correct password from `REMOTE_ADDR="10.0.0.2"` → 302 (logged in).
3. `test_lock_expires` — 3 failures at T0; at `T0 + 901 s` correct password → 302.
4. `test_success_resets_counter` — 2 failures, success (302), logout (POST), 2 failures, correct password → 302.
5. `test_messages_do_not_reveal_user_existence` — the error text for a wrong password of `u1` equals the error text for unknown user `nobody`; after 3 failures each, the "locked" message is identical for both.
6. `test_xff_ignored_by_default` — 3 failures with different `HTTP_X_FORWARDED_FOR` values each (same `REMOTE_ADDR`) → 4th attempt with correct password is locked.
7. `test_xff_used_when_enabled` — `override_settings(CLIENT_IP_HEADER="HTTP_X_FORWARDED_FOR")`; 3 failures with `HTTP_X_FORWARDED_FOR="5.5.5.5"`; correct password with `HTTP_X_FORWARDED_FOR="6.6.6.6"` → 302.
8. `test_admin_login_protected` — superuser with password; 3 failures on `reverse("admin:login")`; correct password → 200 with "locked" message, not logged in.
9. `test_locked_does_not_authenticate` — after lockout, patch `django.contrib.auth.forms.authenticate` (the name `AuthenticationForm.clean()` calls) with a `mock.Mock()` and assert it was **not** called on the locked attempt.
10. Unit tests for `get_client_ip` and `normalize_username` (3.4); `register_failure` sets `locked_until = now + window` exactly at the limit; old window (`first_failure_at` older than window) restarts counting at 1.

---

## 4. Item 2 — `seed_demo` record-number collision (`accounts/demo.py`)

In `seed_demo_data`, **before** any write (first lines inside `transaction.atomic()`, after the password check):
```python
for seed in STUDENT_SEEDS:
    taken = (
        StudentProfile.objects.filter(record_number=seed.record_number)
        .exclude(user__username=seed.username)
        .exists()
    )
    if taken:
        raise DemoSeedError(
            f"Record number {seed.record_number} is already used by another student; "
            f"cannot create demo user '{seed.username}'."
        )
```
Do not print the other student's name.

Test (`accounts/tests/test_seed_demo.py`): `test_record_number_collision_fails_cleanly` — create a non-demo student (`make_student("other", group, "ST-2026-0001")`); record `User`, `Faculty`, `StudyGroup` counts; `call_command("seed_demo")` with `DEMO_PASSWORD` → `CommandError` containing `"ST-2026-0001"`; all counts unchanged; `User.objects.filter(username="student1").exists()` is `False`.

---

## 5. Item 3 — student list markup

`accounts/templates/accounts/student_list.html` content block:
```html
<h1>Студенты факультета</h1>
<p>{{ faculty.name }}</p>
{% if students %}
  <ul class="student-list">
    {% for student in students %}
      <li>
        <a href="{% url 'accounts:staff_student_detail' student.pk %}">{{ student.full_name }}</a>
        · {{ student.group.name }}, {{ student.course }} курс
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p>Студентов нет.</p>
{% endif %}
```
Test (`accounts/tests/test_views.py`): `test_staff_list_empty_state_markup` — staff of a faculty without students: response contains `<p>Студентов нет.</p>` and does not contain `class="student-list"`; the non-empty case still renders `<ul class="student-list">` with `<li>` items.

---

## 6. Item 4 — role/profile consistency (`accounts/models.py`)

All errors are **non-field** `ValidationError`s (a field key that is not in a form makes Django raise `ValueError` → 500).

`User.clean()`:
1. `super().clean()`.
2. If `self.pk is None` → return.
3. `errors = []`; if `self.role != User.Role.STUDENT` and `StudentProfile.objects.filter(user_id=self.pk).exists()` → `"У пользователя есть профиль студента. Удалите профиль, затем меняйте роль."`; if `self.role != User.Role.STAFF` and `StaffProfile.objects.filter(user_id=self.pk).exists()` → `"У пользователя есть профиль сотрудника. Удалите профиль, затем меняйте роль."`.
4. If `errors` → `raise ValidationError(errors)`.
(This also covers making a user with a profile a superuser, because a superuser must have `role=""`.)

`StudentProfile.clean()`:
1. `super().clean()`; if `self.user_id is None` → return.
2. If `self.user.role != User.Role.STUDENT` → `ValidationError("Профиль студента можно привязать только к пользователю с ролью «Студент».")`.
3. If `StaffProfile.objects.filter(user_id=self.user_id).exists()` → `ValidationError("У пользователя уже есть профиль сотрудника.")`.

`StaffProfile.clean()`: symmetric (role STAFF; existing `StudentProfile` → error).

`limit_choices_to` stays as is (extra protection in admin dropdowns).

Tests (`accounts/tests/test_role_consistency.py`, `TestCase`):
1. `test_role_change_with_student_profile_rejected_by_model` — student with profile; `user.role = STAFF`; `user.full_clean()` → `ValidationError`.
2. `test_role_change_rejected_in_admin_without_500` — superuser logged in; POST to `reverse("admin:accounts_user_change", args=[student.pk])` with data `{"username": student.username, "role": "staff", "is_active": "on", "date_joined_0": "2026-11-13", "date_joined_1": "10:00:00", "last_login_0": "", "last_login_1": "", "first_name": "", "last_name": "", "email": ""}` → status 200 (form re-displayed, not 302/500), response contains "профиль студента", DB role still `student`. (If the admin form needs more keys, add only empty/default values for them; the assertion stays the same.)
3. `test_make_superuser_with_profile_rejected` — student with profile: `is_superuser=True`, `is_staff=True`, `role=""` → `full_clean()` → `ValidationError` mentioning the profile.
4. `test_role_change_without_profile_allowed` — student without profile → role STAFF → `full_clean()` passes.
5. `test_staff_profile_for_student_user_rejected` — `StaffProfile(user=student_user, ...).full_clean()` → `ValidationError`.
6. `test_second_profile_rejected` — staff user with `StaffProfile`; `StudentProfile(user=staff_user, ...)` → `ValidationError` (role check); and for a legacy inconsistent row created with `objects.create` (student user that has a `StaffProfile` inserted directly), `StudentProfile(user=that_user, ...).full_clean()` → `ValidationError` "уже есть профиль сотрудника".
7. `test_admin_add_staff_profile_for_student_shows_error` — superuser POST to `admin:accounts_staffprofile_add` with `user=<student pk>` → 200 with a form error, no new row.

---

## 7. Item 5 — demo marker for schedule rows

### 7.1 Model fields (`schedule/models.py`)
Add to **both** `WeeklyLesson` and `LessonChange`:
```python
seed_key = models.SlugField(
    "ключ демо-данных", max_length=40, blank=True, default="", editable=False
)
```
Constraints (append to each `Meta.constraints`):
- `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="schedule_weekly_unique_seed_key")`
- `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="schedule_change_unique_seed_key")`
`""` = created by a person (admin); non-empty = created by `seed_demo`. Not `null=True` (ruff DJ001). `editable=False` keeps it out of admin forms; show it in admin via `readonly_fields = ("seed_key",)` on `WeeklyLessonAdmin` and `LessonChangeAdmin`.
Run `python manage.py makemigrations schedule` → `0002_...`.

### 7.2 Seed (`schedule/demo.py`)
- `LessonSeed` gets a first field `key: str`: `"lesson-01"` … `"lesson-18"` in the current table order. `ChangeSeed` gets `key: str`: `"change-1"` … `"change-8"` in the current order.
- Lesson lookup: `WeeklyLesson.objects.filter(seed_key=seed.key).first()`; a new lesson gets `seed_key=seed.key`. **Remove** the lookup by `(discipline, lesson_type, weekday, slot)`.
- Change refresh: replace the delete by lesson ids with `LessonChange.objects.exclude(seed_key="").delete()` (only demo changes, on any lesson).
- New changes get `seed_key=seed.key`.
- Everything else unchanged (still via `save_weekly_lesson` / `save_lesson_change`).

### 7.3 Data migration `schedule/migrations/0003_mark_existing_demo_rows.py`
- `dependencies = [("schedule", "0002_<generated name>"), ("university", "0002_discipline_room_teacher")]`.
- `operations = [migrations.RunPython(mark_existing_demo_rows, migrations.RunPython.noop)]`.
- Module constants copied as **literals** (migrations must not import `schedule.demo`):
  - `LEGACY_LESSONS`: 18 tuples `(key, discipline_name, lesson_type, weekday, slot, teacher_last_name, room_code, group_names_tuple)` = the `LESSON_SEEDS` rows with keys `lesson-01`…`lesson-18`.
  - `LEGACY_CHANGES`: 8 tuples `(key, lesson_key, kind, reason)`: `("change-1", "lesson-01", "cancelled", "Преподаватель на конференции")`, `("change-2", "lesson-16", "cancelled", "Мероприятие факультета")`, `("change-3", "lesson-08", "moved", "Перенос по просьбе преподавателя")`, `("change-4", "lesson-18", "moved", "Перенос из-за олимпиады")`, `("change-5", "lesson-13", "room_changed", "Ремонт в аудитории 308")`, `("change-6", "lesson-07", "room_changed", "Аудитория занята мероприятием")`, `("change-7", "lesson-10", "teacher_replaced", "Болезнь преподавателя")`, `("change-8", "lesson-12", "teacher_replaced", "Командировка преподавателя")`.

```python
def mark_existing_demo_rows(apps, schema_editor) -> None
```
1. `WeeklyLesson = apps.get_model("schedule", "WeeklyLesson")`; `LessonChange = apps.get_model("schedule", "LessonChange")`.
2. For each legacy lesson: skip if a row with this `seed_key` already exists. `candidates = list(WeeklyLesson.objects.filter(seed_key="", discipline__name=..., lesson_type=..., weekday=..., slot=..., teacher__last_name=..., room__code=...))`; keep only candidates whose `set(c.groups.values_list("name", flat=True)) == set(group_names)`. If **exactly one** remains → set its `seed_key` and `save(update_fields=["seed_key"])`. Otherwise do nothing (ambiguous or absent → treated as admin data).
3. For each legacy change: skip if the key exists. `candidates = list(LessonChange.objects.filter(seed_key="", weekly_lesson__seed_key=lesson_key, kind=kind, reason=reason))`; exactly one → mark.
- Strict matching (all fields + groups) is what makes this safe; the old 4-field key alone is not used.

### 7.4 Tests (`schedule/tests/test_demo_marker.py`, `TestCase`)
Use `seed_demo_data("Demo-Pass-2026-test!")` + `seed_schedule_demo(date(2026, 11, 18))`.
1. `test_seed_marks_rows` — 18 lessons and 8 changes have non-empty unique `seed_key`s.
2. `test_admin_lesson_with_same_old_key_survives_reseed` — after the first seed, create via `save_weekly_lesson` an admin lesson with the same `(discipline, lesson_type, weekday, slot)` as `lesson-01` but `valid_from=date(2028, 1, 1)`, `valid_until=date(2028, 6, 30)`, another room (`room-402`), group `ЦД-101`; re-seed twice → the admin lesson still exists with `seed_key == ""`, same room, same dates, same groups; demo lesson count with `seed_key` still 18.
3. `test_admin_change_survives_reseed` — admin-created `LessonChange` (via `save_lesson_change`, `seed_key=""`) on the admin lesson from test 2 → survives re-seeding.
4. `test_data_migration_marks_legacy_rows` — create the 18 lessons and 8 changes exactly as the old seed did but with `seed_key=""` (call `seed_schedule_demo`, then `WeeklyLesson.objects.update(seed_key="")`, `LessonChange.objects.update(seed_key="")`); add one admin lesson matching `lesson-01`'s 4-field key but with another room and non-overlapping dates; import the migration module (`importlib.import_module("schedule.migrations.0003_mark_existing_demo_rows")`) and call `mark_existing_demo_rows(django.apps.apps, None)` → 18 + 8 rows marked, the admin lesson stays `""`. Calling it a second time changes nothing.
5. `test_reseed_after_migration_no_duplicates` — after test 4's marking, `seed_schedule_demo(...)` → still 18 demo lessons, 8 demo changes, total lessons 19.

---

## 8. Item 6 — locking in schedule writes

### 8.1 `schedule/locking.py`
```python
def lock_rooms_and_groups(room_ids: Iterable[int | None], group_ids: Iterable[int]) -> None
```
- Purpose: serialize concurrent writes that could conflict. Any two conflicting lessons/changes share a room or a group, so locking those rows makes the second writer wait until the first commits; its conflict queries then see the committed data (PostgreSQL READ COMMITTED takes a new snapshot per statement).
- Algorithm:
  1. If `not transaction.get_connection().in_atomic_block` → return (locks only make sense inside a transaction; all write paths are atomic: `schedule/mutations.py` and Django admin `changeform_view`).
  2. `rooms = sorted({r for r in room_ids if r is not None})`; `groups = sorted(set(group_ids))`.
  3. If `rooms`: `list(Room.objects.select_for_update().filter(pk__in=rooms).order_by("pk").values_list("pk", flat=True))`.
  4. If `groups`: `list(StudyGroup.objects.select_for_update().filter(pk__in=groups).order_by("pk").values_list("pk", flat=True))`.
- Fixed order (rooms first, then groups, each by pk) prevents deadlocks.
- SQLite: Django ignores `select_for_update()` (no `FOR UPDATE` support); SQLite serializes writers with a database-level lock anyway. Document this in the module docstring.

### 8.2 Call sites (`schedule/validation.py`)
- `validate_weekly_lesson(...)`: first statement → `lock_rooms_and_groups([room_id], group_ids)`.
- `change_conflicts(change)`: after early return for CANCELLED/TEACHER_REPLACED, after computing `target_room_id` and `group_ids` → `lock_rooms_and_groups([target_room_id], group_ids)`, then the occurrence query.
Because the admin form, `LessonChange.clean()` and `mutations.py` all call these two functions, every path is covered. Import the module as `from . import locking` and call `locking.lock_rooms_and_groups(...)` (so tests can patch `schedule.locking.lock_rooms_and_groups`).

### 8.3 Tests (`schedule/tests/test_locking.py`)
1. `test_save_weekly_lesson_locks_room_and_groups` — `mock.patch("schedule.locking.lock_rooms_and_groups", wraps=lock_rooms_and_groups)`; `save_weekly_lesson(...)` with room R and groups G2, G1 → called with `[R.pk]` and the group ids; (order inside the helper is checked in test 3).
2. `test_change_locks_target_room` — MOVED change with `new_room` R2 → called with `[R2.pk]` and the lesson's groups.
3. `test_lock_queries_issued` — inside `transaction.atomic()` and `CaptureQueriesContext(connection)`: call `lock_rooms_and_groups([r2.pk, r1.pk, None], [g2.pk, g1.pk])`; assert two queries on `university_room` and `university_studygroup`; if `connection.features.has_select_for_update` → both contain `FOR UPDATE`; room query precedes group query.
4. `test_no_lock_outside_atomic` — `TransactionTestCase`: call the helper outside `atomic` → no queries executed.
5. `test_admin_form_locks` — `WeeklyLessonAdminForm(data=...).is_valid()` inside `atomic` → helper called.

---

## 9. Item 7 — re-validation against existing changes

### 9.1 New check inside `validate_weekly_lesson` (`schedule/validation.py`)
Signature unchanged. After the existing checks, **only if `errors` is still empty**, append the result of:
```python
def _occurrence_conflicts(*, lesson_pk: int | None, weekday: int, slot: int, valid_from: date, valid_until: date, room_id: int, group_ids: Collection[int]) -> list[str]
```
- Purpose: simulate the proposed lesson together with its existing changes and compare with everything else that happens (including other lessons' moved-in and room-changed occurrences).
- Algorithm:
  1. `own_changes = {c.original_date: c for c in LessonChange.objects.filter(weekly_lesson_id=lesson_pk).select_related("new_room")}` if `lesson_pk` else `{}`.
  2. Build proposed own occurrences `P` as tuples `(date, slot_number, room_id, original_date, label)`:
     - for each `d` in `[valid_from, valid_until]` with `d.weekday() == weekday`: `c = own_changes.get(d)`; skip if `c` is CANCELLED or MOVED; room = `c.new_room_id` if `c` is ROOM_CHANGED else `room_id`; add `(d, slot, room, d)`.
     - for each own MOVED change: add `(c.new_date, c.new_slot, c.new_room_id or room_id, c.original_date)`.
  3. If `P` is empty → `[]`.
  4. `others = [i for i in occurrences_between(min(P dates), max(P dates), None) if i.is_happening and i.lesson.id != lesson_pk]` (DB items of this lesson are stale and replaced by `P`). Index by `(date, slot.number)`.
  5. For each `p` in `P`, for each other item at `(p.date, p.slot)`:
     - `item.room.id == p.room` → `f"{p.date:%d.%m.%Y}, {p.slot} пара: аудитория {item.room.number} занята ({item.lesson.discipline.name})."`;
     - for each group of `item.lesson.groups.all()` with id in `group_ids` → `f"{p.date:%d.%m.%Y}, {p.slot} пара: группа {g.name} занята ({item.lesson.discipline.name})."`.
  6. Own duplicates: two entries of `P` with the same `(date, slot)` → `f"{date:%d.%m.%Y}, {slot} пара: занятие стоит дважды из-за переноса."`.
  7. Own ROOM_CHANGED changes with `new_room_id == room_id` → `f"Изменение на {c.original_date:%d.%m.%Y}: новая аудитория совпадает с аудиторией занятия. Удалите изменение."`.
  8. Deduplicate messages preserving order; if more than 10, keep the first 10 and append `f"…и ещё {n} конфликтов."`.
- Query cost: 1 + 4 queries regardless of the range length; the Python loop is days × lessons (small for this project).
- Notes: template-level conflicts (existing checks) still run first; this check adds date-level conflicts created by changes. It also applies to **new** lessons (`lesson_pk=None`), e.g. a new lesson placed where another lesson was moved in.

### 9.2 Tests (`schedule/tests/test_revalidation.py`, `TestCase`)
Reference week Monday 2026-11-16. Lessons valid `2026-09-01..2026-12-31`. Each test: build state with `save_weekly_lesson` / `save_lesson_change`, then change one attribute and call `save_weekly_lesson` → expect `ValidationError` whose messages contain the date `"23.11.2026"` (or the relevant date); state in DB unchanged.
1. `test_slot_change_hits_moved_in_room` — L1 (G1, R1, Mon s2). L2 (G2, R2, Tue s1) moved from Tue 2026-11-17 to Mon 2026-11-23 s3 with `new_room=R1`. Change L1 slot 2→3 → error (room R1, 23.11.2026).
2. `test_room_change_hits_room_changed_occurrence` — L1 (G1, R1, Mon s2); L3 (G3, R3, Mon s2); L3 ROOM_CHANGED on 2026-11-23 to R4. Change L1 room R1→R4 → error (23.11.2026).
3. `test_own_move_target_conflicts_after_room_change` — L1 (G1, R1, Mon s2) moved from 2026-11-23 to Wed 2026-11-25 s4 without `new_room`; L4 (G4, R2, Wed s4). Change L1 room R1→R2 → error (25.11.2026, room).
4. `test_own_room_change_equals_new_room` — L1 ROOM_CHANGED on 2026-11-23 to R2; change L1 room → R2 → error "совпадает".
5. `test_group_change_hits_moved_in_group` — L5 (G2, R5, Thu s1) moved to Mon 2026-11-23 s2 (own room R5). L1 (G1, R1, Mon s2) adds G2 → error (группа G2, 23.11.2026).
6. `test_cancelled_own_occurrence_frees_date` — like test 1 but L1's 2026-11-23 occurrence is CANCELLED → slot change allowed.
7. `test_new_lesson_where_other_was_moved_in` — no L1; L2 moved into Mon 2026-11-23 s3 room R1; create new lesson (G9, R1, Mon s3) → error.
8. `test_admin_form_reports_revalidation_error` — case 1 through `WeeklyLessonAdminForm(instance=L1, data=...)` → `is_valid() is False`, message in `non_field_errors()`.
9. `test_message_limit` — L1 (G1, R1, Mon s2); O (G2, R2, Mon s3) with ROOM_CHANGED to R1 on 12 different Mondays inside the range; change L1 slot 2→3 → exactly 11 messages, the last starts with `"…и ещё"`.

---

## 10. Implementation order

Shell: repo root, `.venv` active, `export DEBUG=true`, `export DEMO_PASSWORD='Local-Demo-Pass-2026!'`. Never open or edit `.env`. Do not delete `db.sqlite3` or existing migrations.

1. Item 3 (template) + test. `python manage.py test accounts`.
2. Item 2 (seed precheck) + test.
3. Item 4 (clean methods) + tests.
4. Item 1: `env_utils` + settings + `.env.example`; `LoginThrottle` model → `makemigrations accounts`; `throttling.py`, `forms.py`, wiring; admin; tests.
5. Item 5: `seed_key` fields → `makemigrations schedule`; seed changes; hand-written `0003` migration; `migrate`; tests.
6. Item 6: `locking.py` + call sites + tests.
7. Item 7: `_occurrence_conflicts` + tests. Run the whole suite.
8. README (env rows, "Login protection" paragraph incl. nginx `proxy_set_header X-Real-IP $remote_addr;` + `CLIENT_IP_HEADER=X-Real-IP`, "Demo data": demo schedule rows carry `seed_key`, admin-created rows are never touched by `seed_demo`).
9. `ruff format .`; section 11; `REPORT` to the Reviewer. Do not commit.

## 11. Verification
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
Also on the existing local DB (created before this task): `python manage.py migrate` applies `0003` and then `seed_demo` reports 18 lessons / 8 changes without duplicates (`WeeklyLesson.objects.count()` unchanged).

In the `REPORT`: output tails, test count, and for item 6 state that SQLite does not emit `FOR UPDATE` (test 3 branch taken).

## 12. Risks
- **Lockout as DoS**: an attacker on the **same IP** as a jury member could lock that member's login for 15 minutes. Accepted (narrow); per-IP key prevents global lockout.
- **Proxy header spoofing**: `CLIENT_IP_HEADER` must be set only if nginx **overwrites** the header. With the wrong setting every client could choose its own IP and bypass the limit.
- **Personal data**: login names and IPs are stored ≤ ~1 day for throttling; no passwords are stored or logged.
- **Locks**: effective on PostgreSQL only; SQLite serializes writes. Locks are held until the admin/mutation transaction ends (short).
- **Data migration**: strict matching may leave some legacy demo rows unmarked (e.g. edited in admin); they are then treated as admin data, and the seed may report a conflict (`CommandError`) instead of overwriting them. Fix by deleting those rows in admin.
- **Model validation bypass**: `objects.create()` / `.save()` without `full_clean()` skips item 4 and schedule rules. Only seed code and `schedule/mutations.py` write these models.

---

## Clarifications

- **Q1 (Coder, ruff S104 on `"0.0.0.0"`)**: define the sentinel once in `accounts/throttling.py`:
  ```python
  # Sentinel for "client IP unknown"; not a bind address.
  UNKNOWN_IP = "0.0.0.0"  # noqa: S104
  ```
  `get_client_ip` returns `UNKNOWN_IP` in every fallback case (3.4 steps 1 and 4). Tests import `UNKNOWN_IP` and assert against it — no `"0.0.0.0"` literal elsewhere. No per-file ignores in `pyproject.toml`, and no obfuscated constructions (such as `str(ipaddress.ip_address(0))`) to hide the value from the linter.
