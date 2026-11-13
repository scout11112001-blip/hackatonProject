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
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
```

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

## Schedule

Students: `/schedule/` (today) and `/schedule/week/` (week view). Staff:
`/staff/schedule/` (group list). Schedule editing happens in Django admin.

## Login protection

Failed login attempts are throttled per (username, client IP) and stored in
the database (`LOGIN_FAILURE_LIMIT` failures → lockout for
`LOGIN_LOCKOUT_SECONDS` seconds). Behind a reverse proxy, set
`CLIENT_IP_HEADER=X-Real-IP` **only** if nginx overwrites the header, e.g.:

```nginx
proxy_set_header X-Real-IP $remote_addr;
```

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
