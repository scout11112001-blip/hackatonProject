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
