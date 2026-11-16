# Digital Dean's Office of the Future

A minimal Django skeleton for the "Digital Dean's Office of the Future" prototype.

> Concept for the MGIMO AI Challenge contest. This is not an official university
> service. All data is fictional.

## Requirements

- Python 3.12

## Setup

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then edit as needed
```

## Run

```bash
python manage.py migrate
python manage.py runserver
```

## Test & lint

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python scripts/run_tests_at.py 2027-03-01T12:00:00   # tests must not depend on the real date
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
```

- Assertions on whole pages: use exact markup (e.g. `href="/staff/schedule/12/"`) or
  `response.context`; never a short alphanumeric needle — the page contains a
  random CSRF token.

## Demo data

```bash
python manage.py migrate
python manage.py seed_demo   # needs DEMO_PASSWORD in .env or the environment
```

All demo data is fictional. Logins (password: the value of `DEMO_PASSWORD`):

| Login | Faculty | Group |
|---|---|---|
| `student1` | FDD | ЦД-101 |
| `student2` | FAE | ЭД-201 |
| `student3` | FDD | ЦД-101 |
| `staff1` | FDD | — |
| `staff2` | FAE | — |

Superuser (Django admin only): `python manage.py createsuperuser`.

The demo schedule covers 8 weeks before and 12 weeks after the run date.
Re-running `seed_demo` replaces the demo schedule changes with fresh ones for
the current and next week. Demo schedule rows carry a `seed_key`; rows created
by a person in Django admin are never touched by `seed_demo`.

Demo academics: `student1` is strong (average 5.00, no debts); `student3` has a
retake and an open debt («Основы права») and low attendance; `student2` is from
the other faculty (average 4.50). The seed only creates missing academic rows.

Demo requests: `student1` has a submitted certificate and issued/processing
requests; `student3` has a ready and a rejected request; `student2` has a
submitted and an in-progress request. Each staff faculty has at least one
request waiting in its queue.

## Schedule

Students: `/schedule/` (today) and `/schedule/week/` (week view). Staff:
`/staff/schedule/` (group list). Schedule editing happens in Django admin.

## Grades

Students: `/grades/` and `/grades/<term_code>/`. Staff open a student's report
from the student card (`/staff/students/<pk>/grades/`). Definitions: the
average is the arithmetic mean of numeric effective results (2–5, including 2),
rounded to 2 decimals half-up; a debt is a finished-session curriculum item
with a missing or failing effective result; attendance percent is
present/(present+absent), rounded half-up, with excused absences excluded and
shown as «не отмечено» when a past occurrence has no record.

## Requests

Students: `/requests/` (my requests), `/requests/new/` (catalog) and a
per-request detail with history and downloads. Staff: `/staff/requests/` (queue,
own faculty, filtered by status/type, open oldest first) and per-request actions
(take in progress, mark ready, mark issued, reject) and staff comments.

Status workflow:

| Status | Allowed transitions |
|---|---|
| Подана (submitted) | В работе, Отклонена |
| В работе (in_progress) | Готова, Отклонена |
| Готова (ready) | Выдана |
| Выдана (issued) | — |
| Отклонена (rejected) | — |

Limits: at most 3 open requests of the same type per student; up to 3
attachments, each ≤ 5 MB, PDF only (extension, content type and `%PDF-`
signature are all checked). Attachments are stored in `PRIVATE_MEDIA_ROOT`,
which must **never** be served by nginx or live inside `static/`; downloads go
through Django access checks only. nginx should allow larger request bodies for
multipart uploads:

```nginx
client_max_body_size 20m;
```

## Notifications

Students: `/notifications/` shows a «Ближайшие дедлайны» block (deadlines
today or later, nearest first, labelled «сегодня» / «завтра» / «через N
дней») and one feed of dean's-office news and personal changes (request status
changes and staff comments, schedule changes for lessons in the next 14 days,
new current marks and final results). The feed is computed from existing rows,
covers the last 30 days, and is capped at 50 items.

Unread state is one «seen until» timestamp per account (no per-item flags):
the nav shows «Уведомления (N)» for students, and opening `/notifications/`
marks everything as read.

Staff: `/staff/announcements/` lists and creates announcements for the staff
member's own faculty or one of its groups (no edit, no hard delete; an
announcement can be unpublished). University-wide announcements are created
only in the Django admin.

Demo data: `seed_demo` creates 9 announcements (2 university-wide, 5 faculty, 2
group; 2 unpublished); published deadlines fall on run day +1…+5.

## Map

Students and staff: `/map/` (lowest floor with rooms), `/map/floor/<n>/`
(a specific floor, 404 when no room is on it) and `/map/room/<code>/` (a room's
floor with that room highlighted). The map is one fictional building drawn as an
inline SVG with portrait floor plans for floors 1–4 in `university/building.py`.
Each floor has a vertical corridor in the middle, rooms of different sizes on
both sides, and service spaces (no free space except the corridor). Two L-shaped
spaces are drawn as `<polygon>`: the canteen «Столовая» (floor 1) and room 210
(floor 2).

A room appears on the plan when its number is a slot on its floor's plan (no
admin placement; to add a room to the plan, change the code). Rooms elsewhere
(or floors 5–9, which have no plan) show «нет на схеме». Non-teaching spaces —
landmarks («Лестница», «Вход», «Столовая», «Деканат», «Библиотека») and
services («Гардероб», «Туалеты», «Кафедра», «Медпункт», «Склад», «Охрана»,
«Архив») — are drawn always; the legend explains the three kinds. A room number
is exactly three digits (`NNN`) and its first digit must equal the floor (1–9).
The highlighted room uses the single CSS class `map-current` (colour token
`--color-map-highlight`).

## Chat

Students write to the dean's office of their faculty in one dialog (`/chat/`),
created on their first message. Any staff member of that faculty reads and
answers from «Чаты» (`/staff/chats/`). Messages are append-only plain text
(autoescaped, `linebreaksbr`), ordered by message id. Without JavaScript the
pages work with a plain POST form and an «Обновить» link; with JavaScript
(`static/js/chat.js`, deferred, no inline script) the page polls the fragment
view every 5 seconds and appends server-rendered new messages, pausing while the
tab is hidden. Sending is a normal POST (PRG, no `fetch`). Student rate limit:
`RATE_LIMIT_MESSAGES` (20) per `RATE_LIMIT_MINUTES` (10). A hidden `client_token`
guards against double submit. New staff replies appear in «Уведомления»
(source `chat_reply`) and in the badge; the nav item shows «Чат (N)». Read
markers are message ids on the dialog (student marker, shared staff marker);
both only move forward.

## Login protection

Failed login attempts are throttled per (username, client IP) and stored in
the database (`LOGIN_FAILURE_LIMIT` failures → lockout for
`LOGIN_LOCKOUT_SECONDS` seconds). Behind a reverse proxy, set
`CLIENT_IP_HEADER=X-Real-IP` **only** if nginx overwrites the header, e.g.:

```nginx
proxy_set_header X-Real-IP $remote_addr;
```

## Deployment notes

- Run `python manage.py seed_demo` once on the server on 2026-11-22 (submission
  day), after `migrate`. It needs `DEMO_PASSWORD` in the environment.
- Back up `PRIVATE_MEDIA_ROOT` together with the database: attachments are
  referenced by database rows, so restoring one without the other breaks
  downloads.
- nginx must not serve `PRIVATE_MEDIA_ROOT`; set `client_max_body_size 20m;`
  (see the «Requests» section).

## Known limitations

- After a student moves to another group, attendance for the former group's
  lessons is not shown (group transfers are out of scope for the prototype).
- `seed_demo` never updates existing academic rows, so data edited in the admin
  is never overwritten. Re-running it only adds missing rows (new past
  occurrences). On the server it is run once, on 2026-11-22 (submission day);
  there is no scheduled re-run.
- The unread counter is per account: after one person opens «Уведомления» as
  `student1`, others logged in as `student1` see no new items.
- Grades and lesson changes appear in the feed by the time they were recorded;
  a grade entered later for an old date still shows as new.
- Plans exist for floors 1–4 only; a room is drawn only if its number is a slot
  in `university/building.py`.
- Chat uses polling (5-second requests, paused on a hidden tab), not WebSockets,
  so delivery is not instantaneous; the last five consecutive poll errors stop
  auto-refresh with a text notice.

## Environment variables

| Name | Default | Purpose |
|---|---|---|
| `DEBUG` | `false` | Enable debug mode in development. |
| `SECRET_KEY` | (dev key in debug) | Django secret key; required when `DEBUG=false`. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` (debug) | Comma-separated allowed hostnames. |
| `CSRF_TRUSTED_ORIGINS` | (empty) | Comma-separated trusted origins. |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | Database URL (SQLite or PostgreSQL). |
| `ADMIN_URL` | `admin/` (debug) | Admin path prefix; required when `DEBUG=false`. |
| `SECURE_SSL_REDIRECT` | `true` | Redirect HTTP to HTTPS (production only). |
| `SECURE_HSTS_SECONDS` | `3600` | HSTS max-age (production only). |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `true` | Apply HSTS to subdomains (production only). |
| `SECURE_HSTS_PRELOAD` | `false` | Opt in to HSTS preload (production only). |
| `LOG_LEVEL` | `INFO` | Logging level. |
| `DEMO_PASSWORD` | (none) | Password for demo accounts; required by `seed_demo`. |
| `LOGIN_FAILURE_LIMIT` | `5` | Failures per (username, IP) before login lockout. |
| `LOGIN_LOCKOUT_SECONDS` | `900` | Login lockout duration in seconds. |
| `CLIENT_IP_HEADER` | (empty) | Proxy header for the client IP (`X-Real-IP` or `X-Forwarded-For`). |
| `PRIVATE_MEDIA_ROOT` | `<repo>/private_media` | Private uploads (request attachments); never served by nginx. |
