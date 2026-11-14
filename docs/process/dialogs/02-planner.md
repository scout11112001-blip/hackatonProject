── User ────────────────────────────────────────────────────
Ты работаешь в этом треде постоянно в роли «Планировщик».
Прочитай файл .claude/agents/planner.md и .bb/AGENTS.md. Следуй им во всех ответах этого треда.
Сейчас задач нет. Ответь одной строкой, что ты готов, и жди задачу от пользователя.

── Explored 1 file ─────────────────────────────────────────
  ── Read ~/hackatonproject/.claude/agents/planner.md
  ── Thought for 3ms
    The system prompt already has the AGENTS.md instructions, so I just need to reply in one line in Russian.

── Assistant ───────────────────────────────────────────────
Я в роли Планировщика, правила прочитал. Жду задачу: план запишу в `docs/plan.md`, продуктовый код писать не буду.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[SETUP] Team lead -> all: PROTOCOL UPDATE
The team protocol and your role prompt have changed. Re-read `.bb/AGENTS.md` and your role file now; they replace all earlier instructions in this thread. Key points: think and talk to agents in English, talk to the user in Russian, stack is Python + Django, use `bb thread tell` for handoffs. No task yet. Do not reply to this message.

── Explored 1 file ─────────────────────────────────────────
  ── Thought for 7ms
    I'm re-reading the files first. The message I received is addressed to the sender and doesn't need a reply, but my final answer still goes to the user, so I'll read the files before I write it.
  ── Read .bb/AGENTS.md

── Assistant ───────────────────────────────────────────────
Я заново прочитал обновлённый протокол и файл своей роли. Задач пока нет, тимлиду не отвечаю: он просил не отвечать.

Что изменилось:
- **Откуда задачи:** беру только от тимлида (`thr_4izdzwetb4`), у каждой задачи номер вида `TASK-NNN`.
- **Что пишу:** спецификацию на английском в `docs/tasks/TASK-NNN.md`. В ней задача разбита на отдельные функции, у каждой указаны сигнатура, алгоритм, граничные случаи и тесты.
- **Кому передаю:** кодеру (`thr_ng6cbgatm6`) через `bb thread tell`. Его вопросы по спецификации тоже разбираю я.
- **Стек:** Python + Django.
- **Чего не делаю:** не пишу продуктовый код, не пишу ревьюеру и не выполняю его указания.

Жду задачу от тимлида.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-001] Team lead -> Planner: TASK
Approved by the user. Write the spec `docs/tasks/TASK-001.md` and hand it to the Coder.

## Context
Project: "Digital Dean's Office of the Future" - a student personal-account prototype for a university hackathon (deadline 2026-11-22). The product plan is in `plan.md` (Russian). Key product decisions that shape this skeleton:
- Server-rendered Django only: templates, forms, Django admin. No REST API, no SPA, no JSON endpoints.
- Two user roles later: student and dean's-office staff.
- Mobile-first: every page must work at 360 px width. Final retro/pixel-art skin comes at the end, so styling must be a separate, replaceable layer.
- Local development first (SQLite), production later on a rented Linux server in Russia (PostgreSQL, gunicorn, nginx, HTTPS).
- Only fictional data. The site must state it is a contest concept, not an official university service.

## Goal
A minimal, production-sane Django skeleton that all later tasks build on. No domain features yet.

## Requirements
1. Python 3.12 from `/opt/homebrew/bin/python3.12`; virtualenv in `.venv/` (already git-ignored).
2. Django 5.2 LTS. Pin exact versions in `requirements.txt` (runtime) and `requirements-dev.txt` (dev/test tools, includes `-r requirements.txt`).
3. Project package `config` at the repo root: `manage.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`.
4. One app `core` for shared pieces (health check, base template, context processors if needed). No domain models.
5. Settings from environment variables: SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, DATABASE_URL. Use exactly one helper library for env loading (django-environ preferred, because it also parses DATABASE_URL); justify the choice in the spec.
   - DATABASE_URL default: SQLite file in the project root. PostgreSQL must work by changing only DATABASE_URL: add the PostgreSQL driver (`psycopg[binary]`) to `requirements.txt`.
   - DEBUG is false by default. Fail fast with a clear error when SECRET_KEY is missing and DEBUG is false.
   - When DEBUG is false: SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, SECURE_HSTS_*, SECURE_CONTENT_TYPE_NOSNIFF, X_FRAME_OPTIONS=DENY, SECURE_PROXY_SSL_HEADER for nginx; SECURE_SSL_REDIRECT controlled by an env variable.
   - LANGUAGE_CODE = "ru", TIME_ZONE = "Europe/Moscow", USE_TZ = True.
   - Password hashing: Django defaults (do not weaken). Enable all default password validators.
6. Agents must NOT read or edit `.env` (it holds API keys). Create `.env.example` with every variable and safe placeholder values. The user will copy the values into `.env` manually.
7. Static files: `STATIC_ROOT` for `collectstatic`, `static/` source dir. Serve static files in production with WhiteNoise (allowed dependency).
8. Base template `templates/base.html`:
   - `<meta name="viewport" content="width=device-width, initial-scale=1">`, `lang="ru"`;
   - semantic layout blocks: header, main navigation placeholder, `{% block content %}`, footer;
   - footer disclaimer (Russian): "Концепт для конкурса MGIMO AI Challenge. Не является официальным сервисом вуза. Все данные вымышлены.";
   - CSS split into `static/css/tokens.css` (CSS custom properties: colors, fonts, spacing - the future pixel-art skin replaces only this file and `theme.css`), `static/css/base.css` (mobile-first layout, no visual theme), `static/css/theme.css` (empty placeholder);
   - no external CDNs.
9. Home page `GET /` rendering `base.html` with a placeholder heading, and `GET /health/` returning `{"status": "ok"}` (the only JSON response, used for server monitoring). Tests for both.
10. Django admin enabled at a non-default path taken from env variable ADMIN_URL (default `admin/` in development).
11. Logging to console; no secrets in logs.
12. Tooling: ruff (lint + format) configured in `pyproject.toml`; tests run with `python manage.py test`.
13. `README.md` (English): setup, run, test commands. Short.
14. CI with GitHub Actions: `.github/workflows/ci.yml`, triggered on push and pull_request.
    - Ubuntu runner, Python 3.12, pip cache keyed on the requirements files.
    - Steps: install `requirements-dev.txt`; `ruff check .`; `ruff format --check .`; `python manage.py check`; `python manage.py makemigrations --check --dry-run`; `python manage.py test`; `python manage.py check --deploy` with production-like env.
    - All env values in the workflow are dummy test values set inline (e.g. a throwaway SECRET_KEY). No GitHub secrets are needed and no real secret may appear in the workflow.
    - The GitHub remote does not exist yet; the workflow must simply be valid and ready. Validate its YAML syntax locally.

## Out of scope
Domain models, authentication UI, roles, Docker, deployment scripts, creating the GitHub repository.

## Verification the spec must include
- `python manage.py check`
- `DEBUG=false SECRET_KEY=<test> ALLOWED_HOSTS=example.com python manage.py check --deploy` with zero warnings, or each remaining warning justified
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test`
- `ruff check .` and `ruff format --check .`
- `.github/workflows/ci.yml` parses as valid YAML and runs the same commands as above
- Manual: open `/` at 360 px width, no horizontal scroll.

── Explored 2 lists, 1 file, ran 2 commands, created 1 file
  ── Thought for 10ms
    I'm starting by getting a feel for the project before doing anything else.
  ── Listed files in .
  ── Thought for 4ms
    I'm checking what's in docs/tasks and the coder role file, and I'll also look up the current package versions on PyPI.
  ── Listed files in docs/tasks
  ── Ran for p in django django-environ whitenoise "psycopg" "psycopg-binary" ruff pyyaml; do printf "%s: " $p; curl -s https://pypi.org/pypi/$p/json | /opt/homebrew/bin/python3.12 -c "import sys,json;d=json.load(sys.stdin);print(d['info']['version'], [v for v in d['releases'] if v.startswith('5.2.')][-3:] if d['info']['name'].lower()=='django' else '')"; done (22s)
    $ for p in django django-environ whitenoise "psycopg" "psycopg-binary" ruff pyyaml; do printf "%s: " $p; curl -s https://pypi.org/pypi/$p/json | /opt/homebrew/bin/python3.12 -c "import sys,json;d=json.load(sys.stdin);print(d['info']['version'], [v for v in d['releases'] if v.startswith('5.2.')][-3:] if d['info']['name'].lower()=='django' else '')"; done
    django: 6.1.3 ['5.2.7', '5.2.8', '5.2.9']
    django-environ: 0.14.0 
    whitenoise: 6.12.0 
    psycopg: 3.3.8 
    psycopg-binary: 3.3.8 
    ruff: 0.17.4 
    pyyaml: 6.0.3
  ── Thought for 8ms
    I need to check the releases list properly, since it's sorted as strings and versions like '5.2.10' could be sitting in there out of order.
  ── Ran curl -s https://pypi.org/pypi/django/json | /opt/homebrew/bin/python3.12 -c " import sys,json;d=json.load(sys.stdin) v=[k for k in d['releases'] if k.startswith('5.2.') and d['releases'][k]] v.sort(key=lambda s:[int(x) for x in s.split('.')]);print(v[-3:])" curl -s https://pypi.org/pypi/django-environ/json | /opt/homebrew/bin/python3.12 -c "import sys,json;d=json.load(sys.stdin);print(d['info']['requires_python'], d['info']['classifiers'][:0] or [c for c in d['info']['classifiers'] if 'Django ::' in c])" curl -s https://pypi.org/pypi/whitenoise/json | /opt/homebrew/bin/python3.12 -c "import sys,json;d=json.load(sys.stdin);print([c for c in d['info']['classifiers'] if 'Django ::' in c])" (7s)
    $ curl -s https://pypi.org/pypi/django/json | /opt/homebrew/bin/python3.12 -c "
  import sys,json;d=json.load(sys.stdin)
  v=[k for k in d['releases'] if k.startswith('5.2.') and d['releases'][k]]
  v.sort(key=lambda s:[int(x) for x in s.split('.')]);print(v[-3:])"
  curl -s https://pypi.org/pypi/django-environ/json | /opt/homebrew/bin/python3.12 -c "import sys,json;d=json.load(sys.stdin);print(d['info']['requires_python'], d['info']['classifiers'][:0] or [c for c in d['info']['classifiers'] if 'Django ::' in c])"
  curl -s https://pypi.org/pypi/whitenoise/json | /opt/homebrew/bin/python3.12 -c "import sys,json;d=json.load(sys.stdin);print([c for c in d['info']['classifiers'] if 'Django ::' in c])"
    ['5.2.17', '5.2.18', '5.2.19']
    <4,>=3.9 ['Framework :: Django :: 2.2', 'Framework :: Django :: 3.0', 'Framework :: Django :: 3.1', 'Framework :: Django :: 3.2', 'Framework :: Django :: 4.0', 'Framework :: Django :: 4.1', 'Framework :: Django :: 4.2', 'Framework :: Django :: 5.0', 'Framework :: Django :: 5.1', 'Framework :: Django :: 5.2', 'Framework :: Django :: 6.0']
    ['Framework :: Django :: 4.2', 'Framework :: Django :: 5.0', 'Framework :: Django :: 5.1', 'Framework :: Django :: 5.2', 'Framework :: Django :: 6.0']
  ── Thought for 1m 40s
    I'm sketching out the spec now, starting with the dependency list. Django, django-environ, whitenoise, and psycopg are in; gunicorn is left out since deployment comes later. I'm also weighing whether to pull in PyYAML to validate the YAML.

    I'm settling the dev dependencies next: pyyaml==6.0.3 goes in for the YAML check. I'm also questioning whether to pin only the top-level packages and leave the transitive ones unpinned, which seems acceptable. For settings, I'm weighing whether to load a local .env file without overriding real environment variables, since that keeps local dev simple.

    I'm checking how the settings should treat DEBUG and SECRET_KEY when no environment is set, since a missing key would make local `manage.py` runs fail unless `.env` supplies DEBUG=true. Reading `.env` only when it exists and never overriding real environment variables keeps tests predictable.

    I'm working out how the verification commands will run, since the .env file won't supply DEBUG to the checks by default, so I'll set DEBUG=true explicitly in the commands. I'm also noting that Django's test runner adds "testserver" to ALLOWED_HOSTS on its own, so the default host list only needs the local addresses.

    I'm working out the security headers for non-debug mode, looking at whether HSTS should default to a nonzero value so the deploy check doesn't flag it. I'm also weighing whether to include subdomains and preload, since the server's domain isn't known yet.

    I'm weighing whether to make the W021 preload warning go away by silencing it in settings, or to keep it, leave preload off by default, and justify the warning instead. Silencing it would hide the check, so I'm leaning toward a CI deploy check that fails on warnings, with the HSTS value set through the environment.

    I'm settling the HSTS preload warning by silencing W021 unconditionally, since it can't fire when preload is on anyway. Next I'm deciding SECURE_SSL_REDIRECT, which should default to True and be controlled by an environment variable, since a reverse proxy might handle the redirect instead.

    I'm settling the HSTS duration at a short one-hour default so the initial deploy stays low-risk, to be raised later. I'm also checking the proxy SSL header, which is only safe if the reverse proxy sets it and strips any client-supplied value.

    I'm noting that the CI dummy secret key needs to be long enough to clear the W009 check, and that `ALLOWED_HOSTS` gets set to a real value in CI so the empty-host warning doesn't fire. I'm also keeping the insecure fallback key limited to debug mode, and the CSRF trusted origins defaulting to an empty list. The database URL will default to a local SQLite file unless an environment variable overrides it.

    I'm settling on an ADMIN_URL that defaults to "admin/" and checking that it ends with a slash and doesn't start with one.

    I'm settling on a helper, `normalize_admin_url`, in `config/env_utils.py` that strips whitespace and slashes, rejects empty or invalid values, and returns the path with a trailing slash. I'm keeping the production check to format validation only, without requiring the default to change.

    I'm planning the health check as a simple GET-only JSON view that returns a status of ok without touching the database. I'm also wondering whether it should be exempt from the SSL redirect.

    I'm planning the home view as a TemplateView that renders a home template extending base.html, with a placeholder heading. I'm placing that template under the core app's templates folder, and I'm keeping the context processors out of it for now.

    I'm settling the static files setup next: a STATIC_ROOT in the project folder, gitignored, with WhiteNoise's compressed manifest storage as the backend. That manifest storage raises an error for `{% static %}` when DEBUG is off, and tests run with DEBUG off, so I'm working out how to avoid that during the test run.

    I'm working through the static storage backend now. The manifest-backed storage would raise on `{% static %}` in the test run, since tests run with DEBUG off and no manifest exists, so I'm checking whether turning off strict manifest lookup lets it fall back to the plain filename.

    I'm working through the static storage backend and realizing that the manifest-backed option fails in tests, because a missing manifest or uncollected file raises an error. I'm considering choosing the storage backend per environment, possibly through an environment variable, so tests can use plain static files.

    I'm weighing how to handle the static storage in tests, since the manifest backend would fail there. I'm thinking about choosing the storage backend based on DEBUG, so tests running with it set get plain static files, though that depends on which environment the test step uses.

    I'm weighing whether to put the static storage choice behind a test-detection check or keep it tied to DEBUG. Tying it to DEBUG keeps the settings simple, but it means the CI test step has to run with DEBUG enabled.

    I'm going with the DEBUG-dependent static backend, and I'm accepting that running locally with DEBUG off will need a collectstatic step first. I'm also placing WhiteNoise right after SecurityMiddleware and adding its runserver_nostatic app for parity. Logging will go to the console, with the root level read from an environment variable that defaults to INFO, and I'm making sure no secrets end up in the logs.

    I'm settling the lint setup in `pyproject.toml` with a py312 target, a 100-character line length, and a Ruff rule selection covering the main error, import, and Django checks, while leaving migrations out. For CI I'm pinning the usual checkout and setup-python actions with pip caching keyed on the requirements files.

    I'm checking the CI env setup, with the test steps running under DEBUG=true and a dummy secret key, and the deploy check running separately with DEBUG=false and `--fail-level WARNING`.

    I'm checking the CI workflow file's syntax with a quick YAML parse, which PyYAML can handle. Then I'm turning to the example env file, with a placeholder secret key, debug on for local dev, and the allowed hosts set to localhost.

    I'm settling the `.env.example` contents now, leaving the Postgres URL commented out, with the admin path, SSL redirect, HSTS, and log level set to their defaults. I'm also weighing whether `SECURE_HSTS_INCLUDE_SUBDOMAINS` should default to true, since W005 flags it when it's off, but that depends on whether the domain sits under a shared provider.

    I'm going through the security warnings now: with the defaults, the HSTS, cookie, nosniff, frame, and allowed-hosts checks should all pass. The production-only settings will sit inside an `if not DEBUG:` block, with HSTS left at zero in debug mode.

    I'm laying out the base template now: a Russian-language HTML5 skeleton with a title block defaulting to the project name, and the stylesheet links ordered tokens, base, then theme. Next I'm adding an extra head block and a skip-link to the main content at the top of the body.

    Writing the base template's header, navigation, main and footer markup...

    Writing the test cases now: the home page should return 200 with base.html and the home template, the disclaimer, and the stylesheets in the right order, and the health endpoint should return JSON and reject POST...

    I'm laying out the URL wiring next: the admin route uses the configurable ADMIN_URL, and the core app's home and health routes sit at the root. Then I'm weighing whether to use Django's default User model or add a custom one now, since changing it after the first migration is painful, but the spec says the core app holds everything and has no domain models, so that's a conflict I need to resolve.

    I'm weighing whether to flag the custom user model question to the team lead before handing off the spec. Migrations shouldn't be an issue yet, since the skeleton has no models and there's no production database, so a custom user could still be added in a later task.

    I'm writing the `env_utils` helpers now: one to resolve the secret key depending on DEBUG, and one to normalize the admin URL path and reject invalid values.

    I'm writing the settings logging config now, with a console handler and a simple format.

    I'm working through the logging level setting now, mainly whether to validate it or let Python's logging raise on a bad value, which would already fail fast at startup.

    I'm checking how the settings file reads the environment, and whether the local verification commands need DEBUG=true set explicitly, since the current .env has no Django variables. I'm also noting that the environment variables loaded by manage.py shouldn't be printed anywhere in the output.

    I'm checking whether the Django debug page would expose the API key, and it looks like the name filter masks it. I'm also confirming that runserver with DEBUG on is the manual check, and that a DEBUG value of "false" or "0" parses as off. The CI deploy check still needs to run with `--fail-level WARNING`.

    I'm checking the remaining security warnings against the defaults, and the middleware ordering looks fine for the CI deploy check. Next I'm deciding how ADMIN_URL should behave in production, since the spec says the default path applies in development but a non-default path should come from the environment.

    I'm settling the admin URL behavior: if DEBUG is off and ADMIN_URL isn't set, the settings will raise ImproperlyConfigured, since the default path only applies in development. The CI deploy step will set ADMIN_URL explicitly, and the helper will take the raw value along with the debug flag. I'm also keeping SSL redirect on by default with the health endpoint exempt, and I don't need any new gitignore entries since staticfiles and db.sqlite3 are already covered. Last, I'm listing the files the skeleton needs: the requirements pair, pyproject.toml, manage.py, and the config package modules.

    I'm listing the remaining files for the core app and the templates and static assets, and I'm deciding not to create models or migrations for now. Next I'm checking whether to add the core tests, which cover the views, env helpers and settings.

    I'm now thinking about whether the settings tests should run the app in a subprocess with DEBUG off and no SECRET_KEY, to confirm it fails at startup. The worry is that a `.env` file could supply a key and make that test unreliable.

    I'm checking whether `read_env` would fill in a SECRET_KEY that the test removes from the environment, since that would make the subprocess test unreliable. I'm dropping that test and relying on the helper unit tests and the CI deploy check instead. I'm also checking how `read_env` handles a missing file, since it affects whether the settings module can load without `.env`.

    I'm checking whether `read_env` warns when the `.env` file is missing, so I'll guard the call with an is-file check to keep CI clean. I'm also adding a dev-only fallback key constant for the debug path. Last, I'm pinning the package versions for the requirements files.

    I'm deciding how the coder should run pinned installs, and I'll tell them to ask if a pinned version won't install rather than swap it out. I'm leaving commit handling to the team lead, so the spec won't mention it. Next I'm writing the spec itself.
  ── Read plan.md
  ── Thought for 6ms
    I'm going to write the spec now.
  ── Created docs/tasks/TASK-001.md +549
    --- /dev/null
    +++ b~/hackatonproject/docs/tasks/TASK-001.md
    +# TASK-001: Django project skeleton + CI
    +
    +Author: Planner. Status: ready for implementation.
    +Product context: `plan.md` (Russian). Team protocol: `.bb/AGENTS.md`.
    +
    +---
    +
    +## 1. Goal
    +
    +Create a minimal, production-sane Django 5.2 LTS skeleton for the "Digital Dean's Office of the Future" prototype. All later tasks build on it. No domain features.
    +
    +## 2. Acceptance criteria
    +
    +All must be true:
    +
    +1. `.venv/` exists, created with `/opt/homebrew/bin/python3.12`; `pip install -r requirements-dev.txt` succeeds.
    +2. With `DEBUG=true` in the environment:
    +   - `python manage.py check` → `System check identified no issues (0 silenced).`
    +   - `python manage.py makemigrations --check --dry-run` → `No changes detected`, exit code 0.
    +   - `python manage.py test` → all tests pass (at least the tests listed in section 6).
    +3. With `DEBUG=false SECRET_KEY=<50+ char dummy> ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/`:
    +   `python manage.py check --deploy --fail-level WARNING` → exit code 0. The only silenced check is `security.W021` (justified in section 5.3).
    +4. With `DEBUG=false` and no `SECRET_KEY`: any `manage.py` command fails immediately with `django.core.exceptions.ImproperlyConfigured` whose message mentions `SECRET_KEY`.
    +5. `ruff check .` and `ruff format --check .` → no errors.
    +6. `.github/workflows/ci.yml` is valid YAML and runs the same commands as items 2, 3 and 5.
    +7. `GET /` → 200, HTML page with `lang="ru"`, viewport meta, header, nav placeholder, main content, footer disclaimer (exact text in 5.6).
    +8. `GET /health/` → 200, `Content-Type: application/json`, body exactly `{"status": "ok"}`.
    +9. Admin is reachable at `/<ADMIN_URL>`; default `admin/` only when `DEBUG=true`.
    +10. No external URLs (CDNs, fonts) in templates or CSS.
    +11. `.env` is not read, printed or modified by any agent. `.env.example` lists every variable with safe placeholders.
    +12. Manual: `/` at 360 px width has no horizontal scroll.
    +
    +## 3. Out of scope
    +
    +- Domain models, custom user model, authentication UI, roles, permissions.
    +- Docker, gunicorn, nginx config, deployment scripts.
    +- Creating the GitHub repository or pushing.
    +- Pixel-art styling, fonts, icons, logo.
    +- REST API / JSON endpoints (except `/health/`).
    +- Committing to git (the Team lead decides when to commit).
    +
    +---
    +
    +## 4. Dependencies (exact pins)
    +
    +Checked on PyPI on 2026-11-11.
    +
    +`requirements.txt` (runtime):
    +```
    +Django==5.2.19
    +django-environ==0.14.0
    +whitenoise==6.12.0
    +psycopg[binary]==3.3.8
    +```
    +
    +`requirements-dev.txt`:
    +```
    +-r requirements.txt
    +ruff==0.17.4
    +PyYAML==6.0.3
    +```
    +
    +Only top-level packages are pinned. Do not add other packages. If a pin fails to install, send a `QUESTION` to the Planner — do not pick another version yourself.
    +
    +**Why django-environ** (the only env helper): it reads environment variables with typed casting (`bool`, `list`, `int`), reads an optional `.env` file without overriding real environment variables, and parses `DATABASE_URL` into Django's `DATABASES` dict for both SQLite and PostgreSQL. `python-decouple` would need a second library (`dj-database-url`) for `DATABASE_URL`; `pydantic-settings` is heavier and not Django-specific.
    +
    +PyYAML is dev-only, used to validate the CI workflow syntax locally.
    +
    +---
    +
    +## 5. Architecture
    +
    +### 5.1 File tree (create exactly these; do not run `startapp`)
    +
    +```
    +manage.py
    +config/__init__.py            (empty)
    +config/settings.py
    +config/env_utils.py           (pure helper functions, see section 6)
    +config/urls.py
    +config/wsgi.py
    +config/asgi.py
    +core/__init__.py              (empty)
    +core/apps.py
    +core/urls.py
    +core/views.py
    +core/templates/core/home.html
    +core/tests/__init__.py        (empty)
    +core/tests/test_env_utils.py
    +core/tests/test_views.py
    +core/tests/test_settings.py
    +templates/base.html
    +static/css/tokens.css
    +static/css/base.css
    +static/css/theme.css
    +requirements.txt
    +requirements-dev.txt
    +pyproject.toml
    +.env.example
    +README.md
    +.github/workflows/ci.yml
    +```
    +
    +`core` has no `models.py`, no `admin.py`, no `migrations/`. Do not change `.gitignore` (it already ignores `.venv/`, `db.sqlite3`, `/staticfiles/`, `.env`).
    +
    +`manage.py`, `config/wsgi.py`, `config/asgi.py`: standard Django 5.2 `startproject` content with `DJANGO_SETTINGS_MODULE` = `"config.settings"`.
    +
    +`core/apps.py`:
    +```python
    +class CoreConfig(AppConfig):
    +    default_auto_field = "django.db.models.BigAutoField"
    +    name = "core"
    +```
    +
    +### 5.2 `config/settings.py` — exact structure
    +
    +Write the settings in this order. Use `environ.Env()` from django-environ. All names below are module-level settings.
    +
    +1. **Paths and env loading**
    +   ```python
    +   BASE_DIR = Path(__file__).resolve().parent.parent
    +   env = environ.Env()
    +   _env_file = BASE_DIR / ".env"
    +   if _env_file.is_file():
    +       environ.Env.read_env(_env_file)   # overwrite=False (default): real env vars win
    +   ```
    +   Never log, print or iterate over the loaded values.
    +
    +2. **Core flags**
    +   - `DEBUG = env.bool("DEBUG", default=False)`
    +   - `SECRET_KEY = resolve_secret_key(env.str("SECRET_KEY", default=""), DEBUG)` (from `config.env_utils`)
    +   - `ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"] if DEBUG else [])`
    +   - `CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])`
    +   - `ADMIN_URL = resolve_admin_url(env.str("ADMIN_URL", default=""), DEBUG)`
    +
    +3. **Apps** (this order):
    +   ```
    +   "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    +   "django.contrib.sessions", "django.contrib.messages",
    +   "whitenoise.runserver_nostatic", "django.contrib.staticfiles",
    +   "core",
    +   ```
    +
    +4. **Middleware** (this order; WhiteNoise right after SecurityMiddleware):
    +   ```
    +   "django.middleware.security.SecurityMiddleware",
    +   "whitenoise.middleware.WhiteNoiseMiddleware",
    +   "django.contrib.sessions.middleware.SessionMiddleware",
    +   "django.middleware.locale.LocaleMiddleware" -> NOT added (single language),
    +   "django.middleware.common.CommonMiddleware",
    +   "django.middleware.csrf.CsrfViewMiddleware",
    +   "django.contrib.auth.middleware.AuthenticationMiddleware",
    +   "django.contrib.messages.middleware.MessageMiddleware",
    +   "django.middleware.clickjacking.XFrameOptionsMiddleware",
    +   ```
    +   (Do not add LocaleMiddleware; the line above is only a note.)
    +
    +5. `ROOT_URLCONF = "config.urls"`, `WSGI_APPLICATION = "config.wsgi.application"`, `ASGI_APPLICATION = "config.asgi.application"`.
    +
    +6. **Templates**: one `DjangoTemplates` backend, `DIRS=[BASE_DIR / "templates"]`, `APP_DIRS=True`, context processors: `debug`, `request`, `auth`, `messages` (the Django 5.2 `startproject` defaults).
    +
    +7. **Database**
    +   ```python
    +   DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
    +   ```
    +   PostgreSQL example: `DATABASE_URL=postgres://user:password@localhost:5432/deanery`. No other DB code.
    +   `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`.
    +
    +8. **Passwords**: `PASSWORD_HASHERS` not set (Django default). `AUTH_PASSWORD_VALIDATORS` = all four Django defaults (`UserAttributeSimilarityValidator`, `MinimumLengthValidator`, `CommonPasswordValidator`, `NumericPasswordValidator`) with default options.
    +
    +9. **I18N**: `LANGUAGE_CODE = "ru"`, `TIME_ZONE = "Europe/Moscow"`, `USE_I18N = True`, `USE_TZ = True`.
    +
    +10. **Static files**
    +    ```python
    +    STATIC_URL = "static/"
    +    STATICFILES_DIRS = [BASE_DIR / "static"]
    +    STATIC_ROOT = BASE_DIR / "staticfiles"
    +    STORAGES = {
    +        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    +        "staticfiles": {
    +            "BACKEND": (
    +                "django.contrib.staticfiles.storage.StaticFilesStorage"
    +                if DEBUG
    +                else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    +            )
    +        },
    +    }
    +    ```
    +    Reason for the switch: the manifest storage raises an error for `{% static %}` until `collectstatic` has run; development and tests run with `DEBUG=true` and do not run `collectstatic`.
    +
    +11. **Security** (always set):
    +    - `X_FRAME_OPTIONS = "DENY"`
    +    - `SECURE_CONTENT_TYPE_NOSNIFF = True`
    +    - `SECURE_REFERRER_POLICY = "same-origin"`
    +    - `SESSION_COOKIE_HTTPONLY = True`
    +
    +    **Only `if not DEBUG:`**
    +    - `SESSION_COOKIE_SECURE = True`
    +    - `CSRF_COOKIE_SECURE = True`
    +    - `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
    +    - `SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)`
    +    - `SECURE_REDIRECT_EXEMPT = [r"^health/$"]` (local monitoring may call gunicorn over plain HTTP)
    +    - `SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)`
    +    - `SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)`
    +    - `SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)`
    +
    +12. **Silenced checks**
    +    ```python
    +    # security.W021: HSTS preload is an irreversible browser-list commitment.
    +    # A contest prototype must not opt in. Enable via SECURE_HSTS_PRELOAD only deliberately.
    +    SILENCED_SYSTEM_CHECKS = ["security.W021"]
    +    ```
    +
    +13. **Logging** (console only):
    +    ```python
    +    LOG_LEVEL = env.str("LOG_LEVEL", default="INFO").upper()
    +    LOGGING = {
    +        "version": 1,
    +        "disable_existing_loggers": False,
    +        "formatters": {"simple": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}},
    +        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    +        "root": {"handlers": ["console"], "level": LOG_LEVEL},
    +        "loggers": {"django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False}},
    +    }
    +    ```
    +    Do not configure `django.db.backends` at DEBUG level (it logs SQL parameters). Do not log settings or environment values anywhere.
    +
    +### 5.3 `check --deploy` result (expected)
    +
    +With the CI production-like env, every deploy check passes except `security.W021` (HSTS preload), which is silenced in settings with the justification above. No other check may be silenced.
    +
    +### 5.4 URLs
    +
    +`config/urls.py`:
    +```python
    +urlpatterns = [
    +    path(settings.ADMIN_URL, admin.site.urls),
    +    path("", include("core.urls")),
    +]
    +```
    +
    +`core/urls.py`:
    +```python
    +app_name = "core"
    +urlpatterns = [
    +    path("", views.HomeView.as_view(), name="home"),
    +    path("health/", views.health, name="health"),
    +]
    +```
    +
    +### 5.5 Views (`core/views.py`) — see section 6 for details
    +
    +- `HomeView(TemplateView)`, `template_name = "core/home.html"`.
    +- `health(request)` function view.
    +
    +### 5.6 Templates
    +
    +`templates/base.html` — exact structure (Russian UI text):
    +```html
    +{% load static %}<!doctype html>
    +<html lang="ru">
    +<head>
    +  <meta charset="utf-8">
    +  <meta name="viewport" content="width=device-width, initial-scale=1">
    +  <title>{% block title %}Цифровой деканат будущего{% endblock %}</title>
    +  <link rel="stylesheet" href="{% static 'css/tokens.css' %}">
    +  <link rel="stylesheet" href="{% static 'css/base.css' %}">
    +  <link rel="stylesheet" href="{% static 'css/theme.css' %}">
    +  {% block extra_head %}{% endblock %}
    +</head>
    +<body>
    +  <a class="skip-link" href="#main">Перейти к содержимому</a>
    +  <header class="site-header">
    +    <a class="site-title" href="{% url 'core:home' %}">Цифровой деканат будущего</a>
    +    <nav class="site-nav" aria-label="Основная навигация">{% block nav %}{% endblock %}</nav>
    +  </header>
    +  <main id="main" class="site-main">
    +    {% block content %}{% endblock %}
    +  </main>
    +  <footer class="site-footer">
    +    <p class="site-disclaimer">Концепт для конкурса MGIMO AI Challenge. Не является официальным сервисом вуза. Все данные вымышлены.</p>
    +  </footer>
    +</body>
    +</html>
    +```
    +CSS order is fixed: tokens → base → theme.
    +
    +`core/templates/core/home.html`:
    +```html
    +{% extends "base.html" %}
    +{% block content %}
    +  <h1>Цифровой деканат будущего</h1>
    +  <p>Прототип личного кабинета студента. Раздел в разработке.</p>
    +{% endblock %}
    +```
    +
    +### 5.7 CSS layer contract
    +
    +- `static/css/tokens.css`: only a `:root { ... }` block with custom properties. No selectors other than `:root`. Required tokens:
    +  `--color-bg`, `--color-text`, `--color-muted`, `--color-accent`, `--color-border`,
    +  `--font-body` (system font stack), `--font-heading` (same stack for now),
    +  `--font-size-base` (`1rem`), `--line-height-base` (`1.5`),
    +  `--space-1` (`0.25rem`), `--space-2` (`0.5rem`), `--space-3` (`1rem`), `--space-4` (`1.5rem`), `--space-5` (`2rem`),
    +  `--content-max-width` (`60rem`), `--radius` (`0`).
    +  Use neutral values (e.g. white bg, near-black text).
    +- `static/css/base.css`: mobile-first layout only. Every color, font, spacing value comes from `var(--...)`; no literal colors. Must include:
    +  - `*, *::before, *::after { box-sizing: border-box; }`
    +  - `body { margin: 0; font-family: var(--font-body); ... background: var(--color-bg); color: var(--color-text); }`
    +  - `img, svg { max-width: 100%; height: auto; }`
    +  - `body { overflow-wrap: anywhere; }` (long words must not cause horizontal scroll)
    +  - `.site-header`, `.site-main`, `.site-footer`: padding `var(--space-3)`; `.site-main` has `max-width: var(--content-max-width); margin-inline: auto;`
    +  - `.skip-link`: visually hidden until `:focus`.
    +  - One `@media (min-width: 48rem)` block for wider padding. No fixed widths in px above 360.
    +- `static/css/theme.css`: only a comment: `/* Visual theme layer. The pixel-art skin replaces this file and tokens.css. */`
    +
    +No `@import`, no `url(http...)`, no external fonts.
    +
    +### 5.8 `.env.example`
    +
    +Exact content:
    +```
    +# Copy to .env and edit. Never commit .env.
    +# Development defaults. For production set DEBUG=false and real values.
    +DEBUG=true
    +SECRET_KEY=change-me-to-a-long-random-string-of-at-least-50-characters
    +ALLOWED_HOSTS=localhost,127.0.0.1
    +CSRF_TRUSTED_ORIGINS=
    +# SQLite (default if unset). PostgreSQL example:
    +# DATABASE_URL=postgres://deanery:change-me@localhost:5432/deanery
    +DATABASE_URL=sqlite:///db.sqlite3
    +# Required when DEBUG=false. Use a non-obvious path, must end with "/".
    +ADMIN_URL=admin/
    +# Production only (ignored when DEBUG=true)
    +SECURE_SSL_REDIRECT=true
    +SECURE_HSTS_SECONDS=3600
    +SECURE_HSTS_INCLUDE_SUBDOMAINS=true
    +SECURE_HSTS_PRELOAD=false
    +LOG_LEVEL=INFO
    +```
    +Note: `sqlite:///db.sqlite3` is relative to the working directory; this is fine because commands run from the repo root.
    +
    +### 5.9 `pyproject.toml`
    +
    +Only ruff config (no `[project]` table):
    +```toml
    +[tool.ruff]
    +target-version = "py312"
    +line-length = 100
    +extend-exclude = ["*/migrations/*", ".venv", "staticfiles"]
    +
    +[tool.ruff.lint]
    +select = ["E", "F", "W", "I", "B", "UP", "DJ", "S"]
    +ignore = []
    +
    +[tool.ruff.lint.per-file-ignores]
    +"*/tests/*" = ["S101", "S105", "S106"]
    +"config/env_utils.py" = ["S105"]
    +
    +[tool.ruff.lint.isort]
    +known-first-party = ["config", "core"]
    +
    +[tool.ruff.format]
    +quote-style = "double"
    +```
    +If a rule in `select` produces a finding you believe is a false positive, do not add ignores yourself: send a `QUESTION`.
    +
    +### 5.10 `.github/workflows/ci.yml`
    +
    +Exact content:
    +```yaml
    +name: CI
    +
    +on:
    +  push:
    +  pull_request:
    +
    +permissions:
    +  contents: read
    +
    +jobs:
    +  test:
    +    runs-on: ubuntu-latest
    +    env:
    +      DEBUG: "true"
    +      SECRET_KEY: "ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop"
    +    steps:
    +      - uses: actions/checkout@v4
    +      - uses: actions/setup-python@v5
    +        with:
    +          python-version: "3.12"
    +          cache: pip
    +          cache-dependency-path: |
    +            requirements.txt
    +            requirements-dev.txt
    +      - name: Install dependencies
    +        run: python -m pip install -r requirements-dev.txt
    +      - name: Ruff lint
    +        run: ruff check .
    +      - name: Ruff format
    +        run: ruff format --check .
    +      - name: Django check
    +        run: python manage.py check
    +      - name: Missing migrations
    +        run: python manage.py makemigrations --check --dry-run
    +      - name: Tests
    +        run: python manage.py test
    +      - name: Deploy check (production-like env)
    +        env:
    +          DEBUG: "false"
    +          ALLOWED_HOSTS: "example.com"
    +          ADMIN_URL: "ci-staff-panel/"
    +        run: python manage.py check --deploy --fail-level WARNING
    +```
    +All values are dummies. No `secrets.*`.
    +
    +### 5.11 `README.md` (English, short)
    +
    +Sections: title + one-line description + disclaimer (fictional data, contest concept); Requirements (Python 3.12); Setup (`/opt/homebrew/bin/python3.12 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements-dev.txt`, `cp .env.example .env` then edit); Run (`python manage.py migrate`, `python manage.py runserver`); Test & lint (the commands of section 8); Environment variables (table: name, default, purpose — from 5.8).
    +
    +---
    +
    +## 6. Functions
    +
    +### 6.1 `config/env_utils.py`
    +
    +Module constant:
    +```python
    +DEV_SECRET_KEY = "django-insecure-dev-only-key-do-not-use-in-production"
    +```
    +Imports: only `re` and `django.core.exceptions.ImproperlyConfigured`. Must not import `django.conf.settings`.
    +
    +#### `resolve_secret_key(raw: str, debug: bool) -> str`
    +- Purpose: return the secret key, failing fast in production when it is missing.
    +- Inputs: `raw` — value of `SECRET_KEY` env var (`""` when unset); `debug` — the DEBUG flag.
    +- Output: the key string.
    +- Raises: `ImproperlyConfigured("SECRET_KEY environment variable is required when DEBUG is false.")`.
    +- Algorithm:
    +  1. `value = raw.strip()`.
    +  2. If `value` → return `value`.
    +  3. If `debug` → return `DEV_SECRET_KEY`.
    +  4. Else raise the error above.
    +- Edge cases: whitespace-only → treated as missing. Never include `raw` in any message.
    +- Caller: `config/settings.py` only.
    +- Tests (`core/tests/test_env_utils.py`, `SimpleTestCase`):
    +  - `test_returns_given_key` (debug False, `"abc..."` → same).
    +  - `test_strips_whitespace` (`"  key  "` → `"key"`).
    +  - `test_dev_fallback_when_debug` (`""`, True → `DEV_SECRET_KEY`).
    +  - `test_missing_key_in_production_raises` (`""`, False → raises, message contains `"SECRET_KEY"`).
    +  - `test_whitespace_key_in_production_raises` (`"   "`, False → raises).
    +
    +#### `resolve_admin_url(raw: str, debug: bool) -> str`
    +- Purpose: return a validated URL prefix for Django admin, e.g. `"staff-panel/"`.
    +- Inputs: `raw` — value of `ADMIN_URL` env var (`""` when unset); `debug`.
    +- Output: path segment(s) without leading slash, with exactly one trailing slash.
    +- Raises: `ImproperlyConfigured` with a message that mentions `ADMIN_URL`.
    +- Algorithm:
    +  1. `value = raw.strip().strip("/")`.
    +  2. If `value == ""`: if `debug` → return `"admin/"`; else raise `ImproperlyConfigured("ADMIN_URL environment variable is required when DEBUG is false.")`.
    +  3. If not `re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", value)` → raise `ImproperlyConfigured("ADMIN_URL may contain only letters, digits, '-', '_' and '/'.")`.
    +  4. Return `value + "/"`.
    +- Edge cases: `"/staff/"` → `"staff/"`; `"staff"` → `"staff/"`; `"a//b"` → raises; `"../x"` → raises; `"admin/"` with debug False → allowed (operator's choice).
    +- Caller: `config/settings.py` only.
    +- Tests:
    +  - `test_default_in_debug` (`""`, True → `"admin/"`).
    +  - `test_missing_in_production_raises` (`""`, False → raises, message contains `"ADMIN_URL"`).
    +  - `test_adds_trailing_slash` (`"staff"` → `"staff/"`).
    +  - `test_strips_slashes_and_spaces` (`" /staff/ "` → `"staff/"`).
    +  - `test_nested_path_allowed` (`"x/staff"` → `"x/staff/"`).
    +  - `test_invalid_characters_raise` — subTests for `"a//b"`, `"../x"`, `"st aff"`, `"staff?x=1"`.
    +
    +### 6.2 `core/views.py`
    +
    +#### `class HomeView(TemplateView)`
    +- Purpose: placeholder home page.
    +- `template_name = "core/home.html"`. No other code.
    +- Access: public.
    +- Tests (`core/tests/test_views.py`, `TestCase`):
    +  - `test_home_status_and_templates`: `GET reverse("core:home")` → 200; `assertTemplateUsed` for `"core/home.html"` and `"base.html"`.
    +  - `test_home_base_layout`: response contains `lang="ru"`, `name="viewport"`, `<header`, `<nav`, `<main`, `<footer`, and the exact disclaimer text from 5.6.
    +  - `test_home_css_layers_in_order`: positions of `css/tokens.css` < `css/base.css` < `css/theme.css` in the content.
    +  - `test_home_has_no_external_resources`: content does not contain `"http://"` or `"https://"`.
    +
    +#### `def health(request: HttpRequest) -> JsonResponse`
    +- Purpose: liveness check for server monitoring.
    +- Decorators (outermost first): `@never_cache`, `@require_GET`.
    +- Algorithm: return `JsonResponse({"status": "ok"})`. No DB access, no other data (no version, no hostnames, no settings).
    +- `HEAD` is allowed by `require_GET`; other methods → 405.
    +- Access: public.
    +- Tests:
    +  - `test_health_ok`: 200, `response["Content-Type"] == "application/json"`, `response.json() == {"status": "ok"}`.
    +  - `test_health_no_cache`: `"no-cache"` in `response["Cache-Control"]` (or `"max-age=0"`).
    +  - `test_health_rejects_post`: `POST` → 405.
    +  - `test_health_no_db_queries`: `with self.assertNumQueries(0)`.
    +
    +### 6.3 Settings tests (`core/tests/test_settings.py`, `SimpleTestCase`)
    +
    +- `test_locale`: `LANGUAGE_CODE == "ru"`, `TIME_ZONE == "Europe/Moscow"`, `USE_TZ is True`.
    +- `test_password_validators_enabled`: the 4 default validator class paths are all present in `AUTH_PASSWORD_VALIDATORS`.
    +- `test_admin_mounted_at_admin_url`: `reverse("admin:index") == "/" + settings.ADMIN_URL`.
    +- `test_whitenoise_after_security_middleware`: `MIDDLEWARE.index("whitenoise.middleware.WhiteNoiseMiddleware") == MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1`.
    +- `test_only_w021_silenced`: `SILENCED_SYSTEM_CHECKS == ["security.W021"]`.
    +
    +---
    +
    +## 7. Implementation order
    +
    +Run every command from the repo root with `.venv` activated and `export DEBUG=true` set in your shell (the settings default is DEBUG=false; you must not edit `.env`).
    +
    +1. Create `.venv` with `/opt/homebrew/bin/python3.12 -m venv .venv`. Write `requirements.txt`, `requirements-dev.txt`; `pip install -r requirements-dev.txt`. Verify: `python -c "import django; print(django.get_version())"` → `5.2.19`.
    +2. Write `pyproject.toml`. Verify: `ruff --version` → `0.17.4`.
    +3. Write `config/env_utils.py` and `core/tests/test_env_utils.py` (plus `core/__init__.py`, `core/tests/__init__.py`). Verify later in step 6.
    +4. Write `manage.py`, `config/*` (settings per 5.2, urls per 5.4), `core/apps.py`, `core/urls.py`, `core/views.py`. Verify: `python manage.py check`.
    +5. Write templates (5.6) and CSS (5.7). Verify: `python manage.py runserver`, open `/` and `/health/`.
    +6. Write `core/tests/test_views.py`, `core/tests/test_settings.py`. Verify: `python manage.py test` → all pass.
    +7. Write `.env.example`, `README.md`. Verify deploy check (section 8, command 4).
    +8. Write `.github/workflows/ci.yml`. Verify YAML (section 8, command 7).
    +9. Run `ruff format .` then the full verification list in section 8. All must pass. Then send the `REPORT` to the Reviewer.
    +
    +## 8. Verification
    +
    +```bash
    +source .venv/bin/activate
    +export DEBUG=true
    +python manage.py check                                     # 1: no issues
    +python manage.py makemigrations --check --dry-run          # 2: No changes detected
    +python manage.py test                                      # 3: OK
    +DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
    +  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
    +  python manage.py check --deploy --fail-level WARNING     # 4: exit 0, "(1 silenced)"
    +DEBUG=false SECRET_KEY= python manage.py check; echo "exit=$?"   # 5: ImproperlyConfigured mentioning SECRET_KEY, exit != 0
    +ruff check . && ruff format --check .                      # 6: clean
    +python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"  # 7
    +```
    +Command 5 sets `SECRET_KEY=` explicitly (empty) so a value from `.env` cannot hide the failure; an empty real env var wins over `.env` because `read_env` does not overwrite existing variables.
    +
    +Manual: `python manage.py runserver`, open `http://127.0.0.1:8000/` in browser dev tools at 360 px width → no horizontal scroll; footer disclaimer visible.
    +
    +In the `REPORT`, paste the output tail of commands 1–7.
    +
    +---
    +
    +## 9. Risks
    +
    +- **Secrets**: `.env` holds unrelated API keys. Settings load it into the process environment but must never log or print env values. Agents must not open `.env`; use shell `export` for verification.
    +- **`SECURE_PROXY_SSL_HEADER`** is safe only if nginx always sets (overwrites) `X-Forwarded-Proto`. The future deployment task must configure nginx with `proxy_set_header X-Forwarded-Proto $scheme;`.
    +- **HSTS**: default 1 hour on purpose for the first deploy (17.11); raise after HTTPS is stable. Preload stays off.
    +- **Custom user model (important for next tasks)**: this skeleton uses `auth.User`. The next task that adds users/roles must define `AUTH_USER_MODEL` before any app migration depends on users, and the local `db.sqlite3` must then be recreated. No production DB exists yet, so this costs nothing now.
    +- **Static storage switch** depends on DEBUG: production must run `python manage.py collectstatic --noinput` before start, otherwise pages with `{% static %}` return 500.
    +- **SQLite relative path in `.env.example`**: commands must run from the repo root.
  ── Thought for 4s
    I'm going to fix the middleware list, since the LocaleMiddleware note reads badly. I'm also checking whether the S105 hardcoded-password rule applies to the `SECRET_KEY` settings and the `DEV_SECRET_KEY` in env_utils; that one I'm treating as ignored. The CI dummy in the YAML isn't linted, and the per-file test ignores look fine.

    I'm now checking whether HEAD requests should be allowed on the health endpoint. Django's `require_GET` only accepts GET, while `require_safe` also allows HEAD, so the note should say HEAD gets a 405 rather than a 200. The no-cache headers and the JSON content type also check out.

── Assistant ───────────────────────────────────────────────
Пишу спецификацию TASK-001. Черновик готов. Исправляю две неточности и передаю задачу кодеру.

── Edited 1 file ───────────────────────────────────────────
  ── Edited docs/tasks/TASK-001.md +1 -2
    --- a~/hackatonproject/docs/tasks/TASK-001.md
    +++ b~/hackatonproject/docs/tasks/TASK-001.md
    -   "django.middleware.locale.LocaleMiddleware" -> NOT added (single language),
    -   (Do not add LocaleMiddleware; the line above is only a note.)
    +   Do not add `LocaleMiddleware` (single language).
  ── Edited docs/tasks/TASK-001.md +1 -1
    --- a~/hackatonproject/docs/tasks/TASK-001.md
    +++ b~/hackatonproject/docs/tasks/TASK-001.md
    -- `HEAD` is allowed by `require_GET`; other methods → 405.
    +- `require_GET` allows only `GET`; every other method (including `HEAD`, `POST`) → 405.
  ── Thought for 6ms
    I'm checking the settings: the ALLOWED_HOSTS list default and the admin URL test both look fine. The .env.example database URL is also fine. My one concern is that DEBUG gets set to true at import while the test runner turns it off, though testserver is already in ALLOWED_HOSTS, so that should be okay.

    Handing off to the coder now.

── Ran bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-001] Planner -> Coder: TASK Spec: docs/tasks/TASK-001.md (approved by the Team lead). Summary: - Build a Django 5.2.19 skeleton: project package `config`, one app `core` (no models), env-based settings via django-environ, WhiteNoise, ruff, GitHub Actions CI. - Exact pins, file tree, settings order, function signatures (`config/env_utils.py`), views, templates, CSS layers, `.env.example` and `ci.yml` are all in the spec. Follow them literally. - Use `/opt/homebrew/bin/python3.12` for `.venv`. Run commands with `export DEBUG=true`. Never open or edit `.env`. - Follow section 7 (implementation order). Run all of section 8 before you send the REPORT to the Reviewer. - If something is unclear or a pin does not install, send a QUESTION to me. Do not decide it yourself. EOF (1s)
  $ bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
[TASK-001] Planner -> Coder: TASK
Spec: docs/tasks/TASK-001.md (approved by the Team lead).
Summary:
- Build a Django 5.2.19 skeleton: project package `config`, one app `core` (no models), env-based settings via django-environ, WhiteNoise, ruff, GitHub Actions CI.
- Exact pins, file tree, settings order, function signatures (`config/env_utils.py`), views, templates, CSS layers, `.env.example` and `ci.yml` are all in the spec. Follow them literally.
- Use `/opt/homebrew/bin/python3.12` for `.venv`. Run commands with `export DEBUG=true`. Never open or edit `.env`.
- Follow section 7 (implementation order). Run all of section 8 before you send the REPORT to the Reviewer.
- If something is unclear or a pin does not install, send a QUESTION to me. Do not decide it yourself.
EOF
  Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Спецификация TASK-001 готова: [docs/tasks/TASK-001.md](docs/tasks/TASK-001.md). Я передал её кодеру (`thr_ng6cbgatm6`). Проверок пока не было: код ещё не написан.

Решения, которых не было в задаче тимлида:
- **Версии:** Django 5.2.19, django-environ 0.14.0, whitenoise 6.12.0, psycopg[binary] 3.3.8, ruff 0.17.4. Для проверки синтаксиса CI добавлен PyYAML 6.0.3, только для разработки. Последние версии я сверил на PyPI.
- **Проверки на старте:** при `DEBUG=false` настройки не запустятся без `SECRET_KEY` и без `ADMIN_URL`. Обе проверки — две отдельные функции в `config/env_utils.py`, у каждой свои тесты.
- **Предупреждения `check --deploy`:** проверка должна пройти без предупреждений. Исключение одно: отключена проверка W021 (HSTS preload). Причина: включить preload — обязательство, которое нельзя отменить. Для прототипа к конкурсу оно не нужно.
- **Время HSTS:** по умолчанию 1 час, чтобы пробный деплой 17.11 прошёл безопасно. Значение меняется через переменную окружения.
- **Хранение статики:** при `DEBUG=true` используется обычное хранилище, иначе версия WhiteNoise с хешами в именах файлов. Хешированной версии нужен `collectstatic`, а в тестах его нет.
- **Проверка `/health/` без HTTPS:** адрес исключён из перенаправления на HTTPS, чтобы мониторинг на сервере мог обращаться к нему по HTTP.

Решение для следующих задач: каркас использует стандартную модель пользователя Django. Задача про пользователей и роли должна первой задать свою модель через `AUTH_USER_MODEL`. После этого локальную `db.sqlite3` нужно создать заново. Сейчас это ничего не стоит: рабочей базы ещё нет.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[SETUP] Team lead -> all: PROTOCOL UPDATE
New rule (see "Git and commits" in `.bb/AGENTS.md`): only the Team lead commits. Never run `git commit`, `git push`, `git stash`, `git checkout`, `git reset` or any command that changes git history or the index. Coder: keep all TASK-001 changes uncommitted. Reviewer: review uncommitted changes including untracked files. Do not reply to this message.

── Thought for 6ms ─────────────────────────────────────────
  The spec already rules out committing to git, so that's settled and nothing needs changing. I don't need to reply yet; a brief acknowledgement to the user will do.

── Assistant ───────────────────────────────────────────────
Правило о git на мою работу не влияет: я не делаю коммитов и не меняю индекс. В спецификации TASK-001 коммиты уже вынесены за рамки задачи. Тимлиду не отвечаю, он просил не отвечать. Жду вопросов от кодера.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[SETUP] Team lead -> all: PROTOCOL UPDATE
New message type `TEST PROPOSAL` (see `.bb/AGENTS.md` workflow step 7 and the "Test proposals" section in `.claude/agents/reviewer.md`). Reviewer: when the spec lacks tests that are really necessary, send a `TEST PROPOSAL` to the Team lead instead of `APPROVE`. Planner: you may receive "Spec amendment: additional tests" for an existing task; add the tests to the same spec and hand them to the Coder. Do not reply to this message.

── Assistant ───────────────────────────────────────────────
Понял новое правило. Если тимлид пришлёт «Spec amendment: additional tests», я допишу эти тесты в ту же спецификацию и передам кодеру. Тимлиду не отвечаю, он просил не отвечать.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-001] Team lead -> Planner: TASK
Spec amendment: additional tests (accepted from a Reviewer TEST PROPOSAL; no user approval needed under the protocol).

TASK-001 is already committed (2492a70). Add a new section to `docs/tasks/TASK-001.md` ("Amendment 1: production settings tests") and hand it to the Coder. Only tests change; no production code changes unless a test reveals a real defect (then report it in the REPORT, do not redesign).

Gap: all current tests run with DEBUG=true, so the production branch of `config/settings.py` (the `if not DEBUG:` block) and the DEBUG default are never exercised.

Add `core/tests/test_production_settings.py` (SimpleTestCase) with:
1. test_debug_defaults_to_false - with DEBUG and SECRET_KEY absent from the environment and `.env` reading disabled: DEBUG is False and loading settings raises ImproperlyConfigured about SECRET_KEY.
2. test_health_exempt_from_ssl_redirect_in_production - production env (DEBUG=false, dummy SECRET_KEY, ALLOWED_HOSTS=testserver, ADMIN_URL=staff-panel/); apply the loaded SECURE_SSL_REDIRECT / SECURE_REDIRECT_EXEMPT via override_settings; plain-HTTP GET /health/ -> 200 {"status": "ok"}; GET / -> 301 to https://.
3. test_production_security_flags - same production env: SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE are True; SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https"); ALLOWED_HOSTS == ["testserver"] (no debug defaults leak); static storage is WhiteNoise CompressedManifestStaticFilesStorage.

Mechanism (your decision; Reviewer's suggestion): settings are evaluated at import, so use a hermetic loader - `importlib.util.spec_from_file_location` on `config/settings.py` under a private module name, inside `mock.patch.dict(os.environ, ..., clear=True)`, with `environ.Env.read_env` patched to a no-op so the developer's real `.env` cannot affect results. Avoid subprocess (ruff S603/S607).

Verification: all TASK-001 verification commands pass; test count grows by 3.

── Ran 3 commands ──────────────────────────────────────────
  ── Thought for 6ms
    I'm going to read the current spec, which has changed on disk, along with the current settings.py so the design matches what's actually there.
  ── Ran git log --oneline | head -3 && cat config/settings.py && ls core/tests && tail -40 docs/tasks/TASK-001.md && git diff 2492a70 --stat (1s)
    $ git log --oneline | head -3 && cat config/settings.py && ls core/tests && tail -40 docs/tasks/TASK-001.md && git diff 2492a70 --stat
    42f5465 Team protocol: reviewer test proposals
    2492a70 TASK-001: Django skeleton and CI
    bd9d1c1 Team protocol: lead-only commits, changelog, agreed project plan
    """Django settings for the Digital Dean's Office of the Future prototype."""

    from pathlib import Path

    import environ

    from config.env_utils import resolve_admin_url, resolve_secret_key

    BASE_DIR = Path(__file__).resolve().parent.parent
    env = environ.Env()
    _env_file = BASE_DIR / ".env"
    if _env_file.is_file():
        environ.Env.read_env(_env_file)

    # Core flags
    DEBUG = env.bool("DEBUG", default=False)
    SECRET_KEY = resolve_secret_key(env.str("SECRET_KEY", default=""), DEBUG)
    ALLOWED_HOSTS = env.list(
        "ALLOWED_HOSTS",
        default=["localhost", "127.0.0.1", "[::1]"] if DEBUG else [],
    )
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
    ADMIN_URL = resolve_admin_url(env.str("ADMIN_URL", default=""), DEBUG)

    INSTALLED_APPS = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "whitenoise.runserver_nostatic",
        "django.contrib.staticfiles",
        "core",
    ]

    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]

    ROOT_URLCONF = "config.urls"
    WSGI_APPLICATION = "config.wsgi.application"
    ASGI_APPLICATION = "config.asgi.application"

    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [BASE_DIR / "templates"],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        },
    ]

    DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
    DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

    AUTH_PASSWORD_VALIDATORS = [
        {
            "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
        },
    ]

    LANGUAGE_CODE = "ru"
    TIME_ZONE = "Europe/Moscow"
    USE_I18N = True
    USE_TZ = True

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

    # Security
    X_FRAME_OPTIONS = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    SESSION_COOKIE_HTTPONLY = True

    if not DEBUG:
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
        SECURE_REDIRECT_EXEMPT = [r"^health/$"]
        SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
        SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
        SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)

    # security.W021: HSTS preload is an irreversible browser-list commitment.
    # A contest prototype must not opt in. Enable via SECURE_HSTS_PRELOAD only deliberately.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]

    LOG_LEVEL = env.str("LOG_LEVEL", default="INFO").upper()
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"simple": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
        "root": {"handlers": ["console"], "level": LOG_LEVEL},
        "loggers": {"django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False}},
    }
    __init__.py
    __pycache__
    test_env_utils.py
    test_settings.py
    test_views.py
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
     .bb/AGENTS.md              | 9 +++++----
     .bb/roles/lead.md          | 6 ++++++
     .claude/agents/reviewer.md | 7 +++++++
     CHANGELOG.md               | 4 ++++
     4 files changed, 22 insertions(+), 4 deletions(-)
  ── Thought for 15s
    Now I'm sketching a loader helper in the test module that builds a settings module from the settings file path, using the importlib spec machinery.

    Checking whether the partial module keeps its attributes when exec raises, since that decides how I can assert DEBUG is False in the first test.

    I'm settling on a helper split: one function to create a fresh settings module, another to exec it with given env vars, plus a convenience loader for production settings. That way, when the exec raises, I can still inspect DEBUG on the partially built module. For the second test, I'm noting that the security middleware reads its settings at construction time, and the test client's handler builds the middleware chain on first request, so the overrides have to be in place before that happens.

    Checking the redirect path next: the test client builds its middleware chain lazily on the first request, so entering `override_settings` as a context manager inside the test should be enough, and I'll create a fresh `Client()` there to be safe. The request is plain HTTP, so `/` should return a 301 with a `Location` starting with `https://testserver/`.

    Now I'm checking the redirect test: the exempt pattern should match the health path, so that route stays on plain HTTP. I'll also assert that the production `SECURE_SSL_REDIRECT` is True before relying on it.

    Still writing the production env fixture and checking the dummy secret key against the test lint rules, which are relaxed for tests.

    Adding a third test is next, and I'm planning to write the amendment for it now, since the count goes up by three.
  ── Ran cat >> docs/tasks/TASK-001.md <<'EOF' --- ## Amendment 1: production settings tests Source: Team lead, accepted Reviewer `TEST PROPOSAL`. Base commit: `2492a70`. ### A1.1 Goal All existing tests run with `DEBUG=true`, so the `DEBUG` default and the `if not DEBUG:` block of `config/settings.py` are never exercised. Add 3 tests that load the settings module hermetically with a production environment. ### A1.2 Scope - Create only `core/tests/test_production_settings.py`. - Do not change production code. If a test reveals a real defect in `config/settings.py`, keep the failing test, describe the defect in the `REPORT`, and do not redesign anything. A minimal fix is allowed only if it keeps every design decision of this spec; describe it in the `REPORT`. - No subprocess (ruff S603/S607). No new dependencies. ### A1.3 Mechanism (hermetic settings loader) `config/settings.py` is evaluated at import time, so the tests execute a **fresh copy** of the file under a private module name. The copy is never put into `sys.modules` and never touches `django.conf.settings`. Module-level code in `core/tests/test_production_settings.py`: ```python import importlib.util import os from pathlib import Path from types import ModuleType from unittest import mock import environ from django.conf import settings from django.core.exceptions import ImproperlyConfigured from django.test import Client, SimpleTestCase, override_settings SETTINGS_PATH = Path(settings.BASE_DIR) / "config" / "settings.py" PRODUCTION_ENV = {     "DEBUG": "false",     "SECRET_KEY": "test-dummy-secret-key-not-for-production-0123456789abcdefghij",     "ALLOWED_HOSTS": "testserver",     "ADMIN_URL": "staff-panel/", } ``` #### `_new_settings_module() -> ModuleType` - Purpose: create an empty module object for `config/settings.py` without executing it. - Algorithm:   1. `spec = importlib.util.spec_from_file_location("_hermetic_settings", SETTINGS_PATH)`.   2. `assert spec is not None and spec.loader is not None`.   3. Return `importlib.util.module_from_spec(spec)`. - Do not add the module to `sys.modules`. #### `_exec_settings(module: ModuleType, env_vars: dict[str, str]) -> None` - Purpose: execute the settings file in `module` with exactly `env_vars` as the process environment and with `.env` reading disabled. - Algorithm:   1. Enter `mock.patch.dict(os.environ, env_vars, clear=True)`.   2. Enter `mock.patch.object(environ.Env, "read_env", return_value=None)` — the developer's real `.env` must not affect results.   3. Call `module.__spec__.loader.exec_module(module)`.   4. Exceptions from step 3 propagate to the caller. Both patches are undone on exit (use `with`). - Edge case: if `exec_module` raises, attributes assigned before the error (for example `DEBUG`) stay on `module`. Test 1 relies on this. #### `_load_production_settings() -> ModuleType` - Purpose: convenience for tests 2 and 3. - Algorithm: `module = _new_settings_module()`; `_exec_settings(module, PRODUCTION_ENV)`; return `module`. ### A1.4 Tests (`class ProductionSettingsTests(SimpleTestCase)`) #### 1. `test_debug_defaults_to_false` 1. `module = _new_settings_module()`. 2. `with self.assertRaisesMessage(ImproperlyConfigured, "SECRET_KEY"): _exec_settings(module, {})`. 3. `self.assertIs(module.DEBUG, False)`. #### 2. `test_health_exempt_from_ssl_redirect_in_production` 1. `prod = _load_production_settings()`. 2. `self.assertIs(prod.SECURE_SSL_REDIRECT, True)` (default when the env var is unset). 3. Inside `with override_settings(SECURE_SSL_REDIRECT=prod.SECURE_SSL_REDIRECT, SECURE_REDIRECT_EXEMPT=prod.SECURE_REDIRECT_EXEMPT, SECURE_PROXY_SSL_HEADER=prod.SECURE_PROXY_SSL_HEADER):`    - create a new `client = Client()` **inside** the `with` block (the middleware chain reads settings when it is built);    - `response = client.get("/health/")` (plain HTTP, no `X-Forwarded-Proto` header) → `status_code == 200`, `response.json() == {"status": "ok"}`;    - `response = client.get("/")` → `status_code == 301`, `response["Location"] == "https://testserver/"`. - Use literal paths `"/health/"` and `"/"` (not `reverse`) because the test checks the real URL that the exemption regex matches. #### 3. `test_production_security_flags` 1. `prod = _load_production_settings()`. 2. Assert:    - `prod.DEBUG is False`;    - `prod.SESSION_COOKIE_SECURE is True`, `prod.CSRF_COOKIE_SECURE is True`;    - `prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")`;    - `prod.ALLOWED_HOSTS == ["testserver"]` (debug defaults must not leak);    - `prod.ADMIN_URL == "staff-panel/"`;    - `prod.STORAGES["staticfiles"]["BACKEND"] == "whitenoise.storage.CompressedManifestStaticFilesStorage"`. ### A1.5 Implementation order 1. Write `core/tests/test_production_settings.py` per A1.3–A1.4. 2. `DEBUG=true python manage.py test core.tests.test_production_settings -v 2` → 3 tests OK. 3. `ruff format .` then run all of section 8. `python manage.py test` count = previous count + 3. 4. Run `python manage.py test` a second time and confirm `git status --short` shows only the new test file (the loader must not create files or change the environment). 5. Send the `REPORT` to the Reviewer. Do not commit (only the Team lead commits). ### A1.6 Risks - `mock.patch.dict(..., clear=True)` empties `os.environ` only for the duration of `exec_module`; it is restored on exit even on exceptions. Do not run anything else inside that block. - If a future change makes `config/settings.py` import other project modules with import-time side effects, this loader runs them again. Keep settings free of side effects. EOF bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-001] Planner -> Coder: TASK Spec amendment: docs/tasks/TASK-001.md, section "Amendment 1: production settings tests". Summary: - Add only `core/tests/test_production_settings.py` with 3 tests that load `config/settings.py` hermetically (importlib under a private name, `os.environ` patched with `clear=True`, `environ.Env.read_env` patched to a no-op). - Helper functions, exact env values and assertions are in A1.3-A1.4. Follow them literally. - No production code changes. If a test reveals a real defect, report it in the REPORT; do not redesign. - Run A1.5 and all of section 8; test count grows by 3. Do not commit. Send the REPORT to the Reviewer. EOF (2s)
    $ cat >> docs/tasks/TASK-001.md <<'EOF'

  ---

  ## Amendment 1: production settings tests

  Source: Team lead, accepted Reviewer `TEST PROPOSAL`. Base commit: `2492a70`.

  ### A1.1 Goal
  All existing tests run with `DEBUG=true`, so the `DEBUG` default and the `if not DEBUG:` block of `config/settings.py` are never exercised. Add 3 tests that load the settings module hermetically with a production environment.

  ### A1.2 Scope
  - Create only `core/tests/test_production_settings.py`.
  - Do not change production code. If a test reveals a real defect in `config/settings.py`, keep the failing test, describe the defect in the `REPORT`, and do not redesign anything. A minimal fix is allowed only if it keeps every design decision of this spec; describe it in the `REPORT`.
  - No subprocess (ruff S603/S607). No new dependencies.

  ### A1.3 Mechanism (hermetic settings loader)
  `config/settings.py` is evaluated at import time, so the tests execute a **fresh copy** of the file under a private module name. The copy is never put into `sys.modules` and never touches `django.conf.settings`.

  Module-level code in `core/tests/test_production_settings.py`:

  ```python
  import importlib.util
  import os
  from pathlib import Path
  from types import ModuleType
  from unittest import mock

  import environ
  from django.conf import settings
  from django.core.exceptions import ImproperlyConfigured
  from django.test import Client, SimpleTestCase, override_settings

  SETTINGS_PATH = Path(settings.BASE_DIR) / "config" / "settings.py"

  PRODUCTION_ENV = {
      "DEBUG": "false",
      "SECRET_KEY": "test-dummy-secret-key-not-for-production-0123456789abcdefghij",
      "ALLOWED_HOSTS": "testserver",
      "ADMIN_URL": "staff-panel/",
  }
  ```

  #### `_new_settings_module() -> ModuleType`
  - Purpose: create an empty module object for `config/settings.py` without executing it.
  - Algorithm:
    1. `spec = importlib.util.spec_from_file_location("_hermetic_settings", SETTINGS_PATH)`.
    2. `assert spec is not None and spec.loader is not None`.
    3. Return `importlib.util.module_from_spec(spec)`.
  - Do not add the module to `sys.modules`.

  #### `_exec_settings(module: ModuleType, env_vars: dict[str, str]) -> None`
  - Purpose: execute the settings file in `module` with exactly `env_vars` as the process environment and with `.env` reading disabled.
  - Algorithm:
    1. Enter `mock.patch.dict(os.environ, env_vars, clear=True)`.
    2. Enter `mock.patch.object(environ.Env, "read_env", return_value=None)` — the developer's real `.env` must not affect results.
    3. Call `module.__spec__.loader.exec_module(module)`.
    4. Exceptions from step 3 propagate to the caller. Both patches are undone on exit (use `with`).
  - Edge case: if `exec_module` raises, attributes assigned before the error (for example `DEBUG`) stay on `module`. Test 1 relies on this.

  #### `_load_production_settings() -> ModuleType`
  - Purpose: convenience for tests 2 and 3.
  - Algorithm: `module = _new_settings_module()`; `_exec_settings(module, PRODUCTION_ENV)`; return `module`.

  ### A1.4 Tests (`class ProductionSettingsTests(SimpleTestCase)`)

  #### 1. `test_debug_defaults_to_false`
  1. `module = _new_settings_module()`.
  2. `with self.assertRaisesMessage(ImproperlyConfigured, "SECRET_KEY"): _exec_settings(module, {})`.
  3. `self.assertIs(module.DEBUG, False)`.

  #### 2. `test_health_exempt_from_ssl_redirect_in_production`
  1. `prod = _load_production_settings()`.
  2. `self.assertIs(prod.SECURE_SSL_REDIRECT, True)` (default when the env var is unset).
  3. Inside `with override_settings(SECURE_SSL_REDIRECT=prod.SECURE_SSL_REDIRECT, SECURE_REDIRECT_EXEMPT=prod.SECURE_REDIRECT_EXEMPT, SECURE_PROXY_SSL_HEADER=prod.SECURE_PROXY_SSL_HEADER):`
     - create a new `client = Client()` **inside** the `with` block (the middleware chain reads settings when it is built);
     - `response = client.get("/health/")` (plain HTTP, no `X-Forwarded-Proto` header) → `status_code == 200`, `response.json() == {"status": "ok"}`;
     - `response = client.get("/")` → `status_code == 301`, `response["Location"] == "https://testserver/"`.
  - Use literal paths `"/health/"` and `"/"` (not `reverse`) because the test checks the real URL that the exemption regex matches.

  #### 3. `test_production_security_flags`
  1. `prod = _load_production_settings()`.
  2. Assert:
     - `prod.DEBUG is False`;
     - `prod.SESSION_COOKIE_SECURE is True`, `prod.CSRF_COOKIE_SECURE is True`;
     - `prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")`;
     - `prod.ALLOWED_HOSTS == ["testserver"]` (debug defaults must not leak);
     - `prod.ADMIN_URL == "staff-panel/"`;
     - `prod.STORAGES["staticfiles"]["BACKEND"] == "whitenoise.storage.CompressedManifestStaticFilesStorage"`.

  ### A1.5 Implementation order
  1. Write `core/tests/test_production_settings.py` per A1.3–A1.4.
  2. `DEBUG=true python manage.py test core.tests.test_production_settings -v 2` → 3 tests OK.
  3. `ruff format .` then run all of section 8. `python manage.py test` count = previous count + 3.
  4. Run `python manage.py test` a second time and confirm `git status --short` shows only the new test file (the loader must not create files or change the environment).
  5. Send the `REPORT` to the Reviewer. Do not commit (only the Team lead commits).

  ### A1.6 Risks
  - `mock.patch.dict(..., clear=True)` empties `os.environ` only for the duration of `exec_module`; it is restored on exit even on exceptions. Do not run anything else inside that block.
  - If a future change makes `config/settings.py` import other project modules with import-time side effects, this loader runs them again. Keep settings free of side effects.
  EOF
  bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
  [TASK-001] Planner -> Coder: TASK
  Spec amendment: docs/tasks/TASK-001.md, section "Amendment 1: production settings tests".
  Summary:
  - Add only `core/tests/test_production_settings.py` with 3 tests that load `config/settings.py` hermetically (importlib under a private name, `os.environ` patched with `clear=True`, `environ.Env.read_env` patched to a no-op).
  - Helper functions, exact env values and assertions are in A1.3-A1.4. Follow them literally.
  - No production code changes. If a test reveals a real defect, report it in the REPORT; do not redesign.
  - Run A1.5 and all of section 8; test count grows by 3. Do not commit. Send the REPORT to the Reviewer.
  EOF
    Thread thr_ng6cbgatm6 steered
    [This command modified 1 file you've previously read: docs/tasks/TASK-001.md. Call Read before editing.]
  ── Thought for 520ms
    I'm wondering whether to quickly verify the mechanism, maybe with a throwaway experiment in TMPDIR so the repo stays untouched. I'd use the .venv and run a short script that sets up Django, focusing on the read_env patch and the Client override, while making sure .env contents never get printed.
  ── Thought
    Сейчас проверю, что предложенный способ загрузки настроек работает на текущем коде, а скрипт создам во временной папке, не трогая проект.
  ── Ran mkdir -p "$TMPDIR/a1" && cat > "$TMPDIR/a1/test_a1_probe.py" <<'EOF' import importlib.util, os from pathlib import Path from unittest import mock import environ from django.conf import settings from django.core.exceptions import ImproperlyConfigured from django.test import Client, SimpleTestCase, override_settings P = Path(settings.BASE_DIR) / "config" / "settings.py" ENV = {"DEBUG":"false","SECRET_KEY":"x"*60,"ALLOWED_HOSTS":"testserver","ADMIN_URL":"staff-panel/"} def new():     s = importlib.util.spec_from_file_location("_hermetic_settings", P); return importlib.util.module_from_spec(s) def run(m, e):     with mock.patch.dict(os.environ, e, clear=True), mock.patch.object(environ.Env, "read_env", return_value=None):         m.__spec__.loader.exec_module(m) class T(SimpleTestCase):     def test_1(self):         m = new()         with self.assertRaisesMessage(ImproperlyConfigured, "SECRET_KEY"): run(m, {})         self.assertIs(m.DEBUG, False)     def test_2(self):         p = new(); run(p, ENV)         with override_settings(SECURE_SSL_REDIRECT=p.SECURE_SSL_REDIRECT, SECURE_REDIRECT_EXEMPT=p.SECURE_REDIRECT_EXEMPT, SECURE_PROXY_SSL_HEADER=p.SECURE_PROXY_SSL_HEADER):             c = Client(); r = c.get("/health/"); self.assertEqual(r.status_code, 200); self.assertEqual(r.json(), {"status":"ok"})             r = c.get("/"); self.assertEqual(r.status_code, 301); self.assertEqual(r["Location"], "https://testserver/")     def test_3(self):         p = new(); run(p, ENV)         self.assertEqual(p.ALLOWED_HOSTS, ["testserver"]); self.assertEqual(p.STORAGES["staticfiles"]["BACKEND"], "whitenoise.storage.CompressedManifestStaticFilesStorage") EOF cd "$TMPDIR/a1" && DEBUG=true PYTHONPATH=~/hackatonproject DJANGO_SETTINGS_MODULE=config.settings ~/hackatonproject/.venv/bin/python -c " import django,sys;django.setup() from django.test.utils import get_runner from django.conf import settings R=get_runner(settings)(verbosity=1);sys.exit(R.run_tests(['test_a1_probe']))" 2>&1 | tail -5 (1s)
    $ mkdir -p "$TMPDIR/a1" && cat > "$TMPDIR/a1/test_a1_probe.py" <<'EOF'
  import importlib.util, os
  from pathlib import Path
  from unittest import mock
  import environ
  from django.conf import settings
  from django.core.exceptions import ImproperlyConfigured
  from django.test import Client, SimpleTestCase, override_settings
  P = Path(settings.BASE_DIR) / "config" / "settings.py"
  ENV = {"DEBUG":"false","SECRET_KEY":"x"*60,"ALLOWED_HOSTS":"testserver","ADMIN_URL":"staff-panel/"}
  def new():
      s = importlib.util.spec_from_file_location("_hermetic_settings", P); return importlib.util.module_from_spec(s)
  def run(m, e):
      with mock.patch.dict(os.environ, e, clear=True), mock.patch.object(environ.Env, "read_env", return_value=None):
          m.__spec__.loader.exec_module(m)
  class T(SimpleTestCase):
      def test_1(self):
          m = new()
          with self.assertRaisesMessage(ImproperlyConfigured, "SECRET_KEY"): run(m, {})
          self.assertIs(m.DEBUG, False)
      def test_2(self):
          p = new(); run(p, ENV)
          with override_settings(SECURE_SSL_REDIRECT=p.SECURE_SSL_REDIRECT, SECURE_REDIRECT_EXEMPT=p.SECURE_REDIRECT_EXEMPT, SECURE_PROXY_SSL_HEADER=p.SECURE_PROXY_SSL_HEADER):
              c = Client(); r = c.get("/health/"); self.assertEqual(r.status_code, 200); self.assertEqual(r.json(), {"status":"ok"})
              r = c.get("/"); self.assertEqual(r.status_code, 301); self.assertEqual(r["Location"], "https://testserver/")
      def test_3(self):
          p = new(); run(p, ENV)
          self.assertEqual(p.ALLOWED_HOSTS, ["testserver"]); self.assertEqual(p.STORAGES["staticfiles"]["BACKEND"], "whitenoise.storage.CompressedManifestStaticFilesStorage")
  EOF
  cd "$TMPDIR/a1" && DEBUG=true PYTHONPATH=~/hackatonproject DJANGO_SETTINGS_MODULE=config.settings ~/hackatonproject/.venv/bin/python -c "
  import django,sys;django.setup()
  from django.test.utils import get_runner
  from django.conf import settings
  R=get_runner(settings)(verbosity=1);sys.exit(R.run_tests(['test_a1_probe']))" 2>&1 | tail -5
    Ran 3 tests in 0.007s

    OK
    Found 3 test(s).
    System check identified no issues (0 silenced).
    Shell cwd was reset to ~/hackatonproject
  ── Thought for 4s
    The fix works, so I'll clear out the temp files in TMPDIR and then write the report for the user in Russian. I'm not sure who the parent is, since the bb status output didn't show it, but the message came from the lead via tell, so I'll only reply if it's needed.

── Assistant ───────────────────────────────────────────────
Я дописал в [docs/tasks/TASK-001.md](docs/tasks/TASK-001.md) раздел «Amendment 1: production settings tests» и передал его кодеру.

Новые тесты проверяют рабочий режим, когда `DEBUG` выключен. Раньше все тесты шли только в режиме разработки. Кодер добавит один файл `core/tests/test_production_settings.py` с тремя тестами:

1. **Без `DEBUG` и `SECRET_KEY` в окружении.** `DEBUG` по умолчанию выключен, а запуск без `SECRET_KEY` падает с ошибкой.
2. **Перенаправление на HTTPS.** `/health/` отвечает по обычному HTTP. Главная страница `/` перенаправляет на `https://testserver/`.
3. **Флаги безопасности.** Cookie помечены как защищённые, задан заголовок от nginx, в `ALLOWED_HOSTS` нет значений из режима разработки, статика идёт через WhiteNoise.

Тесты загружают копию `config/settings.py` в отдельном окружении. Ваш `.env` на результат не влияет.

Этот способ я проверил на текущем коде пробным скриптом во временной папке, а не в проекте: все три теста прошли. Дефектов в настройках не нашлось.

Продуктовый код кодер не меняет и коммит не делает. После тестов он отправит отчёт ревьюеру.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-002] Team lead -> Planner: TASK
Approved by the user. Write the spec `docs/tasks/TASK-002.md` and hand it to the Coder.

## Context
TASK-001 is done (commit 2492a70): Django 5.2 skeleton, `config` + `core`, env settings, base template, CI. Read `plan.md` and `docs/tasks/TASK-001.md` (section 9 risks). This task creates the user foundation that every later feature (schedule, grades, requests, notifications, chat, map) depends on, so design the data model with those features in mind, but implement only what is listed here.

## Goal
Users, roles, profiles, login/logout and strict data isolation for both students and dean's-office staff.

## Requirements
1. Custom user model (AbstractUser) in a new app `accounts`, set as AUTH_USER_MODEL before any other model migrations. The local `db.sqlite3` may be deleted and recreated (development data only; approved by the Team lead).
2. Two roles: STUDENT and STAFF (dean's office employee). A user has exactly one role. Choose the representation (role field vs groups) and justify it.
3. University reference data in a separate app (e.g. `university`): Faculty, Program (field of study, belongs to a Faculty), StudyGroup (belongs to a Program, has course number 1-6). Schedule and grades will reference these later.
4. StudentProfile (one-to-one with user): full name parts (last, first, middle - optional), StudyGroup (faculty, program and course are derived from it, not duplicated), student record number (fictional).
   StaffProfile (one-to-one with user): full name parts, position, Faculty they serve.
5. Pages (server-rendered, Russian UI text, mobile-first using the existing base template and CSS layers; no visual theme yet):
   - Login page (username + password) and logout (POST only).
   - `/profile/` - the current user's own profile, for both roles. No user/profile ID in this URL.
   - Staff only: list of students of the staff member's own faculty, and a student detail page. A staff member must get 404 for a student of another faculty.
   - Navigation in the base template depends on the role.
6. Access control - default deny:
   - Every page requires login by default (use Django 5.1+ `LoginRequiredMiddleware`); only login and `/health/` are explicitly public.
   - Students: see only their own data. Any staff URL returns 403 or 404 for a student.
   - Staff: see only their own profile and students of their own faculty. A staff member never sees other staff members' profiles.
   - Use reusable role checks (mixins/decorators) and queryset scoping by the current user, so later tasks reuse the same pattern. No object lookup by raw ID without scoping.
   - Django admin is for the superuser (system operator) only. Neither students nor dean's-office staff get `is_staff`.
7. Passwords: Django default hashing and validators. No plain-text passwords anywhere (code, fixtures, logs, docs).
8. Demo data: an idempotent management command (e.g. `seed_demo`) that creates fictional reference data and at least: 2 students in different faculties and groups, 2 staff members in different faculties (to demonstrate isolation). Logins are fixed and documented in README; the password is taken from env variable `DEMO_PASSWORD` (add it to `.env.example`), and the command fails clearly if it is missing. All names and numbers are fictional.
9. Fix the TASK-001 review notes: in `core/tests/test_env_utils.py` assert `ImproperlyConfigured` instead of `Exception`; add the deploy-check and CI YAML commands to README "Test & lint".

## Tests (must exist)
- Anonymous user is redirected to login from every non-public page.
- Student A cannot see Student B's data by any URL.
- Student gets 403/404 on every staff page.
- Staff of faculty X gets 404 for a student of faculty Y; staff cannot see another staff profile.
- Logout works only via POST.
- Stored passwords are hashed; `seed_demo` is idempotent and fails without `DEMO_PASSWORD`.

## Out of scope
Schedule, grades, requests, notifications, chat, map. Password reset by email, registration, rate limiting of login attempts (later task). Visual theme.

## Verification
All TASK-001 verification commands still pass (check, deploy check, makemigrations --check, test, ruff, CI YAML) plus `python manage.py seed_demo` run twice without errors.

── Ran 1 command, explored 1 file ──────────────────────────
  ── Thought for 6ms
    I'm going through the current code to get oriented: the URLs, views, templates, tests, the README, test_env_utils, pyproject, and the Amendment status.
  ── Ran git log --oneline | head -5 && git status --short && ls -R config core templates static | grep -v pycache && cat config/urls.py core/urls.py core/views.py templates/base.html && cat core/tests/test_env_utils.py | head -40 && cat README.md && cat pyproject.toml && cat .env.example && sed -n 1,60p static/css/base.css (1s)
    $ git log --oneline | head -5 && git status --short && ls -R config core templates static | grep -v pycache && cat config/urls.py core/urls.py core/views.py templates/base.html && cat core/tests/test_env_utils.py | head -40 && cat README.md && cat pyproject.toml && cat .env.example && sed -n 1,60p static/css/base.css
    04b7f0c TASK-001: production settings tests (amendment 1)
    42f5465 Team protocol: reviewer test proposals
    2492a70 TASK-001: Django skeleton and CI
    bd9d1c1 Team protocol: lead-only commits, changelog, agreed project plan
    15e0748 Initial commit: agent team configuration
     M plan.md
    config:
    __init__.py
    asgi.py
    env_utils.py
    settings.py
    urls.py
    wsgi.py

    __init__.cpython-312.pyc
    env_utils.cpython-312.pyc
    settings.cpython-312.pyc
    urls.cpython-312.pyc

    core:
    __init__.py
    apps.py
    templates
    tests
    urls.py
    views.py

    __init__.cpython-312.pyc
    apps.cpython-312.pyc
    urls.cpython-312.pyc
    views.cpython-312.pyc

    core/templates:
    core

    core/templates/core:
    home.html

    core/tests:
    __init__.py
    test_env_utils.py
    test_production_settings.py
    test_settings.py
    test_views.py

    __init__.cpython-312.pyc
    test_env_utils.cpython-312.pyc
    test_production_settings.cpython-312.pyc
    test_settings.cpython-312.pyc
    test_views.cpython-312.pyc

    static:
    css

    static/css:
    base.css
    theme.css
    tokens.css

    templates:
    base.html
    """URL configuration for the deanery project."""

    from django.conf import settings
    from django.contrib import admin
    from django.urls import include, path

    urlpatterns = [
        path(settings.ADMIN_URL, admin.site.urls),
        path("", include("core.urls")),
    ]
    from django.urls import path

    from . import views

    app_name = "core"
    urlpatterns = [
        path("", views.HomeView.as_view(), name="home"),
        path("health/", views.health, name="health"),
    ]
    from django.http import HttpRequest, JsonResponse
    from django.views.decorators.cache import never_cache
    from django.views.decorators.http import require_GET
    from django.views.generic import TemplateView


    class HomeView(TemplateView):
        template_name = "core/home.html"


    @never_cache
    @require_GET
    def health(request: HttpRequest) -> JsonResponse:
        return JsonResponse({"status": "ok"})
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
    from django.core.exceptions import ImproperlyConfigured
    from django.test import SimpleTestCase

    from config.env_utils import (
        DEV_SECRET_KEY,
        resolve_admin_url,
        resolve_secret_key,
    )


    class ResolveSecretKeyTests(SimpleTestCase):
        def test_returns_given_key(self):
            self.assertEqual(resolve_secret_key("abc...", False), "abc...")

        def test_strips_whitespace(self):
            self.assertEqual(resolve_secret_key("  key  ", False), "key")

        def test_dev_fallback_when_debug(self):
            self.assertEqual(resolve_secret_key("", True), DEV_SECRET_KEY)

        def test_missing_key_in_production_raises(self):
            with self.assertRaisesMessage(Exception, "SECRET_KEY"):
                resolve_secret_key("", False)

        def test_whitespace_key_in_production_raises(self):
            with self.assertRaises(ImproperlyConfigured):
                resolve_secret_key("   ", False)


    class ResolveAdminUrlTests(SimpleTestCase):
        def test_default_in_debug(self):
            self.assertEqual(resolve_admin_url("", True), "admin/")

        def test_missing_in_production_raises(self):
            with self.assertRaisesMessage(Exception, "ADMIN_URL"):
                resolve_admin_url("", False)

        def test_adds_trailing_slash(self):
            self.assertEqual(resolve_admin_url("staff", False), "staff/")

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
    *,
    *::before,
    *::after {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: var(--font-body);
      font-size: var(--font-size-base);
      line-height: var(--line-height-base);
      background: var(--color-bg);
      color: var(--color-text);
      overflow-wrap: anywhere;
    }

    img,
    svg {
      max-width: 100%;
      height: auto;
    }

    .site-header,
    .site-main,
    .site-footer {
      padding: var(--space-3);
    }

    .site-main {
      max-width: var(--content-max-width);
      margin-inline: auto;
    }

    .skip-link {
      position: absolute;
      left: -10000px;
      top: auto;
      width: 1px;
      height: 1px;
      overflow: hidden;
    }

    .skip-link:focus {
      left: var(--space-3);
      top: var(--space-3);
      width: auto;
      height: auto;
      overflow: visible;
    }

    @media (min-width: 48rem) {
      .site-header,
      .site-main,
      .site-footer {
        padding: var(--space-4);
      }
    }
  ── Read core/tests/test_views.py
  ── Thought for 2m 7s
    I'm designing TASK-002 and weighing how to represent the role field on User. The open question is whether it should be required, since superusers don't fit neatly into the student-or-staff split, so I'm considering a blank default.

    I'm checking whether a superuser with no role can still satisfy the constraints. Plain `role` with no default would store an empty string for createsuperuser, so the database check has to allow an empty role only for superusers. I'm also thinking about tying `is_staff` to `is_superuser` so students and staff can't get it, and I'm leaning toward forbidding a role on superusers entirely to keep the split clean.

    I'm settling on the role-and-superuser constraints: a superuser gets no role and must have is_staff set, while students and staff must not be superusers. Using a DB check on role rather than groups keeps the exactly-one rule enforceable and cheap to filter, since groups are many-to-many and can't guarantee that.

    I'm working out where the staff student views should live, and I'm leaning toward keeping them in `accounts` under `/staff/students/` since the profiles already sit there. I'm also weighing whether to use the primary key or the student record number in the detail URL.

    I'm sketching the university models now, starting with Faculty, and I'm thinking about giving it a unique code so seed data can be matched on something stable.

    I'm defining the Faculty and Program models now, with unique codes so seed data can be matched reliably. For Program, the code is unique only within its faculty, since national program codes can repeat across faculties. StudyGroup gets a course number limited to 1 through 6 by both a validator and a check constraint.

    I'm settling the User model's fields and constraints, and I'm deciding how to handle the full name. Superuser access is already covered by the role constraints, so the remaining question is whether the name lives on AbstractUser's first_name and last_name or on the profiles.

    I'm settling StudentProfile: it links one-to-one to the user, holds the last, first and middle names, a unique record number, and a PROTECT foreign key to StudyGroup. Since a database constraint can't check the user's role across tables, I'll enforce that a profile's user must have the student role in clean().

    I'm settling the StudentProfile and StaffProfile details, including their name fields, position, and faculty links. Then I'm weighing whether a student with no profile should be handled as a special case or just denied. I'm leaning toward denying access by default: the role mixins will require both the right role and an existing profile, returning 403 otherwise, and the profile page will show a "profile not filled in" message when none exists.

    I'm laying out the access helpers next: functions that return a user's student or staff profile, and a base mixin that checks the required role and that the profile exists, raising a 403 otherwise. Superusers have no role, so they're denied on staff pages by design, and the student and staff mixins will just set the role they need.

    I'm deciding how the access helpers should scope visibility: staff see only students whose group's program falls under their faculty, students see only their own profile, and everyone else sees nothing. I'm also settling on a single role check that both the mixins and a decorator can call, so the logic lives in one place.

    I'm checking that staff detail views only resolve students in their faculty, so anything outside it returns a 404. I'm also planning tests that confirm no staff URL leaks another staff member's name, since there's no staff profile page beyond their own /profile/.

    I'm checking how the login-required middleware treats the public views: the health check gets the no-login decorator, but the home page needs a login. That means the existing home tests have to log a user in now, since anonymous requests will be redirected.

    I'm checking whether the login-required middleware skips the database when a view is marked as public, since the health check must stay at zero queries. The view flag is read before the user is loaded, so it should return early. I'm now working out the decorator order, because the no-login marker has to survive the caching wrapper.

    I'm setting the login and logout redirects to the accounts URLs and mapping the routes for login, logout, profile, and the staff student list and detail pages. I'm also deciding that the login view will use a dedicated accounts template so the disclaimer appears there.

    I'm checking how the login and logout views behave: login stays public with a disclaimer, and logout only accepts POST, so the nav needs a small form for it. Next I'm working out how the base template shows the nav based on the user's role, and whether an anonymous user needs a guard so the role checks don't break.

    I'm settling the admin side: only superusers get in, since the constraint already restricts is_staff to them, so I'll register the models with a UserAdmin that exposes the role field in both the edit and add forms.

    I'm checking how Django's admin form for the custom user works: the stock creation form points at the built-in User model, so I'll need a subclass that adds the role field.

    I'm working out how Django's admin forms relate to the custom user: the stock creation and change forms point at the built-in User model, so I'll need subclasses in accounts/admin.py that include the role field. I also want the User model's clean() to check the same role rules, so an operator setting is_staff on a student gets a validation error in the admin instead of an IntegrityError.

    I'm noting that Django's full_clean already runs model constraints, so a violation shows up as a form error in the admin without a custom clean(). I'll set violation_error_message on each constraint so the text is readable. For the profiles, limit_choices_to on the one-to-one field to role "student" should cover both the admin dropdown and model validation, so I don't need a separate clean() there.

    I'm moving on to the seed command: it will live in the accounts app, since it needs both the university and accounts models. The demo data will sit in a module-level constant, and every record will be matched by its natural key so that running the command repeatedly creates no duplicates. I'm also planning to reset the demo password on each run from the DEMO_PASSWORD setting, and to validate that value.

    I'm setting up the seed command to read DEMO_PASSWORD from the environment, validate it with Django's password validators, and wrap the writes in a transaction so a failure leaves nothing half-created.

    I'm sketching the demo seed data now: a fictional faculty pair for digital diplomacy and applied economics, each with a program and a study group, and a first student record to anchor the list.

    I'm settling on the demo roster now: two fictional faculties, each with one program and one study group, plus three students and two staff members, with the usernames kept in plain ASCII.

    I'm making the seed command read the demo password from the environment and fail with a clear error if it's missing, and I'm planning a test that confirms no users get created in that case.

    I'm settling the admin tests and the profile page: a student sees their faculty, program, course, group and record number, while staff see their position and faculty, and anyone without a profile just sees their username with a note that the profile isn't filled in. I'm also planning a student list for each faculty that shows name, group and course.

    I'm laying out the home page, the student list and detail pages as plain lists rather than tables so they fit on a narrow screen, and deciding to keep HomeView as a login-required greeting. I'm also planning the test helpers for creating a university, students and staff, and starting the model tests.

    I'm writing the access tests next: checking that every page outside the public set redirects anonymous visitors to login, including the logout endpoint, and I'm still working out how the admin's own login interacts with the middleware.

    I'm writing the access tests to check that a default-deny walk over every URL pattern requires login unless the view is explicitly public, which covers the login page and the health check. I'm also planning a student-isolation check, and a separate test where a logged-in student hitting the admin index gets redirected to the admin login rather than a 200.

    I'm checking the staff-side tests next: a staff member's list should hold only students from their own faculty, a faculty-Y student's detail page should 404 for them, and their profile should show only their own details. I'm also making sure no URL takes a staff id directly.

    I'm wrapping up the settings changes: registering the accounts and university apps, pointing AUTH_USER_MODEL at the custom user, adding LoginRequiredMiddleware right after authentication, and setting up the login URL.

    I'm finishing the settings changes: adding a couple of tests to confirm the login-required middleware and custom user model are wired up, then listing the accounts and university apps in the known-first-party config. I'm also deleting the old SQLite database and generating the migrations with makemigrations rather than writing them by hand, and I'm noting the Ruff DJ rule against null=True on character fields.

    I'm running through lint rules: every model needs a `__str__`, and the inner classes should follow the DJ012 ordering. Test-only hardcoded passwords are fine under S106, and the seed command won't hardcode one. Next I'm sketching the templates, with a shared student-fields include so the profile and detail pages reuse the same markup, and I'm working out the Russian labels on the login page.

    I'm wrapping up the presentation details now: the login form's non-field errors, minimal CSS for the nav, form fields and profile definition list, and showing the role label through the display helper. I also want the student list to pull related faculty, group and user data in one query, and the student detail page to look records up by the profile's own primary key.

    I'm making the User model's role-checking properties: `is_student` and `is_deanery_staff`, each comparing the role against its enum value. I'm also sketching a `get_profile_for_role` helper to pick the right profile for a given role.

    Now I'm writing the role-check helper: it rejects anonymous users and anyone whose role doesn't match, then picks the student or staff profile off the user and raises PermissionDenied if that profile doesn't exist. Next I'm sketching a mixin that holds the required role and the resolved profile.

    I'm wiring up the role checks as a mixin and a decorator, and the staff-only pages will return 403 for students and 404 for staff looking at another faculty's records. I also want the staff navigation link to appear only when the user is deanery staff, and I'm checking the existing home template next.

    I'm leaving the home template as it is and only adding the login requirement, since the nav already gives the links. In the home tests I'll create and log in a plain student user, and add a check that the home page redirects anonymous visitors. I also need to confirm the external-resources test still passes once the nav is in place. Last, I'm noting that the nav and any role checks have to handle an anonymous user safely, which means guarding the role properties in the templates.

    I'm setting up the admin: a custom user admin that adds the role field to both the edit and create forms, with list filters on role and active status, and simple admin registrations for the student and staff profiles and the university models.

    I'm settling on the User model's constraints and how it's declared: a Q constraint that references the superuser flag, which is fine since createsuperuser with an empty role and is_superuser set will pass. I need the test helpers to always pass a role, because create_user without one would hit the IntegrityError. For the Meta class, I'm leaning toward a plain `class Meta:` rather than subclassing AbstractUser.Meta, since the custom-user docs don't subclass it.

    I'm settling the seed command's password handling: it will run the demo password through the validators and fail with a clear error if it's too weak, and the tests will use a strong one.

    I'm adding CI steps that migrate the database and run the seed command twice with a dummy demo password, to match the local checks. Then I'm removing the old database file, since the lead approved deleting it, before generating fresh migrations.

    I'm checking the remaining verification steps: the seed command gets the demo password from the environment on the command line, and I'll note for the lead that .env needs DEMO_PASSWORD set. For the anonymous-redirect test I'm covering the public-facing pages like the home, profile, and staff student list, and I'm planning a resolver walk to catch any other URLs.

    I'm checking how the view-level login exemption is marked: Django's LoginView applies a login_not_required decorator through its dispatch method, and as_view copies those attributes onto the callable, so the callback should report login_required as False. That means a test can walk the URL resolver and assert that only the login and health endpoints are public.

    I'm settling the remaining details for the spec: `/health/` gets `login_not_required` above its existing decorators, the staff student list shows "Студентов нет." when empty, and the student detail page title includes the student's name. I'm also noting that the university app has no views, and that future schedule, grade, and request data will hang off StudyGroup and the profiles.

    I'm settling the file layout for the accounts app: models, admin, the role-access and selector helpers, views, URLs, demo data, and the seed command, plus the four templates for login, profile, and the staff student pages.

    I'm listing the file layout for the accounts app's test modules, plus the university app's files, and noting that the config URL include goes before core. I'm also planning to use a plain dict for the seed data.

    I'm defining the seed data as frozen dataclasses for faculties, programs, groups, students, and staff, then sketching how the seed command will run: it reads DEMO_PASSWORD from the environment and raises a clear error if it's missing.

    I'm writing the seed command's per-user loop: it looks up or creates each demo user, refuses to touch any existing user whose role differs or who is a superuser, validates the demo password against each user before setting it, and then updates the matching profile.

    I'm writing the seed logic into `accounts/demo.py`, with the data constants and a `seed_demo_data` function that takes the password, so the management command stays thin and the logic can be tested directly. I'm also thinking about how to check the password hash in the tests, expecting it to be a PBKDF2 hash rather than the raw password.

    Writing the password-hash test now, checking that the stored value is a PBKDF2 hash rather than the raw password. Test speed is a concern since PBKDF2 is slow, so I'll use force_login and unusable passwords where possible, and keep the default hasher for the seed tests.

── Assistant ───────────────────────────────────────────────
Изучил код после TASK-001. Пишу спецификацию TASK-002: модель данных, роли, проверки доступа и демо-данные.

── Created 1 file ──────────────────────────────────────────
  ── Created docs/tasks/TASK-002.md +635
    --- /dev/null
    +++ b~/hackatonproject/docs/tasks/TASK-002.md
    +# TASK-002: Users, roles, profiles, login and data isolation
    +
    +Author: Planner. Status: ready for implementation.
    +Base commit: `04b7f0c`. Product context: `plan.md`. Previous spec: `docs/tasks/TASK-001.md`.
    +
    +---
    +
    +## 1. Goal
    +
    +Create the user foundation for every later feature: a custom user model with exactly one role (student or dean's-office staff), university reference data, student and staff profiles, login/logout, own-profile page, a staff-only student directory, and default-deny access control with reusable role checks and queryset scoping.
    +
    +## 2. Acceptance criteria
    +
    +1. `AUTH_USER_MODEL = "accounts.User"`; migrations exist for `university` and `accounts`; `makemigrations --check --dry-run` is clean.
    +2. Every URL requires login except `accounts:login` and `core:health` (proved by a test that walks the URL resolver).
    +3. Students see only their own data; every staff URL returns 403 for a student.
    +4. Staff see only their own profile and students of their own faculty; a student of another faculty returns 404; no URL shows another staff member's profile.
    +5. Logout works only via POST (GET → 405).
    +6. Students and staff can never have `is_staff=True` (DB constraint); only superusers reach Django admin.
    +7. `seed_demo` creates the demo data, is idempotent, never prints the password, and fails with a clear `CommandError` when `DEMO_PASSWORD` is missing.
    +8. Pages work at 360 px width, Russian UI text, no new visual theme.
    +9. All TASK-001 verification commands still pass; `python manage.py seed_demo` runs twice without errors.
    +10. TASK-001 review notes fixed (section 5.12).
    +
    +## 3. Out of scope
    +
    +Schedule, grades, requests, notifications, chat, map. Registration, password reset/change, email, login rate limiting, 2FA. Visual theme. Editing profiles from the site (data is edited only in Django admin by the superuser). Pagination of the student list.
    +
    +---
    +
    +## 4. Design decisions
    +
    +### 4.1 Role representation: a `role` field on `User`, not Django groups
    +- "Exactly one role" is enforced by the database with a `CheckConstraint`. Groups are many-to-many and cannot enforce "exactly one".
    +- Role checks and queryset filters are a simple column comparison; no extra joins.
    +- We do not use Django's model permissions for business access. Access is decided by role + data ownership (queryset scoping). Groups would add nothing.
    +- The superuser (system operator) is not a domain user: `role=""` is allowed **only** for superusers, and a superuser cannot have a role.
    +
    +**Naming warning**: Django's `User.is_staff` means "may log in to Django admin". It has nothing to do with the dean's-office role. Never use `is_staff` for role checks. Use `user.role` / `user.is_deanery_staff`.
    +
    +### 4.2 Apps and dependency direction
    +```
    +university  (Faculty, Program, StudyGroup)  — depends on nothing in the project
    +accounts    (User, StudentProfile, StaffProfile, access, selectors, views, seed)  — depends on university
    +core        (home, health, base template)  — depends on nothing; templates use `user`
    +```
    +`university` must never import from `accounts`.
    +
    +### 4.3 How later tasks will use this model (do not implement now)
    +- Schedule → `StudyGroup`. Grades/attendance → `StudentProfile`. Requests → `StudentProfile`, handled by `StaffProfile` of the same faculty. Notifications → `Faculty`/`StudyGroup`/`StudentProfile`. Chat → `StudentProfile` ↔ staff of the student's faculty.
    +- All of them reuse `accounts.access` (role checks) and the `accounts.selectors` pattern (scope by current user, then look up the object).
    +
    +### 4.4 Names live in profiles
    +`StudentProfile`/`StaffProfile` hold `last_name`, `first_name`, `middle_name`. `User.first_name`/`User.last_name` (inherited from `AbstractUser`) stay empty and are not used anywhere.
    +
    +---
    +
    +## 5. Architecture
    +
    +### 5.1 Files
    +
    +Create:
    +```
    +university/__init__.py
    +university/apps.py
    +university/models.py
    +university/admin.py
    +university/migrations/__init__.py
    +university/migrations/0001_initial.py        (generated by makemigrations)
    +university/tests/__init__.py
    +university/tests/test_models.py
    +
    +accounts/__init__.py
    +accounts/apps.py
    +accounts/models.py
    +accounts/admin.py
    +accounts/access.py
    +accounts/selectors.py
    +accounts/views.py
    +accounts/urls.py
    +accounts/demo.py
    +accounts/management/__init__.py
    +accounts/management/commands/__init__.py
    +accounts/management/commands/seed_demo.py
    +accounts/migrations/__init__.py
    +accounts/migrations/0001_initial.py          (generated by makemigrations)
    +accounts/templates/accounts/login.html
    +accounts/templates/accounts/profile.html
    +accounts/templates/accounts/student_list.html
    +accounts/templates/accounts/student_detail.html
    +accounts/templates/accounts/includes/student_fields.html
    +accounts/templates/accounts/includes/staff_fields.html
    +accounts/tests/__init__.py
    +accounts/tests/helpers.py
    +accounts/tests/test_models.py
    +accounts/tests/test_access.py
    +accounts/tests/test_views.py
    +accounts/tests/test_seed_demo.py
    +accounts/tests/test_admin.py
    +```
    +
    +Change:
    +```
    +config/settings.py, config/urls.py, core/views.py, templates/base.html, static/css/base.css,
    +core/tests/test_views.py, core/tests/test_settings.py, core/tests/test_env_utils.py,
    +README.md, .env.example, pyproject.toml, .github/workflows/ci.yml
    +```
    +Do not change any other file. Do not edit `core/templates/core/home.html`.
    +
    +### 5.2 Database reset (approved by the Team lead)
    +`rm -f db.sqlite3` once, before the first `migrate` after adding `AUTH_USER_MODEL`. This is the only destructive command allowed in this task.
    +
    +### 5.3 `university/models.py`
    +
    +App config `UniversityConfig`: `name = "university"`, `verbose_name = "Университет"`, `default_auto_field = "django.db.models.BigAutoField"`.
    +
    +All models: define `__str__`; ruff DJ012 order (fields → `Meta` → `__str__` → properties/methods). Russian `verbose_name` on models and fields.
    +
    +**`Faculty`**
    +| Field | Definition |
    +|---|---|
    +| `code` | `CharField(max_length=20, unique=True)` — short code, e.g. `"FDD"` |
    +| `name` | `CharField(max_length=200, unique=True)` |
    +- `Meta`: `ordering = ["name"]`, `verbose_name = "факультет"`, `verbose_name_plural = "факультеты"`.
    +- `__str__` → `self.name`.
    +
    +**`Program`** (field of study)
    +| Field | Definition |
    +|---|---|
    +| `faculty` | `ForeignKey(Faculty, on_delete=models.PROTECT, related_name="programs")` |
    +| `code` | `CharField(max_length=20)` — e.g. `"41.03.05"` |
    +| `name` | `CharField(max_length=200)` |
    +- `Meta`: `ordering = ["faculty__name", "name"]`; `constraints = [UniqueConstraint(fields=["faculty", "code"], name="university_program_unique_faculty_code")]`; verbose names `"направление подготовки"` / `"направления подготовки"`.
    +- `__str__` → `f"{self.code} {self.name}"`.
    +
    +**`StudyGroup`**
    +| Field | Definition |
    +|---|---|
    +| `program` | `ForeignKey(Program, on_delete=models.PROTECT, related_name="groups")` |
    +| `name` | `CharField(max_length=20, unique=True)` — e.g. `"ЦД-101"` |
    +| `course` | `PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)])` |
    +- `Meta`: `ordering = ["name"]`; `constraints = [CheckConstraint(condition=Q(course__gte=1) & Q(course__lte=6), name="university_studygroup_course_1_6")]` (Django 5.2: use `condition=`, not `check=`); verbose names `"учебная группа"` / `"учебные группы"`.
    +- `__str__` → `self.name`.
    +- `@property faculty -> Faculty`: `return self.program.faculty`.
    +
    +`university/admin.py`: register all three with `list_display` (`Faculty`: code, name; `Program`: code, name, faculty; `StudyGroup`: name, program, course), `list_filter` (`Program`: faculty; `StudyGroup`: course, program__faculty), `search_fields` (`name`, plus `code` where present).
    +
    +### 5.4 `accounts/models.py`
    +
    +App config `AccountsConfig`: `name = "accounts"`, `verbose_name = "Пользователи"`, `default_auto_field = "django.db.models.BigAutoField"`.
    +
    +**`User(AbstractUser)`**
    +```python
    +class Role(models.TextChoices):
    +    STUDENT = "student", "Студент"
    +    STAFF = "staff", "Сотрудник деканата"
    +```
    +Define `Role` as a nested class `User.Role`.
    +
    +| Field | Definition |
    +|---|---|
    +| `role` | `CharField("роль", max_length=16, choices=Role.choices, blank=True, default="")` |
    +
    +`Meta` (`verbose_name = "пользователь"`, `verbose_name_plural = "пользователи"`), constraints:
    +```python
    +models.CheckConstraint(
    +    condition=(Q(is_superuser=False) & Q(role__in=["student", "staff"]))
    +    | (Q(is_superuser=True) & Q(role="")),
    +    name="accounts_user_role_matches_superuser",
    +    violation_error_message="Обычный пользователь должен иметь роль; у суперпользователя роли нет.",
    +),
    +models.CheckConstraint(
    +    condition=Q(is_staff=False) | Q(is_superuser=True),
    +    name="accounts_user_admin_access_superuser_only",
    +    violation_error_message="Доступ к админке есть только у суперпользователя.",
    +),
    +```
    +Consequences (intended): `create_user(...)` without `role` fails with `IntegrityError`; `createsuperuser` works (role `""`, `is_staff=True`, `is_superuser=True`). Admin forms show the messages above because `full_clean()` validates constraints.
    +
    +Properties:
    +- `is_student -> bool`: `return self.role == self.Role.STUDENT`
    +- `is_deanery_staff -> bool`: `return self.role == self.Role.STAFF`
    +
    +`__str__` → `self.username`. Do not override the manager.
    +
    +**`StudentProfile`**
    +| Field | Definition |
    +|---|---|
    +| `user` | `OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile", limit_choices_to={"role": "student"})` |
    +| `last_name` | `CharField("фамилия", max_length=100)` |
    +| `first_name` | `CharField("имя", max_length=100)` |
    +| `middle_name` | `CharField("отчество", max_length=100, blank=True, default="")` |
    +| `group` | `ForeignKey("university.StudyGroup", on_delete=models.PROTECT, related_name="students")` |
    +| `record_number` | `CharField("номер зачётной книжки", max_length=20, unique=True)` |
    +- `Meta`: `ordering = ["last_name", "first_name"]`, verbose names `"профиль студента"` / `"профили студентов"`.
    +- `__str__` → `self.full_name`.
    +- Properties: `full_name -> str` = `" ".join(part for part in (last_name, first_name, middle_name) if part)`; `program` → `self.group.program`; `faculty` → `self.group.program.faculty`; `course -> int` → `self.group.course`. No duplicated faculty/program/course fields.
    +
    +**`StaffProfile`**
    +| Field | Definition |
    +|---|---|
    +| `user` | `OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile", limit_choices_to={"role": "staff"})` |
    +| `last_name`, `first_name`, `middle_name` | same as `StudentProfile` |
    +| `position` | `CharField("должность", max_length=150)` |
    +| `faculty` | `ForeignKey("university.Faculty", on_delete=models.PROTECT, related_name="staff_members")` |
    +- `Meta`: `ordering = ["last_name", "first_name"]`, verbose names `"профиль сотрудника"` / `"профили сотрудников"`.
    +- `__str__` → `self.full_name`; property `full_name` as above.
    +
    +`limit_choices_to` is enforced by `full_clean()` (admin); code that creates profiles (only `accounts/demo.py`) must set the correct role itself.
    +
    +### 5.5 `accounts/admin.py`
    +
    +- `UserCreationAdminForm(AdminUserCreationForm)` with `class Meta(AdminUserCreationForm.Meta): model = User; fields = ("username", "role")`.
    +- `UserChangeAdminForm(UserChangeForm)` with `class Meta(UserChangeForm.Meta): model = User`.
    +- `@admin.register(User) class UserAdmin(django.contrib.auth.admin.UserAdmin)`:
    +  - `form = UserChangeAdminForm`, `add_form = UserCreationAdminForm`
    +  - `list_display = ("username", "role", "is_active", "is_superuser", "last_login")`
    +  - `list_filter = ("role", "is_active", "is_superuser")`
    +  - `fieldsets = BaseUserAdmin.fieldsets + (("Роль", {"fields": ("role",)}),)`
    +  - `add_fieldsets = BaseUserAdmin.add_fieldsets + (("Роль", {"fields": ("role",)}),)`
    +- `StudentProfileAdmin`: `list_display = ("full_name", "group", "record_number", "user")`, `list_filter = ("group__program__faculty", "group")`, `search_fields = ("last_name", "first_name", "record_number", "user__username")`, `list_select_related = ("group", "user")`.
    +- `StaffProfileAdmin`: `list_display = ("full_name", "position", "faculty", "user")`, `list_filter = ("faculty",)`, `search_fields = ("last_name", "first_name", "user__username")`.
    +
    +### 5.6 `config/settings.py` changes
    +
    +1. `INSTALLED_APPS`: insert `"university"` and `"accounts"` before `"core"` (order: `..., "django.contrib.staticfiles", "university", "accounts", "core"`).
    +2. After `INSTALLED_APPS`: `AUTH_USER_MODEL = "accounts.User"`.
    +3. `MIDDLEWARE`: insert `"django.contrib.auth.middleware.LoginRequiredMiddleware"` directly after `AuthenticationMiddleware`.
    +4. Add:
    +   ```python
    +   LOGIN_URL = "accounts:login"
    +   LOGIN_REDIRECT_URL = "accounts:profile"
    +   LOGOUT_REDIRECT_URL = "accounts:login"
    +   ```
    +Nothing else changes in settings.
    +
    +### 5.7 URLs
    +
    +`config/urls.py`:
    +```python
    +urlpatterns = [
    +    path(settings.ADMIN_URL, admin.site.urls),
    +    path("", include("accounts.urls")),
    +    path("", include("core.urls")),
    +]
    +```
    +
    +`accounts/urls.py` (`app_name = "accounts"`):
    +| Path | View | Name |
    +|---|---|---|
    +| `login/` | `views.DeaneryLoginView.as_view()` | `login` |
    +| `logout/` | `django.contrib.auth.views.LogoutView.as_view()` | `logout` |
    +| `profile/` | `views.ProfileView.as_view()` | `profile` |
    +| `staff/students/` | `views.StaffStudentListView.as_view()` | `staff_student_list` |
    +| `staff/students/<int:pk>/` | `views.StaffStudentDetailView.as_view()` | `staff_student_detail` |
    +
    +`pk` is `StudentProfile.pk`. There is no URL with a user ID or a staff profile ID.
    +
    +### 5.8 Templates and navigation
    +
    +All templates extend `base.html`, Russian text, no inline styles, no external URLs.
    +
    +`templates/base.html` — replace only the line `<nav ...>{% block nav %}{% endblock %}</nav>` with:
    +```html
    +<nav class="site-nav" aria-label="Основная навигация">
    +  {% block nav %}
    +  {% if user.is_authenticated %}
    +  <ul class="site-nav-list">
    +    <li><a href="{% url 'accounts:profile' %}">Профиль</a></li>
    +    {% if user.is_deanery_staff %}
    +    <li><a href="{% url 'accounts:staff_student_list' %}">Студенты</a></li>
    +    {% endif %}
    +    <li>
    +      <form class="site-nav-logout" method="post" action="{% url 'accounts:logout' %}">
    +        {% csrf_token %}
    +        <button type="submit">Выйти</button>
    +      </form>
    +    </li>
    +  </ul>
    +  {% endif %}
    +  {% endblock %}
    +</nav>
    +```
    +
    +`accounts/login.html`: `{% block title %}Вход — Цифровой деканат будущего{% endblock %}`; `<h1>Вход</h1>`; `<form method="post" class="form">` with `{% csrf_token %}`, `{{ form }}`, hidden `next` input (`<input type="hidden" name="next" value="{{ next }}">`), `<button type="submit">Войти</button>`. Show non-field errors via `{{ form }}` (Django default rendering).
    +
    +`accounts/includes/student_fields.html` (expects `profile`): a `<dl class="fields">` with: ФИО (`profile.full_name`), Факультет (`profile.faculty.name`), Направление (`profile.program`), Курс (`profile.course`), Группа (`profile.group.name`), Номер зачётной книжки (`profile.record_number`).
    +
    +`accounts/includes/staff_fields.html` (expects `profile`): `<dl class="fields">` with ФИО, Должность, Факультет.
    +
    +`accounts/profile.html`: `<h1>Мой профиль</h1>`; `<p>Роль: {{ user.get_role_display|default:"Администратор системы" }}</p>`; then:
    +- if `student_profile` → include `student_fields.html` with `profile=student_profile`;
    +- elif `staff_profile` → include `staff_fields.html` with `profile=staff_profile`;
    +- else `<p>Профиль не заполнен.</p>`.
    +
    +`accounts/student_list.html`: `<h1>Студенты факультета</h1>`, `<p>{{ faculty.name }}</p>`; `<ul class="student-list">` with one `<li>` per student: link to detail (`full_name`), then `· {{ group.name }}, {{ course }} курс`. Empty state: `<p>Студентов нет.</p>` (`{% empty %}`).
    +
    +`accounts/student_detail.html`: `<h1>{{ student.full_name }}</h1>`, include `student_fields.html` with `profile=student`, link back «← К списку студентов».
    +
    +`static/css/base.css` — append (tokens only, no literal colors):
    +```css
    +.site-nav-list { display: flex; flex-wrap: wrap; gap: var(--space-3); list-style: none; margin: var(--space-2) 0 0; padding: 0; }
    +.site-nav-logout { margin: 0; }
    +.form input { display: block; width: 100%; max-width: 100%; }
    +.form button { margin-top: var(--space-3); }
    +.fields dt { font-weight: bold; margin-top: var(--space-2); }
    +.fields dd { margin: 0; }
    +.student-list { padding-left: var(--space-4); }
    +```
    +(Format with one declaration per line, like the existing file.)
    +
    +### 5.9 `core/views.py` change
    +Add `from django.contrib.auth.decorators import login_not_required` and make it the **outermost** decorator of `health`:
    +```python
    +@login_not_required
    +@never_cache
    +@require_GET
    +def health(request: HttpRequest) -> JsonResponse:
    +```
    +`HomeView` is unchanged and now requires login (default deny).
    +
    +### 5.10 `.env.example`
    +Append:
    +```
    +# Password for all demo accounts created by `python manage.py seed_demo`.
    +# Must pass Django password validators.
    +DEMO_PASSWORD=change-me-demo-password-2026
    +```
    +
    +### 5.11 CI (`.github/workflows/ci.yml`)
    +After the `Tests` step and before the deploy check, add:
    +```yaml
    +      - name: Migrate and seed demo data twice
    +        env:
    +          DEMO_PASSWORD: "ci-dummy-demo-password-2026"
    +        run: |
    +          python manage.py migrate --noinput
    +          python manage.py seed_demo
    +          python manage.py seed_demo
    +```
    +
    +### 5.12 TASK-001 review notes
    +- `core/tests/test_env_utils.py`: replace both `assertRaisesMessage(Exception, ...)` with `assertRaisesMessage(ImproperlyConfigured, ...)`.
    +- `README.md`, section "Test & lint": append the deploy check and YAML commands exactly as in TASK-001 section 8 (commands 4 and 7).
    +- `README.md`: add section "Demo data" (see 6.6) and the row `DEMO_PASSWORD | (none) | Password for demo accounts; required by seed_demo.` to the env table.
    +- `pyproject.toml`: `known-first-party = ["config", "core", "accounts", "university"]`.
    +
    +---
    +
    +## 6. Functions
    +
    +### 6.1 `accounts/access.py` — role checks
    +
    +```python
    +def get_profile_for_role(user: AbstractBaseUser | AnonymousUser, role: str) -> StudentProfile | StaffProfile
    +```
    +- Purpose: the single place that decides whether `user` acts in `role`; returns the role's profile.
    +- Inputs: `user` (from `request.user`); `role` — `User.Role.STUDENT` or `User.Role.STAFF`.
    +- Output: `user.student_profile` for STUDENT, `user.staff_profile` for STAFF.
    +- Raises: `PermissionDenied` (→ 403) in every failure case. `ValueError` if `role` is not one of the two values (programming error).
    +- Algorithm:
    +  1. If `role` not in `(User.Role.STUDENT, User.Role.STAFF)` → `raise ValueError`.
    +  2. If not `user.is_authenticated` or not `user.is_active` → `raise PermissionDenied`.
    +  3. If `user.role != role` → `raise PermissionDenied` (covers superusers: role `""`).
    +  4. `attr = "student_profile" if role == User.Role.STUDENT else "staff_profile"`.
    +  5. `try: return getattr(user, attr)` / `except ObjectDoesNotExist: raise PermissionDenied`.
    +- Edge cases: role matches but no profile → 403. Anonymous → 403 (normally the middleware redirects first).
    +- Tests (`accounts/tests/test_access.py`, `TestCase`): returns own student profile; returns own staff profile; student asking STAFF → `PermissionDenied`; staff asking STUDENT → `PermissionDenied`; superuser → `PermissionDenied` for both; role student without profile → `PermissionDenied`; `AnonymousUser()` → `PermissionDenied`; inactive user → `PermissionDenied`; bad role `"admin"` → `ValueError`.
    +
    +```python
    +class RoleRequiredMixin:
    +    required_role: ClassVar[str]
    +    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse
    +```
    +- Purpose: CBV guard. Algorithm: `self.profile = get_profile_for_role(request.user, self.required_role)`; then `return super().dispatch(request, *args, **kwargs)`.
    +- Must be listed **first** in the view's bases.
    +
    +```python
    +class StudentRequiredMixin(RoleRequiredMixin): required_role = User.Role.STUDENT
    +class StaffRequiredMixin(RoleRequiredMixin):   required_role = User.Role.STAFF
    +```
    +
    +```python
    +def role_required(role: str) -> Callable[[ViewFunc], ViewFunc]
    +```
    +- Purpose: same guard for function views (used by later tasks).
    +- Algorithm: returns a decorator; the wrapper (with `functools.wraps`) calls `request.profile = get_profile_for_role(request.user, role)` and then the view.
    +- Tests: with `RequestFactory`, a dummy view decorated with `role_required(User.Role.STAFF)`: staff → 200 and `request.profile` is the staff profile; student → `PermissionDenied`.
    +
    +### 6.2 `accounts/selectors.py` — queryset scoping
    +
    +```python
    +def students_visible_to(user: AbstractBaseUser | AnonymousUser) -> QuerySet[StudentProfile]
    +```
    +- Purpose: every student-data lookup starts from this queryset. Never look up `StudentProfile` by a raw ID without it.
    +- Algorithm:
    +  1. `qs = StudentProfile.objects.select_related("user", "group__program__faculty")`.
    +  2. If not authenticated or not active → `return qs.none()`.
    +  3. If `user.role == STAFF`: `profile = getattr(user, "staff_profile", None)` (catch `ObjectDoesNotExist` → `qs.none()`); `return qs.filter(group__program__faculty=profile.faculty, user__is_active=True)`.
    +  4. If `user.role == STUDENT`: `return qs.filter(user=user)`.
    +  5. Else (superuser / no role) → `return qs.none()`.
    +- Tests (`accounts/tests/test_access.py`): staff of faculty X sees exactly X students; staff without profile → empty; student sees only self; superuser → empty; anonymous → empty; inactive student is hidden from staff.
    +
    +### 6.3 `accounts/views.py`
    +
    +```python
    +class DeaneryLoginView(LoginView):
    +    template_name = "accounts/login.html"
    +    redirect_authenticated_user = True
    +```
    +(`LoginView` is already `login_not_required` in Django 5.1+; do not add anything else.)
    +
    +```python
    +class ProfileView(TemplateView):
    +    template_name = "accounts/profile.html"
    +    def get_context_data(self, **kwargs: Any) -> dict[str, Any]
    +```
    +- Access: any logged-in user (middleware). Shows **only** `request.user`'s data; takes no URL parameters.
    +- Algorithm: `context = super().get_context_data(**kwargs)`; `user = self.request.user`; `context["student_profile"] = StudentProfile.objects.select_related("group__program__faculty").filter(user=user).first()` if `user.is_student` else `None`; `context["staff_profile"] = StaffProfile.objects.select_related("faculty").filter(user=user).first()` if `user.is_deanery_staff` else `None`; return.
    +
    +```python
    +class StaffStudentListView(StaffRequiredMixin, ListView):
    +    template_name = "accounts/student_list.html"
    +    context_object_name = "students"
    +    def get_queryset(self) -> QuerySet[StudentProfile]
    +    def get_context_data(self, **kwargs: Any) -> dict[str, Any]
    +```
    +- `get_queryset`: `return students_visible_to(self.request.user)` (ordering from `Meta`).
    +- `get_context_data`: add `context["faculty"] = self.profile.faculty`.
    +
    +```python
    +class StaffStudentDetailView(StaffRequiredMixin, DetailView):
    +    template_name = "accounts/student_detail.html"
    +    context_object_name = "student"
    +    def get_queryset(self) -> QuerySet[StudentProfile]
    +```
    +- `get_queryset`: `return students_visible_to(self.request.user)` → `DetailView` returns 404 for a pk outside the staff member's faculty.
    +
    +Logout: Django's `LogoutView` (POST only in Django 5; GET → 405). `LOGOUT_REDIRECT_URL` sends to login.
    +
    +### 6.4 `accounts/demo.py` — demo data
    +
    +Data constants (frozen dataclasses `FacultySeed`, `ProgramSeed`, `GroupSeed`, `StudentSeed`, `StaffSeed`). All data is fictional — use exactly these values:
    +
    +Faculties:
    +| code | name |
    +|---|---|
    +| `FDD` | Факультет цифровой дипломатии |
    +| `FAE` | Факультет прикладной экономики |
    +
    +Programs:
    +| faculty | code | name |
    +|---|---|---|
    +| `FDD` | `41.03.05` | Цифровая дипломатия |
    +| `FAE` | `38.03.01` | Экономика данных |
    +
    +Groups:
    +| name | program (faculty, code) | course |
    +|---|---|---|
    +| `ЦД-101` | (`FDD`, `41.03.05`) | 1 |
    +| `ЭД-201` | (`FAE`, `38.03.01`) | 2 |
    +
    +Students:
    +| username | last | first | middle | group | record_number |
    +|---|---|---|---|---|---|
    +| `student1` | Соколова | Анна | Петровна | `ЦД-101` | `ST-2026-0001` |
    +| `student2` | Белов | Максим | (empty) | `ЭД-201` | `ST-2025-0002` |
    +| `student3` | Ким | Дарья | Сергеевна | `ЦД-101` | `ST-2026-0003` |
    +
    +Staff:
    +| username | last | first | middle | position | faculty |
    +|---|---|---|---|---|---|
    +| `staff1` | Миронова | Елена | Викторовна | Специалист деканата | `FDD` |
    +| `staff2` | Кузнецов | Игорь | Андреевич | Заместитель декана | `FAE` |
    +
    +```python
    +@dataclass(frozen=True)
    +class SeedSummary:
    +    faculties: int
    +    programs: int
    +    groups: int
    +    students: int
    +    staff: int
    +
    +def seed_demo_data(password: str) -> SeedSummary
    +```
    +- Purpose: create or update all demo records; safe to run any number of times.
    +- Raises: `DemoSeedError(Exception)` (defined in this module) for: empty password; weak password; an existing user with the same username but another role or `is_superuser=True`.
    +- Algorithm (all inside `transaction.atomic()`):
    +  1. If `not password` → `raise DemoSeedError("DEMO_PASSWORD is empty.")`.
    +  2. Faculties: `Faculty.objects.update_or_create(code=..., defaults={"name": ...})`.
    +  3. Programs: `Program.objects.update_or_create(faculty=<faculty>, code=..., defaults={"name": ...})`.
    +  4. Groups: `StudyGroup.objects.update_or_create(name=..., defaults={"program": ..., "course": ...})`.
    +  5. For each student/staff seed call `_upsert_user(username, role, password)` (below), then `StudentProfile.objects.update_or_create(user=user, defaults={...})` / `StaffProfile.objects.update_or_create(user=user, defaults={...})`.
    +  6. Return `SeedSummary` with the number of seed records of each kind (not DB totals).
    +
    +```python
    +def _upsert_user(username: str, role: str, password: str) -> User
    +```
    +- Algorithm:
    +  1. `user = User.objects.filter(username=username).first()`.
    +  2. If `user` exists and (`user.is_superuser` or `user.role != role`) → `raise DemoSeedError(f"User '{username}' already exists with a different role.")`.
    +  3. If `user is None` → `user = User(username=username, role=role)`.
    +  4. `try: validate_password(password, user)` / `except ValidationError as exc: raise DemoSeedError("DEMO_PASSWORD is too weak: " + " ".join(exc.messages)) from None`.
    +  5. `user.set_password(password)`; `user.is_active = True`; `user.is_staff = False`; `user.is_superuser = False`; `user.save()`; return `user`.
    +- Never include the password in any message or log.
    +
    +### 6.5 `accounts/management/commands/seed_demo.py`
    +
    +```python
    +class Command(BaseCommand):
    +    help = "Create or update fictional demo data. Password comes from DEMO_PASSWORD."
    +    def handle(self, *args: Any, **options: Any) -> None
    +```
    +- Algorithm:
    +  1. `password = os.environ.get("DEMO_PASSWORD", "")` (settings already loaded `.env` into the environment).
    +  2. If not `password` → `raise CommandError("DEMO_PASSWORD environment variable is required. Set it in .env or the environment.")`.
    +  3. `try: summary = seed_demo_data(password)` / `except DemoSeedError as exc: raise CommandError(str(exc)) from None`.
    +  4. `self.stdout.write(self.style.SUCCESS(f"Demo data ready: {summary.faculties} faculties, {summary.programs} programs, {summary.groups} groups, {summary.students} students, {summary.staff} staff."))`.
    +- Tests (`accounts/tests/test_seed_demo.py`, `TestCase`; use `mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"})`):
    +  - `test_creates_expected_data`: counts — 2 faculties, 2 programs, 2 groups, 3 student profiles, 2 staff profiles; `student1` role student, `staff1` role staff; nobody has `is_staff`.
    +  - `test_idempotent`: call twice → same counts as above; `User.objects.count() == 5`; `check_password` still true.
    +  - `test_passwords_hashed`: for each seeded user `user.password != password`, `user.password.startswith("pbkdf2_sha256$")`, `user.check_password(password)`.
    +  - `test_missing_password_fails`: inside `mock.patch.dict(os.environ)`, `os.environ.pop("DEMO_PASSWORD", None)`; `call_command("seed_demo")` raises `CommandError` with message containing `"DEMO_PASSWORD"`; `User.objects.count() == 0`.
    +  - `test_weak_password_fails`: `DEMO_PASSWORD="123"` → `CommandError` containing `"too weak"`; `User.objects.count() == 0` (rolled back).
    +  - `test_conflicting_existing_user_fails`: pre-create `student1` with role staff → `CommandError`; existing user role unchanged.
    +  - `test_password_not_printed`: capture `stdout` (`call_command(..., stdout=StringIO())`); password string not in output.
    +
    +### 6.6 README "Demo data" section
    +```
    +python manage.py migrate
    +python manage.py seed_demo   # needs DEMO_PASSWORD in .env or the environment
    +```
    +Table of logins: `student1` (ФМО-подобный факультет FDD, ЦД-101), `student2` (FAE, ЭД-201), `student3` (FDD, ЦД-101), `staff1` (FDD), `staff2` (FAE). Password: the value of `DEMO_PASSWORD`. Superuser: `python manage.py createsuperuser` (admin only). State that all data is fictional.
    +
    +---
    +
    +## 7. Tests (complete list)
    +
    +Helpers in `accounts/tests/helpers.py` (plain functions, no new dependencies):
    +- `make_faculty(code: str) -> Faculty`, `make_group(faculty: Faculty, name: str, course: int = 1) -> StudyGroup` (creates a `Program` too).
    +- `make_student(username: str, group: StudyGroup, record_number: str) -> User` — `User.objects.create_user(username=username, role=User.Role.STUDENT)` (no password → unusable, fast) + `StudentProfile`.
    +- `make_staff(username: str, faculty: Faculty) -> User` — same pattern + `StaffProfile`.
    +Tests log in with `self.client.force_login(user)`.
    +
    +Shared fixture (`setUpTestData`) for view/access tests: faculties X and Y; groups GX (faculty X) and GY (faculty Y); students A (GX), B (GY), C (GX); staff SX (X) and SY (Y); each with distinctive names/record numbers.
    +
    +`accounts/tests/test_views.py`:
    +1. `test_every_non_public_url_redirects_anonymous` — for `/`, `/profile/`, `/staff/students/`, `/staff/students/<A.pk>/`: GET → 302 and `Location` starts with `"/login/?next="`.
    +2. `test_only_login_and_health_are_public` — walk `django.urls.get_resolver().url_patterns` recursively (skip `URLResolver` with `app_name == "admin"`); collect fully namespaced names of patterns whose `callback` has `login_required is False`; assert the set equals `{"accounts:login", "core:health"}`.
    +3. `test_login_page_public` — anonymous GET `/login/` → 200, contains `<form`, disclaimer text present.
    +4. `test_login_success_redirects_to_profile` — user with password set via `set_password` + save; POST credentials → 302 to `/profile/`.
    +5. `test_logout_get_not_allowed` — logged in, GET `/logout/` → 405, still logged in (`/profile/` → 200).
    +6. `test_logout_post` — POST `/logout/` → 302 to `/login/`; then `/profile/` → 302 to login.
    +7. `test_student_profile_shows_only_own_data` — A's `/profile/` contains A's record number and full name; does not contain B's or C's record numbers.
    +8. `test_student_forbidden_on_staff_pages` — A: `/staff/students/` → 403; `/staff/students/<B.pk>/` → 403; `/staff/students/<A.pk>/` → 403.
    +9. `test_staff_list_scoped_to_faculty` — SX list contains A and C names, not B.
    +10. `test_staff_detail_own_faculty` — SX `/staff/students/<A.pk>/` → 200 with A's record number.
    +11. `test_staff_detail_other_faculty_404` — SX `/staff/students/<B.pk>/` → 404.
    +12. `test_staff_detail_nonexistent_404` — SX with pk `999999` → 404.
    +13. `test_staff_never_sees_other_staff` — SX: `/profile/`, `/staff/students/`, `/staff/students/<A.pk>/` responses do not contain SY's full name.
    +14. `test_staff_profile_shows_own_data` — SX `/profile/` contains SX full name, position and faculty name.
    +15. `test_nav_depends_on_role` — A's page has no `/staff/students/` link; SX's page has it; both have the
    …[5,692 more characters truncated]
  ── Thought for 6ms
    I need to clean up a stray line of text in the README's demo section, which is the first item on my list. Then I want to check several Django facts in the venv: the login_not_required setting on LoginView in 5.2, whether AdminUserCreationForm is available from 5.1, what LogoutView returns for GET, how admin redirects behave under LoginRequiredMiddleware, and whether create_superuser accepts a role keyword.

── Assistant ───────────────────────────────────────────────
Проверю в установленном Django 5.2 несколько фактов, на которые опирается спецификация.

── Ran 1 command ───────────────────────────────────────────
  ── Ran .venv/bin/python - <<'EOF' import django; print(django.get_version()) from django.conf import settings settings.configure(INSTALLED_APPS=["django.contrib.auth","django.contrib.contenttypes","django.contrib.admin","django.contrib.sessions","django.contrib.messages"]) django.setup() from django.contrib.auth.views import LoginView, LogoutView print("LoginView login_required:", getattr(LoginView.as_view(), "login_required", True)) print("Logout methods:", LogoutView.http_method_names) from django.contrib.auth import forms print("AdminUserCreationForm:", hasattr(forms, "AdminUserCreationForm")) from django.contrib.auth.decorators import login_not_required; print("login_not_required ok") import inspect from django.contrib.admin import sites src = inspect.getsource(sites.AdminSite.get_urls) print("admin wrap login_not_required:", "login_not_required" in inspect.getsource(sites)) from django.contrib.auth.middleware import LoginRequiredMiddleware print(inspect.getsource(LoginRequiredMiddleware.process_view)[:600]) EOF (1s)
    $ .venv/bin/python - <<'EOF'
  import django; print(django.get_version())
  from django.conf import settings
  settings.configure(INSTALLED_APPS=["django.contrib.auth","django.contrib.contenttypes","django.contrib.admin","django.contrib.sessions","django.contrib.messages"])
  django.setup()
  from django.contrib.auth.views import LoginView, LogoutView
  print("LoginView login_required:", getattr(LoginView.as_view(), "login_required", True))
  print("Logout methods:", LogoutView.http_method_names)
  from django.contrib.auth import forms
  print("AdminUserCreationForm:", hasattr(forms, "AdminUserCreationForm"))
  from django.contrib.auth.decorators import login_not_required; print("login_not_required ok")
  import inspect
  from django.contrib.admin import sites
  src = inspect.getsource(sites.AdminSite.get_urls)
  print("admin wrap login_not_required:", "login_not_required" in inspect.getsource(sites))
  from django.contrib.auth.middleware import LoginRequiredMiddleware
  print(inspect.getsource(LoginRequiredMiddleware.process_view)[:600])
  EOF
    5.2.19
    LoginView login_required: False
    Logout methods: ['post', 'options']
    AdminUserCreationForm: True
    login_not_required ok
    admin wrap login_not_required: True
        def process_view(self, request, view_func, view_args, view_kwargs):
            if request.user.is_authenticated:
                return None

            if not getattr(view_func, "login_required", True):
                return None

            return self.handle_no_permission(request, view_func)
  ── Thought for 8s
    I'm checking whether `is_authenticated` triggers a database query for anonymous requests. With no session cookie, the session comes back empty without touching the database, so there are zero queries. Admin views are marked login_not_required, so the resolver walk test will need to account for that.

    Next I'm checking the admin resolver: its app_name is "admin", so the walk can skip it, and anonymous admin requests go to the admin login anyway. The logout view allows POST and OPTIONS, so a GET should return 405.

    Now I'm checking the admin add and change forms for the custom user model, since the add form's fields need to include the role. Next I'll fix the README demo text and hand it to the coder.

── Edited 1 file ───────────────────────────────────────────
  ── Edited docs/tasks/TASK-002.md +1 -1
    --- a~/hackatonproject/docs/tasks/TASK-002.md
    +++ b~/hackatonproject/docs/tasks/TASK-002.md
    -Table of logins: `student1` (ФМО-подобный факультет FDD, ЦД-101), `student2`
    +Table of logins: `student1` (FDD, ЦД-101), `student2`
  ── Edited docs/tasks/TASK-002.md +1 -1
    --- a~/hackatonproject/docs/tasks/TASK-002.md
    +++ b~/hackatonproject/docs/tasks/TASK-002.md
    -(`LoginView` is already `login_not_required` in Django 5.1+; do not add anything else.)
    +(`LoginView` is already `login_not_required` in Django 5.1+ — verified on 5.2.19; do not add anything else. Django admin views are also `login_not_required` and use their own login; that is why test 2 in section 7 skips the admin resolver.)

── Ran bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-002] Planner -> Coder: TASK Spec: docs/tasks/TASK-002.md (approved by the Team lead). Summary: - New apps `university` (Faculty, Program, StudyGroup) and `accounts` (custom User with `role` + DB constraints, StudentProfile, StaffProfile). Set AUTH_USER_MODEL; `rm -f db.sqlite3` once is approved for this task only (section 5.2). - Default deny: LoginRequiredMiddleware; only login and /health/ public. Reusable guards in `accounts/access.py`, queryset scoping in `accounts/selectors.py`; never look up a StudentProfile by raw pk without `students_visible_to()`. - Pages: login, POST-only logout, /profile/, staff student list/detail (404 for other faculty), role-based nav in base.html. - `seed_demo` command with fixed fictional data, password only from DEMO_PASSWORD, never printed. Plus TASK-001 review notes (5.12) and CI step (5.11). - Follow section 8 order and section 9 verification; full test list is in section 7. Do not use `is_staff` for role checks. Do not commit. Questions -> me. EOF (1s)
  $ bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
[TASK-002] Planner -> Coder: TASK
Spec: docs/tasks/TASK-002.md (approved by the Team lead).
Summary:
- New apps `university` (Faculty, Program, StudyGroup) and `accounts` (custom User with `role` + DB constraints, StudentProfile, StaffProfile). Set AUTH_USER_MODEL; `rm -f db.sqlite3` once is approved for this task only (section 5.2).
- Default deny: LoginRequiredMiddleware; only login and /health/ public. Reusable guards in `accounts/access.py`, queryset scoping in `accounts/selectors.py`; never look up a StudentProfile by raw pk without `students_visible_to()`.
- Pages: login, POST-only logout, /profile/, staff student list/detail (404 for other faculty), role-based nav in base.html.
- `seed_demo` command with fixed fictional data, password only from DEMO_PASSWORD, never printed. Plus TASK-001 review notes (5.12) and CI step (5.11).
- Follow section 8 order and section 9 verification; full test list is in section 7. Do not use `is_staff` for role checks. Do not commit. Questions -> me.
EOF
  Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Спецификация TASK-002 готова: [docs/tasks/TASK-002.md](docs/tasks/TASK-002.md). Я передал её кодеру. Код ещё не написан, поэтому самих проверок пока не было. Я сверил с установленным Django 5.2.19 только то, на что опирается спецификация: страница входа открыта без входа, выход из системы принимает только POST, нужные формы админки на месте.

Основные решения:
- **Роль хранится полем `role` у пользователя, а не группой Django.** База данных сама следит, чтобы у каждого пользователя была ровно одна роль. Группа так не умеет. У суперпользователя роли нет: он администратор системы. Второе ограничение в базе запрещает студентам и сотрудникам деканата входить в админку Django.
- **Две новые части проекта.** `university` хранит факультеты, направления и группы. `accounts` хранит пользователей, профили, проверки доступа и демо-данные. Факультет, направление и курс студента берутся из его группы, второй раз они не хранятся.
- **Доступ по умолчанию закрыт.** Каждая страница требует входа. Открыты только вход и `/health/`. Отдельный тест обходит все адреса сайта и падает, если открытой окажется ещё какая-то страница.
- **Ограничения по ролям.**
  - Студент на страницах сотрудника получает ошибку 403.
  - Сотрудник видит только студентов своего факультета. Для студента другого факультета он получает 404.
  - Адресов, которые показывают профиль другого сотрудника, нет.
  - Эти проверки вынесены в общие функции, их будут использовать и следующие задачи.
- **Демо-данные.** Два факультета, три студента (`student1`–`student3`) и два сотрудника (`staff1`, `staff2`), все данные вымышлены. Пароль берётся только из `DEMO_PASSWORD`. Команду `seed_demo` можно запускать повторно. Без пароля или со слабым паролем она завершается с понятной ошибкой.

Вам нужно сделать одно: добавьте строку `DEMO_PASSWORD=...` в свой `.env` вручную. Без неё команда `seed_demo` не запустится. Агентам открывать `.env` нельзя.

── User ────────────────────────────────────────────────────
DEMO_PASSWORD добавлен

── Assistant ───────────────────────────────────────────────
Понял, спасибо. Теперь `seed_demo` на вашей машине возьмёт пароль из `.env`.

Проверка в спецификации TASK-002, что команда без пароля завершается ошибкой, у вас больше не сработает. Это не помешает: кодер проверяет этот случай отдельным тестом, на него `.env` не влияет. Менять спецификацию не нужно.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-003] Team lead -> Planner: TASK
Approved by the user. Write the spec `docs/tasks/TASK-003.md` and hand it to the Coder.

## Context
TASK-001 (skeleton) and TASK-002 (users, roles, `accounts`, `university`, access helpers such as `students_visible_to`) are done. Reuse the TASK-002 access pattern (role checks + queryset scoping by the current user). Read `plan.md`, `docs/tasks/TASK-002.md` and the TASK-002 review note: do not rely on admin forms validating constraints on fields the form does not include.

Later tasks depend on this one, so design for them but do not implement them:
- Room map (sprint 3): a schedule item will link to the map and highlight its room. Rooms need a stable unique code usable as an SVG element id, plus a floor (multi-floor map is planned).
- Grades and attendance (sprint 2): will reference the discipline and, for attendance, a concrete lesson occurrence on a date.
- Notifications (sprint 2): must be able to query "schedule changes affecting group X in a date range".

## Goal
Students see their schedule for today and for a week: time, discipline, lesson type, teacher, room. Changes (cancelled, moved, room changed, teacher replaced) are clearly visible.

## Requirements
1. Data model (in `university` or a new `schedule` app - justify):
   - The fictional university has exactly ONE building (user decision, for simplicity). Do not create a Building model. Room: floor, number, unique stable `code`.
   - Teacher (fictional full name, academic title optional). Teachers do not log in.
   - Discipline (name, short name).
   - Regular timetable and dated changes. Hard constraint: the schedule must render correctly for ANY date without re-running seeds - the jury will open it on arbitrary dates until at least 2026-11-28. Recommended: a weekly template (weekday, time slot, discipline, lesson type, teacher, room, one or more study groups, active date range) plus explicit dated change records (cancel / move to another date-time / room change / teacher replacement, with a short reason). Choose and justify; a "generate dated lessons" approach is acceptable only if it meets the hard constraint.
   - Time slots (pair number -> start/end time) defined once (model or constant - justify).
   - Lectures may be shared by several groups.
   - No odd/even week alternation.
2. Pages (server-rendered, Russian UI, mobile-first, existing CSS layers, no visual theme):
   - Student: "today" view (default) and "week" view with previous/next week navigation. No group or user ID in student URLs.
   - Today view: mark the lesson in progress and the next lesson; show an empty state when there are no lessons.
   - Every lesson shows time, discipline, type, teacher, room (floor, number). Changed lessons are visually marked and show both the original and the new value (e.g. old room struck through) plus the reason.
   - Each room element carries its room code (e.g. a data attribute) so the map task can link it later. Do not render links to pages that do not exist yet.
   - Staff: read-only schedule of any study group of their own faculty (group chosen from a list). 404 for a group of another faculty.
   - Navigation: add "Расписание" for both roles.
3. Dates and times use Europe/Moscow and `django.utils.timezone`. "Today", "in progress" and "next" must be testable with a controlled current time (mock `timezone.now` / `timezone.localdate`; a time-freezing library only if justified).
4. Admin (superuser only, as before): manage rooms, teachers, disciplines, timetable and changes. Validation of overlapping lessons for the same group or room is required at the model/service level, not only in admin forms.
5. Demo data: extend `seed_demo` (still idempotent) with rooms on several floors of the single building, teachers, disciplines, a full week timetable for every demo group, and several changes of each kind in the current and next week relative to the run date. Re-running must not duplicate data. Document in README that re-running `seed_demo` refreshes the demo changes.
6. Queries: no N+1 on schedule pages (select_related / prefetch_related); add a test that bounds the query count.

## Tests (must exist)
- Student sees only lessons of their own group (including shared lectures) - never another group's.
- Student gets 403/404 on staff schedule pages; staff gets 404 for another faculty's group.
- Today/week views at controlled times: in-progress and next lesson, week boundaries, empty day.
- Each change type is applied and shown correctly (cancelled, moved in and out of a day/week, room change, teacher replacement).
- Overlap validation for group and room.
- Schedule renders for a date far from the seed date (e.g. +2 weeks) without reseeding.
- `seed_demo` remains idempotent.

## Out of scope
Room map, grades, attendance, notifications, staff editing of the schedule outside admin, calendar export, visual theme. TASK-002 tech-debt items (separate task).

## Verification
All existing verification commands pass (check, deploy check, makemigrations --check, test, ruff, CI YAML), `seed_demo` runs twice without errors, manual check of today/week pages at 360 px width.

── Ran 2 commands, explored 1 search, 1 file ───────────────
  ── Thought for 5ms
    I need to check where things stand: the TASK-002 implementation, the review notes, and whether the TASK-002 spec has changed.
  ── Ran git log --oneline | head -8 && git status --short && git diff 04b7f0c --stat | tail -5 && ls docs docs/* && grep -n "Amendment\|review note\|Review note" -i docs/tasks/TASK-002.md | head; tail -60 docs/tasks/TASK-002.md | head -80 (1s)
    $ git log --oneline | head -8 && git status --short && git diff 04b7f0c --stat | tail -5 && ls docs docs/* && grep -n "Amendment\|review note\|Review note" -i docs/tasks/TASK-002.md | head; tail -60 docs/tasks/TASK-002.md | head -80
    001c455 TASK-002: users, roles, login and access control
    04b7f0c TASK-001: production settings tests (amendment 1)
    42f5465 Team protocol: reviewer test proposals
    2492a70 TASK-001: Django skeleton and CI
    bd9d1c1 Team protocol: lead-only commits, changelog, agreed project plan
    15e0748 Initial commit: agent team configuration
     M plan.md
     university/migrations/__init__.py                  |   0
     university/models.py                               |  64 ++
     university/tests/__init__.py                       |   0
     university/tests/test_models.py                    |  35 ++
     50 files changed, 2237 insertions(+), 6 deletions(-)
    docs:
    tasks

    docs/tasks:
    TASK-001.md
    TASK-002.md
    23:10. TASK-001 review notes fixed (section 5.12).
    346:### 5.12 TASK-001 review notes

    `accounts/tests/test_admin.py`:
    - `test_student_and_staff_cannot_open_admin` — force_login student, then staff; GET `reverse("admin:index")` → 302 to admin login (not 200).
    - `test_superuser_can_open_admin` — 200.
    - `test_admin_user_add_form_has_role` — superuser GET `reverse("admin:accounts_user_add")` → 200, contains `name="role"`.

    `university/tests/test_models.py`:
    - `test_course_out_of_range_rejected` — `StudyGroup(course=0)` and `7` → `IntegrityError` on save (each in `transaction.atomic()`); `full_clean()` → `ValidationError`.
    - `test_program_unique_per_faculty` — duplicate (faculty, code) → `IntegrityError`; same code in another faculty is allowed.
    - `test_group_faculty_property`.

    `core/tests/test_views.py` changes: `HomeViewTests.setUpTestData` creates `User.objects.create_user("home-user", role="student")`; `setUp` calls `self.client.force_login(...)`. Add `test_home_requires_login` (anonymous → 302 to `/login/?next=/`). Health tests unchanged and must still pass (including `assertNumQueries(0)`).

    `core/tests/test_settings.py` add:
    - `test_custom_user_model` — `settings.AUTH_USER_MODEL == "accounts.User"`.
    - `test_login_required_middleware_after_auth` — index of `LoginRequiredMiddleware` == index of `AuthenticationMiddleware` + 1.

    ---

    ## 8. Implementation order

    Shell for every step: repo root, `.venv` active, `export DEBUG=true`, `export DEMO_PASSWORD='Local-Demo-Pass-2026!'` (never edit `.env`).

    1. `university` app: models, admin, apps; add to `INSTALLED_APPS`. Do **not** migrate yet.
    2. `accounts` app: models, admin, apps; settings changes 5.6 (all of them). `rm -f db.sqlite3`. `python manage.py makemigrations university accounts`. `python manage.py migrate`. Verify `python manage.py check`.
    3. `accounts/access.py`, `accounts/selectors.py` + `accounts/tests/helpers.py`, `test_access.py`, `test_models.py`, `university/tests/test_models.py`. Verify: `python manage.py test accounts university`.
    4. Views, URLs, templates, `base.html` nav, CSS, `core/views.py` decorator. Update `core/tests/*`. Write `accounts/tests/test_views.py`, `test_admin.py`. Verify: `python manage.py test`.
    5. `accounts/demo.py`, command, `test_seed_demo.py`. Verify: `python manage.py seed_demo` twice.
    6. `.env.example`, README, `pyproject.toml`, CI, TASK-001 notes (5.10–5.12).
    7. `ruff format .`, then all of section 9. Send the `REPORT` to the Reviewer. Do not commit.

    ## 9. Verification

    ```bash
    source .venv/bin/activate
    export DEBUG=true
    python manage.py check                                   # no issues
    python manage.py makemigrations --check --dry-run        # No changes detected
    python manage.py test                                    # OK
    DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
      ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
      python manage.py check --deploy --fail-level WARNING   # exit 0, "(1 silenced)"
    ruff check . && ruff format --check .
    python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
    DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo   # twice, both succeed
    DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
    env -u DEMO_PASSWORD python manage.py seed_demo; echo "exit=$?"     # CommandError, exit != 0 (only if .env has no DEMO_PASSWORD)
    ```
    Manual (runserver, 360 px width): log in as `student1` → profile; `/staff/students/` → 403. Log in as `staff1` → list shows Соколова and Ким, not Белов. No horizontal scroll on any page.

    In the `REPORT`, paste the output tails and the test count.

    ## 10. Risks

    - **Role vs `is_staff` confusion** (section 4.1). The DB constraint blocks admin access for non-superusers even if code makes a mistake.
    - **IDOR**: any future view that takes a student ID must start from `students_visible_to(request.user)` (or an equivalent selector). Raw `StudentProfile.objects.get(pk=...)` in a view is a defect.
    - **Default deny**: new views are protected automatically by `LoginRequiredMiddleware`; making a view public requires `@login_not_required` and an update of test 2 in section 7 (intended friction).
    - **Demo password**: one shared password for all demo accounts, from env only. The user must add `DEMO_PASSWORD` to `.env` manually. It must not appear in README, fixtures, logs or command output.
    - **Login brute force**: no rate limiting yet (out of scope; later task before public deploy).
    - **Migration reset**: the first migrations of `accounts` and `university` are created now; after this task never delete them — later model changes need new migrations.
  ── Thought for 7ms
    I'm looking for a review note saying admin forms shouldn't be trusted to validate constraints on fields they don't include. It might be in the CHANGELOG or plan.md, so I'll grep for it.
  ── Searched for constraint\|tech-debt\|tech debt in CHANGELOG.md
  ── Thought for 1s
    I'm noting that Django only runs constraint validation when every referenced field is on the form, so the overlap check has to live in the model's clean() and a service function instead of relying on the admin form. I'm weighing whether the check belongs in save() too, leaning toward a validate_* service function called from clean(), with the admin form needing to include all the relevant fields.

    I'm also making the seed call run full_clean and validation explicitly. Next I'll go through the accounts demo module, the seed command, the models, the base template nav, the test helpers, the README sections, and the CSS.
  ── Read accounts/demo.py
  ── Thought for 3m 44s
    I'm checking whether the test_seed_demo test uses exact counts that the new models would break, and I'm noting the resolver walk test should be fine since the new URLs require login. Then I'm moving on to design TASK-003, starting with a new `schedule` app as its own bounded context, separate from the university reference data, since grades and attendance will later depend on it.

    I'm weighing where Discipline, Teacher, and Room should live, since grades will also use Discipline. I'm leaning toward putting them in `university` as shared reference data, with the timetable itself in `schedule`, so the map can depend on Room without going through schedule.

    I'm settling the time slots as a fixed code constant rather than a database model, with seven 90-minute periods, since no one edits them. Room codes will be lowercase slugs that work as SVG ids, with a floor and a unique number, and I'm checking whether a regex check constraint can be enforced on SQLite.

    I'm settling the remaining model fields: Teacher gets a name split with an optional middle name, a title, and derived full and short name properties, while Discipline gets a unique name and a short name. For the schedule app, I'm starting to list the lesson types, leaning toward lecture, seminar, and lab, and I'm wondering whether to add practice or consultation as well.

    I'm defining the `WeeklyLesson` template for the timetable: a weekday, a time slot, the discipline, lesson type, teacher, room, and the groups it applies to, valid over a date range. I'm adding constraints so the end date can't precede the start, the weekday stays within the week, and the slot must exist in the fixed time slot table.

    I'm working out how to seed WeeklyLesson rows without creating duplicates on a re-run, since a fixed semester date range would go stale if the seed runs in a later year. A relative date range is the alternative, but it doesn't solve the lookup problem, and I'm weighing which natural key could identify a lesson reliably.

    I'm weighing whether seeding by deleting and recreating the weekly lessons is safe, since later attendance records would cascade with them. I'm leaning toward giving each seeded lesson a stable key so re-runs update in place instead of wiping rows that other data will point to.

    I'm settling the seed date range as a fixed semester window, Sep 2026 through Jan 2027, so the demo lessons stay valid through the period I need. I'm still checking what happens if the seed runs outside that window, such as in CI at some other date.

    I'm deciding how to seed the demo weekly lessons so re-runs update in place: I'm keying each one on discipline, lesson type, weekday, and slot, and making the date range relative to the run date. The one edge I'm accepting is that an admin-created lesson with the same combination would collide.

    I'm deciding the seed's validity window relative to the run date instead of fixed semester dates, so the demo stays valid whenever it's run. I'm weighing a range around the run date against constants for a semester, and I'm checking that re-running the seed with updated ranges won't trip the overlap validation.

    I'm settling the date range for seeded weekly lessons relative to the run date, from eight weeks back to about twelve weeks ahead, so re-runs extend it. I'm also defining the LessonChange record, a dated change to a single occurrence of a weekly lesson, with a kind of cancelled, moved, room changed, or teacher replaced, plus optional new date, slot, room, and teacher, and a required reason.

    I'm working out the LessonChange kinds: a cancellation carries no replacement values, a move needs a new date and slot with an optional new room, a room change needs only a new room, and a teacher replacement needs only a new teacher. I'm planning to enforce those rules with check constraints in the database and again in clean().

    I'm defining the occurrence structure that the schedule service will return: the template lesson, its original and actual dates, slot, room, teacher, any change attached, and a status field.

    I'm pinning down the day view: regular occurrences for the day's weekday, with a cancelled or moved-out lesson struck at its original slot, room or teacher changes shown as old-to-new, and moved-in lessons appearing at their new slot with a note of where they came from, including the same-day move case where both entries appear.

    I'm defining the item shape for the day view: each entry carries its times, discipline, teacher and room, and the original values where something changed. I'm marking which kinds actually take place and which don't, cancelled and moved-out entries among them.

    I'm writing the day-view query: first the weekly lessons for the requested groups whose validity overlaps the range, then the changes for those lessons that fall in the range or move into it.

    I'm now deciding the helper signatures: a `TimeSlot` record with start and end times, a fixed slot tuple with a choices list and a lookup that fails on unknown numbers, and a Monday-based week start with a parser for the week query parameter.

    I'm settling the URL shape for the schedule views: today at `/schedule/`, and a week view where the date goes in the path, with a custom ISO date converter that returns a 404 on invalid input.

    I'm settling the staff schedule URLs: a group list for the faculty at `/staff/schedule/`, and per-group views for the current week and for the week containing a given date, using the same date converter.

    I'm settling where group visibility lives: an `accounts/selectors.py` function that returns the groups a user can see, with staff limited to their faculty and students to their own group. For the "today" page, I'm planning to mark the item currently in progress and the next upcoming one, comparing against the current local time.

    I'm settling the overlap check for same-time entries: two happening occurrences at the same date and slot that share a group or a room.

    I'm working through the overlap check for the weekly lessons: two lessons at the same weekday and slot with overlapping validity and either the same room or shared groups. Since groups are many-to-many and only saved after the main object, I can't rely on model clean() for that, so I'm leaning toward a service function that validates, saves and sets the groups atomically, called from the admin form and the seed.

    I'm settling the conflict check for weekly lessons: a function in `schedule/validation.py` that looks for overlapping lessons with the same weekday and slot, a shared room or shared groups, and I'm planning to call it from the admin form's clean and from the seed, since the group relation isn't saved until after the model.

    I'm sketching the `save_weekly_lesson` service: it wraps validation, saving, and setting the groups inside one atomic step, since the group relation can only be written after the lesson exists.

    I'm settling how the save path works: `save_weekly_lesson` checks conflicts, saves the lesson and sets its groups in one atomic step, since model `clean()` can't see the many-to-many groups. The admin form will run the same check against its cleaned groups, and `save_lesson_change` will validate a change before saving it.

    I'm working out how to check for conflicts when a lesson change moves an occurrence: for a target date, slot, room and group set, I need to find which happening occurrences already sit in that slot, counting recurring lessons that run that day minus any cancelled or moved out.

    I'm working out the validation for the occurrences: I'll reuse one `occurrences_between` helper for both the day view and the conflict checks, with groups left open so the check covers every group. For a template lesson, the room is overridden if a change applies, and for a moved-in lesson it's the change's new room, so a collision is any shared room or shared group in the same slot.

    I'm checking the validation rules for `LessonChange` next: the original date has to fall on the lesson's weekday and within its validity, and each change kind needs its own required fields. A move must actually change the date or slot, a room change needs a different room, and a teacher replacement needs a different teacher. Cancellations carry no replacement values, and every change needs a non-blank reason.

    I'm now checking the remaining conflict rules for `LessonChange`: a moved lesson has to avoid the room and groups at its new date and slot, and a room change has to avoid other occurrences using the new room at the original slot. I'm leaving teacher double-booking out of scope since the requirement only covers groups and rooms. I'm also planning DB check constraints so cancellations carry no replacement values and moves always set a new date and slot.

    I'm adding the CHECK constraint that ties each change kind to its own required fields, plus a unique constraint so a weekly lesson has at most one change per date. Then I'm noting that a single occurrence can't carry both a room change and a teacher replacement, which I'll accept and document. Last, I'm planning a `changes_affecting` selector that finds changes for a group set across a date range by either original or new date, since the display needs it anyway.

    Still writing the display dataclass...

    I'm defining the display dataclasses for the schedule, with a flag for whether an item still happens and one for whether it differs from the regular timetable. Moved-out and moved-in items get simpler fields for the destination date and slot. Each day's items will be sorted by slot and kind, and the week will cover Monday onward, with empty days hidden.

    I'm laying out the service API: `occurrences_between` for a date range with optional groups, `day_schedule` and `week_schedule` built on top of it, a pure `mark_today` that picks the in-progress and next items, and a `week_start` helper. I'm about to write out the algorithm for `occurrences_between`.

    I'm working through the query for occurrences: first checking that the range is valid, then narrowing the lessons to those valid in the window and, if groups were given, to those tied to them. I'm also pulling the changes that apply to those groups in the same range, so both can be combined.

    I'm working through how each lesson on a given day turns into a schedule item: regular lessons keep their own room and teacher, cancelled ones are marked cancelled, moved-out ones point to their new date and slot, and room-changed ones take the new room while keeping the original.

    I'm settling the algorithm for `occurrences_between`: each lesson on a matching weekday becomes a regular item unless a change applies, with cancellations, moved-out, room-changed and teacher-replaced cases each handled separately. Moved lessons also produce a moved-in item at their new date and slot, and the whole list gets sorted by date, slot, discipline and kind. I'm also counting the database queries it needs.

    I'm checking that the query count stays flat as the data grows, by comparing a small dataset against one with ten more lessons and changes, and I'm keeping the prefetched groups so shared lectures show up for each student's group.

    I'm sketching the lesson item template next, with a CSS class per kind, a "now" marker for the in-progress item, and the time range and period number in the header. The discipline name and lesson type go on the title line, and the teacher shows the original struck through when it was replaced.

    I'm sketching the lesson item template now: a class per kind, the time range and period number in the header, the discipline and lesson type on the title line, and the teacher and room shown with the original struck through when they were replaced.

    I'm working out how to mark the currently in-progress and next items in the template. Comparing dataclass instances for equality would be heavy and fragile, so I'm considering having the day builder attach a marker to each item instead.

    I'm settling how the today view picks out the in-progress and next lessons: a pure function that takes the day's items and the current local time, and returns rows flagging each item as in progress or next, along with a day-finished flag. The next lesson is the first one starting after the current time, and if something is already in progress, the next one is the item after it.

    I'm settling the Django details: dates format in Russian, so the week's day names come out right, and staff group lists are filtered to what each deanery user can see, with other faculties' groups returning a 404. Students hitting staff pages get a 403, and the nav link points to the today view for students and the staff group list for deanery staff.

    I'm mapping out the URL names for the schedule app: today, the student week views, and the staff group list and week view for a given group and date.

    I'm setting up the URL converter for the ISO dates, limiting the accepted range to 2000 through 2100 so the ±7-day week navigation can't overflow near the edges of date. Then I'm adding the week view context, with the previous and next week starts and a heading showing the date span.

    I'm deciding where the demo seeding code should live, so it doesn't create an import cycle between the accounts and schedule apps. The cleanest option looks like a separate management command that calls the accounts seeder and then a new schedule seeder, rather than having one app import the other.

    I'm sketching out the demo seed data now, starting with a small set of rooms spread across the building's first few floors. The plan is to call the schedule seeder from a single management command inside one transaction, so the accounts seeding and the new timetable data either both land or neither does.

    Now I'm listing the demo teachers and the discipline names I'll use for the timetable seed data.

    I'm laying out the weekly timetable for the first group: a Monday lecture on digital diplomacy with Lebedev in room 101, and an English seminar with Nazarova in room 308 in the second slot.

    I'm laying out the rest of the weekly timetable for both groups, with the shared Wednesday philosophy lecture placed in room 101 and the Thursday and Friday slots filled in.

    I'm checking the Thursday and Friday slots for the second group, moving the English seminar to room 315 in the fourth period so it doesn't clash with the lecturer's other class. Then I'm checking for conflicts across Monday's slots.

    I'm checking the Thursday and Friday slots for conflicts across the rooms and teachers, and confirming that Glebov and Lebedev don't double-book anywhere in the week.

    I'm checking the seed data's timing for the teacher and room conflicts, and I'm defining the eight schedule changes next: cancellations, moves, room swaps and teacher replacements, spread across this week and next. Each change will point to a lesson by its discipline, type, weekday and slot.

    I'm listing the eight schedule changes now, going through the cancellations and moves, and I'm checking the Thursday slot for the moved analytics lab so it doesn't collide with anything.

    I'm pinning down the remaining schedule changes: a room change for Thursday's English seminar moving it to room 402 because of the 308 renovation, and another for next week's Tuesday microeconomics seminar moving to room 114. I'm also setting a cross-week move for the Friday philosophy seminar, from this week into next Monday in room 212.

    I'm finishing the teacher replacement for the Thursday analytics seminar, with Shestakova covering it next week, and noting that the cancellation and move entries are already in place. I'm also making sure all the demo changes stay within the 8-week-back to 12-week-ahead validity window, and that re-running the seed clears the previous demo changes first so nothing duplicates.

    I'm working out the order of the seed steps: rooms first, then teachers matched by their name parts, then disciplines.

    I'm writing the conflict-safe update path: each demo lesson is found by its seed key, its fields are set, and it goes through the same validation as any other save. The demo changes get cleared before the lessons are upserted, and then recreated, so a re-run leaves no duplicates. I'm also planning a summary of the counts for rooms, teachers, disciplines, weekly lessons and changes, and a test that the seed is idempotent and refreshes the changes when run at a later date.

    I'm now checking the test expectations: the seed should be idempotent, and the week schedule for group ЦД-101 should still have lessons on every weekday at a date two weeks later. Then I'm moving on to the admin setup, starting with Room, Teacher and Discipline in the university app, and planning the weekly lesson admin in schedule.

    I'm setting up the admin for LessonChange as well, using all fields, and I'm checking that the weekly lesson form runs the overlap check explicitly in its clean step, so it doesn't depend on database constraints the form leaves out.

    I'm checking where the model-level clean should stop: it will validate the date range order and room conflicts, but the group overlap check belongs in the admin form, since the saved groups aren't set yet when the model validates.

    I'm now sorting out the validation split: the model's clean will only check the date range order and weekday/slot validity, while every conflict check goes through the shared conflicts function called from the form and the service. I'm also noting that editing a weekly lesson's weekday could leave existing changes pointing at dates that no longer match, so that check needs to live in the same place.

    I'm settling the change-conflict logic: a cancelled or teacher-replaced lesson can't create a conflict, so those skip the check. For moves, the target date and slot come from the new values; otherwise they stay with the original. I'm also starting to pick the room to check against, which falls back to the lesson's own room when the change doesn't set one.

    I'm working through the conflict check for each occurrence on the target date: I'll skip the item that is this same lesson's occurrence (matched by lesson id and original date), since for an existing change it would otherwise collide with itself, and flag anything else that is happening in the same slot.

    I'm checking how a moved lesson's target slot can collide with another group's or room's existing occurrence, and I'm making sure each conflict message names the room or group and the clashing lesson. I'm also noting that a move into a later week of the same lesson counts as a group conflict, since it's a different occurrence in the same slot.

    I'm writing the weekly lesson conflict check: it looks for other templates on the same weekday and slot whose date range overlaps, then reports any that share the room or a group. A separate pass will flag the group clash and the orphaned-change case when a template is edited.

    I'm now writing the save path: the lesson gets validated with its own checks first, and the group-level conflict checks run in the same transaction before anything is stored.

    I'm working out the save path for a LessonChange: the change gets its own full validation, then it's stored. For the weekly lesson's own clean, I'm limiting it to the date range order and the weekday/slot validity, since the conflict checks belong in the shared validator.

    I'm writing out the validation rules for LessonChange: date weekday and range checks, the required and forbidden fields for each change kind, and making sure a move or swap isn't identical to the original. If nothing has failed yet, I'll run the conflict check and raise any messages it returns.

    I'm settling the module layout for the schedule app: the models stay in models.py, the time slots in timeslots.py, the read-side views in services.py, and the validation and save logic in validation.py. To avoid a circular import, the model's clean method will import change_conflicts from the services module locally.

    I'm settling the module split: the read-side services stay in their own module, and the validation and save logic goes into a separate module for mutations, so the write path is kept apart from the reads.

    Next I'm sketching the remaining files: admin, the weekly lesson admin form, demo data, templates and tests. Then the Teacher, Room and Discipline models in university, with a migration, and I'm starting on the Room model with its code, floor and number fields and their constraints.

    I'm dropping the idea of a database-level regex check on the room code, since SQLite would depend on a custom function that other tools might not have. The field validator and clean step will cover the code format instead, and the admin form runs them on every save.

    I'm adding the Teacher model with a unique constraint on the full name so seeding stays idempotent, and I'm planning a Discipline model with a unique name and a short name. For WeeklyLesson, I'm defining the weekday and slot fields with their Russian labels and choices, and starting on the discipline link.

    I'm defining the WeeklyLesson fields: the discipline, lesson type, teacher and room links, the groups many-to-many, and the validity date range, then adding meta constraints on the date order, weekday and slot bounds, and an index on weekday and slot.

    Writing the LessonChange model's fields now: a link to the weekly lesson, the original date, the change kind, optional new date, slot, room and teacher, a reason, and a creation timestamp.

    I'm settling the field constraints for LessonChange: the reason can't be empty, and I'm checking the kind-specific required fields alongside the uniqueness rule for one change per occurrence. I'm also looking at the week bounds, Monday through Sunday, and whether Sunday should show in the week view.

    I'm settling the presentation details: the week view will list all seven days, with a compact empty-state line for days that have nothing scheduled. Each teacher will show just their short name, and the staff week header will carry the group name, program and course.

    I'm verifying that November 16, 2026 is a Monday by working out the weekday from January 1 and the day-of-year offset, which lands on Monday.

    I'm now listing the test cases for the schedule services: week start for Monday, Sunday and mid-week, plus occurrences that only fall on the matching weekday within the validity range, with the boundaries inclusive. I'm also checking that a shared lecture shows for both groups, that group A never sees group B's lessons, and how cancelled, moved-within-week and moved-across-week changes appear in the week and day views.

    I'm checking the annotate_today cases next: before the first lesson, during a slot, during a break, after the last one, skipping cancelled lessons, and making sure a time exactly at a slot's end doesn't count as in progress. I'm also planning a test for changes_for_groups_between to confirm it returns a change whose original date falls in the range.

    I'm moving on to the validation tests, covering group and room overlaps with different date ranges, the partial overlap case for a shared group, editing a lesson without flagging itself, and rejecting an empty groups list.

    I'm listing the tests for the validation rules on LessonChange: a weekday mismatch, a date outside the range, a missing new date on a move, a new room on a cancellation, the same room for a room change, and a blank reason. I'm also covering a move into an occupied group slot, a move into a slot freed by a cancellation, a room change into an occupied room, and the database constraints that reject a cancellation with a room and a duplicate change for the same occurrence. Last, I'm checking that the admin form rejects conflicting data, and I'm starting on the view tests, beginning with the redirect to login for anonymous users.

    I'm now writing the view tests: checking that the student today view shows the in-progress slot and next lesson at a fixed time, that Sunday shows the empty-day line, that the week view includes the group's own and shared lessons but not other groups', and that the week navigation and invalid-date 404 behave correctly. Next I'm turning to how a room-changed lesson renders.

    I'm listing the view tests next: the room-changed rendering with the struck-through old room and the new one, the cancelled and moved labels, and the data-room-code attribute. I'm also checking that the student today URL is plain `/schedule/`, that students get 403 on staff pages, and that staff only see their own faculty's groups, with 404s for other faculties and unknown groups. Last, I'm covering the nav links for both roles, a query-count bound on the view, and a far-date render check that I'll put in the seed tests.

    I'm writing the demo seed tests: checking the object counts after seeding, that a second run changes nothing, and that a rerun two weeks later moves the changes into the new week without duplicating them. I'm also confirming that the room ЦД-101 has lessons on every weekday of the far-future week, and that the seeded schedule passes the conflict validation.

    I'm now tallying the lesson counts for the seed data, working through each group's weekly slots by day, and noting that the shared Wednesday lecture would be double-counted if I'm not careful.

    I'm tallying the seeded lessons by group: the nine for each group include the shared Wednesday lecture, so the total is 18 unique lessons. I'm also checking that each lesson's key of discipline, type, weekday and slot is unique across the seed data.

    I'm checking the Thursday lessons for both groups, which are fine, and then verifying the four seeded changes for conflicts. The two cancellations are straightforward, and the Tuesday lab moved to Thursday slot 5 with its room kept is clear. The Friday seminar moves to Monday slot 4 and keeps room-212, and nothing else is scheduled in either of those slots.

    I'm checking the seeded changes against the schedule, starting with the room change for the Thursday seminar, which moves to room 402 with nothing else in that slot. I'm then confirming the Tuesday lab's room change to room 114 doesn't clash with the other group's lesson in that slot, and I'm noting the two teacher changes are simple swaps. That makes two of each change kind, so the seed meets the requirement.

    I'm settling how the seed data is defined, using constants keyed by name. For the staff views, I'm planning that the visible groups come from the staff member's faculty and students see only their own group, and I'm noting that the existing public-URL test still holds, while the new app goes into INSTALLED_APPS and the known-first-party list, along with README and CSS additions.

    I'm sketching the view classes next, starting with a TodayView for students that builds on the same mixins used for the staff pages.

    I'm sketching the view classes now: a student today view that pulls the day's schedule for their group and annotates the rows against the current time, returning the in-progress and next lessons, plus a student week view that defaults to today's date and builds the prev, next and current week links.

    I'm defining the staff group list view as a ListView limited to the groups the staff member can see, and the staff group week view as a page fetched through the same visible-groups lookup, returning a 404 for anything outside it. I'm sharing a week-context helper between the student and staff week views, and I'm defining the day and week schedule structures that the lookup functions return.

    I'm sketching out the spec for the schedule views and demo data, and I'll verify the Monday date for November 16, 2026 and the slot times with a quick Python check before writing it up.
  ── Thought for 6ms
    Расписание оказывается самой большой частью проекта, поэтому сначала проверю даты, на которые будут опираться тесты, и только потом возьмусь за спецификацию.
  ── Ran python3 -c " import datetime as d for s in ['2026-11-16','2026-11-22','2026-11-28','2026-11-12']: x=d.date.fromisoformat(s); print(s, x.strftime('%A'))"; cat accounts/tests/test_seed_demo.py | head -50; grep -n "Demo data" -A 25 README.md | head -40
    $ python3 -c "
  import datetime as d
  for s in ['2026-11-16','2026-11-22','2026-11-28','2026-11-12']: x=d.date.fromisoformat(s); print(s, x.strftime('%A'))"; cat accounts/tests/test_seed_demo.py | head -50; grep -n "Demo data" -A 25 README.md | head -40
    2026-11-16 Monday
    2026-11-22 Sunday
    2026-11-28 Saturday
    2026-11-12 Thursday
    import os
    from io import StringIO
    from unittest import mock

    from django.core.management import call_command
    from django.core.management.base import CommandError
    from django.test import TestCase

    from accounts.models import StaffProfile, StudentProfile, User
    from university.models import Faculty, Program, StudyGroup


    class SeedDemoTests(TestCase):
        def test_creates_expected_data(self):
            with mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}):
                call_command("seed_demo")
            self.assertEqual(Faculty.objects.count(), 2)
            self.assertEqual(Program.objects.count(), 2)
            self.assertEqual(StudyGroup.objects.count(), 2)
            self.assertEqual(StudentProfile.objects.count(), 3)
            self.assertEqual(StaffProfile.objects.count(), 2)
            student1 = User.objects.get(username="student1")
            staff1 = User.objects.get(username="staff1")
            self.assertEqual(student1.role, User.Role.STUDENT)
            self.assertEqual(staff1.role, User.Role.STAFF)
            self.assertFalse(User.objects.filter(is_staff=True).exists())

        def test_idempotent(self):
            with mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}):
                call_command("seed_demo")
                call_command("seed_demo")
            self.assertEqual(Faculty.objects.count(), 2)
            self.assertEqual(Program.objects.count(), 2)
            self.assertEqual(StudyGroup.objects.count(), 2)
            self.assertEqual(StudentProfile.objects.count(), 3)
            self.assertEqual(StaffProfile.objects.count(), 2)
            self.assertEqual(User.objects.count(), 5)
            self.assertTrue(
                User.objects.get(username="student1").check_password("Demo-Pass-2026-test!")
            )

        def test_passwords_hashed(self):
            password = "Demo-Pass-2026-test!"
            with mock.patch.dict(os.environ, {"DEMO_PASSWORD": password}):
                call_command("seed_demo")
            for user in User.objects.all():
                self.assertNotEqual(user.password, password)
                self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
                self.assertTrue(user.check_password(password))

    42:## Demo data
    43-
    44-```bash
    45-python manage.py migrate
    46-python manage.py seed_demo   # needs DEMO_PASSWORD in .env or the environment
    47-```
    48-
    49-All demo data is fictional. Logins (password: the value of `DEMO_PASSWORD`):
    50-
    51-| Login | Faculty | Group |
    52-|---|---|---|
    53-| `student1` | FDD | ЦД-101 |
    54-| `student2` | FAE | ЭД-201 |
    55-| `student3` | FDD | ЦД-101 |
    56-| `staff1` | FDD | — |
    57-| `staff2` | FAE | — |
    58-
    59-Superuser (Django admin only): `python manage.py createsuperuser`.
    60-
    61-## Environment variables
    62-
    63-| Name | Default | Purpose |
    64-|---|---|---|
    65-| `DEBUG` | `false` | Enable debug mode in development. |
    66-| `SECRET_KEY` | (dev key in debug) | Django secret key; required when `DEBUG=false`. |
    67-| `ALLOWED_HOSTS` | `localhost,127.0.0.1` (debug) | Comma-separated allowed hostnames. |
  ── Thought for 4ms
    I'm noting that the existing seed tests call the seed command without mocking time, so the schedule seed will use the real current date, which is acceptable. Next I'll write the spec, and I want it thorough and precise.

── Assistant ───────────────────────────────────────────────
Даты подтвердились: 16.11.2026 — понедельник. Пишу спецификацию TASK-003.

── Created 1 file ──────────────────────────────────────────
  ── Created docs/tasks/TASK-003.md +768
    --- /dev/null
    +++ b~/hackatonproject/docs/tasks/TASK-003.md
    +# TASK-003: Schedule (today / week, changes, staff view)
    +
    +Author: Planner. Status: ready for implementation.
    +Base commit: `001c455`. Product context: `plan.md`. Previous specs: `docs/tasks/TASK-001.md`, `docs/tasks/TASK-002.md` (reuse its access pattern).
    +
    +---
    +
    +## 1. Goal
    +
    +Students see their schedule for today and for any week: time, discipline, lesson type, teacher, room. Changes (cancelled, moved, room changed, teacher replaced) are clearly marked with old and new values and a reason. Staff see a read-only week schedule of any study group of their own faculty. The schedule renders correctly for **any date** without re-running the seed.
    +
    +## 2. Acceptance criteria
    +
    +1. New app `schedule` with `WeeklyLesson` and `LessonChange`; `university` gains `Room`, `Teacher`, `Discipline`. Migrations exist; `makemigrations --check --dry-run` is clean.
    +2. `/schedule/` (today) and `/schedule/week/[<YYYY-MM-DD>/]` work for students; no user or group ID in student URLs.
    +3. Today view marks the lesson in progress and the next lesson; shows an empty state on a day without lessons. Tested with a mocked `django.utils.timezone.now`.
    +4. Every lesson shows time, discipline, type, teacher, room (number, floor); every room element has `data-room-code="<Room.code>"`.
    +5. Each change kind renders with a status label, old value struck through (`<del>`), new value (`<ins>`) where applicable, and the reason.
    +6. Staff: group list limited to own faculty; week view of own-faculty group 200; another faculty's group 404; students get 403 on all staff schedule URLs.
    +7. Overlap of the same group or the same room is rejected by the validation/service layer (not only by admin forms), for weekly lessons and for changes.
    +8. Schedule pages run a constant number of SQL queries (test proves it does not grow with data).
    +9. `seed_demo` remains idempotent; it adds rooms on several floors, teachers, disciplines, a full week for both demo groups and 2 changes of each kind in the current and next week relative to the run date. Re-running refreshes the demo changes.
    +10. All existing verification commands pass; manual check at 360 px.
    +
    +## 3. Out of scope
    +
    +Room map pages (only `data-room-code` now; no links to non-existent pages), grades, attendance, notifications, staff editing outside admin, calendar export, visual theme, teacher double-booking validation, odd/even weeks, one-off extra lessons not derived from a weekly lesson, TASK-002 tech-debt items.
    +
    +---
    +
    +## 4. Design decisions
    +
    +### 4.1 Where models live
    +- `university` (reference data, depends on nothing): add `Room`, `Teacher`, `Discipline`. The map task needs `Room` without the schedule; grades need `Discipline` without the schedule.
    +- New app `schedule` (depends on `university` and `accounts`): `WeeklyLesson`, `LessonChange`, time slots, schedule computation, validation, views, demo seed for the schedule. It is a separate bounded context with its own services and pages; putting it into `university` would mix reference data with business logic.
    +- `university` must never import from `schedule` or `accounts`.
    +
    +### 4.2 Weekly template + dated changes (no generated dated lessons)
    +- `WeeklyLesson` = a recurring lesson: weekday, slot, discipline, type, teacher, room, one or more groups, active date range `[valid_from, valid_until]` (inclusive).
    +- `LessonChange` = an explicit change of **one occurrence**, identified by `(weekly_lesson, original_date)`.
    +- Occurrences are computed on the fly for any requested date range. Therefore the schedule renders for any date without re-seeding (hard constraint). Nothing is stored per date except changes.
    +- **Occurrence identity** (for attendance later): `(weekly_lesson_id, original_date)`. A moved lesson keeps its identity.
    +- At most one change per occurrence (DB unique constraint). A combined change (e.g. moved and new teacher) is out of scope.
    +
    +### 4.3 Time slots are a code constant, not a model
    +The bell schedule is fixed for the fictional university and never edited by users. A constant needs no migration, data seeding or joins, and makes overlap checks an equality test on `(date, slot)` — partial time overlaps cannot happen. Stored as `slot` number (1–7) on lessons and changes.
    +
    +### 4.4 Validation layer (TASK-002 review note)
    +Do not rely on admin forms validating DB constraints for fields they do not include. All business rules live in plain functions in `schedule/validation.py` and are called from:
    +- `schedule/mutations.py` (`save_weekly_lesson`, `save_lesson_change`) — the only write path for code (seed, tests, later tasks);
    +- `LessonChange.clean()` (runs in every `full_clean()`, including admin);
    +- `WeeklyLessonAdminForm.clean()` (needed because `groups` is many-to-many and is not available in `WeeklyLesson.clean()`).
    +Admin forms for schedule models use `fields = "__all__"`.
    +
    +### 4.5 Later tasks (do not implement)
    +- Map: `Room.code` is a stable, unique, lowercase id valid as an SVG element id; `Room.floor` supports multi-floor maps.
    +- Grades: reference `university.Discipline`. Attendance: reference occurrence `(weekly_lesson, original_date)`.
    +- Notifications: `schedule.services.changes_for_groups_between(group_ids, start, end)` answers "schedule changes affecting group X in a date range".
    +
    +---
    +
    +## 5. Architecture
    +
    +### 5.1 Files
    +
    +Create:
    +```
    +schedule/__init__.py
    +schedule/apps.py
    +schedule/models.py
    +schedule/timeslots.py
    +schedule/services.py
    +schedule/validation.py
    +schedule/mutations.py
    +schedule/converters.py
    +schedule/forms.py
    +schedule/admin.py
    +schedule/views.py
    +schedule/urls.py
    +schedule/demo.py
    +schedule/migrations/__init__.py
    +schedule/migrations/0001_initial.py                 (generated)
    +schedule/templates/schedule/today.html
    +schedule/templates/schedule/week.html
    +schedule/templates/schedule/staff_group_list.html
    +schedule/templates/schedule/includes/lesson_item.html
    +schedule/templates/schedule/includes/week_days.html
    +schedule/templates/schedule/includes/week_nav.html
    +schedule/tests/__init__.py
    +schedule/tests/helpers.py
    +schedule/tests/test_timeslots.py
    +schedule/tests/test_services.py
    +schedule/tests/test_validation.py
    +schedule/tests/test_views.py
    +schedule/tests/test_demo.py
    +university/migrations/0002_<generated name>.py     (generated)
    +```
    +Change:
    +```
    +university/models.py, university/admin.py, university/tests/test_models.py,
    +accounts/selectors.py, accounts/tests/test_access.py,
    +accounts/management/commands/seed_demo.py,
    +config/settings.py (INSTALLED_APPS only), config/urls.py,
    +templates/base.html (nav only), static/css/tokens.css, static/css/base.css,
    +README.md, pyproject.toml
    +```
    +Do not change any other file. Do not change `accounts/demo.py`.
    +
    +### 5.2 Settings / URLs / tooling
    +- `INSTALLED_APPS`: add `"schedule"` right after `"accounts"`.
    +- `config/urls.py`: add `path("", include("schedule.urls"))` after the `accounts` include.
    +- `pyproject.toml`: `known-first-party = ["config", "core", "accounts", "university", "schedule"]`.
    +- `SchedulesConfig`: class name `ScheduleConfig`, `name = "schedule"`, `verbose_name = "Расписание"`, `default_auto_field = "django.db.models.BigAutoField"`.
    +
    +### 5.3 `university/models.py` additions
    +
    +**`Room`**
    +| Field | Definition |
    +|---|---|
    +| `code` | `CharField("код", max_length=32, unique=True, validators=[RegexValidator(r"^[a-z][a-z0-9-]*$", "Код: латинские строчные буквы, цифры и дефис; начинается с буквы.")])` |
    +| `floor` | `PositiveSmallIntegerField("этаж", validators=[MinValueValidator(1), MaxValueValidator(20)])` |
    +| `number` | `CharField("номер", max_length=10, unique=True)` |
    +- `Meta`: `ordering = ["floor", "number"]`; `constraints = [CheckConstraint(condition=Q(floor__gte=1) & Q(floor__lte=20), name="university_room_floor_1_20")]`; verbose `"аудитория"` / `"аудитории"`.
    +- `__str__` → `f"ауд. {self.number}"`.
    +- No DB regex constraint (SQLite would need an app-defined function); the validator runs in every `full_clean()`, and seed values are fixed.
    +
    +**`Teacher`** (does not log in; no user link)
    +| Field | Definition |
    +|---|---|
    +| `last_name`, `first_name` | `CharField(max_length=100)` (`"фамилия"`, `"имя"`) |
    +| `middle_name` | `CharField("отчество", max_length=100, blank=True, default="")` |
    +| `title` | `CharField("учёная степень, звание", max_length=100, blank=True, default="")` |
    +- `Meta`: `ordering = ["last_name", "first_name"]`; `constraints = [UniqueConstraint(fields=["last_name", "first_name", "middle_name"], name="university_teacher_unique_name")]`; verbose `"преподаватель"` / `"преподаватели"`.
    +- Properties: `full_name` (same rule as `StudentProfile.full_name`); `short_name` → `"Лебедев А. С."` = `last_name` + `" "` + `f"{first_name[0]}."` + (`f" {middle_name[0]}."` if `middle_name` else `""`).
    +- `__str__` → `self.full_name`.
    +
    +**`Discipline`**
    +| Field | Definition |
    +|---|---|
    +| `name` | `CharField("название", max_length=200, unique=True)` |
    +| `short_name` | `CharField("краткое название", max_length=50)` |
    +- `Meta`: `ordering = ["name"]`; verbose `"дисциплина"` / `"дисциплины"`. `__str__` → `self.name`.
    +
    +`university/admin.py`: register `Room` (`list_display = ("number", "floor", "code")`, `list_filter = ("floor",)`, `search_fields = ("number", "code")`), `Teacher` (`list_display = ("full_name", "title")`, `search_fields = ("last_name", "first_name")`), `Discipline` (`list_display = ("name", "short_name")`, `search_fields = ("name", "short_name")`).
    +
    +### 5.4 `schedule/timeslots.py`
    +
    +```python
    +@dataclass(frozen=True)
    +class TimeSlot:
    +    number: int
    +    start: time
    +    end: time
    +
    +TIME_SLOTS: tuple[TimeSlot, ...] = (
    +    TimeSlot(1, time(9, 0), time(10, 30)),
    +    TimeSlot(2, time(10, 40), time(12, 10)),
    +    TimeSlot(3, time(12, 55), time(14, 25)),
    +    TimeSlot(4, time(14, 35), time(16, 5)),
    +    TimeSlot(5, time(16, 15), time(17, 45)),
    +    TimeSlot(6, time(17, 55), time(19, 25)),
    +    TimeSlot(7, time(19, 35), time(21, 5)),
    +)
    +SLOT_CHOICES: list[tuple[int, str]] = [(s.number, f"{s.number} пара ({s.start:%H:%M}–{s.end:%H:%M})") for s in TIME_SLOTS]
    +MAX_SLOT: int = len(TIME_SLOTS)
    +
    +def get_slot(number: int) -> TimeSlot
    +```
    +- `get_slot`: return the slot with this number; `raise ValueError(f"Unknown slot {number}")` otherwise.
    +- Tests (`test_timeslots.py`, `SimpleTestCase`): numbers are 1..7 consecutive; each `start < end`; slots do not overlap and are ordered; `get_slot(2).start == time(10, 40)`; `get_slot(0)` and `get_slot(8)` raise `ValueError`.
    +
    +### 5.5 `schedule/models.py`
    +
    +```python
    +class Weekday(models.IntegerChoices):   # matches date.weekday()
    +    MONDAY = 0, "Понедельник"
    +    TUESDAY = 1, "Вторник"
    +    WEDNESDAY = 2, "Среда"
    +    THURSDAY = 3, "Четверг"
    +    FRIDAY = 4, "Пятница"
    +    SATURDAY = 5, "Суббота"
    +    SUNDAY = 6, "Воскресенье"
    +
    +class LessonType(models.TextChoices):
    +    LECTURE = "lecture", "Лекция"
    +    SEMINAR = "seminar", "Семинар"
    +    LAB = "lab", "Лабораторная работа"
    +
    +class ChangeKind(models.TextChoices):
    +    CANCELLED = "cancelled", "Отмена"
    +    MOVED = "moved", "Перенос"
    +    ROOM_CHANGED = "room_changed", "Замена аудитории"
    +    TEACHER_REPLACED = "teacher_replaced", "Замена преподавателя"
    +```
    +
    +**`WeeklyLesson`**
    +| Field | Definition |
    +|---|---|
    +| `weekday` | `PositiveSmallIntegerField("день недели", choices=Weekday.choices)` |
    +| `slot` | `PositiveSmallIntegerField("пара", choices=SLOT_CHOICES)` |
    +| `discipline` | `ForeignKey("university.Discipline", on_delete=PROTECT, related_name="weekly_lessons", verbose_name="дисциплина")` |
    +| `lesson_type` | `CharField("тип занятия", max_length=16, choices=LessonType.choices)` |
    +| `teacher` | `ForeignKey("university.Teacher", on_delete=PROTECT, related_name="weekly_lessons", verbose_name="преподаватель")` |
    +| `room` | `ForeignKey("university.Room", on_delete=PROTECT, related_name="weekly_lessons", verbose_name="аудитория")` |
    +| `groups` | `ManyToManyField("university.StudyGroup", related_name="weekly_lessons", verbose_name="группы")` |
    +| `valid_from` | `DateField("действует с")` |
    +| `valid_until` | `DateField("действует по")` (inclusive) |
    +- `Meta`: `ordering = ["weekday", "slot"]`; `indexes = [Index(fields=["weekday", "slot"], name="schedule_weekly_day_slot_idx")]`; constraints:
    +  - `CheckConstraint(condition=Q(valid_until__gte=F("valid_from")), name="schedule_weekly_valid_range")`
    +  - `CheckConstraint(condition=Q(weekday__gte=0) & Q(weekday__lte=6), name="schedule_weekly_weekday_0_6")`
    +  - `CheckConstraint(condition=Q(slot__gte=1) & Q(slot__lte=MAX_SLOT), name="schedule_weekly_slot_range")`
    +  - verbose `"занятие (еженедельное)"` / `"занятия (еженедельные)"`.
    +- `__str__` → `f"{self.get_weekday_display()}, {self.slot} пара — {self.discipline}"`.
    +- `clean()`: `super().clean()`; if both dates set and `valid_until < valid_from` → `ValidationError({"valid_until": "Дата окончания раньше даты начала."})`. No conflict checks here (groups are M2M; see 4.4).
    +- Property `time_slot -> TimeSlot` → `get_slot(self.slot)`.
    +
    +**`LessonChange`**
    +| Field | Definition |
    +|---|---|
    +| `weekly_lesson` | `ForeignKey(WeeklyLesson, on_delete=CASCADE, related_name="changes", verbose_name="занятие")` |
    +| `original_date` | `DateField("дата занятия по расписанию")` |
    +| `kind` | `CharField("вид изменения", max_length=20, choices=ChangeKind.choices)` |
    +| `new_date` | `DateField("новая дата", null=True, blank=True)` |
    +| `new_slot` | `PositiveSmallIntegerField("новая пара", choices=SLOT_CHOICES, null=True, blank=True)` |
    +| `new_room` | `ForeignKey("university.Room", on_delete=PROTECT, null=True, blank=True, related_name="+", verbose_name="новая аудитория")` |
    +| `new_teacher` | `ForeignKey("university.Teacher", on_delete=PROTECT, null=True, blank=True, related_name="+", verbose_name="новый преподаватель")` |
    +| `reason` | `CharField("причина", max_length=200)` |
    +| `created_at` | `DateTimeField("создано", auto_now_add=True)` |
    +- `Meta`: `ordering = ["original_date"]`; `indexes = [Index(fields=["original_date"], name="schedule_change_orig_idx"), Index(fields=["new_date"], name="schedule_change_new_idx")]`; constraints:
    +  - `UniqueConstraint(fields=["weekly_lesson", "original_date"], name="schedule_change_one_per_occurrence")`
    +  - `CheckConstraint(condition=~Q(reason=""), name="schedule_change_reason_required")`
    +  - `CheckConstraint(name="schedule_change_fields_match_kind", condition=` OR of:
    +    - `Q(kind="cancelled", new_date__isnull=True, new_slot__isnull=True, new_room__isnull=True, new_teacher__isnull=True)`
    +    - `Q(kind="moved", new_date__isnull=False, new_slot__isnull=False, new_teacher__isnull=True)` (`new_room` optional)
    +    - `Q(kind="room_changed", new_room__isnull=False, new_date__isnull=True, new_slot__isnull=True, new_teacher__isnull=True)`
    +    - `Q(kind="teacher_replaced", new_teacher__isnull=False, new_date__isnull=True, new_slot__isnull=True, new_room__isnull=True)` `)`
    +  - also `CheckConstraint(condition=Q(new_slot__isnull=True) | (Q(new_slot__gte=1) & Q(new_slot__lte=MAX_SLOT)), name="schedule_change_new_slot_range")`
    +  - verbose `"изменение расписания"` / `"изменения расписания"`.
    +- `__str__` → `f"{self.get_kind_display()}: {self.weekly_lesson} ({self.original_date:%d.%m.%Y})"`.
    +- `clean()` — see 6.3.
    +
    +### 5.6 `accounts/selectors.py` addition
    +
    +```python
    +def groups_visible_to(user: AbstractBaseUser | AnonymousUser) -> QuerySet[StudyGroup]
    +```
    +- Purpose: every study-group lookup from a request starts here (same pattern as `students_visible_to`).
    +- Algorithm:
    +  1. `qs = StudyGroup.objects.select_related("program__faculty")`.
    +  2. Not authenticated / not active → `qs.none()`.
    +  3. STAFF: staff profile (missing → `qs.none()`) → `qs.filter(program__faculty=profile.faculty)`.
    +  4. STUDENT: student profile (missing → `qs.none()`) → `qs.filter(pk=profile.group_id)`.
    +  5. Else → `qs.none()`.
    +- Tests (add to `accounts/tests/test_access.py`): staff X sees only faculty X groups; student sees only own group; superuser, anonymous, staff without profile → empty.
    +
    +### 5.7 URLs (`schedule/urls.py`, `app_name = "schedule"`)
    +
    +`register_converter(IsoDateConverter, "isodate")`.
    +
    +| Path | View | Name |
    +|---|---|---|
    +| `schedule/` | `TodayView` | `today` |
    +| `schedule/week/` | `StudentWeekView` | `week` |
    +| `schedule/week/<isodate:day>/` | `StudentWeekView` | `week_of` |
    +| `staff/schedule/` | `StaffGroupListView` | `staff_groups` |
    +| `staff/schedule/<int:group_id>/` | `StaffGroupWeekView` | `staff_group_week` |
    +| `staff/schedule/<int:group_id>/<isodate:day>/` | `StaffGroupWeekView` | `staff_group_week_of` |
    +
    +`schedule/converters.py`:
    +```python
    +class IsoDateConverter:
    +    regex = r"\d{4}-\d{2}-\d{2}"
    +    def to_python(self, value: str) -> date
    +    def to_url(self, value: date) -> str
    +```
    +- `to_python`: `day = date.fromisoformat(value)` (invalid → `ValueError`); if not `date(2000, 1, 1) <= day <= date(2100, 12, 31)` → `raise ValueError`. Django turns `ValueError` into "no match" → 404. The range keeps `±7 days` arithmetic far from `date.min/max`.
    +- `to_url`: `value.isoformat()`.
    +- Tests: `"2026-11-16"` → `date(2026, 11, 16)`; `"2026-02-30"` and `"1999-12-31"` → `ValueError`; `to_url(date(2026, 11, 16)) == "2026-11-16"`.
    +
    +### 5.8 Navigation (`templates/base.html`)
    +Inside the existing `<ul class="site-nav-list">`, after the "Профиль" item:
    +```html
    +{% if user.is_student %}
    +<li><a href="{% url 'schedule:today' %}">Расписание</a></li>
    +{% elif user.is_deanery_staff %}
    +<li><a href="{% url 'schedule:staff_groups' %}">Расписание</a></li>
    +{% endif %}
    +```
    +
    +---
    +
    +## 6. Functions
    +
    +### 6.1 `schedule/services.py` — read side
    +
    +```python
    +class ItemKind(StrEnum):
    +    REGULAR = "regular"
    +    CANCELLED = "cancelled"
    +    MOVED_OUT = "moved-out"      # shown on the original date: the lesson is not here
    +    MOVED_IN = "moved-in"        # shown on the new date
    +    ROOM_CHANGED = "room-changed"
    +    TEACHER_REPLACED = "teacher-replaced"
    +
    +@dataclass(frozen=True, eq=False)
    +class ScheduleItem:
    +    kind: ItemKind
    +    date: date                    # date on which this item is displayed
    +    slot: TimeSlot                # displayed slot
    +    lesson: WeeklyLesson
    +    original_date: date           # occurrence identity together with lesson.id
    +    room: Room                    # effective room
    +    teacher: Teacher              # effective teacher
    +    original_room: Room | None    # set when the effective room differs from lesson.room
    +    original_teacher: Teacher | None
    +    change: LessonChange | None
    +    moved_to_date: date | None    # MOVED_OUT only
    +    moved_to_slot: TimeSlot | None
    +    moved_from_date: date | None  # MOVED_IN only
    +    moved_from_slot: TimeSlot | None
    +
    +    @property is_happening -> bool: kind not in (CANCELLED, MOVED_OUT)
    +    @property is_changed -> bool:   kind != REGULAR
    +
    +@dataclass(frozen=True)
    +class DaySchedule:
    +    date: date
    +    items: list[ScheduleItem]
    +    is_today: bool
    +
    +@dataclass(frozen=True)
    +class WeekSchedule:
    +    start: date                   # Monday
    +    end: date                     # Sunday
    +    days: list[DaySchedule]       # exactly 7, Monday..Sunday
    +
    +@dataclass(frozen=True)
    +class TodayRow:
    +    item: ScheduleItem
    +    is_in_progress: bool
    +    is_next: bool
    +
    +@dataclass(frozen=True)
    +class TodayAnnotation:
    +    rows: list[TodayRow]
    +    in_progress: ScheduleItem | None
    +    next_item: ScheduleItem | None
    +    day_finished: bool            # there were happening lessons and all have ended
    +```
    +`eq=False` on `ScheduleItem`: identity comparison only (model instances inside).
    +
    +#### `week_start(day: date) -> date`
    +Return `day - timedelta(days=day.weekday())` (Monday). Tests: Monday → same; Sunday 2026-11-22 → 2026-11-16; Wednesday → Monday.
    +
    +#### `changes_for_groups_between(group_ids: Collection[int] | None, start: date, end: date) -> QuerySet[LessonChange]`
    +- Purpose: all changes affecting the groups in `[start, end]` (inclusive). Reused by notifications later.
    +- Algorithm:
    +  1. `qs = LessonChange.objects.filter(Q(original_date__range=(start, end)) | Q(kind=ChangeKind.MOVED, new_date__range=(start, end)))`.
    +  2. If `group_ids is not None`: `qs = qs.filter(weekly_lesson__groups__in=group_ids).distinct()`.
    +  3. `return qs.select_related("weekly_lesson__discipline", "weekly_lesson__teacher", "weekly_lesson__room", "new_room", "new_teacher").prefetch_related("weekly_lesson__groups")`.
    +- Tests: includes a change with `original_date` in range; includes a MOVED change whose `new_date` is in range and `original_date` is not; excludes changes of other groups; `None` returns all groups.
    +
    +#### `occurrences_between(start: date, end: date, group_ids: Collection[int] | None) -> list[ScheduleItem]`
    +- Purpose: the single computation of what happens in `[start, end]` for the groups (`None` = all groups; used by validation).
    +- Raises: `ValueError` if `start > end`.
    +- Algorithm:
    +  1. If `group_ids is not None and not group_ids` → return `[]`.
    +  2. `lessons_qs = WeeklyLesson.objects.filter(valid_from__lte=end, valid_until__gte=start)`; if `group_ids is not None`: `.filter(groups__in=group_ids).distinct()`; then `.select_related("discipline", "teacher", "room").prefetch_related("groups")`. Evaluate to a list.
    +  3. `changes = list(changes_for_groups_between(group_ids, start, end))`; `by_key = {(c.weekly_lesson_id, c.original_date): c for c in changes}`.
    +  4. For each day `d` from `start` to `end`, for each lesson with `lesson.weekday == d.weekday()` and `lesson.valid_from <= d <= lesson.valid_until`: `change = by_key.get((lesson.id, d))` and build an item with `date=d`, `original_date=d`, `slot=lesson.time_slot`:
    +     - no change → `REGULAR`, `room=lesson.room`, `teacher=lesson.teacher`;
    +     - `CANCELLED` → `CANCELLED`, room/teacher from lesson;
    +     - `MOVED` → `MOVED_OUT`, room/teacher from lesson, `moved_to_date=change.new_date`, `moved_to_slot=get_slot(change.new_slot)`;
    +     - `ROOM_CHANGED` → `ROOM_CHANGED`, `room=change.new_room`, `original_room=lesson.room`;
    +     - `TEACHER_REPLACED` → `TEACHER_REPLACED`, `teacher=change.new_teacher`, `original_teacher=lesson.teacher`.
    +  5. For each change with `kind == MOVED` and `start <= change.new_date <= end`: `lesson = change.weekly_lesson`; item `MOVED_IN` with `date=change.new_date`, `slot=get_slot(change.new_slot)`, `original_date=change.original_date`, `room=change.new_room or lesson.room`, `original_room=lesson.room if change.new_room and change.new_room_id != lesson.room_id else None`, `teacher=lesson.teacher`, `moved_from_date=change.original_date`, `moved_from_slot=lesson.time_slot`.
    +  6. Sort by `(item.date, item.slot.number, item.is_happening is False, item.lesson.discipline.name)` — at the same slot, happening items come first.
    +- Query budget: exactly 4 queries (lessons, lessons' groups, changes, changes' lessons' groups), independent of data size.
    +- Edge cases: lesson whose range starts/ends inside `[start, end]` — only days inside the range; MOVED change whose original occurrence is outside `[start, end]` still yields `MOVED_IN` inside; the same lesson moved within one day yields both `MOVED_OUT` and `MOVED_IN` on that day.
    +
    +#### `day_schedule(day: date, group_ids: Collection[int], today: date) -> DaySchedule`
    +`items = occurrences_between(day, day, group_ids)`; return `DaySchedule(date=day, items=items, is_today=(day == today))`.
    +
    +#### `week_schedule(any_day: date, group_ids: Collection[int], today: date) -> WeekSchedule`
    +1. `start = week_start(any_day)`, `end = start + timedelta(days=6)`.
    +2. `items = occurrences_between(start, end, group_ids)` (one call).
    +3. Group items by `item.date` into 7 `DaySchedule`s (Monday..Sunday; empty lists for empty days; `is_today = d == today`).
    +
    +#### `annotate_today(items: list[ScheduleItem], now: time) -> TodayAnnotation`
    +- Pure function (no DB, no clock).
    +- Algorithm:
    +  1. `happening = [i for i in items if i.is_happening]`.
    +  2. `in_progress` = first `i` in `happening` with `i.slot.start <= now < i.slot.end`, else `None`.
    +  3. `next_item` = first `i` in `happening` with `i.slot.start > now`, else `None`.
    +  4. `day_finished = bool(happening) and all(i.slot.end <= now for i in happening)`.
    +  5. `rows = [TodayRow(item=i, is_in_progress=i is in_progress, is_next=i is next_item) for i in items]`.
    +- Tests (build `ScheduleItem`s via `occurrences_between` on test data or construct directly with unsaved model instances):
    +  - before first lesson (08:00): `in_progress None`, `next` = slot 1 item;
    +  - during slot 2 (10:50): `in_progress` = slot 2, `next` = slot 3;
    +  - in a break (12:30, between slots 2 and 3): `in_progress None`, `next` = slot 3;
    +  - exactly at end of slot 2 (12:10): slot 2 not in progress;
    +  - after last lesson: both `None`, `day_finished True`;
    +  - cancelled slot 3 is skipped: `next` = slot 4;
    +  - empty list: all `None`, `day_finished False`.
    +
    +### 6.2 `schedule/validation.py`
    +
    +#### `validate_weekly_lesson(*, weekday: int, slot: int, valid_from: date, valid_until: date, room_id: int, group_ids: Collection[int], exclude_pk: int | None) -> list[str]`
    +- Purpose: business rules for a weekly lesson that need other rows or M2M data. Returns Russian error messages (empty list = valid).
    +- Algorithm:
    +  1. `errors = []`. If not `group_ids` → append `"Выберите хотя бы одну группу."`.
    +  2. `others = WeeklyLesson.objects.filter(weekday=weekday, slot=slot, valid_from__lte=valid_until, valid_until__gte=valid_from)`; if `exclude_pk`: `.exclude(pk=exclude_pk)`.
    +  3. For each `o` in `others.filter(room_id=room_id).select_related("discipline", "room")`: append `f"Аудитория {o.room.number} уже занята в это время: {o.discipline.name}."`.
    +  4. For each `o` in `others.filter(groups__in=group_ids).distinct().select_related("discipline").prefetch_related("groups")`: for each group of `o` whose id is in `group_ids`: append `f"Группа {g.name} уже занята в это время: {o.discipline.name}."`.
    +  5. If `exclude_pk`: for each `LessonChange` of that lesson where `original_date.weekday() != weekday` or not `valid_from <= original_date <= valid_until`: append `f"Есть изменение на {c.original_date:%d.%m.%Y}, которое не подходит к новому расписанию. Сначала удалите его."`.
    +  6. Return `errors`.
    +- Overlap means: same weekday and slot and overlapping date ranges (inclusive). Changes are ignored here (a template conflict is a conflict).
    +
    +#### `change_conflicts(change: LessonChange) -> list[str]`
    +- Purpose: group/room conflicts of the target occurrence of a MOVED or ROOM_CHANGED change.
    +- Precondition: `change.weekly_lesson` is saved; kind-specific fields are valid.
    +- Algorithm:
    +  1. If `change.kind` in (`CANCELLED`, `TEACHER_REPLACED`) → `[]`.
    +  2. `lesson = change.weekly_lesson`. Target: MOVED → `(change.new_date, change.new_slot)`; ROOM_CHANGED → `(change.original_date, lesson.slot)`.
    +  3. `target_room_id = change.new_room_id or lesson.room_id`; `group_ids = set(lesson.groups.values_list("id", flat=True))`.
    +  4. `items = occurrences_between(target_date, target_date, None)`.
    +  5. For each `item` with `item.is_happening` and `item.slot.number == target_slot`, skipping the same occurrence (`item.lesson.id == lesson.id and item.original_date == change.original_date`):
    +     - if `item.room.id == target_room_id` → `f"Аудитория {item.room.number} занята: {item.lesson.discipline.name}, {target_date:%d.%m.%Y}, {target_slot} пара."`;
    +     - for each group of `item.lesson.groups.all()` with id in `group_ids` → `f"Группа {g.name} занята: {item.lesson.discipline.name}, {target_date:%d.%m.%Y}, {target_slot} пара."`.
    +  6. Return the list.
    +- Effect: a slot freed by a cancellation or a move-out is free; editing an existing change does not conflict with itself.
    +
    +### 6.3 `LessonChange.clean()`
    +1. `super().clean()`. If `weekly_lesson_id` is `None` or `original_date` is `None` or `kind` is empty → return (field errors are reported by Django).
    +2. `lesson = self.weekly_lesson`; `errors: dict[str, list[str]] = {}`.
    +3. `original_date.weekday() != lesson.weekday` → `errors["original_date"]` += `"Дата не совпадает с днём недели занятия."`; outside `[lesson.valid_from, lesson.valid_until]` → `"Дата вне периода действия занятия."`.
    +4. Kind rules (mirror of the DB constraint, field-level messages):
    +   - required: MOVED → `new_date`, `new_slot` (`"Обязательно для переноса."`); ROOM_CHANGED → `new_room`; TEACHER_REPLACED → `new_teacher` (`"Обязательно для этого вида изменения."`);
    +   - forbidden (must be empty, `"Не заполняйте для этого вида изменения."`): every `new_*` field not allowed by the constraint in 5.5.
    +5. Value rules: MOVED with `(new_date, new_slot) == (original_date, lesson.slot)` and (`new_room` empty or equal to `lesson.room`) → `errors["new_date"]` `"Новое время совпадает со старым."`; ROOM_CHANGED with `new_room_id == lesson.room_id` → `errors["new_room"]` `"Аудитория не изменилась."`; TEACHER_REPLACED with `new_teacher_id == lesson.teacher_id` → `errors["new_teacher"]` `"Преподаватель не изменился."`.
    +6. If `errors` → `raise ValidationError(errors)`.
    +7. `conflicts = change_conflicts(self)` (import inside the method to avoid a circular import); if any → `raise ValidationError(conflicts)`.
    +
    +### 6.4 `schedule/mutations.py` — the only write path in code
    +
    +#### `save_weekly_lesson(lesson: WeeklyLesson, groups: Sequence[StudyGroup]) -> WeeklyLesson`
    +1. `with transaction.atomic():`
    +2. `lesson.full_clean()` (M2M is ignored by Django here).
    +3. `errors = validate_weekly_lesson(weekday=lesson.weekday, slot=lesson.slot, valid_from=lesson.valid_from, valid_until=lesson.valid_until, room_id=lesson.room_id, group_ids=[g.pk for g in groups], exclude_pk=lesson.pk)`; if `errors` → `raise ValidationError(errors)`.
    +4. `lesson.save()`; `lesson.groups.set(groups)`; return `lesson`.
    +
    +#### `save_lesson_change(change: LessonChange) -> LessonChange`
    +`with transaction.atomic(): change.full_clean(); change.save(); return change`.
    +
    +Tests (`test_validation.py`, `TestCase`):
    +- `test_group_overlap_rejected` — second lesson, same group/weekday/slot, overlapping ranges, other room → `ValidationError` mentioning the group name.
    +- `test_room_overlap_rejected` — different groups, same room/weekday/slot → error mentioning the room number.
    +- `test_partial_group_overlap_rejected` — `[A, B]` vs `[B, C]` → error for `B` only.
    +- `test_non_overlapping_ranges_allowed` — same group/slot, ranges `[Sep 1, Oct 31]` and `[Nov 1, Dec 31]` → OK.
    +- `test_adjacent_inclusive_range_conflicts` — ranges sharing one day (`... Oct 31` and `Oct 31 ...`) → error.
    +- `test_editing_lesson_does_not_conflict_with_itself`.
    +- `test_empty_groups_rejected`.
    +- `test_weekday_edit_with_existing_change_rejected`.
    +- `test_invalid_range_rejected` — `valid_until < valid_from` → `ValidationError`.
    +- `test_admin_form_rejects_group_overlap` — `WeeklyLessonAdminForm(data=...)` → `is_valid() is False`, error in `non_field_errors()`.
    +- Change rules, each via `save_lesson_change` → `ValidationError` with the field key: weekday mismatch; date out of range; MOVED without `new_date`; CANCELLED with `new_room`; ROOM_CHANGED same room; TEACHER_REPLACED same teacher; blank reason.
    +- `test_move_into_busy_group_slot_rejected`; `test_move_into_slot_freed_by_cancellation_allowed`; `test_room_change_into_busy_room_rejected`; `test_room_change_into_room_freed_by_move_allowed`; `test_editing_existing_change_no_self_conflict`.
    +- DB level: `LessonChange.objects.create(kind="cancelled", new_room=room, ...)` → `IntegrityError`; second change for the same `(weekly_lesson, original_date)` → `IntegrityError`; `reason=""` → `IntegrityError` (each in `transaction.atomic()`).
    +
    +### 6.5 `schedule/forms.py` and `schedule/admin.py`
    +
    +```python
    +class WeeklyLessonAdminForm(forms.ModelForm):
    +    class Meta:
    +        model = WeeklyLesson
    +        fields = "__all__"
    +    def clean(self) -> dict[str, Any]
    +```
    +- `clean()`: `cleaned = super().clean()`; if 
    …[23,550 more characters truncated]
  ── Thought for 8s
    I'm dropping the unprofessional "Wait" aside and the stray "SchedulesConfig" typo line. I'm also re-checking that the seed has no conflicts and that the changes are valid: on Friday, slot 1 is room 114 for ЭД, slot 2 is room 205 for ЦД, and slot 3 is room 212 for ЭД, which holds up. Now I'm moving on to change 4, lesson 18 for the Friday week.

    Next I'm checking the remaining changes against the schedule for conflicts. Change 3 moves lesson 8 to Thursday slot 5 in room 205, which is free, and change 5 puts lesson 13 in room 402 with no other Thursday slot-3 lessons. Change 6 moves lesson 7 into room 114 on Tuesday slot 2, which doesn't clash with lesson 6 in room 101. The date-range and rerun tests also look consistent with the valid-from logic.

    I'm checking the query count next: the prefetch on the changes list means "at most 4" is the right bound, not exactly 4, since the prefetch is skipped when there are no changes. The template lookups for groups and the moved-in lesson's discipline and teacher data should all be covered by the existing select_related and prefetch calls, and the student profile lookup adds a fixed cost either way. Then I'll make the edits.

── Ran 1 command ───────────────────────────────────────────
  ── Ran python3 - <<'EOF' p="docs/tasks/TASK-003.md" s=open(p).read() s=s.replace("\nWait — rows 14 and 15 have the same key fields except discipline? No: row 14 is ТМО, row 15 is Английский язык; keys differ. Row 2 and row 13/15 differ by weekday/slot. All keys unique.\n","\nAll 18 keys are unique; the table has no group, room or slot conflicts (checked by `test_seeded_schedule_has_no_conflicts`).\n") s=s.replace("- `SchedulesConfig`: class name `ScheduleConfig`,","- App config class `ScheduleConfig`:") s=s.replace("- Query budget: exactly 4 queries (lessons, lessons' groups, changes, changes' lessons' groups), independent of data size.","- Query budget: at most 4 queries (lessons, lessons' groups, changes, changes' lessons' groups; prefetch queries are skipped when a list is empty), independent of data size.") open(p,"w").write(s) EOF grep -n "Wait\|SchedulesConfig\|exactly 4" docs/tasks/TASK-003.md; echo done (1s)
    $ python3 - <<'EOF'
  p="docs/tasks/TASK-003.md"
  s=open(p).read()
  s=s.replace("\nWait — rows 14 and 15 have the same key fields except discipline? No: row 14 is ТМО, row 15 is Английский язык; keys differ. Row 2 and row 13/15 differ by weekday/slot. All keys unique.\n","\nAll 18 keys are unique; the table has no group, room or slot conflicts (checked by `test_seeded_schedule_has_no_conflicts`).\n")
  s=s.replace("- `SchedulesConfig`: class name `ScheduleConfig`,","- App config class `ScheduleConfig`:")
  s=s.replace("- Query budget: exactly 4 queries (lessons, lessons' groups, changes, changes' lessons' groups), independent of data size.","- Query budget: at most 4 queries (lessons, lessons' groups, changes, changes' lessons' groups; prefetch queries are skipped when a list is empty), independent of data size.")
  open(p,"w").write(s)
  EOF
  grep -n "Wait\|SchedulesConfig\|exactly 4" docs/tasks/TASK-003.md; echo done
    done
  ── Thought for 988ms
    Checking that the change I made holds up, mostly the Django timezone mocking and how the StrEnum value behaves in the template's class attribute.

    Checking the StrEnum string comparison and the date format for the Russian weekday name, both look fine. Sending it to the coder next.

── Ran bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-003] Planner -> Coder: TASK Spec: docs/tasks/TASK-003.md (approved by the Team lead). Summary: - `university` gains Room/Teacher/Discipline; new app `schedule` with WeeklyLesson (weekly template with date range, M2M groups) and LessonChange (one change per occurrence: cancelled/moved/room_changed/teacher_replaced). Occurrences are computed on the fly, so any date renders without reseeding. Time slots are a code constant. - Read side in `schedule/services.py` (`occurrences_between` is the single computation, max 4 queries). Business rules in `schedule/validation.py`; the only code write path is `schedule/mutations.py`. Admin forms use `fields="__all__"`; WeeklyLesson group overlap is checked in the admin form and in `save_weekly_lesson` (M2M), LessonChange rules in `LessonChange.clean()`. - Views: student today/week (no IDs in URLs, `isodate` converter), staff group list/week scoped by new `accounts.selectors.groups_visible_to` (404 for other faculty). Use `timezone.localtime()/localdate()` only; tests mock `django.utils.timezone.now`. - `seed_demo` also calls `seed_schedule_demo(timezone.localdate())` in one transaction; exact demo tables and change dates are in 6.9. - Follow section 8 order and section 9 verification; full test list in section 7. Do not delete db.sqlite3 or migrations. Do not commit. Questions -> me. EOF
  $ bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
[TASK-003] Planner -> Coder: TASK
Spec: docs/tasks/TASK-003.md (approved by the Team lead).
Summary:
- `university` gains Room/Teacher/Discipline; new app `schedule` with WeeklyLesson (weekly template with date range, M2M groups) and LessonChange (one change per occurrence: cancelled/moved/room_changed/teacher_replaced). Occurrences are computed on the fly, so any date renders without reseeding. Time slots are a code constant.
- Read side in `schedule/services.py` (`occurrences_between` is the single computation, max 4 queries). Business rules in `schedule/validation.py`; the only code write path is `schedule/mutations.py`. Admin forms use `fields="__all__"`; WeeklyLesson group overlap is checked in the admin form and in `save_weekly_lesson` (M2M), LessonChange rules in `LessonChange.clean()`.
- Views: student today/week (no IDs in URLs, `isodate` converter), staff group list/week scoped by new `accounts.selectors.groups_visible_to` (404 for other faculty). Use `timezone.localtime()/localdate()` only; tests mock `django.utils.timezone.now`.
- `seed_demo` also calls `seed_schedule_demo(timezone.localdate())` in one transaction; exact demo tables and change dates are in 6.9.
- Follow section 8 order and section 9 verification; full test list in section 7. Do not delete db.sqlite3 or migrations. Do not commit. Questions -> me.
EOF
  Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Спецификация TASK-003 готова: [docs/tasks/TASK-003.md](docs/tasks/TASK-003.md). Я передал её кодеру. Код ещё не написан, поэтому проверок пока не было. Я сверил только даты для тестов: 16.11.2026 — понедельник.

Основные решения:
- **Где хранятся данные.**
  - Аудитории, преподаватели и дисциплины лежат в `university`. Они понадобятся карте и оценкам и без расписания.
  - Само расписание вынесено в новую часть проекта `schedule`.
  - Аудитория получает постоянный код вида `room-308`. Его можно использовать как идентификатор элемента на будущей SVG-карте.
- **Как устроено расписание.** Есть шаблон недели: день, номер пары, группы, период действия. Отдельно хранятся изменения конкретного занятия в конкретную дату. Занятия на нужные даты система вычисляет при каждом запросе. Поэтому расписание открывается на любую дату без повторного запуска `seed_demo`, и жюри сможет смотреть его до 28.11 и позже.
- **Время пар задано в коде, а не в базе.** Звонки фиксированы. Поэтому пересечение двух занятий — это просто совпадение даты и номера пары.
- **Изменения.** Отмена, перенос, замена аудитории и замена преподавателя. На одно занятие в одну дату — одно изменение. На странице видны старое и новое значение (старое зачёркнуто) и причина.
- **Проверка пересечений.** Пересечения по группе и аудитории проверяются в отдельном слое, а не только в формах админки. Так я учёл замечание ревьюера к TASK-002. Записывать занятия и изменения в коде можно только через этот слой.
- **Страницы.** Студент видит «Сегодня» с отметками «Сейчас» и «Следующая» и неделю с переходом вперёд и назад. В адресах студента нет номеров групп и пользователей. Сотрудник видит группы только своего факультета, для группы чужого факультета получает 404.
- **Демо-данные.**
  - 7 аудиторий на 4 этажах, 6 преподавателей, 6 дисциплин.
  - 18 занятий в неделю для двух групп, философия — общая лекция для обеих.
  - 8 изменений, по 2 каждого вида, на текущую и следующую неделю от даты запуска.
  - Повторный запуск `seed_demo` создаёт эти изменения заново. Это будет записано в README.
- **Скорость.** Расписание недели загружается не больше чем за 4 запроса к базе. Тест проверяет, что их число не растёт вместе с данными.

От вас сейчас ничего не нужно.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_ng6cbgatm6]

[TASK-003] Coder -> Planner: QUESTION

Spec: docs/tasks/TASK-003.md. Section 4.4 and 6.5 require the schedule admin form to use `fields = "__all__"` (WeeklyLessonAdminForm). However the project's ruff config (pyproject.toml, `select = [..., "DJ", ...]`, `ignore = []`) enables rule DJ007 ("Do not use `__all__` with ModelForm, use `fields` instead"), so `ruff check .` (required by section 9) fails on schedule/forms.py:12 with DJ007.

Per the team protocol I do not add per-file-ignores myself. Two possible resolutions, please pick one:

1. Keep `fields = "__all__"` and add `"schedule/forms.py" = ["DJ007"]` to `[tool.ruff.lint.per-file-ignores]` in pyproject.toml (you author the ignore).
2. Replace `fields = "__all__"` with an explicit fields list: `fields = ["weekday", "slot", "discipline", "lesson_type", "teacher", "room", "groups", "valid_from", "valid_until"]` (behaviorally identical, no ignore needed).

Everything else is implemented and passing; only this blocks a clean `ruff check .`.

── Ran 1 command ───────────────────────────────────────────
  ── Thought for 7ms
    I'm going with option 2, since the explicit field list also covers the requirement that the form includes all fields. LessonChangeAdmin doesn't use a form, so it needs no change. Next I'll update the spec and write the answer.
  ── Ran python3 - <<'EOF' p="docs/tasks/TASK-003.md" s=open(p).read() old='''    class Meta:         model = WeeklyLesson         fields = "__all__"''' new='''    class Meta:         model = WeeklyLesson         fields = ["weekday", "slot", "discipline", "lesson_type", "teacher", "room", "groups", "valid_from", "valid_until"]''' assert old in s; s=s.replace(old,new) old2='Admin forms for schedule models use `fields = "__all__"`.' assert old2 in s s=s.replace(old2,'Admin forms for schedule models include every editable model field (explicit list in `WeeklyLessonAdminForm`, because ruff DJ007 forbids `"__all__"`; `LessonChangeAdmin` does not restrict `fields`).') s=s.rstrip("\n")+''' --- ## Clarifications - **Q1 (Coder, DJ007)**: `WeeklyLessonAdminForm.Meta.fields` is the explicit list of all 9 editable fields (see 6.5), not `"__all__"`. No ruff ignores. If a field is added to `WeeklyLesson` later, it must be added to this list. ''' open(p,"w").write(s) EOF bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-003] Planner -> Coder: ANSWER Option 2. Use the explicit list `fields = ["weekday", "slot", "discipline", "lesson_type", "teacher", "room", "groups", "valid_from", "valid_until"]` in WeeklyLessonAdminForm. Do not add any ruff ignore. Spec updated: docs/tasks/TASK-003.md sections 4.4, 6.5 and "Clarifications" Q1. EOF (2s)
    $ python3 - <<'EOF'
  p="docs/tasks/TASK-003.md"
  s=open(p).read()
  old='''    class Meta:
          model = WeeklyLesson
          fields = "__all__"'''
  new='''    class Meta:
          model = WeeklyLesson
          fields = ["weekday", "slot", "discipline", "lesson_type", "teacher", "room", "groups", "valid_from", "valid_until"]'''
  assert old in s; s=s.replace(old,new)
  old2='Admin forms for schedule models use `fields = "__all__"`.'
  assert old2 in s
  s=s.replace(old2,'Admin forms for schedule models include every editable model field (explicit list in `WeeklyLessonAdminForm`, because ruff DJ007 forbids `"__all__"`; `LessonChangeAdmin` does not restrict `fields`).')
  s=s.rstrip("\n")+'''

  ---

  ## Clarifications

  - **Q1 (Coder, DJ007)**: `WeeklyLessonAdminForm.Meta.fields` is the explicit list of all 9 editable fields (see 6.5), not `"__all__"`. No ruff ignores. If a field is added to `WeeklyLesson` later, it must be added to this list.
  '''
  open(p,"w").write(s)
  EOF
  bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
  [TASK-003] Planner -> Coder: ANSWER
  Option 2. Use the explicit list `fields = ["weekday", "slot", "discipline", "lesson_type", "teacher", "room", "groups", "valid_from", "valid_until"]` in WeeklyLessonAdminForm. Do not add any ruff ignore. Spec updated: docs/tasks/TASK-003.md sections 4.4, 6.5 and "Clarifications" Q1.
  EOF
    Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Я ответил на вопрос кодера по TASK-003 и поправил спецификацию.

Кодер спросил о противоречии: спецификация требовала у формы админки для занятий `fields = "__all__"`, а настройки проверки кода ruff запрещают такую запись (правило DJ007).

Я выбрал явный список из всех 9 полей занятия, без исключений в ruff. Работает форма так же, все поля по-прежнему в ней. Правило проверки кода не ослаблено.

В [docs/tasks/TASK-003.md](docs/tasks/TASK-003.md) я изменил разделы 4.4 и 6.5 и добавил раздел «Clarifications». Там записано: если у занятия появится новое поле, его нужно добавить и в этот список.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-004] Team lead -> Planner: TASK
Approved by the user. Write the spec `docs/tasks/TASK-004.md` and hand it to the Coder.

## Context
Tech-debt task collected from the TASK-001..003 reviews (see `plan.md`, section "Технический долг"). No new features. Keep every fix minimal and covered by a regression test. Reuse existing services and patterns; validation at model/service level, never only in admin forms.

## Items
1. Login brute-force protection.
   - Limit failed login attempts per (username, client IP) combination, e.g. 5 failures -> 15-minute lockout (values as settings with env overrides). Lockout by username alone is NOT allowed: anyone could then lock the jury out of the demo accounts.
   - The error message must not reveal whether the username exists. A successful login resets the counter.
   - Storage must work with several gunicorn workers in production (no per-process memory). One dependency is allowed if justified (e.g. django-axes); otherwise a DB-backed implementation. Client IP behind nginx: trust X-Forwarded-For / X-Real-IP only via an explicit setting (do not trust it by default).
   - Admin login must be protected the same way.
2. `seed_demo` record-number collision (`accounts/demo.py:184`): if a demo student's record number is already used by a non-demo student, fail with a clear CommandError (no raw IntegrityError, nothing partially written).
3. Invalid HTML in `accounts/templates/accounts/student_list.html:12` (`<p>` inside `<ul>`): fix markup; keep the empty state.
4. Role/profile consistency: changing a user's role while a profile of the other role is attached must be rejected with a validation error (model/service level, shown as an admin form error, never 500). Also reject attaching a profile that does not match the role (already partly done in TASK-002 - verify and extend).
5. `seed_demo` must touch only its own schedule data. Mark demo-created schedule objects explicitly (e.g. a demo marker field or registry) instead of matching by (discipline, lesson type, weekday, slot); an admin-created lesson with the same key must survive re-seeding. Provide a data migration or seed logic for already existing demo rows.
6. Concurrency in schedule mutations (`schedule/mutations.py`): validation + write are in `transaction.atomic()` but two concurrent saves can still both pass overlap validation. Serialize conflicting writes, e.g. `select_for_update()` on the affected room and study groups (or another justified locking scheme) before validating. Must be correct on PostgreSQL; document that SQLite serializes writes anyway.
7. Re-validation: when a weekly lesson's slot, weekday, room or groups change, re-check conflicts with existing LessonChange records (moved-in changes targeting the same slot/room/groups, and the lesson's own changes). Reject with a clear error.

## Tests (must exist)
- Lockout after N failures for (username, IP); another IP with the same username is not locked; success resets; message does not reveal user existence; admin login protected; X-Forwarded-For ignored unless enabled.
- Each of items 2, 4, 5, 7 has a regression test reproducing the original problem.
- Item 6: a test that the locking query is issued (e.g. inspect captured SQL for `FOR UPDATE` on PostgreSQL or assert the locking helper is called); a real concurrency test is optional.

## Out of scope
New features, grades (next task), visual theme. Manual 360 px check (the Team lead does it separately).

## Verification
All existing verification commands pass (check, deploy check, makemigrations --check, test, ruff, CI YAML), `seed_demo` twice without errors.

── Ran 3 commands, explored 2 files, created 1 file ────────
  ── Thought for 6ms
    I'm reviewing the current state of the project: the git log, the tech debt in plan.md, and the relevant files across accounts, schedule, validation, and the student list template, plus the settings and tests. I'm also checking whether the TASK-001 and TASK-003 specs have been amended.
  ── Ran git log --oneline | head -8 && git status --short && sed -n '/Технический долг/,/## 7/p' plan.md && grep -n "^## " docs/tasks/TASK-001.md docs/tasks/TASK-003.md | tail -15 && cat accounts/models.py accounts/admin.py && cat accounts/templates/accounts/student_list.html (2s)
    $ git log --oneline | head -8 && git status --short && sed -n '/Технический долг/,/## 7/p' plan.md && grep -n "^## " docs/tasks/TASK-001.md docs/tasks/TASK-003.md | tail -15 && cat accounts/models.py accounts/admin.py && cat accounts/templates/accounts/student_list.html
    a240f23 TASK-003: schedule
    001c455 TASK-002: users, roles, login and access control
    04b7f0c TASK-001: production settings tests (amendment 1)
    42f5465 Team protocol: reviewer test proposals
    2492a70 TASK-001: Django skeleton and CI
    bd9d1c1 Team protocol: lead-only commits, changelog, agreed project plan
    15e0748 Initial commit: agent team configuration
     M plan.md
    | TASK-004 | Технический долг (пункты 1–4, 6–8 раздела 6a) | У Планировщика |
    | TASK-005 | Успеваемость и посещения | Ждёт одобрения, текст готов |

    ## 6a. Технический долг (из ревью)
    - Ограничение попыток входа (защита от подбора пароля).
    - `seed_demo` падает с IntegrityError, если номер зачётки демо-студента уже занят другим студентом (`accounts/demo.py:184`).
    - `<p>` внутри `<ul>` в `accounts/templates/accounts/student_list.html:12`.
    - При смене роли пользователя в админке старый профиль остаётся привязанным. Доступ безопасен, но данные несогласованы.
    - Ручная проверка всех страниц на ширине 360 px.
    - `seed_demo` ищет демо-занятия по ключу (предмет, тип, день, пара). Занятие с тем же ключом, созданное в админке, будет перезаписано.
    - Нет блокировки при одновременном редактировании расписания в админке.
    - При смене аудитории или пары у регулярного занятия не перепроверяются уже существующие переносы на это время.

    ## 7. Открытые вопросы
    docs/tasks/TASK-001.md:504:## 7. Implementation order
    docs/tasks/TASK-001.md:518:## 8. Verification
    docs/tasks/TASK-001.md:541:## 9. Risks
    docs/tasks/TASK-001.md:552:## Amendment 1: production settings tests
    docs/tasks/TASK-003.md:8:## 1. Goal
    docs/tasks/TASK-003.md:12:## 2. Acceptance criteria
    docs/tasks/TASK-003.md:25:## 3. Out of scope
    docs/tasks/TASK-003.md:31:## 4. Design decisions
    docs/tasks/TASK-003.md:62:## 5. Architecture
    docs/tasks/TASK-003.md:294:## 6. Functions
    docs/tasks/TASK-003.md:679:## 7. Tests (complete list)
    docs/tasks/TASK-003.md:733:## 8. Implementation order
    docs/tasks/TASK-003.md:745:## 9. Verification
    docs/tasks/TASK-003.md:765:## 10. Risks
    docs/tasks/TASK-003.md:776:## Clarifications
    from django.conf import settings
    from django.contrib.auth.models import AbstractUser
    from django.db import models


    class User(AbstractUser):
        class Role(models.TextChoices):
            STUDENT = "student", "Студент"
            STAFF = "staff", "Сотрудник деканата"

        role = models.CharField("роль", max_length=16, choices=Role.choices, blank=True, default="")

        class Meta:
            verbose_name = "пользователь"
            verbose_name_plural = "пользователи"
            constraints = [
                models.CheckConstraint(
                    condition=(models.Q(is_superuser=False) & models.Q(role__in=["student", "staff"]))
                    | (models.Q(is_superuser=True) & models.Q(role="")),
                    name="accounts_user_role_matches_superuser",
                    violation_error_message=(
                        "Обычный пользователь должен иметь роль; у суперпользователя роли нет."
                    ),
                ),
                models.CheckConstraint(
                    condition=models.Q(is_staff=False) | models.Q(is_superuser=True),
                    name="accounts_user_admin_access_superuser_only",
                    violation_error_message="Доступ к админке есть только у суперпользователя.",
                ),
            ]

        @property
        def is_student(self) -> bool:
            return self.role == self.Role.STUDENT

        @property
        def is_deanery_staff(self) -> bool:
            return self.role == self.Role.STAFF

        def __str__(self) -> str:
            return self.username


    class StudentProfile(models.Model):
        user = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name="student_profile",
            limit_choices_to={"role": "student"},
            verbose_name="пользователь",
        )
        last_name = models.CharField("фамилия", max_length=100)
        first_name = models.CharField("имя", max_length=100)
        middle_name = models.CharField("отчество", max_length=100, blank=True, default="")
        group = models.ForeignKey(
            "university.StudyGroup",
            on_delete=models.PROTECT,
            related_name="students",
            verbose_name="группа",
        )
        record_number = models.CharField("номер зачётной книжки", max_length=20, unique=True)

        class Meta:
            ordering = ["last_name", "first_name"]
            verbose_name = "профиль студента"
            verbose_name_plural = "профили студентов"

        def __str__(self) -> str:
            return self.full_name

        @property
        def full_name(self) -> str:
            return " ".join(
                part for part in (self.last_name, self.first_name, self.middle_name) if part
            )

        @property
        def program(self):
            return self.group.program

        @property
        def faculty(self):
            return self.group.program.faculty

        @property
        def course(self) -> int:
            return self.group.course


    class StaffProfile(models.Model):
        user = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name="staff_profile",
            limit_choices_to={"role": "staff"},
            verbose_name="пользователь",
        )
        last_name = models.CharField("фамилия", max_length=100)
        first_name = models.CharField("имя", max_length=100)
        middle_name = models.CharField("отчество", max_length=100, blank=True, default="")
        position = models.CharField("должность", max_length=150)
        faculty = models.ForeignKey(
            "university.Faculty",
            on_delete=models.PROTECT,
            related_name="staff_members",
            verbose_name="факультет",
        )

        class Meta:
            ordering = ["last_name", "first_name"]
            verbose_name = "профиль сотрудника"
            verbose_name_plural = "профили сотрудников"

        def __str__(self) -> str:
            return self.full_name

        @property
        def full_name(self) -> str:
            return " ".join(
                part for part in (self.last_name, self.first_name, self.middle_name) if part
            )
    from django.contrib import admin
    from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
    from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

    from .models import StaffProfile, StudentProfile, User


    class UserCreationAdminForm(AdminUserCreationForm):
        class Meta(AdminUserCreationForm.Meta):
            model = User
            fields = ("username", "role")

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["role"].required = True


    class UserChangeAdminForm(UserChangeForm):
        class Meta(UserChangeForm.Meta):
            model = User


    @admin.register(User)
    class UserAdmin(BaseUserAdmin):
        form = UserChangeAdminForm
        add_form = UserCreationAdminForm
        list_display = ("username", "role", "is_active", "is_superuser", "last_login")
        list_filter = ("role", "is_active", "is_superuser")
        fieldsets = BaseUserAdmin.fieldsets + (("Роль", {"fields": ("role",)}),)
        add_fieldsets = BaseUserAdmin.add_fieldsets + (("Роль", {"fields": ("role",)}),)


    @admin.register(StudentProfile)
    class StudentProfileAdmin(admin.ModelAdmin):
        list_display = ("full_name", "group", "record_number", "user")
        list_filter = ("group__program__faculty", "group")
        search_fields = ("last_name", "first_name", "record_number", "user__username")
        list_select_related = ("group", "user")


    @admin.register(StaffProfile)
    class StaffProfileAdmin(admin.ModelAdmin):
        list_display = ("full_name", "position", "faculty", "user")
        list_filter = ("faculty",)
        search_fields = ("last_name", "first_name", "user__username")
    {% extends "base.html" %}
    {% block content %}
      <h1>Студенты факультета</h1>
      <p>{{ faculty.name }}</p>
      <ul class="student-list">
        {% for student in students %}
          <li>
            <a href="{% url 'accounts:staff_student_detail' student.pk %}">{{ student.full_name }}</a>
            · {{ student.group.name }}, {{ student.course }} курс
          </li>
        {% empty %}
          <p>Студентов нет.</p>
        {% endfor %}
      </ul>
    {% endblock %}
  ── Read schedule/mutations.py
  ── Thought for 3m 31s
    I'm weighing two options for login throttling: django-axes, which is mature and covers admin login through its authentication backend and middleware, or a custom DB-backed approach. I'm leaning toward django-axes and looking at its lockout settings, the failure limit, the cool-off time, and resetting on success.

    I'm checking the axes details next: IP detection through the proxy settings, the 429 lockout response, and version compatibility with Django 5.2. The concern I'm noting is that axes adds its own models and migrations, plus middleware and backend ordering. The bigger issue is that `client.login` calls authenticate without a request, which would make axes raise an error in existing tests.

    I'm settling on a DB-backed throttle rather than django-axes, since a small custom form hook avoids the dependency and its version constraints. The plan is a `LoginThrottle` model keyed on username and IP, wrapped around `AuthenticationForm` so the site and admin login share it, with the same generic message for existing and missing users. I'm picking it mainly because axes needs a request on every `authenticate` call, which would break `Client.login` in the existing tests.

    I'm settling the admin side too: the admin login has to be throttled the same way, so I'll set `admin.site.login_form` to a throttled subclass of the admin's authentication form, placed in `accounts/admin.py` so it loads with admin autodiscovery. There are no other login entry points to cover.

    I'm sketching the username key for the throttle model: I'll normalize it so variant spellings can't split the count, though the exact casing question matters less because wrong-case names never authenticate anyway.

    I'm settling the throttle model's fields: a normalized username key capped at 150 characters, the IP address, a failure count, the first-failure timestamp, an optional lock-until time, and a unique constraint on username and IP. I'm also setting the three limits (failure count, lockout length, and failure window) to be configurable through environment variables, with defaults of 5 failures and 900 seconds.

    I'm defining the client IP helper next, which reads the forwarded header only when the configured setting names one, validating the value as an IP and falling back to REMOTE_ADDR.

    I'm working out how the client IP gets read, taking the rightmost X-Forwarded-For entry since that's the one the proxy saw, and falling back to REMOTE_ADDR or 0.0.0.0. I'm also defining the username normalization, the lock check, and a failure-registration step that runs atomically.

    I'm looking at how the lock check fits in: the throttle counts failures in a single atomic step and locks the pair once the limit is reached. I'm also noting that concurrent first-time requests might race on creating the row, so I'll rely on the get-or-create call to handle that case.

    I'm working through the lockout rules: if the lock has expired, or the failure window has passed, the counter resets on the next failure. I'm also settling the messages, using Django's standard invalid-login text so existing and missing usernames look the same, and a separate generic message for a locked pair.

    I'm sketching the form mixin next, which will check the lock inside the form's clean step so the view never reaches authenticate for a locked pair.

    I'm writing the form clean step: it checks for a lock before authenticating, and counts a failure whenever the parent form raises an invalid-login or inactive error.

    I'm writing the form mixin's clean step, which counts a failure on any validation error from the parent form. I'm also handling a missing request by falling back to a placeholder IP, and I'm setting up the two throttled form classes for the site and admin logins.

    I'm finishing the admin side by pointing the admin login at the throttled admin form in `accounts/admin.py`, and registering the throttle model as read-only so an operator can unlock an account by deleting its row.

    I'm mapping the client IP header setting to the matching request meta key, accepting either header name in any letter case and rejecting anything else with a configuration error. I'm also noting the three new environment variables for the failure limit, lockout length, and proxy header, plus the README entry for them, and I'll treat the failure window as part of the same lockout settings.

    I'm now looking at the record number collision case for the demo seeding: before writing each student, I'll check whether another student's profile already holds that record number, and if so stop with an error naming the conflict. I'm planning to run that check for all student seeds up front, before any writes happen.

    I'm checking the seed for a record-number clash, making sure a conflicting non-demo student blocks the run before anything is written, and that the test covers it. I'm also confirming that an existing `student1` with that same number is fine, and adding an empty-state line for the student list.

    I'm adding a check that the seeded students' record numbers aren't already taken, then I'm moving on to making sure a user's role and profile stay consistent: a user can't switch role while a student or staff profile still exists for them.

    I'm checking whether the model's clean step can safely report a role error. If the form doesn't include the role field, a ValidationError keyed to "role" might not attach to anything, so I need to see how Django routes errors for fields outside the form.

    I'm checking whether assigning a ValidationError to the "role" key is safe when that field isn't on the form, since Django may reject errors keyed to fields outside the form.

    I'm checking how Django routes a model-level ValidationError when its key isn't a field on the form, since the role check would key its error to "role" and that might not attach anywhere.

    I'm deciding whether a non-field error is safer than keying the role error to "role", since a model-level error on a field outside the form can raise a ValueError, so I'm leaning toward the non-field error.

    I'm settling on the role check: the User model's clean step will reject a role change while a student or staff profile still exists, and I'm using a non-field error so it can't crash on a form that lacks the role field.

    I'm adding explicit checks to the profile models' clean step, so a student profile can only belong to a user with the student role, and a user can't hold both a student and a staff profile.

    I'm settling the profile checks: each profile's clean step will reject a user whose role doesn't match or who already holds the other profile type, since data could be inconsistent even if the role rule normally prevents it. I'm also planning regression tests for a role change, a superuser toggle, and a staff profile attached to a student user.

    I'm writing the admin tests now, covering the role-change and superuser-toggle cases, plus a staff profile attached to a student user. For the user-change form test, I'm building the POST data from the model's current values and then altering the role.

    I'm working out how to build the admin test's POST data from the model's current values, since the date fields need to be strings and I'm not sure a plain DateTimeField will take datetime objects directly.

    I'm settling on the admin test approach: rather than hand-building a POST for the user change form, I'll get the form class from the registered ModelAdmin and check the model-level validation directly with `full_clean()`, plus a form-level check.

    I'm sketching the admin test as a client POST with an explicit data dict, including the required username and date_joined fields and leaving last_login blank.

    I'm sketching the admin test as a client POST with an explicit data dict: username, role set to staff, is_active, the split date_joined fields, and the name and email fields left blank. I expect a 200 response with the form redisplayed and an error shown, and the role in the database unchanged. If the admin needs more fields to get past basic validation, I'll add them and still assert the role error specifically.

    I'm deciding where to put the demo marker: a nullable unique field on the lesson model would trip the lint rule against null on string fields, so I'm considering a separate registry model with a one-to-one link to the lesson instead.

    I'm settling on a conditional unique constraint over a plain marker field, since it avoids nullable string fields, and I'm making the marker non-editable so it stays out of the admin forms. I'm also wondering whether lesson changes need their own marker, so the seed only deletes its own changes and leaves admin-made ones alone.

    I'm settling on a conditional unique constraint for the change's seed marker too, so reseeding can remove only the demo-created changes, and I'm considering what happens if an admin-made change clashes with one or sits on a date the demo lesson's new range invalidates.

    I'm switching the rooms, teachers, and disciplines to get-or-create, so seeding won't overwrite reference data an admin already changed, like a room's floor.

    I'm keeping the reference data as it is rather than switching rooms, teachers, and disciplines to get-or-create, since a room with a clashing number could raise a raw IntegrityError and that's outside what the lesson question asks. I'll note it as a risk, and I'm also thinking about how existing demo rows without a seed key get handled in the migration.

    I'm weighing a data migration for the 18 existing demo lessons: it would match each legacy row on its old key plus its group set, teacher, and room, with the seed data copied as literal values into the migration.

    I'm deciding how to handle the 18 existing demo lessons: a data migration that matches each legacy row on its old key, group set, teacher, and room, using the seed values copied in as literals. Changes on those lessons whose reason and kind match a seed entry would get their keys marked the same way. I'm also noting that a plain reset of the local dev DB would be simpler, but the strict-match migration is what's needed here, so it becomes a noop-reverse RunPython in a separate migration after the schema change.

    I'm settling on a data migration split into two files: a schema change adding the seed key, then a RunPython step that marks existing demo rows. For testing, I'll move the matching logic into a function the migration calls, and load the migration module with importlib so the test can run it against the real app registry.

    I'm planning a test with legacy demo rows and an admin-created duplicate that differs by room, expecting only the exact match to be marked. I'm also planning a regression check that an admin lesson sharing a demo lesson's slot but living in a separate period survives reseeding, along with its changes.

    I'm locking the room and the affected study groups inside the same transaction before validating, always in pk order so concurrent saves can't deadlock. Once the locks are held, the validation queries should see the other writer's committed rows, since each statement in PostgreSQL's READ COMMITTED gets a fresh snapshot.

    I'm locking the lesson's room and groups, including the old ones, and expecting the change writer to take the same locks so the two stay consistent. For a lesson change, I'm locking the lesson's room and its groups, plus the target room when it's a move, always in sorted pk order, before running `full_clean` and saving. I'm planning a shared helper that takes the room and group ids and locks them with `select_for_update` in that order.

    I'm checking whether the shared lock helper covers every conflict: two lessons conflict only if they share a room or a group, and each one locks both, so any overlapping pair gets serialized. I'm also noting that calling the helper outside a transaction should fail loudly, which is the guard I want. Next I'm turning to the admin path, where saves go through the admin's save_model.

    I'm checking the admin path, where the form's clean step runs outside the lock, so there's still a race. I'm considering routing admin saves through the same service with the lock held, though a validation error at that point would surface as a 500 that I'd need to handle.

    I'm checking whether the admin's form clean and save both run inside one transaction, since that decides whether taking the locks in save_related closes the race. If they do, the request is atomic end to end and the locks can cover the validation that matters.

    I'm looking at whether the admin form's validation can run inside a transaction, since the admin wraps its whole request in one. If it can, I could take the room and group locks in the form's clean step, so they stay held until the admin commits. The open question is what happens when the helper runs outside a transaction, as in a plain test.

    I'm settling the admin side: form.clean will take the room and group locks when there's an open transaction, since the admin wraps the whole request in one, so the validation holds until commit. The service path will lock and validate on its own too, which keeps both entry points consistent.

    I'm putting the locking inside the validation functions themselves: `validate_weekly_lesson` and `change_conflicts`, each taking the lock when an atomic block is open. That way the service path, the admin form, and the model clean all lock without extra wiring. I'm also planning a test that captures the queries from `save_weekly_lesson` and checks that a `FOR UPDATE` lock is issued.

    I'm working out how the test should check the locking: on SQLite the `FOR UPDATE` clause isn't emitted, so I'll only assert on the emitted SQL when the backend supports it, and otherwise check the lock queries directly.

    I'm checking whether the lock helper actually refuses to run outside a transaction, and it turns out that check only fires on backends that support `select_for_update`, so SQLite won't raise. I'm deciding whether the helper should run only inside an atomic block at all, though the tests are already wrapped in one, so it probably doesn't matter in practice.

    I'm making the lock helper a no-op outside an atomic block, so a bare `full_clean` call on a change can't raise on PostgreSQL. I'm also noting that SQLite ignores `select_for_update` and serializes writes at the database level instead. Next I'm turning to re-validation: when a weekly lesson's slot, weekday, room, or groups change, I need to recheck existing change records that target that slot on the affected dates.

    I'm now working through the cases where changes to a weekly lesson could invalidate existing change records, starting with other lessons' moved-in changes that target the new slot and could clash on room or groups.

    I'm now checking the occurrence-level case: a lesson's new room can clash with another lesson's ROOM_CHANGED change that moves that lesson onto the same room on a specific date, even when the templates themselves look fine. I'm planning a validation step that computes the affected occurrences and checks them against those changes.

    I'm working out the occurrence-level check for the lesson's new room: other lessons' moved-in changes that land on the same weekday and slot within the date range, plus ROOM_CHANGED changes on lessons in that slot whose changed room could now collide.

    I'm working through the remaining occurrence-level cases: other lessons' moved-in changes that land on this slot and could clash on room or groups, and whether this lesson's own occurrence on that date is still happening.

    I'm now working out the occurrence-level check: for a proposed lesson state, the dates to examine are those touched by its own changes plus those touched by other lessons' moved-in and room-changed entries.

    I'm weighing whether to run the occurrence-level check after saving inside the transaction, so the DB state is what gets validated and a failure rolls back. That fits the service path well, but the admin form's clean runs before anything is saved, so it would need a different place to hook in.

    I'm working out the admin-side alternative: routing the save through the service or hooking into the admin's changeform view, though both get complicated. I'm also considering a pre-save simulation, passing an override draft into the occurrence lookup, but building an unsaved copy of the lesson with its groups would be messy. A targeted function with explicit rules for each conflict source looks more practical, so I'm starting to define its signature.

    I'm drafting the first step of the conflict check: pulling other lessons' moved-in changes that land on this slot and date range, and then comparing their effective room against the proposed room.

    I'm now writing the room-change check for other lessons: a ROOM_CHANGED entry on the same weekday and slot that moves its lesson onto this room within the date range, skipping this lesson's own changes on those dates.

    I'm now writing the room-change check for the lesson's own changes: a ROOM_CHANGED entry whose new room matches the lesson's new room gets flagged. I'm also looking at whether a room change at that date and slot collides with other lessons already in that room at the same weekday and slot.

    I'm now checking the room-change case for the lesson's own changes: whether a ROOM_CHANGED entry at the original date and new slot would collide with another occurrence that uses the new room. I'm also looking at how a moved occurrence should be checked against other lessons at the target date and slot, using the new room and groups.

    I'm now working through the own-occurrence case for moved changes: the lesson's stale DB occurrences should be excluded, and the new regular slot checked against the target date.

    I'm sketching a helper that finds the occupants of a given day and slot, excluding the lesson being changed, and I'm considering a single occurrence query over the whole valid range to check the other lessons' moved-in changes against the proposed room and groups.

    I'm sketching the conflict check as a single simulation: I'll build the schedule over the proposed range, apply this lesson's own changes as they would stand after the save, and then check each affected occurrence for room or group clashes.

    I'm now writing out the conflict check as a numbered procedure: build the proposed occurrences, check other lessons' items at those date and slot pairs for room or group overlap, flag any two of the lesson's own occurrences that collide, and reject a room change that matches the new room.

    I'm checking whether the simulation's range covers enough dates, since a year-long range could mean a lot of lookups. I'm estimating that the cost stays manageable for the admin path, so I'll keep the template-level checks as they are and run the simulation only when they pass.

    I'm now planning to run the simulation at the end of validate_weekly_lesson, only when the template-level checks pass, so the function signature can stay the same.

    I'm finishing the message wording for conflicts, capping the list at ten entries with a count for the rest, and planning regression tests for the slot-change case where a moved-in lesson clashes with an edited lesson.

    I'm sketching regression test cases for the slot-change and room-change conflicts: one where another lesson's moved-in occurrence clashes after an edit to the slot, one where another lesson's room change collides with a new room, and one where the lesson's own moved occurrence ends up in a room that another lesson already uses.

    I'm reviewing the remaining regression cases: changing a lesson's groups to include another group that already has a moved-in occurrence, and confirming that a cancelled occurrence frees its slot so the edit is allowed. I'm also noting that the admin form path should reject the same conflict as the service path, and that the lock helper inside validate_weekly_lesson still needs to be worked out.

    I'm working out the locking scope for this path: the room and groups get locked, which should be enough since any conflict found shares one of them with the lesson. I'm also planning to document that validation after the lock sees the latest committed data under READ COMMITTED, and I'm moving on to the seed script in accounts/demo.py, where lessons and changes get tagged with a seed key.

    I'm adding a `seed_key` marker to the demo lessons and changes, so the seed can tell its own data apart and clear only that. I'll also show the marker read-only in both admins, so an operator can see which records came from the demo and would be overwritten on reseed.

    I'm drafting a data migration that matches each legacy demo lesson by its discipline, type, weekday, slot, teacher, room and group set, and tags it with a seed key when exactly one candidate fits. For the demo changes, I'm planning to tag them by their parent lesson's key, kind and reason, and I'm checking whether the candidate count could ever be more than one.

    I'm working through the data migration for the seed markers: after it runs, any legacy demo changes that weren't tagged would stay on the demo lessons and could clash with the new seeded changes. I'm leaning toward having the migration tag them too, and I'm planning the lesson keys and change keys to match the demo spec.

    I'm adding the settings for login failure limit and lockout duration, with the client IP header resolved through the env helper. I'm also planning a check that rejects non-positive values with ImproperlyConfigured, and then moving on to the accounts migration for the login throttle.

    I'm adding a cleanup step to the login failure path so that stale throttle rows from other keys, such as random usernames, get removed by a single query on each failure. I'm settling on the timestamp check and will set the timestamp fields explicitly so the cutoff doesn't depend on how auto_now behaves.

    I'm noting that the username gets stripped, casefolded, and capped at 150 characters to match the User model, and that the IP and username stored in the throttle table are personal data I'll keep for only a day. I'm also planning a test where varying X-Forwarded-For headers still share one lock when CLIENT_IP_HEADER is left at its empty default.

    I'm planning admin login tests that submit five failures for a superuser, then check that a correct password is still refused with a lock message. I'm also adding a test where a second IP using the same username isn't locked, and I'm noting that the lock message shouldn't reveal whether a username exists.

    I'm writing the success-reset and shared-username tests now, plus the check that the lock message is identical whether or not the username exists. I'm also noting that the existing login tests stay as they are, since `client.login()` bypasses the throttle. Next I'm turning to the `User.clean()` changes for the role-based profile checks.

    I'm writing the `User.clean()` check so that a role change is rejected while a student or staff profile still exists for that user. The student and staff profile `clean()` methods come next, and they'll require the profile's user to have the matching role.

    I'm adding the `User.clean()` check that rejects a role change when a student or staff profile still exists, and the profile `clean()` methods that require the matching role. I'm also keeping in mind that `seed_demo` already checks role conflicts, and that code calling `save()` directly skips validation, so `get_profile_for_role` remains the safe access point. I'll confirm the form's error path leaves nothing partially written.

    I'm listing the tests and their order, then the README and .env.example updates for the new login limits, the proxy header, and the demo seed key. The new throttling and form modules, the lock helper, and the generated migrations are the files still to write.

    I'm listing the remaining files to change: the schedule and accounts models and admin, the views, demo precheck, the student list template, settings, the env helper with its tests, and the README and env example updates.

    I'm mapping out the remaining files to touch: the schedule models and their `seed_key` field, validation, admin, and demo keys, plus the env example and README. For the existing demo rows I'm planning a data migration that runs after the schedule and university migrations, and I'm noting the generated migration name has to be filled in.

    I'm mapping the legacy demo lessons and changes into the migration's tuples, with each lesson keyed by discipline, type, slot, teacher, room and groups, and the changes keyed to their parent lesson. I'm now working through the first few change rows from the earlier task, the cancelled and moved entries tied to specific lessons.

    I'm now checking the remaining change rows against the TASK-003 table, with the cancelled, moved, room-change and teacher-replacement entries tied to their lessons. I still need to confirm that the seed data in schedule/demo.py matches those rows exactly.
  ── Read schedule/demo.py
  ── Thought for 4ms
    The data lines up with what I expected. I also want to check that Django's admin changeform_view runs inside a transaction, that `iso_week_day` is no longer needed given the simulation approach, and that SQLite reports `has_select_for_update` as False.
  ── Ran DEBUG=true .venv/bin/python -c " import django,os;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup() import inspect from django.contrib.admin.options import ModelAdmin print('atomic' in inspect.getsource(ModelAdmin.changeform_view)) from django.db import connection;print('sqlite has_select_for_update', connection.features.has_select_for_update) from django.contrib.auth.forms import AuthenticationForm;print(inspect.getsource(AuthenticationForm.clean)) from django.contrib.admin import site;print(site.login_form) "
    $ DEBUG=true .venv/bin/python -c "
  import django,os;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup()
  import inspect
  from django.contrib.admin.options import ModelAdmin
  print('atomic' in inspect.getsource(ModelAdmin.changeform_view))
  from django.db import connection;print('sqlite has_select_for_update', connection.features.has_select_for_update)
  from django.contrib.auth.forms import AuthenticationForm;print(inspect.getsource(AuthenticationForm.clean))
  from django.contrib.admin import site;print(site.login_form)
  "
    True
    sqlite has_select_for_update False
        @sensitive_variables()
        def clean(self):
            username = self.cleaned_data.get("username")
            password = self.cleaned_data.get("password")

            if username is not None and password:
                self.user_cache = authenticate(
                    self.request, username=username, password=password
                )
                if self.user_cache is None:
                    raise self.get_invalid_login_error()
                else:
                    self.confirm_login_allowed(self.user_cache)

            return self.cleaned_data

    None
  ── Thought for 739ms
    I'm checking whether the mixin's clean method needs the sensitive_variables decorator like AuthenticationForm's clean does. Since ours never touches the password, I'll still suggest applying a bare `@sensitive_variables()` as a precaution. Next I'll write the spec.
  ── Thought
    Проверил ключевые факты: админка сохраняет объекты в транзакции, SQLite не поддерживает `FOR UPDATE`, форма входа Django в порядке. Теперь пишу спецификацию TASK-004.
  ── Created docs/tasks/TASK-004.md +422
    --- /dev/null
    +++ b~/hackatonproject/docs/tasks/TASK-004.md
    +# TASK-004: Technical debt from TASK-001..003 reviews
    +
    +Author: Planner. Status: ready for implementation.
    +Base commit: `a240f23`. Product context: `plan.md` section 6a. Previous specs: `docs/tasks/TASK-001.md` … `TASK-003.md`.
    +
    +No new features. Every fix is minimal and has a regression test. Business rules live at model/service level; admin forms only call them.
    +
    +---
    +
    +## 1. Items and acceptance criteria
    +
    +| # | Item | Done when |
    +|---|---|---|
    +| 1 | Login brute-force protection | (username, IP) lockout after N failures for M seconds, DB-backed, site and admin login, generic messages, proxy header only via explicit setting |
    +| 2 | `seed_demo` record-number collision | clear `CommandError`, nothing written |
    +| 3 | `<p>` inside `<ul>` in student list | valid markup, empty state kept |
    +| 4 | Role/profile consistency | role change with a profile of the other role → validation error (admin form error, no 500); profile/role mismatch rejected |
    +| 5 | Demo schedule marker | demo lessons/changes marked by `seed_key`; admin data with the same old key survives re-seeding; data migration marks existing demo rows |
    +| 6 | Concurrency in schedule writes | room and group rows locked (`select_for_update`) before conflict checks, in every write path |
    +| 7 | Re-validation against existing changes | changing weekday/slot/room/groups/range of a weekly lesson re-checks all existing changes (own and others) |
    +
    +All existing verification commands pass; `seed_demo` runs twice.
    +
    +## 2. Out of scope
    +New features, grades, visual theme, manual 360 px check, CAPTCHA, email alerts, IP-only throttling, cleanup command for throttle rows (opportunistic cleanup only, see 4.3). Reference data (rooms/teachers/disciplines) keeps the current `update_or_create` behaviour in the seed.
    +
    +---
    +
    +## 2a. Files
    +
    +Create:
    +```
    +accounts/throttling.py
    +accounts/forms.py
    +accounts/migrations/0002_loginthrottle.py                 (generated)
    +accounts/tests/test_throttling.py
    +accounts/tests/test_role_consistency.py
    +schedule/locking.py
    +schedule/migrations/0002_<generated>.py                   (generated: seed_key fields + constraints)
    +schedule/migrations/0003_mark_existing_demo_rows.py       (hand-written data migration)
    +schedule/tests/test_locking.py
    +schedule/tests/test_revalidation.py
    +schedule/tests/test_demo_marker.py
    +```
    +Change:
    +```
    +config/settings.py, config/env_utils.py, core/tests/test_env_utils.py, core/tests/test_settings.py,
    +accounts/models.py, accounts/admin.py, accounts/views.py, accounts/demo.py,
    +accounts/templates/accounts/student_list.html, accounts/tests/test_seed_demo.py, accounts/tests/test_views.py,
    +schedule/models.py, schedule/validation.py, schedule/admin.py, schedule/demo.py,
    +.env.example, README.md
    +```
    +No other files. No new dependencies.
    +
    +---
    +
    +## 3. Item 1 — login brute-force protection
    +
    +### 3.1 Decision: DB-backed, no new dependency
    +- `django-axes` was considered and rejected: it requires `request` in every `authenticate()` call (breaks `Client.login()` in tests and any helper that calls `authenticate()` without a request), adds 3 tables, a middleware, an auth backend and `django-ipware`. We have exactly two entry points (site login and admin login), both `AuthenticationForm` subclasses, so one form mixin covers all.
    +- Storage: one DB table `accounts.LoginThrottle`. Works with many gunicorn workers (shared DB), row lock per key avoids lost updates.
    +- Key: `(normalized username, client IP)`. Never username alone (would let anyone lock the jury accounts), never IP alone.
    +
    +### 3.2 Settings (`config/settings.py`) and env helpers
    +
    +Add after `ADMIN_URL`:
    +```python
    +LOGIN_FAILURE_LIMIT = env.int("LOGIN_FAILURE_LIMIT", default=5)
    +LOGIN_LOCKOUT_SECONDS = env.int("LOGIN_LOCKOUT_SECONDS", default=900)
    +if LOGIN_FAILURE_LIMIT < 1 or LOGIN_LOCKOUT_SECONDS < 1:
    +    raise ImproperlyConfigured("LOGIN_FAILURE_LIMIT and LOGIN_LOCKOUT_SECONDS must be positive.")
    +CLIENT_IP_HEADER = resolve_client_ip_header(env.str("CLIENT_IP_HEADER", default=""))
    +```
    +(`from django.core.exceptions import ImproperlyConfigured`.)
    +
    +`config/env_utils.py`:
    +```python
    +def resolve_client_ip_header(raw: str) -> str
    +```
    +- Purpose: map the env value to a `request.META` key; empty = do not trust any proxy header.
    +- Algorithm: `value = raw.strip().lower()`; `""` → `""`; `"x-real-ip"` → `"HTTP_X_REAL_IP"`; `"x-forwarded-for"` → `"HTTP_X_FORWARDED_FOR"`; anything else → `ImproperlyConfigured("CLIENT_IP_HEADER must be empty, 'X-Real-IP' or 'X-Forwarded-For'.")`.
    +- Tests (`core/tests/test_env_utils.py`): `""` and `"  "` → `""`; `"X-Real-IP"` → `"HTTP_X_REAL_IP"`; `"x-forwarded-for"` → `"HTTP_X_FORWARDED_FOR"`; `"X-Client-IP"` → `ImproperlyConfigured`.
    +
    +`core/tests/test_settings.py` add `test_login_throttle_defaults`: `LOGIN_FAILURE_LIMIT == 5`, `LOGIN_LOCKOUT_SECONDS == 900`, `CLIENT_IP_HEADER == ""` (tests run without these env vars; if the developer's `.env` sets them, the test may be skipped with `skipUnless` on `os.environ`).
    +
    +`.env.example` append:
    +```
    +# Login brute-force protection: failures per (username, IP) before lockout, lockout length.
    +LOGIN_FAILURE_LIMIT=5
    +LOGIN_LOCKOUT_SECONDS=900
    +# Client IP header set by YOUR reverse proxy. Leave empty unless nginx overwrites it.
    +# Values: X-Real-IP (recommended with `proxy_set_header X-Real-IP $remote_addr;`) or X-Forwarded-For.
    +CLIENT_IP_HEADER=
    +```
    +README env table: add the three rows.
    +
    +### 3.3 Model `accounts.LoginThrottle` (in `accounts/models.py`)
    +| Field | Definition |
    +|---|---|
    +| `username_key` | `CharField("логин", max_length=150)` |
    +| `ip_address` | `GenericIPAddressField("IP-адрес")` |
    +| `failures` | `PositiveIntegerField("неудачных попыток", default=0)` |
    +| `first_failure_at` | `DateTimeField("первая неудача")` |
    +| `last_failure_at` | `DateTimeField("последняя неудача")` |
    +| `locked_until` | `DateTimeField("заблокирован до", null=True, blank=True)` |
    +- `Meta`: `constraints = [UniqueConstraint(fields=["username_key", "ip_address"], name="accounts_loginthrottle_unique_key")]`; `indexes = [Index(fields=["last_failure_at"], name="accounts_throttle_last_idx")]`; verbose `"блокировка входа"` / `"блокировки входа"`.
    +- `__str__` → `f"{self.username_key} @ {self.ip_address}"`.
    +- No `auto_now` fields (times are set explicitly from `timezone.now()` so tests can mock the clock).
    +
    +Admin (`accounts/admin.py`): `LoginThrottleAdmin` — `list_display = ("username_key", "ip_address", "failures", "locked_until", "last_failure_at")`, `search_fields = ("username_key", "ip_address")`, all fields read-only (`readonly_fields` = all fields), `has_add_permission` → `False`. Deleting a row unlocks the key.
    +
    +### 3.4 `accounts/throttling.py`
    +
    +```python
    +def normalize_username(username: str) -> str
    +```
    +`return username.strip().casefold()[:150]`. Test: `"  Student1 "` → `"student1"`.
    +
    +```python
    +def get_client_ip(request: HttpRequest | None) -> str
    +```
    +- Algorithm:
    +  1. `request is None` → `"0.0.0.0"`.
    +  2. `header = settings.CLIENT_IP_HEADER`. If `header == "HTTP_X_REAL_IP"`: `candidate = request.META.get(header, "").strip()`. If `header == "HTTP_X_FORWARDED_FOR"`: take the **last** comma-separated entry, stripped (nginx `$proxy_add_x_forwarded_for` appends the address it saw; earlier entries are client-controlled). Otherwise `candidate = ""`.
    +  3. If `candidate` is a valid IP (`ipaddress.ip_address(candidate)` does not raise) → return it.
    +  4. Else `remote = request.META.get("REMOTE_ADDR", "")`; return it if valid, else `"0.0.0.0"`.
    +- Tests: default setting ignores `HTTP_X_FORWARDED_FOR` and `HTTP_X_REAL_IP` (returns `REMOTE_ADDR`); with `HTTP_X_REAL_IP` setting returns that header; with XFF setting and `"1.1.1.1, 2.2.2.2"` returns `"2.2.2.2"`; invalid header value falls back to `REMOTE_ADDR`; missing `REMOTE_ADDR` → `"0.0.0.0"`; `None` → `"0.0.0.0"`.
    +
    +```python
    +def is_locked(username: str, ip: str, now: datetime) -> bool
    +```
    +`return LoginThrottle.objects.filter(username_key=normalize_username(username), ip_address=ip, locked_until__gt=now).exists()`.
    +
    +```python
    +def register_failure(username: str, ip: str, now: datetime) -> None
    +```
    +- Algorithm (inside `transaction.atomic()`):
    +  1. `key = normalize_username(username)`; `window = timedelta(seconds=settings.LOGIN_LOCKOUT_SECONDS)`.
    +  2. Opportunistic cleanup: `LoginThrottle.objects.filter(last_failure_at__lt=now - max(window, timedelta(days=1)), locked_until__isnull=True).delete()` and the same filter with `locked_until__lt=now - timedelta(days=1)`. (Keeps the table small; IP + login are personal data, retained ≤ ~1 day.)
    +  3. `row, _ = LoginThrottle.objects.get_or_create(username_key=key, ip_address=ip, defaults={"first_failure_at": now, "last_failure_at": now})`.
    +  4. `row = LoginThrottle.objects.select_for_update().get(pk=row.pk)`.
    +  5. If `row.locked_until is not None and row.locked_until <= now` (expired lock) or `row.first_failure_at <= now - window` (old window): `row.failures = 0`, `row.first_failure_at = now`, `row.locked_until = None`.
    +  6. `row.failures += 1`; `row.last_failure_at = now`; if `row.failures >= settings.LOGIN_FAILURE_LIMIT`: `row.locked_until = now + window`.
    +  7. `row.save()`.
    +
    +```python
    +def reset_failures(username: str, ip: str) -> None
    +```
    +`LoginThrottle.objects.filter(username_key=normalize_username(username), ip_address=ip).delete()`.
    +
    +### 3.5 `accounts/forms.py`
    +
    +```python
    +class ThrottledLoginFormMixin:
    +    error_messages = {
    +        **AuthenticationForm.error_messages,
    +        "locked": "Слишком много неудачных попыток входа. Попробуйте позже.",
    +    }
    +
    +    @method_decorator(sensitive_variables())
    +    def clean(self) -> dict[str, Any]
    +```
    +- Algorithm:
    +  1. `username = self.cleaned_data.get("username") or ""`; `ip = get_client_ip(self.request)`; `now = timezone.now()`.
    +  2. If `username` and `is_locked(username, ip, now)` → `raise ValidationError(self.error_messages["locked"], code="locked")`. Do **not** call `authenticate()` while locked (no password oracle; the same message for existing and non-existing users).
    +  3. `try: cleaned = super().clean()` / `except ValidationError: if username: register_failure(username, ip, now); raise`.
    +  4. If `username`: `reset_failures(username, ip)`. Return `cleaned`.
    +- A failure is any `ValidationError` from `AuthenticationForm.clean()` (wrong password, unknown user, inactive user — Django already uses one generic message for all of them).
    +- Empty password → field error, `AuthenticationForm.clean()` does not authenticate, no failure counted.
    +
    +```python
    +class ThrottledAuthenticationForm(ThrottledLoginFormMixin, AuthenticationForm): pass
    +class ThrottledAdminAuthenticationForm(ThrottledLoginFormMixin, AdminAuthenticationForm): pass
    +```
    +Wiring:
    +- `accounts/views.py`: `DeaneryLoginView.authentication_form = ThrottledAuthenticationForm`.
    +- `accounts/admin.py` (module level, after imports): `admin.site.login_form = ThrottledAdminAuthenticationForm`.
    +
    +### 3.6 Tests (`accounts/tests/test_throttling.py`, `TestCase`, `@override_settings(LOGIN_FAILURE_LIMIT=3, LOGIN_LOCKOUT_SECONDS=900, CLIENT_IP_HEADER="")`)
    +Fixture: student `u1` with password set via `set_password` + `save` (`"Test-Pass-2026!"`). Helper `post_login(username, password, **extra)` → `self.client.post(reverse("accounts:login"), {"username": ..., "password": ...}, **extra)`. Clock: `mock.patch("django.utils.timezone.now", return_value=T0)` where needed.
    +1. `test_lockout_after_limit` — 3 wrong passwords; then the correct password → 200, response contains the "locked" message, user not authenticated (`"_auth_user_id" not in self.client.session`).
    +2. `test_lock_is_per_ip` — 3 failures from `REMOTE_ADDR="10.0.0.1"`; correct password from `REMOTE_ADDR="10.0.0.2"` → 302 (logged in).
    +3. `test_lock_expires` — 3 failures at T0; at `T0 + 901 s` correct password → 302.
    +4. `test_success_resets_counter` — 2 failures, success (302), logout (POST), 2 failures, correct password → 302.
    +5. `test_messages_do_not_reveal_user_existence` — the error text for a wrong password of `u1` equals the error text for unknown user `nobody`; after 3 failures each, the "locked" message is identical for both.
    +6. `test_xff_ignored_by_default` — 3 failures with different `HTTP_X_FORWARDED_FOR` values each (same `REMOTE_ADDR`) → 4th attempt with correct password is locked.
    +7. `test_xff_used_when_enabled` — `override_settings(CLIENT_IP_HEADER="HTTP_X_FORWARDED_FOR")`; 3 failures with `HTTP_X_FORWARDED_FOR="5.5.5.5"`; correct password with `HTTP_X_FORWARDED_FOR="6.6.6.6"` → 302.
    +8. `test_admin_login_protected` — superuser with password; 3 failures on `reverse("admin:login")`; correct password → 200 with "locked" message, not logged in.
    +9. `test_locked_does_not_authenticate` — after lockout, `mock.patch("accounts.forms.authenticate")` is not needed; instead patch `django.contrib.auth.forms.authenticate` with a mock and assert it was **not** called on the locked attempt.
    +10. Unit tests for `get_client_ip` and `normalize_username` (3.4); `register_failure` sets `locked_until = now + window` exactly at the limit; old window (`first_failure_at` older than window) restarts counting at 1.
    +
    +---
    +
    +## 4. Item 2 — `seed_demo` record-number collision (`accounts/demo.py`)
    +
    +In `seed_demo_data`, **before** any write (first lines inside `transaction.atomic()`, after the password check):
    +```python
    +for seed in STUDENT_SEEDS:
    +    taken = (
    +        StudentProfile.objects.filter(record_number=seed.record_number)
    +        .exclude(user__username=seed.username)
    +        .exists()
    +    )
    +    if taken:
    +        raise DemoSeedError(
    +            f"Record number {seed.record_number} is already used by another student; "
    +            f"cannot create demo user '{seed.username}'."
    +        )
    +```
    +Do not print the other student's name.
    +
    +Test (`accounts/tests/test_seed_demo.py`): `test_record_number_collision_fails_cleanly` — create a non-demo student (`make_student("other", group, "ST-2026-0001")`); record `User`, `Faculty`, `StudyGroup` counts; `call_command("seed_demo")` with `DEMO_PASSWORD` → `CommandError` containing `"ST-2026-0001"`; all counts unchanged; `User.objects.filter(username="student1").exists()` is `False`.
    +
    +---
    +
    +## 5. Item 3 — student list markup
    +
    +`accounts/templates/accounts/student_list.html` content block:
    +```html
    +<h1>Студенты факультета</h1>
    +<p>{{ faculty.name }}</p>
    +{% if students %}
    +  <ul class="student-list">
    +    {% for student in students %}
    +      <li>
    +        <a href="{% url 'accounts:staff_student_detail' student.pk %}">{{ student.full_name }}</a>
    +        · {{ student.group.name }}, {{ student.course }} курс
    +      </li>
    +    {% endfor %}
    +  </ul>
    +{% else %}
    +  <p>Студентов нет.</p>
    +{% endif %}
    +```
    +Test (`accounts/tests/test_views.py`): `test_staff_list_empty_state_markup` — staff of a faculty without students: response contains `<p>Студентов нет.</p>` and does not contain `class="student-list"`; the non-empty case still renders `<ul class="student-list">` with `<li>` items.
    +
    +---
    +
    +## 6. Item 4 — role/profile consistency (`accounts/models.py`)
    +
    +All errors are **non-field** `ValidationError`s (a field key that is not in a form makes Django raise `ValueError` → 500).
    +
    +`User.clean()`:
    +1. `super().clean()`.
    +2. If `self.pk is None` → return.
    +3. `errors = []`; if `self.role != User.Role.STUDENT` and `StudentProfile.objects.filter(user_id=self.pk).exists()` → `"У пользователя есть профиль студента. Удалите профиль, затем меняйте роль."`; if `self.role != User.Role.STAFF` and `StaffProfile.objects.filter(user_id=self.pk).exists()` → `"У пользователя есть профиль сотрудника. Удалите профиль, затем меняйте роль."`.
    +4. If `errors` → `raise ValidationError(errors)`.
    +(This also covers making a user with a profile a superuser, because a superuser must have `role=""`.)
    +
    +`StudentProfile.clean()`:
    +1. `super().clean()`; if `self.user_id is None` → return.
    +2. If `self.user.role != User.Role.STUDENT` → `ValidationError("Профиль студента можно привязать только к пользователю с ролью «Студент».")`.
    +3. If `StaffProfile.objects.filter(user_id=self.user_id).exists()` → `ValidationError("У пользователя уже есть профиль сотрудника.")`.
    +
    +`StaffProfile.clean()`: symmetric (role STAFF; existing `StudentProfile` → error).
    +
    +`limit_choices_to` stays as is (extra protection in admin dropdowns).
    +
    +Tests (`accounts/tests/test_role_consistency.py`, `TestCase`):
    +1. `test_role_change_with_student_profile_rejected_by_model` — student with profile; `user.role = STAFF`; `user.full_clean()` → `ValidationError`.
    +2. `test_role_change_rejected_in_admin_without_500` — superuser logged in; POST to `reverse("admin:accounts_user_change", args=[student.pk])` with data `{"username": student.username, "role": "staff", "is_active": "on", "date_joined_0": "2026-11-13", "date_joined_1": "10:00:00", "last_login_0": "", "last_login_1": "", "first_name": "", "last_name": "", "email": ""}` → status 200 (form re-displayed, not 302/500), response contains "профиль студента", DB role still `student`. (If the admin form needs more keys, add only empty/default values for them; the assertion stays the same.)
    +3. `test_make_superuser_with_profile_rejected` — student with profile: `is_superuser=True`, `is_staff=True`, `role=""` → `full_clean()` → `ValidationError` mentioning the profile.
    +4. `test_role_change_without_profile_allowed` — student without profile → role STAFF → `full_clean()` passes.
    +5. `test_staff_profile_for_student_user_rejected` — `StaffProfile(user=student_user, ...).full_clean()` → `ValidationError`.
    +6. `test_second_profile_rejected` — staff user with `StaffProfile`; `StudentProfile(user=staff_user, ...)` → `ValidationError` (role check); and for a legacy inconsistent row created with `objects.create` (student user that has a `StaffProfile` inserted directly), `StudentProfile(user=that_user, ...).full_clean()` → `ValidationError` "уже есть профиль сотрудника".
    +7. `test_admin_add_staff_profile_for_student_shows_error` — superuser POST to `admin:accounts_staffprofile_add` with `user=<student pk>` → 200 with a form error, no new row.
    +
    +---
    +
    +## 7. Item 5 — demo marker for schedule rows
    +
    +### 7.1 Model fields (`schedule/models.py`)
    +Add to **both** `WeeklyLesson` and `LessonChange`:
    +```python
    +seed_key = models.SlugField("ключ демо-данных", max_length=40, blank=True, default="", editable=False)
    +```
    +Constraints (append to each `Meta.constraints`):
    +- `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="schedule_weekly_unique_seed_key")`
    +- `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="schedule_change_unique_seed_key")`
    +`""` = created by a person (admin); non-empty = created by `seed_demo`. Not `null=True` (ruff DJ001). `editable=False` keeps it out of admin forms; show it in admin via `readonly_fields = ("seed_key",)` on `WeeklyLessonAdmin` and `LessonChangeAdmin`.
    +Run `python manage.py makemigrations schedule` → `0002_...`.
    +
    +### 7.2 Seed (`schedule/demo.py`)
    +- `LessonSeed` gets a first field `key: str`: `"lesson-01"` … `"lesson-18"` in the current table order. `ChangeSeed` gets `key: str`: `"change-1"` … `"change-8"` in the current order.
    +- Lesson lookup: `WeeklyLesson.objects.filter(seed_key=seed.key).first()`; a new lesson gets `seed_key=seed.key`. **Remove** the lookup by `(discipline, lesson_type, weekday, slot)`.
    +- Change refresh: replace the delete by lesson ids with `LessonChange.objects.exclude(seed_key="").delete()` (only demo changes, on any lesson).
    +- New changes get `seed_key=seed.key`.
    +- Everything else unchanged (still via `save_weekly_lesson` / `save_lesson_change`).
    +
    +### 7.3 Data migration `schedule/migrations/0003_mark_existing_demo_rows.py`
    +- `dependencies = [("schedule", "0002_<generated name>"), ("university", "0002_discipline_room_teacher")]`.
    +- `operations = [migrations.RunPython(mark_existing_demo_rows, migrations.RunPython.noop)]`.
    +- Module constants copied as **literals** (migrations must not import `schedule.demo`):
    +  - `LEGACY_LESSONS`: 18 tuples `(key, discipline_name, lesson_type, weekday, slot, teacher_last_name, room_code, group_names_tuple)` = the `LESSON_SEEDS` rows with keys `lesson-01`…`lesson-18`.
    +  - `LEGACY_CHANGES`: 8 tuples `(key, lesson_key, kind, reason)`: `("change-1", "lesson-01", "cancelled", "Преподаватель на конференции")`, `("change-2", "lesson-16", "cancelled", "Мероприятие факультета")`, `("change-3", "lesson-08", "moved", "Перенос по просьбе преподавателя")`, `("change-4", "lesson-18", "moved", "Перенос из-за олимпиады")`, `("change-5", "lesson-13", "room_changed", "Ремонт в аудитории 308")`, `("change-6", "lesson-07", "room_changed", "Аудитория занята мероприятием")`, `("change-7", "lesson-10", "teacher_replaced", "Болезнь преподавателя")`, `("change-8", "lesson-12", "teacher_replaced", "Командировка преподавателя")`.
    +
    +```python
    +def mark_existing_demo_rows(apps, schema_editor) -> None
    +```
    +1. `WeeklyLesson = apps.get_model("schedule", "WeeklyLesson")`; `LessonChange = apps.get_model("schedule", "LessonChange")`.
    +2. For each legacy lesson: skip if a row with this `seed_key` already exists. `candidates = list(WeeklyLesson.objects.filter(seed_key="", discipline__name=..., lesson_type=..., weekday=..., slot=..., teacher__last_name=..., room__code=...))`; keep only candidates whose `set(c.groups.values_list("name", flat=True)) == set(group_names)`. If **exactly one** remains → set its `seed_key` and `save(update_fields=["seed_key"])`. Otherwise do nothing (ambiguous or absent → treated as admin data).
    +3. For each legacy change: skip if the key exists. `candidates = list(LessonChange.objects.filter(seed_key="", weekly_lesson__seed_key=lesson_key, kind=kind, reason=reason))`; exactly one → mark.
    +- Strict matching (all fields + groups) is what makes this safe; the old 4-field key alone is not used.
    +
    +### 7.4 Tests (`schedule/tests/test_demo_marker.py`, `TestCase`)
    +Use `seed_demo_data("Demo-Pass-2026-test!")` + `seed_schedule_demo(date(2026, 11, 18))`.
    +1. `test_seed_marks_rows` — 18 lessons and 8 changes have non-empty unique `seed_key`s.
    +2. `test_admin_lesson_with_same_old_key_survives_reseed` — after the first seed, create via `save_weekly_lesson` an admin lesson with the same `(discipline, lesson_type, weekday, slot)` as `lesson-01` but `valid_from=date(2028, 1, 1)`, `valid_until=date(2028, 6, 30)`, another room (`room-402`), group `ЦД-101`; re-seed twice → the admin lesson still exists with `seed_key == ""`, same room, same dates, same groups; demo lesson count with `seed_key` still 18.
    +3. `test_admin_change_survives_reseed` — admin-created `LessonChange` (via `save_lesson_change`, `seed_key=""`) on the admin lesson from test 2 → survives re-seeding.
    +4. `test_data_migration_marks_legacy_rows` — create the 18 lessons and 8 changes exactly as the old seed did but with `seed_key=""` (call `seed_schedule_demo`, then `WeeklyLesson.objects.update(seed_key="")`, `LessonChange.objects.update(seed_key="")`); add one admin lesson matching `lesson-01`'s 4-field key but with another room and non-overlapping dates; import the migration module (`importlib.import_module("schedule.migrations.0003_mark_existing_demo_rows")`) and call `mark_existing_demo_rows(django.apps.apps, None)` → 18 + 8 rows marked, the admin lesson stays `""`. Calling it a second time changes nothing.
    +5. `test_reseed_after_migration_no_duplicates` — after test 4's marking, `seed_schedule_demo(...)` → still 18 demo lessons, 8 demo changes, total lessons 19.
    +
    +---
    +
    +## 8. Item 6 — locking in schedule writes
    +
    +### 8.1 `schedule/locking.py`
    +```python
    +def lock_rooms_and_groups(room_ids: Iterable[int | None], group_ids: Iterable[int]) -> None
    +```
    +- Purpose: serialize concurrent writes that could conflict. Any two conflicting lessons/changes share a room or a group, so locking those rows makes the second writer wait until the first commits; its conflict queries then see the committed data (PostgreSQL READ COMMITTED takes a new snapshot per statement).
    +- Algorithm:
    +  1. If `not transaction.get_connection().in_atomic_block` → return (locks only make sense inside a transaction; all write paths are atomic: `schedule/mutations.py` and Django admin `changeform_view`).
    +  2. `rooms = sorted({r for r in room_ids if r is not None})`; `groups = sorted(set(group_ids))`.
    +  3. If `rooms`: `list(Room.objects.select_for_update().filter(pk__in=rooms).order_by("pk").values_list("pk", flat=True))`.
    +  4. If `groups`: `list(StudyGroup.objects.select_for_update().filter(pk__in=groups).order_by("pk").values_list("pk", flat=True))`.
    +- Fixed order (rooms first, then groups, each by pk) prevents deadlocks.
    +- SQLite: Django ignores `select_for_update()` (no `FOR UPDATE` support); SQLite serializes writers with a database-level lock anyway. Document this in the module docstring.
    +
    +### 8.2 Call sites (`schedule/validation.py`)
    +- `validate_weekly_lesson(...)`: first statement → `lock_rooms_and_groups([room_id], group_ids)`.
    +- `change_conflicts(change)`: after early return for CANCELLED/TEACHER_REPLACED, after computing `target_room_id` and `group_ids` → `lock_rooms_and_groups([target_room_id], group_ids)`, then the occurrence query.
    +Because the admin form, `LessonChange.clean()` and `mutations.py` all call these two functions, every path is covered. Import the module as `from . import locking` and call `locking.lock_rooms_and_groups(...)` (so tests can patch `schedule.locking.lock_rooms_and_groups`).
    +
    +### 8.3 Tests (`schedule/tests/test_locking.py`)
    +1. `test_save_weekly_lesson_locks_room_and_groups` — `mock.patch("schedule.locking.lock_rooms_and_groups", wraps=lock_rooms_and_groups)`; `save_weekly_lesson(...)` with room R and groups G2, G1 → called with `[R.pk]` and the group ids; (order inside the helper is checked in test 3).
    +2. `test_change_locks_target_room` — MOVED change with `new_room` R2 → called with `[R2.pk]` and the lesson's groups.
    +3. `test_lock_queries_issued` — inside `transaction.atomic()` and `CaptureQueriesContext(connection)`: call `lock_rooms_and_groups([r2.pk, r1.pk, None], [g2.pk, g1.pk])`; assert two queries on `university_room` and `university_studygroup`; if `connection.features.has_select_for_update` → both contain `FOR UPDATE`; room query precedes group query.
    +4. `test_no_lock_outside_atomic` — `TransactionTestCase`: call the helper outside `atomic` → no queries executed.
    +5. `test_admin_form_locks` — `WeeklyLessonAdminForm(data=...).is_valid()` inside `atomic` → helper called.
    +
    +---
    +
    +## 9. Item 7 — re-validation against existing changes
    +
    +### 9.1 New check inside `validate_weekly_lesson` (`schedule/validation.py`)
    +Signature unchanged. After the existing checks, **only if `errors` is still empty**, append the result of:
    +```python
    +def _occurrence_conflicts(*, lesson_pk: int | None, weekday: int, slot: int, valid_from: date, valid_until: date, room_id: int, group_ids: Collection[int]) -> list[str]
    +```
    +- Purpose: simulate the proposed lesson together with its existing changes and compare with everything else that happens (including other lessons' moved-in and room-changed occurrences).
    +- Algorithm:
    +  1. `own_changes = {c.original_date: c for c in LessonChange.objects.filter(weekly_lesson_id=lesson_pk).select_related("new_room")}` if `lesson_pk` else `{}`.
    +  2. Build proposed own occurrences `P` as tuples `(date, slot_number, room_id, original_date, label)`:
    +     - for each `d` in `[valid_from, valid_until]` with `d.weekday() == weekday`: `c = own_changes.get(d)`; skip if `c` is CANCELLED or MOVED; room = `c.new_room_id` if `c` is ROOM_CHANGED else `room_id`; add `(d, slot, room, d)`.
    +     - for each own MOVED change: add `(c.new_date, c.new_slot, c.new_room_id or room_id, c.original_date)`.
    +  3. If `P` is empty → `[]`.
    +  4. `others = [i for i in occurrences_between(min(P dates), max(P dates), None) if i.is_happening and i.lesson.id != lesson_pk]` (DB items of this lesson are stale and replaced by `P`). Index by `(date, slot.number)`.
    +  5. For each `p` in `P`, for each other item at `(p.date, p.slot)`:
    +     - `item.room.id == p.room` → `f"{p.date:%d.%m.%Y}, {p.slot} пара: аудитория {item.room.number} занята ({item.lesson.discipline.name})."`;
    +     - for each group of `item.lesson.groups.all()` with id in `group_ids` → `f"{p.date:%d.%m.%Y}, {p.slot} пара: группа {g.name} занята ({item.lesson.discipline.name})."`.
    +  6. Own duplicates: two entries of `P` with the same `(date, slot)` → `f"{date:%d.%m.%Y}, {slot} пара: занятие стоит дважды из-за переноса."`.
    +  7. Own ROOM_CHANGED changes with `new_room_id == room_id` → `f"Изменение на {c.original_date:%d.%m.%Y}: новая аудитория совпадает с аудиторией занятия. Удалите изменение."`.
    +  8. Deduplicate messages preserving order; if more than 10, keep the first 10 and append `f"…и ещё {n} конфликтов."`.
    +- Query cost: 1 + 4 queries regardless of the range length; the Python loop is days × lessons (small for this project).
    +- Notes: template-level conflicts (existing checks) still run first; this check adds date-level conflicts created by changes. It also applies to **new** lessons (`lesson_pk=None`), e.g. a new lesson placed where another lesson was moved in.
    +
    +### 9.2 Tests (`schedule/tests/test_revalidation.py`, `TestCase`)
    +Reference week Monday 2026-11-16. Lessons valid `2026-09-01..2026-12-31`. Each test: build state with `save_weekly_lesson` / `save_lesson_change`, then change one attribute and call `save_weekly_lesson` → expect `ValidationError` whose messages contain the date `"23.11.2026"` (or the relevant date); state in DB unchanged.
    +1. `test_slot_change_hits_moved_in_room` — L1 (G1, R1, Mon s2). L2 (G2, R2, Tue s1) moved from Tue 2026-11-17 to Mon 2026-11-23 s3 with `new_room=R1`. Change L1 slot 2→3 → error (room R1, 23.11.2026).
    +2. `test_room_change_hits_room_changed_occurrence` — L1 (G1, R1, Mon s2); L3 (G3, R3, Mon s2); L3 ROOM_CHANGED on 2026-11-23 to R4. Change L1 room R1→R4 → error (23.11.2026).
    +3. `test_own_move_target_conflicts_after_room_change` — L1 (G1, R1, Mon s2) moved from 2026-11-23 to Wed 2026-11-25 s4 without `new_room`; L4 (G4, R2, Wed s4). Change L1 room R1→R2 → error (25.11.2026, room).
    +4. `test_own_room_change_equals_new_room` — L1 ROOM_CHANGED on 2026-11-23 to R2; change L1 room → R2 → error "совпадает".
    +5. `test_group_change_hits_moved_in_group` — L5 (G2, R5, Thu s1) moved to Mon 2026-11-23 s2 (own room R5). L1 (G1, R1, Mon s2) adds G2 → error (группа G2, 23.11.2026).
    +6. `test_cancelled_own_occurrence_frees_date` — like test 1 but L1's 2026-11-23 occurrence is CANCELLED → slot change allowed.
    +7. `test_new_lesson_where_other_was_moved_in` — no L1; L2 moved into Mon 2026-11-23 s3 room R1; create new lesson (G9, R1, Mon s3) → error.
    +8. `test_admin_form_reports_revalidation_error` — case 1 through `WeeklyLessonAdminForm(instance=L1, data=...)` → `is_valid() is False`, message in `non_field_errors()`.
    +9. `test_message_limit` — a lesson with > 10 date conflicts → exactly 11 messages, last starts with `"…и ещё"`.
    +
    +---
    +
    +## 10. Implementation order
    +
    +Shell: repo root, `.venv` active, `export DEBUG=true`, `export DEMO_PASSWORD='Local-Demo-Pass-2026!'`. Never open or edit `.env`. Do not delete `db.sqlite3` or existing migrations.
    +
    +1. Item 3 (template) + test. `python manage.py test accounts`.
    +2. Item 2 (seed precheck) + test.
    +3. Item 4 (clean methods) + tests.
    +4. Item 1: `env_utils` + settings + `.env.example`; `LoginThrottle` model → `makemigrations accounts`; `throttling.py`, `forms.py`, wiring; admin; tests.
    +5. Item 5: `seed_key` fields → `makemigrations schedule`; seed changes; hand-written `0003` migration; `migrate`; tests.
    +6. Item 6: `locking.py` + call sites + tests.
    +7. Item 7: `_occurrence_conflicts` + tests. Run the whole suite.
    +8. README (env rows, "Login protection" paragraph incl. nginx `proxy_set_header X-Real-IP $remote_addr;` + `CLIENT_IP_
    …[2,278 more characters truncated]
  ── Thought for 13s
    I'm double-checking the throttling tests. Test 9's patch target, django.contrib.auth.forms.authenticate, looks right since that's where the form looks up authenticate, but the note about not patching accounts.forms.authenticate reads confusingly and needs rewording. I'm also still verifying that test 5's lockout message is identical for an unknown user, which it should be.

    I'm going through the remaining checks: the seed-lesson validation paths, the demo-marker test where the admin lesson differs in room and dates so it survives the migration, and the reseed count. Those all look consistent. I'm partway into the revalidation test for lesson L2, which is being moved to a different day and slot.

    I'm checking the revalidation cases for lessons L1 through L4, looking at whether moving L1 to a new slot or room creates a conflict with L2, L3 or L4 at the same time. Each case seems to hinge on whether the simulated schedule and the template-level check agree.

    I'm checking the revalidation for L5, moved to Monday the 23rd in slot 2 where L1 already sits; the groups differ, so the creation-time check passes. Adding group G2 to L1 then collides with the simulated schedule, since the moved-in L5 has G2. I'm also considering whether more than ten date conflicts could come from one lesson sharing a weekday with another in a different slot, though I'm not sure that template-level room check would catch it.

    I'm checking how the simulation handles the orphan case: it only runs once the earlier validation has passed, so that path is fine. I'm also confirming the TransactionTestCase helper runs outside any atomic block, so autocommit makes that fine too. Next I need to reword the test 9 note and add the hint for the conflict count.

    I'm adding the hint for the message limit test now, since the rewording of the test 9 note is still pending.
  ── Ran python3 - <<'EOF' p="docs/tasks/TASK-004.md" s=open(p).read() old='9. `test_locked_does_not_authenticate` — after lockout, `mock.patch("accounts.forms.authenticate")` is not needed; instead patch `django.contrib.auth.forms.authenticate` with a mock and assert it was **not** called on the locked attempt.' new='9. `test_locked_does_not_authenticate` — after lockout, patch `django.contrib.auth.forms.authenticate` (the name `AuthenticationForm.clean()` calls) with a `mock.Mock()` and assert it was **not** called on the locked attempt.' assert old in s; s=s.replace(old,new) old='9. `test_message_limit` — a lesson with > 10 date conflicts → exactly 11 messages, last starts with `"…и ещё"`.' new='9. `test_message_limit` — L1 (G1, R1, Mon s2); O (G2, R2, Mon s3) with ROOM_CHANGED to R1 on 12 different Mondays inside the range; change L1 slot 2→3 → exactly 11 messages, the last starts with `"…и ещё"`.' assert old in s; s=s.replace(old,new) open(p,"w").write(s) EOF bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-004] Planner -> Coder: TASK Spec: docs/tasks/TASK-004.md (approved by the Team lead). Tech debt only, 7 items, each with regression tests. Summary: - Item 1: DB-backed login throttle (new model `accounts.LoginThrottle`, `accounts/throttling.py`, form mixin in `accounts/forms.py`) keyed by (normalized username, client IP); used by the site login view and `admin.site.login_form`. Proxy header only via `CLIENT_IP_HEADER`. No new dependency (django-axes rejected, see 3.1). - Items 2-4: seed record-number precheck; student list markup; non-field role/profile validation in `User.clean()` and both profile `clean()`s. - Item 5: `seed_key` on WeeklyLesson and LessonChange (blank default, conditional unique); seed looks up only by `seed_key`; hand-written data migration 0003 with strict matching. - Items 6-7: `schedule/locking.py` called from `validate_weekly_lesson` and `change_conflicts` (all write paths); `_occurrence_conflicts` simulation added to `validate_weekly_lesson`. - Follow section 10 order and section 11 verification. Do not delete db.sqlite3 or migrations. Do not commit. Questions -> me. EOF (2s)
    $ python3 - <<'EOF'
  p="docs/tasks/TASK-004.md"
  s=open(p).read()
  old='9. `test_locked_does_not_authenticate` — after lockout, `mock.patch("accounts.forms.authenticate")` is not needed; instead patch `django.contrib.auth.forms.authenticate` with a mock and assert it was **not** called on the locked attempt.'
  new='9. `test_locked_does_not_authenticate` — after lockout, patch `django.contrib.auth.forms.authenticate` (the name `AuthenticationForm.clean()` calls) with a `mock.Mock()` and assert it was **not** called on the locked attempt.'
  assert old in s; s=s.replace(old,new)
  old='9. `test_message_limit` — a lesson with > 10 date conflicts → exactly 11 messages, last starts with `"…и ещё"`.'
  new='9. `test_message_limit` — L1 (G1, R1, Mon s2); O (G2, R2, Mon s3) with ROOM_CHANGED to R1 on 12 different Mondays inside the range; change L1 slot 2→3 → exactly 11 messages, the last starts with `"…и ещё"`.'
  assert old in s; s=s.replace(old,new)
  open(p,"w").write(s)
  EOF
  bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
  [TASK-004] Planner -> Coder: TASK
  Spec: docs/tasks/TASK-004.md (approved by the Team lead). Tech debt only, 7 items, each with regression tests.
  Summary:
  - Item 1: DB-backed login throttle (new model `accounts.LoginThrottle`, `accounts/throttling.py`, form mixin in `accounts/forms.py`) keyed by (normalized username, client IP); used by the site login view and `admin.site.login_form`. Proxy header only via `CLIENT_IP_HEADER`. No new dependency (django-axes rejected, see 3.1).
  - Items 2-4: seed record-number precheck; student list markup; non-field role/profile validation in `User.clean()` and both profile `clean()`s.
  - Item 5: `seed_key` on WeeklyLesson and LessonChange (blank default, conditional unique); seed looks up only by `seed_key`; hand-written data migration 0003 with strict matching.
  - Items 6-7: `schedule/locking.py` called from `validate_weekly_lesson` and `change_conflicts` (all write paths); `_occurrence_conflicts` simulation added to `validate_weekly_lesson`.
  - Follow section 10 order and section 11 verification. Do not delete db.sqlite3 or migrations. Do not commit. Questions -> me.
  EOF
    Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Спецификация TASK-004 готова: [docs/tasks/TASK-004.md](docs/tasks/TASK-004.md). Я передал её кодеру. Код ещё не написан, поэтому проверок пока не было. Перед написанием я сверил с текущим кодом три вещи: админка сохраняет объекты внутри транзакции, SQLite не поддерживает блокировку строк `FOR UPDATE`, форма входа Django устроена так, как я рассчитывал.

Решения по семи пунктам:
1. **Защита входа от подбора пароля.** Без новых зависимостей: счётчик неудачных попыток хранится в отдельной таблице базы.
   - Блокировка по паре «логин + IP»: 5 ошибок, затем 15 минут. Значения меняются через переменные окружения.
   - Защищены и обычная страница входа, и вход в админку.
   - Сообщение одинаковое для существующих и несуществующих логинов. Успешный вход обнуляет счётчик.
   - Заголовок с IP от nginx учитывается, только если его явно включить настройкой `CLIENT_IP_HEADER`.
   - Библиотеку django-axes я отклонил. Ей нужен запрос в каждом вызове проверки пароля, это ломает часть тестов. Ещё она добавляет три таблицы и вторую зависимость.
2. **Занятый номер зачётки в `seed_demo`.** Проверка идёт до любой записи. Если номер занят, команда завершается понятной ошибкой и ничего не записывает.
3. **Список студентов.** Пустое состояние вынесено из списка в отдельный абзац, разметка стала корректной.
4. **Роль и профиль.** Нельзя сменить роль, пока у пользователя есть профиль другой роли. Нельзя привязать профиль не к той роли. Админка показывает ошибку в форме, без ошибки 500.
5. **Метка демо-данных.**
   - У занятий и изменений появилось поле `seed_key`. `seed_demo` находит и обновляет только записи со своей меткой. Занятие, созданное в админке, повторный запуск больше не трогает.
   - Уже существующие демо-записи помечает отдельная миграция данных. Она сравнивает все поля и группы, а не четыре признака, как раньше.
6. **Одновременное редактирование.** Перед проверкой пересечений блокируются строки аудитории и групп. Блокировка срабатывает во всех путях записи: админка, сервисный слой, проверка изменений. На PostgreSQL это защищает от гонки. SQLite и так выполняет записи по очереди.
7. **Повторная проверка изменений.** При смене дня, пары, аудитории, групп или периода занятия проверяются все существующие изменения: и его собственные, и перенесённые на это время занятия других групп.

Главный риск: в `CLIENT_IP_HEADER` можно указать заголовок, только если nginx его перезаписывает. Иначе любой клиент подставит свой IP и обойдёт ограничение. Это записано в спецификации и попадёт в README.

От вас сейчас ничего не нужно.

── User ────────────────────────────────────────────────────
> Код ещё не написан, поэтому проверок пока не было.

Что ты имеешь ввиду?

── Thought for 9ms ─────────────────────────────────────────
  Пользователь спрашивает, что я имел в виду. Объясню, что я выступаю в роли планировщика и написал только спецификацию, а кодер будет её реализовывать, а проверочные команды вроде тестов и ruff запустятся уже после этого. Возможно, стоит также уточнить, что я сам проверил по поведению Django, и ответить коротко по-русски.

── Assistant ───────────────────────────────────────────────
Я имел в виду, что спецификация пока проверена только на бумаге. Код по ней ещё никто не запускал.

Моя роль — планировщик. Я пишу только документ с планом, сейчас это [docs/tasks/TASK-004.md](docs/tasks/TASK-004.md), а продуктовый код не пишу. Дальше всё идёт так:

1. **Кодер** пишет код по спецификации и запускает проверки из её раздела 11: тесты, `check`, `check --deploy`, ruff, проверку файла CI и двойной запуск `seed_demo`.
2. **Ревьюер** смотрит код и результаты этих проверок. Он возвращает код кодеру на доработку или одобряет задачу.
3. **Тимлид** после одобрения делает коммит и сообщает вам.

Сейчас идёт шаг 1. Поэтому я не мог написать «тесты прошли»: тестов ещё нет.

Кое-что я всё же проверил перед написанием спецификации. На установленном Django 5.2.19 я убедился, что админка сохраняет объекты внутри транзакции, SQLite не поддерживает блокировку строк `FOR UPDATE`, а форма входа Django проверяет пароль так, как я рассчитывал. Это проверка моих предположений о Django, а не проверка решения.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_ng6cbgatm6]

[TASK-004] Coder -> Planner: QUESTION

Spec: docs/tasks/TASK-004.md, Item 1 (3.4). `get_client_ip` must return the sentinel `"0.0.0.0"` for "no client IP" (request is None / invalid remote addr), and the tests (3.6 item 10) assert exactly `"0.0.0.0"`. But the project ruff config (`select = [..., "S", ...]`) enables rule S104 ("hardcoded-bind-all-interfaces"), which flags every `"0.0.0.0"` string literal: 2 sites in `accounts/throttling.py` (return "0.0.0.0") and 2 in `accounts/tests/test_throttling.py` (assertEqual(get_client_ip(...), "0.0.0.0")). So `ruff check .` (required by section 11) fails.

This is a false positive: `"0.0.0.0"` here is an "unknown IP" sentinel, not a socket bind address. Per protocol I do not add per-file-ignores myself. Two options:

1. Add `"accounts/throttling.py" = ["S104"]` and `"accounts/tests/test_throttling.py" = ["S104"]` to `[tool.ruff.lint.per-file-ignores]` (you author the ignore).
2. Replace the literal with a module constant built without a `"0.0.0.0"` literal, e.g. `UNKNOWN_IP = str(ipaddress.ip_address(0))` and return `UNKNOWN_IP` (value is still "0.0.0.0", no literal for ruff to flag, no ignore needed).

Everything else for Item 1 (and Items 2-7) is implemented; only S104 blocks a clean `ruff check .`.

── Ran 1 command ───────────────────────────────────────────
  ── Thought for 8ms
    I'd rather use the explicit, scoped suppression than the obfuscated workaround, since it's honest about what's being skipped. A single `# noqa: S104` on one constant in throttling.py, with the tests importing it, keeps the exception to one justified line instead of a file-wide ignore.

    Next I'll update the spec and then write the answer.
  ── Ran python3 - <<'EOF' p="docs/tasks/TASK-004.md" s=open(p).read() s=s.rstrip("\n")+''' --- ## Clarifications - **Q1 (Coder, ruff S104 on `"0.0.0.0"`)**: define the sentinel once in `accounts/throttling.py`:   ```python   # Sentinel for "client IP unknown"; not a bind address.   UNKNOWN_IP = "0.0.0.0"  # noqa: S104   ```   `get_client_ip` returns `UNKNOWN_IP` in every fallback case (3.4 steps 1 and 4). Tests import `UNKNOWN_IP` and assert against it — no `"0.0.0.0"` literal elsewhere. No per-file ignores in `pyproject.toml`, and no obfuscated constructions (such as `str(ipaddress.ip_address(0))`) to hide the value from the linter. ''' open(p,"w").write(s) EOF bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-004] Planner -> Coder: ANSWER Neither option as proposed. Define the sentinel once in accounts/throttling.py with a single line-level suppression and a comment:     # Sentinel for "client IP unknown"; not a bind address.     UNKNOWN_IP = "0.0.0.0"  # noqa: S104 Return UNKNOWN_IP in all fallback cases. In tests, import UNKNOWN_IP and assert against it (no "0.0.0.0" literal in tests). No per-file ignores in pyproject.toml; do not use str(ipaddress.ip_address(0)) to hide the value from ruff. Spec updated: docs/tasks/TASK-004.md, "Clarifications" Q1. EOF (2s)
    $ python3 - <<'EOF'
  p="docs/tasks/TASK-004.md"
  s=open(p).read()
  s=s.rstrip("\n")+'''

  ---

  ## Clarifications

  - **Q1 (Coder, ruff S104 on `"0.0.0.0"`)**: define the sentinel once in `accounts/throttling.py`:
    ```python
    # Sentinel for "client IP unknown"; not a bind address.
    UNKNOWN_IP = "0.0.0.0"  # noqa: S104
    ```
    `get_client_ip` returns `UNKNOWN_IP` in every fallback case (3.4 steps 1 and 4). Tests import `UNKNOWN_IP` and assert against it — no `"0.0.0.0"` literal elsewhere. No per-file ignores in `pyproject.toml`, and no obfuscated constructions (such as `str(ipaddress.ip_address(0))`) to hide the value from the linter.
  '''
  open(p,"w").write(s)
  EOF
  bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
  [TASK-004] Planner -> Coder: ANSWER
  Neither option as proposed. Define the sentinel once in accounts/throttling.py with a single line-level suppression and a comment:
      # Sentinel for "client IP unknown"; not a bind address.
      UNKNOWN_IP = "0.0.0.0"  # noqa: S104
  Return UNKNOWN_IP in all fallback cases. In tests, import UNKNOWN_IP and assert against it (no "0.0.0.0" literal in tests). No per-file ignores in pyproject.toml; do not use str(ipaddress.ip_address(0)) to hide the value from ruff. Spec updated: docs/tasks/TASK-004.md, "Clarifications" Q1.
  EOF
    Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Я ответил кодеру и дописал решение в спецификацию TASK-004.

Кодер спросил вот о чём. Функция определения IP возвращает `"0.0.0.0"`, если адрес клиента неизвестен. Проверка кода ruff помечает такую строку как ошибку безопасности (правило S104): обычно `"0.0.0.0"` означает, что сервер слушает все сетевые интерфейсы. Здесь значение означает просто «IP неизвестен», так что срабатывание ложное. Кодер предложил два варианта:

- **Отключить правило для двух файлов целиком.** Я отказался: так правило перестанет ловить настоящие ошибки во всём файле.
- **Собрать то же значение хитрым кодом, чтобы ruff его не узнал.** Я тоже отказался: это прятало бы значение от проверки, а не решало вопрос честно.

Я выбрал третий вариант. Значение задаётся один раз как константа `UNKNOWN_IP = "0.0.0.0"` с комментарием, что это пометка «IP неизвестен», а не сетевой адрес. Правило отключено только на этой одной строке (`# noqa: S104`). Тесты используют ту же константу.

Решение записано в разделе «Clarifications» файла [docs/tasks/TASK-004.md](docs/tasks/TASK-004.md).

── User ────────────────────────────────────────────────────
Не лучше ли в таком случае выводить невозможный ip по типу "999.999.999.999"? Или выход за пределы будет давать исключения?

── Thought for 2s ──────────────────────────────────────────
  I'm checking whether a GenericIPAddressField can hold "999.999.999.999": it can't, since it's not a valid IP, so PostgreSQL's inet column would throw a DataError on insert and SQLite would save it but fail full_clean. ipaddress.ip_address would also raise a ValueError, so this would be an exception either way. I'm also weighing whether to store None and skip throttling instead, but that would let an attacker bypass the limit, and behind gunicorn REMOTE_ADDR is normally always present anyway.

  I'm weighing whether 0.0.0.0 would work as a fallback key: it's a valid IP that never shows up as a real client address, so unknown clients would all share one bucket, which fails closed. I'm also checking whether "::" would trip the same lint warning, since S104 seems to flag only "0.0.0.0", though it has the same hiding issue.

── Assistant ───────────────────────────────────────────────
Нет, `"999.999.999.999"` хуже. Этот адрес не сохранится в базу, а `"0.0.0.0"` сохраняется без проблем.

**Где будут исключения.** Пометка «IP неизвестен» попадает в поле `ip_address` таблицы `LoginThrottle`. Это поле Django типа `GenericIPAddressField`.
- **На PostgreSQL** такое поле хранится в столбце типа `inet`. Записать в него `999.999.999.999` нельзя: запрос упадёт с ошибкой `DataError`. Неудачная попытка входа превратится в ошибку 500, и счётчик не увеличится.
- **На SQLite** база примет любую строку. Но получится, что код работает локально и ломается на сервере. Это худший вариант.
- **В самом коде** `get_client_ip` проверяет адреса через `ipaddress.ip_address()`. Для `999.999.999.999` эта функция выбрасывает `ValueError`. Значит, пометку пришлось бы обходить отдельной веткой.

**Почему `"0.0.0.0"` подходит.**
- Это корректный адрес. Он проходит проверку и в Python, и в обеих базах.
- С такого адреса не приходят настоящие запросы клиентов, поэтому с реальным IP пометка не совпадёт.
- Все запросы с неизвестным IP попадают в один общий счётчик. Неудачные попытки суммируются, и блокировка срабатывает раньше. Обойти ограничение, скрыв свой IP, не выйдет.

На практике этот случай почти не встречается: за gunicorn и nginx адрес соединения (`REMOTE_ADDR`) задан всегда. Так что оставляем `"0.0.0.0"`, менять ничего не нужно.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[SETUP] Team lead -> Planner: PROTOCOL UPDATE
Your role file `.claude/agents/planner.md` has two new mandatory sections: "Feasibility check" (run and record it before handing any spec to the Coder) and "Test plan" (you own the test design; the Team lead's test list is a minimum). Re-read the file now; it applies from the next task (TASK-005). Do not reply to this message.

── Explored 1 file ─────────────────────────────────────────
  ── Read .claude/agents/planner.md
  ── Thought for 4s
    I'm planning a short reply to the lead in Russian, with no further steps to take here.

── Assistant ───────────────────────────────────────────────
Я прочитал обновлённый файл роли. Начиная с TASK-005, в каждой спецификации будет два новых обязательных раздела:

- **Проверка выполнимости.** Перед передачей задачи кодеру я убеждаюсь в нескольких вещах. В репозитории нет чужих незакоммиченных изменений. Всё, на что ссылается спецификация, существует. Новые имена ни с чем не совпадают. Миграции применяются к уже существующим данным. Нужные инструменты и возможности Django есть в установленной версии. Команды проверки проходят до начала работы. Результат каждого пункта с доказательством записываю в спецификацию. Если запрос противоречит коду, я не придумываю обходной путь, а задаю вопрос тимлиду.
- **План тестов.** Список тестов от тимлида — это минимум, сами тесты проектирую я. В план входят:
  - таблица «критерий приёмки → тесты»;
  - матрица доступа для каждой страницы: аноним, студент, сотрудник своего и чужого факультета, суперпользователь;
  - граничные случаи и тесты с подменой текущего времени;
  - тест на число запросов к базе для страниц со списками;
  - регрессионные тесты для каждой исправленной ошибки;
  - точные имена файлов, классов и методов, чтобы ревьюер мог сверить тесты по одному.

На TASK-004, которую сейчас делает кодер, это не влияет. Тимлиду не отвечаю, он просил не отвечать.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-005] Team lead -> Planner: TASK
Approved by the user. Write the spec `docs/tasks/TASK-005.md` and hand it to the Coder.

## Context
Done: TASK-001 (skeleton), TASK-002 (users, roles, `accounts`, `university`, access helpers `students_visible_to` / `groups_visible_to`), TASK-003 (`schedule`: WeeklyLesson + LessonChange, `occurrences_between`, occurrence identity = `(weekly_lesson_id, original_date)`; a moved lesson keeps its identity). Reuse the existing access pattern and services. Read `plan.md`, `docs/tasks/TASK-003.md` (sections on occurrence identity and "later tasks") and the TASK-002/TASK-003 review notes (do not rely on admin forms validating fields they do not include; validation at model/service level).

The user wants this feature as simple as possible: a plain list is fine. Clarity matters more than features.

Later tasks depend on this one (design for them, do not implement): notifications (sprint 2) may announce new final results and debts.

## Goal
A student sees "how am I doing": grades and pass/fail results per discipline, session results, debts, and attendance per discipline.

## Requirements
1. New app (e.g. `academics` - justify). Data model:
   - Term (academic semester): name, start/end dates, session start/end dates.
   - Curriculum item: what a study group studies in a term - group, discipline, term, assessment form (exam / pass-fail credit / graded credit), credits (ECTS, optional). Unique per (group, discipline, term).
   - Grades:
     - current marks during the term (e.g. seminar, test): value on a 2-5 scale, date, short kind/comment;
     - final result per student per curriculum item: grade 2-5 for exam/graded credit, pass/fail for credit; date; retake attempts must be representable (keep the latest attempt as the effective result, keep history).
   - Attendance: one record per (student, occurrence) with status present / absent / excused absence. There is NO "late" status (user decision). Reference the occurrence as `(weekly_lesson, original_date)`. Validate at model/service level that the occurrence really exists for the student's group and is not cancelled, and that the student belongs to one of the lesson's groups.
   - Students only belong to one group (TASK-002); grades and attendance belong to the student, not the group.
2. Derived values (pure, testable service functions, one place):
   - average grade per term and overall (numeric final results only; define rounding);
   - debts: curriculum items of a finished session with a failing or missing final result;
   - attendance per discipline: present / marked occurrences, plus a count of unmarked past occurrences (shown as "не отмечено", not counted as absences);
   - an overall status line for the student based on debts only: "Всё в порядке" / "Есть задолженности: N". Attendance is NOT part of the status line (user decision); it is shown only in the per-discipline attendance summary.
3. Pages (server-rendered, Russian UI, mobile-first, existing CSS layers, no visual theme, no JavaScript required):
   - Student `/grades/`: status line and averages at the top; then one entry per discipline of the selected term: assessment form, current marks, final result, attendance summary. Use native `<details>/<summary>` for per-discipline detail (marks list, attendance list by date). Term selector (current term by default; past terms available). Session results and debts are clearly visible. Empty states for a term with no data.
   - No student, curriculum or grade IDs in student URLs. The term is selected by a public term code (terms are not secret); all data shown is always filtered by the current student.
   - Staff: read-only grades and attendance of a student of their own faculty, reachable from the existing staff student detail page. 404 for a student of another faculty.
   - Navigation: add "Успеваемость" for students.
4. Admin (superuser only): manage terms, curriculum items, marks, final results, attendance. Model/service-level validation (value ranges, assessment form vs result type, attendance occurrence checks, unique constraints). Invalid input -> form errors, never 500.
5. Demo data: extend `seed_demo` (still idempotent):
   - a finished previous term with session results, including one retake and at least one open debt for one demo student;
   - the current term (containing the run date) with current marks and attendance for past occurrences up to the run date, using real occurrences from the TASK-003 schedule;
   - demo students must differ visibly (e.g. one strong student, one with a debt and low attendance), so the jury sees data isolation.
   Re-running must not duplicate data. Viewing on a later date without reseeding must still work (newer occurrences simply appear as "не отмечено").
6. Queries: no N+1 on the grades page and the staff view; add query-count tests.

7. UI fixes found by the Team lead's 360 px check (small, independent of the grades feature):
   - `schedule/templates/schedule/week.html:6`: the student week view renders "← К списку групп" with an empty href (the link is meant for staff only; `back_url` is set only in the staff view). Show the link only when `back_url` is set, i.e. only for staff. Regression test: the student week page contains no "К списку групп" link; the staff group week page still contains it with the correct URL.
   - `schedule/templates/schedule/includes/lesson_item.html`: the change label renders "Отменено . Причина: ..." with a space before the period. Fix the whitespace for every change kind. Regression test on the rendered text, e.g. "Отменено. Причина:".

## Tests (must exist)
- Student sees only their own grades and attendance; never another student's, including via term switching.
- Student gets 403/404 on staff views; staff gets 404 for a student of another faculty.
- Average, debts, retake (latest attempt wins), attendance percentage, unmarked occurrences, status line - unit tests on the service functions, including edge cases (no results, only pass/fail, all excused).
- Attendance validation: occurrence of another group, cancelled occurrence, non-existent date, duplicate record.
- Result-type validation: numeric grade on a pass/fail credit and vice versa are rejected.
- `seed_demo` idempotent; the page renders on a date weeks after seeding.

## Out of scope
Teacher accounts and grade entry outside admin, notifications, rating among students, GPA conversion tables, exports, charts, visual theme, remaining tech-debt items from `plan.md` (only the two UI fixes in item 7 are in scope).

## Verification
All existing verification commands pass (check, deploy check, makemigrations --check, test, ruff, CI YAML), `seed_demo` twice without errors, manual check of `/grades/` at 360 px width.

── Ran 1 command ───────────────────────────────────────────
  ── Thought for 9ms
    I'm starting with a feasibility check: looking at git status, whether TASK-004 has been committed, and what files are in place.
  ── Ran git log --oneline | head -5 && git status --short && ls && ls */migrations/ | head -40 && cat schedule/templates/schedule/week.html schedule/templates/schedule/includes/lesson_item.html && cat schedule/views.py | sed -n 1,200p
    $ git log --oneline | head -5 && git status --short && ls && ls */migrations/ | head -40 && cat schedule/templates/schedule/week.html schedule/templates/schedule/includes/lesson_item.html && cat schedule/views.py | sed -n 1,200p
    e7aa72a Team protocol: planner test plan and feasibility check
    c5e2174 TASK-004: tech debt from reviews
    a240f23 TASK-003: schedule
    001c455 TASK-002: users, roles, login and access control
    04b7f0c TASK-001: production settings tests (amendment 1)
     M plan.md
    CHANGELOG.md
    README.md
    accounts
    config
    core
    db.sqlite3
    docs
    manage.py
    opencode.json
    plan.md
    pyproject.toml
    requirements-dev.txt
    requirements.txt
    schedule
    static
    templates
    university
    accounts/migrations/:
    0001_initial.py
    0002_loginthrottle.py
    __init__.py
    __pycache__

    schedule/migrations/:
    0001_initial.py
    0002_lessonchange_seed_key_weeklylesson_seed_key_and_more.py
    0003_mark_existing_demo_rows.py
    __init__.py
    __pycache__

    university/migrations/:
    0001_initial.py
    0002_discipline_room_teacher.py
    __init__.py
    __pycache__
    {% extends "base.html" %}
    {% block content %}
      <h1>{{ title }}</h1>
      {% if group %}
        <p>{{ group.program }}, {{ group.course }} курс</p>
        <p><a href="{{ back_url }}">← К списку групп</a></p>
      {% endif %}
      {% include "schedule/includes/week_nav.html" %}
      {% include "schedule/includes/week_days.html" %}
    {% endblock %}
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
    from datetime import date, timedelta
    from typing import Any

    from django.db.models import QuerySet
    from django.shortcuts import get_object_or_404
    from django.urls import reverse
    from django.utils import timezone
    from django.views.generic import ListView, TemplateView

    from accounts.access import StaffRequiredMixin, StudentRequiredMixin
    from accounts.selectors import groups_visible_to
    from schedule.services import (
        WeekSchedule,
        annotate_today,
        day_schedule,
        week_schedule,
        week_start,
    )
    from university.models import StudyGroup


    class TodayView(StudentRequiredMixin, TemplateView):
        template_name = "schedule/today.html"

        def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
            context = super().get_context_data(**kwargs)
            now = timezone.localtime()
            day = day_schedule(now.date(), [self.profile.group_id], today=now.date())
            annotation = annotate_today(day.items, now.time())
            context["day"] = day
            context["annotation"] = annotation
            context["group"] = self.profile.group
            context["week_url"] = reverse("schedule:week")
            return context


    class StudentWeekView(StudentRequiredMixin, TemplateView):
        template_name = "schedule/week.html"

        def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
            context = super().get_context_data(**kwargs)
            today = timezone.localdate()
            day = self.kwargs.get("day") or today
            week = week_schedule(day, [self.profile.group_id], today)
            context.update(_week_context(week, today, "schedule:week_of", {}))
            context["group"] = self.profile.group
            context["title"] = "Моё расписание"
            return context


    class StaffGroupListView(StaffRequiredMixin, ListView):
        template_name = "schedule/staff_group_list.html"
        context_object_name = "groups"

        def get_queryset(self) -> QuerySet[StudyGroup]:
            return groups_visible_to(self.request.user)


    class StaffGroupWeekView(StaffRequiredMixin, TemplateView):
        template_name = "schedule/week.html"

        def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
            context = super().get_context_data(**kwargs)
            group = get_object_or_404(groups_visible_to(self.request.user), pk=self.kwargs["group_id"])
            today = timezone.localdate()
            day = self.kwargs.get("day") or today
            week = week_schedule(day, [group.pk], today)
            context.update(
                _week_context(week, today, "schedule:staff_group_week_of", {"group_id": group.pk})
            )
            context["group"] = group
            context["title"] = f"Расписание группы {group.name}"
            context["back_url"] = reverse("schedule:staff_groups")
            return context


    def _week_context(
        week: WeekSchedule, today: date, url_name: str, url_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "week": week,
            "prev_url": reverse(url_name, kwargs={**url_kwargs, "day": week.start - timedelta(days=7)}),
            "next_url": reverse(url_name, kwargs={**url_kwargs, "day": week.start + timedelta(days=7)}),
            "current_url": reverse(url_name, kwargs={**url_kwargs, "day": today}),
            "is_current_week": week.start == week_start(today),
        }
  ── Thought for 102ms
    I've confirmed the git status is clean apart from plan.md, so item 1 is feasible. Next I need to gather the pieces this will touch: the schedule service's item and occurrence helpers, the demo seed flow and command, the student detail template, the test helpers, the nav in base.html, and the StudentProfile fields. After that I'll run the test suite to get a baseline.

── Explored 2 searches, 1 file ─────────────────────────────
  ── Searched for ^def \|^class \|^    def \|^@ in schedule/services.py
  ── Read schedule/services.py
  ── Thought for 5ms
    I'm checking a grep problem caused by zsh globbing, so I'll make sure the pattern is quoted. I also want to run a baseline verification alongside that fix.
  ── Searched for academics\|/grades in templates
  ── Thought for 5ms
    The test output tail got swallowed, and it looks like the tests are printing seed output instead of the real results. I need to check the result line to see what actually happened.

── Ran 1 command ───────────────────────────────────────────
  ── Ran source .venv/bin/activate && DEBUG=true python manage.py test 2>&1 | grep -E "^(Ran|OK|FAILED)"; DEBUG=true DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo | tail -1 (46s)
    $ source .venv/bin/activate && DEBUG=true python manage.py test 2>&1 | grep -E "^(Ran|OK|FAILED)"; DEBUG=true DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo | tail -1
    Ran 223 tests in 43.212s
    OK
    Schedule ready: 7 rooms, 6 teachers, 6 disciplines, 18 weekly lessons, 8 changes.
  ── Thought for 1m 52s
    I'm noting that the local dev database was already seeded, which is fine since the seed is idempotent. Next I'm working out the design, starting with the decision to put this in its own `academics` app as a separate bounded context. For the `Term` model, I'm planning a unique slug code like "2026-autumn" for use in URLs, along with a display name.

    I'm settling the `Term` fields: a name, start and end dates for the whole term, and session start and end dates, with the session falling inside the term. I'm also planning to order terms by most recent start and reject overlapping terms in `clean()`, since "current term" depends on that. For the lookup, I'd take the term containing today, otherwise the most recent one that already ended.

    I'm settling the rest of the models: `CurriculumItem` ties a group, discipline and term together with an assessment form, optional credits, and a uniqueness rule per group, discipline and term. `CurrentMark` belongs to a student and a curriculum item, with the item protected from deletion while marks exist, and the student must belong to that item's group.

    I'm adding the attempt-level result for each student and curriculum item: an attempt number from one to three, a date, and either a grade from two to five or a pass flag, with exactly one of them set. Each student can have at most one record per attempt, and `clean()` will check that the result form matches the assessment type and that later attempts are not dated before earlier ones.

    I'm settling the grade rules for the attempts: a grade of 3 or higher, or a passed flag, counts as positive, while a grade of 2 or a failed flag counts as failing. I'm also leaning toward rejecting any new attempt after a positive one, to keep the debt logic simple, and requiring that attempts be numbered consecutively from one with dates that never go backwards. For the nullable `passed` field, I'm starting to sketch its definition.

    I'm weighing a single `result` field instead of separate grade and passed fields, since it would let one set of choices cover both exams and credits. Exams and graded credits would take values 2 through 5, while plain credits would take pass or fail. The main trade-off is that averages would need a numeric mapping, though that seems manageable.

    I'm laying out the `Attendance` model: each record ties a student to a weekly lesson on a specific date, with a status of present, absent, or excused, and a uniqueness rule per student, lesson and date. Validation will check that the student's group is among the lesson's groups and that the date really is an occurrence of that lesson.

    I'm checking the attendance validation rules: the student's group has to be among the lesson's groups, the date has to match the lesson's weekday and validity range, and it can't be a cancelled occurrence. I'm also rejecting future occurrences, using the moved date if the lesson was rescheduled, and I'll check those directly against the models rather than through the occurrence service.

    I'm defining the attendance checks as a single helper: first the lesson's weekday and validity range must match the date, then a cancellation record for that date rules it out. Next I'm working out the effective date, using the moved date if the lesson was rescheduled, and rejecting it if that is in the future. Last, I'm confirming the student belongs to one of the lesson's groups, with the discipline taken from the lesson.

    I'm working out how attendance gets summarized per discipline for a term: it's keyed by the lesson's discipline and counts occurrences whose original date falls in the term, up to today. Disciplines that have lessons but no curriculum item in the term won't be shown.

    I'm settling how attendance counts past lessons: an occurrence is past only if its effective date is before today, so a lesson happening today doesn't count as unmarked yet, though a record marked today still counts. For the term summary, I'll look at effective dates from the term start up to yesterday, since a rescheduled lesson may show up on a date outside its original range.

    I'm now defining how attendance is summarized: happening occurrences in the term range whose date is before today count as unmarked when they have no record, and records for occurrences in the range are counted as marked, including ones dated today.

    I'm weighing how to handle the attendance percentage: I'm leaning toward leaving excused absences out of the denominator, so the figure is present divided by present plus absent, and showing a dash when that total is zero, rather than counting all marked records.

    I'm settling the average as the mean of the effective numeric results, including failing 2s, rounded to two decimals with half-up rounding.

    I'm now finishing the average and debt rules: debts only count for curriculum items in a term whose session has already ended, where the effective result is missing or failing, and a summary status line will show either "all good" or the number of debts across all terms. Effective results come from the highest attempt per student and item, and the service layer in `academics/services.py` will hold these calculations.

    I'm sketching the service functions in `academics/services.py`: picking the current term, collapsing results to the latest attempt per item, and computing the average and debts as pure functions. The attendance summary will be a pure function too, taking occurrence keys and records and returning per-discipline counts and a percentage.

    I'm sketching the report data structures next: an attendance summary with present, absent, excused, and unmarked counts plus a percentage, an attendance entry for each occurrence, and a discipline report wrapping the curriculum item.

    I'm now writing out the report's query plan, starting with loading the term's curriculum items for the student's group along with their disciplines.

    I'm now planning the report's queries: the items for the term should cover the student's current group as well as any item that has a mark or result for this student, so a transfer doesn't lose past grades. Marks and final results will be pulled for the term, ordered by date and attempt, and attendance records will be filtered to the term's date range, with occurrences computed up to the earlier of the term end and today.

    I'm sketching the rest of the report logic: skipping occurrence lookup when the term hasn't started, and using a fixed number of queries. For the overview across all terms, I'm pulling the student's items, results, and terms together, with the term loaded so debts can check its session end. Attendance entries per discipline will list the occurrences that have already happened or been marked, keyed by lesson and original date, and I'm planning `/grades/` plus a per-term route with a selector covering terms that have data for the student.

    I'm planning the term and staff routes next: a term selector listing terms with data for the student, and a 404 for unknown term codes. Students only ever see their own records, while staff access goes through a student lookup restricted to what they can see.

    I'm wiring the student's grades and staff's per-student views into the academics app: named routes for both, a link from the staff student detail page, a nav entry for students, and admin registrations for terms, curriculum items, marks, results, and attendance.

    I'm making sure the admin forms run the model checks, so I'll keep the cross-field validation in `clean()` as non-field errors and guard against missing foreign keys so it never crashes. For the write path, I'm still weighing whether the admin's save or a separate `academics/mutations.py` module should handle the seed data.

    I'm settling on `save_validated` in `academics/mutations.py` to run `full_clean()` before saving, with attendance checks using today's date and seed data limited to past occurrences.

    I'm adding validation rules for the write path: a mark must belong to the student's current group and fall within the term's dates, with values limited to 2 through 5. For a final result I'm checking the same group match, requiring the date to be on or after the term start and not in the future, and for retakes I'm requiring a previous failing attempt with a date no earlier than it.

    I'm checking that an attempt can't be retaken after a passing result, so saving attempt n gets rejected if any later attempt exists with a positive result. For `Term`, I'm validating that the dates are in order and that no other term overlaps the range, with the code kept as a slug. The demo seed will generate a current term containing today, starting eight weeks before this week's start and running twelve weeks forward.

    I'm choosing the term code for the seeded current term. Rather than a generic "demo" slug, I'm leaning toward a date-based code: the autumn semester of year Y becomes "Y-autumn" with a matching display name, and the spring semester follows the same pattern. The session dates will then be fixed to the real calendar, not computed from the run date.

    I'm deciding the term dates by calendar rather than by the run date: from September through December a term is the autumn one, starting September 1 and running to January 31 of the next year, with the session in the last few weeks of January. January belongs to the autumn term that began the previous year. February through August falls under the spring term, so I'm working out its start and end dates next.

    I'm settling the term dates by calendar: the spring term runs February 1 through August 31 with its session in June, and the autumn term runs September 1 through January 31 with its session in January. Together they tile the whole year, so a current term always exists. I'm working out the codes as "2026-autumn" and "2026-spring" with matching names, and deriving the previous term from the day before the current term starts.

    I'm checking the seed's idempotency with `update_or_create` on the term code, and I'm going to keep the overlap error generic so it reads correctly for any conflict with existing data. For the demo records themselves, I'm weighing whether to add a marker so the seed only touches its own rows, or to rely on natural unique keys.

    I'm deciding how to keep the demo marks apart from real data, since marks have no natural unique key the way attendance does. Attendance will use get_or_create on its unique key so any records an admin already made are left alone, and each student's status for an occurrence will come from a fixed rule rather than randomness. Marks will likely need a seed_key slug to mark which rows the seed owns.

    I'm deciding to add a `seed_key` to the marks, results, and attendance so the seed only updates rows it created itself, and it won't overwrite anything an admin entered by hand. If a row with the same unique key already exists without a seed key, the seed will skip it.

    I'm going with get_or_create for all the seed's academic rows, so it creates what's missing and never overwrites existing data, and I'm adding a seed_key only to current marks since they have no natural unique key. The mark dates will be anchored to the term's start with offsets, and only past dates get created, so later reruns fill in more.

    I'm listing the curriculum for each group in the term: the disciplines from the schedule seed, with their assessment types and ECTS credits, starting with the ЦД-101 group's courses.

    I'm listing the previous term's curriculum for ЦД-101, swapping in different disciplines so the two terms don't repeat: История дипломатии as an exam, Математика as a graded credit, Основы права as a credit, and Английский. I'm reusing the get-or-create approach so the reference disciplines are upserted by name.

    I'm listing the previous term's results for the demo students: the strong student with two fives and two passes, and the student with a retake in История дипломатии and an open debt in Основы права, with their averages worked out from those marks.

    I'm rounding out the demo data: the previous term's results are set, and the current term gets marks on a fixed schedule from its start date, but only for dates already past, with values rotating across disciplines.

    I'm settling attendance next: student1 is present except for an excused absence every tenth occurrence, student3 is absent on every third occurrence to show low attendance, and student2 misses every sixth. Occurrences get indexed by date and slot, so earlier entries keep their index when the seed reruns and new days just extend the list.

    I'm settling on a status rule for attendance that's stable per occurrence: each one gets a fixed status from its original date plus its slot, so reruns produce the same result. Student1 is excused on every eleventh occurrence and otherwise present, student3 is absent on every third and excused on every seventh, and student2 is absent on every eighth. I'm also making sure only occurrences before today count, that cancelled ones are skipped, and that records are keyed by the original date.

    I'm checking that the attendance records fit the rules (the original date's weekday and range, and that the student belongs to the lesson's group), then confirming the previous term has no attendance since its schedule ended before the window. I'm estimating about 216 attendance rows, each needing a few queries to validate, and the reruns are fine because each row is checked for existence first.

    I'm moving on to the UI fixes: adding a back link to the group list inside the week template when a back URL is given, and reworking the lesson item label so the cancellation reason follows directly after "Отменено" with a period and no stray whitespace.

    Finishing the lesson-change label: I'm putting the cancellation reason right after "Отменено" with a period and no extra whitespace, using one template line with the conditionals inline. Then I'll cover the lesson-change text in the tests for each change kind, plus checking that the student's week view doesn't show the back link.

    I'm turning to the view tests now: anonymous visitors should get redirected, a student sees their own grades, and staff only see students in their own faculty, with other faculties getting a 404 and superusers a 403 on both pages. An unknown term code should return 404 on both. The settings aren't touched, so there's nothing to cover there. For query counts, I'm going to compare the grades and staff pages with small and larger datasets and assert the counts stay the same.

    I'm checking whether any existing test asserts on "Отменено" with a newline before or after it, since the label change could break that.
  ── Thought for 8ms
    Все 223 теста, проверки check и ruff, а также файл CI прошли, и репозиторий чистый, если не считать незакоммиченного plan.md тимлида. Дальше сверю пару мест в коде и напишу спецификацию.

── Explored 1 search ───────────────────────────────────────
  ── Searched for Отменено\|К списку групп\|Причина in accounts/tests
  ── Thought for 5ms
    Now I'm moving on to writing the spec, which is going to be a large piece of work, so I'll draft it carefully but efficiently.

── Created 1 file ──────────────────────────────────────────
  ── Created docs/tasks/TASK-005.md +598
    --- /dev/null
    +++ b~/hackatonproject/docs/tasks/TASK-005.md
    +# TASK-005: Grades, session results, debts, attendance (+ 2 schedule UI fixes)
    +
    +Author: Planner. Status: ready for implementation.
    +Base commit: `e7aa72a`. Product context: `plan.md`. Reused: `docs/tasks/TASK-002.md` (access pattern), `docs/tasks/TASK-003.md` (occurrence identity `(weekly_lesson, original_date)`, `occurrences_between`), `docs/tasks/TASK-004.md` (validation at model/service level, non-field errors).
    +
    +The user wants this **as simple as possible**: plain lists, native `<details>`, no JavaScript, no charts.
    +
    +---
    +
    +## 1. Goal
    +
    +A student opens `/grades/` and sees "how am I doing": a status line (debts), averages, and per discipline of the selected term — assessment form, current marks, final result (with retake history), attendance summary. Staff see the same report, read-only, for students of their own faculty.
    +
    +## 2. Acceptance criteria
    +
    +| ID | Criterion |
    +|---|---|
    +| AC1 | New app `academics` with `Term`, `CurriculumItem`, `CurrentMark`, `FinalResult`, `Attendance`; migrations exist; `makemigrations --check` clean. |
    +| AC2 | All business rules are enforced in model `clean()` with **non-field** errors and in DB constraints where possible; admin shows form errors, never 500. |
    +| AC3 | Retakes: several attempts per (student, curriculum item); the highest attempt number is the effective result; history is shown. |
    +| AC4 | Attendance references an occurrence `(weekly_lesson, original_date)`; rejected for: wrong group, no lesson on that date, cancelled occurrence, future occurrence, duplicate. Status is only present / absent / excused. |
    +| AC5 | Pure service functions compute: effective results, term and overall averages (2 decimals, half-up), debts (finished session, failing or missing result), attendance summary (present, absent, excused, unmarked, percent), status line. |
    +| AC6 | `/grades/` shows status line, overall and term averages, term selector (links), one `<details>` entry per discipline, debts marked, empty state. `/grades/<term_code>/` selects a term; unknown code → 404. No student/curriculum/grade IDs in student URLs. |
    +| AC7 | Staff report `/staff/students/<pk>/grades/[<term_code>/]` for own-faculty students (link from the staff student detail page); another faculty → 404; students → 403. |
    +| AC8 | Navigation shows "Успеваемость" for students only. |
    +| AC9 | Grades page and staff report run a constant number of queries. |
    +| AC10 | `seed_demo` (idempotent) adds a finished previous term with results (one retake, one open debt) and the current term with marks and attendance for past occurrences; students differ visibly; renders weeks later without reseeding. |
    +| AC11 | Schedule UI fixes: no "К списку групп" link on the student week page; change label renders without a space before the period. |
    +
    +## 3. Out of scope
    +
    +Teacher accounts, grade entry outside admin, notifications, rating, GPA tables, exports, charts, visual theme, other `plan.md` tech-debt items, linking attendance to curriculum items, attendance of the previous term in demo data, grade-improvement retakes (a new attempt after a positive result is rejected).
    +
    +---
    +
    +## 4. Design decisions
    +
    +### 4.1 New app `academics`
    +Grades and attendance are a separate bounded context: own models, rules, services and pages. It depends on `university` (groups, disciplines), `accounts` (students, access) and `schedule` (occurrences). Nothing in those apps imports `academics` (exception: two templates link to `academics` URLs — `base.html` nav and `accounts/student_detail.html`). Notifications will later read `academics.services`.
    +
    +### 4.2 One `result` field for final results
    +`FinalResult.result` is a single choice field: `"5"`, `"4"`, `"3"`, `"2"`, `"pass"`, `"fail"`. The assessment form decides the allowed subset (exam / graded credit → `2..5`; credit → `pass/fail`). One field is simpler than `grade` + `passed` and makes "numeric on a credit" a plain set-membership check.
    +
    +### 4.3 Definitions (used everywhere)
    +- **Effective result** of (student, curriculum item) = the `FinalResult` with the highest `attempt`.
    +- **Positive** result: `5`, `4`, `3`, `pass`. **Failing**: `2`, `fail`.
    +- **Average** = arithmetic mean of numeric effective results (`2..5`, **including 2**), `Decimal` rounded to 2 places with `ROUND_HALF_UP`; `None` when there are no numeric results. Current marks never enter averages.
    +- **Session finished**: `today > term.session_end`.
    +- **Debt**: curriculum item of a term whose session is finished and whose effective result is missing or failing.
    +- **Status line**: `"Всё в порядке"` if 0 debts in all terms, else `f"Есть задолженности: {n}"`. Attendance is not part of it.
    +- **Attendance percent** = `present / (present + absent) * 100`, rounded half-up to an integer; `None` if `present + absent == 0`. **Excused absences are marked but excluded from the percent** (an excused absence must not lower attendance; "all excused" → `None`, shown as "—"). Counts of all three statuses are shown.
    +- **Past occurrence**: a happening occurrence (`ScheduleItem.is_happening`) whose displayed date `item.date < today`. **Unmarked** = past occurrence without an attendance record; shown as «не отмечено», not an absence. Today's lessons are not "past" yet but may already be marked.
    +- **Term of an occurrence**: `term.start_date <= item.date <= term.end_date`. Attendance is grouped by `item.lesson.discipline`; only disciplines that have a curriculum item for the student in the term are shown.
    +- **Current term** (`current_term(today)`): the term containing `today`; else the most recent term that ended before `today`; else the earliest future term; else `None`.
    +
    +### 4.4 Validation layer
    +Same pattern as TASK-004: every rule is in `Model.clean()` and raises **non-field** `ValidationError`s (a field key absent from a form would cause a 500). Code writes go through `academics/mutations.save_validated()` (`full_clean()` + `save()` in a transaction). Admin uses default `ModelForm`s, so `clean()` always runs.
    +
    +### 4.5 Later tasks (do not implement)
    +Notifications can call `student_overview(student, today).debts` and query `FinalResult` by `created_at` for "new final results".
    +
    +---
    +
    +## 5. Architecture
    +
    +### 5.1 Files
    +
    +Create:
    +```
    +academics/__init__.py
    +academics/apps.py
    +academics/models.py
    +academics/services.py
    +academics/mutations.py
    +academics/admin.py
    +academics/views.py
    +academics/urls.py
    +academics/demo.py
    +academics/migrations/__init__.py
    +academics/migrations/0001_initial.py                       (generated)
    +academics/templates/academics/report.html
    +academics/templates/academics/includes/discipline.html
    +academics/tests/__init__.py
    +academics/tests/helpers.py
    +academics/tests/test_models.py
    +academics/tests/test_services.py
    +academics/tests/test_views.py
    +academics/tests/test_demo.py
    +```
    +Change:
    +```
    +config/settings.py (INSTALLED_APPS), config/urls.py, pyproject.toml (known-first-party),
    +templates/base.html (nav), accounts/templates/accounts/student_detail.html (link),
    +accounts/management/commands/seed_demo.py, static/css/base.css,
    +schedule/templates/schedule/week.html, schedule/templates/schedule/includes/lesson_item.html,
    +schedule/tests/test_views.py (2 regression tests), README.md
    +```
    +No other files. No new dependencies. Do not change `.env.example` (no new env variables).
    +
    +### 5.2 Wiring
    +- `INSTALLED_APPS`: add `"academics"` after `"schedule"`.
    +- `config/urls.py`: `path("", include("academics.urls"))` after the `schedule` include.
    +- `pyproject.toml`: `known-first-party = ["config", "core", "accounts", "university", "schedule", "academics"]`.
    +- `AcademicsConfig`: `name = "academics"`, `verbose_name = "Успеваемость"`, `default_auto_field = "django.db.models.BigAutoField"`.
    +
    +### 5.3 Models (`academics/models.py`)
    +
    +All models: Russian `verbose_name`s, `__str__`, ruff DJ012 order. Enums:
    +```python
    +class AssessmentForm(models.TextChoices):
    +    EXAM = "exam", "Экзамен"
    +    CREDIT = "credit", "Зачёт"
    +    GRADED_CREDIT = "graded_credit", "Дифференцированный зачёт"
    +
    +class ResultValue(models.TextChoices):
    +    FIVE = "5", "Отлично (5)"
    +    FOUR = "4", "Хорошо (4)"
    +    THREE = "3", "Удовлетворительно (3)"
    +    TWO = "2", "Неудовлетворительно (2)"
    +    PASS = "pass", "Зачтено"
    +    FAIL = "fail", "Не зачтено"
    +
    +NUMERIC_RESULTS = {"5", "4", "3", "2"}
    +PASS_FAIL_RESULTS = {"pass", "fail"}
    +POSITIVE_RESULTS = {"5", "4", "3", "pass"}
    +
    +class AttendanceStatus(models.TextChoices):
    +    PRESENT = "present", "Присутствовал"
    +    ABSENT = "absent", "Отсутствовал"
    +    EXCUSED = "excused", "Уважительная причина"
    +```
    +
    +**`Term`**
    +| Field | Definition |
    +|---|---|
    +| `code` | `SlugField("код", max_length=30, unique=True)` — public, used in URLs, e.g. `2026-autumn` |
    +| `name` | `CharField("название", max_length=100)` |
    +| `start_date` | `DateField("начало")` |
    +| `end_date` | `DateField("окончание")` (inclusive; includes the session) |
    +| `session_start` | `DateField("начало сессии")` |
    +| `session_end` | `DateField("окончание сессии")` |
    +- `Meta`: `ordering = ["-start_date"]`; constraint `CheckConstraint(condition=Q(start_date__lte=F("session_start")) & Q(session_start__lte=F("session_end")) & Q(session_end__lte=F("end_date")), name="academics_term_dates_order")`.
    +- `__str__` → `self.name`.
    +- `clean()`: if all four dates set: order violated → `ValidationError("Даты должны идти по порядку: начало ≤ начало сессии ≤ конец сессии ≤ окончание.")`; overlap with another term (`Term.objects.exclude(pk=self.pk).filter(start_date__lte=self.end_date, end_date__gte=self.start_date)` exists) → `ValidationError("Семестр пересекается с семестром «<name>».")`.
    +
    +**`CurriculumItem`**
    +| Field | Definition |
    +|---|---|
    +| `group` | `ForeignKey("university.StudyGroup", PROTECT, related_name="curriculum_items")` |
    +| `discipline` | `ForeignKey("university.Discipline", PROTECT, related_name="curriculum_items")` |
    +| `term` | `ForeignKey(Term, PROTECT, related_name="curriculum_items")` |
    +| `assessment_form` | `CharField("форма контроля", max_length=16, choices=AssessmentForm.choices)` |
    +| `credits` | `PositiveSmallIntegerField("зачётные единицы", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(30)])` |
    +- `Meta`: `ordering = ["term", "discipline__name"]`; `UniqueConstraint(fields=["group", "discipline", "term"], name="academics_curriculum_unique")`; `CheckConstraint(condition=Q(credits__isnull=True) | (Q(credits__gte=1) & Q(credits__lte=30)), name="academics_curriculum_credits_range")`.
    +- `__str__` → `f"{self.discipline} — {self.group} ({self.term})"`.
    +- Property `allowed_results -> set[str]`: `PASS_FAIL_RESULTS` if `CREDIT` else `NUMERIC_RESULTS`.
    +
    +**`CurrentMark`**
    +| Field | Definition |
    +|---|---|
    +| `student` | `ForeignKey("accounts.StudentProfile", CASCADE, related_name="current_marks")` |
    +| `curriculum_item` | `ForeignKey(CurriculumItem, PROTECT, related_name="current_marks")` |
    +| `value` | `PositiveSmallIntegerField("оценка", validators=[MinValueValidator(2), MaxValueValidator(5)])` |
    +| `date` | `DateField("дата")` |
    +| `kind` | `CharField("вид работы", max_length=100)` — e.g. «Семинар», «Контрольная работа» |
    +| `seed_key` | `SlugField("ключ демо-данных", max_length=80, blank=True, default="", editable=False)` |
    +- `Meta`: `ordering = ["date", "pk"]`; `CheckConstraint(condition=Q(value__gte=2) & Q(value__lte=5), name="academics_mark_value_2_5")`; `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="academics_mark_unique_seed_key")`.
    +- `__str__` → `f"{self.value} ({self.date:%d.%m.%Y})"`.
    +- `clean()` (skip a check if a required FK/value is `None`):
    +  - `student.group_id != curriculum_item.group_id` → `"Студент не из группы этого учебного плана."`;
    +  - `date` outside `[term.start_date, term.end_date]` → `"Дата вне семестра."`;
    +  - `date > timezone.localdate()` → `"Дата оценки в будущем."`.
    +
    +**`FinalResult`**
    +| Field | Definition |
    +|---|---|
    +| `student` | `ForeignKey("accounts.StudentProfile", CASCADE, related_name="final_results")` |
    +| `curriculum_item` | `ForeignKey(CurriculumItem, PROTECT, related_name="final_results")` |
    +| `attempt` | `PositiveSmallIntegerField("попытка", default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])` |
    +| `result` | `CharField("результат", max_length=8, choices=ResultValue.choices)` |
    +| `date` | `DateField("дата")` |
    +| `created_at` | `DateTimeField("создано", auto_now_add=True)` |
    +- `Meta`: `ordering = ["curriculum_item", "attempt"]`; `UniqueConstraint(fields=["student", "curriculum_item", "attempt"], name="academics_result_unique_attempt")`; `CheckConstraint(condition=Q(attempt__gte=1) & Q(attempt__lte=5), name="academics_result_attempt_1_5")`; `CheckConstraint(condition=Q(result__in=["5", "4", "3", "2", "pass", "fail"]), name="academics_result_value")`.
    +- Properties: `is_numeric` (`result in NUMERIC_RESULTS`), `numeric_value -> int | None`, `is_positive` (`result in POSITIVE_RESULTS`).
    +- `__str__` → `f"{self.get_result_display()} (попытка {self.attempt})"`.
    +- `clean()` (skip checks whose inputs are `None`):
    +  1. `result not in curriculum_item.allowed_results` → `"Для формы контроля «<form>» допустимы только: <labels>."` (labels joined by `", "`).
    +  2. student not in item group → same message as `CurrentMark`.
    +  3. `date < term.start_date` → `"Дата раньше начала семестра."`; `date > timezone.localdate()` → `"Дата результата в будущем."`.
    +  4. `others = FinalResult.objects.filter(student=…, curriculum_item=…).exclude(pk=self.pk)`:
    +     - if `attempt > 1`: `prev = others.filter(attempt=attempt - 1).first()`; `prev is None` → `"Сначала внесите попытку <attempt-1>."`; `prev.is_positive` → `"Предыдущая попытка уже успешна — пересдача не нужна."`; `date < prev.date` → `"Пересдача не может быть раньше предыдущей попытки."`;
    +     - if `self.is_positive` and `others.filter(attempt__gt=attempt).exists()` → `"После успешной попытки не может быть следующих попыток."`.
    +
    +**`Attendance`**
    +| Field | Definition |
    +|---|---|
    +| `student` | `ForeignKey("accounts.StudentProfile", CASCADE, related_name="attendance_records")` |
    +| `weekly_lesson` | `ForeignKey("schedule.WeeklyLesson", PROTECT, related_name="attendance_records")` |
    +| `original_date` | `DateField("дата занятия по расписанию")` |
    +| `status` | `CharField("статус", max_length=10, choices=AttendanceStatus.choices)` |
    +- `Meta`: `ordering = ["original_date"]`; `UniqueConstraint(fields=["student", "weekly_lesson", "original_date"], name="academics_attendance_one_per_occurrence")`; `CheckConstraint(condition=Q(status__in=["present", "absent", "excused"]), name="academics_attendance_status")`; `Index(fields=["student", "original_date"], name="academics_att_student_date_idx")`.
    +- `__str__` → `f"{self.get_status_display()} — {self.weekly_lesson} ({self.original_date:%d.%m.%Y})"`.
    +- `clean()` — calls `validate_occurrence_for_student(student, weekly_lesson, original_date, today=timezone.localdate())` (6.1) and raises `ValidationError(errors)` if the list is non-empty. Duplicate (same student + occurrence): `validate_unique()` in `full_clean()` reports it (all three fields are in the admin form); `save_validated` also runs it. DB unique constraint is the last line.
    +
    +### 5.4 URLs (`academics/urls.py`, `app_name = "academics"`)
    +| Path | View | Name |
    +|---|---|---|
    +| `grades/` | `StudentGradesView` | `my_grades` |
    +| `grades/<slug:term_code>/` | `StudentGradesView` | `my_grades_term` |
    +| `staff/students/<int:pk>/grades/` | `StaffStudentGradesView` | `staff_student_grades` |
    +| `staff/students/<int:pk>/grades/<slug:term_code>/` | `StaffStudentGradesView` | `staff_student_grades_term` |
    +
    +`pk` = `StudentProfile.pk` (same as the existing staff student detail URL).
    +
    +### 5.5 Navigation and links
    +- `templates/base.html`: inside `{% if user.is_student %}` (the existing schedule item block) add after the schedule item: `<li><a href="{% url 'academics:my_grades' %}">Успеваемость</a></li>`.
    +- `accounts/templates/accounts/student_detail.html`: before the back link add `<p><a href="{% url 'academics:staff_student_grades' student.pk %}">Успеваемость и посещаемость</a></p>`.
    +
    +### 5.6 Admin (`academics/admin.py`)
    +Default `ModelForm`s (all fields). `TermAdmin` (`list_display = ("code", "name", "start_date", "end_date", "session_start", "session_end")`, `search_fields = ("code", "name")`); `CurriculumItemAdmin` (`list_display = ("discipline", "group", "term", "assessment_form", "credits")`, `list_filter = ("term", "group", "assessment_form")`, `list_select_related = ("discipline", "group", "term")`); `CurrentMarkAdmin` (`list_display = ("student", "curriculum_item", "value", "date", "kind")`, `list_filter = ("curriculum_item__term",)`, `readonly_fields = ("seed_key",)`, `list_select_related = ("student", "curriculum_item__discipline")`); `FinalResultAdmin` (`list_display = ("student", "curriculum_item", "attempt", "result", "date")`, `list_filter = ("curriculum_item__term", "result")`, `list_select_related`); `AttendanceAdmin` (`list_display = ("student", "weekly_lesson", "original_date", "status")`, `list_filter = ("status",)`, `date_hierarchy = "original_date"`, `list_select_related = ("student", "weekly_lesson__discipline")`). Search: `student__last_name` where a student FK exists.
    +
    +---
    +
    +## 6. Functions
    +
    +### 6.1 `academics/services.py` — validation helper
    +
    +```python
    +def validate_occurrence_for_student(student: StudentProfile | None, lesson: WeeklyLesson | None, original_date: date | None, today: date) -> list[str]
    +```
    +- Purpose: one place that decides whether an attendance record may reference this occurrence.
    +- Algorithm (return Russian messages; empty = OK):
    +  1. If any of `student`, `lesson`, `original_date` is `None` → `[]` (Django reports missing fields).
    +  2. `group_ids = set(lesson.groups.values_list("id", flat=True))`; `student.group_id not in group_ids` → `"Студент не относится к группам этого занятия."`.
    +  3. `original_date.weekday() != lesson.weekday` or not `lesson.valid_from <= original_date <= lesson.valid_until` → `"В эту дату этого занятия нет по расписанию."`; return immediately (later checks are meaningless).
    +  4. `change = LessonChange.objects.filter(weekly_lesson=lesson, original_date=original_date).first()`; `change` and `change.kind == CANCELLED` → `"Занятие отменено."`.
    +  5. `effective = change.new_date if change and change.kind == MOVED else original_date`; `effective > today` → `"Нельзя отметить посещение будущего занятия."`.
    +  6. Return the list.
    +- Tests: see section 7 (TP-M*).
    +
    +### 6.2 `academics/services.py` — read side
    +
    +Dataclasses (all `frozen=True`):
    +```python
    +class AttendanceSummary:
    +    present: int; absent: int; excused: int; unmarked: int
    +    @property marked -> int           # present + absent + excused
    +    @property percent -> int | None   # 4.3 rule
    +
    +class AttendanceEntry:
    +    date: date                 # displayed date (item.date)
    +    original_date: date
    +    lesson_type: str           # item.lesson.get_lesson_type_display()
    +    status: str | None         # AttendanceStatus value or None (unmarked)
    +    status_label: str          # Russian label or "не отмечено"
    +
    +class DisciplineReport:
    +    item: CurriculumItem
    +    marks: list[CurrentMark]
    +    attempts: list[FinalResult]        # ascending attempt
    +    effective: FinalResult | None
    +    is_debt: bool
    +    attendance: AttendanceSummary
    +    attendance_entries: list[AttendanceEntry]   # ascending date
    +
    +class TermReport:
    +    term: Term
    +    session_finished: bool
    +    disciplines: list[DisciplineReport]         # by discipline name
    +    average: Decimal | None
    +
    +class StudentOverview:
    +    debts: list[CurriculumItem]                 # across all terms, ordered by term start, discipline name
    +    status_text: str
    +    overall_average: Decimal | None
    +```
    +
    +Pure functions (no DB, no clock):
    +
    +#### `effective_results(results: Iterable[FinalResult]) -> dict[int, FinalResult]`
    +Key `curriculum_item_id` → result with max `attempt`. Tests: single attempt; retake (attempt 2 wins even if its `pk` is smaller); empty → `{}`.
    +
    +#### `average_grade(results: Iterable[FinalResult]) -> Decimal | None`
    +`values = [r.numeric_value for r in results if r.is_numeric]`; empty → `None`; else `(Decimal(sum(values)) / Decimal(len(values))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. Callers pass **effective** results only. Tests: `[5, 4, 4]` → `4.33`; `[5, 4]` → `4.50`; `[3, 4, 4, 4]`... use `[4, 5, 5]` → `4.67`; half-up case `[4, 5, 4, 5, 4, 5, 4, 4]` (`4.375`) → `4.38`; only pass/fail → `None`; includes `2`.
    +
    +#### `is_debt(item: CurriculumItem, effective: FinalResult | None, today: date) -> bool`
    +`today > item.term.session_end and (effective is None or not effective.is_positive)`. Tests: session not finished + missing → `False`; finished + missing → `True`; finished + `2` → `True`; finished + `fail` → `True`; finished + `3` → `False`; failing attempt 1 then positive attempt 2 → `False`; boundary `today == session_end` → `False`, `session_end + 1` → `True`.
    +
    +#### `status_text(debt_count: int) -> str`
    +`0` → `"Всё в порядке"`; else `f"Есть задолженности: {debt_count}"`.
    +
    +#### `summarize_attendance(occurrences: Iterable[ScheduleItem], records: Mapping[tuple[int, date], str], today: date) -> tuple[AttendanceSummary, list[AttendanceEntry]]`
    +- `occurrences`: happening items of one discipline (already filtered); `records`: `{(weekly_lesson_id, original_date): status}` of the student.
    +- Algorithm: for each item (sorted by `item.date`, `item.slot.number`): `key = (item.lesson.id, item.original_date)`; `status = records.get(key)`; if `status` → count it and add an entry; elif `item.date < today` → `unmarked += 1` and add an entry with `status=None`, label «не отмечено»; else (today/future, not marked) → skip. Build the summary.
    +- Tests: all present → 100; 3 present / 1 absent → 75; 2 present / 1 absent → 67 (half-up of 66.67); all excused → `percent None`, `marked == 3`; no records, 2 past → `unmarked 2`, `percent None`; future unmarked item not counted; today's marked item counted, today's unmarked not counted; record for a key not in `occurrences` is ignored.
    +
    +#### `current_term(today: date) -> Term | None`  (1 query)
    +`terms = list(Term.objects.all())`; return per 4.3 rule. Tests: inside; between terms → previous; before all terms → earliest; no terms → `None`.
    +
    +#### `student_terms(student: StudentProfile) -> list[Term]`  (1 query)
    +Terms having a curriculum item of the student's group, or a mark/result/attendance-free... exactly: `Term.objects.filter(Q(curriculum_items__group_id=student.group_id) | Q(curriculum_items__final_results__student=student) | Q(curriculum_items__current_marks__student=student)).distinct().order_by("-start_date")`.
    +
    +#### `student_term_report(student: StudentProfile, term: Term, today: date) -> TermReport`
    +Query budget: constant (≤ 9 queries including `occurrences_between`'s 4).
    +1. `items = list(CurriculumItem.objects.filter(term=term).filter(Q(group_id=student.group_id) | Q(final_results__student=student) | Q(current_marks__student=student)).distinct().select_related("discipline", "term", "group"))`.
    +2. `marks = list(CurrentMark.objects.filter(student=student, curriculum_item__term=term).order_by("date", "pk"))` → group by `curriculum_item_id`.
    +3. `results = list(FinalResult.objects.filter(student=student, curriculum_item__term=term).order_by("attempt"))` → group by item; `eff = effective_results(results)`.
    +4. Attendance: if `today < term.start_date` → no occurrences; else `end = min(term.end_date, today)`; `occ = [i for i in occurrences_between(term.start_date, end, [student.group_id]) if i.is_happening]`; `records = {(a.weekly_lesson_id, a.original_date): a.status for a in Attendance.objects.filter(student=student, original_date__range=(term.start_date - timedelta(days=366), term.end_date))}` (wide lower bound: a moved occurrence's `original_date` may lie before the term — keep it simple: filter by `student` and `weekly_lesson_id__in={i.lesson.id for i in occ}`) — **use the `weekly_lesson_id__in` filter**, not the date range.
    +5. For each item: `discipline_occ = [i for i in occ if i.lesson.discipline_id == item.discipline_id]`; `summary, entries = summarize_attendance(discipline_occ, records, today)`; `DisciplineReport(item, marks_by_item.get(item.id, []), results_by_item.get(item.id, []), eff.get(item.id), is_debt(item, eff.get(item.id), today), summary, entries)`.
    +6. Sort by `item.discipline.name`. `average = average_grade(eff.values())`. `session_finished = today > term.session_end`.
    +- Access: callers pass only a student they are allowed to see.
    +
    +#### `student_overview(student: StudentProfile, today: date) -> StudentOverview`  (2 queries)
    +1. `items = list(CurriculumItem.objects.filter(Q(group_id=student.group_id) | Q(final_results__student=student)).distinct().select_related("term", "discipline"))`.
    +2. `eff = effective_results(FinalResult.objects.filter(student=student))`.
    +3. `debts = [i for i in items if is_debt(i, eff.get(i.id), today)]`, sorted by `(i.term.start_date, i.discipline.name)`.
    +4. `overall_average = average_grade(eff.values())`; `status_text(len(debts))`.
    +
    +### 6.3 `academics/mutations.py`
    +```python
    +def save_validated(instance: models.Model) -> models.Model
    +```
    +`with transaction.atomic(): instance.full_clean(); instance.save(); return instance`. The only write path for `academics` models in code (seed, tests that test valid data).
    +
    +### 6.4 Views (`academics/views.py`)
    +
    +```python
    +class StudentGradesView(StudentRequiredMixin, TemplateView):
    +    template_name = "academics/report.html"
    +```
    +`get_context_data`: `today = timezone.localdate()`; `student = self.profile`; `context.update(_report_context(student, today, self.kwargs.get("term_code"), url_name="academics:my_grades_term", url_kwargs={}))`; `context["is_staff_view"] = False`.
    +
    +```python
    +class StaffStudentGradesView(StaffRequiredMixin, TemplateView):
    +    template_name = "academics/report.html"
    +```
    +`get_context_data`: `student = get_object_or_404(students_visible_to(self.request.user), pk=self.kwargs["pk"])`; same `_report_context(..., url_name="academics:staff_student_grades_term", url_kwargs={"pk": student.pk})`; `context["is_staff_view"] = True`; `context["student"] = student`; `context["back_url"] = reverse("accounts:staff_student_detail", args=[student.pk])`.
    +
    +```python
    +def _report_context(student: StudentProfile, today: date, term_code: str | None, url_name: str, url_kwargs: dict[str, Any]) -> dict[str, Any]
    +```
    +1. `terms = student_terms(student)`.
    +2. If `term_code`: `term = get_object_or_404(Term, code=term_code)` (any existing term is allowed; data is always filtered by `student`). Else `term = current_term(today)`.
    +3. `report = student_term_report(student, term, today) if term else None`.
    +4. Selector entries: for each `t` in `terms` (plus `term` if not in `terms`, ordered by `-start_date`): `{"term": t, "url": reverse(url_name, kwargs={**url_kwargs, "term_code": t.code}), "is_selected": t == term}`.
    +5. Return `{"overview": student_overview(student, today), "term": term, "report": report, "term_links": [...], "today": today}`.
    +
    +### 6.5 Templates
    +
    +`academics/report.html` (extends `base.html`):
    +```
    +<h1>{% if is_staff_view %}Успеваемость: {{ student.full_name }}{% else %}Моя успеваемость{% endif %}</h1>
    +{% if is_staff_view %}<p><a href="{{ back_url }}">← К карточке студента</a></p>{% endif %}
    +<p class="status {% if overview.debts %}status--debt{% else %}status--ok{% endif %}"><strong>{{ overview.status_text }}</strong></p>
    +{% if overview.debts %}<ul class="debt-list">{% for item in overview.debts %}<li>{{ item.discipline.name }} — {{ item.term.name }}</li>{% endfor %}</ul>{% endif %}
    +<p>Средний балл за всё время: {{ overview.overall_average|default:"—" }}</p>
    +{% if term_links %}<nav class="term-nav" aria-label="Семестры"><ul>{% for link in term_links %}<li>{% if link.is_selected %}<strong>{{ link.term.name }}</strong>{% else %}<a href="{{ link.url }}">{{ link.term.name }}</a>{% endif %}</li>{% endfor %}</ul></nav>{% endif %}
    +{% if not term %}<p>Семестров пока нет.</p>
    +{% else %}
    +  <h2>{{ term.name }}</h2>
    +  <p>Сессия: {{ term.session_start|date:"j E" }} — {{ term.session_end|date:"j E Y" }}{% if report.session_finished %} (завершена){% endif %}</p>
    +  <p>Средний балл за семестр: {{ report.average|default:"—" }}</p>
    +  {% if report.disciplines %}<ul class="discipline-list">{% for d in report.disciplines %}{% include "academics/includes/discipline.html" %}{% endfor %}</ul>
    +  {% else %}<p>За этот семестр данных нет.</p>{% endif %}
    +{% endif %}
    +```
    +`academics/includes/discipline.html` (expects `d`):
    +```
    +<li class="discipline{% if d.is_debt %} discipline--debt{% endif %}">
    +  <details>
    +    <summary>
    +      <strong>{{ d.item.discipline.name }}</strong> · {{ d.item.get_assessment_form_display }}
    +      · Итог: {% if d.effective %}{{ d.effective.get_result_display }}{% else %}нет{% endif %}
    +      {% if d.is_debt %}· <strong>Задолженность</strong>{% endif %}
    +      · Посещаемость: {% if d.attendance.percent is not None %}{{ d.attendance.percent }}%{% else %}—{% endif %}
    +    </summary>
    +    <h3>Текущие оценки</h3>
    +    {% if d.marks %}<ul>{% for m in d.marks %}<li>{{ m.date|date:"j E" }} — {{ m.kind }}: {{ m.value }}</li>{% endfor %}</ul>{% else %}<p>Оценок нет.</p>{% endif %}
    +    <h3>Итоговый результат</h3>
    +    {% if d.attempts %}<ul>{% for r in d.attempts %}<li>Попытка {{ r.attempt }}, {{ r.date|date:"j E Y" }}: {{ r.get_result_display }}{% if r == d.effective %} (действующий){% endif %}</li>{% endfor %}</ul>{% else %}<p>Результата пока нет.</p>{% endif %}
    +    <h3>Посещаемость</h3>
    +    <p>Присутствовал: {{ d.attendance.present }}, отсутствовал: {{ d.attendance.absent }}, по уважительной причине: {{ d.attendance.excused }}, не отмечено: {{ d.attendance.unmarked }}.</p>
    +    {% if d.attendance_entries %}<ul>{% for e in d.attendance_entries %}<li>{{ e.date|date:"j E" }} ({{ e.lesson_type }}) — {{ e.status_label }}</li>{% endfor %}</ul>{% endif %}
    +  </details>
    +</li>
    +```
    +(`r == d.effective` compares model instances by pk — fine.)
    +
    +CSS (`static/css/base.css`, tokens only, one declaration per line): `.discipline-list { list-style: none; padding: 0; }`, `.discipline { border-top: 1px solid var(--color-border); padding: var(--space-2) 0; }`, `.discipline--debt summary, .status--debt { color: var(--color-changed); }`, `.term-nav ul { display: flex; flex-wrap: wrap; gap: var(--space-3); list-style: none; padding: 0; }`, `details summary { cursor: pointer; }`.
    +
    +### 6.6 Demo data (`academics/demo.py`)
    +
    +```python
    +@dataclass(frozen=True)
    +class AcademicsSeedSummary:
    +    terms: int; curriculum_items: int; marks: int; results: int; attendance: int
    +
    +def term_bounds(day: date) -> tuple[str, str, date, date, date, date]
    +def seed_academics_demo(today: date) -> AcademicsSeedSummary
    +```
    +`term_bounds(day)` → `(code, name, start, end, session_start, session_end)`:
    +- `month >= 9` → autumn of `Y = day.year`; `month == 1` → autumn of `Y = day.year - 1`: `code=f"{Y}-autumn"`, `name=f"Осенний семестр {Y}/{Y + 1}"`, `start=date(Y, 9, 1)`, `end=date(Y + 1, 1, 31)`, session `date(Y + 1, 1, 10)`…`date(Y + 1, 1, 31)`.
    +- otherwise (Feb–Aug) → spring of `Y = day.year`: `code=f"{Y}-spring"`, `name=f"Весенний семестр {Y}"`, `start=date(Y, 2, 1)`, `end=date(Y, 8, 31)`, session `date(Y, 6, 1)`…`date(Y, 6, 30)`.
    +Terms tile the calendar without overlap. Tests: 2026-11-18 → `2026-autumn`; 2027-01-15 → `2026-autumn`; 2027-03-01 → `2027-spring`; `term_bounds(start - 1 day)` of autumn 2026 → `2026-spring`.
    +
    +Seed rule: **create missing rows, never update existing ones** (idempotent; data created in admin always survives). Every row goes through `save_validated`. Lookups:
    +- Terms: `Term.objects.filter(code=code).first()` or create.
    +- Disciplines (university reference data): `Di
    …[22,428 more characters truncated]
  ── Thought for 7s
    I'm tidying up the spec now. The average-tests example has a messy bit around the sample lists, the student_terms description has an unclear "exactly" phrasing, step 4 of the student_term_report needs its date-range sentence cleaned up before the weekly_lesson_id filter, and 6.6 needs its row-count wording clarified.

    I'm settling the 6.6 attendance range: I'll use cur.start through yesterday and skip it if that's empty, since occurrences_between already limits results to lesson validity. Next I'm checking the staff 403 on the unknown-term grades route, which the role check already covers, and confirming the TermBoundsTests reference. I'm also dropping the NullBooleanSelect note from the feasibility list, which doesn't apply here. The open question is assumption A1, which the protocol requires the Team lead to confirm before handoff, so I need to ask before passing this to the coder.

    Checking the remaining points on the spec: the 6.4 unknown-term lookup returns a 404 for staff, the `student_term_report` union with the distinct join holds up, and the `test_moved_to_past_allowed` case needs a free slot on Wednesday 11-11 before the move is valid. The "all excused" edge case still needs the Team lead's call on whether it counts as 0% or is excluded.

── Ran 1 command ───────────────────────────────────────────
  ── Ran python3 - <<'EOF' p="docs/tasks/TASK-005.md" s=open(p).read() reps=[ ("Tests: `[5, 4, 4]` → `4.33`; `[5, 4]` → `4.50`; `[3, 4, 4, 4]`... use `[4, 5, 5]` → `4.67`; half-up case","Tests: `[5, 4, 4]` → `4.33`; `[5, 4]` → `4.50`; `[4, 5, 5]` → `4.67`; half-up case"), ("Terms having a curriculum item of the student's group, or a mark/result/attendance-free... exactly: `Term","Terms with a curriculum item of the student's group or with the student's marks/results: `Term"), ("`records = {(a.weekly_lesson_id, a.original_date): a.status for a in Attendance.objects.filter(student=student, original_date__range=(term.start_date - timedelta(days=366), term.end_date))}` (wide lower bound: a moved occurrence's `original_date` may lie before the term — keep it simple: filter by `student` and `weekly_lesson_id__in={i.lesson.id for i in occ}`) — **use the `weekly_lesson_id__in` filter**, not the date range.","`records = {(a.weekly_lesson_id, a.original_date): a.status for a in Attendance.objects.filter(student=student, weekly_lesson_id__in={i.lesson.id for i in occ})}` (filter by lesson ids, not by date: a moved occurrence's `original_date` may lie outside the term)."), ("Return counts of rows **created in this run** is confusing — return counts of **rows that exist for the demo data** after the run: terms 2; curriculum items 17; results 13; marks and attendance = number of demo rows present.","Return the number of demo rows that exist after the run: terms 2; curriculum items 17; results 13; marks = rows with a `seed_key` starting with `m-{cur.code}-`; attendance = demo students' rows in `[cur.start, cur.end]`."), ("Attendance `cur`: for each demo student, `occ = [i for i in occurrences_between(max(cur.start, earliest lesson valid_from), today - 1 day, [group_id]) if i.is_happening]` (skip if the range is empty);","Attendance `cur`: for each demo student, if `today - 1 day >= cur.start`: `occ = [i for i in occurrences_between(cur.start, today - timedelta(days=1), [group_id]) if i.is_happening]` (lessons exist only inside their validity range, so earlier dates simply yield nothing);"), ("\n(Compute the start as `max(cur.start, today - timedelta(weeks=8))` — the schedule seed starts lessons 8 weeks before the run week.)\n","\n"), (", `<details>` (HTML), `ROUND_HALF_UP` (stdlib `decimal`), `django.forms.widgets.NullBooleanSelect` not needed. Verified",", `<details>` (HTML), `ROUND_HALF_UP` (stdlib `decimal`). Verified"), ("   - A2: demo terms are calendar-based (autumn 1 Sep–31 Jan, spring 1 Feb–31 Aug) so a current term always exists for any run date.\n",""), ] for a,b in reps:     assert a in s, a[:60]; s=s.replace(a,b) open(p,"w").write(s) EOF echo ok (1s)
    $ python3 - <<'EOF'
  p="docs/tasks/TASK-005.md"
  s=open(p).read()
  reps=[
  ("Tests: `[5, 4, 4]` → `4.33`; `[5, 4]` → `4.50`; `[3, 4, 4, 4]`... use `[4, 5, 5]` → `4.67`; half-up case","Tests: `[5, 4, 4]` → `4.33`; `[5, 4]` → `4.50`; `[4, 5, 5]` → `4.67`; half-up case"),
  ("Terms having a curriculum item of the student's group, or a mark/result/attendance-free... exactly: `Term","Terms with a curriculum item of the student's group or with the student's marks/results: `Term"),
  ("`records = {(a.weekly_lesson_id, a.original_date): a.status for a in Attendance.objects.filter(student=student, original_date__range=(term.start_date - timedelta(days=366), term.end_date))}` (wide lower bound: a moved occurrence's `original_date` may lie before the term — keep it simple: filter by `student` and `weekly_lesson_id__in={i.lesson.id for i in occ}`) — **use the `weekly_lesson_id__in` filter**, not the date range.","`records = {(a.weekly_lesson_id, a.original_date): a.status for a in Attendance.objects.filter(student=student, weekly_lesson_id__in={i.lesson.id for i in occ})}` (filter by lesson ids, not by date: a moved occurrence's `original_date` may lie outside the term)."),
  ("Return counts of rows **created in this run** is confusing — return counts of **rows that exist for the demo data** after the run: terms 2; curriculum items 17; results 13; marks and attendance = number of demo rows present.","Return the number of demo rows that exist after the run: terms 2; curriculum items 17; results 13; marks = rows with a `seed_key` starting with `m-{cur.code}-`; attendance = demo students' rows in `[cur.start, cur.end]`."),
  ("Attendance `cur`: for each demo student, `occ = [i for i in occurrences_between(max(cur.start, earliest lesson valid_from), today - 1 day, [group_id]) if i.is_happening]` (skip if the range is empty);","Attendance `cur`: for each demo student, if `today - 1 day >= cur.start`: `occ = [i for i in occurrences_between(cur.start, today - timedelta(days=1), [group_id]) if i.is_happening]` (lessons exist only inside their validity range, so earlier dates simply yield nothing);"),
  ("\n(Compute the start as `max(cur.start, today - timedelta(weeks=8))` — the schedule seed starts lessons 8 weeks before the run week.)\n","\n"),
  (", `<details>` (HTML), `ROUND_HALF_UP` (stdlib `decimal`), `django.forms.widgets.NullBooleanSelect` not needed. Verified",", `<details>` (HTML), `ROUND_HALF_UP` (stdlib `decimal`). Verified"),
  ("   - A2: demo terms are calendar-based (autumn 1 Sep–31 Jan, spring 1 Feb–31 Aug) so a current term always exists for any run date.\n",""),
  ]
  for a,b in reps:
      assert a in s, a[:60]; s=s.replace(a,b)
  open(p,"w").write(s)
  EOF
  echo ok
    ok
  ── Thought for 973ms
    I need to make sure the assumptions list is either empty or confirmed before this goes to the coder. I'll send a QUESTION to the lead and hold off on handing anything over until they answer.
  ── Thought for 6ms
    Спецификация готова, но одно толкование требования надо подтвердить у тимлида, а по новым правилам кодеру задачу передавать до этого нельзя. Сейчас отправляю ему вопрос.

── Ran bb thread tell thr_4izdzwetb4 --message-file - <<'EOF' [TASK-005] Planner -> Team lead: QUESTION Spec draft: docs/tasks/TASK-005.md (feasibility check done, section 8; baseline: 223 tests OK). One assumption blocks the hand-off (section 8, A1): The request says "attendance per discipline: present / marked occurrences". Taken literally, an excused absence lowers the percent (all excused -> 0%). I propose: percent = present / (present + absent); excused absences are counted and shown but excluded from the percent; all excused -> "—". All three counts plus "не отмечено" are shown either way. Options: 1. (recommended) Exclude excused from the percent, as in the draft. 2. Literal: present / (present + absent + excused); all excused -> 0%. The difference is one line in `AttendanceSummary.percent` and 2 tests. I will hand the spec to the Coder after your answer. EOF
  $ bb thread tell thr_4izdzwetb4 --message-file - <<'EOF'
[TASK-005] Planner -> Team lead: QUESTION
Spec draft: docs/tasks/TASK-005.md (feasibility check done, section 8; baseline: 223 tests OK). One assumption blocks the hand-off (section 8, A1):

The request says "attendance per discipline: present / marked occurrences". Taken literally, an excused absence lowers the percent (all excused -> 0%). I propose: percent = present / (present + absent); excused absences are counted and shown but excluded from the percent; all excused -> "—". All three counts plus "не отмечено" are shown either way.

Options:
1. (recommended) Exclude excused from the percent, as in the draft.
2. Literal: present / (present + absent + excused); all excused -> 0%.

The difference is one line in `AttendanceSummary.percent` and 2 tests. I will hand the spec to the Coder after your answer.
EOF
  Thread thr_4izdzwetb4 steered

── Assistant ───────────────────────────────────────────────
Спецификация TASK-005 написана: [docs/tasks/TASK-005.md](docs/tasks/TASK-005.md). Кодеру я её пока не передал: жду ответа тимлида на один вопрос.

**Вопрос.** В задаче процент посещаемости определён как «присутствовал / отмечено». Если читать буквально, пропуск по уважительной причине снижает процент: у студента, который все занятия пропустил по уважительной причине, будет 0%. Я предложил считать процент как «присутствовал / (присутствовал + отсутствовал)». Уважительные пропуски тогда видны в отдельном счётчике, но процент не портят. По новым правилам такое толкование должен подтвердить тимлид. Разница в коде — одна строка и два теста.

**Проверка выполнимости пройдена.** Не закоммичен только `plan.md` тимлида. Все функции, шаблоны, адреса и тестовые вспомогательные функции, на которые ссылается спецификация, существуют. Имя `academics` свободно. До начала работы проходят все 223 теста, `check`, `check --deploy`, ruff, проверка файла CI и `seed_demo`.

**Основные решения:**
- Новая часть проекта `academics`: семестры, учебный план группы, текущие оценки, итоговые результаты, посещаемость.
- Итоговый результат хранится в одном поле: 5/4/3/2 или «зачтено/не зачтено». Форма контроля определяет, какие значения допустимы.
- Пересдачи хранятся как номера попыток. Действует последняя попытка, история видна. Пересдавать после успешной попытки нельзя.
- Средний балл округляется до двух знаков; двойки входят в расчёт.
- Задолженность — это нет итога или итог неудовлетворительный, когда сессия уже закончилась.
- Отметку посещения нельзя поставить, если:
  - студент не из группы этого занятия;
  - занятия в эту дату нет по расписанию;
  - занятие отменено;
  - занятие ещё не прошло.
- Страница `/grades/`:
  - строка статуса и средний балл сверху;
  - ссылки на семестры;
  - по каждой дисциплине раскрывающийся блок `<details>` с оценками, попытками и посещениями по датам;
  - без JavaScript.
  Сотрудник открывает тот же отчёт из карточки студента своего факультета.
- Демо-данные:
  - `student1` — отличник;
  - `student3` — с пересдачей, открытой задолженностью и низкой посещаемостью;
  - `student2` — с другого факультета.
  Повторный запуск `seed_demo` только добавляет недостающие строки и не трогает данные, созданные в админке.
- Две правки расписания с регрессионными тестами:
  - у студента пропадёт пустая ссылка «К списку групп»;
  - исчезнет пробел перед точкой в «Отменено. Причина».

После ответа тимлида поправлю спецификацию, если он выберет другой вариант, и передам задачу кодеру.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-005] Team lead -> Planner: ANSWER
User decision on A1: option 1. Attendance percent = present / (present + absent). Excused absences are counted and shown but excluded from the percent; when there are no present/absent records (e.g. all excused) show "—". All counts (present, absent, excused, "не отмечено") are shown. Mark A1 as confirmed in section 8 and hand the spec to the Coder.

── Ran git status --short && python3 - <<'EOF' p="docs/tasks/TASK-005.md" s=open(p).read() old_start=s.index("   - A1: percent excludes excused absences") old_end=s.index("\n",old_start) s=s[:old_start]+"   - A1 (CONFIRMED by the Team lead / user, 2026-11-13): attendance percent = present / (present + absent); excused absences are counted and shown but excluded from the percent; no present/absent records (e.g. all excused) → \"—\". No open blockers."+s[old_end:] a="9. Conflicts — one requirement interpretation (not a conflict): \"attendance percentage = present / marked\". I exclude excused absences from the percent (4.3) so an excused absence does not lower attendance; all three counts are shown. Reported to the Team lead in the hand-off note." assert a in s s=s.replace(a,"9. Conflicts — one requirement interpretation (\"present / marked\") was escalated to the Team lead as A1 and confirmed: excused absences are excluded from the percent (4.3). No other conflicts.") open(p,"w").write(s) EOF grep -n "A1" docs/tasks/TASK-005.md (2s)
  $ git status --short && python3 - <<'EOF'
p="docs/tasks/TASK-005.md"
s=open(p).read()
old_start=s.index("   - A1: percent excludes excused absences")
old_end=s.index("\n",old_start)
s=s[:old_start]+"   - A1 (CONFIRMED by the Team lead / user, 2026-11-13): attendance percent = present / (present + absent); excused absences are counted and shown but excluded from the percent; no present/absent records (e.g. all excused) → \"—\". No open blockers."+s[old_end:]
a="9. Conflicts — one requirement interpretation (not a conflict): \"attendance percentage = present / marked\". I exclude excused absences from the percent (4.3) so an excused absence does not lower attendance; all three counts are shown. Reported to the Team lead in the hand-off note."
assert a in s
s=s.replace(a,"9. Conflicts — one requirement interpretation (\"present / marked\") was escalated to the Team lead as A1 and confirmed: excused absences are excluded from the percent (4.3). No other conflicts.")
open(p,"w").write(s)
EOF
grep -n "A1" docs/tasks/TASK-005.md
  M plan.md
  ?? docs/tasks/TASK-005.md
  558:9. Conflicts — one requirement interpretation ("present / marked") was escalated to the Team lead as A1 and confirmed: excused absences are excluded from the percent (4.3). No other conflicts.
  560:   - A1 (CONFIRMED by the Team lead / user, 2026-11-13): attendance percent = present / (present + absent); excused absences are counted and shown but excluded from the percent; no present/absent records (e.g. all excused) → "—". No open blockers.

── Ran bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-005] Planner -> Coder: TASK Spec: docs/tasks/TASK-005.md (approved by the Team lead; feasibility check in section 8, A1 confirmed). Summary: - New app `academics`: Term, CurriculumItem, CurrentMark, FinalResult (single `result` field, attempts = retakes, highest attempt is effective), Attendance (occurrence = weekly_lesson + original_date; present/absent/excused only). All rules in model `clean()` as NON-FIELD errors; code writes only via `academics/mutations.save_validated`. - Pure service functions in `academics/services.py` (effective results, average 2 decimals half-up incl. 2, debts after finished session, attendance percent = present/(present+absent), status line) + `student_term_report` / `student_overview` with constant query count. - Pages: `/grades/[<term_code>/]` for students, `/staff/students/<pk>/grades/[<term_code>/]` for staff via `students_visible_to`; `<details>` per discipline; nav "Успеваемость" for students; link from staff student card. - Seed: `academics/demo.py` creates only missing rows (never updates); calendar-based terms; data tables in 6.6. Plus two schedule template fixes (6.8) with regression tests that must fail before the fix. - Follow section 9 order and section 10 verification; full test plan in section 7 (access matrix 7.2). Do not delete db.sqlite3 or migrations. Do not commit. Questions -> me. EOF
  $ bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
[TASK-005] Planner -> Coder: TASK
Spec: docs/tasks/TASK-005.md (approved by the Team lead; feasibility check in section 8, A1 confirmed).
Summary:
- New app `academics`: Term, CurriculumItem, CurrentMark, FinalResult (single `result` field, attempts = retakes, highest attempt is effective), Attendance (occurrence = weekly_lesson + original_date; present/absent/excused only). All rules in model `clean()` as NON-FIELD errors; code writes only via `academics/mutations.save_validated`.
- Pure service functions in `academics/services.py` (effective results, average 2 decimals half-up incl. 2, debts after finished session, attendance percent = present/(present+absent), status line) + `student_term_report` / `student_overview` with constant query count.
- Pages: `/grades/[<term_code>/]` for students, `/staff/students/<pk>/grades/[<term_code>/]` for staff via `students_visible_to`; `<details>` per discipline; nav "Успеваемость" for students; link from staff student card.
- Seed: `academics/demo.py` creates only missing rows (never updates); calendar-based terms; data tables in 6.6. Plus two schedule template fixes (6.8) with regression tests that must fail before the fix.
- Follow section 9 order and section 10 verification; full test plan in section 7 (access matrix 7.2). Do not delete db.sqlite3 or migrations. Do not commit. Questions -> me.
EOF
  Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Вы выбрали вариант 1. Я отметил решение в [docs/tasks/TASK-005.md](docs/tasks/TASK-005.md) и передал спецификацию кодеру. Код ещё не написан, поэтому тестов по задаче пока нет.

Процент посещаемости будет считаться как «присутствовал / (присутствовал + отсутствовал)». Уважительные пропуски войдут в свой счётчик, но процент снижать не будут. Если у студента одни уважительные пропуски, вместо процента будет «—». Счётчики «присутствовал», «отсутствовал», «по уважительной причине» и «не отмечено» видны всегда.

Других открытых вопросов в спецификации нет.

── User ────────────────────────────────────────────────────
Тест, игнорируй сообщение

── Assistant ───────────────────────────────────────────────
Понял, ничего не делаю.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[SETUP] Team lead -> all: PROTOCOL UPDATE
Fix tasks now use IDs `TASK-NNN-FIX` (then `TASK-NNN-FIX2`, ...) with specs `docs/tasks/TASK-NNN-FIX.md` (see `.bb/AGENTS.md`, workflow step 1). They follow the normal workflow. Do not reply to this message.

── Thought for 7ms ─────────────────────────────────────────
  I'm not replying to the lead yet. I'll send the user a short note instead. I'm considering whether to check AGENTS.md, but a quick read isn't needed, so I'll just acknowledge.

── Assistant ───────────────────────────────────────────────
Понял новое правило. Задачи-исправления теперь получают номера `TASK-NNN-FIX`, затем `TASK-NNN-FIX2` и дальше. Спецификацию для них я пишу в `docs/tasks/TASK-NNN-FIX.md`. Работаю с ними по обычной схеме: проверка выполнимости, план тестов, передача кодеру. Тимлиду не отвечаю, он просил не отвечать.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-005-FIX] Team lead -> Planner: TASK
Approved by the user. Write the spec `docs/tasks/TASK-005-FIX.md` and hand it to the Coder.

## Context
Fix task for small defects found during TASK-004 and TASK-005 reviews (see `docs/tasks/TASK-004.md`, `docs/tasks/TASK-005.md` section 11, and the Reviewer's notes quoted below). No new features. Every fix is minimal, at model/service level (never only in admin forms), and has a regression test that fails without the fix. Apply your "Feasibility check" and "Test plan" sections.

## Items to fix
1. Deleting a LessonChange is not validated (TASK-004 review).
   Reproduced by the Reviewer: lesson A is CANCELLED on a date; lesson B is MOVED into A's freed room/slot; the cancellation is deleted in admin -> two happening occurrences in the same room and slot (and possibly the same group).
   Fix: a service function that deletes a LessonChange only if restoring the original occurrence (and removing the moved/room-changed target) causes no group/room conflict; it uses the same locking order as `schedule/locking.py` and returns a clear error otherwise. The admin must use it for single delete (`delete_model`) AND for the bulk "delete selected" action (`delete_queryset` or disable the bulk action for this model). Invalid delete -> admin error message, nothing deleted, never 500.

2. Attendance of a later-cancelled occurrence is silently ignored (TASK-005 section 11).
   Fix: saving a CANCELLED LessonChange for an occurrence that already has Attendance records is rejected with a clear validation error ("есть отметки посещения"). Same for a MOVED change only if the identity rule would hide existing records (check; moved lessons keep their identity, so probably only CANCELLED is affected - confirm in the feasibility check).

3. Flaky test around local midnight (seen once by the Coder, not reproduced).
   Note: the project time zone is Europe/Moscow while the development machine runs in another time zone, so Moscow midnight falls in the local afternoon. No test calls the real clock directly (grep for `timezone.now()`, `timezone.localdate()`, `date.today()`, `datetime.now(` in tests is empty), so the likely cause is application code (views, model `clean()`, services, seed) calling the real clock while the test mocks the clock in another module, or a test building dates relative to the real current date indirectly.
   Fix: find every place where code under test reads the clock, make the tests control it consistently (single patch point or an injected `today`), and add a test that runs the affected code with the clock set to 23:59:59 and 00:00:00 Europe/Moscow.

## Accepted limitations (do NOT fix; document only)
- After a student moves to another group, attendance for the former group's lessons is not shown. Group transfers are out of scope for the prototype.
- `seed_demo` never updates existing academic rows. This is intended: it must not overwrite data edited in admin. Re-running it adds missing rows (new past occurrences), so a daily run on the server keeps the demo fresh (the Team lead adds this to the deployment checklist).
Add both to README "Known limitations" (create the section if missing).

## Out of scope
New features, visual theme, deployment.

## Verification
All existing verification commands pass (check, deploy check, makemigrations --check, test, ruff, CI YAML), `seed_demo` twice without errors.

── Ran 5 commands, explored 3 searches, 1 file, created 1 file
  ── Thought for 8ms
    I'm first checking the state of things: whether TASK-005 is committed, then looking at the schedule admin, mutations, locking, validation, and the attendance models, along with any tests that depend on clocks.
  ── Ran git log --oneline | head -4 && git status --short && cat schedule/admin.py schedule/mutations.py schedule/locking.py && sed -n '/^class LessonChange/,$p' schedule/models.py | grep -n "def clean" -A 70 | head -90 (3s)
    $ git log --oneline | head -4 && git status --short && cat schedule/admin.py schedule/mutations.py schedule/locking.py && sed -n '/^class LessonChange/,$p' schedule/models.py | grep -n "def clean" -A 70 | head -90
    3aa61bf Team protocol: fix cycle instead of deferred tech debt
    3378cbc TASK-005: grades and attendance
    e7aa72a Team protocol: planner test plan and feasibility check
    c5e2174 TASK-004: tech debt from reviews
     M plan.md
    from django.contrib import admin

    from .forms import WeeklyLessonAdminForm
    from .models import LessonChange, WeeklyLesson


    @admin.register(WeeklyLesson)
    class WeeklyLessonAdmin(admin.ModelAdmin):
        form = WeeklyLessonAdminForm
        list_display = (
            "weekday",
            "slot",
            "discipline",
            "lesson_type",
            "teacher",
            "room",
            "group_names",
            "valid_from",
            "valid_until",
        )
        list_filter = ("weekday", "lesson_type", "groups")
        filter_horizontal = ("groups",)
        list_select_related = ("discipline", "teacher", "room")
        readonly_fields = ("seed_key",)

        def get_queryset(self, request):
            return super().get_queryset(request).prefetch_related("groups")

        @admin.display(description="группы")
        def group_names(self, obj):
            return ", ".join(g.name for g in obj.groups.all())


    @admin.register(LessonChange)
    class LessonChangeAdmin(admin.ModelAdmin):
        list_display = (
            "original_date",
            "kind",
            "weekly_lesson",
            "new_date",
            "new_slot",
            "new_room",
            "new_teacher",
            "reason",
        )
        list_filter = ("kind",)
        date_hierarchy = "original_date"
        list_select_related = ("weekly_lesson__discipline", "new_room", "new_teacher")
        readonly_fields = ("seed_key",)
    """The only write path for schedule models in application code."""

    from collections.abc import Sequence

    from django.core.exceptions import ValidationError
    from django.db import transaction

    from university.models import StudyGroup

    from .models import LessonChange, WeeklyLesson
    from .validation import validate_weekly_lesson


    def save_weekly_lesson(lesson: WeeklyLesson, groups: Sequence[StudyGroup]) -> WeeklyLesson:
        with transaction.atomic():
            lesson.full_clean()
            errors = validate_weekly_lesson(
                weekday=lesson.weekday,
                slot=lesson.slot,
                valid_from=lesson.valid_from,
                valid_until=lesson.valid_until,
                room_id=lesson.room_id,
                group_ids=[g.pk for g in groups],
                exclude_pk=lesson.pk,
            )
            if errors:
                raise ValidationError(errors)
            lesson.save()
            lesson.groups.set(groups)
            return lesson


    def save_lesson_change(change: LessonChange) -> LessonChange:
        with transaction.atomic():
            change.full_clean()
            change.save()
            return change
    """Serialize schedule writes by locking the rooms and groups they touch.

    Any two conflicting lessons/changes share a room or a group, so locking those
    rows makes the second writer wait until the first commits; its conflict queries
    then see the committed data (PostgreSQL READ COMMITTED takes a new snapshot per
    statement). On SQLite Django ignores ``select_for_update()`` (no ``FOR UPDATE``
    support); SQLite serializes writers with a database-level lock anyway.
    """

    from collections.abc import Iterable

    from django.db import transaction

    from university.models import Room, StudyGroup


    def lock_rooms_and_groups(room_ids: Iterable[int | None], group_ids: Iterable[int]) -> None:
        if not transaction.get_connection().in_atomic_block:
            return
        rooms = sorted({r for r in room_ids if r is not None})
        groups = sorted(set(group_ids))
        if rooms:
            list(
                Room.objects.select_for_update()
                .filter(pk__in=rooms)
                .order_by("pk")
                .values_list("pk", flat=True)
            )
        if groups:
            list(
                StudyGroup.objects.select_for_update()
                .filter(pk__in=groups)
                .order_by("pk")
                .values_list("pk", flat=True)
            )
    99:    def clean(self):
    100-        super().clean()
    101-        if self.weekly_lesson_id is None or self.original_date is None or not self.kind:
    102-            return
    103-        lesson = self.weekly_lesson
    104-        errors: dict[str, list[str]] = {}
    105-        if self.original_date.weekday() != lesson.weekday:
    106-            errors.setdefault("original_date", []).append(
    107-                "Дата не совпадает с днём недели занятия."
    108-            )
    109-        if not lesson.valid_from <= self.original_date <= lesson.valid_until:
    110-            errors.setdefault("original_date", []).append("Дата вне периода действия занятия.")
    111-
    112-        # Kind rules (mirror of the DB constraint, field-level messages).
    113-        required = {
    114-            ChangeKind.MOVED: ("new_date", "new_slot"),
    115-            ChangeKind.ROOM_CHANGED: ("new_room",),
    116-            ChangeKind.TEACHER_REPLACED: ("new_teacher",),
    117-        }
    118-        for field in required.get(self.kind, ()):
    119-            if getattr(self, field) is None:
    120-                errors.setdefault(field, []).append("Обязательно для этого вида изменения.")
    121-
    122-        forbidden = {
    123-            ChangeKind.CANCELLED: ("new_date", "new_slot", "new_room", "new_teacher"),
    124-            ChangeKind.MOVED: ("new_teacher",),
    125-            ChangeKind.ROOM_CHANGED: ("new_date", "new_slot", "new_teacher"),
    126-            ChangeKind.TEACHER_REPLACED: ("new_date", "new_slot", "new_room"),
    127-        }
    128-        for field in forbidden.get(self.kind, ()):
    129-            if getattr(self, field) is not None:
    130-                errors.setdefault(field, []).append("Не заполняйте для этого вида изменения.")
    131-
    132-        if self.kind == ChangeKind.MOVED:
    133-            if (self.new_date, self.new_slot) == (self.original_date, lesson.slot) and (
    134-                self.new_room is None or self.new_room_id == lesson.room_id
    135-            ):
    136-                errors.setdefault("new_date", []).append("Новое время совпадает со старым.")
    137-        elif self.kind == ChangeKind.ROOM_CHANGED:
    138-            if self.new_room_id == lesson.room_id:
    139-                errors.setdefault("new_room", []).append("Аудитория не изменилась.")
    140-        elif self.kind == ChangeKind.TEACHER_REPLACED:
    141-            if self.new_teacher_id == lesson.teacher_id:
    142-                errors.setdefault("new_teacher", []).append("Преподаватель не изменился.")
    143-
    144-        if errors:
    145-            raise ValidationError(errors)
    146-
    147-        from .validation import change_conflicts
    148-
    149-        conflicts = change_conflicts(self)
    150-        if conflicts:
    151-            raise ValidationError(conflicts)
  ── Thought for 32s
    I'm checking the attendance validation in the academics app, where an occurrence is rejected if its move's effective date is in the future. I also need to confirm that a move recorded after attendance still keeps the same occurrence identity, keyed by lesson and original date.

    I'm checking whether a MOVED change with a new date in the future hides an occurrence that already has attendance, since the term-range filter would drop the moved-in item. Recording attendance and then moving the lesson to a date that hasn't happened yet looks contradictory, so I'm considering rejecting any MOVED or CANCELLED change on an occurrence that already has attendance.

    I'm settling on the rule for MOVED changes: since a moved occurrence with existing attendance can drop out of the visible range when its new date is in the future or outside the term, I'll reject MOVED on any occurrence that already has attendance, keeping it consistent with CANCELLED. Deleting a MOVED change is safe because the records still line up with the original past date, and a cancelled occurrence can't hold attendance anyway. One risk I'll note but leave out of scope is changing a weekly lesson's weekday or range, which could orphan existing attendance.

    I'm weighing a way for schedule to check attendance without importing academics, since academics already depends on schedule. One option is a registry of change guards that academics fills in at startup. Another is reaching attendance through the reverse relation on the weekly lesson, which avoids an import but couples the two apps by name.

    I'm moving on to deleting a lesson change: I need to check that once the change is removed, the original occurrence fits back into its slot without clashing with another item, so I'm planning to lock the affected rooms and groups and simulate the restored state before deleting.

    I'm working out how to check that deleting a lesson change won't clash with anything when the original occurrence is restored: cancelled occurrences reappear, moved ones return to their original date, and room changes revert to the lesson's own room. Teacher replacements need no check, since teacher conflicts aren't validated. I'm starting to sketch a helper that computes these restored-occurrence conflicts for a given change.

    I'm working out the conflict check for restoring the original occurrence: it would clash if another happening item sits in the same slot on that date and shares the room or a group, ignoring the occurrence itself. The deletion would then run inside a transaction, lock the affected rooms and groups, and raise a validation error if conflicts are found before removing the change.

    I'm looking at the admin side: deleting through the admin would log the deletion and show a success message even if the conflict check raises, so I need to handle the error differently there.

    I'm weighing how to handle a delete that fails validation in the admin: the plan is to wrap the POST delete in a transaction, catch the validation error outside it so the rollback also drops the log entry, and show an error message instead of a success one.

    I'm checking how the admin delete view handles a failed validation: the plan is to wrap the POST in an outer transaction so that a rollback also drops the log entry, then show an error message and redirect to the change page instead of a success message.

    I'm handling the bulk delete action for this model by removing it from the admin actions, since a failed conflict check there would leave a 500 error or a misleading success message. Deleting a weekly lesson can also cascade into its changes, so I'm considering how that path should be treated.

    I'm thinking through the seed script now: it bulk-deletes demo changes and then recreates them, so restored occurrences could briefly clash with admin-made changes that took over a slot freed by a demo cancellation. I'm checking whether the lesson validation run on save would catch that case.

    I'm checking the seed script's revalidation path: after the demo changes are bulk-deleted, re-saving each demo lesson should run the occurrence conflict check against admin-made moves that took over freed slots, which would surface as a ValidationError. Then I'm going to grep for where the code reads the clock and how tests mock it.
  ── Searched for timezone\.\(now\|localdate\|localtime\)\|date\.today\|datetime\.now\|datetime\.today in config
  ── Thought for 26s
    I'm checking where the clock-dependent flakiness could come from: the time functions are patched correctly, but some academics tests may create marks, results, or attendance through save_validated without the mock in place. Since clean compares against localdate for the future-date check, that could be the source, especially in setUpTestData helpers outside the patch.

    I'm checking the real-date comparisons in the seed path: seed_demo takes localdate() once, then Attendance.clean reads it again, and a midnight crossing in that direction shouldn't cause a failure. The more likely mismatch is a test computing its expected "current week" from a different "today" than the seed used, if the two calls straddle midnight.

    I'm checking whether tests that read the real clock without mocking could be the flake source. The seed path takes the date once and the attendance clean reads it again, but a midnight crossing there only makes the check less strict, so it can't cause a failure. Tests don't seem to compute their own "today," so the remaining suspect is code that reads the clock twice in one flow.

    I'm checking whether the seed path could flake: it takes the date once, and Attendance.validation reads the clock again, but a midnight crossing there only makes the check less strict, so it can't cause a failure. The remaining candidates are tests or views that read the real clock in more than one place within a single flow.

    I'm looking for tests that read the real clock without mocking, especially ones that call views or seed commands with fixed dates, since the code under test still reads the current date. I'm also checking whether a midnight crossing could make the test's expected date differ from what the seed computed.

    I'm weighing a fix that centralizes time access in one clock module, so tests could patch a single point instead of relying on the scattered patches around django.utils.timezone.

    I'm considering whether the flake could come from unpatched tests that run clock-dependent code, since the patch on timezone.now already covers every app call, so a single patch point exists. I'm thinking about which tests hit those paths without mocking, and whether a fixed fixture date versus the real date could explain a midnight-dependent failure.

    I'm going to run the whole test suite under a fixed fake "now" at a few instants, including one just before Moscow midnight and one far in the future, so any test that silently depends on the real date will fail and reveal itself. I'll write a small runner script in a temp directory to do that.

    I'm going to run the suite under a global fake "now" by starting a patch in a runner script before the Django test runner, since any test that silently depends on the real date would then surface.
  ── Thought for 3ms
    Все чтения времени идут через django.utils.timezone, и тесты подменяют именно его, так что нестабильность, скорее всего, в тестах, которые часы не подменяют. Сейчас прогоню весь набор с часами, выставленными на 23:59:59 и 00:00:00 по Москве и на далёкую дату.
  ── Ran mkdir -p "$TMPDIR/clk" && cat > "$TMPDIR/clk/run_at.py" <<'EOF' import os, sys from datetime import datetime from unittest import mock from zoneinfo import ZoneInfo sys.path.insert(0, "~/hackatonproject") os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings") import django when = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=ZoneInfo("Europe/Moscow")) p = mock.patch("django.utils.timezone.now", return_value=when) p.start() django.setup() from django.conf import settings from django.test.utils import get_runner r = get_runner(settings)(verbosity=0, parallel=0) sys.exit(bool(r.run_tests([]))) EOF cd ~/hackatonproject && source .venv/bin/activate && for t in "2026-11-13T23:59:59" "2026-11-14T00:00:00" "2027-03-01T12:00:00"; do echo "== $t"; DEBUG=true python "$TMPDIR/clk/run_at.py" "$t" 2>&1 | grep -E "^(FAIL|ERROR):|^Ran|^OK|^FAILED" | head -20; done (3m 40s)
    $ mkdir -p "$TMPDIR/clk" && cat > "$TMPDIR/clk/run_at.py" <<'EOF'
  import os, sys
  from datetime import datetime
  from unittest import mock
  from zoneinfo import ZoneInfo
  sys.path.insert(0, "~/hackatonproject")
  os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
  import django
  when = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=ZoneInfo("Europe/Moscow"))
  p = mock.patch("django.utils.timezone.now", return_value=when)
  p.start()
  django.setup()
  from django.conf import settings
  from django.test.utils import get_runner
  r = get_runner(settings)(verbosity=0, parallel=0)
  sys.exit(bool(r.run_tests([])))
  EOF
  cd ~/hackatonproject && source .venv/bin/activate && for t in "2026-11-13T23:59:59" "2026-11-14T00:00:00" "2027-03-01T12:00:00"; do echo "== $t"; DEBUG=true python "$TMPDIR/clk/run_at.py" "$t" 2>&1 | grep -E "^(FAIL|ERROR):|^Ran|^OK|^FAILED" | head -20; done
    == 2026-11-13T23:59:59
    Ran 364 tests in 73.524s
    OK
    == 2026-11-14T00:00:00
    Ran 364 tests in 72.323s
    OK
    == 2027-03-01T12:00:00
    FAIL: test_week_shows_only_own_group (schedule.tests.test_views.ScheduleViewsTests.test_week_shows_only_own_group)
    Ran 364 tests in 70.174s
    FAILED (failures=1)
  ── Thought for 3s
    I've found that test_week_shows_only_own_group relies on the real date because it hits the default week without a patch. That doesn't explain the midnight flake, though, so I'm checking whether some test reads the unpatched clock twice and could straddle midnight, like a seed step that grabs today and a later view that grabs it again.

    I'm checking the seed path next: the seed takes today's date once, and the attendance and marks checks read the clock again, so I'm working through whether a midnight crossing could break those comparisons. Then I'll scan the other tests for schedule and grades URLs hit without a patch.
  ── Thought
    Тест `test_week_shows_only_own_group` использует реальную текущую дату без подмены часов и падает на далёких датах. Сейчас проверю, нет ли других мест с зависимостью от времени без подмены.
  ── Searched for def test_week_shows_only_own_group in schedule/tests/test_views.py
  ── Thought for 16s
    I'm checking whether `_get` is already patched at line 61, which looks fine. Next is the `accounts` demo seed test, which runs unpatched with the real date: the schedule seed and the academics seed both take the same `today` from line 24, and the attendance validation uses the real local date, so it should pass.

    I'm checking whether the midnight-straddle scenario could break the seed: the clock moving from day D to D+1 mid-seed doesn't seem to cause a failure, since the attendance and mark validations hold either way. The schedule seed's LessonChange clean has no clock dependency, so that's fine too. I'm now looking at other midnight-sensitive candidates, especially fixtures in `setUpTestData` that might read the real date.

    I'm wondering whether the flaky failure depends on the real date, since some fixtures may only be valid up to a certain day. I can't reproduce it, so my plan is to find every place that reads the clock and make the tests control it consistently, then add a test that runs at the boundary dates.

    I'm checking where the timezone gets resolved, since `aware()` uses Moscow time while `date.today()` doesn't appear anywhere. If the seed reads `today` once and `clean()` reads the clock again, a midnight crossing would only make validation less strict, never more, because time only moves forward.

    I'm grepping the tests for naive `datetime(...)` values that might get passed into models, since `timezone.now` is the only clock the models should see. Next I want to freeze the suite at Sunday 23:59:59 and Monday 00:00, because a week boundary could break things differently than a plain midnight does.

    I'm going to run the suite frozen at Monday 00:00 and at the jury window dates around late November, to see whether anything depends on the real date.
  ── Ran source .venv/bin/activate && for t in "2026-11-15T23:59:59" "2026-11-16T00:00:00" "2026-11-28T12:00:00" "2026-12-31T23:59:59" "2027-01-01T00:00:00"; do echo "== $t"; DEBUG=true python "$TMPDIR/clk/run_at.py" "$t" 2>&1 | grep -E "^(FAIL|ERROR):|^Ran|^OK|^FAILED" | head -20; done; grep -rn "datetime(20" --include='test_*.py' accounts schedule academics core | grep -v "tzinfo\|aware" | head (5m 58s)
    $ source .venv/bin/activate && for t in "2026-11-15T23:59:59" "2026-11-16T00:00:00" "2026-11-28T12:00:00" "2026-12-31T23:59:59" "2027-01-01T00:00:00"; do echo "== $t"; DEBUG=true python "$TMPDIR/clk/run_at.py" "$t" 2>&1 | grep -E "^(FAIL|ERROR):|^Ran|^OK|^FAILED" | head -20; done; grep -rn "datetime(20" --include='test_*.py' accounts schedule academics core | grep -v "tzinfo\|aware" | head
    == 2026-11-15T23:59:59
    Ran 364 tests in 73.077s
    OK
    == 2026-11-16T00:00:00
    Ran 364 tests in 70.928s
    OK
    == 2026-11-28T12:00:00
    Ran 364 tests in 69.882s
    OK
    == 2026-12-31T23:59:59
    Ran 364 tests in 69.509s
    OK
    == 2027-01-01T00:00:00
    Ran 364 tests in 70.006s
    OK
  ── Thought for 6s
    The 2027-01-01 date passes but 2027-03-01 fails, so the lesson holds only through 2026-12-31. On 2027-01-01 the week still starts Monday 2026-12-28, which covers the same days, so that's fine. Frozen clocks don't show any midnight dependency, so the flake is probably a clock reading taken on either side of midnight in a test that isn't patched. I'm checking the accounts tests that read the clock in their fixtures or bodies.

    I'm going to find which tests read the real clock implicitly, by running the suite with a global patch that records the calling test whenever the clock is read outside an inner patch. I'll filter the stack down to our app code so Django's own login and session reads don't clutter the results.
  ── Thought for 5ms
    С замороженными часами тесты на границах дня, недели и года проходят, так что сбой возникает только при реальной полуночи во время прогона. Ищу тесты, которые читают реальные часы без подмены.
  ── Ran cat > "$TMPDIR/clk/trace.py" <<'EOF' import os, sys, traceback from collections import defaultdict from unittest import mock sys.path.insert(0, "~/hackatonproject") os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings") import django from django.utils import timezone as tz real_now = tz.now hits = defaultdict(set) APP = ("/accounts/", "/schedule/", "/academics/", "/university/", "/core/") def fake():     st = traceback.extract_stack()[:-1]     test = next((f"{os.path.relpath(f.filename,'~/hackatonproject')}::{f.name}" for f in st if "/tests/" in f.filename and f.name.startswith(("test_","setUp"))), None)     app = [f for f in st if any(a in f.filename for a in APP) and "/tests/" not in f.filename and ".venv" not in f.filename]     if test and app:         a = app[-1]         hits[test].add(f"{os.path.relpath(a.filename,'~/hackatonproject')}:{a.lineno}")     return real_now() p = mock.patch("django.utils.timezone.now", side_effect=fake); p.start() django.setup() from django.conf import settings from django.test.utils import get_runner get_runner(settings)(verbosity=0, parallel=0).run_tests([]) for t in sorted(hits): print(t, "->", ", ".join(sorted(hits[t]))) EOF cd ~/hackatonproject && source .venv/bin/activate && DEBUG=true python "$TMPDIR/clk/trace.py" 2>/dev/null | grep -- "->" | grep -v "accounts/forms.py" | head -60 (1m 13s)
    $ cat > "$TMPDIR/clk/trace.py" <<'EOF'
  import os, sys, traceback
  from collections import defaultdict
  from unittest import mock
  sys.path.insert(0, "~/hackatonproject")
  os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
  import django
  from django.utils import timezone as tz
  real_now = tz.now
  hits = defaultdict(set)
  APP = ("/accounts/", "/schedule/", "/academics/", "/university/", "/core/")
  def fake():
      st = traceback.extract_stack()[:-1]
      test = next((f"{os.path.relpath(f.filename,'~/hackatonproject')}::{f.name}" for f in st if "/tests/" in f.filename and f.name.startswith(("test_","setUp"))), None)
      app = [f for f in st if any(a in f.filename for a in APP) and "/tests/" not in f.filename and ".venv" not in f.filename]
      if test and app:
          a = app[-1]
          hits[test].add(f"{os.path.relpath(a.filename,'~/hackatonproject')}:{a.lineno}")
      return real_now()
  p = mock.patch("django.utils.timezone.now", side_effect=fake); p.start()
  django.setup()
  from django.conf import settings
  from django.test.utils import get_runner
  get_runner(settings)(verbosity=0, parallel=0).run_tests([])
  for t in sorted(hits): print(t, "->", ", ".join(sorted(hits[t])))
  EOF
  cd ~/hackatonproject && source .venv/bin/activate && DEBUG=true python "$TMPDIR/clk/trace.py" 2>/dev/null | grep -- "->" | grep -v "accounts/forms.py" | head -60
    academics/tests/test_demo.py::test_admin_rows_survive -> academics/models.py:177, accounts/demo.py:138
    academics/tests/test_demo.py::test_attendance_only_past_and_valid -> accounts/demo.py:138
    academics/tests/test_demo.py::test_command_output -> accounts/demo.py:138
    academics/tests/test_demo.py::test_counts -> accounts/demo.py:138
    academics/tests/test_demo.py::test_idempotent -> accounts/demo.py:138
    academics/tests/test_demo.py::test_page_renders_weeks_after_seed -> accounts/demo.py:138
    academics/tests/test_demo.py::test_rerun_later_adds_only_new_rows -> accounts/demo.py:138
    academics/tests/test_demo.py::test_retake_present -> accounts/demo.py:138
    academics/tests/test_demo.py::test_students_differ -> accounts/demo.py:138
    academics/tests/test_models.py::test_attempt_2_without_1_rejected -> academics/models.py:254
    academics/tests/test_models.py::test_cancelled_rejected -> schedule/mutations.py:36
    academics/tests/test_models.py::test_duplicate_attempt_rejected -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_models.py::test_moved_to_future_rejected -> schedule/mutations.py:36
    academics/tests/test_models.py::test_moved_to_past_allowed -> schedule/mutations.py:36
    academics/tests/test_models.py::test_numeric_on_graded_credit_allowed -> academics/models.py:254
    academics/tests/test_models.py::test_positive_earlier_attempt_with_later_attempt_rejected -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_models.py::test_retake_after_fail_allowed -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_models.py::test_retake_after_positive_rejected -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_models.py::test_retake_earlier_date_rejected -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_models.py::test_value_range_rejected -> academics/models.py:177
    academics/tests/test_services.py::test_marks_and_attempts_attached -> academics/models.py:177, academics/models.py:254, academics/mutations.py:9
    academics/tests/test_services.py::test_only_pass_fail_average_none -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_services.py::test_overall_average_across_terms -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_services.py::test_retake_clears_debt -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_views.py::setUpTestData -> academics/models.py:177, academics/models.py:254, academics/mutations.py:9
    academics/tests/test_views.py::test_admin_attendance_cancelled_shows_error -> academics/models.py:321, schedule/mutations.py:36
    academics/tests/test_views.py::test_admin_attendance_without_lesson_shows_error -> academics/models.py:321
    academics/tests/test_views.py::test_admin_attendance_without_student_shows_error -> academics/models.py:321
    academics/tests/test_views.py::test_debt_marked -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_views.py::test_retake_history_shown -> academics/models.py:254, academics/mutations.py:9
    academics/tests/test_views.py::test_staff_page_constant_queries -> academics/models.py:177, academics/models.py:254, academics/mutations.py:9
    academics/tests/test_views.py::test_student_page_constant_queries -> academics/models.py:177, academics/models.py:254, academics/mutations.py:9
    accounts/tests/test_admin.py::test_admin_user_add_form_has_role -> accounts/admin.py:17
    accounts/tests/test_admin.py::test_admin_user_add_without_role_shows_error -> accounts/admin.py:17
    accounts/tests/test_seed_demo.py::test_conflicting_existing_user_fails -> accounts/management/commands/seed_demo.py:24
    accounts/tests/test_seed_demo.py::test_creates_expected_data -> academics/models.py:177, academics/models.py:254, academics/models.py:321, academics/mutations.py:9, accounts/demo.py:138, accounts/management/commands/seed_demo.py:24, schedule/mutations.py:36
    accounts/tests/test_seed_demo.py::test_idempotent -> academics/models.py:177, academics/models.py:254, academics/models.py:321, academics/mutations.py:9, accounts/demo.py:138, accounts/management/commands/seed_demo.py:24, schedule/mutations.py:36
    accounts/tests/test_seed_demo.py::test_password_not_printed -> academics/models.py:177, academics/models.py:254, academics/models.py:321, academics/mutations.py:9, accounts/demo.py:138, accounts/management/commands/seed_demo.py:24, schedule/mutations.py:36
    accounts/tests/test_seed_demo.py::test_passwords_hashed -> academics/models.py:177, academics/models.py:254, academics/models.py:321, academics/mutations.py:9, accounts/demo.py:138, accounts/management/commands/seed_demo.py:24, schedule/mutations.py:36
    accounts/tests/test_seed_demo.py::test_record_number_collision_fails_cleanly -> accounts/management/commands/seed_demo.py:24
    accounts/tests/test_seed_demo.py::test_weak_password_fails -> accounts/demo.py:138, accounts/management/commands/seed_demo.py:24
    schedule/tests/test_demo.py::test_change_dates_in_current_and_next_week -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo.py::test_command_output_and_idempotency -> accounts/demo.py:138
    schedule/tests/test_demo.py::test_counts -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo.py::test_far_date_renders_without_reseed -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo.py::test_idempotent -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo.py::test_rerun_later_refreshes_changes -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo.py::test_rerun_months_later_refreshes_changes -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo.py::test_seeded_schedule_has_no_conflicts -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo_marker.py::test_admin_change_survives_reseed -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo_marker.py::test_admin_lesson_with_same_old_key_survives_reseed -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo_marker.py::test_data_migration_marks_legacy_rows -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo_marker.py::test_reseed_after_migration_no_duplicates -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_demo_marker.py::test_seed_marks_rows -> accounts/demo.py:138, schedule/mutations.py:36
    schedule/tests/test_locking.py::test_change_locks_target_room -> schedule/mutations.py:36
    schedule/tests/test_revalidation.py::test_admin_form_reports_revalidation_error -> schedule/mutations.py:36
    schedule/tests/test_revalidation.py::test_cancelled_own_occurrence_frees_date -> schedule/mutations.py:36
    schedule/tests/test_revalidation.py::test_group_change_hits_moved_in_group -> schedule/mutations.py:36
    schedule/tests/test_revalidation.py::test_message_limit -> schedule/mutations.py:36
    schedule/tests/test_revalidation.py::test_new_lesson_where_other_was_moved_in -> schedule/mutations.py:36
  ── Thought for 32s
    I'm checking which of these timestamps actually matter. Most are auto-filled `created_at` or `date_joined` fields and are harmless, but the future-date checks in academics/models.py, the today-check for attendance, and the seed_demo.py line are the ones worth looking at. Next I'll move on to the unpatched tests.

    I'm working through the FinalResult tests in academics, which compare result dates against the local date in Moscow. Fixed dates near the current date could pass or fail depending on the time of day, since Moscow can roll past midnight before the local machine does. That timing mismatch looks like the source of the flaky behavior.

    I'm going to make the clock-dependent tests use a frozen clock, since the clock patch point is already single and the gap is that some tests never patch it. I'll check which dates the unpatched FinalResult tests and the test_views setup use, though the fix is the same either way: every test that reaches clock-dependent code needs to control the clock.

    I'm planning a frozen-clock base class that patches the timezone now() for whole test classes, including setUpTestData, so every clock-dependent check sees a fixed date. I'm also considering a boundary test that runs the FinalResult, CurrentMark, and Attendance checks at 23:59:59 and 00:00:00 Moscow time to confirm they respect the local date.

    I'm also adding a boundary test that runs the FinalResult, CurrentMark, and Attendance checks at 23:59:59 and 00:00:00 Moscow time, and a check that TodayView shows day D at the first and day D+1 at the second. Separately, test_week_shows_only_own_group also depends on the real date, so I'll wrap it in the frozen clock too.

    I'm sketching a small mixin for the clock that lives in core/testing.py rather than a tests package, so other apps can import it. It will hold a fixed Moscow time as a class attribute and patch the timezone now() for the whole class.

    I'm wiring up a mixin that freezes the clock for the whole test class, starting the patch in setUpClass before setUpTestData runs and stopping it in tearDownClass. It needs to come first in the MRO so it wraps TestCase, and any inner patches a test adds will still take precedence.

    I'm deciding which test classes should get the frozen clock: the ones that touch the model date checks, the seed script, and the views that use the local date. I'll list the classes in academics, the schedule view and demo tests, and the accounts seed test rather than hand-picking a fragile subset. I also want a check that runs the suite at a few fixed instants to confirm nothing still depends on the real clock.

    I'm adding a verification step that runs the suite at fixed instants through a small helper script, to catch any test that still depends on the real clock. I'll also add boundary tests around midnight Moscow time for the date checks and the today view.

    I'm writing the boundary tests for the Moscow midnight cases: marks and final results dated today should validate at 00:00:00 but be rejected at 23:59:59 the day before, and the same split applies to attendance, with the today view switching days at midnight.

    I'm adding boundary tests for Moscow midnight: a mark or final result dated today should pass at 00:00:00 but fail at 23:59:59 the day before, and attendance should follow the same split. I'll also check the today view's day switch at midnight, the grades-page count for unmarked lessons, and that the seed script runs cleanly at both instants. To confirm the logic doesn't depend on the machine's timezone, I'll repeat the today-view check with the process TZ set to America/Los_Angeles.

    I'm checking whether the clock-dependent tests hold up across the midnight boundary in Moscow time. The suite passes at several instants near midnight but fails at 2027-03-01, which points to `test_week_shows_only_own_group` depending on the real date. The future-date checks in the models are the likely source of the flakiness, since they compare fixed fixture dates against the current Moscow date.

    I'm checking whether the fixture dates in the academics tests were set to match the date when they were written, since that would explain why the future-date checks fail at certain times. I'll grep for the hardcoded 2026-11 dates in test_models.py and test_services.py to confirm.
  ── Searched for ^class \|TODAY\|NOW =\|date(2026, 11, 1[0-9]) in academics/tests/test_views.py
  ── Thought for 59s
    I'm checking the FinalResult tests, which read the clock unpatched at models.py:254 while their fixture dates are 2026-11-18. If the real date falls before that, an unpatched validation of those dates would fail, and the trace points that way.

    Checking the academics app config so I can register the new guard in its ready() hook. The guard plan is a small registry in schedule/guards.py, with LessonChange.clean running the guards after field checks and combining their messages with the conflict errors.

    I'm working out how the guard should treat MOVED changes: it would block an admin re-saving an existing moved change if attendance was marked on a past date, so I'm checking when those records would actually be hidden.

    I'm working out the MOVED case: a moved lesson is only hidden when its new date falls after today, so the guard should reject it then if attendance is already marked. A move into a past date with attendance stays visible under its own term, so I'll let that through.

    I'm settling the MOVED rule: block it only when attendance exists and the new date is still in the future. Moving a lesson into the past keeps its record visible, so that case stays allowed. CANCELLED is always rejected when records exist, and the clock check will use timezone.localdate() to match how Attendance reads the date.

    I'm considering whether the delete path needs a guard too: a MOVED change with attendance whose original date is still in the future would hide those records once removed, so it might be rejected the same way. I'm also planning to check the admin's delete view, where the delete model method would need to run the guards.

    I'm wrapping up the admin delete path: the delete_view override will catch the ValidationError, show its messages as an error, and send the user back to the change page. I'm still deciding the exact redirect target, since the object id is already a string and reverse needs care with it.

    I'm checking whether the admin delete path needs the same guard handling. Bulk delete actions should be removed so that only the single-object delete goes through the guards, and I'm also considering whether deleting a WeeklyLesson cascades to its changes in a way that would bypass them.

    I'm checking the seed path next: it bulk-deletes demo changes with queryset.delete(), which skips the service, so I'm confirming that re-saving the demo lesson afterward still catches any conflicts against the admin occurrences.

    I'm checking the seed path for a later rerun: the demo cancellation would be recreated against attendance that was never recorded for that occurrence, so the guard should pass.

    I'm checking the seed's MOVED case for a rerun later in the same week: the change gets deleted, and I need to see whether attendance for that lesson's original occurrence would already be recorded at that moment.

    I'm checking the seed's later-week rerun for the Friday-to-Monday move: the attendance it depends on would only exist for a past occurrence, so the guard should pass there too.

    I'm checking the Sunday-to-Monday case: a lesson moved from Fri W+1 to Mon W+2 would only have attendance if Fri W+1 had already passed and been marked, which a run on Sat W+1 would not have done yet, so the guard should pass on a rerun.

    I'm going back over the seed's same-week rerun case: a cancellation or move created on an earlier run would only collide with attendance if that occurrence had already passed and been marked, and I'm checking whether any previous run could have done that before the rerun.

    I'm checking the seed's reruns at a few offsets, D, D+2, D+7 and D+9, to confirm none of them fail. The guard could still block the seed in an odd case, so it should raise a clear CommandError if it does. I also need to record in the README's known limitations section that the moved-change rule is only safe because of how the seed schedules its changes.

    I'm moving on to the test plan: the admin delete view is reachable only by superusers, which existing tests already cover, so I'll note that rather than add new access cases. The remaining work is how to apply the frozen-clock mixin across the test classes that save validated data, starting with where the mixin lives in core/testing.py.

    I'm going through the test classes next: the demo and revalidation suites, plus the seed-demo tests, all of which run on the frozen clock, and planning to wrap every TestCase in academics, schedule and the seed tests with the mixin at 2026-11-18 12:00 unless a class sets its own time.

    I'm planning a script that runs the test suite at four fixed instants, including a far-future and a past date, to confirm nothing depends on the real clock. I'm also weighing a CI step at 2027-03-01, since it's cheap and would catch date-dependent regressions.

    I'm working through the test cases for the delete path: one where a cancellation on Monday 23 blocks deleting it when a move frees the slot into a room that's already in use, and a variant where the same group is moved into that slot. In both I expect the delete to be rejected with a ValidationError naming the room, with the cancellation still in place.

    I'm working through the remaining delete-path cases: a room-change cancellation that frees a slot another change takes, the same for a moved lesson, and checking that the allowed deletes still go through. I'm also planning a locking check that wraps the room and group lock call.

    I'm laying out the delete-path tests: rooms and groups locked on delete, the admin delete view rejecting conflicting deletes with an error message and a redirect, and the bulk delete action being absent.

    I'm writing out the admin-side cases next: cancelling a lesson that already has attendance gets rejected with a message, while one without attendance goes through. Moves into the future with attendance are blocked, and moves into the past are allowed with the attendance still visible in the report. Room changes and teacher replacements are allowed even with attendance, and I'm also checking that editing the reason on an existing past move still works.

    I'm checking the academics app config next, to see whether it has a ready() hook where the guard can be registered, and confirming that schedule/guards.py is free to hold the new registry. I'm also planning a test that the guard list includes the academics guard once the apps load.
  ── Thought for 5ms
    Причина найдена: часы читаются через `django.utils.timezone`, но часть тестов сверяет фиксированные даты с реальной московской датой. Дальше проверю пару имён и напишу спецификацию.
  ── Read academics/apps.py
  ── Created docs/tasks/TASK-005-FIX.md +334
    --- /dev/null
    +++ b~/hackatonproject/docs/tasks/TASK-005-FIX.md
    +# TASK-005-FIX: change deletion, attendance vs changes, real-clock test dependency
    +
    +Author: Planner. Status: ready for implementation.
    +Base commit: `3aa61bf`. Related specs: `docs/tasks/TASK-003.md`, `TASK-004.md`, `TASK-005.md`.
    +
    +No new features. Every fix is minimal, at model/service level, and has a regression test that fails without the fix.
    +
    +---
    +
    +## 1. Goal and acceptance criteria
    +
    +| ID | Criterion |
    +|---|---|
    +| AC1 | Deleting a `LessonChange` goes through `schedule.mutations.delete_lesson_change`, which locks (same order as `schedule/locking.py`) and rejects the delete if the restored original occurrence would collide with another happening occurrence in the same room or with a shared group. |
    +| AC2 | Admin single delete uses the service; an invalid delete shows an admin error message, deletes nothing, never 500. The bulk "delete selected" action is removed for `LessonChange`. |
    +| AC3 | A `LessonChange` cannot be saved (created or edited) as CANCELLED for an occurrence with attendance records, nor as MOVED to a date after today for such an occurrence. Deleting a MOVED change is rejected if it would return an occurrence with attendance records to a future date. Clear non-field error mentioning «отметки посещения». |
    +| AC4 | `schedule` still does not import `academics`: the attendance rule is registered by `academics` through a guard registry in `schedule`. |
    +| AC5 | Every test class that runs clock-dependent code freezes the clock for the whole class (including `setUpTestData`). The full suite passes with the global clock frozen at Moscow 23:59:59, 00:00:00 and at dates far from today. |
    +| AC6 | New tests run the clock-dependent code at 23:59:59 and 00:00:00 Europe/Moscow and prove the result does not depend on the machine time zone. |
    +| AC7 | README has a "Known limitations" section with the two accepted limitations. |
    +
    +## 2. Out of scope
    +New features, visual theme, deployment, teacher-conflict validation, group transfers, changes to `seed_demo` behaviour (it keeps its bulk delete of demo changes; see Risks).
    +
    +---
    +
    +## 3. Findings (root causes)
    +
    +### 3.1 Item 1 — deletion is not validated
    +`schedule/admin.py` `LessonChangeAdmin` uses Django's default delete (single and bulk). `schedule/mutations.py` has no delete function. Removing a CANCELLED / ROOM_CHANGED / MOVED change "restores" the original occurrence at `(original_date, lesson.slot, lesson.room)` without any conflict check. Removing a TEACHER_REPLACED change cannot create a group/room conflict (teacher conflicts are out of scope). Removing a moved-in target never creates a conflict (it only frees a slot).
    +
    +### 3.2 Item 2 — which change kinds hide attendance
    +`academics.services.student_term_report` builds attendance from `occurrences_between(term.start_date, min(term.end_date, today), [group])`, keeps only `is_happening` items and matches records by `(weekly_lesson_id, original_date)`. Therefore:
    +- **CANCELLED**: the occurrence is not happening → records are hidden. **Affected.**
    +- **MOVED** to `new_date <= today`: the MOVED_IN item keeps the identity `(lesson, original_date)` and is inside the range → records stay visible. **Not affected.**
    +- **MOVED** to `new_date > today`: the MOVED_IN item is outside the range (`end = today`) and MOVED_OUT is not happening → records are hidden. **Affected.** (It is also inconsistent: the occurrence has not happened yet, but attendance exists. `validate_occurrence_for_student` already rejects marking such an occurrence.)
    +- **ROOM_CHANGED / TEACHER_REPLACED**: still happening, same identity → not affected.
    +- **Deleting a MOVED change** whose `original_date > today` while records exist → the occurrence returns to a future date → records hidden. **Affected** (same rule, delete path).
    +- Deleting a CANCELLED change cannot hide records (a cancelled occurrence cannot have records).
    +
    +### 3.3 Item 3 — clock in tests
    +- All application code reads the clock through `django.utils.timezone` (`timezone.now/localdate/localtime`): `accounts/forms.py:23`, `accounts/management/commands/seed_demo.py:24`, `schedule/views.py:27,42,65`, `academics/views.py:21,42`, `academics/models.py:177` (`CurrentMark` future-date check), `:254` (`FinalResult` future-date check), `:321` (`Attendance.clean` → `today`). Tests patch `django.utils.timezone.now`, which `localdate/localtime` call internally — so the patch point is already single. `aware()` builds Moscow-aware datetimes, so the machine time zone is irrelevant **when the clock is patched**.
    +- The problem is tests that do **not** patch the clock while running that code. A tracing run (global wrapper around `timezone.now` recording the calling test) found unpatched clock reads in: `academics/tests/test_models.py` (`FinalResultModelTests`, `CurrentMarkModelTests`, `AttendanceModelTests` via `setUpTestData`/helpers), `academics/tests/test_services.py` (`StudentTermReportTests`, `StudentOverviewTests`), `academics/tests/test_views.py` (`AccessFixture.setUpTestData`, admin tests), `academics/tests/test_demo.py`, `accounts/tests/test_seed_demo.py` (whole `seed_demo` on the real date), `schedule/tests/test_views.py` (`test_week_shows_only_own_group` uses `/schedule/week/` = real current week), `schedule/tests/test_demo.py`, `schedule/tests/test_demo_marker.py`. (Other hits are `auto_now_add` timestamps — harmless.)
    +- These tests validate **fixed** dates (e.g. 2026-11-16..18) against the **real Moscow date**. Their result depends on when they run: before the Moscow date reaches the fixture date they fail ("дата в будущем"); Moscow midnight falls in the local afternoon, which matches the observed flake. Reproduction: running the full suite with the global clock frozen at `2027-03-01 12:00 MSK` fails `schedule.tests.test_views.ScheduleViewsTests.test_week_shows_only_own_group` (lessons valid only until 2026-12-31). Frozen at 2026-11-13 23:59:59, 2026-11-14 00:00:00, 2026-11-15 23:59:59, 2026-11-16 00:00:00, 2026-11-28 12:00, 2026-12-31 23:59:59 and 2027-01-01 00:00:00 the suite passes (364 tests).
    +- Fix: freeze the clock per test class (one mixin), and add a CI step that runs the suite with a frozen far-future clock, so any new real-clock dependency fails deterministically.
    +
    +---
    +
    +## 4. Architecture
    +
    +### 4.1 Files
    +Create:
    +```
    +schedule/guards.py
    +core/testing.py
    +scripts/run_tests_at.py
    +schedule/tests/test_change_delete.py
    +academics/tests/test_change_guard.py
    +academics/tests/test_clock_boundaries.py
    +```
    +Change:
    +```
    +schedule/models.py (LessonChange.clean), schedule/mutations.py, schedule/admin.py,
    +academics/apps.py, academics/services.py (new guard function),
    +.github/workflows/ci.yml, README.md,
    +test classes listed in 5.4 (add the mixin only; no other test edits except 5.4 item 3)
    +```
    +No migrations (no model field changes). No new dependencies. No new env variables.
    +
    +---
    +
    +## 5. Functions
    +
    +### 5.1 `schedule/guards.py` — change guard registry (AC4)
    +```python
    +ChangeGuard = Callable[["LessonChange", bool], list[str]]   # (change, deleting) -> messages
    +
    +_guards: list[ChangeGuard] = []
    +
    +def register_change_guard(guard: ChangeGuard) -> None
    +def run_change_guards(change: LessonChange, *, deleting: bool) -> list[str]
    +```
    +- `register_change_guard`: append if not already present (idempotent; `ready()` may run more than once in tests).
    +- `run_change_guards`: concatenate `guard(change, deleting)` results of all registered guards, in registration order.
    +- Purpose: lets apps that depend on `schedule` (e.g. `academics`) veto schedule changes without `schedule` importing them.
    +- Tests (in `academics/tests/test_change_guard.py`): `test_academics_guard_registered` (`attendance_change_guard in guards._guards`); `test_register_is_idempotent` (register twice → present once; remove the test guard in `finally`).
    +
    +### 5.2 `LessonChange.clean()` change (`schedule/models.py`)
    +After the existing `if errors: raise ValidationError(errors)` and **before** `change_conflicts`:
    +```python
    +from .guards import run_change_guards
    +guard_errors = run_change_guards(self, deleting=False)
    +if guard_errors:
    +    raise ValidationError(guard_errors)
    +```
    +(Non-field errors. Keep the existing conflict check after it.)
    +
    +### 5.3 `academics/services.py` + `academics/apps.py` — attendance guard (AC3)
    +```python
    +def attendance_change_guard(change: LessonChange, deleting: bool) -> list[str]
    +```
    +- Algorithm:
    +  1. If `change.weekly_lesson_id is None` or `change.original_date is None` → `[]`.
    +  2. `count = Attendance.objects.filter(weekly_lesson_id=change.weekly_lesson_id, original_date=change.original_date).count()`; `count == 0` → `[]`.
    +  3. `today = timezone.localdate()`; `d = f"{change.original_date:%d.%m.%Y}"`.
    +  4. Not deleting:
    +     - `kind == CANCELLED` → `[f"Нельзя отменить занятие {d}: есть отметки посещения ({count}). Сначала удалите их."]`;
    +     - `kind == MOVED` and `change.new_date is not None and change.new_date > today` → `[f"Нельзя перенести занятие {d} на будущую дату: есть отметки посещения ({count}). Сначала удалите их."]`.
    +  5. Deleting: `kind == MOVED` and `change.original_date > today` → `[f"Нельзя удалить перенос занятия {d}: занятие вернётся на будущую дату, а отметки посещения ({count}) уже есть. Сначала удалите их."]`.
    +  6. Otherwise `[]`.
    +- `AcademicsConfig.ready()`: `from schedule.guards import register_change_guard`; `from .services import attendance_change_guard`; `register_change_guard(attendance_change_guard)`.
    +
    +### 5.4 `schedule/mutations.py` — delete service (AC1)
    +```python
    +def delete_lesson_change(change: LessonChange) -> None
    +```
    +- Algorithm:
    +  1. `with transaction.atomic():`
    +  2. `errors = restored_occurrence_conflicts(change) + run_change_guards(change, deleting=True)`.
    +  3. If `errors` → `raise ValidationError(errors)`.
    +  4. `change.delete()`.
    +
    +Put the helper in `schedule/validation.py` next to `change_conflicts`:
    +```python
    +def restored_occurrence_conflicts(change: LessonChange) -> list[str]
    +```
    +- Purpose: conflicts that appear when `change` is removed and its original occurrence becomes regular again.
    +- Algorithm:
    +  1. If `change.kind == TEACHER_REPLACED` → `[]`.
    +  2. `lesson = change.weekly_lesson`; `group_ids = set(lesson.groups.values_list("id", flat=True))`.
    +  3. `locking.lock_rooms_and_groups([lesson.room_id], group_ids)` (same helper and order as other writes).
    +  4. `items = occurrences_between(change.original_date, change.original_date, None)`.
    +  5. For each `item` with `item.is_happening` and `item.slot.number == lesson.slot`, **skip** the same occurrence (`item.lesson.id == lesson.id and item.original_date == change.original_date`):
    +     - `item.room.id == lesson.room_id` → `f"Нельзя удалить изменение: {change.original_date:%d.%m.%Y}, {lesson.slot} пара, аудитория {item.room.number} уже занята ({item.lesson.discipline.name})."`;
    +     - each group of `item.lesson.groups.all()` with id in `group_ids` → `f"Нельзя удалить изменение: {change.original_date:%d.%m.%Y}, {lesson.slot} пара, группа {g.name} уже занята ({item.lesson.discipline.name})."`.
    +  6. Return the list.
    +- Note: the moved-in/room-changed target of the change disappears with it; removing an occurrence never creates a conflict, so only the restored original is checked.
    +
    +### 5.5 Admin (`schedule/admin.py`, AC2)
    +In `LessonChangeAdmin`:
    +```python
    +def get_actions(self, request):
    +    actions = super().get_actions(request)
    +    actions.pop("delete_selected", None)
    +    return actions
    +
    +def delete_model(self, request, obj):
    +    delete_lesson_change(obj)
    +
    +def delete_view(self, request, object_id, extra_context=None):
    +    try:
    +        with transaction.atomic():
    +            return super().delete_view(request, object_id, extra_context)
    +    except ValidationError as exc:
    +        self.message_user(request, " ".join(exc.messages), level=messages.ERROR)
    +        return HttpResponseRedirect(reverse("admin:schedule_lessonchange_change", args=[object_id]))
    +```
    +`super().delete_view` already runs in a transaction; the outer `atomic` makes the deletion log entry roll back together with the failed delete. Imports: `django.contrib.messages`, `django.core.exceptions.ValidationError`, `django.db.transaction`, `django.http.HttpResponseRedirect`, `django.urls.reverse`, `.mutations.delete_lesson_change`.
    +Cascade deletes (deleting a `WeeklyLesson` deletes its changes) are unchanged: removing a whole lesson removes occurrences and cannot create conflicts; lessons with attendance are protected (`on_delete=PROTECT`).
    +
    +### 5.6 `core/testing.py` — frozen clock for test classes (AC5)
    +```python
    +MOSCOW = ZoneInfo("Europe/Moscow")
    +
    +def moscow(dt_str: str) -> datetime        # "2026-11-18 12:00" -> aware Moscow datetime
    +
    +class FrozenClockMixin:
    +    frozen_now: ClassVar[str] = "2026-11-18 12:00"
    +
    +    @classmethod
    +    def setUpClass(cls) -> None
    +    @classmethod
    +    def tearDownClass(cls) -> None
    +```
    +- `setUpClass`: `cls._clock_patcher = mock.patch("django.utils.timezone.now", return_value=moscow(cls.frozen_now))`; `cls._clock_patcher.start()`; then `try: super().setUpClass()` / `except Exception: cls._clock_patcher.stop(); raise` (so `setUpTestData` runs with the frozen clock).
    +- `tearDownClass`: `try: super().tearDownClass()` / `finally: cls._clock_patcher.stop()`.
    +- Must be listed **before** `TestCase`/`SimpleTestCase` in the bases. Inner `mock.patch("django.utils.timezone.now", ...)` in single tests keeps working (it overrides and then restores the class-level mock).
    +- `core/testing.py` is a plain module (not a test module); it imports only `unittest.mock`, `datetime`, `zoneinfo`, `typing`.
    +
    +Apply the mixin (only add it to the bases; keep `frozen_now` default unless a class's own mocks need another value) to these classes:
    +1. `academics/tests/test_models.py`: `ModelFixture` (base of all model test classes).
    +2. `academics/tests/test_services.py`: every `TestCase` class (not the `SimpleTestCase` ones).
    +3. `academics/tests/test_views.py`: `AccessFixture`. `academics/tests/test_demo.py`: `AcademicsDemoTests`.
    +4. `accounts/tests/test_seed_demo.py`: `SeedDemoTests`.
    +5. `schedule/tests/test_views.py`: `ScheduleViewsTests`, `ChangeRenderingTests`, `ScheduleUiFixTests`. `test_week_shows_only_own_group` then renders the week of 2026-11-18 (inside the fixture lessons' validity) — no other edit needed.
    +6. `schedule/tests/test_demo.py`: `ScheduleDemoTests`; `schedule/tests/test_demo_marker.py`: `DemoMarkerTests`; `schedule/tests/test_revalidation.py`, `test_locking.py`, `test_validation.py`, `test_services.py`: every `TestCase` class.
    +7. New test classes in this task.
    +`academics/tests/test_models.py` may keep its existing `_clock()` helper; it becomes redundant but harmless.
    +
    +### 5.7 `scripts/run_tests_at.py` — whole-suite frozen-clock run
    +Usage: `python scripts/run_tests_at.py 2027-03-01T12:00:00 [test labels...]`. Algorithm:
    +1. Insert the repo root (parent of `scripts/`) into `sys.path`; `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")`.
    +2. Parse `sys.argv[1]` with `datetime.fromisoformat`, attach `ZoneInfo("Europe/Moscow")`.
    +3. `mock.patch("django.utils.timezone.now", return_value=when).start()` **before** `django.setup()`.
    +4. `django.setup()`; run `get_runner(settings)(verbosity=1).run_tests(sys.argv[2:])`; `sys.exit(1 if failures else 0)`.
    +Docstring: "Runs the test suite with the clock frozen at a Moscow time. Tests must not depend on the real current date."
    +
    +CI (`.github/workflows/ci.yml`), after the `Tests` step:
    +```yaml
    +      - name: Tests with a frozen far-future clock
    +        run: python scripts/run_tests_at.py 2027-03-01T12:00:00
    +```
    +
    +### 5.8 README — "Known limitations" (AC7)
    +Create section `## Known limitations` before "Environment variables":
    +- After a student moves to another group, attendance for the former group's lessons is not shown (group transfers are out of scope for the prototype).
    +- `seed_demo` never updates existing academic rows, so data edited in the admin is never overwritten. Re-running it only adds missing rows (new past occurrences); run it daily on the server to keep the demo fresh.
    +Also add to "Test & lint": `python scripts/run_tests_at.py 2027-03-01T12:00:00` with one line: "tests must not depend on the real date".
    +
    +---
    +
    +## 6. Test plan
    +
    +Clock for all new tests: `FrozenClockMixin` with `frozen_now = "2026-11-18 12:00"` (Wednesday) unless stated. Reference: Monday 2026-11-16, next Monday 2026-11-23. Lessons valid `2026-09-01..2026-12-31`. Build data with `accounts/tests/helpers.py`, `schedule/tests/helpers.py`, `academics/tests/helpers.py`; changes via `save_lesson_change`. Never use `seed_demo` data (except the seed boundary test, which tests the seed).
    +
    +### 6.1 Traceability
    +| AC | Tests |
    +|---|---|
    +| AC1 | `schedule/tests/test_change_delete.py::DeleteLessonChangeTests.*` |
    +| AC2 | `schedule/tests/test_change_delete.py::DeleteLessonChangeAdminTests.*` |
    +| AC3 | `academics/tests/test_change_guard.py::AttendanceChangeGuardTests.*` |
    +| AC4 | `academics/tests/test_change_guard.py::GuardRegistryTests.*`, plus `grep -rn "academics" schedule/*.py` → empty (verification) |
    +| AC5 | full suite + `scripts/run_tests_at.py` runs (section 8) |
    +| AC6 | `academics/tests/test_clock_boundaries.py::MoscowMidnightTests.*` |
    +| AC7 | manual check of README (Reviewer) |
    +
    +### 6.2 Access matrix
    +Only the admin delete view changes. Admin access is unchanged (superuser only; covered by `accounts/tests/test_admin.py`). Cells: superuser → tests in 6.3 `DeleteLessonChangeAdminTests`; student/staff/anonymous → existing admin tests (redirect to admin login) — `test_non_superuser_cannot_delete_change` added: student and staff POST to the delete URL → 302 to admin login, change still exists. No new non-admin views.
    +
    +### 6.3 `schedule/tests/test_change_delete.py`
    +`DeleteLessonChangeTests(FrozenClockMixin, TestCase)` — fixture: groups G1, G2, G3; rooms R1..R6; L_A (G1, R1, Mon s2).
    +1. `test_reviewer_scenario_room_conflict_rejected` — CANCEL L_A on 2026-11-23; L_B (G2, R2, Tue s1) MOVED from 2026-11-17 to 2026-11-23 s2 with `new_room=R1`; `delete_lesson_change(cancel)` → `ValidationError` mentioning «аудитория 1» (R1 number) and «23.11.2026»; the cancel still exists.
    +2. `test_group_conflict_rejected` — CANCEL L_A on 23.11; L_C (G1, R3, Tue s1) MOVED to 23.11 s2 (own room R3) → delete cancel → error mentions group G1.
    +3. `test_room_changed_restore_conflict_rejected` — L_A ROOM_CHANGED on 23.11 to R5; L_D (G3, R6, Mon s2) ROOM_CHANGED on 23.11 to R1 → delete L_A's room change → error (R1).
    +4. `test_moved_restore_conflict_rejected` — L_A MOVED from 23.11 to Wed 25.11 s4; L_E (G2, R4, Tue s1) MOVED from 17.11 to 23.11 s2 with `new_room=R1` → delete L_A's move → error.
    +5. `test_delete_without_conflict_allowed` — CANCEL L_A on 23.11, nothing else → deleted.
    +6. `test_delete_teacher_replacement_always_allowed` — even when another lesson occupies R1 that day via a move (no check for this kind) → deleted.
    +7. `test_delete_moved_in_target_never_conflicts` — delete L_B's MOVED change from test 1 (the moved-in one) → allowed; then L_A cancel still exists.
    +8. `test_delete_locks_room_and_groups` — `mock.patch("schedule.locking.lock_rooms_and_groups", wraps=...)` → called with `[L_A.room_id]` and `{G1.pk}`.
    +9. `test_delete_is_atomic_on_error` — after a rejected delete, `LessonChange.objects.count()` unchanged.
    +
    +`DeleteLessonChangeAdminTests(FrozenClockMixin, TestCase)` (superuser client):
    +10. `test_admin_invalid_delete_shows_error` — scenario 1; POST `{"post": "yes"}` to `reverse("admin:schedule_lessonchange_delete", args=[cancel.pk])` → 302 to the change page; follow → message contains «Нельзя удалить изменение»; the change exists; `LogEntry.objects.filter(action_flag=DELETION).count() == 0`.
    +11. `test_admin_valid_delete` — scenario 5 → 302, change deleted.
    +12. `test_admin_bulk_delete_action_removed` — GET changelist → `"delete_selected"` not among `response.context["action_form"].fields["action"].choices` values; POST `{"action": "delete_selected", "_selected_action": [cancel.pk]}` to the changelist → the change still exists.
    +13. `test_non_superuser_cannot_delete_change` — see 6.2.
    +
    +### 6.4 `academics/tests/test_change_guard.py`
    +`AttendanceChangeGuardTests(FrozenClockMixin, TestCase)` — student A in G1; L (G1, R1, Mon s2); attendance for occurrence 2026-11-16 (present).
    +1. `test_cancel_with_attendance_rejected` — CANCEL on 16.11 → `ValidationError` containing «отметки посещения»; nothing saved.
    +2. `test_cancel_without_attendance_allowed` — CANCEL on 09.11 (no records) → saved.
    +3. `test_edit_existing_change_to_cancel_rejected` — existing ROOM_CHANGED on 16.11 (allowed with records); edit kind to CANCELLED (clear `new_room`) → rejected.
    +4. `test_move_to_future_with_attendance_rejected` — MOVED 16.11 → 2026-11-20 s3 → rejected.
    +5. `test_move_to_past_with_attendance_allowed_and_visible` — MOVED 16.11 → 2026-11-17 s3 → saved; `student_term_report(A, term, date(2026, 11, 18))` attendance for L's discipline has `present == 1`.
    +6. `test_room_and_teacher_change_with_attendance_allowed`.
    +7. `test_edit_reason_of_allowed_move_with_attendance` — change from test 5, edit `reason` → saved.
    +8. `test_delete_move_returning_to_future_rejected` — L2 (G1, R2, Mon s3); MOVED 23.11 → 17.11 s4 (past); attendance for (L2, 23.11) present (effective date 17.11 is past → allowed); `delete_lesson_change(move)` → rejected with «отметки посещения».
    +9. `test_delete_move_returning_to_past_allowed` — MOVED 16.11 → 17.11 with record → delete → allowed (occurrence back to 16.11, past).
    +10. `test_admin_cancel_with_attendance_shows_form_error` — superuser POST to `admin:schedule_lessonchange_add` (CANCELLED, L, 16.11, reason) → 200, error text, no new row.
    +11. `test_clock_boundary_move` — MOVED 16.11 → 18.11 with records: with clock `2026-11-17 23:59:59` → rejected (future); with clock `2026-11-18 00:00:00` → allowed.
    +`GuardRegistryTests(SimpleTestCase)`: tests from 5.1.
    +
    +### 6.5 `academics/tests/test_clock_boundaries.py`
    +`MoscowMidnightTests(FrozenClockMixin, TestCase)`; each test patches `django.utils.timezone.now` with `moscow("2026-11-17 23:59:59")` and `moscow("2026-11-18 00:00:00")` in turn:
    +1. `test_mark_future_check` — mark dated 2026-11-18: 23:59:59 → `ValidationError` «в будущем»; 00:00:00 → valid.
    +2. `test_final_result_future_check` — same for `FinalResult`.
    +3. `test_attendance_today_check` — lesson on Wednesday; occurrence 2026-11-18: 23:59:59 → rejected (future); 00:00:00 → allowed.
    +4. `test_today_view_date` — student GET `/schedule/`: `response.context["day"].date` is 2026-11-17, then 2026-11-18.
    +5. `test_unmarked_counter_switches_at_midnight` — occurrence on 2026-11-17 without a record: GET `/grades/` at `2026-11-17 23:59:59` → that occurrence not counted as «не отмечено» (`report` unmarked == N); at `2026-11-18 00:00:00` → `N + 1`.
    +6. `test_machine_timezone_does_not_matter` — inside `mock.patch.dict(os.environ, {"TZ": "America/Los_Angeles"})` + `time.tzset()` (restore with `time.tzset()` after leaving the context, in `finally`): repeat test 4 at `2026-11-18 00:00:00` → day is 2026-11-18. Skip with `unittest.skipUnless(hasattr(time, "tzset"), ...)`.
    +7. `test_seed_at_midnight` — `call_command("seed_demo")` with `DEMO_PASSWORD` set, at `2026-11-17 23:59:59` and again at `2026-11-18 00:00:00` → both succeed; every `Attendance` row satisfies `validate_occurrence_for_student(..., today=date(2026, 11, 18)) == []`; no `CurrentMark` / `FinalResult` dated after 2026-11-18.
    +
    +### 6.6 Negative / edge cases covered
    +Rejected delete leaves data and log unchanged (6.3 #9, #10); same-occurrence skip (6.3 #7); midnight boundary (6.4 #11, 6.5); edit vs create (6.4 #3, #7); delete path of the guard (6.4 #8, #9).
    +
    +### 6.7 Settings branches
    +Not applicable (no settings changes).
    +
    +### 6.8 Query count
    +Not applicable (no list or aggregate page changes).
    +
    +### 6.9 Regression tests (must fail before the fix)
    +6.3 #1–#4, #10, #12; 6.4 #1, #3, #4, #8, #10; `ScheduleViewsTests.test_week_shows_only_own_group` under `scripts/run_tests_at.py 2027-03-01T12:00:00` (fails before the mixin is applied). Report in the `REPORT` that you saw them fail before the fix.
    +
    +---
    +
    +## 7. Feasibility check (performed 2026-11-13 on `3aa61bf`)
    +1. Clean start — `git status --short` → only ` M plan.md` (Team lead). OK.
    +2. Referenced objects — `LessonChange.clean()` (`schedule/models.py`, conflicts at the end via `change_conflicts`), `schedule/mutations.py` (`save_weekly_lesson`, `save_lesson_change`; no delete function), `schedule/locking.lock_rooms_and_groups` (`schedule/locking.py`), `schedule/validation.change_conflicts`, `schedule.services.occurrences_between` (`schedule/services.py:102`), `LessonChangeAdmin` (`schedule/admin.py`, no delete overrides), `academics/apps.py` (`AcademicsConfig`, no `ready()`), `Attendance.weekly_lesson` (`related_name="attendance_records"`, `academics/models.py:286`), `academics.services.validate_occurrence_for_student` (`academics/services.py:78`), `student_term_report`, test helpers in all three apps, test classes named in 5.6 (checked with `grep -n "^class "`). OK.
    +3. No collisions — `schedule/guards.py`, `core/testing.py`, `scripts/` do not exist; README has no "Known limitations" section. OK.
    +4. Data/migrations — no model field changes, no migration; `makemigrations --check` → "No changes detected". OK.
    +5. Tools — `.venv` Python 3.12.16, Django 5.2.19, ruff clean. `time.tzset` exists on macOS/Linux (CI ubuntu). OK.
    +6. Framework — `ModelAdmin.delete_view` runs `_delete_view` inside `transaction.atomic` and calls `delete_model` (Django 5.2); `get_actions` returns a dict containing `"delete_selected"`; `AppConfig.ready()`. OK.
    +7. Environment — no new env variables. OK.
    +8. Verification runnable — current tree: `test` → `Ran 364 tests … OK`; frozen-clock runs: passes at 7 instants listed in 3.3, fails at `2027-03-01 12:00` with 1 failure (the bug to fix). check, deploy check, ruff, YAML → OK.
    +9. Conflicts — Item 2's MOVED question resolved by analysis (3.2): only MOVED to a future date (and deleting a MOVED change back to a future date) hides records; ROOM/TEACHER changes do not. No conflicts with the request.
    +10. Assumptions / blockers — none.
    +
    +## 8. Implementation order
    +Shell: repo root, `.venv` active, `export DEBUG=true`, `export DEMO_PASSWORD='Local-Demo-Pass-2026!'`. Never open or edit `.env`. Do not delete `db.sqlite3` or migrations.
    +1. `core/testing.py`; `scripts/run_tests_at.py`; confirm `python scripts/run_tests_at.py 2027-03-01T12:00:00` fails (1 failure) before the next step.
    +2. Apply the mixin (5.6). Re-run the script at the 2027 date and at `2026-11-17T23:59:59` / `2026-11-18T00:00:00` → all pass. Add the CI step.
    +3. Write the new tests for items 1 and 2 first; confirm the regression tests fail.
    +4. `schedule/guards.py`, `LessonChange.clean()` change, `attendance_change_guard` + `ready()`.
    +5. `restored_occurrence_conflicts`, `delete_lesson_change`, admin changes.
    +6. `test_clock_boundaries.py`. README.
    +7. `ruff format .`; section 9; `REPORT` to the Reviewer. Do not commit.
    +
    +## 9. Verification
    +```bash
    +source .venv/bin/activate
    +export DEBUG=true
    +python manage.py check
    +python manage.py makemigrations --check --dry-run
    +python manage.py test
    +python scripts/run_tests_at.py 2026-11-17T23:59:59
    +python scripts/run_tests_at.py 2026-11-18T00:00:00
    +python scripts/run_tests_at.py 2027-03-01T12:00:00
    +DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
    +  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
    +  python manage.py check --deploy --fail-level WARNING
    +ruff check . && ruff format --check .
    +python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
    +grep -rn "academics" schedule --include='*.py' | grep -v "/tests/" ; echo "expect: no output"
    +DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
    +DEMO_PASSWORD='Local-Demo-Pass-2026!' python manage.py seed_demo
    +```
    +In the `REPORT`: output tails, test count (was 364), confirmation that the regression tests failed before the fix.
    +
    +## 10. Risks
    +- **Seed bulk delete**: `schedule/demo.py` still deletes demo changes with `queryset.delete()` (bypasses `delete_lesson_change`). Conflicts it could create are caught right after by `save_weekly_lesson` (occurrence simulation from TASK-004) → `CommandError`. The attendance guard runs when the seed re-creates changes; by construction the seed creates attendance only for past happening occurrences, so its own changes do not trip the guard. If an admin-created record does, the seed stops with a clear `CommandError`.
    +- **Guard registry**: guards are global; tests that register a temporary guard must remove it in `finally`.
    +- **Frozen clock mixin**: a test class without the mixin that runs clock-dependent code becomes date-dependent again; the CI far-future run catches it.
    +- **`time.tzset()`** changes process state; restore it in `finally`.
  ── Thought for 5s
    I'm going through a few spots: the test 6.3 #1 message names room "аудитория 1", which comes from the code "room-r1", so that's too specific and I'll change it to refer to R1's number. Next, the 6.4 #3 case with ROOM_CHANGED and then a switch to CANCELLED looks fine. Then I'm moving on to the attendance check for (L2, 23.11) after the move to 17.11.

    I'm checking the attendance validation for the move to 18.11, where the record for 16.11 already exists. If the move is created at 23:59:59 on the 17th, the new date of 18.11 is after today and gets rejected, but at 00:00 on the 18th it's allowed. Next I'm noting that the grades test needs a fixture with the autumn term and a curriculum item for the lesson's discipline, and that the midnight seed works with the clock patches.
  ── Ran python3 - <<'EOF' p="docs/tasks/TASK-005-FIX.md" s=open(p).read() reps=[ ("→ `ValidationError` mentioning «аудитория 1» (R1 number) and «23.11.2026»;","→ `ValidationError` whose message contains `f\"аудитория {R1.number}\"` and «23.11.2026»;"), ("- Purpose: lets apps that depend on `schedule` (e.g. `academics`) veto schedule changes without `schedule` importing them.","- Purpose: lets apps that depend on `schedule` veto schedule changes without `schedule` importing them. Do not write the word `academics` anywhere in non-test `schedule` code (docstrings included) — verification greps for it."), ("5. `test_unmarked_counter_switches_at_midnight` — occurrence on 2026-11-17 without a record:","5. `test_unmarked_counter_switches_at_midnight` — fixture: term `2026-09-01..2027-01-31` (session `2027-01-10..01-31`), curriculum item for the lesson's discipline and the student's group, lesson on Tuesdays; occurrence on 2026-11-17 without a record:"), ] for a,b in reps:     assert a in s, a[:50]; s=s.replace(a,b) open(p,"w").write(s) EOF bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-005-FIX] Planner -> Coder: TASK Spec: docs/tasks/TASK-005-FIX.md (approved by the Team lead; feasibility check in section 7, no blockers). Summary: - Item 1: `schedule.validation.restored_occurrence_conflicts` + `schedule.mutations.delete_lesson_change` (locks via `lock_rooms_and_groups`); admin `delete_model`/`delete_view` use it with an error message (no 500); bulk "delete_selected" removed for LessonChange. - Item 2: new guard registry `schedule/guards.py`; `LessonChange.clean()` and the delete service run guards; `academics` registers `attendance_change_guard` in `AcademicsConfig.ready()` (rejects CANCELLED with attendance, MOVED to a future date with attendance, deleting a MOVED change back to a future date with attendance). `schedule` must not mention `academics`. - Item 3 root cause: tests validating fixed dates against the real Moscow date. Add `core/testing.FrozenClockMixin` to the classes in 5.6, `scripts/run_tests_at.py` + CI step at 2027-03-01, and midnight boundary tests (6.5). README "Known limitations". - Write regression tests first and confirm they fail (section 8). Verification in section 9. Do not commit. Questions -> me. EOF (2s)
    $ python3 - <<'EOF'
  p="docs/tasks/TASK-005-FIX.md"
  s=open(p).read()
  reps=[
  ("→ `ValidationError` mentioning «аудитория 1» (R1 number) and «23.11.2026»;","→ `ValidationError` whose message contains `f\"аудитория {R1.number}\"` and «23.11.2026»;"),
  ("- Purpose: lets apps that depend on `schedule` (e.g. `academics`) veto schedule changes without `schedule` importing them.","- Purpose: lets apps that depend on `schedule` veto schedule changes without `schedule` importing them. Do not write the word `academics` anywhere in non-test `schedule` code (docstrings included) — verification greps for it."),
  ("5. `test_unmarked_counter_switches_at_midnight` — occurrence on 2026-11-17 without a record:","5. `test_unmarked_counter_switches_at_midnight` — fixture: term `2026-09-01..2027-01-31` (session `2027-01-10..01-31`), curriculum item for the lesson's discipline and the student's group, lesson on Tuesdays; occurrence on 2026-11-17 without a record:"),
  ]
  for a,b in reps:
      assert a in s, a[:50]; s=s.replace(a,b)
  open(p,"w").write(s)
  EOF
  bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
  [TASK-005-FIX] Planner -> Coder: TASK
  Spec: docs/tasks/TASK-005-FIX.md (approved by the Team lead; feasibility check in section 7, no blockers).
  Summary:
  - Item 1: `schedule.validation.restored_occurrence_conflicts` + `schedule.mutations.delete_lesson_change` (locks via `lock_rooms_and_groups`); admin `delete_model`/`delete_view` use it with an error message (no 500); bulk "delete_selected" removed for LessonChange.
  - Item 2: new guard registry `schedule/guards.py`; `LessonChange.clean()` and the delete service run guards; `academics` registers `attendance_change_guard` in `AcademicsConfig.ready()` (rejects CANCELLED with attendance, MOVED to a future date with attendance, deleting a MOVED change back to a future date with attendance). `schedule` must not mention `academics`.
  - Item 3 root cause: tests validating fixed dates against the real Moscow date. Add `core/testing.FrozenClockMixin` to the classes in 5.6, `scripts/run_tests_at.py` + CI step at 2027-03-01, and midnight boundary tests (6.5). README "Known limitations".
  - Write regression tests first and confirm they fail (section 8). Verification in section 9. Do not commit. Questions -> me.
  EOF
    Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Спецификация TASK-005-FIX готова: [docs/tasks/TASK-005-FIX.md](docs/tasks/TASK-005-FIX.md). Я передал её кодеру. Открытых вопросов в ней нет. Сами исправления ещё не написаны.

**1. Удаление изменения в расписании.** Сейчас админка удаляет изменение без проверки. Сценарий ревьюера подтвердился. Занятие A отменено. Занятие B перенесено в освободившуюся аудиторию в тот же час. Если удалить отмену, оба занятия окажутся в одной аудитории в одно время.
- Удаление пойдёт через новую функцию. Она блокирует строки аудитории и групп в том же порядке, что и остальные записи. Удаление пройдёт, только если восстановленное занятие ни с чем не пересечётся.
- Если пересечение есть, админка покажет ошибку и ничего не удалит.
- Массовое удаление для изменений расписания будет отключено.

**2. Отметки посещения и изменения расписания.** Я проверил, какие изменения прячут уже поставленные отметки. Прячут два:
- отмена занятия;
- перенос на будущую дату. Так же действует удаление переноса, если занятие возвращается на будущую дату.

Перенос в прошлое, замена аудитории и замена преподавателя отметки не прячут. Запрет сделан так, чтобы `schedule` по-прежнему не зависел от `academics`. В `schedule` появится список проверок, и `academics` регистрирует в нём свою проверку при запуске.

**3. Нестабильный тест — причину нашёл.**
- Сам код читает время правильно, через одно место, которое тесты подменяют.
- Но часть тестов не подменяет время и сверяет фиксированные даты, например 16–18 ноября, с реальной московской датой. Результат зависит от момента запуска. Московская полночь у вас приходится на день, поэтому сбой и появлялся днём.
- Я прогнал весь набор тестов с часами, замороженными на разные моменты. На полночь, на смену недели и на смену года всё проходит. На 1 марта 2027 один тест падает: он открывает реальную текущую неделю.

Исправление:
- Каждый класс тестов, который работает со временем, замораживает часы целиком, включая подготовку данных.
- Появится скрипт `scripts/run_tests_at.py`: он прогоняет все тесты на заданную дату. В CI добавится шаг с датой в будущем, и такая зависимость больше не пройдёт незамеченной.
- Новые тесты проверят поведение в 23:59:59 и 00:00:00 по Москве. Отдельный тест покажет, что часовой пояс компьютера на результат не влияет.

**Ограничения.** Два ограничения, которые вы приняли, будут записаны в README в разделе «Known limitations». Первое: после перевода студента в другую группу не видна посещаемость прежней группы. Второе: `seed_demo` не обновляет уже существующие строки успеваемости.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-005-FIX] Team lead -> Planner: TASK
Spec amendment 1 (approved by the user after a Reviewer ESCALATION). Add a section "Amendment 1" to `docs/tasks/TASK-005-FIX.md` and hand it to the Coder. The current implementation is otherwise correct; keep it.

## A1. Edit path of the "restored occurrence" defect
The spec closed only the DELETE path. Editing a LessonChange can restore a hidden occurrence without checks. Reproduced by the Reviewer:
- Setup: lesson A (G1, R1, Mon slot 2) is CANCELLED on 23.11.2026; lesson B is MOVED into 23.11 slot 2 with new_room=R1.
- Edit A's change kind CANCELLED -> TEACHER_REPLACED (+ new_teacher) via save_lesson_change -> saved; R1 has 2 happening occurrences on 23.11 slot 2.
- Edit A's change original_date 23.11 -> 30.11 -> saved; same double booking on 23.11.
- Same blind spot in the attendance guard: editing the original_date of a MOVED change can return an occurrence that has attendance records to a future date.
Cause: LessonChange.clean() validates only the NEW state and never the effect of leaving the OLD state.
Required behaviour: when an existing change is edited so that it stops hiding its old occurrence (old kind CANCELLED / MOVED / ROOM_CHANGED and the new kind is TEACHER_REPLACED, or original_date or weekly_lesson changes, or the move target changes), run the same checks as delete for the OLD state (restored-occurrence conflicts and the delete guards) in addition to the existing checks for the NEW state, inside the same transaction and locking order. Reviewer's suggestion (your decision): in clean() when pk is set, load the stored row and run restored_occurrence_conflicts(old_row) and run_change_guards(old_row, deleting=True). Admin edits must show a form error, never 500.
Regression tests: both scenarios above, the attendance scenario, and a positive case (an edit that does not restore a conflicting occurrence is still allowed).

## A2. Exclude the process archive from ruff
`docs/process/` holds verbatim agent dialog backups (Markdown). ruff 0.17 formats code blocks inside .md files, so `ruff format --check .` (a CI step) fails on the committed archive and `ruff format .` rewrites it. Add `docs/process` to `extend-exclude` in `pyproject.toml`. Verify: `ruff format --check .` and `ruff check .` pass without touching docs/process. Never run `ruff format` on docs/process.

## Reminder for the Coder (protocol)
Do not delete or recreate the local `db.sqlite3` (or any database) without Team lead approval. Use a temporary database (e.g. DATABASE_URL=sqlite:///$TMPDIR/...) for seed checks.

── Ran 4 commands ──────────────────────────────────────────
  ── Thought for 39s
    I'm checking where the implementation stands: the coder's uncommitted changes are expected for this task, so they're fine. I'm looking at the current `LessonChange.clean`, `restored_occurrence_conflicts`, the pyproject, whether the docs/process files exist, and the failing ruff format check.

    I also need to make sure the old-state check accounts for the new state as well, for example when a CANCELLED occurrence is changed to TEACHER_REPLACED on the same date.

    I'm checking whether the old-state check also has to account for the new state, such as a cancelled occurrence being changed to a teacher replacement on the same date. If the edit keeps the old occurrence hidden, I don't need the check, but when it is released or its kind changes, the conflict check on the old row applies.

    I'm working out when the old-state check is actually needed: only when the edit releases a hidden occurrence and its old kind was CANCELLED, MOVED, or ROOM_CHANGED. Switching from CANCELLED to MOVED or ROOM_CHANGED doesn't free the original slot in a way that needs a restore check, since the new-state check already covers the target and groups. Running the old check there would wrongly block a valid edit because of another lesson in room R1.

    I'm working out the ROOM_CHANGED-to-TEACHER_REPLACED case: the occurrence returns to the lesson's room, so the restore check on room R1 applies there. The group check at that slot already ran under the ROOM_CHANGED state, so it shouldn't need to run again.

    I'm working out when the old-state restore check is actually needed: when the edit releases a hidden occurrence whose old kind was CANCELLED, MOVED, or ROOM_CHANGED, or when it ends up as a TEACHER_REPLACED. Switching between CANCELLED, MOVED, and ROOM_CHANGED doesn't need it, since the new-state check already covers the target slot and groups.

    I'm checking the old-state restore case for a MOVED occurrence whose edit changes it to ROOM_CHANGED on the same date: the occurrence returns to its original date, and if that date is still in the future with attendance records, it stays hidden. My current rule doesn't catch that, so I need to account for it.

    I'm settling on the guard rule: when an old MOVED occurrence moves back to its original date, I'll run the old-state attendance guard, and I'll apply the restored-occurrence conflict check to the cases where the occurrence returns to the lesson's room.

    I'm settling on a generalized new-state attendance guard: if records exist for the new lesson and original date, a cancelled occurrence is rejected, and so is one whose effective date lies in the future. For the old state, I'll run the deleting guard whenever the occurrence's lesson or original date changes, or its kind changes.

    I'm settling the guard conditions: the old-state restore check applies only when the occurrence's identity (lesson or original date) changes, or when the new kind is TEACHER_REPLACED. If the identity stays the same, the new-state guard already evaluates the same records against the new effective date, so it's enough. I'm also checking whether widening the non-deleting guard would break any existing tests.

    For an identity change, the restore check on the old row is still needed, but `change_conflicts` would read the old row from the DB. That old row still holds the MOVED_IN item at the original date, so the new target would collide with the edit's own former move target. The check has to exclude the row being edited before it reads the DB.

    I'm adding a skip in `change_conflicts` for items whose `change` pk matches the row being edited, so the edit doesn't collide with its own old moved-in item. That same false positive already shows up when editing the original date of a MOVED occurrence, and it should be fixed at the same time.

    I'm planning to take all the locks in one pass before running the checks, so the rooms and groups are always locked in the same global order and two transactions can't deadlock against each other.

    I'm sketching a helper, `released_occurrence_errors`, that checks whether an edit frees an occurrence's original slot, and I'm planning to call it from `LessonChange.clean()` once the old row is loaded.

    I'm settling the error handling for the edit path: the restore conflicts get a prefix that fits an edit rather than a delete, and the guards run against the old row when the identity changed. I'm also planning to lock the rooms and groups from both the old and new lesson in one pass before running any checks.

    I'm adjusting the attendance guard for non-deleting edits: a cancelled occurrence is still rejected, and an effective date in the future is rejected when records exist, with the message differing for moved occurrences. Next I'll check the existing implementation names, whether the docs and process files exist, and whether `ruff format --check` currently fails.
  ── Ran git status --short | head -30 && ls docs/process 2>&1 | head -5 && grep -n "extend-exclude" pyproject.toml && source .venv/bin/activate && ruff --version && ruff format --check . 2>&1 | tail -3; ruff check . 2>&1 | tail -2; grep -n "def restored_occurrence_conflicts\|def change_conflicts" -A 30 schedule/validation.py | grep -n "skip\|continue\|def \|lock" ; grep -n "def attendance_change_guard" -A 30 academics/services.py; grep -n "run_change_guards\|change_conflicts" schedule/models.py (2s)
    $ git status --short | head -30 && ls docs/process 2>&1 | head -5 && grep -n "extend-exclude" pyproject.toml && source .venv/bin/activate && ruff --version && ruff format --check . 2>&1 | tail -3; ruff check . 2>&1 | tail -2; grep -n "def restored_occurrence_conflicts\|def change_conflicts" -A 30 schedule/validation.py | grep -n "skip\|continue\|def \|lock" ; grep -n "def attendance_change_guard" -A 30 academics/services.py; grep -n "run_change_guards\|change_conflicts" schedule/models.py
    M .github/workflows/ci.yml
     M README.md
     M academics/apps.py
     M academics/services.py
     M academics/tests/test_demo.py
     M academics/tests/test_models.py
     M academics/tests/test_services.py
     M academics/tests/test_views.py
     M accounts/tests/test_seed_demo.py
     M plan.md
     M schedule/admin.py
     M schedule/models.py
     M schedule/mutations.py
     M schedule/tests/test_demo.py
     M schedule/tests/test_demo_marker.py
     M schedule/tests/test_locking.py
     M schedule/tests/test_revalidation.py
     M schedule/tests/test_services.py
     M schedule/tests/test_validation.py
     M schedule/tests/test_views.py
     M schedule/validation.py
    ?? academics/tests/test_change_guard.py
    ?? academics/tests/test_clock_boundaries.py
    ?? core/testing.py
    ?? docs/tasks/TASK-005-FIX.md
    ?? schedule/guards.py
    ?? schedule/tests/test_change_delete.py
    ?? scripts/
    README.md
    dialogs
    screenshots
    4:extend-exclude = ["*/migrations/*", ".venv", "staticfiles"]
    ruff 0.17.4
          |

    1 file would be reformatted, 108 files already formatted
    All checks passed!
    1:171:def change_conflicts(change: LessonChange) -> list[str]:
    16:186-    locking.lock_rooms_and_groups([target_room_id], group_ids)
    22:192-            continue
    24:194-            continue
    33:209:def restored_occurrence_conflicts(change: LessonChange) -> list[str]:
    41:217-    locking.lock_rooms_and_groups([lesson.room_id], group_ids)
    47:223-            continue
    49:225-            continue
    292:def attendance_change_guard(change: LessonChange, deleting: bool) -> list[str]:
    293-    """Reject changes that would hide existing attendance records.
    294-
    295-    Registered via schedule.guards so that the schedule app never imports academics.
    296-    """
    297-    if change.weekly_lesson_id is None or change.original_date is None:
    298-        return []
    299-    count = Attendance.objects.filter(
    300-        weekly_lesson_id=change.weekly_lesson_id, original_date=change.original_date
    301-    ).count()
    302-    if count == 0:
    303-        return []
    304-    today = timezone.localdate()
    305-    d = f"{change.original_date:%d.%m.%Y}"
    306-    if not deleting:
    307-        if change.kind == ChangeKind.CANCELLED:
    308-            return [
    309-                f"Нельзя отменить занятие {d}: есть отметки посещения ({count}). "
    310-                "Сначала удалите их."
    311-            ]
    312-        if (
    313-            change.kind == ChangeKind.MOVED
    314-            and change.new_date is not None
    315-            and change.new_date > today
    316-        ):
    317-            return [
    318-                f"Нельзя перенести занятие {d} на будущую дату: есть отметки посещения ({count}). "
    319-                "Сначала удалите их."
    320-            ]
    321-    else:
    322-        if change.kind == ChangeKind.MOVED and change.original_date > today:
    245:        from .guards import run_change_guards
    247:        guard_errors = run_change_guards(self, deleting=False)
    251:        from .validation import change_conflicts
    253:        conflicts = change_conflicts(self)
  ── Thought for 8ms
    I'm checking whether the file that would be reformatted is in docs/process. I also want to look at the restored_occurrence_conflicts signature and message, along with the skip rule lines in change_conflicts.
  ── Ran source .venv/bin/activate && ruff format --check . 2>&1 | grep -i "would reformat"; sed -n 171,245p schedule/validation.py; sed -n 225,260p schedule/models.py
    $ source .venv/bin/activate && ruff format --check . 2>&1 | grep -i "would reformat"; sed -n 171,245p schedule/validation.py; sed -n 225,260p schedule/models.py
    def change_conflicts(change: LessonChange) -> list[str]:
        if change.kind in (ChangeKind.CANCELLED, ChangeKind.TEACHER_REPLACED):
            return []

        lesson = change.weekly_lesson
        if change.kind == ChangeKind.MOVED:
            target_date = change.new_date
            target_slot = change.new_slot
        else:  # ROOM_CHANGED
            target_date = change.original_date
            target_slot = lesson.slot

        target_room_id = change.new_room_id or lesson.room_id
        group_ids = set(lesson.groups.values_list("id", flat=True))

        locking.lock_rooms_and_groups([target_room_id], group_ids)

        items = occurrences_between(target_date, target_date, None)
        conflicts: list[str] = []
        for item in items:
            if not item.is_happening or item.slot.number != target_slot:
                continue
            if item.lesson.id == lesson.id and item.original_date == change.original_date:
                continue
            if item.room.id == target_room_id:
                conflicts.append(
                    f"Аудитория {item.room.number} занята: {item.lesson.discipline.name}, "
                    f"{target_date:%d.%m.%Y}, {target_slot} пара."
                )
            for g in item.lesson.groups.all():
                if g.id in group_ids:
                    conflicts.append(
                        f"Группа {g.name} занята: {item.lesson.discipline.name}, "
                        f"{target_date:%d.%m.%Y}, {target_slot} пара."
                    )
        return conflicts


    def restored_occurrence_conflicts(change: LessonChange) -> list[str]:
        """Conflicts when ``change`` is removed and its original occurrence becomes regular again."""
        if change.kind == ChangeKind.TEACHER_REPLACED:
            return []

        lesson = change.weekly_lesson
        group_ids = set(lesson.groups.values_list("id", flat=True))

        locking.lock_rooms_and_groups([lesson.room_id], group_ids)

        items = occurrences_between(change.original_date, change.original_date, None)
        conflicts: list[str] = []
        for item in items:
            if not item.is_happening or item.slot.number != lesson.slot:
                continue
            if item.lesson.id == lesson.id and item.original_date == change.original_date:
                continue
            if item.room.id == lesson.room_id:
                conflicts.append(
                    f"Нельзя удалить изменение: {change.original_date:%d.%m.%Y}, {lesson.slot} пара, "
                    f"аудитория {item.room.number} уже занята ({item.lesson.discipline.name})."
                )
            for g in item.lesson.groups.all():
                if g.id in group_ids:
                    conflicts.append(
                        f"Нельзя удалить изменение: {change.original_date:%d.%m.%Y}, "
                        f"{lesson.slot} пара, группа {g.name} уже занята "
                        f"({item.lesson.discipline.name})."
                    )
        return conflicts
            }
            for field in forbidden.get(self.kind, ()):
                if getattr(self, field) is not None:
                    errors.setdefault(field, []).append("Не заполняйте для этого вида изменения.")

            if self.kind == ChangeKind.MOVED:
                if (self.new_date, self.new_slot) == (self.original_date, lesson.slot) and (
                    self.new_room is None or self.new_room_id == lesson.room_id
                ):
                    errors.setdefault("new_date", []).append("Новое время совпадает со старым.")
            elif self.kind == ChangeKind.ROOM_CHANGED:
                if self.new_room_id == lesson.room_id:
                    errors.setdefault("new_room", []).append("Аудитория не изменилась.")
            elif self.kind == ChangeKind.TEACHER_REPLACED:
                if self.new_teacher_id == lesson.teacher_id:
                    errors.setdefault("new_teacher", []).append("Преподаватель не изменился.")

            if errors:
                raise ValidationError(errors)

            from .guards import run_change_guards

            guard_errors = run_change_guards(self, deleting=False)
            if guard_errors:
                raise ValidationError(guard_errors)

            from .validation import change_conflicts

            conflicts = change_conflicts(self)
            if conflicts:
                raise ValidationError(conflicts)
  ── Ran source .venv/bin/activate && ruff format --check . 2>&1 | head -5; ruff format --check --extend-exclude docs/process . 2>&1 | tail -1
    $ source .venv/bin/activate && ruff format --check . 2>&1 | head -5; ruff format --check --extend-exclude docs/process . 2>&1 | tail -1
    unformatted: File would be reformatted
         --> docs/process/dialogs/03-coder-deepseek.md:148:47
          |
    147   |          if _env_file.is_file():
          -              environ.Env.read_env(_env_file)   # overwrite=False (default): real env vars win
    104 files already formatted
  ── Thought for 3ms
    I've confirmed that the `docs/process` exclusion works in pyproject's `extend-exclude`, the same as it did on the command line. Now I'm writing the amendment.
  ── Ran cat >> docs/tasks/TASK-005-FIX.md <<'EOF' --- ## Amendment 1 (Team lead, approved by the user after a Reviewer ESCALATION) Keep the current implementation. Add only what is below. ### A1. Edit path of the "restored occurrence" defect #### A1.1 Analysis — which edits release the old occurrence `LessonChange.clean()` validates only the new state. An edit can also **release** the old state. Identity = `(weekly_lesson_id, original_date)`. For an existing row (`pk` set) compare the stored row `old` with the edited instance `new`: | Edit | Effect on the old occurrence | Check needed for the OLD state | |---|---|---| | identity changed (`weekly_lesson` or `original_date`), old kind CANCELLED / MOVED / ROOM_CHANGED | old occurrence becomes regular again | restored-occurrence conflicts **and** delete guards | | identity changed, old kind TEACHER_REPLACED | old occurrence keeps room/slot | delete guards only (no room/group effect) | | same identity, old kind CANCELLED / MOVED / ROOM_CHANGED → new kind TEACHER_REPLACED | occurrence returns to `lesson.room` at the original slot | restored-occurrence conflicts | | same identity, CANCELLED/ROOM_CHANGED → MOVED, CANCELLED/MOVED → ROOM_CHANGED, any → CANCELLED, MOVED target change | the original slot stays free or the new placement is fully checked by the existing new-state checks (`change_conflicts` checks room **and** groups of the new placement) | none (a check here would give false positives: the freed room may already be used legitimately) | The Team lead's list included "the move target changes". Analysis: changing `new_date`/`new_slot`/`new_room` of a MOVED change with the same identity frees the old target (freeing never conflicts), and the new target is checked by `change_conflicts`. So no old-state check is needed for this case. Attendance with the same identity: the records stay with the occurrence, so the **new-state** guard must judge the new placement for **every** kind, not only MOVED (example: MOVED to a past date with records → edited to ROOM_CHANGED; the occurrence goes back to its future original date and the records disappear from the report). See A1.3. Self-conflict found during the analysis: when the identity of a MOVED/ROOM_CHANGED change is edited, `change_conflicts` reads the DB, where the old row still produces an item (for example the old MOVED_IN item) with another `original_date`. That item is not skipped and reports a conflict with itself. Fix in A1.4. #### A1.2 New function `schedule/validation.py` ```python def released_occurrence_errors(old: LessonChange, new: LessonChange) -> list[str] ``` 1. `identity_changed = old.weekly_lesson_id != new.weekly_lesson_id or old.original_date != new.original_date`. 2. `hides = old.kind in (CANCELLED, MOVED, ROOM_CHANGED)`. 3. `restores = hides and (identity_changed or new.kind == TEACHER_REPLACED)`. 4. If not `restores` and not `identity_changed` → `[]`. 5. Locking (one call, before any check, keeps the global order): rooms = `{old.weekly_lesson.room_id, new.weekly_lesson.room_id, new.new_room_id}`; groups = groups of `old.weekly_lesson` ∪ groups of `new.weekly_lesson`; `locking.lock_rooms_and_groups(rooms, groups)`. The later lock calls in `restored_occurrence_conflicts` / `change_conflicts` only re-lock rows that are already held. 6. `errors = []`; if `restores`: `errors += restored_occurrence_conflicts(old, prefix="Нельзя так изменить запись")`; if `identity_changed`: `errors += run_change_guards(old, deleting=True)`. 7. Return `errors`. `restored_occurrence_conflicts(change, prefix: str = "Нельзя удалить изменение")`: add the keyword parameter and use it instead of the fixed text "Нельзя удалить изменение" in both messages. Existing callers and tests stay unchanged. #### A1.3 `attendance_change_guard` — new-state branch (`deleting=False`) for every kind Replace the non-deleting branch with: 1. `kind == CANCELLED` → existing message (unchanged). 2. `effective = change.new_date if change.kind == MOVED else change.original_date`; if `effective is not None and effective > today`:    - `kind == MOVED` → existing MOVED message (unchanged);    - otherwise → `f"Нельзя сохранить изменение занятия {d}: занятие окажется в будущем, а отметки посещения ({count}) уже есть. Сначала удалите их."`. The deleting branch is unchanged. #### A1.4 `change_conflicts` — skip the row being edited In the loop, after the existing "same occurrence" skip, add: `if change.pk is not None and item.change is not None and item.change.pk == change.pk: continue` (the DB items produced by the stored version of this same change are replaced by the new state). Do the same in `restored_occurrence_conflicts` is **not** needed (it receives the stored row itself). #### A1.5 `LessonChange.clean()` order After the field-rule errors (unchanged) and before the new-state guards: ```python if self.pk is not None:     old = LessonChange.objects.select_related("weekly_lesson").filter(pk=self.pk).first()     if old is not None:         from .validation import released_occurrence_errors         released = released_occurrence_errors(old, self)         if released:             raise ValidationError(released) ``` Then the existing `run_change_guards(self, deleting=False)` and `change_conflicts(self)`. All errors are non-field → admin shows a form error, no 500. `clean()` runs inside `save_lesson_change`'s and the admin's transaction, so locks are held until commit. #### A1.6 Tests — `schedule/tests/test_change_edit.py` (new) `EditLessonChangeTests(FrozenClockMixin, TestCase)`; clock `2026-11-18 12:00`; fixture as in 6.3: L_A (G1, R1, Mon s2), cancel C on 23.11; L_B (G2, R2, Tue s1) MOVED 17.11 → 23.11 s2 with `new_room=R1`. Edits go through `save_lesson_change` on the fetched row (`LessonChange.objects.get(pk=...)`, change fields, save). 1. `test_cancel_to_teacher_replaced_rejected` — C: kind → TEACHER_REPLACED, `new_teacher=T2` → `ValidationError` with `f"аудитория {R1.number}"` and «23.11.2026»; DB row still CANCELLED. 2. `test_cancel_original_date_change_rejected` — C: `original_date` → 30.11 → rejected; DB row still 23.11. 3. `test_room_changed_to_teacher_replaced_rejected` — L_A ROOM_CHANGED on 23.11 to R5 (instead of C); L_D (G3, R6, Mon s2) ROOM_CHANGED on 23.11 to R1; edit L_A's change to TEACHER_REPLACED → rejected. 4. `test_group_conflict_on_restore_rejected` — L_C (G1, R3, Tue s1) MOVED to 23.11 s2 (own room); edit C to 30.11 → rejected with group G1. 5. `test_allowed_edits` (subTests, each from a fresh C): reason change → saved; `original_date` 23.11 → 30.11 when nothing occupies 23.11 s2 (delete L_B's move first) → saved; CANCELLED → MOVED to Wed 25.11 s4 (B still in R1 on 23.11) → saved (no false positive). 6. `test_move_target_change_allowed` — L_A MOVED 23.11 → 25.11 s4; edit `new_slot` to 5 → saved. 7. `test_move_original_date_change_no_self_conflict` — L_A MOVED 23.11 → 25.11 s4; edit `original_date` → 30.11 (same target) → saved (A1.4). 8. `test_admin_edit_shows_form_error` — superuser POST to `admin:schedule_lessonchange_change` for scenario 1 → 200, error text, no 500, DB unchanged. 9. `test_edit_locks_once_in_order` — patch `schedule.locking.lock_rooms_and_groups` with `wraps`; scenario 2 → the first call receives rooms `{R1}` and groups `{G1}` (union of old/new). `academics/tests/test_change_guard.py` — add to `AttendanceChangeGuardTests`: 10. `test_edit_move_original_date_returns_records_to_future_rejected` — L2 (G1, R2, Mon s3) MOVED 23.11 → 17.11 s4; attendance for (L2, 23.11); edit the move's `original_date` to 30.11 (new target unchanged) → rejected «отметки посещения» (old occurrence 23.11 returns to the future with records). 11. `test_edit_move_to_room_change_returns_records_to_future_rejected` — same setup; edit kind → ROOM_CHANGED (`new_date=None`, `new_slot=None`, `new_room=R3`) → rejected (A1.3). 12. `test_edit_without_releasing_records_allowed` — MOVED 16.11 → 17.11 with records on 16.11; edit `reason` → saved. ### A2. Exclude the process archive from ruff `pyproject.toml`: `extend-exclude = ["*/migrations/*", ".venv", "staticfiles", "docs/process"]`. Never run `ruff format` on `docs/process`. Feasibility evidence: today `ruff format --check .` → "1 file would be reformatted" (`docs/process/dialogs/03-coder-deepseek.md:148`); `ruff format --check --extend-exclude docs/process .` → "104 files already formatted". ### A3. Protocol reminder Do not delete or recreate `db.sqlite3` (or any database) without Team lead approval. For seed checks use a temporary DB: `DATABASE_URL=sqlite:///$TMPDIR/seedcheck.sqlite3 python manage.py migrate && DATABASE_URL=sqlite:///$TMPDIR/seedcheck.sqlite3 python manage.py seed_demo` (twice). ### A4. Feasibility check (amendment, 2026-11-13, working tree of TASK-005-FIX in progress) 1. Clean start — uncommitted files are this task's own changes (listed by `git status`) plus `plan.md`. OK for an amendment of the same task. 2. Referenced objects — `restored_occurrence_conflicts(change)` and `change_conflicts(change)` (`schedule/validation.py:171, 209`), `LessonChange.clean()` guard/conflict calls (`schedule/models.py:245-253`), `attendance_change_guard(change, deleting)` (`academics/services.py:292`), `ScheduleItem.change` field, `FrozenClockMixin` (`core/testing.py`), test file `academics/tests/test_change_guard.py`. OK. 3. No collisions — `released_occurrence_errors`, `schedule/tests/test_change_edit.py` do not exist. OK. 4. Migrations — none. OK. 5–7. Tools/framework/env — unchanged. OK. 8. Verification — ruff state recorded in A2; the rest as in section 9. 9. Conflicts — "move target changes" from the request needs no old-state check (A1.1); the new-state guard is extended instead (A1.3). Not a contradiction of the requirement (every release of an occurrence is checked). 10. Assumptions / blockers — none. ### A5. Order and verification 1. A2 first (`ruff format --check .` passes). 2. Write A1.6 tests; confirm 1–4, 7, 8, 10, 11 fail. 3. Implement A1.2–A1.5. 4. Section 9 commands (seed checks with the temporary DB from A3). `REPORT` to the Reviewer with the regression evidence. Do not commit. EOF bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-005-FIX] Planner -> Coder: TASK Spec amendment: docs/tasks/TASK-005-FIX.md, section "Amendment 1" (approved by the user). Keep the current implementation; add: - A1: new `released_occurrence_errors(old, new)` in schedule/validation.py called from `LessonChange.clean()` when pk is set (edit path): restored-occurrence conflicts when an edit releases a hidden occurrence, delete guards when the identity changes; one lock call over old+new rooms/groups first. `restored_occurrence_conflicts` gets a `prefix` kwarg. `change_conflicts` skips items produced by the row being edited. `attendance_change_guard` new-state branch applies to every kind (effective date in the future with records -> reject). - A2: add "docs/process" to ruff extend-exclude; never format docs/process. - A3: never delete db.sqlite3; seed checks on a temporary DATABASE_URL. - Tests: schedule/tests/test_change_edit.py (9) + 3 in academics/tests/test_change_guard.py; confirm regressions fail first (A5). EOF (1s)
    $ cat >> docs/tasks/TASK-005-FIX.md <<'EOF'

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
  EOF
  bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
  [TASK-005-FIX] Planner -> Coder: TASK
  Spec amendment: docs/tasks/TASK-005-FIX.md, section "Amendment 1" (approved by the user). Keep the current implementation; add:
  - A1: new `released_occurrence_errors(old, new)` in schedule/validation.py called from `LessonChange.clean()` when pk is set (edit path): restored-occurrence conflicts when an edit releases a hidden occurrence, delete guards when the identity changes; one lock call over old+new rooms/groups first. `restored_occurrence_conflicts` gets a `prefix` kwarg. `change_conflicts` skips items produced by the row being edited. `attendance_change_guard` new-state branch applies to every kind (effective date in the future with records -> reject).
  - A2: add "docs/process" to ruff extend-exclude; never format docs/process.
  - A3: never delete db.sqlite3; seed checks on a temporary DATABASE_URL.
  - Tests: schedule/tests/test_change_edit.py (9) + 3 in academics/tests/test_change_guard.py; confirm regressions fail first (A5).
  EOF
    Thread thr_ng6cbgatm6 steered
    [This command modified 1 file you've previously read: docs/tasks/TASK-005-FIX.md. Call Read before editing.]

── Assistant ───────────────────────────────────────────────
Я дописал в [docs/tasks/TASK-005-FIX.md](docs/tasks/TASK-005-FIX.md) раздел «Amendment 1» и передал его кодеру. Код по дополнению ещё не написан.

**A1. Проверка при редактировании изменения.** Раньше проверялось только удаление. Ревьюер нашёл, что тот же результат можно получить правкой записи. Например, поменять отмену на «замену преподавателя» или сменить дату отмены — и в одной аудитории окажутся два занятия одновременно.

Я разобрал, какие правки возвращают скрытое занятие на прежнее место:
- **Смена даты или самого занятия в записи.** Если старая запись отменяла, переносила или меняла аудиторию, прежнее занятие возвращается. Проверяю его так же, как при удалении: на пересечения и на отметки посещения.
- **Отмена, перенос или замена аудитории превращается в замену преподавателя.** Занятие возвращается в свою аудиторию. Проверяю на пересечения.
- **Остальные правки** — например, отмена превращается в перенос или у переноса меняется цель. Старое место остаётся свободным, а новое уже проверяется существующей проверкой. Тимлид предлагал проверять и смену цели переноса. Я не стал: здесь это дало бы ложные ошибки, и в спецификации объяснено почему.

При разборе нашлись ещё две проблемы:
- **Ложное пересечение с самим собой.** Если поменять дату у переноса, проверка находит в базе старую версию этой же записи и сообщает о пересечении с ней. Теперь такие элементы пропускаются.
- **Отметки посещения.** Перенос в прошлое с отметками можно было переделать в замену аудитории. Тогда занятие возвращалось на будущую дату, и отметки пропадали из отчёта. Теперь проверка отметок учитывает итоговую дату занятия для любого вида изменения.

Блокировка аудиторий и групп берётся один раз на старое и новое состояние вместе, в общем порядке. Админка показывает ошибку в форме, без ошибки 500. Добавил 12 регрессионных тестов, в том числе положительные случаи: допустимые правки должны проходить.

**A2. Ruff и архив диалогов.** Подтвердил на текущем коде: `ruff format --check .` падает на `docs/process/dialogs/03-coder-deepseek.md`. После исключения папки `docs/process` из проверки ruff все 104 файла проходят.

**A3. Напоминание кодеру.** Удалять локальную базу нельзя. Проверять `seed_demo` нужно на временной базе.

── User ────────────────────────────────────────────────────
[bb message from thread:thr_4izdzwetb4]

[TASK-006] Team lead -> Planner: TASK
Approved by the user. Write the spec `docs/tasks/TASK-006.md` and hand it to the Coder.

## Context
Done: TASK-001..005 and TASK-005-FIX (users and roles, schedule, grades and attendance, change guards, `core/testing.py` FrozenClockMixin, `scripts/run_tests_at.py`). Reuse the existing access helpers (`students_visible_to`, role mixins), the validation pattern (model/service level, admin form errors never 500) and the locking pattern. Read `plan.md`, `README.md` "Known limitations" and the previous specs.

This is a mandatory part of the contest: "order a certificate or submit an application online and see its status". The jury will walk this scenario on a phone: log in as a student -> submit a request -> see its status; log in as dean's-office staff -> process it.

Later tasks depend on this one (design for them, do not implement): notifications (TASK-007) will announce request status changes, so every status change must be stored as a history record with time, actor and comment.

## Item 0 (tooling, do it first)
Exclude the whole `docs/` directory from ruff in `pyproject.toml` (replace the current `docs/process` exclusion). ruff 0.17 formats code blocks inside Markdown, and it already rewrote a spec once. Verify `ruff check .` and `ruff format --check .` pass and do not touch `docs/`.

## Goal
Students order certificates and submit applications online and track their status. Dean's-office staff process requests of their own faculty.

## Requirements
1. New app. Do NOT name it `requests` (it would shadow the popular `requests` library); e.g. `deanery` or `petitions` - justify.
2. Request types (catalog), managed in admin (superuser): name, kind (certificate / application), short description, expected processing time in working days, `comment_required` flag and a hint text shown above the comment field.
   The student form has exactly two inputs (user decision): "Комментарий" (text) and PDF attachments. There is no "number of copies" field (always 1) and no other fields.
   - If `comment_required` is set, the comment is mandatory (validated at form AND service level) and the hint states it, e.g. "Обязательно укажите причину обращения."
   - Seed exactly these fictional types:
     - "Справка об обучении" - certificate, comment optional;
     - "Справка для стипендиального отдела" - certificate, comment required (reason);
     - "Заявление на повторную промежуточную аттестацию" - application, comment required (reason);
     - "Заявление на академический отпуск" - application, comment required (reason).
2a. PDF attachments (security-critical):
   - Optional, up to 3 files per request, each at most 5 MB (named constants). Attached only when the request is submitted.
   - Accept only real PDFs: check the extension, the declared content type AND the file signature (`%PDF-`). Reject anything else with a clear form error.
   - Store files outside any publicly served directory under random, non-guessable names (user decision, exact scheme):
     - the name comes from a cryptographically secure generator: `uuid.uuid4().hex` (or `secrets.token_hex(16)`); never the `random` module, never a hash of the file name or content;
     - path format: `request_attachments/<first 2 chars>/<32 hex chars>.pdf`; the `.pdf` extension is fixed by the code;
     - nothing from the user goes into the path: not the original file name, not the student/request ID, not a date or counter (prevents path traversal and guessing). The `upload_to` callable ignores its `filename` argument;
     - collision protection: the stored file name/path field has a database UNIQUE constraint; on the (practically impossible) collision, generate a new name and retry a bounded number of times, then fail with a clear error; the storage must never overwrite an existing file;
     - keep the original file name only as display metadata (sanitized, length-limited) and use it in `Content-Disposition` on download.
   - Serve files ONLY through a Django view that applies the same access rules as the request (owner student, staff of the student's faculty), with `Content-Disposition: attachment`, the correct content type and `X-Content-Type-Options: nosniff`. No direct media URL. Document in README that nginx must not serve this directory.
   - Uploads must work with the existing security settings (CSRF, `FILE_UPLOAD_MAX_MEMORY_SIZE`/`DATA_UPLOAD_MAX_MEMORY_SIZE` adjusted only as needed).
   - Tests use small generated PDFs; `seed_demo` attaches a tiny generated fictional PDF to some demo requests.
3. Request: student, type, student comment, attachments, created_at, status, expected ready date (computed from working days; weekends only, no holiday calendar). Do NOT store which staff member "took" the request (user decision). Public identifier in URLs must be non-sequential (e.g. UUID); access is still checked on every request.
3a. Staff comments: ANY staff member with access to the request (staff of the student's faculty) can add comments at any status. Comments are append-only records (author, time, text), visible to the student in the request detail. Appending never overwrites another staff member's comment.
4. Status workflow (one place, explicit transition table):
   submitted (Подана) -> in_progress (В работе) -> ready (Готова) -> issued/closed (Выдана);
   submitted / in_progress -> rejected (Отклонена; comment required).
   There is no "cancel/withdraw" by the student (user decision).
   Every transition stores a history record (from, to, actor, time, comment). Invalid transitions are rejected at service level.
5. Concurrency: two staff members may act on the same request at the same time (status change vs status change, status change vs comment). A transition must succeed only if the current status is still the one the actor saw (e.g. `select_for_update` + expected-status check, or an optimistic version field - justify). The loser gets a clear message "Заявка уже изменена, обновите страницу", never a silent overwrite.
6. Abuse limit: a student may have at most 3 open (submitted or in_progress) requests of the same type (named constant).
7. Pages (server-rendered, Russian UI, mobile-first, existing CSS layers, no visual theme; all state changes via POST with CSRF):
   - Student: catalog of types -> form (comment + PDF files, hint for required comment) -> confirmation; "Мои заявки" list (newest first, status clearly visible, empty state); request detail with status history, staff comments and attachment downloads. No withdraw action.
   - Staff (dean's office): queue of requests of their own faculty with filter by status and type (default: open requests, oldest first); request detail with student info, student comment, attachments, history and staff comments; actions: take into work, mark ready, mark issued, reject (comment required), add comment.
   - Navigation: "Заявки" for both roles.
8. Access: students see only their own requests and attachments; staff only requests and attachments of students of their own faculty (404 otherwise); a student cannot perform staff transitions or add staff comments; no access via guessed IDs (requests and files).
9. Demo data: extend `seed_demo` (idempotent): requests of demo students in every status with history, so the jury immediately sees a filled list; at least one request per staff faculty waiting in the queue.
10. Queries: no N+1 on the lists; query-count tests.

## Out of scope
Attachments added by staff, file types other than PDF, antivirus scanning, generating PDF documents, e-mail, notifications (TASK-007), chat (TASK-009), visual theme, holiday calendar.

## Verification
All existing verification commands pass (check, deploy check, makemigrations --check, test, `scripts/run_tests_at.py` at a Moscow midnight boundary, ruff, CI YAML), `seed_demo` twice without errors (temporary database), manual check of the student and staff pages at 360 px width.

── Ran 5 commands, created 1 file ──────────────────────────
  ── Thought for 11ms
    I'm starting with a feasibility check: pulling the git status, the media, storage and upload settings, the pyproject exclude, the base nav, the accounts selectors, core/testing, the seed command, and the README's known limitations. I also want a baseline of test counts and a look at run_tests_at at midnight.
  ── Ran git log --oneline | head -4 && git status --short && grep -n "extend-exclude\|known-first" pyproject.toml && grep -n "MEDIA\|STORAGES\|UPLOAD\|STATIC_ROOT\|INSTALLED_APPS" -A0 config/settings.py && sed -n '/STORAGES = {/,/^}/p' config/settings.py && cat .gitignore | grep -n media && sed -n '/site-nav-list/,/<\/ul>/p' templates/base.html && cat core/testing.py | head -40 && cat config/urls.py | tail -8 && ls deanery petitions 2>&1 (2s, error)
    $ git log --oneline | head -4 && git status --short && grep -n "extend-exclude\|known-first" pyproject.toml && grep -n "MEDIA\|STORAGES\|UPLOAD\|STATIC_ROOT\|INSTALLED_APPS" -A0 config/settings.py && sed -n '/STORAGES = {/,/^}/p' config/settings.py && cat .gitignore | grep -n media && sed -n '/site-nav-list/,/<\/ul>/p' templates/base.html && cat core/testing.py | head -40 && cat config/urls.py | tail -8 && ls deanery petitions 2>&1
    Exit code 1
    23eeb2e Team protocol: compact the Coder above 200k tokens
    18adf49 Coder role: format only task files, protected paths, git status self-check
    507ee3b TASK-005-FIX: schedule change delete/edit checks, attendance guard, clock-safe tests
    3bc206f Team protocol: compact the Coder only above 250k tokens
     M plan.md
    4:extend-exclude = ["*/migrations/*", ".venv", "staticfiles", "docs/process"]
    15:known-first-party = ["config", "core", "accounts", "university", "schedule", "academics"]
    32:INSTALLED_APPS = [
    110:STATIC_ROOT = BASE_DIR / "staticfiles"
    111:STORAGES = {
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
    16:/media/
          <ul class="site-nav-list">
            <li><a href="{% url 'accounts:profile' %}">Профиль</a></li>
            {% if user.is_student %}
            <li><a href="{% url 'schedule:today' %}">Расписание</a></li>
            <li><a href="{% url 'academics:my_grades' %}">Успеваемость</a></li>
            {% elif user.is_deanery_staff %}
            <li><a href="{% url 'schedule:staff_groups' %}">Расписание</a></li>
            {% endif %}
            {% if user.is_deanery_staff %}
            <li><a href="{% url 'accounts:staff_student_list' %}">Студенты</a></li>
            {% endif %}
            <li>
              <form class="site-nav-logout" method="post" action="{% url 'accounts:logout' %}">
                {% csrf_token %}
                <button type="submit">Выйти</button>
              </form>
            </li>
          </ul>
    """Test clock helpers.

    A plain module (not a test module). It freezes ``django.utils.timezone.now`` for a
    whole test class so tests do not depend on the real current date.
    """

    from datetime import datetime
    from typing import ClassVar
    from unittest import mock
    from zoneinfo import ZoneInfo

    MOSCOW = ZoneInfo("Europe/Moscow")


    def moscow(dt_str: str) -> datetime:
        """Parse an ISO string as a Moscow-aware datetime, e.g. "2026-11-18 12:00"."""
        return datetime.fromisoformat(dt_str).replace(tzinfo=MOSCOW)


    class FrozenClockMixin:
        frozen_now: ClassVar[str] = "2026-11-18 12:00"

        @classmethod
        def setUpClass(cls) -> None:
            cls._clock_patcher = mock.patch(
                "django.utils.timezone.now", return_value=moscow(cls.frozen_now)
            )
            cls._clock_patcher.start()
            try:
                super().setUpClass()
            except Exception:
                cls._clock_patcher.stop()
                raise

        @classmethod
        def tearDownClass(cls) -> None:
            try:
                super().tearDownClass()
            finally:
                cls._clock_patcher.stop()

    urlpatterns = [
        path(settings.ADMIN_URL, admin.site.urls),
        path("", include("accounts.urls")),
        path("", include("schedule.urls")),
        path("", include("academics.urls")),
        path("", include("core.urls")),
    ]
    ls: deanery: No such file or directory
    ls: petitions: No such file or directory
    exit 1
  ── Thought for 2m
    I'm settling on the names first, then working out the settings for a private storage location. I'll set `PRIVATE_MEDIA_ROOT` to a `private_media` folder under the base directory, with a dedicated storage instance pointing there and no public base URL. I also need to make sure that folder is ignored by git.

    I'm going to give the storage a custom class that overrides `get_available_name`, so that on a filename collision it picks a new name rather than overwriting the existing file. The private storage itself will be reached through `storages["private"]`, wrapped in a callable so tests can swap it out with override_settings.

    I'm checking whether the custom storage should raise on an existing name rather than renaming, since the default `_save` loop would then just end in an exception. I'm also weighing whether the service should generate the name and check both the database and the file system before saving, rather than letting `upload_to` handle it. Last, I'm looking at whether `unique=True` is allowed on a `FileField` in current Django versions.

    I'm checking the collision path end to end: the storage should raise on an existing name instead of renaming, and the service should retry up to a small fixed number of attempts inside a savepoint when an IntegrityError or FileExistsError comes back. I also want the tests to force a collision by patching the uuid generator so the retry can be exercised deterministically.

    I'm checking that a storage collision raises rather than overwriting, and that the service handles the IntegrityError with a retry. I also need to decide whether to delete orphaned files if the database insert fails, and the plan is to validate all inputs first, then create the request and its attachments.

    I'm setting up PDF validation in the service: checking the extension, the declared content type, a non-zero size under 5 MB, and the `%PDF-` header, with a cap of three files. I'm also looking at how to handle multiple file uploads in the Django form.

    Next I'm looking at how uploads are size-limited: Django's default `FILE_UPLOAD_MAX_MEMORY_SIZE` streams larger files to temp files, and `DATA_UPLOAD_MAX_MEMORY_SIZE` doesn't count file bodies, so I may not need to change either. The real cap will probably have to come from the reverse proxy, and I'm also considering setting `FILE_UPLOAD_PERMISSIONS` to `0o640` for the saved files.

    I'm going to settle on the app name now. `deanery` feels too broad, and `petitions` doesn't fit certificates, so I'm leaning toward a name that covers both applications and certificates without overlapping with a future chat feature.

    I'm going with `petitions` as the app name, since it fits the applications and certificates without clashing with a likely chat feature. Next I'm laying out the `RequestType` model: a unique name, a certificate or application kind, a processing window of 1 to 60 days, an optional comment requirement with a hint, and an active flag so types can be hidden without being deleted.

    I'm settling the fields for the request model: a PROTECT foreign key to the student and to the request type, a comment capped at 2000 characters, a status, timestamps, and an expected-ready date. For concurrency I'm leaning toward a row lock with select_for_update plus an expected-status check, since status changes all go through one service. Comments are append-only and don't touch the request row, so they can't overwrite a status change, but the requirement still asks me to think about concurrency for

    I'm settling on the model names now: `Petition` for the request, since the internal name should stay distinct from Django's HTTP request object. Each attachment needs a private file field with a unique name, an original filename, a size, and its own UUID for public reference.

    I'm defining the persistence layer next: a `PetitionStatusChange` history model that records each transition with its actor and an optional comment, and a `PetitionComment` model for staff notes with a 2000-character limit, where only staff authors are allowed.

    I'm working out the date helper next: a function that adds a number of working days, Monday to Friday, to a start date, where each day is counted after the start. I'm also wondering what to do if the start falls on a weekend, since the processing window is at least one day.

    I'm planning the `submit_petition` service now: first confirm the request type is active, then check the comment's length and require it when the type demands one. Next I'll validate the attachments, and inside a transaction lock the student's row so two simultaneous submissions can't both slip past the per-type open-request limit.

    I'm now working out the service flow for submitting a petition: creating the record with a working-day deadline, logging the initial status in history, saving the attachments with retries, and cleaning up stored files if anything fails. Then I'm turning to the status-change service, which needs a staff permission check and a locked lookup of the petition within what that staff member can see.

    I'm settling the staff-side rules for the status change: the service will re-check that the actor can see the petition, reject the change if the status has moved since the form was loaded, and refuse any transition the workflow doesn't allow. A rejection will also need a comment.

    I'm defining the selectors next: petitions visible to a student are their own, and staff see petitions for students in their faculty, with attachments filtered the same way. I'm also noting that the submit and status-change services lock different rows, so they shouldn't deadlock, and that the expected ready date is fixed at submission.

    I'm laying out the student-facing views now: a catalog of active request types, and a submission form where the student adds a comment and files. After a successful submit, I'm planning to redirect to a confirmation page tied to the new petition's public ID.

    I'm defining the student-facing views: a confirmation page after submitting, a list of the student's own petitions, and a detail view. Then I'm planning one download view shared by both roles, which looks up the attachment only within what that user can see.

    I'm finishing the download view's response headers, adding an explicit nosniff header and a private, no-store cache policy. Then I'm laying out the staff side: a queue filtered by status and request type, defaulting to open requests oldest first, plus a detail page and a POST endpoint for status transitions.

    I'm wrapping up the staff side: the transition form carries the expected and new status plus a comment, and errors will go through the messages framework with a redirect back to the detail page. I still need to check whether base.html renders messages, and the staff comment endpoint and student history view are next on the list.

    I'm setting up the admin: the request type gets full editing, but the petition admin stays read-only so changes can't bypass the workflow and history. I'm also leaving the file field out of the admin display, since a private storage URL would raise an error. Staff access to a petition will be limited to students in their own faculty, and anyone else gets a 404, while students hitting staff URLs get a 403.

    I'm planning the seed command next, keeping it idempotent by keying each petition on a seed key, and I'm deciding whether to write its history rows directly with past timestamps instead of going through the services, which always stamp the current time.

    I'm making the seed command idempotent and planning to store a small PDF for each demo petition through the same attachment helper. The demo set covers a few students across two faculties, starting with a submitted certificate request that has a comment and one file.

    I'm going through the demo petitions now: a seeded in-progress request for the scholarship certificate, a ready re-attestation request with a PDF, a rejected leave application, an issued certificate from twenty days ago, and a submitted certificate in the other faculty's queue with a file attached.

    I'm settling the demo petitions now: a submitted certificate for the scholarship office, a rejected leave application, and an issued certificate, each with a fixed expected date based on its processing window. For the seed command, I'm deciding how to store the attached PDFs so they land in the private storage location without breaking the idempotent run.

    I'm working out how the tests should handle the private storage location, since the existing seed tests would otherwise write files into the project's private media folder. I'm considering a test mixin that points storage at a temporary directory, and whether the other apps' seed tests need the same override.

    I'm checking which test classes call the `seed_demo` command, since those would now write attachment files into the real private storage folder. I'll add a reusable mixin in `core/testing` that points storage at a temporary directory and cleans it up afterward, then apply it to the accounts, schedule, and academics classes that run the command.

    I'm considering a project-wide test runner instead of per-class mixins. It would point the private storage at a temporary directory for the whole run and clean it up afterward, so every test, including the seed command tests, stays out of the real private media folder.

    I'm settling on the private storage setup: a `PRIVATE_MEDIA_ROOT` setting with a private storage backend that has no base URL, so files can't be reached directly. I'm weighing whether that storage class belongs in a shared `core` module instead of the petitions app, since it could serve other private attachments later.

    I'm checking how a callable storage on a FileField behaves, since Django evaluates it once when the model loads and would ignore later setting overrides in tests. That makes a plain callable unreliable here, so I'm considering a lazily resolved storage object that looks up `storages["private"]` at access time instead.

    I'm weighing a lazily resolved storage object for the private field, since Django's own storage handling resets `default_storage` when settings change but would leave a custom alias cached. Running the tests under a global runner that overrides the private storage before anything loads seems like the more reliable route.

    I'm weighing whether the settings can pick the private storage location at import time, since a callable storage on the model would be fixed before any test override applies. The trouble is that redirecting storage after models load doesn't work cleanly, so I'm looking at whether the environment or the settings module should decide the path instead.

    I'm writing a storage class that reads the location from settings on every access, so tests can redirect it without stale cached values. It extends the standard file storage with no public base URL, and I'm defining its location property to return the private media path.

    I'm making the storage class's location a property that reads `PRIVATE_MEDIA_ROOT` on each access, so the test override takes effect. For the migration, I'll point the field at a callable that returns the storage instance, so the migration references a stable function rather than a serialized object.

    I'm setting the test runner up to create a temporary private media directory, overriding the private storage location for the run, and tearing it down afterward.

    I'm writing the test runner's teardown so the temporary private media folder gets removed after the run, and I'm setting `TEST_RUNNER` to point at this custom class. Next I'll add a test check that confirms the private media setting points inside the temporary directory during tests.

    I'm drafting the attachment upload path now: a UUID-based filename under a two-character subfolder, which keeps the path well within the field's length limit. I'm also checking that the storage's name generation will accept it, and planning a store-attachment service that takes the file content and original name.

    I'm writing the save routine so it tries a fresh generated filename on each attempt, wrapping the file write and the database row in one transaction. If the storage reports a name clash, I'll retry, and if the database insert fails I'll clean up the orphaned file before retrying. After the allowed number of attempts, it gives up with a user-facing error.

    I'm checking whether the IntegrityError path could delete a file that an existing row still points to. I'll check the database and storage for the generated name before saving, so I never write over a name that's already taken. Then I'll set the name up front and save without relying on the FileField save behavior.

    I'm checking that the saved name doesn't already exist in the database or storage before writing, and that the file is saved under exactly that name. If the row insert fails, I'll delete the written file and try again. I'm also planning a filename sanitizer that strips any path parts and control characters, normalizes the Unicode, and caps the length while keeping the `.pdf` extension.

    I'm describing the PDF validation helper now: it checks the file name ends in .pdf, the content type is application/pdf, the size is within the limit, and the first bytes match the PDF signature, then rewinds the file. Next I'm defining the petition form with an optional comment field and an optional multiple-file field, where the comment becomes required depending on the request type.

    Still writing the multiple-file field...

    I'm making sure the form's file field validates correctly when nothing is uploaded, then checking the template needs multipart encoding and how upload size limits apply.

    I'm settling the staff transitions: the action buttons will record who acted only through the history actor, since there's no separate field for who took a request into work. I'll cap open requests at three per type for each student, checking that count under a row lock on the student profile, and compute the expected ready date from the working-day helper applied to today's local date.

    I'm sketching the student list and detail views now: the student list will show their own petitions newest first, and the staff queue will filter by status and request type, defaulting to open requests and ignoring invalid parameters. For the detail page, I'll load the petition with its related records and prefetch the history along with the actor names, using the staff profile name for staff and the student name for students.

    I'm defining the history actor display so staff show their full name and students show as "Студент", and I'm loading the actor's staff profile with the history. I'm also making comments show the author's full name, then checking who can see what across the access matrix: anonymous users, students on their own and others' requests, staff in their own and other faculties, and superusers. Finally I'm sketching a concurrency test where a second staff member tries a transition on a petition that has already moved on.

    I'm planning the concurrency check by having a second staff member try a transition with a stale status, then confirming the petition stays unchanged with a single history entry. I'll wrap the locking helper in a mock to verify it gets called, and add tests that every disallowed status pair is rejected and that rejecting without a comment fails.

    I'm checking the deploy settings to confirm nothing changes there, and that no debug branches are needed since media isn't served statically. I'll also make sure the private media path isn't inside the static directories and that no URL pattern routes to the static serve view. Then I'll confirm the existing public-routes test still passes with the new login-required views, and check whether the base template renders messages.
  ── Thought for 8ms
    Имена `petitions` и `deanery` свободны, а папки для приватных файлов в настройках пока нет. Сейчас сверю возможности Django и прогоню базовые проверки.
  ── Ran source .venv/bin/activate && grep -n "messages" templates/base.html | head -3; python -c "import petitions" 2>&1 | tail -1; python -c "import deanery" 2>&1 | tail -1; DEBUG=true python - <<'EOF' import django, os os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings"); django.setup() from django.db import models from django.core import checks class T(models.Model):     f = models.FileField(unique=True, max_length=100)     class Meta: app_label="core" print("FileField unique checks:", [e.id for e in T.check()]) from django.core.files.storage import FileSystemStorage print("base_location is cached_property:", type(FileSystemStorage.__dict__["base_location"]).__name__) import inspect; src=inspect.getsource(FileSystemStorage._save); print("O_EXCL" in src, "get_available_name" in src) from django.urls import converters; print("uuid converter:", "uuid" in converters.DEFAULT_CONVERTERS) from django.conf import settings; print("TEST_RUNNER:", settings.TEST_RUNNER, "FILE_UPLOAD_MAX_MEMORY_SIZE:", settings.FILE_UPLOAD_MAX_MEMORY_SIZE, "PERMS:", settings.FILE_UPLOAD_PERMISSIONS) from django.http import FileResponse; print("FileResponse ok") EOF grep -rln 'call_command("seed_demo")' --include='*.py' . | grep -v .venv; ruff format --check --extend-exclude docs . | tail -1; ruff check --extend-exclude docs . | tail -1 (1s)
    $ source .venv/bin/activate && grep -n "messages" templates/base.html | head -3; python -c "import petitions" 2>&1 | tail -1; python -c "import deanery" 2>&1 | tail -1; DEBUG=true python - <<'EOF'
  import django, os
  os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings"); django.setup()
  from django.db import models
  from django.core import checks
  class T(models.Model):
      f = models.FileField(unique=True, max_length=100)
      class Meta: app_label="core"
  print("FileField unique checks:", [e.id for e in T.check()])
  from django.core.files.storage import FileSystemStorage
  print("base_location is cached_property:", type(FileSystemStorage.__dict__["base_location"]).__name__)
  import inspect; src=inspect.getsource(FileSystemStorage._save); print("O_EXCL" in src, "get_available_name" in src)
  from django.urls import converters; print("uuid converter:", "uuid" in converters.DEFAULT_CONVERTERS)
  from django.conf import settings; print("TEST_RUNNER:", settings.TEST_RUNNER, "FILE_UPLOAD_MAX_MEMORY_SIZE:", settings.FILE_UPLOAD_MAX_MEMORY_SIZE, "PERMS:", settings.FILE_UPLOAD_PERMISSIONS)
  from django.http import FileResponse; print("FileResponse ok")
  EOF
  grep -rln 'call_command("seed_demo")' --include='*.py' . | grep -v .venv; ruff format --check --extend-exclude docs . | tail -1; ruff check --extend-exclude docs . | tail -1
    ModuleNotFoundError: No module named 'petitions'
    ModuleNotFoundError: No module named 'deanery'
    FileField unique checks: []
    base_location is cached_property: cached_property
    True True
    uuid converter: True
    TEST_RUNNER: django.test.runner.DiscoverRunner FILE_UPLOAD_MAX_MEMORY_SIZE: 2621440 PERMS: 420
    FileResponse ok
    academics/tests/test_clock_boundaries.py
    accounts/tests/test_seed_demo.py
    99 files already formatted
    All checks passed!
  ── Thought for 5ms
    The base template doesn't render messages yet, so I need to add that. I also want to run the baseline tests and check run_tests_at midnight.
  ── Ran source .venv/bin/activate && export DEBUG=true && python manage.py check | tail -1 && python manage.py makemigrations --check --dry-run | tail -1 && python manage.py test 2>&1 | grep -E "^(Ran|OK|FAILED)" && python scripts/run_tests_at.py 2026-11-18T00:00:00 2>&1 | grep -E "^(Ran|OK|FAILED)" && DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ python manage.py check --deploy --fail-level WARNING | tail -1; ruff check . | tail -1; ruff format --check . | tail -1; python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"; grep -n "^## " README.md (2m 38s)
    $ source .venv/bin/activate && export DEBUG=true && python manage.py check | tail -1 && python manage.py makemigrations --check --dry-run | tail -1 && python manage.py test 2>&1 | grep -E "^(Ran|OK|FAILED)" && python scripts/run_tests_at.py 2026-11-18T00:00:00 2>&1 | grep -E "^(Ran|OK|FAILED)" && DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ python manage.py check --deploy --fail-level WARNING | tail -1; ruff check . | tail -1; ruff format --check . | tail -1; python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"; grep -n "^## " README.md
    System check identified no issues (0 silenced).
    No changes detected
    Ran 409 tests in 77.367s
    OK
    Ran 409 tests in 77.375s
    OK
    System check identified no issues (1 silenced).
    All checks passed!
    105 files already formatted
    yaml ok
    8:## Requirements
    12:## Setup
    21:## Run
    28:## Test & lint
    43:## Demo data
    71:## Schedule
    76:## Grades
    86:## Login protection
    97:## Known limitations
    105:## Environment variables
  ── Thought for 5ms
    I'm going to seed the baseline using a temporary database, since `DATABASE_URL` is set to a temp instance, and I want to keep this quick.
  ── Ran source .venv/bin/activate && export DEBUG=true DATABASE_URL="sqlite:///$TMPDIR/feas6.sqlite3" DEMO_PASSWORD='Local-Demo-Pass-2026!' && rm -f "$TMPDIR/feas6.sqlite3" && python manage.py migrate -v0 && python manage.py seed_demo | tail -1 && python manage.py seed_demo | tail -1; grep -n "seed_academics_demo\|today = " accounts/management/commands/seed_demo.py; grep -n "def students_visible_to\|def groups_visible_to" accounts/selectors.py (5s)
    $ source .venv/bin/activate && export DEBUG=true DATABASE_URL="sqlite:///$TMPDIR/feas6.sqlite3" DEMO_PASSWORD='Local-Demo-Pass-2026!' && rm -f "$TMPDIR/feas6.sqlite3" && python manage.py migrate -v0 && python manage.py seed_demo | tail -1 && python manage.py seed_demo | tail -1; grep -n "seed_academics_demo\|today = " accounts/management/commands/seed_demo.py; grep -n "def students_visible_to\|def groups_visible_to" accounts/selectors.py
    Academics ready: 2 terms, 17 curriculum items, 13 final results, 70 marks, 249 attendance records.
    Academics ready: 2 terms, 17 curriculum items, 13 final results, 70 marks, 249 attendance records.
    8:from academics.demo import seed_academics_demo
    24:                today = timezone.localdate()
    27:                a = seed_academics_demo(today)
    18:def students_visible_to(
    37:def groups_visible_to(
  ── Thought for 2s
    I'm moving on to writing the spec now, aiming for something thorough but tight.
  ── Thought for 6ms
    Базовые проверки прошли (409 тестов, CI, ruff и прочие); при этом `base.html` пока не выводит системные сообщения, а папка для файлов должна читаться из настроек при каждом обращении, иначе тесты не смогут её подменить. Сейчас пишу спецификацию.
  ── Created docs/tasks/TASK-006.md +575
    --- /dev/null
    +++ b~/hackatonproject/docs/tasks/TASK-006.md
    +# TASK-006: Certificates and applications (requests) with private PDF attachments
    +
    +Author: Planner. Status: ready for implementation.
    +Base commit: `23eeb2e`. Reused: role mixins (`accounts/access.py`), selectors pattern (`accounts/selectors.py`), validation pattern (model/service level, non-field errors, admin never 500), locking pattern (`select_for_update` in services), `core/testing.FrozenClockMixin`, `scripts/run_tests_at.py`.
    +
    +Jury scenario (phone): student logs in → submits a request → sees its status; staff logs in → processes it.
    +
    +---
    +
    +## 1. Acceptance criteria
    +
    +| ID | Criterion |
    +|---|---|
    +| AC0 | `pyproject.toml` excludes the whole `docs/` from ruff; `ruff check .` / `ruff format --check .` pass and never touch `docs/`. |
    +| AC1 | New app `petitions` with `RequestType`, `Petition`, `PetitionAttachment`, `PetitionStatusChange`, `PetitionComment`; migrations exist. |
    +| AC2 | Student form has exactly two inputs: «Комментарий» and PDF files. `comment_required` types require a comment (form **and** service) and show the hint. |
    +| AC3 | Attachments: optional, ≤ 3 files, each ≤ 5 MB; accepted only if extension `.pdf`, declared content type `application/pdf` **and** signature `%PDF-`. |
    +| AC4 | Files are stored in a private directory outside static/media, at `request_attachments/<2 hex>/<32 hex>.pdf`, name from `uuid.uuid4().hex`, nothing user-derived in the path, DB-unique path, bounded retry on collision, storage never overwrites. Original name kept only as sanitized display metadata. |
    +| AC5 | Files are served only by a Django view with the request's access rules, `Content-Disposition: attachment`, `Content-Type: application/pdf`, `X-Content-Type-Options: nosniff`; no public URL exists. |
    +| AC6 | Workflow in one explicit transition table; every status change (and the initial submission) stores a history row (from, to, actor, time, comment); invalid transitions and reject without comment are rejected at service level. No student withdraw. |
    +| AC7 | Concurrency: a transition succeeds only if the locked current status equals the status the actor saw; otherwise «Заявка уже изменена, обновите страницу». Comments are append-only and never conflict. |
    +| AC8 | A student has at most 3 open (submitted / in_progress) requests of the same type. |
    +| AC9 | Pages: student catalog → form → confirmation, «Мои заявки», detail (history, staff comments, downloads); staff queue (own faculty, filter status/type, default open oldest first), detail, actions, comments; nav «Заявки» for both roles; all state changes via POST + CSRF. |
    +| AC10 | Access: students only own requests/files; staff only own faculty (404 otherwise); students cannot transition or comment as staff; URLs use UUIDs. |
    +| AC11 | `seed_demo` (idempotent) creates demo requests in every status with history, comments and tiny PDFs; each staff faculty has a request waiting in the queue. |
    +| AC12 | Lists and details run a constant number of queries. |
    +
    +## 2. Out of scope
    +Staff attachments, non-PDF files, antivirus, PDF generation, e-mail, notifications (TASK-007), chat, visual theme, holiday calendar, editing a submitted request, pagination of lists, student withdraw.
    +
    +---
    +
    +## 3. Design decisions
    +
    +### 3.1 App name `petitions`
    +Not `requests` (would shadow the `requests` library on `import requests`). `deanery` is too broad (chat and notifications are also "dean's office"). `petitions` names exactly this bounded context: requests for certificates and applications. `import petitions` / `import deanery` currently fail in `.venv` (no clash). Model names use `Petition*` to avoid confusion with `HttpRequest`. UI text says «заявка».
    +
    +### 3.2 Concurrency: `select_for_update` + expected status
    +All transitions go through one service. It locks the petition row (`select_for_update`) and compares the locked status with `expected_status` posted by the form (the status the actor saw). No version field is needed: the status itself is the version for transitions, and comments are separate append-only rows (a comment never modifies the petition row, so "status vs comment" cannot overwrite anything). On PostgreSQL the second writer waits for the lock and then sees the new status; on SQLite writes are serialized by the database lock — the expected-status check gives the same result.
    +
    +### 3.3 Private storage
    +`PRIVATE_MEDIA_ROOT` (env, default `BASE_DIR / "private_media"`), never under `STATIC_ROOT`/`static/`, never served by Django URLs or nginx. Storage class `core.storage.PrivateFileStorage` reads `settings.PRIVATE_MEDIA_ROOT` **on every access** (properties, not `cached_property`), because a model field's storage object is created once at model load; reading the setting dynamically lets tests redirect it. `url()` raises (no public URL). `get_available_name()` raises `FileExistsError` instead of renaming → the storage never overwrites and never silently renames.
    +
    +### 3.4 Test isolation of files
    +`TEST_RUNNER = "core.test_runner.ProjectTestRunner"`: creates a temporary `PRIVATE_MEDIA_ROOT` for the whole run and deletes it afterwards. All tests (including existing `seed_demo` tests and `scripts/run_tests_at.py`) never write into the repository.
    +
    +### 3.5 Later tasks
    +Notifications (TASK-007) read `PetitionStatusChange` rows (time, actor, from/to, comment) and `PetitionComment` rows.
    +
    +---
    +
    +## 4. Architecture
    +
    +### 4.1 Files
    +Create:
    +```
    +core/storage.py
    +core/test_runner.py
    +core/tests/test_storage.py
    +petitions/__init__.py
    +petitions/apps.py
    +petitions/models.py
    +petitions/workflow.py
    +petitions/files.py
    +petitions/selectors.py
    +petitions/services.py
    +petitions/forms.py
    +petitions/views.py
    +petitions/urls.py
    +petitions/admin.py
    +petitions/demo.py
    +petitions/migrations/__init__.py
    +petitions/migrations/0001_initial.py                (generated)
    +petitions/templates/petitions/catalog.html
    +petitions/templates/petitions/form.html
    +petitions/templates/petitions/submitted.html
    +petitions/templates/petitions/my_list.html
    +petitions/templates/petitions/detail.html            (student)
    +petitions/templates/petitions/staff_queue.html
    +petitions/templates/petitions/staff_detail.html
    +petitions/templates/petitions/includes/history.html
    +petitions/templates/petitions/includes/comments.html
    +petitions/templates/petitions/includes/attachments.html
    +petitions/tests/__init__.py
    +petitions/tests/helpers.py
    +petitions/tests/test_files.py
    +petitions/tests/test_workflow.py
    +petitions/tests/test_services.py
    +petitions/tests/test_views.py
    +petitions/tests/test_downloads.py
    +petitions/tests/test_demo.py
    +```
    +Change:
    +```
    +pyproject.toml (AC0, known-first-party), config/settings.py, config/urls.py, .env.example, .gitignore,
    +templates/base.html (nav + messages), static/css/base.css,
    +accounts/management/commands/seed_demo.py, README.md
    +```
    +No other files. No new dependencies.
    +
    +### 4.2 Tooling (AC0) — do first
    +`pyproject.toml`: `extend-exclude = ["*/migrations/*", ".venv", "staticfiles", "docs"]` (replaces `"docs/process"`); `known-first-party` += `"petitions"`. Never run `ruff format` on `docs/`.
    +
    +### 4.3 Settings (`config/settings.py`)
    +- `INSTALLED_APPS`: add `"petitions"` after `"academics"`.
    +- After `STORAGES`:
    +  ```python
    +  PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private_media")))
    +  FILE_UPLOAD_PERMISSIONS = 0o640
    +  FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
    +  ```
    +  `FILE_UPLOAD_MAX_MEMORY_SIZE` / `DATA_UPLOAD_MAX_MEMORY_SIZE` stay at Django defaults (2.5 MB): larger uploads are streamed to temporary files, and `DATA_UPLOAD_MAX_MEMORY_SIZE` does not count file data. The 5 MB limit is enforced by validation.
    +- `TEST_RUNNER = "core.test_runner.ProjectTestRunner"`.
    +- No `MEDIA_ROOT`/`MEDIA_URL` and no `static()`/`serve` URL patterns.
    +`.env.example` append:
    +```
    +# Private uploads (request attachments). Must NOT be served by nginx or be inside static/.
    +PRIVATE_MEDIA_ROOT=
    +```
    +(empty = default `<repo>/private_media`; `env.str` with empty value → treat `""` as default: `env.str("PRIVATE_MEDIA_ROOT", default="") or str(BASE_DIR / "private_media")`.) `.gitignore`: add `/private_media/`.
    +
    +### 4.4 `core/storage.py`
    +```python
    +class PrivateFileStorage(FileSystemStorage):
    +    def __init__(self) -> None                      # super().__init__(base_url=None)
    +    @property
    +    def base_location(self) -> str                  # str(settings.PRIVATE_MEDIA_ROOT)
    +    @property
    +    def location(self) -> str                       # os.path.abspath(self.base_location)
    +    def url(self, name: str | None) -> str          # raise ValueError("Private files have no public URL.")
    +    def get_available_name(self, name: str, max_length: int | None = None) -> str
    +        # if self.exists(name): raise FileExistsError(name); return name
    +
    +_private_storage = PrivateFileStorage()
    +
    +def get_private_storage() -> PrivateFileStorage:
    +    return _private_storage
    +```
    +`FileSystemStorage._save` opens with `O_EXCL` and on a race calls `get_available_name` again → our override raises `FileExistsError`; the file is never overwritten.
    +Tests (`core/tests/test_storage.py`): `test_location_follows_setting` (`override_settings(PRIVATE_MEDIA_ROOT=tmp)` → `location == tmp`); `test_url_raises`; `test_existing_name_is_not_overwritten` (save `a/x.pdf`, saving again the same name → `FileExistsError`, original content intact); `test_test_runner_uses_temp_dir` (`settings.PRIVATE_MEDIA_ROOT` is not inside `BASE_DIR`).
    +
    +### 4.5 `core/test_runner.py`
    +```python
    +class ProjectTestRunner(DiscoverRunner):
    +    def setup_test_environment(self, **kwargs) -> None
    +    def teardown_test_environment(self, **kwargs) -> None
    +```
    +- setup: `super()…`; `self._private_dir = tempfile.mkdtemp(prefix="test-private-media-")`; `self._private_override = override_settings(PRIVATE_MEDIA_ROOT=Path(self._private_dir))`; `.enable()`.
    +- teardown: `.disable()`; `shutil.rmtree(self._private_dir, ignore_errors=True)`; `super()…`.
    +
    +### 4.6 Models (`petitions/models.py`)
    +Enums:
    +```python
    +class RequestKind(models.TextChoices):
    +    CERTIFICATE = "certificate", "Справка"
    +    APPLICATION = "application", "Заявление"
    +
    +class PetitionStatus(models.TextChoices):
    +    SUBMITTED = "submitted", "Подана"
    +    IN_PROGRESS = "in_progress", "В работе"
    +    READY = "ready", "Готова"
    +    ISSUED = "issued", "Выдана"
    +    REJECTED = "rejected", "Отклонена"
    +```
    +Constants (`petitions/models.py`): `MAX_COMMENT_LENGTH = 2000`.
    +
    +**`RequestType`**
    +| Field | Definition |
    +|---|---|
    +| `name` | `CharField("название", max_length=200, unique=True)` |
    +| `kind` | `CharField("вид", max_length=16, choices=RequestKind.choices)` |
    +| `description` | `TextField("описание", blank=True, default="")` |
    +| `processing_days` | `PositiveSmallIntegerField("срок, рабочих дней", validators=[MinValueValidator(1), MaxValueValidator(60)])` |
    +| `comment_required` | `BooleanField("комментарий обязателен", default=False)` |
    +| `comment_hint` | `CharField("подсказка к комментарию", max_length=255, blank=True, default="")` |
    +| `is_active` | `BooleanField("доступна для подачи", default=True)` |
    +- `Meta`: `ordering = ["kind", "name"]`; `CheckConstraint(condition=Q(processing_days__gte=1) & Q(processing_days__lte=60), name="petitions_type_days_1_60")`. `__str__` → `name`.
    +- `clean()`: `comment_required` and empty `comment_hint` → non-field error «Для обязательного комментария заполните подсказку.»
    +
    +**`Petition`**
    +| Field | Definition |
    +|---|---|
    +| `public_id` | `UUIDField("номер", default=uuid.uuid4, unique=True, editable=False)` |
    +| `student` | `ForeignKey("accounts.StudentProfile", PROTECT, related_name="petitions")` |
    +| `request_type` | `ForeignKey(RequestType, PROTECT, related_name="petitions")` |
    +| `comment` | `TextField("комментарий", blank=True, default="", max_length=MAX_COMMENT_LENGTH)` |
    +| `status` | `CharField("статус", max_length=16, choices=PetitionStatus.choices, default=SUBMITTED)` |
    +| `created_at` | `DateTimeField("подана", default=timezone.now)` |
    +| `status_changed_at` | `DateTimeField("статус изменён", default=timezone.now)` |
    +| `expected_ready_date` | `DateField("ожидаемая дата готовности")` |
    +| `seed_key` | `SlugField(max_length=40, blank=True, default="", editable=False)` |
    +- `Meta`: `ordering = ["-created_at"]`; `indexes = [Index(fields=["status", "created_at"], name="petitions_status_created_idx")]`; `CheckConstraint(condition=Q(status__in=[...5 values]), name="petitions_status_value")`; `UniqueConstraint(fields=["seed_key"], condition=~Q(seed_key=""), name="petitions_unique_seed_key")`.
    +- `__str__` → `f"{self.request_type} — {self.student} ({self.get_status_display()})"`. Property `short_id` → `str(self.public_id)[:8]` (display only).
    +- No "taken by" field (user decision). No `clean()` (all rules are in services; admin is read-only for petitions).
    +
    +**`PetitionAttachment`**
    +| Field | Definition |
    +|---|---|
    +| `public_id` | `UUIDField(default=uuid.uuid4, unique=True, editable=False)` (download URL id; never the file path) |
    +| `petition` | `ForeignKey(Petition, CASCADE, related_name="attachments")` |
    +| `file` | `FileField(upload_to=attachment_upload_to, storage=get_private_storage, max_length=100, unique=True)` |
    +| `original_name` | `CharField("имя файла", max_length=120)` |
    +| `size` | `PositiveIntegerField("размер, байт")` |
    +| `uploaded_at` | `DateTimeField(default=timezone.now)` |
    +- `Meta`: `ordering = ["uploaded_at", "pk"]`. `__str__` → `original_name`.
    +
    +**`PetitionStatusChange`** (history)
    +| Field | Definition |
    +|---|---|
    +| `petition` | `ForeignKey(Petition, CASCADE, related_name="history")` |
    +| `from_status` | `CharField(max_length=16, choices=PetitionStatus.choices, blank=True, default="")` (`""` = submission) |
    +| `to_status` | `CharField(max_length=16, choices=PetitionStatus.choices)` |
    +| `actor` | `ForeignKey(settings.AUTH_USER_MODEL, PROTECT, related_name="petition_status_changes")` |
    +| `created_at` | `DateTimeField(default=timezone.now)` |
    +| `comment` | `TextField(blank=True, default="", max_length=MAX_COMMENT_LENGTH)` |
    +- `Meta`: `ordering = ["created_at", "pk"]`; `Index(fields=["created_at"], name="petitions_history_created_idx")`.
    +
    +**`PetitionComment`** (staff comments, append-only)
    +| Field | Definition |
    +|---|---|
    +| `petition` | `ForeignKey(Petition, CASCADE, related_name="staff_comments")` |
    +| `author` | `ForeignKey(settings.AUTH_USER_MODEL, PROTECT, related_name="petition_comments")` |
    +| `created_at` | `DateTimeField(default=timezone.now)` |
    +| `text` | `TextField(max_length=MAX_COMMENT_LENGTH)` |
    +- `Meta`: `ordering = ["created_at", "pk"]`; `CheckConstraint(condition=~Q(text=""), name="petitions_comment_not_empty")`.
    +
    +### 4.7 URLs (`petitions/urls.py`, `app_name = "petitions"`; include in `config/urls.py` after `academics`)
    +| Path | View | Name | Method |
    +|---|---|---|---|
    +| `requests/` | `MyPetitionsView` | `my_list` | GET |
    +| `requests/new/` | `CatalogView` | `catalog` | GET |
    +| `requests/new/<int:type_id>/` | `SubmitPetitionView` | `submit` | GET, POST |
    +| `requests/<uuid:public_id>/` | `StudentPetitionDetailView` | `detail` | GET |
    +| `requests/<uuid:public_id>/submitted/` | `SubmittedView` | `submitted` | GET |
    +| `requests/<uuid:public_id>/files/<uuid:file_id>/` | `download_attachment` | `download` | GET (both roles) |
    +| `staff/requests/` | `StaffQueueView` | `staff_queue` | GET |
    +| `staff/requests/<uuid:public_id>/` | `StaffPetitionDetailView` | `staff_detail` | GET |
    +| `staff/requests/<uuid:public_id>/status/` | `StaffTransitionView` | `staff_transition` | POST only |
    +| `staff/requests/<uuid:public_id>/comments/` | `StaffCommentView` | `staff_comment` | POST only |
    +`type_id` is the `RequestType` pk (the catalog is public to students; not a secret).
    +
    +### 4.8 Navigation and messages (`templates/base.html`)
    +- Student block: add `<li><a href="{% url 'petitions:my_list' %}">Заявки</a></li>`; staff block: `<li><a href="{% url 'petitions:staff_queue' %}">Заявки</a></li>`.
    +- Inside `<main>` before `{% block content %}`: `{% if messages %}<ul class="messages">{% for m in messages %}<li class="message message--{{ m.tags }}">{{ m }}</li>{% endfor %}</ul>{% endif %}`.
    +
    +---
    +
    +## 5. Functions
    +
    +### 5.1 `petitions/workflow.py` — single transition table
    +```python
    +TRANSITIONS: dict[str, tuple[str, ...]] = {
    +    SUBMITTED: (IN_PROGRESS, REJECTED),
    +    IN_PROGRESS: (READY, REJECTED),
    +    READY: (ISSUED,),
    +    ISSUED: (),
    +    REJECTED: (),
    +}
    +OPEN_STATUSES = frozenset({SUBMITTED, IN_PROGRESS})
    +COMMENT_REQUIRED_FOR = frozenset({REJECTED})
    +ACTION_LABELS = {IN_PROGRESS: "Взять в работу", READY: "Отметить готовой", ISSUED: "Отметить выданной", REJECTED: "Отклонить"}
    +
    +def allowed_transitions(status: str) -> tuple[str, ...]      # TRANSITIONS.get(status, ())
    +def can_transition(from_status: str, to_status: str) -> bool
    +```
    +Tests (`test_workflow.py`, `SimpleTestCase`): every allowed pair → `True`; every other pair of the 5×5 matrix (incl. same→same) → `False`; `ISSUED`/`REJECTED` final; every target in `TRANSITIONS` has a label; `OPEN_STATUSES` exact.
    +
    +### 5.2 `petitions/files.py` — attachments
    +Constants: `MAX_ATTACHMENTS = 3`, `MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024`, `PDF_CONTENT_TYPE = "application/pdf"`, `PDF_SIGNATURE = b"%PDF-"`, `MAX_NAME_ATTEMPTS = 5`, `ATTACHMENT_DIR = "request_attachments"`, `MAX_DISPLAY_NAME = 120`.
    +
    +```python
    +def attachment_upload_to(instance: object, filename: str) -> str
    +```
    +Ignores both arguments. `name = uuid.uuid4().hex`; return `f"{ATTACHMENT_DIR}/{name[:2]}/{name}.pdf"`. Never use `random`, hashes, the file name, IDs or dates.
    +
    +```python
    +def sanitize_display_name(raw: str) -> str
    +```
    +1. `name = unicodedata.normalize("NFC", raw or "")`; take the part after the last `/` or `\\`.
    +2. Remove control characters (`unicodedata.category(c).startswith("C")`) and `"`; collapse whitespace; strip.
    +3. If not `name.lower().endswith(".pdf")` → append `".pdf"`. If the stem is empty → `"document.pdf"`.
    +4. If `len(name) > MAX_DISPLAY_NAME`: keep `stem[: MAX_DISPLAY_NAME - 4] + ".pdf"`.
    +Tests: `"../../etc/passwd.pdf"` → `"passwd.pdf"`; `"C:\\x\\Справка.PDF"` → `"Справка.PDF"`; control chars removed; 300-char name → length 120, ends `.pdf`; `""` → `"document.pdf"`.
    +
    +```python
    +def validate_pdf(upload: UploadedFile) -> None
    +```
    +Raises `ValidationError` (non-field, Russian, names the sanitized file) when: name does not end with `.pdf` (case-insensitive) → «Файл «X»: допускаются только PDF.»; `upload.content_type != PDF_CONTENT_TYPE` → same message; `upload.size == 0` → «Файл «X» пустой.»; `upload.size > MAX_ATTACHMENT_SIZE` → «Файл «X» больше 5 МБ.»; `upload.seek(0); head = upload.read(5); upload.seek(0)`; `head != PDF_SIGNATURE` → «Файл «X» не является PDF.».
    +
    +```python
    +def validate_attachments(uploads: Sequence[UploadedFile]) -> None
    +```
    +`len(uploads) > MAX_ATTACHMENTS` → «Можно приложить не больше 3 файлов.»; then `validate_pdf` for each; collect all messages; raise one `ValidationError(list)`.
    +
    +```python
    +def store_attachment(petition: Petition, upload: File, original_name: str, size: int) -> PetitionAttachment
    +```
    +Must be called inside a transaction (service). Algorithm, up to `MAX_NAME_ATTEMPTS` times:
    +1. `name = attachment_upload_to(None, "")`; `storage = get_private_storage()`.
    +2. If `storage.exists(name)` or `PetitionAttachment.objects.filter(file=name).exists()` → next attempt.
    +3. `upload.seek(0)`; `try: saved = storage.save(name, upload)` / `except FileExistsError: continue`. Assert `saved == name` (if not: `storage.delete(saved)`; raise `RuntimeError`).
    +4. `try: with transaction.atomic(): att = PetitionAttachment.objects.create(petition=petition, file=saved, original_name=sanitize_display_name(original_name), size=size)` / `except IntegrityError: storage.delete(saved); continue`.
    +5. Return `att`.
    +After all attempts → `raise AttachmentStorageError("Не удалось сохранить файл. Попробуйте ещё раз.")` (`class AttachmentStorageError(Exception)` in this module).
    +
    +Tests (`test_files.py`, `FrozenClockMixin, TestCase`):
    +- `test_upload_to_format` — regex `^request_attachments/[0-9a-f]{2}/[0-9a-f]{32}\.pdf$`, prefix equals first 2 chars; filename argument (`"../../evil.exe"`) ignored.
    +- `test_upload_to_uses_uuid4` — `mock.patch("petitions.files.uuid.uuid4", return_value=uuid.UUID(int=1))` → name derived from it.
    +- `test_store_retries_on_existing_file` — patch `uuid4` with `side_effect=[U1, U1, U2]`, pre-create a file at U1's path → stored at U2's path; the pre-existing file content is unchanged.
    +- `test_store_retries_on_db_collision` — an attachment row with U1's path exists (file absent) → stored at U2.
    +- `test_store_gives_up` — `uuid4` always U1 and file exists → `AttachmentStorageError`; no new rows.
    +- `test_db_unique_path` — two rows with the same `file` → `IntegrityError`.
    +- `validate_pdf`: valid; wrong extension; wrong content type; renamed non-PDF (`.pdf`, `application/pdf`, content `MZ...`); empty; 5 MB exactly OK; 5 MB + 1 rejected (use `SimpleUploadedFile` with `b"%PDF-" + b"0" * (n - 5)`); uppercase `.PDF` OK.
    +- `validate_attachments`: 3 OK, 4 rejected; messages for several bad files are all reported.
    +- sanitize tests above.
    +
    +### 5.3 `petitions/selectors.py`
    +```python
    +def petitions_visible_to(user) -> QuerySet[Petition]
    +def attachments_visible_to(user) -> QuerySet[PetitionAttachment]
    +```
    +`petitions_visible_to`: base `Petition.objects.select_related("request_type", "student__group__program__faculty")`; not authenticated/inactive → `none()`; STUDENT with profile → `filter(student__user=user)`; STAFF with profile → `filter(student__group__program__faculty=profile.faculty)`; else `none()`. `attachments_visible_to`: `PetitionAttachment.objects.filter(petition__in=petitions_visible_to(user))`.
    +Tests in `test_services.py::SelectorTests`: student sees own only; staff own faculty only; superuser/anonymous/staff without profile → empty; attachments follow petitions.
    +
    +### 5.4 `petitions/services.py`
    +Exceptions: `class StaleStatusError(ValidationError)` with default message `"Заявка уже изменена, обновите страницу."`. Constant `MAX_OPEN_PER_TYPE = 3`.
    +
    +#### `add_working_days(start: date, days: int) -> date`
    +Counts `days` working days (Mon–Fri) strictly after `start`. `days < 1` → `ValueError`. Tests: Mon+1 → Tue; Fri+1 → Mon; Sat+1 → Mon; Sun+1 → Mon; Fri+5 → next Fri; Wed+10 → Wed two weeks later.
    +
    +#### `submit_petition(student: StudentProfile, request_type: RequestType, comment: str, uploads: Sequence[UploadedFile]) -> Petition`
    +1. `comment = (comment or "").strip()`. Errors (collect, non-field): `not request_type.is_active` → «Этот вид заявки сейчас недоступен.»; `len(comment) > MAX_COMMENT_LENGTH` → «Комментарий слишком длинный.»; `request_type.comment_required and not comment` → «Для этой заявки комментарий обязателен.»; plus `validate_attachments(uploads)` messages. Any → `raise ValidationError(errors)`.
    +2. `stored: list[str] = []`; `try: with transaction.atomic():`
    +   - `StudentProfile.objects.select_for_update().get(pk=student.pk)` (serializes the limit check per student);
    +   - `open_count = Petition.objects.filter(student=student, request_type=request_type, status__in=OPEN_STATUSES).count()`; `>= MAX_OPEN_PER_TYPE` → `ValidationError(f"У вас уже {MAX_OPEN_PER_TYPE} открытые заявки этого вида. Дождитесь их выполнения.")`;
    +   - `now = timezone.now()`; `petition = Petition.objects.create(student=student, request_type=request_type, comment=comment, status=SUBMITTED, created_at=now, status_changed_at=now, expected_ready_date=add_working_days(timezone.localdate(), request_type.processing_days))`;
    +   - `PetitionStatusChange.objects.create(petition=petition, from_status="", to_status=SUBMITTED, actor=student.user, created_at=now)`;
    +   - for each upload: `att = store_attachment(petition, upload, upload.name, upload.size)`; `stored.append(att.file.name)`.
    +   `except BaseException: for name in stored: get_private_storage().delete(name); raise`.
    +3. Return `petition`.
    +- Access: only the student themself (views pass `self.profile`).
    +
    +#### `change_status(petition: Petition, actor: User, expected_status: str, new_status: str, comment: str = "") -> Petition`
    +1. `staff = get_profile_for_role(actor, User.Role.STAFF)` (→ `PermissionDenied` for students/superusers).
    +2. `comment = (comment or "").strip()`; too long → `ValidationError`.
    +3. `with transaction.atomic():`
    +   - `locked = _lock_petition(petition.pk)`; where `def _lock_petition(pk: int) -> Petition: return Petition.objects.select_for_update().select_related("student__group__program").get(pk=pk)`;
    +   - `locked.student.group.program.faculty_id != staff.faculty_id` → `PermissionDenied`;
    +   - `locked.status != expected_status` → `raise StaleStatusError(StaleStatusError.default_message)`;
    +   - `not can_transition(locked.status, new_status)` → `ValidationError(f"Нельзя перевести заявку из «{label(from)}» в «{label(to)}».")`;
    +   - `new_status in COMMENT_REQUIRED_FOR and not comment` → `ValidationError("Укажите причину отклонения.")`;
    +   - `now = timezone.now()`; `PetitionStatusChange.objects.create(petition=locked, from_status=locked.status, to_status=new_status, actor=actor, created_at=now, comment=comment)`; `locked.status = new_status`; `locked.status_changed_at = now`; `locked.save(update_fields=["status", "status_changed_at"])`.
    +4. Return `locked`.
    +
    +#### `add_staff_comment(petition: Petition, actor: User, text: str) -> PetitionComment`
    +1. `staff = get_profile_for_role(actor, STAFF)`; `petition.student.group.program.faculty_id != staff.faculty_id` → `PermissionDenied`.
    +2. `text = (text or "").strip()`; empty → «Комментарий не может быть пустым.»; too long → «Комментарий слишком длинный.».
    +3. `return PetitionComment.objects.create(petition=petition, author=actor, text=text)`. Allowed at any status. Never updates existing rows.
    +
    +Tests (`test_services.py`, `FrozenClockMixin, TestCase`, clock Wed 2026-11-18 12:00):
    +`SubmitTests`: `test_submit_creates_petition_and_history` (status, expected date = Mon 2026-11-23 for 3 working days, 1 history row from "" by the student); `test_comment_required_rejected`; `test_comment_whitespace_only_rejected_when_required`; `test_comment_optional_ok`; `test_comment_too_long`; `test_inactive_type_rejected`; `test_attachments_stored_privately` (file under `settings.PRIVATE_MEDIA_ROOT`, path format, content equal); `test_invalid_attachment_rejected_nothing_stored` (no petition, no file); `test_limit_three_open_per_type` (3 OK, 4th rejected; other type OK; after one becomes ISSUED → OK again); `test_limit_counts_in_progress`; `test_files_removed_on_failure` (patch `store_attachment` to raise on the 2nd file → no petition, first file deleted from disk); `test_student_row_locked` (`mock.patch.object(StudentProfile.objects, "select_for_update", wraps=...)` or capture SQL on PostgreSQL — assert the lock call happens).
    +`TransitionTests`: every allowed transition succeeds and writes history (from, to, actor, time = frozen now, comment); every disallowed one → `ValidationError`, no history; reject without comment → error; reject with comment stored in history; `test_stale_expected_status_rejected` (status IN_PROGRESS, expected SUBMITTED → `StaleStatusError` with «Заявка уже изменена, обновите страницу», status unchanged, no history row); `test_concurrent_take_and_reject` (staff A takes with expected SUBMITTED → ok; staff B rejects with expected SUBMITTED → `StaleStatusError`); `test_student_cannot_transition` (`PermissionDenied`); `test_other_faculty_staff_cannot_transition`; `test_superuser_cannot_transition`; `test_lock_used` (`mock.patch("petitions.services._lock_petition", wraps=_lock_petition)` called once with pk).
    +`CommentTests`: append at every status; two staff of the faculty both add → 2 rows, first unchanged; empty rejected; student → `PermissionDenied`; other faculty staff → `PermissionDenied`; comment after a concurrent transition (stale page) still succeeds.
    +`WorkingDaysTests`: cases above.
    +
    +### 5.5 Forms (`petitions/forms.py`)
    +```python
    +class MultipleFileInput(forms.ClearableFileInput):
    +    allow_multiple_selected = True
    +
    +class MultipleFileField(forms.FileField):
    +    def __init__(self, *args, **kwargs): kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "application/pdf,.pdf"})); super().__init__(*args, **kwargs)
    +    def clean(self, data, initial=None) -> list[UploadedFile]:
    +        if not data: return []
    +        items = data if isinstance(data, (list, tuple)) else [data]
    +        return [super().clean(item, initial) for item in items]
    +
    +class PetitionForm(forms.Form):
    +    comment = forms.CharField(label="Комментарий", required=False, max_length=MAX_COMMENT_LENGTH, widget=forms.Textarea(attrs={"rows": 4}))
    +    files = MultipleFileField(label="PDF-файлы (необязательно, до 3 файлов по 5 МБ)", required=False)
    +    def __init__(self, *args, request_type: RequestType, **kwargs)
    +    def clean_comment(self) -> str
    +    def clean_files(self) -> list[UploadedFile]
    +```
    +- `__init__`: `self.request_type = request_type`; `self.fields["comment"].required = request_type.comment_required`; `self.fields["comment"].help_text = request_type.comment_hint`.
    +- `clean_comment`: strip; required and empty → `ValidationError("Для этой заявки комментарий обязателен.")`.
    +- `clean_files`: `validate_attachments(files)`; return files.
    +Exactly two fields — test `test_form_has_exactly_two_fields`.
    +
    +```python
    +class TransitionForm(forms.Form):
    +    expected_status = forms.ChoiceField(choices=PetitionStatus.choices)
    +    new_status = forms.ChoiceField(choices=PetitionStatus.choices)
    +    comment = forms.CharField(required=False, max_length=MAX_COMMENT_LENGTH)
    +
    +class StaffCommentForm(forms.Form):
    +    text = forms.CharField(label="Комментарий", max_length=MAX_COMMENT_LENGTH, widget=forms.Textarea(attrs={"rows": 3}))
    +```
    +
    +### 5.6 Views (`petitions/views.py`)
    +- `CatalogView(StudentRequiredMixin, TemplateView)` — `types = RequestType.objects.filter(is_active=True)` grouped by kind (two lists).
    +- `SubmitPetitionView(StudentRequiredMixin, FormView)` — `request_type = get_object_or_404(RequestType, pk=type_id, is_active=True)` in `dispatch` after the mixin; `get_form_kwargs` adds `request_type`; `form_valid`: `try: petition = submit_petition(self.profile, self.request_type, form.cleaned_data["comment"], form.cleaned_data["files"])` / `except ValidationError as exc: form.add_error(None, exc); return self.form_invalid(form)`; redirect to `petitions:submitted`. Template uses `enctype="multipart/form-data"`, shows the hint above the textarea when `comment_required`.
    +- `SubmittedView(StudentRequiredMixin, DetailView)` — queryset `petitions_visible_to(user)`, `slug_field = slug_url_kwarg = "public_id"`; shows «Заявка подана», type, short number, expected date, links to detail and list.
    +- `MyPetitionsView(StudentRequiredMixin, ListView)` — `petitions_visible_to(user).order_by("-created_at")`; empty state «Заявок пока нет.» + link to the catalog.
    +- `StudentPetitionDetailView(StudentRequiredMixin, DetailView)` — queryset `petitions_visible_to(user).prefetch_related(Prefetch("history", queryset=PetitionStatusChange.objects.select_related("actor__staff_profile")), Prefetch("staff_comments", queryset=PetitionComment.objects.select_related("author__staff_profile")), "attachments")`; no action forms.
    +- `StaffQueueView(StaffRequiredMixin, ListView)` — filters from GET: `status` ∈ {`"open"` (default), `"all"`, any status value}; invalid → `"open"`; `type` = `RequestType` pk or empty; invalid → ignored. Queryset `petitions_visible_to(user)` + filters, `.order_by("created_at")` (oldest first), annotated `attachment_count=Count("attachments")`. Context: filter choices, selected values, `types` list.
    +- `StaffPetitionDetailView(StaffRequiredMixin, DetailView)` — same prefetch as the student detail + student info (`student__user`, group, 
    …[20,741 more characters truncated]
  ── Thought for 3s
    I'm cleaning up two inconsistencies: the PRIVATE_MEDIA_ROOT default, where the code and the note disagree on how the fallback works, and the download access check for superusers in the access matrix.

    Checking the superuser download case gives a 404 since no attachments are visible to them, and the student request returns 404 as expected. For the status endpoint, a GET from staff hits the method check before any lookup runs, so it should return 405 rather than 404; I'll set the matrix to 405 to remove the ambiguity.
  ── Ran python3 - <<'EOF' p="docs/tasks/TASK-006.md" s=open(p).read() reps=[ ('  PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private_media")))','  PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default="") or str(BASE_DIR / "private_media"))'), ('(empty = default `<repo>/private_media`; `env.str` with empty value → treat `""` as default: `env.str("PRIVATE_MEDIA_ROOT", default="") or str(BASE_DIR / "private_media")`.) `.gitignore`: add `/private_media/`.','(empty or unset = default `<repo>/private_media`.) `.gitignore`: add `/private_media/`.'), ("   - `StudentProfile.objects.select_for_update().get(pk=student.pk)` (serializes the limit check per student);","   - `_lock_student(student.pk)` where `def _lock_student(pk: int) -> None: StudentProfile.objects.select_for_update().filter(pk=pk).values_list(\"pk\", flat=True).get()` (serializes the limit check per student);"), ("`test_student_row_locked` (`mock.patch.object(StudentProfile.objects, \"select_for_update\", wraps=...)` or capture SQL on PostgreSQL — assert the lock call happens).","`test_student_row_locked` (`mock.patch(\"petitions.services._lock_student\", wraps=_lock_student)` → called once with the student pk)."), ("| `/staff/requests/<PA>/status/` GET | 302 | 403 | — | 405 | 404/405 | 403 |","| `/staff/requests/<PA>/status/` GET | 302 | 403 | — | 405 | 405 | 403 |"), ("- **Disk usage**: max 9 open requests × 3 files × 5 MB per student type set; acceptable for the demo.","- **Disk usage**: at most 3 open requests per type × 4 types × 3 files × 5 MB per student at a time; closed requests keep their files. Acceptable for the demo."), ] for a,b in reps:     assert a in s, a[:60]; s=s.replace(a,b) open(p,"w").write(s) EOF bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF' [TASK-006] Planner -> Coder: TASK Spec: docs/tasks/TASK-006.md (approved by the Team lead; feasibility check in section 7, no blockers). Start with AC0: exclude the whole docs/ from ruff. Summary: - New app `petitions` (RequestType, Petition with UUID public_id, PetitionAttachment, PetitionStatusChange history, PetitionComment). Workflow in one table (`petitions/workflow.py`); `change_status` locks the row and compares `expected_status` (stale -> "Заявка уже изменена, обновите страницу"); comments are append-only. - PDF uploads: ≤3 files, ≤5 MB, extension + content type + `%PDF-` signature; stored by `petitions/files.store_attachment` in `core.storage.PrivateFileStorage` (reads settings.PRIVATE_MEDIA_ROOT dynamically, never overwrites, url() raises) at `request_attachments/<2>/<uuid4 hex>.pdf`, DB-unique, bounded retry. Downloads only via `download_attachment` with access checks and attachment headers. - `core.test_runner.ProjectTestRunner` puts PRIVATE_MEDIA_ROOT in a temp dir for all tests. Messages block + "Заявки" nav in base.html. - Seed: 4 exact request types + 7 demo petitions (every status, both faculties) created only if missing. - Follow section 8 order; verification in section 9 (seed with temporary DATABASE_URL and PRIVATE_MEDIA_ROOT). Do not commit. Questions -> me. EOF (2s)
    $ python3 - <<'EOF'
  p="docs/tasks/TASK-006.md"
  s=open(p).read()
  reps=[
  ('  PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private_media")))','  PRIVATE_MEDIA_ROOT = Path(env.str("PRIVATE_MEDIA_ROOT", default="") or str(BASE_DIR / "private_media"))'),
  ('(empty = default `<repo>/private_media`; `env.str` with empty value → treat `""` as default: `env.str("PRIVATE_MEDIA_ROOT", default="") or str(BASE_DIR / "private_media")`.) `.gitignore`: add `/private_media/`.','(empty or unset = default `<repo>/private_media`.) `.gitignore`: add `/private_media/`.'),
  ("   - `StudentProfile.objects.select_for_update().get(pk=student.pk)` (serializes the limit check per student);","   - `_lock_student(student.pk)` where `def _lock_student(pk: int) -> None: StudentProfile.objects.select_for_update().filter(pk=pk).values_list(\"pk\", flat=True).get()` (serializes the limit check per student);"),
  ("`test_student_row_locked` (`mock.patch.object(StudentProfile.objects, \"select_for_update\", wraps=...)` or capture SQL on PostgreSQL — assert the lock call happens).","`test_student_row_locked` (`mock.patch(\"petitions.services._lock_student\", wraps=_lock_student)` → called once with the student pk)."),
  ("| `/staff/requests/<PA>/status/` GET | 302 | 403 | — | 405 | 404/405 | 403 |","| `/staff/requests/<PA>/status/` GET | 302 | 403 | — | 405 | 405 | 403 |"),
  ("- **Disk usage**: max 9 open requests × 3 files × 5 MB per student type set; acceptable for the demo.","- **Disk usage**: at most 3 open requests per type × 4 types × 3 files × 5 MB per student at a time; closed requests keep their files. Acceptable for the demo."),
  ]
  for a,b in reps:
      assert a in s, a[:60]; s=s.replace(a,b)
  open(p,"w").write(s)
  EOF
  bb thread tell thr_ng6cbgatm6 --message-file - <<'EOF'
  [TASK-006] Planner -> Coder: TASK
  Spec: docs/tasks/TASK-006.md (approved by the Team lead; feasibility check in section 7, no blockers). Start with AC0: exclude the whole docs/ from ruff.
  Summary:
  - New app `petitions` (RequestType, Petition with UUID public_id, PetitionAttachment, PetitionStatusChange history, PetitionComment). Workflow in one table (`petitions/workflow.py`); `change_status` locks the row and compares `expected_status` (stale -> "Заявка уже изменена, обновите страницу"); comments are append-only.
  - PDF uploads: ≤3 files, ≤5 MB, extension + content type + `%PDF-` signature; stored by `petitions/files.store_attachment` in `core.storage.PrivateFileStorage` (reads settings.PRIVATE_MEDIA_ROOT dynamically, never overwrites, url() raises) at `request_attachments/<2>/<uuid4 hex>.pdf`, DB-unique, bounded retry. Downloads only via `download_attachment` with access checks and attachment headers.
  - `core.test_runner.ProjectTestRunner` puts PRIVATE_MEDIA_ROOT in a temp dir for all tests. Messages block + "Заявки" nav in base.html.
  - Seed: 4 exact request types + 7 demo petitions (every status, both faculties) created only if missing.
  - Follow section 8 order; verification in section 9 (seed with temporary DATABASE_URL and PRIVATE_MEDIA_ROOT). Do not commit. Questions -> me.
  EOF
    Thread thr_ng6cbgatm6 steered

── Assistant ───────────────────────────────────────────────
Спецификация TASK-006 готова: [docs/tasks/TASK-006.md](docs/tasks/TASK-006.md). Я передал её кодеру. Открытых вопросов в ней нет. Код по задаче ещё не написан.

**Проверка выполнимости пройдена.** Не закоммичен только `plan.md` тимлида. До начала работы проходят:
- все 409 тестов;
- прогон с часами на московской полуночи;
- `check --deploy`;
- ruff и проверка файла CI;
- `seed_demo` дважды на временной базе.

Если исключить из ruff всю папку `docs/`, проверки проходят.

**Основные решения:**
- **Название части проекта — `petitions`.** `requests` перекрыло бы известную библиотеку с тем же именем. `deanery` слишком широкое: чат и уведомления тоже относятся к деканату.
- **Статусы.** Переходы заданы одной таблицей: «Подана» → «В работе» → «Готова» → «Выдана». Из «Подана» и «В работе» можно перейти в «Отклонена», для этого нужен комментарий. Каждая смена статуса записывается в историю: кто, когда, откуда, куда, с каким комментарием. Эти записи понадобятся уведомлениям в TASK-007.
- **Два сотрудника одновременно.** Сервис блокирует заявку и сравнивает текущий статус с тем, который видел сотрудник. Если они разошлись, второй получает «Заявка уже изменена, обновите страницу». Комментарии только добавляются и не конфликтуют ни с чем.
- **PDF-файлы:**
  - не больше трёх файлов по 5 МБ;
  - проверяются расширение, заявленный тип и сигнатура `%PDF-`;
  - имя файла генерируется через `uuid4` по схеме `request_attachments/xx/<32 символа>.pdf`, от пользователя в пути ничего нет;
  - путь уникален в базе, при совпадении имени делается ограниченное число повторных попыток;
  - хранилище никогда не перезаписывает файл и не выдаёт публичную ссылку;
  - скачать файл можно только через страницу с проверкой доступа, и только как вложение.
- **Папка для файлов** задаётся в `PRIVATE_MEDIA_ROOT`. Она лежит вне статики и не отдаётся nginx; в README будет предупреждение. Настройка читается при каждом обращении. Иначе Django запомнил бы путь при загрузке моделей, и тесты не смогли бы его подменить.
- **Тесты не пишут файлы в репозиторий.** Для них сделан свой запуск тестов: на время прогона, включая старые тесты `seed_demo`, папка для файлов временная.
- **Лимит:** не больше трёх открытых заявок одного вида у одного студента.
- **Демо-данные:**
  - 4 вида заявок ровно по списку;
  - 7 заявок во всех статусах, с историей, комментариями и маленькими PDF;
  - в очереди каждого факультета есть хотя бы одна новая заявка.

В `base.html` не было вывода системных сообщений. Я добавил его в план, без него сотрудник не увидит результат своих действий.

Нужно от вас: на сервере не отдавайте папку `PRIVATE_MEDIA_ROOT` через nginx и поставьте `client_max_body_size 20m`. Это будет записано в README.
