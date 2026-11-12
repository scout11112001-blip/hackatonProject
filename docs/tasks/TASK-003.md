# TASK-003: Schedule (today / week, changes, staff view)

Author: Planner. Status: ready for implementation.
Base commit: `001c455`. Product context: `plan.md`. Previous specs: `docs/tasks/TASK-001.md`, `docs/tasks/TASK-002.md` (reuse its access pattern).

---

## 1. Goal

Students see their schedule for today and for any week: time, discipline, lesson type, teacher, room. Changes (cancelled, moved, room changed, teacher replaced) are clearly marked with old and new values and a reason. Staff see a read-only week schedule of any study group of their own faculty. The schedule renders correctly for **any date** without re-running the seed.

## 2. Acceptance criteria

1. New app `schedule` with `WeeklyLesson` and `LessonChange`; `university` gains `Room`, `Teacher`, `Discipline`. Migrations exist; `makemigrations --check --dry-run` is clean.
2. `/schedule/` (today) and `/schedule/week/[<YYYY-MM-DD>/]` work for students; no user or group ID in student URLs.
3. Today view marks the lesson in progress and the next lesson; shows an empty state on a day without lessons. Tested with a mocked `django.utils.timezone.now`.
4. Every lesson shows time, discipline, type, teacher, room (number, floor); every room element has `data-room-code="<Room.code>"`.
5. Each change kind renders with a status label, old value struck through (`<del>`), new value (`<ins>`) where applicable, and the reason.
6. Staff: group list limited to own faculty; week view of own-faculty group 200; another faculty's group 404; students get 403 on all staff schedule URLs.
7. Overlap of the same group or the same room is rejected by the validation/service layer (not only by admin forms), for weekly lessons and for changes.
8. Schedule pages run a constant number of SQL queries (test proves it does not grow with data).
9. `seed_demo` remains idempotent; it adds rooms on several floors, teachers, disciplines, a full week for both demo groups and 2 changes of each kind in the current and next week relative to the run date. Re-running refreshes the demo changes.
10. All existing verification commands pass; manual check at 360 px.

## 3. Out of scope

Room map pages (only `data-room-code` now; no links to non-existent pages), grades, attendance, notifications, staff editing outside admin, calendar export, visual theme, teacher double-booking validation, odd/even weeks, one-off extra lessons not derived from a weekly lesson, TASK-002 tech-debt items.

---

## 4. Design decisions

### 4.1 Where models live
- `university` (reference data, depends on nothing): add `Room`, `Teacher`, `Discipline`. The map task needs `Room` without the schedule; grades need `Discipline` without the schedule.
- New app `schedule` (depends on `university` and `accounts`): `WeeklyLesson`, `LessonChange`, time slots, schedule computation, validation, views, demo seed for the schedule. It is a separate bounded context with its own services and pages; putting it into `university` would mix reference data with business logic.
- `university` must never import from `schedule` or `accounts`.

### 4.2 Weekly template + dated changes (no generated dated lessons)
- `WeeklyLesson` = a recurring lesson: weekday, slot, discipline, type, teacher, room, one or more groups, active date range `[valid_from, valid_until]` (inclusive).
- `LessonChange` = an explicit change of **one occurrence**, identified by `(weekly_lesson, original_date)`.
- Occurrences are computed on the fly for any requested date range. Therefore the schedule renders for any date without re-seeding (hard constraint). Nothing is stored per date except changes.
- **Occurrence identity** (for attendance later): `(weekly_lesson_id, original_date)`. A moved lesson keeps its identity.
- At most one change per occurrence (DB unique constraint). A combined change (e.g. moved and new teacher) is out of scope.

### 4.3 Time slots are a code constant, not a model
The bell schedule is fixed for the fictional university and never edited by users. A constant needs no migration, data seeding or joins, and makes overlap checks an equality test on `(date, slot)` — partial time overlaps cannot happen. Stored as `slot` number (1–7) on lessons and changes.

### 4.4 Validation layer (TASK-002 review note)
Do not rely on admin forms validating DB constraints for fields they do not include. All business rules live in plain functions in `schedule/validation.py` and are called from:
- `schedule/mutations.py` (`save_weekly_lesson`, `save_lesson_change`) — the only write path for code (seed, tests, later tasks);
- `LessonChange.clean()` (runs in every `full_clean()`, including admin);
- `WeeklyLessonAdminForm.clean()` (needed because `groups` is many-to-many and is not available in `WeeklyLesson.clean()`).
Admin forms for schedule models include every editable model field (explicit list in `WeeklyLessonAdminForm`, because ruff DJ007 forbids `"__all__"`; `LessonChangeAdmin` does not restrict `fields`).

### 4.5 Later tasks (do not implement)
- Map: `Room.code` is a stable, unique, lowercase id valid as an SVG element id; `Room.floor` supports multi-floor maps.
- Grades: reference `university.Discipline`. Attendance: reference occurrence `(weekly_lesson, original_date)`.
- Notifications: `schedule.services.changes_for_groups_between(group_ids, start, end)` answers "schedule changes affecting group X in a date range".

---

## 5. Architecture

### 5.1 Files

Create:
```
schedule/__init__.py
schedule/apps.py
schedule/models.py
schedule/timeslots.py
schedule/services.py
schedule/validation.py
schedule/mutations.py
schedule/converters.py
schedule/forms.py
schedule/admin.py
schedule/views.py
schedule/urls.py
schedule/demo.py
schedule/migrations/__init__.py
schedule/migrations/0001_initial.py                 (generated)
schedule/templates/schedule/today.html
schedule/templates/schedule/week.html
schedule/templates/schedule/staff_group_list.html
schedule/templates/schedule/includes/lesson_item.html
schedule/templates/schedule/includes/week_days.html
schedule/templates/schedule/includes/week_nav.html
schedule/tests/__init__.py
schedule/tests/helpers.py
schedule/tests/test_timeslots.py
schedule/tests/test_services.py
schedule/tests/test_validation.py
schedule/tests/test_views.py
schedule/tests/test_demo.py
university/migrations/0002_<generated name>.py     (generated)
```
Change:
```
university/models.py, university/admin.py, university/tests/test_models.py,
accounts/selectors.py, accounts/tests/test_access.py,
accounts/management/commands/seed_demo.py,
config/settings.py (INSTALLED_APPS only), config/urls.py,
templates/base.html (nav only), static/css/tokens.css, static/css/base.css,
README.md, pyproject.toml
```
Do not change any other file. Do not change `accounts/demo.py`.

### 5.2 Settings / URLs / tooling
- `INSTALLED_APPS`: add `"schedule"` right after `"accounts"`.
- `config/urls.py`: add `path("", include("schedule.urls"))` after the `accounts` include.
- `pyproject.toml`: `known-first-party = ["config", "core", "accounts", "university", "schedule"]`.
- App config class `ScheduleConfig`: `name = "schedule"`, `verbose_name = "Расписание"`, `default_auto_field = "django.db.models.BigAutoField"`.

### 5.3 `university/models.py` additions

**`Room`**
| Field | Definition |
|---|---|
| `code` | `CharField("код", max_length=32, unique=True, validators=[RegexValidator(r"^[a-z][a-z0-9-]*$", "Код: латинские строчные буквы, цифры и дефис; начинается с буквы.")])` |
| `floor` | `PositiveSmallIntegerField("этаж", validators=[MinValueValidator(1), MaxValueValidator(20)])` |
| `number` | `CharField("номер", max_length=10, unique=True)` |
- `Meta`: `ordering = ["floor", "number"]`; `constraints = [CheckConstraint(condition=Q(floor__gte=1) & Q(floor__lte=20), name="university_room_floor_1_20")]`; verbose `"аудитория"` / `"аудитории"`.
- `__str__` → `f"ауд. {self.number}"`.
- No DB regex constraint (SQLite would need an app-defined function); the validator runs in every `full_clean()`, and seed values are fixed.

**`Teacher`** (does not log in; no user link)
| Field | Definition |
|---|---|
| `last_name`, `first_name` | `CharField(max_length=100)` (`"фамилия"`, `"имя"`) |
| `middle_name` | `CharField("отчество", max_length=100, blank=True, default="")` |
| `title` | `CharField("учёная степень, звание", max_length=100, blank=True, default="")` |
- `Meta`: `ordering = ["last_name", "first_name"]`; `constraints = [UniqueConstraint(fields=["last_name", "first_name", "middle_name"], name="university_teacher_unique_name")]`; verbose `"преподаватель"` / `"преподаватели"`.
- Properties: `full_name` (same rule as `StudentProfile.full_name`); `short_name` → `"Лебедев А. С."` = `last_name` + `" "` + `f"{first_name[0]}."` + (`f" {middle_name[0]}."` if `middle_name` else `""`).
- `__str__` → `self.full_name`.

**`Discipline`**
| Field | Definition |
|---|---|
| `name` | `CharField("название", max_length=200, unique=True)` |
| `short_name` | `CharField("краткое название", max_length=50)` |
- `Meta`: `ordering = ["name"]`; verbose `"дисциплина"` / `"дисциплины"`. `__str__` → `self.name`.

`university/admin.py`: register `Room` (`list_display = ("number", "floor", "code")`, `list_filter = ("floor",)`, `search_fields = ("number", "code")`), `Teacher` (`list_display = ("full_name", "title")`, `search_fields = ("last_name", "first_name")`), `Discipline` (`list_display = ("name", "short_name")`, `search_fields = ("name", "short_name")`).

### 5.4 `schedule/timeslots.py`

```python
@dataclass(frozen=True)
class TimeSlot:
    number: int
    start: time
    end: time

TIME_SLOTS: tuple[TimeSlot, ...] = (
    TimeSlot(1, time(9, 0), time(10, 30)),
    TimeSlot(2, time(10, 40), time(12, 10)),
    TimeSlot(3, time(12, 55), time(14, 25)),
    TimeSlot(4, time(14, 35), time(16, 5)),
    TimeSlot(5, time(16, 15), time(17, 45)),
    TimeSlot(6, time(17, 55), time(19, 25)),
    TimeSlot(7, time(19, 35), time(21, 5)),
)
SLOT_CHOICES: list[tuple[int, str]] = [(s.number, f"{s.number} пара ({s.start:%H:%M}–{s.end:%H:%M})") for s in TIME_SLOTS]
MAX_SLOT: int = len(TIME_SLOTS)

def get_slot(number: int) -> TimeSlot
```
- `get_slot`: return the slot with this number; `raise ValueError(f"Unknown slot {number}")` otherwise.
- Tests (`test_timeslots.py`, `SimpleTestCase`): numbers are 1..7 consecutive; each `start < end`; slots do not overlap and are ordered; `get_slot(2).start == time(10, 40)`; `get_slot(0)` and `get_slot(8)` raise `ValueError`.

### 5.5 `schedule/models.py`

```python
class Weekday(models.IntegerChoices):  # matches date.weekday()
    MONDAY = 0, "Понедельник"
    TUESDAY = 1, "Вторник"
    WEDNESDAY = 2, "Среда"
    THURSDAY = 3, "Четверг"
    FRIDAY = 4, "Пятница"
    SATURDAY = 5, "Суббота"
    SUNDAY = 6, "Воскресенье"


class LessonType(models.TextChoices):
    LECTURE = "lecture", "Лекция"
    SEMINAR = "seminar", "Семинар"
    LAB = "lab", "Лабораторная работа"


class ChangeKind(models.TextChoices):
    CANCELLED = "cancelled", "Отмена"
    MOVED = "moved", "Перенос"
    ROOM_CHANGED = "room_changed", "Замена аудитории"
    TEACHER_REPLACED = "teacher_replaced", "Замена преподавателя"
```

**`WeeklyLesson`**
| Field | Definition |
|---|---|
| `weekday` | `PositiveSmallIntegerField("день недели", choices=Weekday.choices)` |
| `slot` | `PositiveSmallIntegerField("пара", choices=SLOT_CHOICES)` |
| `discipline` | `ForeignKey("university.Discipline", on_delete=PROTECT, related_name="weekly_lessons", verbose_name="дисциплина")` |
| `lesson_type` | `CharField("тип занятия", max_length=16, choices=LessonType.choices)` |
| `teacher` | `ForeignKey("university.Teacher", on_delete=PROTECT, related_name="weekly_lessons", verbose_name="преподаватель")` |
| `room` | `ForeignKey("university.Room", on_delete=PROTECT, related_name="weekly_lessons", verbose_name="аудитория")` |
| `groups` | `ManyToManyField("university.StudyGroup", related_name="weekly_lessons", verbose_name="группы")` |
| `valid_from` | `DateField("действует с")` |
| `valid_until` | `DateField("действует по")` (inclusive) |
- `Meta`: `ordering = ["weekday", "slot"]`; `indexes = [Index(fields=["weekday", "slot"], name="schedule_weekly_day_slot_idx")]`; constraints:
  - `CheckConstraint(condition=Q(valid_until__gte=F("valid_from")), name="schedule_weekly_valid_range")`
  - `CheckConstraint(condition=Q(weekday__gte=0) & Q(weekday__lte=6), name="schedule_weekly_weekday_0_6")`
  - `CheckConstraint(condition=Q(slot__gte=1) & Q(slot__lte=MAX_SLOT), name="schedule_weekly_slot_range")`
  - verbose `"занятие (еженедельное)"` / `"занятия (еженедельные)"`.
- `__str__` → `f"{self.get_weekday_display()}, {self.slot} пара — {self.discipline}"`.
- `clean()`: `super().clean()`; if both dates set and `valid_until < valid_from` → `ValidationError({"valid_until": "Дата окончания раньше даты начала."})`. No conflict checks here (groups are M2M; see 4.4).
- Property `time_slot -> TimeSlot` → `get_slot(self.slot)`.

**`LessonChange`**
| Field | Definition |
|---|---|
| `weekly_lesson` | `ForeignKey(WeeklyLesson, on_delete=CASCADE, related_name="changes", verbose_name="занятие")` |
| `original_date` | `DateField("дата занятия по расписанию")` |
| `kind` | `CharField("вид изменения", max_length=20, choices=ChangeKind.choices)` |
| `new_date` | `DateField("новая дата", null=True, blank=True)` |
| `new_slot` | `PositiveSmallIntegerField("новая пара", choices=SLOT_CHOICES, null=True, blank=True)` |
| `new_room` | `ForeignKey("university.Room", on_delete=PROTECT, null=True, blank=True, related_name="+", verbose_name="новая аудитория")` |
| `new_teacher` | `ForeignKey("university.Teacher", on_delete=PROTECT, null=True, blank=True, related_name="+", verbose_name="новый преподаватель")` |
| `reason` | `CharField("причина", max_length=200)` |
| `created_at` | `DateTimeField("создано", auto_now_add=True)` |
- `Meta`: `ordering = ["original_date"]`; `indexes = [Index(fields=["original_date"], name="schedule_change_orig_idx"), Index(fields=["new_date"], name="schedule_change_new_idx")]`; constraints:
  - `UniqueConstraint(fields=["weekly_lesson", "original_date"], name="schedule_change_one_per_occurrence")`
  - `CheckConstraint(condition=~Q(reason=""), name="schedule_change_reason_required")`
  - `CheckConstraint(name="schedule_change_fields_match_kind", condition=` OR of:
    - `Q(kind="cancelled", new_date__isnull=True, new_slot__isnull=True, new_room__isnull=True, new_teacher__isnull=True)`
    - `Q(kind="moved", new_date__isnull=False, new_slot__isnull=False, new_teacher__isnull=True)` (`new_room` optional)
    - `Q(kind="room_changed", new_room__isnull=False, new_date__isnull=True, new_slot__isnull=True, new_teacher__isnull=True)`
    - `Q(kind="teacher_replaced", new_teacher__isnull=False, new_date__isnull=True, new_slot__isnull=True, new_room__isnull=True)` `)`
  - also `CheckConstraint(condition=Q(new_slot__isnull=True) | (Q(new_slot__gte=1) & Q(new_slot__lte=MAX_SLOT)), name="schedule_change_new_slot_range")`
  - verbose `"изменение расписания"` / `"изменения расписания"`.
- `__str__` → `f"{self.get_kind_display()}: {self.weekly_lesson} ({self.original_date:%d.%m.%Y})"`.
- `clean()` — see 6.3.

### 5.6 `accounts/selectors.py` addition

```python
def groups_visible_to(user: AbstractBaseUser | AnonymousUser) -> QuerySet[StudyGroup]
```
- Purpose: every study-group lookup from a request starts here (same pattern as `students_visible_to`).
- Algorithm:
  1. `qs = StudyGroup.objects.select_related("program__faculty")`.
  2. Not authenticated / not active → `qs.none()`.
  3. STAFF: staff profile (missing → `qs.none()`) → `qs.filter(program__faculty=profile.faculty)`.
  4. STUDENT: student profile (missing → `qs.none()`) → `qs.filter(pk=profile.group_id)`.
  5. Else → `qs.none()`.
- Tests (add to `accounts/tests/test_access.py`): staff X sees only faculty X groups; student sees only own group; superuser, anonymous, staff without profile → empty.

### 5.7 URLs (`schedule/urls.py`, `app_name = "schedule"`)

`register_converter(IsoDateConverter, "isodate")`.

| Path | View | Name |
|---|---|---|
| `schedule/` | `TodayView` | `today` |
| `schedule/week/` | `StudentWeekView` | `week` |
| `schedule/week/<isodate:day>/` | `StudentWeekView` | `week_of` |
| `staff/schedule/` | `StaffGroupListView` | `staff_groups` |
| `staff/schedule/<int:group_id>/` | `StaffGroupWeekView` | `staff_group_week` |
| `staff/schedule/<int:group_id>/<isodate:day>/` | `StaffGroupWeekView` | `staff_group_week_of` |

`schedule/converters.py`:
```python
class IsoDateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"
    def to_python(self, value: str) -> date
    def to_url(self, value: date) -> str
```
- `to_python`: `day = date.fromisoformat(value)` (invalid → `ValueError`); if not `date(2000, 1, 1) <= day <= date(2100, 12, 31)` → `raise ValueError`. Django turns `ValueError` into "no match" → 404. The range keeps `±7 days` arithmetic far from `date.min/max`.
- `to_url`: `value.isoformat()`.
- Tests: `"2026-11-16"` → `date(2026, 11, 16)`; `"2026-02-30"` and `"1999-12-31"` → `ValueError`; `to_url(date(2026, 11, 16)) == "2026-11-16"`.

### 5.8 Navigation (`templates/base.html`)
Inside the existing `<ul class="site-nav-list">`, after the "Профиль" item:
```html
{% if user.is_student %}
<li><a href="{% url 'schedule:today' %}">Расписание</a></li>
{% elif user.is_deanery_staff %}
<li><a href="{% url 'schedule:staff_groups' %}">Расписание</a></li>
{% endif %}
```

---

## 6. Functions

### 6.1 `schedule/services.py` — read side

```python
class ItemKind(StrEnum):
    REGULAR = "regular"
    CANCELLED = "cancelled"
    MOVED_OUT = "moved-out"      # shown on the original date: the lesson is not here
    MOVED_IN = "moved-in"        # shown on the new date
    ROOM_CHANGED = "room-changed"
    TEACHER_REPLACED = "teacher-replaced"

@dataclass(frozen=True, eq=False)
class ScheduleItem:
    kind: ItemKind
    date: date                    # date on which this item is displayed
    slot: TimeSlot                # displayed slot
    lesson: WeeklyLesson
    original_date: date           # occurrence identity together with lesson.id
    room: Room                    # effective room
    teacher: Teacher              # effective teacher
    original_room: Room | None    # set when the effective room differs from lesson.room
    original_teacher: Teacher | None
    change: LessonChange | None
    moved_to_date: date | None    # MOVED_OUT only
    moved_to_slot: TimeSlot | None
    moved_from_date: date | None  # MOVED_IN only
    moved_from_slot: TimeSlot | None

    @property is_happening -> bool: kind not in (CANCELLED, MOVED_OUT)
    @property is_changed -> bool:   kind != REGULAR

@dataclass(frozen=True)
class DaySchedule:
    date: date
    items: list[ScheduleItem]
    is_today: bool

@dataclass(frozen=True)
class WeekSchedule:
    start: date                   # Monday
    end: date                     # Sunday
    days: list[DaySchedule]       # exactly 7, Monday..Sunday

@dataclass(frozen=True)
class TodayRow:
    item: ScheduleItem
    is_in_progress: bool
    is_next: bool

@dataclass(frozen=True)
class TodayAnnotation:
    rows: list[TodayRow]
    in_progress: ScheduleItem | None
    next_item: ScheduleItem | None
    day_finished: bool            # there were happening lessons and all have ended
```
`eq=False` on `ScheduleItem`: identity comparison only (model instances inside).

#### `week_start(day: date) -> date`
Return `day - timedelta(days=day.weekday())` (Monday). Tests: Monday → same; Sunday 2026-11-22 → 2026-11-16; Wednesday → Monday.

#### `changes_for_groups_between(group_ids: Collection[int] | None, start: date, end: date) -> QuerySet[LessonChange]`
- Purpose: all changes affecting the groups in `[start, end]` (inclusive). Reused by notifications later.
- Algorithm:
  1. `qs = LessonChange.objects.filter(Q(original_date__range=(start, end)) | Q(kind=ChangeKind.MOVED, new_date__range=(start, end)))`.
  2. If `group_ids is not None`: `qs = qs.filter(weekly_lesson__groups__in=group_ids).distinct()`.
  3. `return qs.select_related("weekly_lesson__discipline", "weekly_lesson__teacher", "weekly_lesson__room", "new_room", "new_teacher").prefetch_related("weekly_lesson__groups")`.
- Tests: includes a change with `original_date` in range; includes a MOVED change whose `new_date` is in range and `original_date` is not; excludes changes of other groups; `None` returns all groups.

#### `occurrences_between(start: date, end: date, group_ids: Collection[int] | None) -> list[ScheduleItem]`
- Purpose: the single computation of what happens in `[start, end]` for the groups (`None` = all groups; used by validation).
- Raises: `ValueError` if `start > end`.
- Algorithm:
  1. If `group_ids is not None and not group_ids` → return `[]`.
  2. `lessons_qs = WeeklyLesson.objects.filter(valid_from__lte=end, valid_until__gte=start)`; if `group_ids is not None`: `.filter(groups__in=group_ids).distinct()`; then `.select_related("discipline", "teacher", "room").prefetch_related("groups")`. Evaluate to a list.
  3. `changes = list(changes_for_groups_between(group_ids, start, end))`; `by_key = {(c.weekly_lesson_id, c.original_date): c for c in changes}`.
  4. For each day `d` from `start` to `end`, for each lesson with `lesson.weekday == d.weekday()` and `lesson.valid_from <= d <= lesson.valid_until`: `change = by_key.get((lesson.id, d))` and build an item with `date=d`, `original_date=d`, `slot=lesson.time_slot`:
     - no change → `REGULAR`, `room=lesson.room`, `teacher=lesson.teacher`;
     - `CANCELLED` → `CANCELLED`, room/teacher from lesson;
     - `MOVED` → `MOVED_OUT`, room/teacher from lesson, `moved_to_date=change.new_date`, `moved_to_slot=get_slot(change.new_slot)`;
     - `ROOM_CHANGED` → `ROOM_CHANGED`, `room=change.new_room`, `original_room=lesson.room`;
     - `TEACHER_REPLACED` → `TEACHER_REPLACED`, `teacher=change.new_teacher`, `original_teacher=lesson.teacher`.
  5. For each change with `kind == MOVED` and `start <= change.new_date <= end`: `lesson = change.weekly_lesson`; item `MOVED_IN` with `date=change.new_date`, `slot=get_slot(change.new_slot)`, `original_date=change.original_date`, `room=change.new_room or lesson.room`, `original_room=lesson.room if change.new_room and change.new_room_id != lesson.room_id else None`, `teacher=lesson.teacher`, `moved_from_date=change.original_date`, `moved_from_slot=lesson.time_slot`.
  6. Sort by `(item.date, item.slot.number, item.is_happening is False, item.lesson.discipline.name)` — at the same slot, happening items come first.
- Query budget: at most 4 queries (lessons, lessons' groups, changes, changes' lessons' groups; prefetch queries are skipped when a list is empty), independent of data size.
- Edge cases: lesson whose range starts/ends inside `[start, end]` — only days inside the range; MOVED change whose original occurrence is outside `[start, end]` still yields `MOVED_IN` inside; the same lesson moved within one day yields both `MOVED_OUT` and `MOVED_IN` on that day.

#### `day_schedule(day: date, group_ids: Collection[int], today: date) -> DaySchedule`
`items = occurrences_between(day, day, group_ids)`; return `DaySchedule(date=day, items=items, is_today=(day == today))`.

#### `week_schedule(any_day: date, group_ids: Collection[int], today: date) -> WeekSchedule`
1. `start = week_start(any_day)`, `end = start + timedelta(days=6)`.
2. `items = occurrences_between(start, end, group_ids)` (one call).
3. Group items by `item.date` into 7 `DaySchedule`s (Monday..Sunday; empty lists for empty days; `is_today = d == today`).

#### `annotate_today(items: list[ScheduleItem], now: time) -> TodayAnnotation`
- Pure function (no DB, no clock).
- Algorithm:
  1. `happening = [i for i in items if i.is_happening]`.
  2. `in_progress` = first `i` in `happening` with `i.slot.start <= now < i.slot.end`, else `None`.
  3. `next_item` = first `i` in `happening` with `i.slot.start > now`, else `None`.
  4. `day_finished = bool(happening) and all(i.slot.end <= now for i in happening)`.
  5. `rows = [TodayRow(item=i, is_in_progress=i is in_progress, is_next=i is next_item) for i in items]`.
- Tests (build `ScheduleItem`s via `occurrences_between` on test data or construct directly with unsaved model instances):
  - before first lesson (08:00): `in_progress None`, `next` = slot 1 item;
  - during slot 2 (10:50): `in_progress` = slot 2, `next` = slot 3;
  - in a break (12:30, between slots 2 and 3): `in_progress None`, `next` = slot 3;
  - exactly at end of slot 2 (12:10): slot 2 not in progress;
  - after last lesson: both `None`, `day_finished True`;
  - cancelled slot 3 is skipped: `next` = slot 4;
  - empty list: all `None`, `day_finished False`.

### 6.2 `schedule/validation.py`

#### `validate_weekly_lesson(*, weekday: int, slot: int, valid_from: date, valid_until: date, room_id: int, group_ids: Collection[int], exclude_pk: int | None) -> list[str]`
- Purpose: business rules for a weekly lesson that need other rows or M2M data. Returns Russian error messages (empty list = valid).
- Algorithm:
  1. `errors = []`. If not `group_ids` → append `"Выберите хотя бы одну группу."`.
  2. `others = WeeklyLesson.objects.filter(weekday=weekday, slot=slot, valid_from__lte=valid_until, valid_until__gte=valid_from)`; if `exclude_pk`: `.exclude(pk=exclude_pk)`.
  3. For each `o` in `others.filter(room_id=room_id).select_related("discipline", "room")`: append `f"Аудитория {o.room.number} уже занята в это время: {o.discipline.name}."`.
  4. For each `o` in `others.filter(groups__in=group_ids).distinct().select_related("discipline").prefetch_related("groups")`: for each group of `o` whose id is in `group_ids`: append `f"Группа {g.name} уже занята в это время: {o.discipline.name}."`.
  5. If `exclude_pk`: for each `LessonChange` of that lesson where `original_date.weekday() != weekday` or not `valid_from <= original_date <= valid_until`: append `f"Есть изменение на {c.original_date:%d.%m.%Y}, которое не подходит к новому расписанию. Сначала удалите его."`.
  6. Return `errors`.
- Overlap means: same weekday and slot and overlapping date ranges (inclusive). Changes are ignored here (a template conflict is a conflict).

#### `change_conflicts(change: LessonChange) -> list[str]`
- Purpose: group/room conflicts of the target occurrence of a MOVED or ROOM_CHANGED change.
- Precondition: `change.weekly_lesson` is saved; kind-specific fields are valid.
- Algorithm:
  1. If `change.kind` in (`CANCELLED`, `TEACHER_REPLACED`) → `[]`.
  2. `lesson = change.weekly_lesson`. Target: MOVED → `(change.new_date, change.new_slot)`; ROOM_CHANGED → `(change.original_date, lesson.slot)`.
  3. `target_room_id = change.new_room_id or lesson.room_id`; `group_ids = set(lesson.groups.values_list("id", flat=True))`.
  4. `items = occurrences_between(target_date, target_date, None)`.
  5. For each `item` with `item.is_happening` and `item.slot.number == target_slot`, skipping the same occurrence (`item.lesson.id == lesson.id and item.original_date == change.original_date`):
     - if `item.room.id == target_room_id` → `f"Аудитория {item.room.number} занята: {item.lesson.discipline.name}, {target_date:%d.%m.%Y}, {target_slot} пара."`;
     - for each group of `item.lesson.groups.all()` with id in `group_ids` → `f"Группа {g.name} занята: {item.lesson.discipline.name}, {target_date:%d.%m.%Y}, {target_slot} пара."`.
  6. Return the list.
- Effect: a slot freed by a cancellation or a move-out is free; editing an existing change does not conflict with itself.

### 6.3 `LessonChange.clean()`
1. `super().clean()`. If `weekly_lesson_id` is `None` or `original_date` is `None` or `kind` is empty → return (field errors are reported by Django).
2. `lesson = self.weekly_lesson`; `errors: dict[str, list[str]] = {}`.
3. `original_date.weekday() != lesson.weekday` → `errors["original_date"]` += `"Дата не совпадает с днём недели занятия."`; outside `[lesson.valid_from, lesson.valid_until]` → `"Дата вне периода действия занятия."`.
4. Kind rules (mirror of the DB constraint, field-level messages):
   - required: MOVED → `new_date`, `new_slot` (`"Обязательно для переноса."`); ROOM_CHANGED → `new_room`; TEACHER_REPLACED → `new_teacher` (`"Обязательно для этого вида изменения."`);
   - forbidden (must be empty, `"Не заполняйте для этого вида изменения."`): every `new_*` field not allowed by the constraint in 5.5.
5. Value rules: MOVED with `(new_date, new_slot) == (original_date, lesson.slot)` and (`new_room` empty or equal to `lesson.room`) → `errors["new_date"]` `"Новое время совпадает со старым."`; ROOM_CHANGED with `new_room_id == lesson.room_id` → `errors["new_room"]` `"Аудитория не изменилась."`; TEACHER_REPLACED with `new_teacher_id == lesson.teacher_id` → `errors["new_teacher"]` `"Преподаватель не изменился."`.
6. If `errors` → `raise ValidationError(errors)`.
7. `conflicts = change_conflicts(self)` (import inside the method to avoid a circular import); if any → `raise ValidationError(conflicts)`.

### 6.4 `schedule/mutations.py` — the only write path in code

#### `save_weekly_lesson(lesson: WeeklyLesson, groups: Sequence[StudyGroup]) -> WeeklyLesson`
1. `with transaction.atomic():`
2. `lesson.full_clean()` (M2M is ignored by Django here).
3. `errors = validate_weekly_lesson(weekday=lesson.weekday, slot=lesson.slot, valid_from=lesson.valid_from, valid_until=lesson.valid_until, room_id=lesson.room_id, group_ids=[g.pk for g in groups], exclude_pk=lesson.pk)`; if `errors` → `raise ValidationError(errors)`.
4. `lesson.save()`; `lesson.groups.set(groups)`; return `lesson`.

#### `save_lesson_change(change: LessonChange) -> LessonChange`
`with transaction.atomic(): change.full_clean(); change.save(); return change`.

Tests (`test_validation.py`, `TestCase`):
- `test_group_overlap_rejected` — second lesson, same group/weekday/slot, overlapping ranges, other room → `ValidationError` mentioning the group name.
- `test_room_overlap_rejected` — different groups, same room/weekday/slot → error mentioning the room number.
- `test_partial_group_overlap_rejected` — `[A, B]` vs `[B, C]` → error for `B` only.
- `test_non_overlapping_ranges_allowed` — same group/slot, ranges `[Sep 1, Oct 31]` and `[Nov 1, Dec 31]` → OK.
- `test_adjacent_inclusive_range_conflicts` — ranges sharing one day (`... Oct 31` and `Oct 31 ...`) → error.
- `test_editing_lesson_does_not_conflict_with_itself`.
- `test_empty_groups_rejected`.
- `test_weekday_edit_with_existing_change_rejected`.
- `test_invalid_range_rejected` — `valid_until < valid_from` → `ValidationError`.
- `test_admin_form_rejects_group_overlap` — `WeeklyLessonAdminForm(data=...)` → `is_valid() is False`, error in `non_field_errors()`.
- Change rules, each via `save_lesson_change` → `ValidationError` with the field key: weekday mismatch; date out of range; MOVED without `new_date`; CANCELLED with `new_room`; ROOM_CHANGED same room; TEACHER_REPLACED same teacher; blank reason.
- `test_move_into_busy_group_slot_rejected`; `test_move_into_slot_freed_by_cancellation_allowed`; `test_room_change_into_busy_room_rejected`; `test_room_change_into_room_freed_by_move_allowed`; `test_editing_existing_change_no_self_conflict`.
- DB level: `LessonChange.objects.create(kind="cancelled", new_room=room, ...)` → `IntegrityError`; second change for the same `(weekly_lesson, original_date)` → `IntegrityError`; `reason=""` → `IntegrityError` (each in `transaction.atomic()`).

### 6.5 `schedule/forms.py` and `schedule/admin.py`

```python
class WeeklyLessonAdminForm(forms.ModelForm):
    class Meta:
        model = WeeklyLesson
        fields = ["weekday", "slot", "discipline", "lesson_type", "teacher", "room", "groups", "valid_from", "valid_until"]
    def clean(self) -> dict[str, Any]
```
- `clean()`: `cleaned = super().clean()`; if any of `weekday, slot, valid_from, valid_until, room, groups` is missing from `cleaned` → return `cleaned` (field errors already exist); `errors = validate_weekly_lesson(..., room_id=cleaned["room"].pk, group_ids=[g.pk for g in cleaned["groups"]], exclude_pk=self.instance.pk)`; `for msg in errors: self.add_error(None, msg)`; return `cleaned`.

`schedule/admin.py`:
- `WeeklyLessonAdmin`: `form = WeeklyLessonAdminForm`; `list_display = ("weekday", "slot", "discipline", "lesson_type", "teacher", "room", "group_names", "valid_from", "valid_until")` where `group_names` is an admin method (`", ".join(g.name for g in obj.groups.all())`, `@admin.display(description="группы")`); `list_filter = ("weekday", "lesson_type", "groups")`; `filter_horizontal = ("groups",)`; `list_select_related = ("discipline", "teacher", "room")`; `get_queryset` adds `.prefetch_related("groups")`.
- `LessonChangeAdmin`: `fields` not restricted (all fields); `list_display = ("original_date", "kind", "weekly_lesson", "new_date", "new_slot", "new_room", "new_teacher", "reason")`; `list_filter = ("kind",)`; `date_hierarchy = "original_date"`; `list_select_related = ("weekly_lesson__discipline", "new_room", "new_teacher")`. Validation comes from `LessonChange.clean()`.

### 6.6 `schedule/views.py`

All views: login required by middleware. Never use a group/user ID from the student's request.

```python
class TodayView(StudentRequiredMixin, TemplateView):
    template_name = "schedule/today.html"
```
`get_context_data`: `now = timezone.localtime()`; `day = day_schedule(now.date(), [self.profile.group_id], today=now.date())`; `annotation = annotate_today(day.items, now.time())`; context: `day`, `annotation`, `group = self.profile.group`, `week_url = reverse("schedule:week")`.

```python
class StudentWeekView(StudentRequiredMixin, TemplateView):
    template_name = "schedule/week.html"
```
`get_context_data`: `today = timezone.localdate()`; `day = self.kwargs.get("day") or today`; `week = week_schedule(day, [self.profile.group_id], today)`; context = `_week_context(week, today, "schedule:week_of", {})` + `group`, `title = "Моё расписание"`.

```python
class StaffGroupListView(StaffRequiredMixin, ListView):
    template_name = "schedule/staff_group_list.html"
    context_object_name = "groups"

    def get_queryset(self) -> QuerySet[StudyGroup]:
        return groups_visible_to(self.request.user)
```

```python
class StaffGroupWeekView(StaffRequiredMixin, TemplateView):
    template_name = "schedule/week.html"
```
`get_context_data`: `group = get_object_or_404(groups_visible_to(self.request.user), pk=self.kwargs["group_id"])`; `today = timezone.localdate()`; `day = self.kwargs.get("day") or today`; `week = week_schedule(day, [group.pk], today)`; context = `_week_context(week, today, "schedule:staff_group_week_of", {"group_id": group.pk})` + `group`, `title = f"Расписание группы {group.name}"`, `back_url = reverse("schedule:staff_groups")`.

```python
def _week_context(week: WeekSchedule, today: date, url_name: str, url_kwargs: dict[str, Any]) -> dict[str, Any]
```
Returns `{"week": week, "prev_url": reverse(url_name, kwargs={**url_kwargs, "day": week.start - timedelta(days=7)}), "next_url": ... + 7 days, "current_url": reverse(url_name, kwargs={**url_kwargs, "day": today}), "is_current_week": week.start == week_start(today)}`.

### 6.7 Templates

All extend `base.html`; Russian text; no inline styles; no external URLs; dates via Django filters (`date:"l, j E"` → «понедельник, 16 ноября»).

`includes/lesson_item.html` (expects `item`, optional `row`):
```html
<li class="lesson lesson--{{ item.kind }}{% if row.is_in_progress %} lesson--now{% endif %}{% if row.is_next %} lesson--next{% endif %}">
  <p class="lesson-time">
    {% if row.is_in_progress %}<strong class="lesson-badge">Сейчас</strong>{% endif %}
    {% if row.is_next %}<strong class="lesson-badge">Следующая</strong>{% endif %}
    <time>{{ item.slot.start|time:"H:i" }}</time>–<time>{{ item.slot.end|time:"H:i" }}</time> · {{ item.slot.number }} пара
  </p>
  <p class="lesson-title">{{ item.lesson.discipline.name }} <span class="lesson-type">{{ item.lesson.get_lesson_type_display }}</span></p>
  <p class="lesson-teacher">Преподаватель:
    {% if item.original_teacher %}<del>{{ item.original_teacher.short_name }}</del> <ins>{{ item.teacher.short_name }}</ins>{% else %}{{ item.teacher.short_name }}{% endif %}
  </p>
  <p class="lesson-room">Аудитория:
    {% if item.original_room %}<del class="room" data-room-code="{{ item.original_room.code }}">{{ item.original_room.number }}, {{ item.original_room.floor }} этаж</del>
    <ins class="room" data-room-code="{{ item.room.code }}">{{ item.room.number }}, {{ item.room.floor }} этаж</ins>
    {% else %}<span class="room" data-room-code="{{ item.room.code }}">{{ item.room.number }}, {{ item.room.floor }} этаж</span>{% endif %}
  </p>
  {% if item.lesson.groups.all|length > 1 %}<p class="lesson-groups">Группы: {% for g in item.lesson.groups.all %}{{ g.name }}{% if not forloop.last %}, {% endif %}{% endfor %}</p>{% endif %}
  {% if item.is_changed %}
  <p class="lesson-change">
    {% if item.kind == "cancelled" %}Отменено
    {% elif item.kind == "moved-out" %}Перенесено на {{ item.moved_to_date|date:"j E" }}, {{ item.moved_to_slot.number }} пара ({{ item.moved_to_slot.start|time:"H:i" }})
    {% elif item.kind == "moved-in" %}Перенесено с {{ item.moved_from_date|date:"j E" }}, {{ item.moved_from_slot.number }} пара
    {% elif item.kind == "room-changed" %}Замена аудитории
    {% elif item.kind == "teacher-replaced" %}Замена преподавателя{% endif %}.
    Причина: {{ item.change.reason }}
  </p>
  {% endif %}
</li>
```
For `CANCELLED` and `MOVED_OUT`, `base.css` strikes through `.lesson-title` (see 6.8).

`today.html`: `<h1>Сегодня</h1>`, `<p>{{ day.date|date:"l, j E" }} · группа {{ group.name }}</p>`; if no items → `<p>Сегодня занятий нет.</p>`; else if `annotation.day_finished` → `<p>Занятия на сегодня закончились.</p>` (still list items); `<ol class="lesson-list">` of `lesson_item` with `row` from `annotation.rows` (`{% include ... with item=row.item row=row %}`); link `<a href="{{ week_url }}">Расписание на неделю</a>`.

`week.html`: `<h1>{{ title }}</h1>`; for staff: `<p>{{ group.program }}, {{ group.course }} курс</p>` and back link; `{% include "schedule/includes/week_nav.html" %}`; `{% include "schedule/includes/week_days.html" %}`.

`includes/week_nav.html`: `<nav class="week-nav" aria-label="Недели">` with «← Предыдущая» (`prev_url`), «Текущая» (`current_url`, only if not `is_current_week`), «Следующая →» (`next_url`); heading `<p>{{ week.start|date:"j E" }} — {{ week.end|date:"j E Y" }}</p>`.

`includes/week_days.html`: for each `day` in `week.days`: `<section class="day{% if day.is_today %} day--today{% endif %}">`, `<h2>{{ day.date|date:"l, j E" }}{% if day.is_today %} (сегодня){% endif %}</h2>`, items as `<ol class="lesson-list">` of `lesson_item` (no `row`), or `<p>Занятий нет.</p>`.

`staff_group_list.html`: `<h1>Расписание групп</h1>`; `<ul>` of groups: link to `schedule:staff_group_week` with `group.name`, then `· {{ group.program.name }}, {{ group.course }} курс`; `{% empty %}<li>Групп нет.</li>`.

### 6.8 CSS
`static/css/tokens.css` — add to `:root`: `--color-changed: #a35200;`, `--color-now-bg: #eaf2ff;`.
`static/css/base.css` — append (tokens only, one declaration per line):
```css
.lesson-list { list-style: none; margin: 0; padding: 0; }
.lesson { border-top: 1px solid var(--color-border); padding: var(--space-2) 0; }
.lesson p { margin: 0; }
.lesson--now { background: var(--color-now-bg); }
.lesson-badge { margin-right: var(--space-2); }
.lesson-type, .lesson-groups { color: var(--color-muted); }
.lesson-change { color: var(--color-changed); }
.lesson--cancelled .lesson-title, .lesson--moved-out .lesson-title { text-decoration: line-through; }
.week-nav { display: flex; flex-wrap: wrap; gap: var(--space-3); }
.day { margin-top: var(--space-4); }
```

### 6.9 Demo data (`schedule/demo.py`)

```python
@dataclass(frozen=True)
class ScheduleSeedSummary:
    rooms: int
    teachers: int
    disciplines: int
    weekly_lessons: int
    changes: int

def seed_schedule_demo(today: date) -> ScheduleSeedSummary
```
Data (fictional; define as tuples of frozen dataclasses, like `accounts/demo.py`):

Rooms (single building): `room-101` (1, "101"), `room-114` (1, "114"), `room-205` (2, "205"), `room-212` (2, "212"), `room-308` (3, "308"), `room-315` (3, "315"), `room-402` (4, "402") — format `(code, floor, number)`.

Teachers `(last, first, middle, title)`: Лебедев Аркадий Семёнович «профессор»; Воронцова Ирина Олеговна «доцент»; Глебов Тимур Русланович «старший преподаватель»; Назарова Вера Ильинична «доцент»; Фомин Павел Андреевич «» (empty); Шестакова Лидия Петровна «ассистент».

Disciplines `(name, short_name)`: «Введение в цифровую дипломатию» / «Цифр. дипломатия»; «Английский язык» / «Англ. яз.»; «Теория международных отношений» / «ТМО»; «Анализ данных на Python» / «Анализ данных»; «Микроэкономика» / «Микроэк.»; «Философия» / «Философия».

Weekly lessons (weekday 0 = Monday; key = (discipline, type, weekday, slot) is unique):
| # | weekday | slot | discipline | type | teacher | room | groups |
|---|---|---|---|---|---|---|---|
| 1 | 0 | 1 | Введение в цифровую дипломатию | lecture | Лебедев | room-101 | ЦД-101 |
| 2 | 0 | 2 | Английский язык | seminar | Назарова | room-308 | ЦД-101 |
| 3 | 0 | 2 | Микроэкономика | lecture | Воронцова | room-114 | ЭД-201 |
| 4 | 0 | 3 | Анализ данных на Python | lab | Глебов | room-205 | ЭД-201 |
| 5 | 1 | 1 | Английский язык | seminar | Назарова | room-315 | ЭД-201 |
| 6 | 1 | 2 | Теория международных отношений | lecture | Лебедев | room-101 | ЦД-101 |
| 7 | 1 | 2 | Микроэкономика | seminar | Воронцова | room-402 | ЭД-201 |
| 8 | 1 | 3 | Анализ данных на Python | lab | Глебов | room-205 | ЦД-101 |
| 9 | 2 | 1 | Философия | lecture | Фомин | room-101 | ЦД-101, ЭД-201 |
| 10 | 2 | 2 | Введение в цифровую дипломатию | seminar | Лебедев | room-212 | ЦД-101 |
| 11 | 2 | 3 | Микроэкономика | seminar | Воронцова | room-402 | ЭД-201 |
| 12 | 3 | 2 | Анализ данных на Python | lab | Глебов | room-205 | ЭД-201 |
| 13 | 3 | 3 | Английский язык | seminar | Назарова | room-308 | ЦД-101 |
| 14 | 3 | 4 | Теория международных отношений | seminar | Лебедев | room-212 | ЦД-101 |
| 15 | 3 | 4 | Английский язык | seminar | Назарова | room-315 | ЭД-201 |
| 16 | 4 | 1 | Микроэкономика | lecture | Воронцова | room-114 | ЭД-201 |
| 17 | 4 | 2 | Анализ данных на Python | lab | Глебов | room-205 | ЦД-101 |
| 18 | 4 | 3 | Философия | seminar | Фомин | room-212 | ЭД-201 |

All 18 keys are unique; the table has no group, room or slot conflicts (checked by `test_seeded_schedule_has_no_conflicts`).

Validity for every lesson (relative to the run date, so the schedule always covers the jury period):
`monday = week_start(today)`; `valid_from = monday - timedelta(weeks=8)`; `valid_until = monday + timedelta(weeks=12) - timedelta(days=1)`.

Changes (`week` 0 = current week, 1 = next week; `original_date = monday + 7*week + lesson.weekday`):
| # | lesson # | week | kind | new values | reason |
|---|---|---|---|---|---|
| 1 | 1 | 0 | cancelled | — | Преподаватель на конференции |
| 2 | 16 | 1 | cancelled | — | Мероприятие факультета |
| 3 | 8 | 0 | moved | `new_date = monday + 3 days` (Thu, week 0), `new_slot = 5` | Перенос по просьбе преподавателя |
| 4 | 18 | 0 | moved | `new_date = monday + 7 days` (Mon, week 1), `new_slot = 4` | Перенос из-за олимпиады |
| 5 | 13 | 0 | room_changed | `new_room = room-402` | Ремонт в аудитории 308 |
| 6 | 7 | 1 | room_changed | `new_room = room-114` | Аудитория занята мероприятием |
| 7 | 10 | 0 | teacher_replaced | `new_teacher = Шестакова` | Болезнь преподавателя |
| 8 | 12 | 1 | teacher_replaced | `new_teacher = Шестакова` | Командировка преподавателя |

Algorithm (`seed_schedule_demo`, inside `transaction.atomic()`):
1. Rooms: `Room.objects.update_or_create(code=..., defaults={"floor": ..., "number": ...})`.
2. Teachers: `update_or_create(last_name=..., first_name=..., middle_name=..., defaults={"title": ...})`.
3. Disciplines: `update_or_create(name=..., defaults={"short_name": ...})`.
4. Groups: `StudyGroup.objects.get(name=...)` for `ЦД-101`, `ЭД-201` (created by `accounts.demo` earlier in the same command).
5. Find existing demo lessons: for each seed row, `WeeklyLesson.objects.filter(discipline=..., lesson_type=..., weekday=..., slot=...).first()`.
6. Delete all `LessonChange` rows of the existing demo lessons (refresh; documented in README).
7. For each seed row: take the existing lesson or a new `WeeklyLesson`; set all fields (teacher, room, validity); `save_weekly_lesson(lesson, groups)`.
8. For each change row: build `LessonChange(...)`; `save_lesson_change(change)`.
9. Return counts of seed rows.
- If `save_*` raises `ValidationError` (e.g. admin data collides with demo data), let it propagate; the command converts it to `CommandError` (6.10).

### 6.10 `seed_demo` command change
```python
def handle(self, *args, **options):
    password = ... (unchanged check)
    try:
        with transaction.atomic():
            summary = seed_demo_data(password)
            schedule_summary = seed_schedule_demo(timezone.localdate())
    except DemoSeedError as exc:
        raise CommandError(str(exc)) from None
    except ValidationError as exc:
        raise CommandError("Schedule demo data conflicts with existing data: " + " ".join(exc.messages)) from None
    self.stdout.write(<existing message>)
    self.stdout.write(self.style.SUCCESS(f"Schedule ready: {s.rooms} rooms, {s.teachers} teachers, {s.disciplines} disciplines, {s.weekly_lessons} weekly lessons, {s.changes} changes."))
```

### 6.11 README
- "Demo data": add one sentence: "The demo schedule covers 8 weeks before and 12 weeks after the run date. Re-running `seed_demo` replaces the demo schedule changes with fresh ones for the current and next week."
- New short section "Schedule": student pages `/schedule/`, `/schedule/week/`; staff `/staff/schedule/`; admin for editing.

---

## 7. Tests (complete list)

`schedule/tests/helpers.py` (plain functions): `make_room(code: str, floor: int = 1) -> Room` (number = code without `room-`), `make_teacher(last_name: str) -> Teacher`, `make_discipline(name: str) -> Discipline`, `make_lesson(groups: Sequence[StudyGroup], weekday: int, slot: int, room: Room, *, discipline: Discipline | None = None, teacher: Teacher | None = None, lesson_type: str = "lecture", valid_from: date = date(2026, 9, 1), valid_until: date = date(2026, 12, 31)) -> WeeklyLesson` (uses `save_weekly_lesson`; creates a default discipline/teacher if `None`), `aware(dt_str: str) -> datetime` (e.g. `"2026-11-16 10:50"` → aware datetime in `Europe/Moscow`). Reuse `accounts/tests/helpers.py` for faculties, groups, students, staff.

Reference week in tests: Monday **2026-11-16** … Sunday **2026-11-22**. Mock the clock with `mock.patch("django.utils.timezone.now", return_value=aware(...))`. No time-freezing library.

`test_services.py` (`TestCase`): tests listed in 6.1, plus:
- `test_weekday_and_validity_bounds` — no item before `valid_from` / after `valid_until`; items on both boundary days.
- `test_shared_lecture_visible_to_both_groups`.
- `test_group_isolation` — group A items never contain a lesson without A.
- `test_cancelled_item`, `test_room_changed_item`, `test_teacher_replaced_item` (kinds, effective and original values).
- `test_move_within_week` — out on Tue, in on Thu of the same week; `week_schedule` contains both.
- `test_move_across_week` — original in week 1, new date in week 2: week 1 has only `MOVED_OUT`, week 2 has only `MOVED_IN`; `day_schedule(new_date)` has `MOVED_IN`.
- `test_move_within_same_day` — both `MOVED_OUT` and `MOVED_IN` on that day, ordered by slot.
- `test_move_with_new_room` — `MOVED_IN.room == new_room`, `original_room == lesson.room`.
- `test_week_has_seven_days_and_today_flag`.
- `test_query_count_constant` — `CaptureQueriesContext` around `week_schedule` with 1 lesson + 1 change; then add 10 lessons (different slots/days) and 5 changes; second count equals the first and is `<= 4`.

`test_validation.py`: list in 6.4.

`test_views.py` (`TestCase`; fixture: faculties X, Y; groups GX1, GX2 (X), GY (Y); student A in GX1, student B in GY; staff SX (X), SY (Y); lessons with unique discipline names per group, one shared lecture GX1+GY):
1. `test_anonymous_redirected` — all 6 URLs → 302 to `/login/?next=`.
2. `test_student_urls_have_no_ids` — `reverse("schedule:today") == "/schedule/"`, `reverse("schedule:week") == "/schedule/week/"`.
3. `test_today_in_progress_and_next` — now `2026-11-16 10:50`; A has lessons at slots 1, 2, 3 on Monday; response context `annotation.in_progress.slot.number == 2`, `annotation.next_item.slot.number == 3`; HTML contains "Сейчас" and "Следующая".
4. `test_today_empty_day` — now Sunday `2026-11-22 12:00` → "Сегодня занятий нет."
5. `test_today_day_finished` — now `2026-11-16 22:00` → "Занятия на сегодня закончились."
6. `test_week_shows_only_own_group` — A's week contains GX1 disciplines and the shared lecture, never the GY-only discipline.
7. `test_week_navigation` — `/schedule/week/2026-11-18/` → `week.start == date(2026, 11, 16)`; links to `/schedule/week/2026-11-09/` and `/schedule/week/2026-11-23/`.
8. `test_week_boundaries` — a lesson on Sunday 2026-11-22 is in week of 11-16; a lesson on Monday 2026-11-23 is not.
9. `test_invalid_date_404` — `/schedule/week/2026-02-30/` → 404; `/schedule/week/1999-12-31/` → 404.
10. `test_change_rendering` — one change of each kind in the reference week: HTML contains "Отменено", "Перенесено на", "Перенесено с", "Замена аудитории", "Замена преподавателя", each reason text, `<del` with the old room number and `<ins` with the new one, `<del>` with the old teacher short name.
11. `test_room_code_attribute` — `data-room-code="<code>"` present for every room in the week.
12. `test_student_forbidden_on_staff_pages` — A: `/staff/schedule/`, `/staff/schedule/<GX1.pk>/`, `/staff/schedule/<GX1.pk>/2026-11-16/` → 403.
13. `test_staff_group_list_scoped` — SX sees GX1, GX2, not GY.
14. `test_staff_group_week_own_faculty` — SX `/staff/schedule/<GX1.pk>/2026-11-16/` → 200 with GX1 disciplines.
15. `test_staff_other_faculty_group_404` — SX `/staff/schedule/<GY.pk>/` → 404; nonexistent pk → 404.
16. `test_nav_schedule_link` — A's page links to `/schedule/`; SX's page links to `/staff/schedule/`.
17. `test_week_view_query_count_constant` — count queries of A's week page with base data, add 10 lessons and 5 changes for GX1, count again → equal.

`test_demo.py` (`TestCase`; call `seed_demo_data("Demo-Pass-2026-test!")` then `seed_schedule_demo(date(2026, 11, 18))`, or `call_command` with patched `timezone.now` and `DEMO_PASSWORD`):
- `test_counts` — 7 rooms, 6 teachers, 6 disciplines, 18 weekly lessons, 8 changes; 2 changes of each kind; rooms on ≥ 3 floors.
- `test_change_dates_in_current_and_next_week` — every `original_date` in `[2026-11-16, 2026-11-29]`.
- `test_idempotent` — run twice with the same date → same counts.
- `test_rerun_later_refreshes_changes` — run at 2026-11-18, then at 2026-12-02 → still 18 lessons and 8 changes; all `original_date`s now in `[2026-11-30, 2026-12-13]`.
- `test_far_date_renders_without_reseed` — seed at 2026-11-18; `week_schedule(date(2026, 12, 2), [ЦД-101.pk], today=...)` has at least one item on each day Monday–Friday; also `date(2026, 11, 28)` week renders.
- `test_seeded_schedule_has_no_conflicts` — for every lesson `validate_weekly_lesson(..., exclude_pk=lesson.pk) == []`.
- `test_command_output_and_idempotency` — `call_command("seed_demo")` twice with patched env and clock; output contains "Schedule ready"; counts unchanged.

`university/tests/test_models.py` add: room code validator (`"Room-1"`, `"1room"` → `ValidationError` on `full_clean`; `"room-1"` OK); floor 0 → `IntegrityError`; `Teacher.short_name` with and without middle name; duplicate teacher name → `IntegrityError`.

Existing tests must keep passing unchanged (including the URL-resolver public-URL test and `accounts/tests/test_seed_demo.py`).

---

## 8. Implementation order

Shell: repo root, `.venv` active, `export DEBUG=true`, `export DEMO_PASSWORD='Local-Demo-Pass-2026!'`. Never open or edit `.env`. Do not delete `db.sqlite3` or any migration.

1. `university` models `Room`, `Teacher`, `Discipline` + admin + tests; `python manage.py makemigrations university`; `migrate`; `python manage.py test university`.
2. `schedule` app skeleton: `apps.py`, `timeslots.py` + test, `models.py`; settings/urls/pyproject changes; `makemigrations schedule`; `migrate`; `python manage.py check`.
3. `services.py` + `test_services.py` (without validation tests). `python manage.py test schedule`.
4. `validation.py`, `LessonChange.clean()`, `mutations.py`, `forms.py`, `admin.py` + `test_validation.py`.
5. `accounts/selectors.groups_visible_to` + tests; `converters.py`, `views.py`, `urls.py`, templates, nav, CSS + `test_views.py`.
6. `schedule/demo.py`, command change, `test_demo.py`; run `python manage.py seed_demo` twice.
7. README. `ruff format .`; run all of section 9; manual check. Send the `REPORT` to the Reviewer. Do not commit.

## 9. Verification

```bash
source .venv/bin/activate
export DEBUG=true
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
ruff check . && ruff format --check .
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
```
Manual (runserver, 360 px): `student1` → `/schedule/` and `/schedule/week/`, next week, changed lessons are visibly marked; `staff1` → `/staff/schedule/` → ЦД-101 week; `/staff/schedule/<ЭД-201 id>/` → 404. No horizontal scroll.

In the `REPORT`: output tails, test count, the two query counts from the query-count tests.

## 10. Risks

- **IDOR**: staff group lookups must start from `groups_visible_to(request.user)`; student views use only `self.profile.group_id`.
- **Validation bypass**: code that writes `WeeklyLesson`/`LessonChange` directly (`objects.create`, `.save()` without `full_clean`) skips overlap checks. Only `schedule/mutations.py` may write them (tests that check DB constraints are the exception).
- **Concurrency**: two simultaneous admin edits could both pass validation (no locking). Acceptable: one operator.
- **Template edits after changes**: editing a weekly lesson's weekday/range is blocked while it has incompatible changes (6.2 step 5). Room/slot edits are not re-validated against existing moved-in changes — documented limitation.
- **Timezone**: always `timezone.localtime()` / `timezone.localdate()` (Europe/Moscow), never `date.today()` or `datetime.now()`.
- **Seed vs real data**: re-running `seed_demo` deletes and recreates changes of the 18 demo lessons only.

---

## Clarifications

- **Q1 (Coder, DJ007)**: `WeeklyLessonAdminForm.Meta.fields` is the explicit list of all 9 editable fields (see 6.5), not `"__all__"`. No ruff ignores. If a field is added to `WeeklyLesson` later, it must be added to this list.
