# TASK-009-FIX: chat messages leak into the messages block, viewer-based alignment, one polling loop, seed skips real dialogs

Author: Planner. Status: ready for implementation.
Base commit: `bcd1280`. Related spec: `docs/tasks/TASK-009.md`. Screenshot: `docs/process/screenshots/2026-11-16_34_chat-dialog_staff1_bug.jpg`.

No new features. Each fix is minimal and has a regression test that fails without it; the visual part and the browser polling are checked by the Team lead.

---

## 1. Acceptance criteria
| ID | Criterion |
|---|---|
| AC1 | No view puts a variable named `messages` into a template context. The chat list is `chat_messages` in all chat views and templates (pages and fragment). The `.messages` block of `base.html` shows only `django.contrib.messages` messages, also on chat pages. The fragment output is unchanged. |
| AC2 | Each chat message has `chat-message--own` or `chat-message--other` by the VIEWER: for a student viewer, student messages are own; for a staff viewer, staff messages (any staff member) are own. Same in the polling fragment. CSS indents own messages on the left (they sit on the right) and other messages on the right. The `chat-message--<author_role>` class stays (labels/theme). |
| AC3 | `static/js/chat.js` runs at most one polling loop: `poll()` returns at once while a request is in flight, and `visibilitychange` starts a poll only when no timer is set and no request is in flight. All TASK-009 rules stay (no HTML-string APIs, error limit, pause while hidden). |
| AC4 | `seed_chat_demo` skips a demo student who already has a dialog (seeded or real): no new messages, no change to read markers or `last_message_*`. A fresh DB is seeded as before; a second run adds nothing. |

## 2. Out of scope
New features, the visual theme, room map v2 (TASK-010).

## 3. Files
Change only: `chat/views.py`, `chat/templates/chat/_messages.html`, `chat/templates/chat/_history.html`, `chat/templates/chat/_message.html`, `static/css/base.css`, `static/js/chat.js`, `chat/demo.py`; tests `chat/tests/test_views.py`, `chat/tests/test_static.py`, `chat/tests/test_demo.py`, `core/tests/test_css.py`. No models, migrations, settings or dependencies.

---

## 4. Fixes

### 4.1 Item 1 — context name `messages`
Sweep (done by the Planner on `bcd1280`, `grep` for `"messages":`, `messages = [`, `context["messages"]`, `in messages`, `messages %}` in all apps and `templates/`, tests excluded):
| Location | Verdict |
|---|---|
| `chat/views.py:40` (`_history_context`), `:55` (`_empty_history`), `:93-94`, `:129` (student fragment), `:175-176`, `:221` (staff fragment) | **fix** → `chat_messages` |
| `chat/templates/chat/_messages.html:1`, `_history.html:4`, `_history.html:6` | **fix** → `chat_messages` |
| `templates/base.html:33-35` | correct use of the `django.contrib.messages` context processor; unchanged |
| any other view/template | none found |

Rename only the context key and its template uses; keep local Python variable names if you like, but the dict key and every `context["…"]` lookup become `chat_messages`. Do not touch `exc.messages` (Django `ValidationError` attribute) or `messages_after` (service name) or `from django.contrib import messages`.

### 4.2 Item 2 — alignment by viewer
`chat/templates/chat/_message.html`, first line:
```django
<li class="chat-message chat-message--{{ m.author_role }} {% if m.author_role == 'student' and viewer_is_student or m.author_role == 'staff' and not viewer_is_student %}chat-message--own{% else %}chat-message--other{% endif %}" id="m-{{ m.pk }}" data-message-id="{{ m.pk }}">
```
(Django `{% if %}` evaluates `and` before `or`.) `viewer_is_student` is already passed by every view (`True` for the student page and student fragment, `False` for the staff page and staff fragment).
`static/css/base.css`: replace the two rules `.chat-message--staff { margin-right: … }` and `.chat-message--student { margin-left: … }` with
```css
.chat-message--own {
  margin-left: var(--space-4);
}

.chat-message--other {
  margin-right: var(--space-4);
}
```

### 4.3 Item 3 — one polling loop (`static/js/chat.js`)
- Add `var inFlight = false;` next to `timer`.
- `poll()`: first lines `if (inFlight || stopped) { return; } inFlight = true; timer = null;`. In the final `.then` (after the `.catch`): `inFlight = false; schedule();`.
- `schedule()`: `if (!stopped && !document.hidden && timer === null && !inFlight) { timer = setTimeout(poll, interval); }`.
- `visibilitychange`: hidden → `clearTimeout(timer); timer = null;`; visible → `if (!stopped && timer === null && !inFlight) { poll(); }`.
Why it is enough: the only two entry points (`setTimeout` callback and the visibility handler) now both pass through the same guard; a request that finishes while the tab is hidden does not schedule (hidden), and the next `visible` event starts exactly one poll.
Manual check for the Team lead (no JS test runner in the project): open the student chat with `runserver` output visible; switch tabs away and back 10 times quickly during polling; then leave the tab visible for 30 s → the server log shows at most one `GET /chat/updates/` per ~5 s (6–7 lines in 30 s), never bursts of parallel requests.

### 4.4 Item 4 — seed skips existing dialogs (`chat/demo.py`)
In `seed_chat_demo`, replace
```python
if Message.objects.filter(seed_key=first_key).exists():
    continue
student = students[student_username]
dialog, _ = Dialog.objects.get_or_create(student=student)
```
with
```python
student = students[student_username]
if Dialog.objects.filter(student=student).exists():
    continue  # seeded earlier or a real dialog: never add or change anything
dialog = Dialog.objects.create(student=student)
```
(`first_key` becomes unused; remove it.) Everything after stays.

---

## 5. Test plan

### 5.1 Rules
Existing world `_ChatWorld` / helpers (`make_world`, `make_dialog`, `add_message`); page assertions use exact markup or `response.context` (TASK-008-FIX rule). Save every test log; report any failed or stalled run by test name and Moscow time.

### 5.2 Traceability and regression evidence
| AC | Test (file::class::method) | Fails before fix because |
|---|---|---|
| AC1 | `chat/tests/test_views.py::ViewTests::test_student_page_has_no_messages_block_from_chat` | chat list rendered as `<ul class="messages">` |
| AC1 | `…::ViewTests::test_staff_dialog_has_no_messages_block_from_chat` | same |
| AC1 | `…::ViewTests::test_framework_message_shown_on_chat_pages` | view context `messages` hides the framework messages |
| AC1 | `…::ViewTests::test_staff_real_framework_message_after_unpublish` | same, through a real flow |
| AC1 | `…::UpdatesViewTests::test_fragment_markup_unchanged` | (guard) |
| AC1 | `…::ViewTests::test_context_uses_chat_messages` | key `chat_messages` missing |
| AC2 | `…::ViewTests::test_alignment_student_viewer`, `test_alignment_staff_viewer`, `UpdatesViewTests::test_fragment_alignment_by_viewer` | classes depend on the author, not the viewer |
| AC2 | `core/tests/test_css.py::BaseCssTests::test_chat_alignment_rules` | rules missing |
| AC3 | `chat/tests/test_static.py::ChatJsTests::test_single_loop_guard` | no `inFlight` |
| AC3 | manual check 4.3; `node --check` | — |
| AC4 | `chat/tests/test_demo.py::ChatSeedTests::test_existing_real_dialog_untouched` | seed adds 4 older messages and rewrites markers |
| AC4 | existing `test_dialogs_and_messages`, `test_idempotent` | (guards) |

### 5.3 Test details
- `test_student_page_has_no_messages_block_from_chat`: `ax` has 3 messages (student, staff, student via `add_message`); GET `/chat/` as `ax` → `'<ul class="messages">' not in content` (no framework messages are queued) and each `data-message-id="<pk>"` appears exactly once.
- `test_staff_dialog_has_no_messages_block_from_chat`: same on `/staff/chats/<ax uuid>/` as `sx`.
- `test_framework_message_shown_on_chat_pages`: `with mock.patch("django.contrib.messages.context_processors.get_messages", return_value=[Message(constants.INFO, "Проверочное сообщение")]):` (`Message` from `django.contrib.messages.storage.base`, `constants` from `django.contrib.messages`) GET `/chat/` as `ax` and `/staff/chats/<ax uuid>/` as `sx` → each contains `<li class="message message--info">Проверочное сообщение</li>`.
- `test_staff_real_framework_message_after_unpublish`: as `sx`, create an FX faculty announcement (`notifications/tests/helpers.py::make_announcement`), POST `notifications:staff_unpublish` (302, not followed), then GET `/staff/chats/<ax uuid>/` → contains `Объявление снято с публикации.` inside `<ul class="messages">`.
- `test_context_uses_chat_messages`: GET `/chat/` → `"chat_messages" in response.context` and `[m.pk for m in response.context["chat_messages"]]` equals the dialog's message ids; the context value `messages` is NOT a list of `chat.Message` (it is the framework storage).
- `test_fragment_markup_unchanged`: GET `/chat/updates/?after=0` as `ax` → 200, `X-Chat-Fragment: 1`, body contains one `<li class="chat-message` per message and no `<ul class="messages">`.
- `test_alignment_student_viewer`: `ax` page → the student message `<li>` has classes `chat-message--student chat-message--own`; the staff message has `chat-message--staff chat-message--other`.
- `test_alignment_staff_viewer`: `sx` dialog page → the student message `chat-message--student chat-message--other`; the staff message (written by another FX staff member, to prove "any staff member") `chat-message--staff chat-message--own`.
- `test_fragment_alignment_by_viewer`: student fragment and staff fragment for the same new staff message → `--own` for staff, `--other` for the student.
  (Assert with exact substrings of the form `id="m-<pk>"` plus the class string, e.g. `f'class="chat-message chat-message--staff chat-message--own" id="m-{pk}"'`.)
- `test_chat_alignment_rules` (`core/tests/test_css.py`): `base.css` matches `r"\.chat-message--own\s*\{\s*margin-left:"` and `r"\.chat-message--other\s*\{\s*margin-right:"`; does not contain `.chat-message--student {` or `.chat-message--staff {`.
- `test_single_loop_guard` (`chat/tests/test_static.py`): `chat.js` contains `var inFlight = false;`, `if (inFlight || stopped)`, and the visibility branch contains `!inFlight`; existing forbidden/required API tests keep passing.
- `test_existing_real_dialog_untouched` (`ChatSeedTests`, frozen `2026-11-22 12:00`): run `seed_demo` once; delete student1's seeded messages and dialog (messages first: `Message.dialog` is `PROTECT`); create a real dialog for student1 with one `add_message(..., text="Реальный вопрос")` and record `(message ids, student_read_id, staff_read_id, last_message_id, last_message_at)`; run `seed_demo` again → the dialog has exactly that one message and the same markers; output contains `Chat ready: 0 dialogs, 0 messages.`; student2/student3 dialogs unchanged.

### 5.4 Access matrix
No access rules change; `AccessTests` (TASK-009) must keep passing.

### 5.5 Query count
No query changes; `QueryCountTests` (TASK-009) must keep passing.

---

## 6. Implementation order
1. Regression tests in 5.2 (confirm the "fails before fix" ones fail).
2. Fixes 4.1–4.4.
3. `ruff format` on changed Python files only; section 7; `REPORT` to the Reviewer with the regression evidence. Do not commit.

## 7. Verification
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
node --check static/js/chat.js && echo "js syntax ok"
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
export DATABASE_URL="sqlite:///$TMPDIR/task009fix.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task009fix-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
rm -f "$TMPDIR/task009fix.sqlite3"
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
git status --short
```
`REPORT`: output tails, test count (was 951), log file names, any failed or stalled run by test name and Moscow time, `git status`.

## 8. Feasibility check (2026-11-16 01:22 MSK on `bcd1280`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — `chat/views.py` keys `"messages"` at lines 40, 55, 93-94, 129, 175-176, 221; `_history_context`, `_empty_history` both set `viewer_is_student`; templates `_messages.html:1`, `_history.html:4,6`, `_message.html:1` (class from `author_role` only); `base.html:33-35` framework loop; CSS rules `.chat-message--staff` / `.chat-message--student` (`base.css` ≈384-390); `chat.js` (`timer`, `schedule`, `poll`, `visibilitychange` handler with `timer === null`); `seed_chat_demo` (`first_key` skip + `get_or_create`); test classes `ViewTests`, `UpdatesViewTests`, `ChatJsTests`, `ChatSeedTests` and helpers `make_world`, `make_dialog`, `add_message`; `django.contrib.messages.context_processors.get_messages` (imported name used by the `messages` processor); `notifications:staff_unpublish` adds «Объявление снято с публикации.». OK.
3. No collisions — no `chat_messages` key, no CSS classes `chat-message--own/--other`, no `inFlight` in `chat.js`, no new test names. OK.
4. Migrations — none. 5. Tools — unchanged; `node` v26.13.0 for `--check`. 6. Framework — a view context key overrides the context-processor key of the same name (context processors are applied under the view context), which is exactly the bug; patching `get_messages` in `django.contrib.messages.context_processors` controls what the processor returns. OK. 7. Environment — nothing new. 8. Verification runnable — 8a. 9. Conflicts — none. 10. Assumptions / blockers — none.

### 8a. Verification results on the current tree
Logs `$TMPDIR/test-20261116-012259-t009fix-feas*.log` (started 2026-11-16 01:22 MSK).
- `check` → no issues; `makemigrations --check --dry-run` → «No changes detected».
- `test` → `Ran 951 tests … OK`; `run_tests_at.py 2026-11-17T23:59:59` → 951 OK; `run_tests_at.py 2026-11-18T00:00:00` → 951 OK. No failed or stalled runs.
- `check --deploy --fail-level WARNING` → no issues (1 silenced); `ruff check .` → all passed; `ruff format --check .` → 183 files already formatted; `node --check static/js/chat.js` → ok; CI YAML ok.
- `seed_demo` twice on a temporary DB and PRIVATE_MEDIA_ROOT → OK («Chat ready: 3 dialogs, 8 messages.», then «Chat ready: 0 dialogs, 0 messages.»).

## 9. Risks
- Renaming a context key in one place but not another would silently render an empty history; the tests count rendered `data-message-id` items on both pages and in the fragment.
- The JS guard cannot be unit-tested here; the static test + `node --check` + the manual check in 4.3 cover it.
