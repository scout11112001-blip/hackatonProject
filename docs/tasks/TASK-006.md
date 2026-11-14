# TASK-006: Certificates and applications (requests) with private PDF attachments

Author: Planner. Status: ready for implementation.
Base commit: `23eeb2e`. Reused: role mixins (`accounts/access.py`), selectors pattern (`accounts/selectors.py`), validation pattern (model/service level, non-field errors, admin never 500), locking pattern (`select_for_update` in services), `core/testing.FrozenClockMixin`, `scripts/run_tests_at.py`.

Jury scenario (phone): student logs in → submits a request → sees its status; staff logs in → processes it.

---

## 1. Acceptance criteria

| ID | Criterion |
|---|---|
| AC0 | `pyproject.toml` excludes the whole `docs/` from ruff; `ruff check .` / `ruff format --check .` pass and never touch `docs/`. |
| AC1 | New app `petitions` with `RequestType`, `Petition`, `PetitionAttachment`, `PetitionStatusChange`, `PetitionComment`; migrations exist. |
| AC2 | Student form has exactly two inputs: «Комментарий» and PDF files. `comment_required` types require a comment (form **and** service) and show the hint. |
| AC3 | Attachments: optional, ≤ 3 files, each ≤ 5 MB; accepted only if extension `.pdf`, declared content type `application/pdf` **and** signature `%PDF-`. |
| AC4 | Files are stored in a private directory outside static/media, at `request_attachments/<2 hex>/<32 hex>.pdf`, name from `uuid.uuid4().hex`, nothing user-derived in the path, DB-unique path, bounded retry on collision, storage never overwrites. Original name kept only as sanitized display metadata. |
| AC5 | Files are served only by a Django view with the request's access rules, `Content-Disposition: attachment`, `Content-Type: application/pdf`, `X-Content-Type-Options: nosniff`; no public URL exists. |
| AC6 | Workflow in one explicit transition table; every status change (and the initial submission) stores a history row (from, to, actor, time, comment); invalid transitions and reject without comment are rejected at service level. No student withdraw. |
| AC7 | Concurrency: a transition succeeds only if the locked current status equals the status the actor saw; otherwise «Заявка уже изменена, обновите страницу». Comments are append-only and never conflict. |
| AC8 | A student has at most 3 open (submitted / in_progress) requests of the same type. |
| AC9 | Pages: student catalog → form → confirmation, «Мои заявки», detail (history, staff comments, downloads); staff queue (own faculty, filter status/type, default open oldest first), detail, actions, comments; nav «Заявки» for both roles; all state changes via POST + CSRF. |
| AC10 | Access: students only own requests/files; staff only own faculty (404 otherwise); students cannot transition or comment as staff; URLs use UUIDs. |
| AC11 | `seed_demo` (idempotent) creates demo requests in every status with history, comments and tiny PDFs; each staff faculty has a request waiting in the queue. |
| AC12 | Lists and details run a constant number of queries. |

## 2. Out of scope
Staff attachments, non-PDF files, antivirus, PDF generation, e-mail, notifications (TASK-007), chat, visual theme, holiday calendar, editing a submitted request, pagination of lists, student withdraw.

---

## 3. Design decisions

### 3.1 App name `petitions`
Not `requests` (would shadow the `requests` library on `import requests`). `deanery` is too broad (chat and notifications are also "dean's office"). `petitions` names exactly this bounded context: requests for certificates and applications. `import petitions` / `import deanery` currently fail in `.venv` (no clash). Model names use `Petition*` to avoid confusion with `HttpRequest`. UI text says «заявка».

### 3.2 Concurrency: `select_for_update` + expected status
All transitions go through one service. It locks the petition row (`select_for_update`) and compares the locked status with `expected_status` posted by the form (the status the actor saw). No version field is needed: the status itself is the version for transitions, and comments are separate append-only rows (a comment never modifies the petition row, so "status vs comment" cannot overwrite anything). On PostgreSQL the second writer waits for the lock and then sees the new status; on SQLite writes are serialized by the database lock — the expected-status check gives the same result.

### 3.3 Private storage
`PRIVATE_MEDIA_ROOT` (env, default `BASE_DIR / "private_media"`), never under `STATIC_ROOT`/`static/`, never served by Django URLs or nginx. Storage class `core.storage.PrivateFileStorage` reads `settings.PRIVATE_MEDIA_ROOT` **on every access** (properties, not `cached_property`), because a model field's storage object is created once at model load; reading the setting dynamically lets tests redirect it. `url()` raises (no public URL). `get_available_name()` raises `FileExistsError` instead of renaming → the storage never overwrites and never silently renames.

### 3.4 Test isolation of files
`TEST_RUNNER = "core.test_runner.ProjectTestRunner"`: creates a temporary `PRIVATE_MEDIA_ROOT` for the whole run and deletes it afterwards. All tests (including existing `seed_demo` tests and `scripts/run_tests_at.py`) never write into the repository.

### 3.5 Later tasks
Notifications (TASK-007) read `PetitionStatusChange` rows (time, actor, from/to, comment) and `PetitionComment` rows.

---

## 4. Architecture

### 4.1 Files
Create:
```
core/storage.py
core/test_runner.py
core/tests/test_storage.py
petitions/__init__.py
petitions/apps.py
petitions/models.py
petitions/workflow.py
petitions/files.py
petitions/selectors.py
petitions/services.py
petitions/forms.py
petitions/views.py
petitions/urls.py
petitions/admin.py
petitions/demo.py
petitions/migrations/__init__.py
petitions/migrations/0001_initial.py                (generated)
petitions/templates/petitions/catalog.html
petitions/templates/petitions/form.html
petitions/templates/petitions/submitted.html
petitions/templates/petitions/my_list.html
petitions/templates/petitions/detail.html            (student)
petitions/templates/petitions/staff_queue.html
petitions/templates/petitions/staff_detail.html
petitions/templates/petitions/includes/history.html
petitions/templates/petitions/includes/comments.html
petitions/templates/petitions/includes/attachments.html
petitions/tests/__init__.py
petitions/tests/helpers.py
petitions/tests/test_files.py
petitions/tests/test_workflow.py
petitions/tests/test_services.py
petitions/tests/test_views.py
petitions/tests/test_downloads.py
petitions/tests/test_demo.py
```
Change:
```
pyproject.toml (AC0, known-first-party), config/settings.py, config/urls.py, .env.example, .gitignore,
templates/base.html (nav + messages), static/css/base.css,
accounts/management/commands/seed_demo.py, README.md
```
No other files. No new dependencies.

### 4.2 Tooling (AC0) — do first
`pyproject.toml`: `extend-exclude = ["*/migrations/*", ".venv", "staticfiles", "docs"]` (replaces `"docs/process"`); `known-first-party` += `"petitions"`. Never run `ruff format` on `docs/`.

### 4.3 Settings (`config/settings.py`)
- `INSTALLED_APPS`: add `"petitions"` after `"academics"`.
- After `STORAGES`:
  ```python
  PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default="") or str(BASE_DIR / "private_media"))
  FILE_UPLOAD_PERMISSIONS = 0o640
  FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
  ```
  `FILE_UPLOAD_MAX_MEMORY_SIZE` / `DATA_UPLOAD_MAX_MEMORY_SIZE` stay at Django defaults (2.5 MB): larger uploads are streamed to temporary files, and `DATA_UPLOAD_MAX_MEMORY_SIZE` does not count file data. The 5 MB limit is enforced by validation.
- `TEST_RUNNER = "core.test_runner.ProjectTestRunner"`.
- No `MEDIA_ROOT`/`MEDIA_URL` and no `static()`/`serve` URL patterns.
`.env.example` append:
```
# Private uploads (request attachments). Must NOT be served by nginx or be inside static/.
PRIVATE_MEDIA_ROOT=
```
(empty or unset = default `<repo>/private_media`.) `.gitignore`: add `/private_media/`.

### 4.4 `core/storage.py`
```python
class PrivateFileStorage(FileSystemStorage):
    def __init__(self) -> None                      # super().__init__(base_url=None)
    @property
    def base_location(self) -> str                  # str(settings.PRIVATE_MEDIA_ROOT)
    @property
    def location(self) -> str                       # os.path.abspath(self.base_location)
    def url(self, name: str | None) -> str          # raise ValueError("Private files have no public URL.")
    def get_available_name(self, name: str, max_length: int | None = None) -> str
        # if self.exists(name): raise FileExistsError(name); return name

_private_storage = PrivateFileStorage()

def get_private_storage() -> PrivateFileStorage:
    return _private_storage
```
`FileSystemStorage._save` opens with `O_EXCL` and on a race calls `get_available_name` again → our override raises `FileExistsError`; the file is never overwritten.
Tests (`core/tests/test_storage.py`): `test_location_follows_setting` (`override_settings(PRIVATE_MEDIA_ROOT=tmp)` → `location == tmp`); `test_url_raises`; `test_existing_name_is_not_overwritten` (save `a/x.pdf`, saving again the same name → `FileExistsError`, original content intact); `test_test_runner_uses_temp_dir` (`settings.PRIVATE_MEDIA_ROOT` is not inside `BASE_DIR`).

### 4.5 `core/test_runner.py`
```python
class ProjectTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs) -> None
    def teardown_test_environment(self, **kwargs) -> None
```
- setup: `super()…`; `self._private_dir = tempfile.mkdtemp(prefix="test-private-media-")`; `self._private_override = override_settings(PRIVATE_MEDIA_ROOT=Path(self._private_dir))`; `.enable()`.
- teardown: `.disable()`; `shutil.rmtree(self._private_dir, ignore_errors=True)`; `super()…`.

### 4.6 Models (`petitions/models.py`)
Enums:
```python
class RequestKind(models.TextChoices):
    CERTIFICATE = "certificate", "Справка"
    APPLICATION = "application", "Заявление"

class PetitionStatus(models.TextChoices):
    SUBMITTED = "submitted", "Подана"
    IN_PROGRESS = "in_progress", "В работе"
    READY = "ready", "Готова"
    ISSUED = "issued", "Выдана"
    REJECTED = "rejected", "Отклонена"
```
Constants (`petitions/models.py`): `MAX_COMMENT_LENGTH = 2000`.

**`RequestType`**
| Field | Definition |
|---|---|
| `name` | `CharField("название", max_length=200, unique=True)` |
| `kind` | `CharField("вид", max_length=16, choices=RequestKind.choices)` |
| `description` | `TextField("описание", blank=True, default="")` |
| `processing_days` | `PositiveSmallIntegerField("срок, рабочих дней", validators=[MinValueValidator(1), MaxValueValidator(60)])` |
| `comment_required` | `BooleanField("комментарий обязателен", default=False)` |
| `comment_hint` | `CharField("подсказка к комментарию", max_length=255, blank=True, default="")` |
| `is_active` | `BooleanField("доступна для подачи", default=True)` |
- `Meta`: `ordering = ["kind", "name"]`; `CheckConstraint(condition=Q(processing_days__gte=1) & Q(processing_days__lte=60), name="petitions_type_days_1_60")`. `__str__` → `name`.
- `clean()`: `comment_required` and empty `comment_hint` → non-field error «Для обязательного комментария заполните подсказку.»

**`Petition`**
| Field | Definition |
|---|---|
| `public_id` | `UUIDField("номер", default=uuid.uuid4, unique=True, editable=False)` |
| `student` | `ForeignKey("accounts.StudentProfile", PROTECT, related_name="petitions")` |
| `request_type` | `ForeignKey(RequestType, PROTECT, related_name="petitions")` |
| `comment` | `TextField("комментарий", blank=True, default="", max_length=MAX_COMMENT_LENGTH)` |
| `status` | `CharField("статус", max_length=16, choices=PetitionStatus.choices, default=SUBMITTED)` |
| `created_at` | `DateTimeField("подана", default=timezone.now)` |
| `status_changed_at` | `DateTimeField("статус изменён", default=timezone.now)` |
| `expected_ready_date` | `DateField("ожидаемая дата готовности")` |
| `seed_key` | `SlugField(max_length=40, blank=True, default="", editable=False)` |
- `Meta`: `ordering = ["-created_at"]`; `indexes = [Index(fields=["status", "created_at"], name="petitions_status_created_idx")]`; `CheckConstraint(condition=Q(status__in=[...5 values]), name="petitions_status_value")`; `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="petitions_unique_seed_key")`.
- `__str__` → `f"{self.request_type} — {self.student} ({self.get_status_display()})"`. Property `short_id` → `str(self.public_id)[:8]` (display only).
- No "taken by" field (user decision). No `clean()` (all rules are in services; admin is read-only for petitions).

**`PetitionAttachment`**
| Field | Definition |
|---|---|
| `public_id` | `UUIDField(default=uuid.uuid4, unique=True, editable=False)` (download URL id; never the file path) |
| `petition` | `ForeignKey(Petition, CASCADE, related_name="attachments")` |
| `file` | `FileField(upload_to=attachment_upload_to, storage=get_private_storage, max_length=100, unique=True)` |
| `original_name` | `CharField("имя файла", max_length=120)` |
| `size` | `PositiveIntegerField("размер, байт")` |
| `uploaded_at` | `DateTimeField(default=timezone.now)` |
- `Meta`: `ordering = ["uploaded_at", "pk"]`. `__str__` → `original_name`.

**`PetitionStatusChange`** (history)
| Field | Definition |
|---|---|
| `petition` | `ForeignKey(Petition, CASCADE, related_name="history")` |
| `from_status` | `CharField(max_length=16, choices=PetitionStatus.choices, blank=True, default="")` (`""` = submission) |
| `to_status` | `CharField(max_length=16, choices=PetitionStatus.choices)` |
| `actor` | `ForeignKey(settings.AUTH_USER_MODEL, PROTECT, related_name="petition_status_changes")` |
| `created_at` | `DateTimeField(default=timezone.now)` |
| `comment` | `TextField(blank=True, default="", max_length=MAX_COMMENT_LENGTH)` |
- `Meta`: `ordering = ["created_at", "pk"]`; `Index(fields=["created_at"], name="petitions_history_created_idx")`.

**`PetitionComment`** (staff comments, append-only)
| Field | Definition |
|---|---|
| `petition` | `ForeignKey(Petition, CASCADE, related_name="staff_comments")` |
| `author` | `ForeignKey(settings.AUTH_USER_MODEL, PROTECT, related_name="petition_comments")` |
| `created_at` | `DateTimeField(default=timezone.now)` |
| `text` | `TextField(max_length=MAX_COMMENT_LENGTH)` |
- `Meta`: `ordering = ["created_at", "pk"]`; `CheckConstraint(condition=~Q(text=""), name="petitions_comment_not_empty")`.

### 4.7 URLs (`petitions/urls.py`, `app_name = "petitions"`; include in `config/urls.py` after `academics`)
| Path | View | Name | Method |
|---|---|---|---|
| `requests/` | `MyPetitionsView` | `my_list` | GET |
| `requests/new/` | `CatalogView` | `catalog` | GET |
| `requests/new/<int:type_id>/` | `SubmitPetitionView` | `submit` | GET, POST |
| `requests/<uuid:public_id>/` | `StudentPetitionDetailView` | `detail` | GET |
| `requests/<uuid:public_id>/submitted/` | `SubmittedView` | `submitted` | GET |
| `requests/<uuid:public_id>/files/<uuid:file_id>/` | `download_attachment` | `download` | GET (both roles) |
| `staff/requests/` | `StaffQueueView` | `staff_queue` | GET |
| `staff/requests/<uuid:public_id>/` | `StaffPetitionDetailView` | `staff_detail` | GET |
| `staff/requests/<uuid:public_id>/status/` | `StaffTransitionView` | `staff_transition` | POST only |
| `staff/requests/<uuid:public_id>/comments/` | `StaffCommentView` | `staff_comment` | POST only |
`type_id` is the `RequestType` pk (the catalog is public to students; not a secret).

### 4.8 Navigation and messages (`templates/base.html`)
- Student block: add `<li><a href="{% url 'petitions:my_list' %}">Заявки</a></li>`; staff block: `<li><a href="{% url 'petitions:staff_queue' %}">Заявки</a></li>`.
- Inside `<main>` before `{% block content %}`: `{% if messages %}<ul class="messages">{% for m in messages %}<li class="message message--{{ m.tags }}">{{ m }}</li>{% endfor %}</ul>{% endif %}`.

---

## 5. Functions

### 5.1 `petitions/workflow.py` — single transition table
```python
TRANSITIONS: dict[str, tuple[str, ...]] = {
    SUBMITTED: (IN_PROGRESS, REJECTED),
    IN_PROGRESS: (READY, REJECTED),
    READY: (ISSUED,),
    ISSUED: (),
    REJECTED: (),
}
OPEN_STATUSES = frozenset({SUBMITTED, IN_PROGRESS})
COMMENT_REQUIRED_FOR = frozenset({REJECTED})
ACTION_LABELS = {IN_PROGRESS: "Взять в работу", READY: "Отметить готовой", ISSUED: "Отметить выданной", REJECTED: "Отклонить"}

def allowed_transitions(status: str) -> tuple[str, ...]      # TRANSITIONS.get(status, ())
def can_transition(from_status: str, to_status: str) -> bool
```
Tests (`test_workflow.py`, `SimpleTestCase`): every allowed pair → `True`; every other pair of the 5×5 matrix (incl. same→same) → `False`; `ISSUED`/`REJECTED` final; every target in `TRANSITIONS` has a label; `OPEN_STATUSES` exact.

### 5.2 `petitions/files.py` — attachments
Constants: `MAX_ATTACHMENTS = 3`, `MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024`, `PDF_CONTENT_TYPE = "application/pdf"`, `PDF_SIGNATURE = b"%PDF-"`, `MAX_NAME_ATTEMPTS = 5`, `ATTACHMENT_DIR = "request_attachments"`, `MAX_DISPLAY_NAME = 120`.

```python
def attachment_upload_to(instance: object, filename: str) -> str
```
Ignores both arguments. `name = uuid.uuid4().hex`; return `f"{ATTACHMENT_DIR}/{name[:2]}/{name}.pdf"`. Never use `random`, hashes, the file name, IDs or dates.

```python
def sanitize_display_name(raw: str) -> str
```
1. `name = unicodedata.normalize("NFC", raw or "")`; take the part after the last `/` or `\\`.
2. Remove control characters (`unicodedata.category(c).startswith("C")`) and `"`; collapse whitespace; strip.
3. If not `name.lower().endswith(".pdf")` → append `".pdf"`. If the stem is empty → `"document.pdf"`.
4. If `len(name) > MAX_DISPLAY_NAME`: keep `stem[: MAX_DISPLAY_NAME - 4] + ".pdf"`.
Tests: `"../../etc/passwd.pdf"` → `"passwd.pdf"`; `"C:\\x\\Справка.PDF"` → `"Справка.PDF"`; control chars removed; 300-char name → length 120, ends `.pdf`; `""` → `"document.pdf"`.

```python
def validate_pdf(upload: UploadedFile) -> None
```
Raises `ValidationError` (non-field, Russian, names the sanitized file) when: name does not end with `.pdf` (case-insensitive) → «Файл «X»: допускаются только PDF.»; `upload.content_type != PDF_CONTENT_TYPE` → same message; `upload.size == 0` → «Файл «X» пустой.»; `upload.size > MAX_ATTACHMENT_SIZE` → «Файл «X» больше 5 МБ.»; `upload.seek(0); head = upload.read(5); upload.seek(0)`; `head != PDF_SIGNATURE` → «Файл «X» не является PDF.».

```python
def validate_attachments(uploads: Sequence[UploadedFile]) -> None
```
`len(uploads) > MAX_ATTACHMENTS` → «Можно приложить не больше 3 файлов.»; then `validate_pdf` for each; collect all messages; raise one `ValidationError(list)`.

```python
def store_attachment(petition: Petition, upload: File, original_name: str, size: int) -> PetitionAttachment
```
Must be called inside a transaction (service). Algorithm, up to `MAX_NAME_ATTEMPTS` times:
1. `name = attachment_upload_to(None, "")`; `storage = get_private_storage()`.
2. If `storage.exists(name)` or `PetitionAttachment.objects.filter(file=name).exists()` → next attempt.
3. `upload.seek(0)`; `try: saved = storage.save(name, upload)` / `except FileExistsError: continue`. Assert `saved == name` (if not: `storage.delete(saved)`; raise `RuntimeError`).
4. `try: with transaction.atomic(): att = PetitionAttachment.objects.create(petition=petition, file=saved, original_name=sanitize_display_name(original_name), size=size)` / `except IntegrityError: storage.delete(saved); continue`.
5. Return `att`.
After all attempts → `raise AttachmentStorageError("Не удалось сохранить файл. Попробуйте ещё раз.")` (`class AttachmentStorageError(Exception)` in this module).

Tests (`test_files.py`, `FrozenClockMixin, TestCase`):
- `test_upload_to_format` — regex `^request_attachments/[0-9a-f]{2}/[0-9a-f]{32}\.pdf$`, prefix equals first 2 chars; filename argument (`"../../evil.exe"`) ignored.
- `test_upload_to_uses_uuid4` — `mock.patch("petitions.files.uuid.uuid4", return_value=uuid.UUID(int=1))` → name derived from it.
- `test_store_retries_on_existing_file` — patch `uuid4` with `side_effect=[U1, U1, U2]`, pre-create a file at U1's path → stored at U2's path; the pre-existing file content is unchanged.
- `test_store_retries_on_db_collision` — an attachment row with U1's path exists (file absent) → stored at U2.
- `test_store_gives_up` — `uuid4` always U1 and file exists → `AttachmentStorageError`; no new rows.
- `test_db_unique_path` — two rows with the same `file` → `IntegrityError`.
- `validate_pdf`: valid; wrong extension; wrong content type; renamed non-PDF (`.pdf`, `application/pdf`, content `MZ...`); empty; 5 MB exactly OK; 5 MB + 1 rejected (use `SimpleUploadedFile` with `b"%PDF-" + b"0" * (n - 5)`); uppercase `.PDF` OK.
- `validate_attachments`: 3 OK, 4 rejected; messages for several bad files are all reported.
- sanitize tests above.

### 5.3 `petitions/selectors.py`
```python
def petitions_visible_to(user) -> QuerySet[Petition]
def attachments_visible_to(user) -> QuerySet[PetitionAttachment]
```
`petitions_visible_to`: base `Petition.objects.select_related("request_type", "student__group__program__faculty")`; not authenticated/inactive → `none()`; STUDENT with profile → `filter(student__user=user)`; STAFF with profile → `filter(student__group__program__faculty=profile.faculty)`; else `none()`. `attachments_visible_to`: `PetitionAttachment.objects.filter(petition__in=petitions_visible_to(user))`.
Tests in `test_services.py::SelectorTests`: student sees own only; staff own faculty only; superuser/anonymous/staff without profile → empty; attachments follow petitions.

### 5.4 `petitions/services.py`
Exceptions: `class StaleStatusError(ValidationError)` with default message `"Заявка уже изменена, обновите страницу."`. Constant `MAX_OPEN_PER_TYPE = 3`.

#### `add_working_days(start: date, days: int) -> date`
Counts `days` working days (Mon–Fri) strictly after `start`. `days < 1` → `ValueError`. Tests: Mon+1 → Tue; Fri+1 → Mon; Sat+1 → Mon; Sun+1 → Mon; Fri+5 → next Fri; Wed+10 → Wed two weeks later.

#### `submit_petition(student: StudentProfile, request_type: RequestType, comment: str, uploads: Sequence[UploadedFile]) -> Petition`
1. `comment = (comment or "").strip()`. Errors (collect, non-field): `not request_type.is_active` → «Этот вид заявки сейчас недоступен.»; `len(comment) > MAX_COMMENT_LENGTH` → «Комментарий слишком длинный.»; `request_type.comment_required and not comment` → «Для этой заявки комментарий обязателен.»; plus `validate_attachments(uploads)` messages. Any → `raise ValidationError(errors)`.
2. `stored: list[str] = []`; `try: with transaction.atomic():`
   - `_lock_student(student.pk)` where `def _lock_student(pk: int) -> None: StudentProfile.objects.select_for_update().filter(pk=pk).values_list("pk", flat=True).get()` (serializes the limit check per student);
   - `open_count = Petition.objects.filter(student=student, request_type=request_type, status__in=OPEN_STATUSES).count()`; `>= MAX_OPEN_PER_TYPE` → `ValidationError(f"У вас уже {MAX_OPEN_PER_TYPE} открытые заявки этого вида. Дождитесь их выполнения.")`;
   - `now = timezone.now()`; `petition = Petition.objects.create(student=student, request_type=request_type, comment=comment, status=SUBMITTED, created_at=now, status_changed_at=now, expected_ready_date=add_working_days(timezone.localdate(), request_type.processing_days))`;
   - `PetitionStatusChange.objects.create(petition=petition, from_status="", to_status=SUBMITTED, actor=student.user, created_at=now)`;
   - for each upload: `att = store_attachment(petition, upload, upload.name, upload.size)`; `stored.append(att.file.name)`.
   `except BaseException: for name in stored: get_private_storage().delete(name); raise`.
3. Return `petition`.
- Access: only the student themself (views pass `self.profile`).

#### `change_status(petition: Petition, actor: User, expected_status: str, new_status: str, comment: str = "") -> Petition`
1. `staff = get_profile_for_role(actor, User.Role.STAFF)` (→ `PermissionDenied` for students/superusers).
2. `comment = (comment or "").strip()`; too long → `ValidationError`.
3. `with transaction.atomic():`
   - `locked = _lock_petition(petition.pk)`; where `def _lock_petition(pk: int) -> Petition: return Petition.objects.select_for_update().select_related("student__group__program").get(pk=pk)`;
   - `locked.student.group.program.faculty_id != staff.faculty_id` → `PermissionDenied`;
   - `locked.status != expected_status` → `raise StaleStatusError(StaleStatusError.default_message)`;
   - `not can_transition(locked.status, new_status)` → `ValidationError(f"Нельзя перевести заявку из «{label(from)}» в «{label(to)}».")`;
   - `new_status in COMMENT_REQUIRED_FOR and not comment` → `ValidationError("Укажите причину отклонения.")`;
   - `now = timezone.now()`; `PetitionStatusChange.objects.create(petition=locked, from_status=locked.status, to_status=new_status, actor=actor, created_at=now, comment=comment)`; `locked.status = new_status`; `locked.status_changed_at = now`; `locked.save(update_fields=["status", "status_changed_at"])`.
4. Return `locked`.

#### `add_staff_comment(petition: Petition, actor: User, text: str) -> PetitionComment`
1. `staff = get_profile_for_role(actor, STAFF)`; `petition.student.group.program.faculty_id != staff.faculty_id` → `PermissionDenied`.
2. `text = (text or "").strip()`; empty → «Комментарий не может быть пустым.»; too long → «Комментарий слишком длинный.».
3. `return PetitionComment.objects.create(petition=petition, author=actor, text=text)`. Allowed at any status. Never updates existing rows.

Tests (`test_services.py`, `FrozenClockMixin, TestCase`, clock Wed 2026-11-18 12:00):
`SubmitTests`: `test_submit_creates_petition_and_history` (status, expected date = Mon 2026-11-23 for 3 working days, 1 history row from "" by the student); `test_comment_required_rejected`; `test_comment_whitespace_only_rejected_when_required`; `test_comment_optional_ok`; `test_comment_too_long`; `test_inactive_type_rejected`; `test_attachments_stored_privately` (file under `settings.PRIVATE_MEDIA_ROOT`, path format, content equal); `test_invalid_attachment_rejected_nothing_stored` (no petition, no file); `test_limit_three_open_per_type` (3 OK, 4th rejected; other type OK; after one becomes ISSUED → OK again); `test_limit_counts_in_progress`; `test_files_removed_on_failure` (patch `store_attachment` to raise on the 2nd file → no petition, first file deleted from disk); `test_student_row_locked` (`mock.patch("petitions.services._lock_student", wraps=_lock_student)` → called once with the student pk).
`TransitionTests`: every allowed transition succeeds and writes history (from, to, actor, time = frozen now, comment); every disallowed one → `ValidationError`, no history; reject without comment → error; reject with comment stored in history; `test_stale_expected_status_rejected` (status IN_PROGRESS, expected SUBMITTED → `StaleStatusError` with «Заявка уже изменена, обновите страницу», status unchanged, no history row); `test_concurrent_take_and_reject` (staff A takes with expected SUBMITTED → ok; staff B rejects with expected SUBMITTED → `StaleStatusError`); `test_student_cannot_transition` (`PermissionDenied`); `test_other_faculty_staff_cannot_transition`; `test_superuser_cannot_transition`; `test_lock_used` (`mock.patch("petitions.services._lock_petition", wraps=_lock_petition)` called once with pk).
`CommentTests`: append at every status; two staff of the faculty both add → 2 rows, first unchanged; empty rejected; student → `PermissionDenied`; other faculty staff → `PermissionDenied`; comment after a concurrent transition (stale page) still succeeds.
`WorkingDaysTests`: cases above.

### 5.5 Forms (`petitions/forms.py`)
```python
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs): kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "application/pdf,.pdf"})); super().__init__(*args, **kwargs)
    def clean(self, data, initial=None) -> list[UploadedFile]:
        if not data: return []
        items = data if isinstance(data, (list, tuple)) else [data]
        return [super().clean(item, initial) for item in items]

class PetitionForm(forms.Form):
    comment = forms.CharField(label="Комментарий", required=False, max_length=MAX_COMMENT_LENGTH, widget=forms.Textarea(attrs={"rows": 4}))
    files = MultipleFileField(label="PDF-файлы (необязательно, до 3 файлов по 5 МБ)", required=False)
    def __init__(self, *args, request_type: RequestType, **kwargs)
    def clean_comment(self) -> str
    def clean_files(self) -> list[UploadedFile]
```
- `__init__`: `self.request_type = request_type`; `self.fields["comment"].required = request_type.comment_required`; `self.fields["comment"].help_text = request_type.comment_hint`.
- `clean_comment`: strip; required and empty → `ValidationError("Для этой заявки комментарий обязателен.")`.
- `clean_files`: `validate_attachments(files)`; return files.
Exactly two fields — test `test_form_has_exactly_two_fields`.

```python
class TransitionForm(forms.Form):
    expected_status = forms.ChoiceField(choices=PetitionStatus.choices)
    new_status = forms.ChoiceField(choices=PetitionStatus.choices)
    comment = forms.CharField(required=False, max_length=MAX_COMMENT_LENGTH)

class StaffCommentForm(forms.Form):
    text = forms.CharField(label="Комментарий", max_length=MAX_COMMENT_LENGTH, widget=forms.Textarea(attrs={"rows": 3}))
```

### 5.6 Views (`petitions/views.py`)
- `CatalogView(StudentRequiredMixin, TemplateView)` — `types = RequestType.objects.filter(is_active=True)` grouped by kind (two lists).
- `SubmitPetitionView(StudentRequiredMixin, FormView)` — `request_type = get_object_or_404(RequestType, pk=type_id, is_active=True)` in `dispatch` after the mixin; `get_form_kwargs` adds `request_type`; `form_valid`: `try: petition = submit_petition(self.profile, self.request_type, form.cleaned_data["comment"], form.cleaned_data["files"])` / `except ValidationError as exc: form.add_error(None, exc); return self.form_invalid(form)`; redirect to `petitions:submitted`. Template uses `enctype="multipart/form-data"`, shows the hint above the textarea when `comment_required`.
- `SubmittedView(StudentRequiredMixin, DetailView)` — queryset `petitions_visible_to(user)`, `slug_field = slug_url_kwarg = "public_id"`; shows «Заявка подана», type, short number, expected date, links to detail and list.
- `MyPetitionsView(StudentRequiredMixin, ListView)` — `petitions_visible_to(user).order_by("-created_at")`; empty state «Заявок пока нет.» + link to the catalog.
- `StudentPetitionDetailView(StudentRequiredMixin, DetailView)` — queryset `petitions_visible_to(user).prefetch_related(Prefetch("history", queryset=PetitionStatusChange.objects.select_related("actor__staff_profile")), Prefetch("staff_comments", queryset=PetitionComment.objects.select_related("author__staff_profile")), "attachments")`; no action forms.
- `StaffQueueView(StaffRequiredMixin, ListView)` — filters from GET: `status` ∈ {`"open"` (default), `"all"`, any status value}; invalid → `"open"`; `type` = `RequestType` pk or empty; invalid → ignored. Queryset `petitions_visible_to(user)` + filters, `.order_by("created_at")` (oldest first), annotated `attachment_count=Count("attachments")`. Context: filter choices, selected values, `types` list.
- `StaffPetitionDetailView(StaffRequiredMixin, DetailView)` — same prefetch as the student detail + student info (`student__user`, group, record number); context: `actions = [(status, ACTION_LABELS[status]) for status in allowed_transitions(object.status)]`, `TransitionForm`/`StaffCommentForm` initial `expected_status=object.status`.
- `StaffTransitionView(StaffRequiredMixin, View)` — `http_method_names = ["post"]`; petition via `get_object_or_404(petitions_visible_to(user), public_id=...)` (404 for other faculty); bind `TransitionForm(request.POST)`; invalid → error message; else `change_status(...)`; `ValidationError` (incl. `StaleStatusError`) → `messages.error(request, " ".join(exc.messages))`; success → `messages.success(request, f"Статус изменён: {label}.")`; always redirect to `staff_detail` (PRG).
- `StaffCommentView(StaffRequiredMixin, View)` — POST only; same lookup; `add_staff_comment`; errors as messages; redirect to `staff_detail`.
- `download_attachment(request, public_id, file_id)` — `@require_GET`; `att = get_object_or_404(attachments_visible_to(request.user).select_related("petition"), public_id=file_id, petition__public_id=public_id)`; `response = FileResponse(att.file.open("rb"), as_attachment=True, filename=att.original_name, content_type="application/pdf")`; `response["X-Content-Type-Options"] = "nosniff"`; `response["Cache-Control"] = "private, no-store"`; return. Anonymous → login redirect (middleware).
Display helper (template filter or model-free function in `views.py`): actor name = `actor.staff_profile.full_name` for staff, «Студент» for students, «Администратор» otherwise.

### 5.7 Templates
All extend `base.html`, Russian, no inline styles, forms with `{% csrf_token %}`. Status shown as text plus class `status status--<value>`.
- `catalog.html`: two sections «Справки», «Заявления»; each type: name, description, «Срок: N раб. дн.», link «Подать».
- `form.html`: `<h1>{{ request_type.name }}</h1>`; hint paragraph when `comment_required`; form `method="post" enctype="multipart/form-data"`; `{{ form.non_field_errors }}`; fields; button «Отправить заявку».
- `submitted.html`, `my_list.html` (`<ul>`: type, «№ {{ short_id }}», date, status, expected date), `detail.html` (type, status, created, expected date, student comment, `includes/attachments.html`, `includes/history.html`, `includes/comments.html`).
- `staff_queue.html`: GET filter form (status select incl. «Открытые» default and «Все», type select, button «Показать»), list: student name, group, type, created, status, attachment count, link; empty state «Заявок нет.».
- `staff_detail.html`: student block (ФИО, группа, номер зачётки), petition block, attachments, history, comments, one POST form per action (hidden `expected_status`, `new_status`; for «Отклонить» a required textarea `comment`), comment form.
- `includes/attachments.html`: list of links to `petitions:download` with `original_name` and size in KB; empty → «Файлов нет.».
- `includes/history.html`: `<ol>`: time, «from → to» labels, actor, comment.
- `includes/comments.html`: `<ul>`: author, time, text; empty → «Комментариев нет.».
CSS (`base.css`, tokens only): `.messages`, `.message--error` (`color: var(--color-changed)`), `.status` (bold), `.petition-list` list reset with borders like `.lesson`, `.action-form` margin.

### 5.8 Admin (`petitions/admin.py`)
- `RequestTypeAdmin`: full CRUD; `list_display = ("name", "kind", "processing_days", "comment_required", "is_active")`; `list_filter = ("kind", "is_active")`.
- `PetitionAdmin`: read-only (`has_add_permission`/`has_change_permission`/`has_delete_permission` → `False`; `has_view_permission` default); `list_display = ("public_id", "request_type", "student", "status", "created_at")`; `list_filter = ("status", "request_type")`; inlines (read-only, `can_delete=False`, `extra=0`, `has_add_permission False`): history, comments, attachments with `fields = ("original_name", "size", "uploaded_at")` — **never** display the `file` field (its `url()` raises by design).
State changes only via the workflow service (staff pages); the superuser does not process requests.

### 5.9 Demo data (`petitions/demo.py`)
```python
DEMO_PDF: bytes  # minimal valid PDF, e.g. b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
def seed_petitions_demo(today: date) -> PetitionsSeedSummary  # types: int, petitions: int, attachments: int
```
Request types (upsert by `name`; `update_or_create` is fine here — reference data like rooms): 
| name | kind | days | comment_required | hint |
|---|---|---|---|---|
| Справка об обучении | certificate | 3 | False | «Можно указать, куда нужна справка.» |
| Справка для стипендиального отдела | certificate | 3 | True | «Обязательно укажите причину обращения.» |
| Заявление на повторную промежуточную аттестацию | application | 10 | True | «Обязательно укажите причину обращения.» |
| Заявление на академический отпуск | application | 15 | True | «Обязательно укажите причину обращения.» |
Descriptions: one short fictional sentence each.

Demo petitions — create only if no row with the `seed_key` exists (never update; same rule as academics). Times: `base = timezone.now()`; `created_at = base - timedelta(days=age)`; history steps at `created_at + timedelta(hours=k * 20)` (k = 1, 2, 3); `expected_ready_date = add_working_days(created_at local date, days)`. Each history row's actor: the student for the submission row, the faculty's staff for the others. Rows are created directly with the ORM (services always use "now"), all inside one `transaction.atomic()`; files via `store_attachment(petition, ContentFile(DEMO_PDF), "<name>", len(DEMO_PDF))`.
| seed_key | student | type | age (days) | final status (path) | student comment | staff comment | files |
|---|---|---|---|---|---|---|---|
| `p-1` | student1 | Справка об обучении | 2 | submitted | «Для предоставления по месту требования.» | — | `spravka-zapros.pdf` |
| `p-2` | student1 | Справка для стипендиального отдела | 4 | in_progress (submitted→in_progress) | «Для оформления повышенной стипендии.» | staff1: «Справка будет готова к пятнице.» | — |
| `p-3` | student3 | Заявление на повторную промежуточную аттестацию | 6 | ready (→in_progress→ready) | «Пропустила экзамен по болезни, справка прилагается.» | — | `spravka-bolezn.pdf` |
| `p-4` | student3 | Заявление на академический отпуск | 9 | rejected (→rejected, comment «Не приложены подтверждающие документы.») | «Прошу предоставить академический отпуск по семейным обстоятельствам.» | — | — |
| `p-5` | student1 | Справка об обучении | 20 | issued (→in_progress→ready→issued) | «Для военкомата.» | — | — |
| `p-6` | student2 | Справка об обучении | 1 | submitted | «Для банка.» | — | `zayavlenie.pdf` |
| `p-7` | student2 | Справка для стипендиального отдела | 5 | in_progress | «Для назначения социальной стипендии.» | staff2: «Проверяем данные о стипендии.» | — |
Every status present; FDD queue has `p-1`, FAE queue has `p-6`. All seeded petitions must also satisfy `full_clean()`.

`seed_demo` command: inside the existing transaction after academics: `p = seed_petitions_demo(today)`; extra output line `f"Requests ready: {p.types} types, {p.petitions} requests, {p.attachments} attachments."`. Seed writes files to `PRIVATE_MEDIA_ROOT`; for local seed checks use a temporary DB **and** `PRIVATE_MEDIA_ROOT=$TMPDIR/...`.

### 5.10 README
Section "Requests": student/staff pages, workflow table, limits (3 open per type, 3 files × 5 MB, PDF only), private storage: «`PRIVATE_MEDIA_ROOT` must never be served by nginx; downloads go through Django access checks»; nginx `client_max_body_size 20m;`. Env table row `PRIVATE_MEDIA_ROOT`. Demo data: list of demo requests per student.

---

## 6. Test plan

Helpers `petitions/tests/helpers.py`: `pdf_upload(name="doc.pdf", size=None, content_type="application/pdf") -> SimpleUploadedFile` (content `b"%PDF-1.4\n" + padding + b"%%EOF"`), `fake_upload(name, content, content_type)`, `make_type(name="Справка", kind="certificate", days=3, comment_required=False, hint="") -> RequestType`, `make_petition(student_profile, request_type, status="submitted", created_at=None) -> Petition` (direct ORM, with a submission history row). Reuse `accounts/tests/helpers.py`. All `TestCase` classes use `FrozenClockMixin` (clock Wed 2026-11-18 12:00 MSK). Never rely on `seed_demo` data outside `test_demo.py`.

### 6.1 Traceability
| AC | Tests |
|---|---|
| AC0 | verification commands (`ruff format --check .` output does not list `docs/`) |
| AC1 | `test_services.*`, migrations check |
| AC2 | `test_views.FormTests.*`, `test_services.SubmitTests.test_comment_*` |
| AC3 | `test_files.ValidatePdfTests.*`, `test_views.FormTests.test_upload_*` |
| AC4 | `test_files.StoreAttachmentTests.*`, `core/tests/test_storage.py` |
| AC5 | `test_downloads.*` |
| AC6 | `test_workflow.*`, `test_services.TransitionTests.*` |
| AC7 | `test_services.TransitionTests.test_stale_*`, `test_concurrent_*`, `test_lock_used`, `test_views.StaffActionTests.test_stale_message_shown` |
| AC8 | `test_services.SubmitTests.test_limit_*` |
| AC9 | `test_views.*` (pages, nav, filters, empty states, POST-only) |
| AC10 | access matrix 6.2 |
| AC11 | `test_demo.*` |
| AC12 | `test_views.QueryCountTests.*` |

### 6.2 Access matrix (`test_views.AccessMatrixTests`, `test_downloads.DownloadAccessTests`)
Fixture: faculties X, Y; students A, A2 (X), B (Y); staff SX (X), SY (Y); superuser U; petitions PA (A, with attachment FA), PA2 (A2), PB (B, with attachment FB).
| URL | anon | student A | student A2 (other student, same faculty) | staff SX (own faculty) | staff SY (other faculty) | superuser |
|---|---|---|---|---|---|---|
| `/requests/` | 302 | 200 own only | — | 403 | 403 | 403 |
| `/requests/new/` | 302 | 200 | — | 403 | 403 | 403 |
| `/requests/new/<type>/` GET/POST | 302 | 200 / 302 on success | — | 403 | 403 | 403 |
| `/requests/new/<inactive type>/` | 302 | 404 | — | 403 | 403 | 403 |
| `/requests/<PA>/` | 302 | 200 | 404 | 403 | 403 | 403 |
| `/requests/<PA>/submitted/` | 302 | 200 | 404 | 403 | 403 | 403 |
| `/requests/<PA>/files/<FA>/` | 302 | 200 | 404 | 200 | 404 | 404 |
| `/requests/<PA>/files/<FB>/` (mismatched pair) | 302 | 404 | 404 | 404 | 404 | 404 |
| `/requests/<random uuid>/files/<random uuid>/` | 302 | 404 | — | 404 | — | 404 |
| `/staff/requests/` | 302 | 403 | — | 200 (PA, PA2 only) | 200 (PB only) | 403 |
| `/staff/requests/<PA>/` | 302 | 403 | — | 200 | 404 | 403 |
| `/staff/requests/<PA>/status/` POST | 302 | 403 | — | 302 + changed | 404, unchanged | 403 |
| `/staff/requests/<PA>/comments/` POST | 302 | 403 | — | 302 + comment | 404, no comment | 403 |
| `/staff/requests/<PA>/status/` GET | 302 | 403 | — | 405 | 405 | 403 |
Each cell is one assertion inside a named test (e.g. `test_detail_other_student_404`, `test_download_other_faculty_404`, `test_staff_transition_other_faculty_404`); "—" = not applicable. Plus `test_random_uuid_404` and `test_sequential_ids_not_used` (URLs contain `public_id`, never `pk`).

### 6.3 Downloads (`test_downloads.py`)
`test_download_headers` — status 200, `Content-Type == "application/pdf"`, `Content-Disposition` starts with `attachment;` and contains the sanitized original name (non-ASCII → `filename*=utf-8''...`), `X-Content-Type-Options == "nosniff"`, `Cache-Control` contains `no-store`, body equals the uploaded bytes. `test_no_public_url` — `PetitionAttachment.file.url` raises `ValueError`; `test_no_static_serve_patterns` — walk `get_resolver()` patterns: no callback is `django.views.static.serve`; `settings.PRIVATE_MEDIA_ROOT` not inside `settings.STATIC_ROOT` or any `STATICFILES_DIRS`. `test_path_traversal_name_not_used` — upload named `../../x.pdf` → stored path matches the format, display name `x.pdf`.

### 6.4 Views (`test_views.py`)
`FormTests`: `test_form_has_exactly_two_fields`; `test_hint_shown_for_required_comment`; `test_required_comment_missing_shows_error` (200, error, no petition); `test_optional_comment_submit` (302 to `submitted`); `test_upload_valid_pdfs` (2 files stored); `test_upload_four_files_rejected`; `test_upload_non_pdf_rejected` (renamed `.exe` content with `.pdf` name); `test_upload_wrong_content_type_rejected`; `test_upload_too_large_rejected`; `test_limit_message_shown` (4th open of the same type → form error); `test_csrf_enforced` (`Client(enforce_csrf_checks=True)` POST without token → 403).
`StudentPagesTests`: `test_catalog_lists_active_types_by_kind`; `test_my_list_newest_first_and_status_text`; `test_my_list_empty_state`; `test_detail_shows_history_comments_attachments`; `test_detail_has_no_action_forms` (no `/staff/` form actions, no «Отозвать»); `test_submitted_page_shows_expected_date`.
`StaffPagesTests`: `test_queue_default_open_oldest_first`; `test_queue_filter_status`; `test_queue_filter_all`; `test_queue_filter_type`; `test_queue_invalid_filter_falls_back`; `test_queue_empty_state`; `test_detail_shows_student_info_and_actions` (buttons only for allowed transitions); `test_final_status_has_no_actions`.
`StaffActionTests`: `test_take_ready_issue_flow` (3 POSTs → ISSUED, 4 history rows, success messages); `test_reject_requires_comment` (error message, unchanged); `test_reject_with_comment`; `test_invalid_transition_message` (POST `new_status=issued` from submitted → error, unchanged); `test_stale_message_shown` (POST with outdated `expected_status` → message «Заявка уже изменена, обновите страницу», unchanged); `test_comment_added_and_visible_to_student`; `test_empty_comment_rejected`; `test_tampered_form_values` (`new_status=unknown` → error, no 500).
`NavigationTests`: student nav links `/requests/`; staff nav links `/staff/requests/`; superuser has neither.
`QueryCountTests`: `test_my_list_constant_queries`, `test_staff_queue_constant_queries`, `test_student_detail_constant_queries`, `test_staff_detail_constant_queries` — count with 1 petition (1 history row, 1 comment, 1 file); add 5 petitions / 10 history rows / 5 comments / 5 files; count again → equal.

### 6.5 Demo (`test_demo.py`, `PetitionsDemoTests`)
Run `seed_demo_data`, `seed_schedule_demo(D)`, `seed_academics_demo(D)`, `seed_petitions_demo(D)` with `D = date(2026, 11, 18)`: `test_types_exact` (4 types with the flags from 5.9); `test_every_status_present`; `test_each_faculty_has_waiting_request` (FDD and FAE each ≥ 1 SUBMITTED); `test_history_consistent` (for each petition: first row from "" to submitted by the student; consecutive rows chain from→to; last `to_status == status`; every step allowed by `can_transition`); `test_demo_files_private_and_valid` (3 files, path format, start with `%PDF-`); `test_idempotent` (run twice → same counts of petitions, history, comments, attachments, files on disk); `test_command_output` (`call_command("seed_demo")` → «Requests ready»).

### 6.6 Settings branches
`core/tests/test_storage.py::test_test_runner_uses_temp_dir`; `test_private_root_default` — loading settings hermetically (reuse the loader from `core/tests/test_production_settings.py`) with `PRIVATE_MEDIA_ROOT` unset → `BASE_DIR/"private_media"`, set → that path, empty → default. DEBUG-dependent behaviour: none (no media serving in any mode) — `test_no_static_serve_patterns` covers both.

### 6.7 Regression and negative cases
Mismatched petition/file pair (6.2), random UUIDs, tampered POST values, CSRF, stale status, collision retry, traversal names, oversize/empty/fake PDFs, limit boundary (3 OK / 4th rejected), final statuses without actions, working-day boundaries (weekends).

---

## 7. Feasibility check (2026-11-14 on `23eeb2e`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — `StudentRequiredMixin`, `StaffRequiredMixin`, `get_profile_for_role` (`accounts/access.py`); selector pattern (`accounts/selectors.py:18,37`); `FrozenClockMixin`, `moscow` (`core/testing.py`); `scripts/run_tests_at.py` uses `get_runner(settings)` (picks up `TEST_RUNNER`); `seed_demo` command computes `today` once (`accounts/management/commands/seed_demo.py:24`) and calls `seed_academics_demo(today)` (`:27`); hermetic settings loader in `core/tests/test_production_settings.py`; nav block in `templates/base.html`; `README.md` sections (Known limitations at line 97). OK.
3. No collisions — `import petitions` / `import deanery` → `ModuleNotFoundError`; no `core/storage.py`, `core/test_runner.py`; `base.html` has no messages block (grep `messages` → none, added here); no `MEDIA_ROOT` or `serve` patterns exist; `.gitignore` has `/media/` only. OK.
4. Migrations — `makemigrations --check --dry-run` → "No changes detected"; the new app only adds tables. OK.
5. Tools — Python 3.12.16, Django 5.2.19, ruff 0.17.4; no new dependency. OK.
6. Framework — verified on 5.2.19: `FileField(unique=True)` passes model checks; `FileSystemStorage.base_location` is a `cached_property` (hence the property override, 3.3); `FileSystemStorage._save` uses `O_EXCL` and calls `get_available_name` on races; `uuid` path converter exists; `FileResponse` available; `FILE_UPLOAD_MAX_MEMORY_SIZE` default 2621440; default `TEST_RUNNER` is `DiscoverRunner`. Django's documented `MultipleFileField` pattern (`allow_multiple_selected = True`) is used. OK.
7. Environment — new env variable `PRIVATE_MEDIA_ROOT` added to `.env.example` by this task. Local seed checks need temporary DB and storage paths (section 9). OK.
8. Verification runnable — on the current tree: check OK; makemigrations no changes; `test` → `Ran 409 tests … OK`; `scripts/run_tests_at.py 2026-11-18T00:00:00` → 409 OK; deploy check exit 0 "(1 silenced)"; ruff check/format clean (105 files); YAML ok; `seed_demo` twice on a temporary DB → success. `ruff format --check --extend-exclude docs .` → 99 files formatted (AC0 works). OK.
9. Conflicts — none.
10. Assumptions / blockers — none.

## 8. Implementation order
Shell: repo root, `.venv` active, `export DEBUG=true`. Never open or edit `.env`. Never delete `db.sqlite3`.
1. AC0 (`pyproject.toml`); run ruff.
2. `core/storage.py`, `core/test_runner.py`, settings, `.env.example`, `.gitignore`; `core/tests/test_storage.py`; full suite still green.
3. App skeleton + models + `makemigrations petitions`; `migrate`.
4. `workflow.py`, `files.py`, `selectors.py`, `services.py` + `test_workflow.py`, `test_files.py`, `test_services.py`.
5. Forms, views, URLs, templates, nav + messages, CSS, admin + `test_views.py`, `test_downloads.py`.
6. `demo.py`, command, `test_demo.py`; README.
7. `ruff format` on changed files only; section 9; manual check at 360 px (student1: submit with a PDF, see status; staff1: take, comment, ready, issue; staff2 cannot see FDD requests). `REPORT` to the Reviewer. Do not commit.

## 9. Verification
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
export DATABASE_URL="sqlite:///$TMPDIR/task006.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task006-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
ls -R "$PRIVATE_MEDIA_ROOT" | head     # 3 files under request_attachments/xx/
git status --short                     # no private_media/, no db changes
```
In the `REPORT`: output tails, test count (was 409), query counts, and the `git status` output.

## 10. Risks
- **IDOR**: every lookup starts from `petitions_visible_to` / `attachments_visible_to`; the download view matches the petition **and** the file UUID.
- **File exposure**: a misconfigured nginx `location` serving `PRIVATE_MEDIA_ROOT` would bypass access checks — README warning; the directory is outside `static/` and `STATIC_ROOT`.
- **Spoofed PDFs**: signature check stops renamed binaries, not malicious PDFs (no antivirus — out of scope). Files are always downloaded (`attachment`), never rendered inline.
- **Orphan files**: files saved before a failing transaction are deleted in `submit_petition`; a crash between file save and commit can still leave an orphan (no cleanup job — acceptable for the prototype).
- **Concurrency**: correct on PostgreSQL via row locks; SQLite serializes writes.
- **Disk usage**: at most 3 open requests per type × 4 types × 3 files × 5 MB per student at a time; closed requests keep their files. Acceptable for the demo.
