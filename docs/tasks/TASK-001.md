# TASK-001: Django project skeleton + CI

Author: Planner. Status: ready for implementation.
Product context: `plan.md` (Russian). Team protocol: `.bb/AGENTS.md`.

---

## 1. Goal

Create a minimal, production-sane Django 5.2 LTS skeleton for the "Digital Dean's Office of the Future" prototype. All later tasks build on it. No domain features.

## 2. Acceptance criteria

All must be true:

1. `.venv/` exists, created with `/opt/homebrew/bin/python3.12`; `pip install -r requirements-dev.txt` succeeds.
2. With `DEBUG=true` in the environment:
   - `python manage.py check` → `System check identified no issues (0 silenced).`
   - `python manage.py makemigrations --check --dry-run` → `No changes detected`, exit code 0.
   - `python manage.py test` → all tests pass (at least the tests listed in section 6).
3. With `DEBUG=false SECRET_KEY=<50+ char dummy> ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/`:
   `python manage.py check --deploy --fail-level WARNING` → exit code 0. The only silenced check is `security.W021` (justified in section 5.3).
4. With `DEBUG=false` and no `SECRET_KEY`: any `manage.py` command fails immediately with `django.core.exceptions.ImproperlyConfigured` whose message mentions `SECRET_KEY`.
5. `ruff check .` and `ruff format --check .` → no errors.
6. `.github/workflows/ci.yml` is valid YAML and runs the same commands as items 2, 3 and 5.
7. `GET /` → 200, HTML page with `lang="ru"`, viewport meta, header, nav placeholder, main content, footer disclaimer (exact text in 5.6).
8. `GET /health/` → 200, `Content-Type: application/json`, body exactly `{"status": "ok"}`.
9. Admin is reachable at `/<ADMIN_URL>`; default `admin/` only when `DEBUG=true`.
10. No external URLs (CDNs, fonts) in templates or CSS.
11. `.env` is not read, printed or modified by any agent. `.env.example` lists every variable with safe placeholders.
12. Manual: `/` at 360 px width has no horizontal scroll.

## 3. Out of scope

- Domain models, custom user model, authentication UI, roles, permissions.
- Docker, gunicorn, nginx config, deployment scripts.
- Creating the GitHub repository or pushing.
- Pixel-art styling, fonts, icons, logo.
- REST API / JSON endpoints (except `/health/`).
- Committing to git (the Team lead decides when to commit).

---

## 4. Dependencies (exact pins)

Checked on PyPI on 2026-11-11.

`requirements.txt` (runtime):
```
Django==5.2.19
django-environ==0.14.0
whitenoise==6.12.0
psycopg[binary]==3.3.8
```

`requirements-dev.txt`:
```
-r requirements.txt
ruff==0.17.4
PyYAML==6.0.3
```

Only top-level packages are pinned. Do not add other packages. If a pin fails to install, send a `QUESTION` to the Planner — do not pick another version yourself.

**Why django-environ** (the only env helper): it reads environment variables with typed casting (`bool`, `list`, `int`), reads an optional `.env` file without overriding real environment variables, and parses `DATABASE_URL` into Django's `DATABASES` dict for both SQLite and PostgreSQL. `python-decouple` would need a second library (`dj-database-url`) for `DATABASE_URL`; `pydantic-settings` is heavier and not Django-specific.

PyYAML is dev-only, used to validate the CI workflow syntax locally.

---

## 5. Architecture

### 5.1 File tree (create exactly these; do not run `startapp`)

```
manage.py
config/__init__.py            (empty)
config/settings.py
config/env_utils.py           (pure helper functions, see section 6)
config/urls.py
config/wsgi.py
config/asgi.py
core/__init__.py              (empty)
core/apps.py
core/urls.py
core/views.py
core/templates/core/home.html
core/tests/__init__.py        (empty)
core/tests/test_env_utils.py
core/tests/test_views.py
core/tests/test_settings.py
templates/base.html
static/css/tokens.css
static/css/base.css
static/css/theme.css
requirements.txt
requirements-dev.txt
pyproject.toml
.env.example
README.md
.github/workflows/ci.yml
```

`core` has no `models.py`, no `admin.py`, no `migrations/`. Do not change `.gitignore` (it already ignores `.venv/`, `db.sqlite3`, `/staticfiles/`, `.env`).

`manage.py`, `config/wsgi.py`, `config/asgi.py`: standard Django 5.2 `startproject` content with `DJANGO_SETTINGS_MODULE` = `"config.settings"`.

`core/apps.py`:
```python
class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
```

### 5.2 `config/settings.py` — exact structure

Write the settings in this order. Use `environ.Env()` from django-environ. All names below are module-level settings.

1. **Paths and env loading**
   ```python
   BASE_DIR = Path(__file__).resolve().parent.parent
   env = environ.Env()
   _env_file = BASE_DIR / ".env"
   if _env_file.is_file():
       environ.Env.read_env(_env_file)  # overwrite=False (default): real env vars win
   ```
   Never log, print or iterate over the loaded values.

2. **Core flags**
   - `DEBUG = env.bool("DEBUG", default=False)`
   - `SECRET_KEY = resolve_secret_key(env.str("SECRET_KEY", default=""), DEBUG)` (from `config.env_utils`)
   - `ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"] if DEBUG else [])`
   - `CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])`
   - `ADMIN_URL = resolve_admin_url(env.str("ADMIN_URL", default=""), DEBUG)`

3. **Apps** (this order):
   ```
   "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
   "django.contrib.sessions", "django.contrib.messages",
   "whitenoise.runserver_nostatic", "django.contrib.staticfiles",
   "core",
   ```

4. **Middleware** (this order; WhiteNoise right after SecurityMiddleware):
   ```
   "django.middleware.security.SecurityMiddleware",
   "whitenoise.middleware.WhiteNoiseMiddleware",
   "django.contrib.sessions.middleware.SessionMiddleware",
   "django.middleware.common.CommonMiddleware",
   "django.middleware.csrf.CsrfViewMiddleware",
   "django.contrib.auth.middleware.AuthenticationMiddleware",
   "django.contrib.messages.middleware.MessageMiddleware",
   "django.middleware.clickjacking.XFrameOptionsMiddleware",
   ```
   Do not add `LocaleMiddleware` (single language).

5. `ROOT_URLCONF = "config.urls"`, `WSGI_APPLICATION = "config.wsgi.application"`, `ASGI_APPLICATION = "config.asgi.application"`.

6. **Templates**: one `DjangoTemplates` backend, `DIRS=[BASE_DIR / "templates"]`, `APP_DIRS=True`, context processors: `debug`, `request`, `auth`, `messages` (the Django 5.2 `startproject` defaults).

7. **Database**
   ```python
   DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
   ```
   PostgreSQL example: `DATABASE_URL=postgres://user:password@localhost:5432/deanery`. No other DB code.
   `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`.

8. **Passwords**: `PASSWORD_HASHERS` not set (Django default). `AUTH_PASSWORD_VALIDATORS` = all four Django defaults (`UserAttributeSimilarityValidator`, `MinimumLengthValidator`, `CommonPasswordValidator`, `NumericPasswordValidator`) with default options.

9. **I18N**: `LANGUAGE_CODE = "ru"`, `TIME_ZONE = "Europe/Moscow"`, `USE_I18N = True`, `USE_TZ = True`.

10. **Static files**
    ```python
    STATIC_URL = "static/"
    STATICFILES_DIRS = [BASE_DIR / "static"]
    STATIC_ROOT = BASE_DIR / "staticfiles"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": (
                "django.contrib.staticfiles.storage.StaticFilesStorage"
                if DEBUG
                else "whitenoise.storage.CompressedManifestStaticFilesStorage"
            )
        },
    }
    ```
    Reason for the switch: the manifest storage raises an error for `{% static %}` until `collectstatic` has run; development and tests run with `DEBUG=true` and do not run `collectstatic`.

11. **Security** (always set):
    - `X_FRAME_OPTIONS = "DENY"`
    - `SECURE_CONTENT_TYPE_NOSNIFF = True`
    - `SECURE_REFERRER_POLICY = "same-origin"`
    - `SESSION_COOKIE_HTTPONLY = True`

    **Only `if not DEBUG:`**
    - `SESSION_COOKIE_SECURE = True`
    - `CSRF_COOKIE_SECURE = True`
    - `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
    - `SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)`
    - `SECURE_REDIRECT_EXEMPT = [r"^health/$"]` (local monitoring may call gunicorn over plain HTTP)
    - `SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)`
    - `SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)`
    - `SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)`

12. **Silenced checks**
    ```python
    # security.W021: HSTS preload is an irreversible browser-list commitment.
    # A contest prototype must not opt in. Enable via SECURE_HSTS_PRELOAD only deliberately.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]
    ```

13. **Logging** (console only):
    ```python
    LOG_LEVEL = env.str("LOG_LEVEL", default="INFO").upper()
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"simple": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
        "root": {"handlers": ["console"], "level": LOG_LEVEL},
        "loggers": {"django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False}},
    }
    ```
    Do not configure `django.db.backends` at DEBUG level (it logs SQL parameters). Do not log settings or environment values anywhere.

### 5.3 `check --deploy` result (expected)

With the CI production-like env, every deploy check passes except `security.W021` (HSTS preload), which is silenced in settings with the justification above. No other check may be silenced.

### 5.4 URLs

`config/urls.py`:
```python
urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("core.urls")),
]
```

`core/urls.py`:
```python
app_name = "core"
urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("health/", views.health, name="health"),
]
```

### 5.5 Views (`core/views.py`) — see section 6 for details

- `HomeView(TemplateView)`, `template_name = "core/home.html"`.
- `health(request)` function view.

### 5.6 Templates

`templates/base.html` — exact structure (Russian UI text):
```html
{% load static %}<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Цифровой деканат будущего{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'css/tokens.css' %}">
  <link rel="stylesheet" href="{% static 'css/base.css' %}">
  <link rel="stylesheet" href="{% static 'css/theme.css' %}">
  {% block extra_head %}{% endblock %}
</head>
<body>
  <a class="skip-link" href="#main">Перейти к содержимому</a>
  <header class="site-header">
    <a class="site-title" href="{% url 'core:home' %}">Цифровой деканат будущего</a>
    <nav class="site-nav" aria-label="Основная навигация">{% block nav %}{% endblock %}</nav>
  </header>
  <main id="main" class="site-main">
    {% block content %}{% endblock %}
  </main>
  <footer class="site-footer">
    <p class="site-disclaimer">Концепт для конкурса MGIMO AI Challenge. Не является официальным сервисом вуза. Все данные вымышлены.</p>
  </footer>
</body>
</html>
```
CSS order is fixed: tokens → base → theme.

`core/templates/core/home.html`:
```html
{% extends "base.html" %}
{% block content %}
  <h1>Цифровой деканат будущего</h1>
  <p>Прототип личного кабинета студента. Раздел в разработке.</p>
{% endblock %}
```

### 5.7 CSS layer contract

- `static/css/tokens.css`: only a `:root { ... }` block with custom properties. No selectors other than `:root`. Required tokens:
  `--color-bg`, `--color-text`, `--color-muted`, `--color-accent`, `--color-border`,
  `--font-body` (system font stack), `--font-heading` (same stack for now),
  `--font-size-base` (`1rem`), `--line-height-base` (`1.5`),
  `--space-1` (`0.25rem`), `--space-2` (`0.5rem`), `--space-3` (`1rem`), `--space-4` (`1.5rem`), `--space-5` (`2rem`),
  `--content-max-width` (`60rem`), `--radius` (`0`).
  Use neutral values (e.g. white bg, near-black text).
- `static/css/base.css`: mobile-first layout only. Every color, font, spacing value comes from `var(--...)`; no literal colors. Must include:
  - `*, *::before, *::after { box-sizing: border-box; }`
  - `body { margin: 0; font-family: var(--font-body); ... background: var(--color-bg); color: var(--color-text); }`
  - `img, svg { max-width: 100%; height: auto; }`
  - `body { overflow-wrap: anywhere; }` (long words must not cause horizontal scroll)
  - `.site-header`, `.site-main`, `.site-footer`: padding `var(--space-3)`; `.site-main` has `max-width: var(--content-max-width); margin-inline: auto;`
  - `.skip-link`: visually hidden until `:focus`.
  - One `@media (min-width: 48rem)` block for wider padding. No fixed widths in px above 360.
- `static/css/theme.css`: only a comment: `/* Visual theme layer. The pixel-art skin replaces this file and tokens.css. */`

No `@import`, no `url(http...)`, no external fonts.

### 5.8 `.env.example`

Exact content:
```
# Copy to .env and edit. Never commit .env.
# Development defaults. For production set DEBUG=false and real values.
DEBUG=true
SECRET_KEY=change-me-to-a-long-random-string-of-at-least-50-characters
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=
# SQLite (default if unset). PostgreSQL example:
# DATABASE_URL=postgres://deanery:change-me@localhost:5432/deanery
DATABASE_URL=sqlite:///db.sqlite3
# Required when DEBUG=false. Use a non-obvious path, must end with "/".
ADMIN_URL=admin/
# Production only (ignored when DEBUG=true)
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=3600
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=false
LOG_LEVEL=INFO
```
Note: `sqlite:///db.sqlite3` is relative to the working directory; this is fine because commands run from the repo root.

### 5.9 `pyproject.toml`

Only ruff config (no `[project]` table):
```toml
[tool.ruff]
target-version = "py312"
line-length = 100
extend-exclude = ["*/migrations/*", ".venv", "staticfiles"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "DJ", "S"]
ignore = []

[tool.ruff.lint.per-file-ignores]
"*/tests/*" = ["S101", "S105", "S106"]
"config/env_utils.py" = ["S105"]

[tool.ruff.lint.isort]
known-first-party = ["config", "core"]

[tool.ruff.format]
quote-style = "double"
```
If a rule in `select` produces a finding you believe is a false positive, do not add ignores yourself: send a `QUESTION`.

### 5.10 `.github/workflows/ci.yml`

Exact content:
```yaml
name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      DEBUG: "true"
      SECRET_KEY: "ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: |
            requirements.txt
            requirements-dev.txt
      - name: Install dependencies
        run: python -m pip install -r requirements-dev.txt
      - name: Ruff lint
        run: ruff check .
      - name: Ruff format
        run: ruff format --check .
      - name: Django check
        run: python manage.py check
      - name: Missing migrations
        run: python manage.py makemigrations --check --dry-run
      - name: Tests
        run: python manage.py test
      - name: Deploy check (production-like env)
        env:
          DEBUG: "false"
          ALLOWED_HOSTS: "example.com"
          ADMIN_URL: "ci-staff-panel/"
        run: python manage.py check --deploy --fail-level WARNING
```
All values are dummies. No `secrets.*`.

### 5.11 `README.md` (English, short)

Sections: title + one-line description + disclaimer (fictional data, contest concept); Requirements (Python 3.12); Setup (`/opt/homebrew/bin/python3.12 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements-dev.txt`, `cp .env.example .env` then edit); Run (`python manage.py migrate`, `python manage.py runserver`); Test & lint (the commands of section 8); Environment variables (table: name, default, purpose — from 5.8).

---

## 6. Functions

### 6.1 `config/env_utils.py`

Module constant:
```python
DEV_SECRET_KEY = "django-insecure-dev-only-key-do-not-use-in-production"
```
Imports: only `re` and `django.core.exceptions.ImproperlyConfigured`. Must not import `django.conf.settings`.

#### `resolve_secret_key(raw: str, debug: bool) -> str`
- Purpose: return the secret key, failing fast in production when it is missing.
- Inputs: `raw` — value of `SECRET_KEY` env var (`""` when unset); `debug` — the DEBUG flag.
- Output: the key string.
- Raises: `ImproperlyConfigured("SECRET_KEY environment variable is required when DEBUG is false.")`.
- Algorithm:
  1. `value = raw.strip()`.
  2. If `value` → return `value`.
  3. If `debug` → return `DEV_SECRET_KEY`.
  4. Else raise the error above.
- Edge cases: whitespace-only → treated as missing. Never include `raw` in any message.
- Caller: `config/settings.py` only.
- Tests (`core/tests/test_env_utils.py`, `SimpleTestCase`):
  - `test_returns_given_key` (debug False, `"abc..."` → same).
  - `test_strips_whitespace` (`"  key  "` → `"key"`).
  - `test_dev_fallback_when_debug` (`""`, True → `DEV_SECRET_KEY`).
  - `test_missing_key_in_production_raises` (`""`, False → raises, message contains `"SECRET_KEY"`).
  - `test_whitespace_key_in_production_raises` (`"   "`, False → raises).

#### `resolve_admin_url(raw: str, debug: bool) -> str`
- Purpose: return a validated URL prefix for Django admin, e.g. `"staff-panel/"`.
- Inputs: `raw` — value of `ADMIN_URL` env var (`""` when unset); `debug`.
- Output: path segment(s) without leading slash, with exactly one trailing slash.
- Raises: `ImproperlyConfigured` with a message that mentions `ADMIN_URL`.
- Algorithm:
  1. `value = raw.strip().strip("/")`.
  2. If `value == ""`: if `debug` → return `"admin/"`; else raise `ImproperlyConfigured("ADMIN_URL environment variable is required when DEBUG is false.")`.
  3. If not `re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", value)` → raise `ImproperlyConfigured("ADMIN_URL may contain only letters, digits, '-', '_' and '/'.")`.
  4. Return `value + "/"`.
- Edge cases: `"/staff/"` → `"staff/"`; `"staff"` → `"staff/"`; `"a//b"` → raises; `"../x"` → raises; `"admin/"` with debug False → allowed (operator's choice).
- Caller: `config/settings.py` only.
- Tests:
  - `test_default_in_debug` (`""`, True → `"admin/"`).
  - `test_missing_in_production_raises` (`""`, False → raises, message contains `"ADMIN_URL"`).
  - `test_adds_trailing_slash` (`"staff"` → `"staff/"`).
  - `test_strips_slashes_and_spaces` (`" /staff/ "` → `"staff/"`).
  - `test_nested_path_allowed` (`"x/staff"` → `"x/staff/"`).
  - `test_invalid_characters_raise` — subTests for `"a//b"`, `"../x"`, `"st aff"`, `"staff?x=1"`.

### 6.2 `core/views.py`

#### `class HomeView(TemplateView)`
- Purpose: placeholder home page.
- `template_name = "core/home.html"`. No other code.
- Access: public.
- Tests (`core/tests/test_views.py`, `TestCase`):
  - `test_home_status_and_templates`: `GET reverse("core:home")` → 200; `assertTemplateUsed` for `"core/home.html"` and `"base.html"`.
  - `test_home_base_layout`: response contains `lang="ru"`, `name="viewport"`, `<header`, `<nav`, `<main`, `<footer`, and the exact disclaimer text from 5.6.
  - `test_home_css_layers_in_order`: positions of `css/tokens.css` < `css/base.css` < `css/theme.css` in the content.
  - `test_home_has_no_external_resources`: content does not contain `"http://"` or `"https://"`.

#### `def health(request: HttpRequest) -> JsonResponse`
- Purpose: liveness check for server monitoring.
- Decorators (outermost first): `@never_cache`, `@require_GET`.
- Algorithm: return `JsonResponse({"status": "ok"})`. No DB access, no other data (no version, no hostnames, no settings).
- `require_GET` allows only `GET`; every other method (including `HEAD`, `POST`) → 405.
- Access: public.
- Tests:
  - `test_health_ok`: 200, `response["Content-Type"] == "application/json"`, `response.json() == {"status": "ok"}`.
  - `test_health_no_cache`: `"no-cache"` in `response["Cache-Control"]` (or `"max-age=0"`).
  - `test_health_rejects_post`: `POST` → 405.
  - `test_health_no_db_queries`: `with self.assertNumQueries(0)`.

### 6.3 Settings tests (`core/tests/test_settings.py`, `SimpleTestCase`)

- `test_locale`: `LANGUAGE_CODE == "ru"`, `TIME_ZONE == "Europe/Moscow"`, `USE_TZ is True`.
- `test_password_validators_enabled`: the 4 default validator class paths are all present in `AUTH_PASSWORD_VALIDATORS`.
- `test_admin_mounted_at_admin_url`: `reverse("admin:index") == "/" + settings.ADMIN_URL`.
- `test_whitenoise_after_security_middleware`: `MIDDLEWARE.index("whitenoise.middleware.WhiteNoiseMiddleware") == MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1`.
- `test_only_w021_silenced`: `SILENCED_SYSTEM_CHECKS == ["security.W021"]`.

---

## 7. Implementation order

Run every command from the repo root with `.venv` activated and `export DEBUG=true` set in your shell (the settings default is DEBUG=false; you must not edit `.env`).

1. Create `.venv` with `/opt/homebrew/bin/python3.12 -m venv .venv`. Write `requirements.txt`, `requirements-dev.txt`; `pip install -r requirements-dev.txt`. Verify: `python -c "import django; print(django.get_version())"` → `5.2.19`.
2. Write `pyproject.toml`. Verify: `ruff --version` → `0.17.4`.
3. Write `config/env_utils.py` and `core/tests/test_env_utils.py` (plus `core/__init__.py`, `core/tests/__init__.py`). Verify later in step 6.
4. Write `manage.py`, `config/*` (settings per 5.2, urls per 5.4), `core/apps.py`, `core/urls.py`, `core/views.py`. Verify: `python manage.py check`.
5. Write templates (5.6) and CSS (5.7). Verify: `python manage.py runserver`, open `/` and `/health/`.
6. Write `core/tests/test_views.py`, `core/tests/test_settings.py`. Verify: `python manage.py test` → all pass.
7. Write `.env.example`, `README.md`. Verify deploy check (section 8, command 4).
8. Write `.github/workflows/ci.yml`. Verify YAML (section 8, command 7).
9. Run `ruff format .` then the full verification list in section 8. All must pass. Then send the `REPORT` to the Reviewer.

## 8. Verification

```bash
source .venv/bin/activate
export DEBUG=true
python manage.py check                                     # 1: no issues
python manage.py makemigrations --check --dry-run          # 2: No changes detected
python manage.py test                                      # 3: OK
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING     # 4: exit 0, "(1 silenced)"
DEBUG=false SECRET_KEY= python manage.py check; echo "exit=$?"   # 5: ImproperlyConfigured mentioning SECRET_KEY, exit != 0
ruff check . && ruff format --check .                      # 6: clean
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"  # 7
```
Command 5 sets `SECRET_KEY=` explicitly (empty) so a value from `.env` cannot hide the failure; an empty real env var wins over `.env` because `read_env` does not overwrite existing variables.

Manual: `python manage.py runserver`, open `http://127.0.0.1:8000/` in browser dev tools at 360 px width → no horizontal scroll; footer disclaimer visible.

In the `REPORT`, paste the output tail of commands 1–7.

---

## 9. Risks

- **Secrets**: `.env` holds unrelated API keys. Settings load it into the process environment but must never log or print env values. Agents must not open `.env`; use shell `export` for verification.
- **`SECURE_PROXY_SSL_HEADER`** is safe only if nginx always sets (overwrites) `X-Forwarded-Proto`. The future deployment task must configure nginx with `proxy_set_header X-Forwarded-Proto $scheme;`.
- **HSTS**: default 1 hour on purpose for the first deploy (17.11); raise after HTTPS is stable. Preload stays off.
- **Custom user model (important for next tasks)**: this skeleton uses `auth.User`. The next task that adds users/roles must define `AUTH_USER_MODEL` before any app migration depends on users, and the local `db.sqlite3` must then be recreated. No production DB exists yet, so this costs nothing now.
- **Static storage switch** depends on DEBUG: production must run `python manage.py collectstatic --noinput` before start, otherwise pages with `{% static %}` return 500.
- **SQLite relative path in `.env.example`**: commands must run from the repo root.
