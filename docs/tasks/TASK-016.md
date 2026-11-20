# TASK-016: security hardening from PENTEST-1

Author: Planner. Assignee: Coder. Status: ready for implementation.
Base: HEAD 851b3ee (clean tree except the Team lead's `plan.md`; do not touch it).
Source: `docs/security/PENTEST-1.md` (findings PT1-F1 … PT1-F13).

## 1. Goal

Close the PENTEST-1 findings the user decided to fix. No Critical/High findings exist; this is hardening.

### Acceptance criteria

| ID | Finding | Criterion |
|---|---|---|
| AC1 | PT1-F1 | nginx limits `POST` requests to every path that ends in `/login/` (the site login and the admin login under any `ADMIN_URL`) to 10 per minute per client IP, burst 10, answer 429. GET requests are not limited. A site-wide limit of 20 concurrent requests per client IP answers 429. The `proxy_set_header` lines are at the `server` level, so every `location` inherits them. |
| AC2 | PT1-F2 | The login lockout key for an IPv6 client is its /64 network address (e.g. `2001:db8:1:2::`); IPv4 is unchanged; an IPv4-mapped IPv6 address counts as its IPv4 address. No per-account lock across addresses (plan.md 6b). |
| AC3 | PT1-F4 | nginx has catch-all `default_server` blocks: port 80 → `return 444`; port 443 → `ssl_reject_handshake on`. HTTP for the domain and `www` serves ACME and redirects with 301 to `https://<domain>$request_uri` (never `$host`). HTTPS `www` redirects with 301 to the domain. The bootstrap config answers ACME for both names. The runbook issues the certificate with `-d "$DOMAIN" -d "www.$DOMAIN"`. |
| AC4 | PT1-F3 | Every response to a signed-in user has `Cache-Control` with `no-store` and `private` (Django's `add_never_cache_headers`). Responses to requests without a session cookie and static files are unchanged. `SESSION_COOKIE_AGE` stays 14 days. |
| AC5 | PT1-F5 | Every response that passes Django's middleware carries exactly this header (admin included): `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`. Exceptions: a response that already has the header keeps it; with `DEBUG=True`, responses with status ≥ 400 get no header (Django's technical error pages). No new dependency. |
| AC6 | PT1-F7 | `RequestType.comment_hint` is HTML-escaped before it becomes the `help_text` of the comment field. |
| AC7 | PT1-F8 | `?type=` on the staff queue is used only if it is 1–18 ASCII digits; any other value (also 19+ digits) is ignored like a non-numeric value. No HTTP 500. All other integer inputs are already safe (section 5, item 6) and get regression tests. |
| AC8 | PT1-F10 | The chat idempotency token is looked up per author; the unique constraint becomes (`dialog`, `author`, `client_token`); migration `chat/0002_message_token_per_author`. |
| AC9 | PT1-F13 | `deploy/backup.sh` passes the database password to `pg_dump` through the libpq environment, never on the command line; other behaviour is unchanged. `deploy/gunicorn.conf.py`: `secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}`. `deploy/systemd/deanery.service`: `ProtectSystem=strict` and the sandbox options listed in F11. `docs/DEPLOY.md`: `DEMO_PASSWORD` is removed from the env file right after the one-time `seed_demo` on 2026-11-22. |
| AC10 | PT1-F6 (part) | The runbook creates the service account with `--shell /usr/sbin/nologin` and has no SSH key step for it. A new runbook step 21 hardens a server installed before this task. |
| AC11 | — | CI runs `pip-audit --requirement requirements.txt` in its own step with `pip-audit==2.10.1`, not in any requirements file. Nothing to fix today (section 5, item 9). |
| AC12 | — | Full suite, `--parallel 2`, `run_tests_at.py`, ruff, `bash -n`, `gunicorn --check-config`, CI YAML, `makemigrations --check` all pass. |

## 2. Out of scope

- Accepted by the user: PT1-F6 rest, PT1-F9, PT1-F11, PT1-F12, TLS cipher list and OCSP, the HSTS raise.
- Not requested: rejecting superusers in the public login form (PT1-F2 point 3), a per-username limit across
  addresses (forbidden, plan.md 6b), shorter sessions, a `DisallowedHost` null logger (PT1-F4; the catch-all
  servers keep foreign hosts away from Django), `psql "$DATABASE_URL"` in the manual restore command.
- `plan.md`, `CHANGELOG.md`, `README.md`, `docs/security/*`, old specs.

## 3. Design decisions

- **D1. Login rate limit by path pattern, not by the admin path.** The limited location is the regex
  `^/(?:[A-Za-z0-9_-]+/)*login/$`. It matches `/login/` and `/<ADMIN_URL>login/` for every valid `ADMIN_URL`
  (`config/env_utils.py:33` allows `[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*`). This differs from the request ("the
  runbook renders the admin path") on purpose: the secret admin path does not go into `/etc/nginx` (world-readable),
  the template needs no extra placeholder, and a changed `ADMIN_URL` needs no nginx change. The only other paths
  the pattern matches do not exist (404 from Django).
- **D2. Only POST is counted, burst 10.** A `map` gives an empty key for every method except POST; nginx does not
  count requests with an empty key. So loading the login page never costs a slot, and jurors behind one NAT
  address can sign in together (10 at once, then one per 6 s). One failed login costs ≈ 0.2 s CPU (PENTEST-1), so
  one address can use at most ≈ 3 % of one CPU after the burst.
- **D3. limit_conn 20** per address for the whole HTTPS site (HTTP/2 counts every active stream). A page loads
  ≈ 7 files; static responses take milliseconds.
- **D4. Zones in the site file.** `map`, `limit_req_zone` and `limit_conn_zone` must be in the `http` context.
  Ubuntu's `nginx.conf` includes `sites-enabled/*` inside `http {}`, so they stay in `deploy/nginx/deanery.conf`;
  no change to the stock `nginx.conf`.
- **D5. Catch-all 443 with `ssl_reject_handshake on`** (nginx ≥ 1.19.4; Ubuntu 24.04 has 1.24): no certificate in
  that block, the TLS handshake for an unknown SNI or no SNI fails, so the domain is not revealed for the IP. Both
  catch-all blocks use the same `listen` options as the domain blocks (`ssl http2`), the 1.24 syntax the existing
  test requires. The stock `default` site is already removed in step 12 (two `default_server` on one port would
  fail `nginx -t`).
- **D6. One CSP for the whole site, the admin included.** Measured (section 5, item 4): with the strict policy,
  69 Django admin pages (every model's list, first change page, add page; date, time, `filter_horizontal`,
  inline "add row" widgets clicked) and 40 student + 40 staff pages give zero CSP violations in Chrome. Django 5.2's
  admin has no inline scripts (`<script id=… src=…>` only) and its single inline `<style>` (`change_list.html:16`)
  renders only when a `ModelAdmin` sets both `actions_on_top` and `actions_on_bottom` to false — none does. Admin
  JavaScript changes styles through CSSOM (`el.style.x = …`), which CSP allows. So no relaxed admin policy is
  needed. If a future admin page needs it, the fallback is `style-src 'self' 'unsafe-inline'` for the admin path
  only (scripts stay strict).
- **D7. No `data:` in `img-src`.** No template, CSS or JS of the project uses a `data:` URI (grep, section 5,
  item 4); the favicon is `static/img/favicon.svg`, the logo and the bell are inline SVG markup (allowed). CSS
  `url(#map-hatch)` refers to an element in the page, not a fetch.
- **D8. CSP middleware position:** right after WhiteNoise. WhiteNoise answers static files before it, so static
  files are unchanged; every Django response (views, redirects of `LoginRequiredMiddleware`, CSRF 403, 404/500)
  passes through it. With `DEBUG=True` responses with status ≥ 400 are skipped because Django's technical pages
  use inline CSS/JS; production has `DEBUG=False`.
- **D9. no-store middleware position:** last in `MIDDLEWARE` (after authentication). It returns early when the
  request has no session cookie, so it never touches the session of anonymous requests (no new `Vary: Cookie`).
  It uses `add_never_cache_headers` (the same headers as the existing `never_cache` views). Chrome check: after
  logout, Back shows the login page, not `/grades/` (section 5, item 5).
- **D10. IPv6 key = network address of the /64** (`str(IPv6Network((addr, 64), strict=False).network_address)`),
  a valid IP for the existing `GenericIPAddressField` (`inet` on PostgreSQL): no migration. The new function
  `throttle_ip()` is applied in the form; `get_client_ip()` stays unchanged (its tests stay).
- **D11. Type filter by regex**, the same pattern as the chat `after` parameter (`chat/views.py:34`): 1–18 ASCII
  digits always fit the 64-bit id range of SQLite and PostgreSQL. `[0-9]` (not `\d`) rejects non-ASCII digits.
- **D12. Chat token per author** needs the constraint change: with the old (`dialog`, `client_token`) constraint a
  staff reply that reuses a student's token would raise `IntegrityError` (HTTP 500) instead of being silently
  dropped. Existing rows satisfy the new, wider constraint (checked on a seeded database).
- **D13. backup.sh: libpq environment.** The script parses `DATABASE_URL` (`postgres://user:pass@host:port/name`,
  the format of `.env.production.example`; the password is hex from `openssl rand -hex 24`) and exports
  `PGUSER PGPASSWORD PGHOST PGPORT PGDATABASE`, then runs `pg_dump --no-owner --no-privileges` without a URL and
  unsets `DATABASE_URL`. On Linux the environment of a process is readable only by its owner and root
  (`/proc/<pid>/environ`), the command line by everybody (`ps`). A URL that does not match stops the script with a
  clear message before any file is written. A new optional variable `DEANERY_ENV_FILE` (default
  `/etc/deanery/deanery.env`) lets the tests run the real script with a stub `pg_dump`.
- **D14. systemd sandbox: what the app writes at run time.** (a) Uploads into `PRIVATE_MEDIA_ROOT`
  (`core/storage.py`) — the two directories in `ReadWritePaths`. (b) Temporary files: Django spools uploads larger
  than 2.5 MB to `tempfile.gettempdir()` (`/tmp`), gunicorn's worker heartbeat files go to `/tmp` — `PrivateTmp=true`
  gives a private writable `/tmp` even with `ProtectSystem=strict`. (c) Logs go to stdout/stderr (journald) —
  file descriptors opened by systemd. (d) The database over TCP `localhost:5432` (`AF_INET`/`AF_INET6`). Nothing
  else: sessions, cache (local memory), static files (collected before, read-only), `.pyc` files (written by
  `manage.sh` runs outside the unit; a failed write of `__pycache__` is silent). Grep evidence in section 5,
  item 7. Port 8000 needs no capability, so `CapabilityBoundingSet=` is empty. `ReadWritePaths` directories must
  exist (step 6 creates both).
- **D15. pip-audit pinned in the CI step** (2.10.1, 2026-06-10, Python ≥ 3.10). It is not in
  `requirements-dev.txt`, so local environments stay small. It resolves `requirements.txt` in its own temporary
  environment.

## 4. Files and functions

Create: `core/middleware.py`, `core/tests/test_middleware.py`, `chat/migrations/0002_message_token_per_author.py`
(generate it, do not write it by hand: `python manage.py makemigrations chat --name message_token_per_author`).
Change: `config/settings.py`, `accounts/throttling.py`, `accounts/forms.py`, `petitions/forms.py`,
`petitions/views.py`, `chat/models.py`, `chat/services.py`, `deploy/nginx/deanery.conf`,
`deploy/nginx/deanery-bootstrap.conf`, `deploy/gunicorn.conf.py`, `deploy/systemd/deanery.service`,
`deploy/backup.sh`, `docs/DEPLOY.md`, `.github/workflows/ci.yml`, and the tests in section 7.

The code below is the exact code that passed all checks in section 5 (the diffs are against HEAD 851b3ee; apply
them by editing the files, never with git commands). Keep comments as written.

### F1. `core/middleware.py` (new)

````python
"""Security response headers: Content-Security-Policy and no-store for signed-in users."""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.cache import add_never_cache_headers

CSP_HEADER = "Content-Security-Policy"

# One strict policy for every page, the Django admin included (TASK-016): the templates
# and the Django 5.2 admin have no inline scripts, inline styles, inline event handlers,
# external URLs or data: URIs.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        # Django's technical error pages (DEBUG only) use inline styles and scripts.
        if settings.DEBUG and response.status_code >= 400:
            return response
        if CSP_HEADER not in response:
            response[CSP_HEADER] = CONTENT_SECURITY_POLICY
        return response


class PrivateCacheMiddleware:
    """Pages of a signed-in user must not stay in the browser cache after logout."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        # Without a session cookie the user is anonymous; do not touch the session then.
        if settings.SESSION_COOKIE_NAME not in request.COOKIES:
            return response
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            add_never_cache_headers(response)
        return response
````

### F2. `config/settings.py` — middleware order

````diff
--- a/config/settings.py
+++ b/config/settings.py
@@ -53,6 +53,7 @@
 MIDDLEWARE = [
     "django.middleware.security.SecurityMiddleware",
     "whitenoise.middleware.WhiteNoiseMiddleware",
+    "core.middleware.ContentSecurityPolicyMiddleware",
     "django.contrib.sessions.middleware.SessionMiddleware",
     "django.middleware.common.CommonMiddleware",
     "django.middleware.csrf.CsrfViewMiddleware",
@@ -60,6 +61,7 @@
     "django.contrib.auth.middleware.LoginRequiredMiddleware",
     "django.contrib.messages.middleware.MessageMiddleware",
     "django.middleware.clickjacking.XFrameOptionsMiddleware",
+    "core.middleware.PrivateCacheMiddleware",
 ]
 
 LOGIN_URL = "accounts:login"
````

### F3. `accounts/throttling.py::throttle_ip` and `accounts/forms.py`

````diff
--- a/accounts/throttling.py
+++ b/accounts/throttling.py
@@ -42,6 +42,23 @@
         return UNKNOWN_IP
 
 
+def throttle_ip(ip: str) -> str:
+    """Lockout key for a client address: IPv4 as is, IPv6 by its /64 network.
+
+    One IPv6 client usually owns a whole /64 and could take a new address for every
+    attempt. The key is the network address (a valid IP, e.g. "2001:db8:1:2::").
+    """
+    try:
+        address = ipaddress.ip_address(ip)
+    except ValueError:
+        return UNKNOWN_IP
+    if isinstance(address, ipaddress.IPv6Address):
+        if address.ipv4_mapped is not None:
+            return str(address.ipv4_mapped)
+        return str(ipaddress.IPv6Network((address, 64), strict=False).network_address)
+    return str(address)
+
+
 def is_locked(username: str, ip: str, now: datetime) -> bool:
     return LoginThrottle.objects.filter(
         username_key=normalize_username(username), ip_address=ip, locked_until__gt=now
````

````diff
--- a/accounts/forms.py
+++ b/accounts/forms.py
@@ -7,7 +7,7 @@
 from django.utils.decorators import method_decorator
 from django.views.decorators.debug import sensitive_variables
 
-from .throttling import get_client_ip, is_locked, register_failure, reset_failures
+from .throttling import get_client_ip, is_locked, register_failure, reset_failures, throttle_ip
 
 
 class ThrottledLoginFormMixin:
@@ -19,7 +19,7 @@
     @method_decorator(sensitive_variables())
     def clean(self) -> dict[str, Any]:
         username = self.cleaned_data.get("username") or ""
-        ip = get_client_ip(self.request)
+        ip = throttle_ip(get_client_ip(self.request))
         now = timezone.now()
         if username and is_locked(username, ip, now):
             raise ValidationError(self.error_messages["locked"], code="locked")
````

### F4. `petitions/forms.py` — escaped hint

````diff
--- a/petitions/forms.py
+++ b/petitions/forms.py
@@ -1,6 +1,7 @@
 """Forms for petitions."""
 
 from django import forms
+from django.utils.html import escape
 
 from petitions.files import validate_attachments
 from petitions.models import MAX_COMMENT_LENGTH, SUBJECT_MAX_LENGTH, PetitionStatus, RequestType
@@ -43,7 +44,8 @@
         super().__init__(*args, **kwargs)
         self.request_type = request_type
         self.fields["comment"].required = request_type.comment_required
-        self.fields["comment"].help_text = request_type.comment_hint
+        # Django renders help_text without escaping; the hint is admin-entered text.
+        self.fields["comment"].help_text = escape(request_type.comment_hint)
         if not request_type.subject_required:
             del self.fields["subject"]
 
````

### F5. `petitions/views.py::StaffQueueView.get_queryset` — type filter

````diff
--- a/petitions/views.py
+++ b/petitions/views.py
@@ -1,6 +1,7 @@
 """Views for the petitions app."""
 
 import logging
+import re
 
 from django.contrib import messages
 from django.core.exceptions import ValidationError
@@ -28,7 +29,9 @@
 
 logger = logging.getLogger(__name__)
 
+_TYPE_ID_RE = re.compile(r"[0-9]{1,18}")
 
+
 class CatalogView(StudentRequiredMixin, TemplateView):
     template_name = "petitions/catalog.html"
 
@@ -130,11 +133,9 @@
         else:
             qs = qs.filter(status__in=OPEN_STATUSES)
         type_id = self.request.GET.get("type", "")
-        if type_id:
-            try:
-                qs = qs.filter(request_type_id=int(type_id))
-            except (TypeError, ValueError):
-                pass
+        # At most 18 digits: always inside the 64-bit id range of the database (PT1-F8).
+        if _TYPE_ID_RE.fullmatch(type_id):
+            qs = qs.filter(request_type_id=int(type_id))
         return qs.order_by("created_at").annotate(attachment_count=Count("attachments"))
 
     def get_context_data(self, **kwargs):
````

### F6. `chat/services.py::_idempotent_message` and `chat/models.py`

````diff
--- a/chat/services.py
+++ b/chat/services.py
@@ -33,10 +33,10 @@
     return []
 
 
-def _idempotent_message(dialog: Dialog, client_token: UUID | None) -> Message | None:
+def _idempotent_message(dialog: Dialog, author: User, client_token: UUID | None) -> Message | None:
     if client_token is None:
         return None
-    return dialog.messages.filter(client_token=client_token).first()
+    return dialog.messages.filter(client_token=client_token, author=author).first()
 
 
 def send_student_message(student: StudentProfile, text: str, client_token: UUID | None) -> Message:
@@ -49,7 +49,7 @@
         dialog, _ = Dialog.objects.get_or_create(student=student)
         dialog = Dialog.objects.select_for_update().get(pk=dialog.pk)
 
-        existing = _idempotent_message(dialog, client_token)
+        existing = _idempotent_message(dialog, student.user, client_token)
         if existing is not None:
             return existing
 
@@ -96,7 +96,7 @@
         if locked is None:
             raise PermissionDenied
 
-        existing = _idempotent_message(locked, client_token)
+        existing = _idempotent_message(locked, actor, client_token)
         if existing is not None:
             return existing
 
````

````diff
--- a/chat/models.py
+++ b/chat/models.py
@@ -70,9 +70,9 @@
                 name="chat_message_author_role_value",
             ),
             models.UniqueConstraint(
-                fields=["dialog", "client_token"],
+                fields=["dialog", "author", "client_token"],
                 condition=models.Q(client_token__isnull=False),
-                name="chat_message_unique_client_token",
+                name="chat_message_unique_author_client_token",
             ),
             models.UniqueConstraint(
                 fields=["seed_key"],
````

Then generate the migration; the generated file must contain exactly these operations:

````python
# Generated by Django 5.2.19 on 2026-11-20 16:16

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='message',
            name='chat_message_unique_client_token',
        ),
        migrations.AddConstraint(
            model_name='message',
            constraint=models.UniqueConstraint(condition=models.Q(('client_token__isnull', False)), fields=('dialog', 'author', 'client_token'), name='chat_message_unique_author_client_token'),
        ),
    ]
````

### F7. `deploy/nginx/deanery.conf` (whole file)

````nginx
# Deanery prototype. Static files are served by Django/WhiteNoise; nginx serves no project files.
# PRIVATE_MEDIA_ROOT must never get a location here (attachments go through Django access checks).
# This file is included inside the http {} block (sites-enabled), so the zones below are valid here.

# Login forms: POST requests per client IP (PT1-F1). GET requests have an empty key: not limited.
map $request_method $deanery_login_key {
    POST    $binary_remote_addr;
    default "";
}
limit_req_zone $deanery_login_key zone=deanery_login:10m rate=10r/m;
# Concurrent requests per client IP, whole site.
limit_conn_zone $binary_remote_addr zone=deanery_conn:10m;

# Requests by IP address or for any other host name: close the connection (PT1-F4).
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    server_tokens off;
    return 444;
}

server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name _;
    server_tokens off;
    ssl_reject_handshake on;
}

# HTTP for the domain and www: ACME challenges, everything else to the HTTPS domain.
server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;
    server_tokens off;

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        default_type "text/plain";
    }

    location / {
        return 301 https://example.com$request_uri;
    }
}

# HTTPS www: redirect to the domain. The certificate covers both names.
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.example.com;
    server_tokens off;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_tickets off;

    return 301 https://example.com$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com;
    server_tokens off;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    client_max_body_size 20m;

    limit_conn deanery_conn 20;
    limit_conn_status 429;
    limit_req_status 429;

    # Not set by Django; X-Frame-Options, nosniff, Referrer-Policy, CSP and HSTS come from Django.
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # Server level: every location below inherits these.
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;
    proxy_connect_timeout 5s;
    proxy_read_timeout 60s;

    # /login/ and the admin login /<ADMIN_URL>login/ (any path ending in /login/).
    location ~ ^/(?:[A-Za-z0-9_-]+/)*login/$ {
        limit_req zone=deanery_login burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
````

### F8. `deploy/nginx/deanery-bootstrap.conf`

````diff
--- a/deploy/nginx/deanery-bootstrap.conf
+++ b/deploy/nginx/deanery-bootstrap.conf
@@ -2,7 +2,7 @@
 server {
     listen 80;
     listen [::]:80;
-    server_name example.com;
+    server_name example.com www.example.com;
     server_tokens off;
 
     location ^~ /.well-known/acme-challenge/ {
````

### F9. `deploy/gunicorn.conf.py`

````diff
--- a/deploy/gunicorn.conf.py
+++ b/deploy/gunicorn.conf.py
@@ -18,3 +18,5 @@
 loglevel = "info"
 capture_output = True
 control_socket_disable = True
+# Trust only the scheme header that nginx always overwrites (PT1-F13).
+secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
````

### F10. `deploy/backup.sh` (whole file; keep mode 755, edit in place)

````bash
#!/usr/bin/env bash
# Daily backup: gzip-compressed pg_dump + tar.gz of PRIVATE_MEDIA_ROOT; keeps KEEP_DAYS days.
set -euo pipefail
umask 077
# Start from / so the script works from any directory (find restores the start directory).
cd /
BACKUP_DIR="${BACKUP_DIR:-/srv/deanery/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
# DEANERY_ENV_FILE overrides the env file path (used by the tests).
ENV_FILE="${DEANERY_ENV_FILE:-/etc/deanery/deanery.env}"
set -a
. "$ENV_FILE"
set +a
# The password goes to pg_dump through the libpq environment, never on the command line (PT1-F13).
DB_URL_RE='^postgres(ql)?://([^:/@]+):([^@]+)@([^:/@]+):([0-9]+)/([^/?]+)$'
if [[ ! "$DATABASE_URL" =~ $DB_URL_RE ]]; then
    echo "backup failed: DATABASE_URL must look like postgres://user:password@host:port/name" >&2
    exit 1
fi
export PGUSER="${BASH_REMATCH[2]}" PGPASSWORD="${BASH_REMATCH[3]}" PGHOST="${BASH_REMATCH[4]}"
export PGPORT="${BASH_REMATCH[5]}" PGDATABASE="${BASH_REMATCH[6]}"
unset DATABASE_URL
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
pg_dump --no-owner --no-privileges | gzip -9 > "$BACKUP_DIR/db-$STAMP.sql.gz"
tar -czf "$BACKUP_DIR/media-$STAMP.tar.gz" -C "$(dirname "$PRIVATE_MEDIA_ROOT")" "$(basename "$PRIVATE_MEDIA_ROOT")"
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'media-*.tar.gz' \) -mtime +"$((KEEP_DAYS - 1))" -delete
echo "backup ok: $STAMP"
````

### F11. `deploy/systemd/deanery.service` (whole file)

````ini
[Unit]
Description=Deanery prototype (gunicorn)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=<APP_USER>
Group=<APP_USER>
WorkingDirectory=/srv/deanery/app
EnvironmentFile=/etc/deanery/deanery.env
ExecStart=/srv/deanery/venv/bin/gunicorn -c deploy/gunicorn.conf.py config.wsgi:application
Restart=on-failure
RestartSec=5
KillMode=mixed
TimeoutStopSec=35
# Sandbox (PT1-F13). At run time the app writes only uploads to PRIVATE_MEDIA_ROOT and
# temporary files (large uploads, gunicorn heartbeats) to its private /tmp.
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
CapabilityBoundingSet=
ReadWritePaths=/srv/deanery/private_media /srv/deanery/private_media_trial

[Install]
WantedBy=multi-user.target
````

### F12. `docs/DEPLOY.md`

Changes: step 0 (A records for `$DOMAIN` and `www.$DOMAIN`; SSH key for your own sudo user, never for
`$APP_USER`), step 6 (`--shell /usr/sbin/nologin` and one sentence), step 12 (`-d "$DOMAIN" -d "www.$DOMAIN"`),
step 15 (three more smoke checks), step 16 (remove `DEMO_PASSWORD` after `seed_demo`), new step 21 at the end.
Steps 0–20 keep their numbers. Do not run `ruff format` on `docs/`.

````diff
--- a/docs/DEPLOY.md
+++ b/docs/DEPLOY.md
@@ -20,12 +20,14 @@
 
 You need:
 
-- a domain whose `A` record already points at the server IP;
-- an SSH key you created and installed on the server:
+- a domain whose `A` records for `$DOMAIN` and `www.$DOMAIN` already point at
+  the server IP;
+- an SSH key you created and installed for your own sudo user (never for
+  `$APP_USER`: the service account has no login shell and no SSH key):
 
 ```bash
 ssh-keygen -t ed25519
-ssh-copy-id "$APP_USER"@<server-ip>
+ssh-copy-id <your-sudo-user>@<server-ip>
 ```
 
 Keep one SSH session open until step 4 (SSH hardening) is verified.
@@ -83,13 +85,15 @@
 ## 6. App user, directories, code
 
 ```bash
-sudo adduser --system --group --home /srv/deanery --shell /bin/bash "$APP_USER"
+sudo adduser --system --group --home /srv/deanery --shell /usr/sbin/nologin "$APP_USER"
 sudo -u "$APP_USER" git clone "$REPO_URL" /srv/deanery/app
 sudo -u "$APP_USER" mkdir -p /srv/deanery/private_media /srv/deanery/private_media_trial /srv/deanery/backups
 sudo chmod 750 /srv/deanery/private_media /srv/deanery/private_media_trial && sudo chmod 700 /srv/deanery/backups
 sudo mkdir -p /var/www/letsencrypt
 ```
 
+`sudo -u "$APP_USER" <command>` still works with the `nologin` shell.
+
 ## 7. Python venv
 
 ```bash
@@ -167,7 +171,7 @@
 sudo ln -sf /etc/nginx/sites-available/deanery /etc/nginx/sites-enabled/deanery
 sudo rm -f /etc/nginx/sites-enabled/default
 sudo nginx -t && sudo systemctl reload nginx
-sudo certbot certonly --webroot -w /var/www/letsencrypt -d "$DOMAIN" --email <your e-mail> --agree-tos --no-eff-email --deploy-hook "systemctl reload nginx"
+sudo certbot certonly --webroot -w /var/www/letsencrypt -d "$DOMAIN" -d "www.$DOMAIN" --email <your e-mail> --agree-tos --no-eff-email --deploy-hook "systemctl reload nginx"
 ```
 
 ## 13. nginx full site
@@ -200,11 +204,17 @@
 
 ```bash
 curl -sI http://$DOMAIN/ | head -1
+curl -sI https://www.$DOMAIN/ | grep -iE '^(HTTP|location)'
 curl -s https://$DOMAIN/health/
-curl -s -o /dev/null -w '%{http_code}' https://$DOMAIN/private_media/
+curl -s -o /dev/null -w '%{http_code}\n' https://$DOMAIN/private_media/
+curl -sI https://$DOMAIN/login/ | grep -i '^content-security-policy'
+curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: other.example' http://127.0.0.1/
 ```
 
-Expected: `http://` → 301 to https; `/health/` → ok; `/private_media/` → 404.
+Expected: `http://` → 301 to https; `https://www.` → 301 to `https://$DOMAIN/`;
+`/health/` → ok; `/private_media/` → 404; the login page has a
+`Content-Security-Policy` header; a foreign Host → `000` (nginx closes the
+connection).
 In the browser: the login page, the admin at `https://$DOMAIN/<ADMIN_URL>`.
 On the **trial** database run `$M seed_demo` once, then open one page per role
 (student: Расписание, Заявки, Чат; staff: Заявки, Чаты); upload a PDF to a
@@ -230,9 +240,13 @@
 M="sudo -u $APP_USER /srv/deanery/app/deploy/manage.sh"
 $M migrate
 $M seed_demo
+sudo sed -i '/^DEMO_PASSWORD=/d' /etc/deanery/deanery.env
 sudo systemctl restart deanery
 ```
 
+The app does not read `DEMO_PASSWORD` at run time; only `seed_demo` needs it, so
+it is removed from the env file right after seeding.
+
 Run `seed_demo` exactly once; do not schedule it as a recurring job. Repeat
 step 15 (without seeding). Optionally drop `deanery_trial` and empty
 `private_media_trial` after 2026-11-28.
@@ -307,3 +321,37 @@
 - 413 Request Entity Too Large → `client_max_body_size` (20m).
 - Locked logins / wrong client IP → `CLIENT_IP_HEADER` and the `X-Real-IP`
   header set by nginx.
+
+## 21. One-time hardening of a server installed before TASK-016
+
+Run after the update procedure (step 17) has pulled the TASK-016 code.
+
+```bash
+sudo usermod --shell /usr/sbin/nologin "$APP_USER"
+getent passwd "$APP_USER"
+sudo ls -la /srv/deanery/.ssh 2>/dev/null || echo "no .ssh directory"
+sudo certbot certificates
+```
+
+`getent` must end with `/usr/sbin/nologin`. `certbot certificates` must list
+both `$DOMAIN` and `www.$DOMAIN` for the certificate in
+`/etc/letsencrypt/live/$DOMAIN/`; if `www` is missing, run the `certbot
+certonly` command of step 12 with `--expand`. Remove the temporary `www`
+redirect site (it now lives in the template), then install the new nginx site
+and the new systemd unit:
+
+```bash
+sudo cp /etc/nginx/sites-available/deanery /root/deanery.nginx.bak
+sudo cp /etc/systemd/system/deanery.service /root/deanery.service.bak
+sudo rm /etc/nginx/sites-enabled/<temporary www site>
+sed "s/example.com/$DOMAIN/g" /srv/deanery/app/deploy/nginx/deanery.conf | sudo tee /etc/nginx/sites-available/deanery > /dev/null
+sudo nginx -t && sudo systemctl reload nginx
+sed "s/<APP_USER>/$APP_USER/g" /srv/deanery/app/deploy/systemd/deanery.service | sudo tee /etc/systemd/system/deanery.service > /dev/null
+sudo systemd-analyze verify /etc/systemd/system/deanery.service
+sudo systemctl daemon-reload && sudo systemctl restart deanery
+systemctl status deanery
+systemd-analyze security deanery | tail -1
+```
+
+Then repeat the smoke check (step 15), upload and download a PDF as a student,
+and run `sudo -u "$APP_USER" /srv/deanery/app/deploy/backup.sh` once.
````

### F13. `.github/workflows/ci.yml`

````diff
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -24,6 +24,10 @@
             requirements-dev.txt
       - name: Install dependencies
         run: python -m pip install -r requirements-dev.txt
+      - name: Dependency audit
+        run: |
+          python -m pip install pip-audit==2.10.1
+          pip-audit --requirement requirements.txt --progress-spinner off
       - name: Shell syntax
         run: bash -n deploy/backup.sh deploy/manage.sh
       - name: gunicorn config
````

## 5. Feasibility check

1. **Baseline** — HEAD 851b3ee copy (`git archive`, no `.env`): 1141 tests OK (TASK-015-FIX count; the commits
   after it change only docs).
2. **Full change applied** — copy `$TMPDIR/t016` with F1–F13 and the tests of section 7:
   `manage.py test --parallel` → `Ran 1181 tests … OK` (`$TMPDIR/test-t016-full-20261120-135146.log`, 00:52 MSK
   21.11); `--parallel 2` → 1181 OK (`$TMPDIR/test-t016-p2-20261120-135324.log`); `scripts/run_tests_at.py
   2027-03-01T12:00:00` → 1181 OK (`$TMPDIR/test-t016-frozen-20261120-135445.log`, 00:57 MSK). `ruff check .`
   and `ruff format --check .` clean. The code-only part (F1–F6, no new tests) also passed the old 1141 tests
   (`$TMPDIR/test-t016-code-20261120-081725.log`): no existing behaviour broke.
3. **New tests fail on HEAD** — the new and changed test modules against the HEAD code: 14 failures + 6 errors,
   all expected: every new nginx/systemd/runbook/backup/gunicorn/CI test, `test_comment_hint_escaped`,
   `test_same_token_other_author_kept`, `test_client_token_unique_per_dialog_and_author` (IntegrityError),
   `test_type_filter_out_of_range_ignored` (`OverflowError: Python int too large to convert to SQLite INTEGER`
   — the PENTEST-1 500), import errors of `test_middleware` and `test_throttling` (`throttle_ip`, `core.middleware`
   missing). Tests that pass on HEAD are regression guards (huge URL ids → 404, 18-digit type → empty list, no
   lock across IPv4 addresses) (`$TMPDIR/test-t016-newtests-on-head-20261120-135242.log`).
4. **CSP in a real browser** — headless Chrome (bb browser-automation) on `runserver` with a seeded temporary
   database: crawl of 40 pages as `student1` and 40 as `staff1` (all links from the pages, 200 each) → zero
   violations (console "Refused to…" and `securitypolicyviolation` events). Positive control: an injected inline
   script and a `style` attribute on `/` → 4 violation reports, so the listener works. Admin with the strict
   policy: 69 pages (all models; list, first change page, add page; date/time shortcuts, `filter_horizontal`
   chooser, inline "add row" clicked; user list search and select-all) → zero violations. Grep: no `<script>`
   without `src`, no `style=`/`<style`, no `on…=` handlers, no `javascript:`, no external URL, no `data:` in
   project templates, CSS or JS (`static/js/chat.js` uses `DOMParser`/`importNode`, allowed).
5. **No-store in a real browser** — log in as `student1`, open `/grades/` (`Cache-Control: max-age=0, no-cache,
   no-store, must-revalidate, private`), log out, press Back → `/login/?next=/grades/` with "Вход", not the grades.
   PENTEST-1 showed the grades page here.
6. **Integer inputs** — with HEAD code every URL kwarg with 26 digits gives 404 (Django 5.2 handles out-of-range
   primary-key lookups): `/requests/new/<n>/`, `/staff/students/<n>/`, `…/grades/`, `…/grades/<term>/`,
   `/staff/schedule/<n>/`, `/staff/schedule/<n>/<date>/`, `/map/floor/<n>/` (Python membership check). Chat
   `after` is limited to 18 digits (`chat/views.py:34`, 400 otherwise). Forms use `ChoiceField`/`UUIDField`/
   `DateField` only. The only unsafe read is `petitions/views.py:135` (F5).
7. **Run-time writes (D14)** — grep of non-test code for `open(`, `tempfile`, `mkdir`, `write`, `FileSystemStorage`,
   `.save(` on storages: only `core/storage.py` (`PRIVATE_MEDIA_ROOT`) and `petitions/files.py` through it.
   `CACHES` not set (local memory). `STATIC_ROOT` filled by `collectstatic` before start. gunicorn 26:
   `worker_tmp_dir` default → `/tmp`; `control_socket_disable = True` (no `$HOME/.gunicorn`). `gunicorn
   --check-config` with F9 → OK; `secure_scheme_headers` accepted.
8. **backup.sh** — real script, stub `pg_dump` on `PATH`, temporary env file (test F14 below): exit 0, both
   archives written, `pg_dump` arguments exactly `--no-owner --no-privileges`, the password only in `PGPASSWORD`,
   `DATABASE_URL` not in `pg_dump`'s environment. A `sqlite:///` URL → exit ≠ 0 with the message, no backup
   directory created. `bash -n` OK. Works on macOS (BSD tar/find) and is written for GNU tools (CI, server).
9. **Dependencies** — `pip-audit` could not be installed here (sandbox TLS to PyPI fails; running outside the
   sandbox was denied). Instead the OSV database (pip-audit's data source) was queried for every installed runtime
   package: Django 5.2.19, django-environ 0.14.0, whitenoise 6.12.0, psycopg 3.3.8, psycopg-binary 3.3.8,
   gunicorn 26.2.0, asgiref 3.13.0, sqlparse 0.6.1, typing-extensions 4.16.0 → no known vulnerability. Control:
   Django 5.2.0 → 70 entries, so the query works. pip-audit 2.10.1 exists on PyPI (2026-06-10, Python ≥ 3.10;
   CI uses 3.12). Expected first CI result: no findings.
10. **Migration and seeding** — a database migrated and seeded with HEAD (8 chat messages), then migrated with the
    change: `chat.0002_message_token_per_author… OK`; `seed_demo` twice → no error, 8 messages;
    `makemigrations --check` → No changes. `check --deploy --fail-level WARNING` with CI-like env → no issues.
    PostgreSQL: the CI `test-postgres` job runs the migrations (no PostgreSQL locally).
11. **Not available locally:** nginx (`nginx -t` on the rendered config) and `systemd-analyze verify` (macOS).
    The Team lead runs both on the server (runbook step 21). Docker is installed but its daemon is not running.

## 6. Implementation order

1. F1 + F2, then `core/tests/test_middleware.py` (F14.1).
2. F3, F4, F5, F6 + migration, with their tests (F14.2–F14.4).
3. F7–F11 (deploy), F12 (runbook), F13 (CI), with the deploy tests (F14.5).
4. `ruff format` on the changed Python files (never on `docs/`), `ruff check .`.
5. Verification (section 8).

## 7. Test plan

### Traceability

| AC | Tests |
|---|---|
| AC1 | `core/tests/test_deploy.py::NginxTemplateTests::test_login_rate_limit`, `::test_login_location_pattern`, `::test_proxy_headers_at_server_level`, `::test_proxy_headers` (unchanged) |
| AC2 | `accounts/tests/test_throttling.py::ThrottleIpTests` (4 tests), `LoginThrottleTests::test_ipv6_same_64_shares_lock`, `::test_ipv6_other_64_not_locked`, `::test_no_lock_across_ipv4_addresses`; existing `::test_lock_is_per_ip`, `::test_xff_*` |
| AC3 | `NginxTemplateTests::test_catch_all_servers`, `::test_www_redirect_and_acme`, `::test_http_redirects_to_https` (changed), `::test_acme_location_in_both` (unchanged); `RunbookTests::test_certificate_for_www` |
| AC4 | `core/tests/test_middleware.py::PrivateCacheTests` (6 tests) |
| AC5 | `core/tests/test_middleware.py::ContentSecurityPolicyTests` (8 tests), `::TemplatesFitPolicyTests::test_no_inline_code_in_templates` |
| AC6 | `petitions/tests/test_views.py::HardeningTests::test_comment_hint_escaped`, `::test_plain_hint_unchanged`; existing `FormTests::test_hint_*` |
| AC7 | `HardeningTests::test_type_filter_valid`, `::test_type_filter_out_of_range_ignored`, `::test_type_filter_18_digits_empty`, `::test_huge_url_ids_404`; existing chat `after` tests |
| AC8 | `chat/tests/test_services.py::ServiceTests::test_same_token_other_author_kept`, `chat/tests/test_models.py::ModelTests::test_client_token_unique_per_dialog_and_author` (renamed, extended); existing `::test_same_client_token_returns_existing` |
| AC9 | `BackupScriptRunTests::test_password_not_on_command_line`, `::test_bad_database_url_fails`, existing `ShellScriptTests` (all 5); `GunicornConfigTests::test_defaults` (extended); `SystemdUnitTests::test_hardening` (changed); `RunbookTests::test_demo_password_removed_after_seed` |
| AC10 | `RunbookTests::test_service_account_nologin`; `RunbookTests::test_steps_numbered_consecutively` (0..21) |
| AC11 | `CiDependencyAuditTests::test_audit_step` |
| AC12 | section 8 |

### Access matrix (headers)

| Request | CSP | Cache-Control added |
|---|---|---|
| anonymous, no cookie (`/login/`, redirect from `/grades/`) | yes | no |
| stale session cookie | yes | no |
| student / staff page | yes | `no-store, private` |
| superuser admin page | yes (same policy) | `no-store, private` |
| static file (WhiteNoise) | no (not tested; WhiteNoise answers before the middleware, D8) | no |
| `DEBUG=True` 404 | no | — |

### Edge cases

IPv6 upper case, IPv4-mapped, loopback `::1` → `::`, invalid address → `0.0.0.0`; type filter `-1`, `1e3`,
leading space, Arabic-Indic digit, `0x1`, empty, 18 vs 25 digits; chat: same author + same token → existing
message, other author + same token → new message; backup with a non-PostgreSQL URL; template scan for every inline
form that CSP blocks.

### Changed existing tests (with reason)

| Test | Change | Reason |
|---|---|---|
| `NginxTemplateTests::test_http_redirects_to_https` | `$host` redirect → fixed domain, twice | AC3 |
| `SystemdUnitTests::test_hardening` | `ProtectSystem=full` → `strict` + new options | AC9 |
| `GunicornConfigTests::test_defaults` | + `secure_scheme_headers` | AC9 |
| `chat/tests/test_models.py::test_client_token_unique_per_dialog` | renamed `…_and_author`; + other author with the same token allowed; count 3 → 4 | AC8 |

Test count: 1141 → 1181 (+40).

### F14. Test code (exact)

F14.1 `core/tests/test_middleware.py` (new):

````python
"""TASK-016: Content-Security-Policy and no-store for signed-in users (PT1-F3, PT1-F5)."""

import re
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.middleware import (
    CONTENT_SECURITY_POLICY,
    ContentSecurityPolicyMiddleware,
    PrivateCacheMiddleware,
)

EXPECTED_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


class ContentSecurityPolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fac = make_faculty("FX")
        group = make_group(fac, "GX")
        cls.student = make_student("csp_student", group, "SA")
        cls.staff = make_staff("csp_staff", fac)
        cls.admin = User.objects.create_superuser("csp_admin", password="Admin-Pass-2026!")

    def test_policy_value(self):
        self.assertEqual(CONTENT_SECURITY_POLICY, EXPECTED_CSP)

    def test_anonymous_login_page(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    def test_student_page(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    def test_staff_page(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("petitions:staff_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    def test_admin_page_same_policy(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    def test_redirect_and_404(self):
        self.assertEqual(self.client.get("/grades/")["Content-Security-Policy"], EXPECTED_CSP)
        self.client.force_login(self.student)
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    @override_settings(DEBUG=True)
    def test_debug_error_pages_without_policy(self):
        self.client.force_login(self.student)
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Content-Security-Policy", response)

    def test_existing_header_kept(self):
        def view(request):
            response = HttpResponse("x")
            response["Content-Security-Policy"] = "default-src 'none'"
            return response

        response = ContentSecurityPolicyMiddleware(view)(RequestFactory().get("/x/"))
        self.assertEqual(response["Content-Security-Policy"], "default-src 'none'")


class TemplatesFitPolicyTests(SimpleTestCase):
    """The strict policy works only while templates stay free of inline code."""

    FORBIDDEN = (
        re.compile(r"<script(?![^>]*\ssrc=)[^>]*>", re.IGNORECASE),
        re.compile(r"<style", re.IGNORECASE),
        re.compile(r"\sstyle\s*=", re.IGNORECASE),
        re.compile(r"\son[a-z]+\s*=", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", re.IGNORECASE),
        re.compile(r"data:image", re.IGNORECASE),
    )

    def test_no_inline_code_in_templates(self):
        base = Path(settings.BASE_DIR)
        paths = sorted(base.glob("templates/**/*.html")) + sorted(
            base.glob("*/templates/**/*.html")
        )
        self.assertGreater(len(paths), 30)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for pattern in self.FORBIDDEN:
                self.assertIsNone(pattern.search(text), f"{path.relative_to(base)}: {pattern}")


class PrivateCacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fac = make_faculty("FX")
        group = make_group(fac, "GX")
        cls.student = make_student("cache_student", group, "SA")
        cls.staff = make_staff("cache_staff", fac)

    def _assert_no_store(self, response):
        cache_control = response["Cache-Control"]
        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)

    def test_student_pages_no_store(self):
        self.client.force_login(self.student)
        for name in ("accounts:profile", "academics:my_grades", "schedule:week"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self._assert_no_store(response)

    def test_staff_page_no_store(self):
        self.client.force_login(self.staff)
        self._assert_no_store(self.client.get(reverse("petitions:staff_queue")))

    def test_anonymous_unchanged(self):
        response = self.client.get("/grades/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("Cache-Control", response)

    def test_stale_session_cookie_unchanged(self):
        self.client.cookies[settings.SESSION_COOKIE_NAME] = "no-such-session"
        response = self.client.get("/grades/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("Cache-Control", response)

    def test_no_session_access_without_cookie(self):
        request = RequestFactory().get("/x/")
        response = PrivateCacheMiddleware(lambda r: HttpResponse("x"))(request)
        self.assertNotIn("Cache-Control", response)
        self.assertFalse(hasattr(request, "user"))

    def test_session_length_unchanged(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 14 * 24 * 3600)
````

F14.2 `accounts/tests/test_throttling.py`:

````diff
--- a/accounts/tests/test_throttling.py
+++ b/accounts/tests/test_throttling.py
@@ -2,7 +2,7 @@
 from unittest import mock
 
 from django.http import HttpRequest
-from django.test import RequestFactory, TestCase, override_settings
+from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
 from django.urls import reverse
 from django.utils import timezone
 
@@ -13,6 +13,7 @@
     is_locked,
     normalize_username,
     register_failure,
+    throttle_ip,
 )
 
 
@@ -96,6 +97,28 @@
         self.assertEqual(response.status_code, 200)
         self.assertIn("Слишком много неудачных попыток", response.content.decode())
 
+    def test_ipv6_same_64_shares_lock(self):
+        # TASK-016 (PT1-F2): a new address in the same /64 does not get new attempts.
+        for host in ("1", "2", "3"):
+            self._post_login("u1", "wrong", REMOTE_ADDR=f"2001:db8:1:2::{host}")
+        response = self._post_login("u1", "Test-Pass-2026!", REMOTE_ADDR="2001:db8:1:2:ffff::9")
+        self.assertEqual(response.status_code, 200)
+        self.assertIn("Слишком много неудачных попыток", response.content.decode())
+        self.assertTrue(LoginThrottle.objects.filter(ip_address="2001:db8:1:2::").exists())
+
+    def test_ipv6_other_64_not_locked(self):
+        for _ in range(3):
+            self._post_login("u1", "wrong", REMOTE_ADDR="2001:db8:1:2::1")
+        response = self._post_login("u1", "Test-Pass-2026!", REMOTE_ADDR="2001:db8:1:3::1")
+        self.assertEqual(response.status_code, 302)
+
+    def test_no_lock_across_ipv4_addresses(self):
+        # User decision (plan.md 6b): no per-account lock across addresses.
+        for host in ("1", "2", "3", "4", "5", "6"):
+            self._post_login("u1", "wrong", REMOTE_ADDR=f"10.0.{host}.1")
+        response = self._post_login("u1", "Test-Pass-2026!", REMOTE_ADDR="10.0.9.1")
+        self.assertEqual(response.status_code, 302)
+
     def test_locked_does_not_authenticate(self):
         for _ in range(3):
             self._post_login("u1", "wrong")
@@ -155,3 +178,20 @@
         register_failure("u1", "10.0.0.1", t_late)
         row = LoginThrottle.objects.get(username_key="u1", ip_address="10.0.0.1")
         self.assertEqual(row.failures, 1)
+
+
+class ThrottleIpTests(SimpleTestCase):
+    def test_ipv4_unchanged(self):
+        self.assertEqual(throttle_ip("203.0.113.7"), "203.0.113.7")
+
+    def test_ipv6_network_64(self):
+        self.assertEqual(throttle_ip("2001:db8:1:2:aaaa:bbbb:cccc:dddd"), "2001:db8:1:2::")
+        self.assertEqual(throttle_ip("2001:DB8:1:2::1"), "2001:db8:1:2::")
+
+    def test_ipv4_mapped_ipv6(self):
+        self.assertEqual(throttle_ip("::ffff:203.0.113.7"), "203.0.113.7")
+
+    def test_loopback_and_unknown(self):
+        self.assertEqual(throttle_ip("::1"), "::")
+        self.assertEqual(throttle_ip(UNKNOWN_IP), UNKNOWN_IP)
+        self.assertEqual(throttle_ip("not-an-ip"), UNKNOWN_IP)
````

F14.3 `petitions/tests/test_views.py` (append):

````diff
--- a/petitions/tests/test_views.py
+++ b/petitions/tests/test_views.py
@@ -927,3 +927,68 @@
         self.assertIn(f'href="/staff/requests/{self.p1.public_id}/"', queue)
         self.assertIn("GX", queue)
         self.assertIn("файлов:", queue)
+
+
+class HardeningTests(FrozenClockMixin, TestCase):
+    """TASK-016: PT1-F7 (hint escaped) and PT1-F8 (out-of-range type filter)."""
+
+    HUGE = "9" * 25
+
+    def setUp(self):
+        self.fac = make_faculty("FX")
+        self.group = make_group(self.fac, "GX")
+        self.student = make_student("a", self.group, "SA").student_profile
+        self.staff = make_staff("sx", self.fac)
+        self.type = make_type()
+        self.other_type = make_type(name="Другая")
+        self.p1 = make_petition(self.student, self.type)
+        self.p2 = make_petition(self.student, self.other_type)
+
+    def test_comment_hint_escaped(self):
+        hint = '<img src=x onerror="alert(1)"> & <b>жирный</b>'
+        t = make_type(name="XSS", comment_required=True, hint=hint)
+        self.client.force_login(self.student.user)
+        content = self.client.get(reverse("petitions:submit", args=[t.pk])).content.decode()
+        self.assertNotIn("<img src=x", content)
+        self.assertNotIn("<b>жирный</b>", content)
+        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; &lt;b&gt;", content)
+
+    def test_plain_hint_unchanged(self):
+        t = make_type(name="Plain", comment_required=True, hint="Укажите причину «А»")
+        form = PetitionForm(request_type=t)
+        self.assertEqual(form.fields["comment"].help_text, "Укажите причину «А»")
+
+    def _queue(self, type_value):
+        self.client.force_login(self.staff)
+        response = self.client.get(reverse("petitions:staff_queue"), {"type": type_value})
+        self.assertEqual(response.status_code, 200, type_value)
+        return response.content.decode()
+
+    def test_type_filter_valid(self):
+        content = self._queue(str(self.type.pk))
+        self.assertIn(str(self.p1.short_id), content)
+        self.assertNotIn(str(self.p2.short_id), content)
+
+    def test_type_filter_out_of_range_ignored(self):
+        for value in (self.HUGE, "-1", "1e3", " 1", "\u0663", "0x1", ""):
+            content = self._queue(value)
+            self.assertIn(str(self.p1.short_id), content, value)
+            self.assertIn(str(self.p2.short_id), content, value)
+
+    def test_type_filter_18_digits_empty(self):
+        content = self._queue("9" * 18)
+        self.assertNotIn(str(self.p1.short_id), content)
+        self.assertNotIn(str(self.p2.short_id), content)
+
+    def test_huge_url_ids_404(self):
+        self.client.force_login(self.student.user)
+        self.assertEqual(self.client.get(f"/requests/new/{self.HUGE}/").status_code, 404)
+        self.assertEqual(self.client.get(f"/map/floor/{self.HUGE}/").status_code, 404)
+        self.client.force_login(self.staff)
+        for path in (
+            f"/staff/students/{self.HUGE}/",
+            f"/staff/students/{self.HUGE}/grades/",
+            f"/staff/schedule/{self.HUGE}/",
+            f"/staff/schedule/{self.HUGE}/2026-11-16/",
+        ):
+            self.assertEqual(self.client.get(path).status_code, 404, path)
````

F14.4 `chat/tests/test_services.py` and `chat/tests/test_models.py`:

````diff
--- a/chat/tests/test_services.py
+++ b/chat/tests/test_services.py
@@ -94,6 +94,20 @@
             send_student_message(self.ax_profile, "заполнение", uuid.uuid4())
         self.assertEqual(send_student_message(self.ax_profile, "Привет", token).pk, first.pk)
 
+    def test_same_token_other_author_kept(self):
+        # TASK-016 (PT1-F10): the token is looked up per author.
+        token = uuid.uuid4()
+        student_message = send_student_message(self.ax_profile, "Вопрос", token)
+        reply = send_staff_message(student_message.dialog, self.sx, "Ответ", token)
+        self.assertNotEqual(reply.pk, student_message.pk)
+        self.assertEqual(reply.author, self.sx)
+        self.assertEqual(reply.text, "Ответ")
+        self.assertEqual(Message.objects.filter(dialog=student_message.dialog).count(), 2)
+        # The same author with the same token still gets the existing message.
+        again = send_staff_message(student_message.dialog, self.sx, "Ответ", token)
+        self.assertEqual(again.pk, reply.pk)
+        self.assertEqual(Message.objects.filter(dialog=student_message.dialog).count(), 2)
+
     def test_two_staff_replies_both_kept_in_id_order(self):
         sx2 = make_staff("sx2", self.fx)
         dialog = make_dialog(self.ax_profile)
````

````diff
--- a/chat/tests/test_models.py
+++ b/chat/tests/test_models.py
@@ -47,7 +47,7 @@
                     dialog=dialog, author=self.student, author_role="bad", text="x"
                 )
 
-    def test_client_token_unique_per_dialog(self):
+    def test_client_token_unique_per_dialog_and_author(self):
         dialog = make_dialog(self.profile)
         other = make_dialog(self.other_profile)
         token = uuid.uuid4()
@@ -68,6 +68,14 @@
                     text="y",
                     client_token=token,
                 )
+        # TASK-016: the same token from another author in the same dialog is fine.
+        Message.objects.create(
+            dialog=dialog,
+            author=self.staff,
+            author_role=AuthorRole.STAFF,
+            text="w",
+            client_token=token,
+        )
         # The same token in another dialog is fine.
         Message.objects.create(
             dialog=other,
@@ -79,7 +87,7 @@
         # Many NULL tokens are fine.
         add_message(dialog, self.student, AuthorRole.STUDENT)
         add_message(dialog, self.student, AuthorRole.STUDENT)
-        self.assertEqual(Message.objects.filter(dialog=dialog).count(), 3)
+        self.assertEqual(Message.objects.filter(dialog=dialog).count(), 4)
 
     def test_ordering_by_id(self):
         dialog = make_dialog(self.profile)
````

F14.5 `core/tests/test_deploy.py`:

````diff
--- a/core/tests/test_deploy.py
+++ b/core/tests/test_deploy.py
@@ -12,6 +12,7 @@
 import shutil
 import subprocess
 import sys
+import tempfile
 from pathlib import Path
 from unittest import mock
 
@@ -66,6 +67,8 @@
         self.assertEqual(cfg["accesslog"], "-")
         self.assertEqual(cfg["errorlog"], "-")
         self.assertIs(cfg["control_socket_disable"], True)
+        # TASK-016 (PT1-F13): trust only X-Forwarded-Proto.
+        self.assertEqual(cfg["secure_scheme_headers"], {"X-FORWARDED-PROTO": "https"})
 
     def test_env_override(self):
         cfg = self._load_config({"GUNICORN_WORKERS": "3", "GUNICORN_BIND": "127.0.0.1:9000"})
@@ -110,8 +113,62 @@
                 self.assertNotIn(forbidden, active, f"{path.name}: {forbidden}")
 
     def test_http_redirects_to_https(self):
-        self.assertIn("return 301 https://$host$request_uri;", _read(NGINX_CONF))
+        # TASK-016 (PT1-F4): the redirect target is the fixed domain, never $host.
+        text = _read(NGINX_CONF)
+        self.assertEqual(text.count("return 301 https://example.com$request_uri;"), 2)
+        self.assertNotIn("$host$request_uri", text)
 
+    def test_catch_all_servers(self):
+        text = _read(NGINX_CONF)
+        for line in (
+            "listen 80 default_server;",
+            "listen [::]:80 default_server;",
+            "return 444;",
+            "listen 443 ssl http2 default_server;",
+            "listen [::]:443 ssl http2 default_server;",
+            "ssl_reject_handshake on;",
+        ):
+            self.assertEqual(text.count(line), 1, line)
+        self.assertEqual(text.count("server_name _;"), 2)
+
+    def test_www_redirect_and_acme(self):
+        text = _read(NGINX_CONF)
+        self.assertIn("server_name example.com www.example.com;", text)
+        self.assertIn("server_name www.example.com;", text)
+        self.assertIn("server_name example.com www.example.com;", _read(NGINX_BOOTSTRAP))
+
+    def test_login_rate_limit(self):
+        text = _read(NGINX_CONF)
+        for line in (
+            "POST    $binary_remote_addr;",
+            'default "";',
+            "limit_req_zone $deanery_login_key zone=deanery_login:10m rate=10r/m;",
+            "limit_req zone=deanery_login burst=10 nodelay;",
+            "limit_req_status 429;",
+            "limit_conn_zone $binary_remote_addr zone=deanery_conn:10m;",
+            "limit_conn deanery_conn 20;",
+            "limit_conn_status 429;",
+        ):
+            self.assertEqual(text.count(line), 1, line)
+
+    def test_login_location_pattern(self):
+        match = re.search(r"location ~ (\S+) \{", _read(NGINX_CONF))
+        self.assertIsNotNone(match)
+        pattern = re.compile(match.group(1))
+        for path in ("/login/", "/staff-1a2b3c/login/", "/a/b_c/login/", "/admin/login/"):
+            self.assertIsNotNone(pattern.search(path), path)
+        for path in ("/login/x", "/logout/", "/loginx/", "/profile/", "/login"):
+            self.assertIsNone(pattern.search(path), path)
+
+    def test_proxy_headers_at_server_level(self):
+        lines = _read(NGINX_CONF).splitlines()
+        headers = [line for line in lines if "proxy_set_header" in line]
+        self.assertEqual(len(headers), 4)
+        for line in headers:
+            self.assertTrue(line.startswith("    proxy_set_header"), line)
+            self.assertFalse(line.startswith("        "), line)
+        self.assertEqual(sum("proxy_pass http://127.0.0.1:8000;" in line for line in lines), 2)
+
     def test_acme_location_in_both(self):
         for path in (NGINX_CONF, NGINX_BOOTSTRAP):
             self.assertIn("location ^~ /.well-known/acme-challenge/", _read(path), path.name)
@@ -251,10 +308,23 @@
         self.assertIn("-c deploy/gunicorn.conf.py config.wsgi:application", _read(SYSTEMD_UNIT))
 
     def test_hardening(self):
-        unit = _read(SYSTEMD_UNIT)
-        self.assertIn("NoNewPrivileges=true", unit)
-        self.assertIn("ProtectSystem=full", unit)
-        self.assertIn("PrivateTmp=true", unit)
+        # TASK-016 (PT1-F13): ProtectSystem=strict and more sandboxing.
+        lines = _read(SYSTEMD_UNIT).splitlines()
+        for line in (
+            "NoNewPrivileges=true",
+            "PrivateTmp=true",
+            "PrivateDevices=true",
+            "ProtectSystem=strict",
+            "ProtectHome=true",
+            "ProtectKernelTunables=true",
+            "ProtectControlGroups=true",
+            "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX",
+            "CapabilityBoundingSet=",
+            "ReadWritePaths=/srv/deanery/private_media /srv/deanery/private_media_trial",
+        ):
+            self.assertIn(line, lines)
+        self.assertNotIn("ProtectSystem=full", lines)
+        self.assertEqual(sum(line.startswith("ReadWritePaths=") for line in lines), 1)
 
 
 class SmallFilesTests(SimpleTestCase):
@@ -435,6 +505,27 @@
             "PasswordAuthentication",
         ):
             self.assertIn(topic, text, topic)
+
+    def test_service_account_nologin(self):
+        # TASK-016 (PT1-F6): no login shell and no SSH key for the service account.
+        text = _read(DEPLOY_MD)
+        self.assertIn('--shell /usr/sbin/nologin "$APP_USER"', text)
+        self.assertNotIn("--shell /bin/bash", text)
+        self.assertNotIn('ssh-copy-id "$APP_USER"', text)
+        self.assertIn('sudo usermod --shell /usr/sbin/nologin "$APP_USER"', text)
+
+    def test_certificate_for_www(self):
+        self.assertIn('-d "$DOMAIN" -d "www.$DOMAIN"', _read(DEPLOY_MD))
+
+    def test_demo_password_removed_after_seed(self):
+        text = _read(DEPLOY_MD)
+        section = text[text.index("## 16. ") : text.index("## 17. ")]
+        removal = "sudo sed -i '/^DEMO_PASSWORD=/d' /etc/deanery/deanery.env"
+        self.assertIn(removal, section)
+        self.assertLess(section.index("$M seed_demo"), section.index(removal))
+        self.assertLess(section.index(removal), section.index("sudo systemctl restart deanery"))
+        # The app itself never reads DEMO_PASSWORD.
+        self.assertNotIn("DEMO_PASSWORD", _read(BASE_DIR / "config" / "settings.py"))
 
     def test_no_daily_seed_cron(self):
         for line in _read(DEPLOY_MD).splitlines():
@@ -504,3 +595,96 @@
         section = text[text.index("## 19. Resources") : text.index("## 20. Troubleshooting")]
         for fragment in ("GUNICORN_WORKERS=5", "min(5, 13)", "512 MB", "20 GB", "10%"):
             self.assertIn(fragment, section, fragment)
+
+
+class BackupScriptRunTests(SimpleTestCase):
+    """TASK-016: run backup.sh with a stub pg_dump; the password never reaches the command line."""
+
+    PASSWORD = "0123abcd4567ef89dummydbpass"
+
+    def test_password_not_on_command_line(self):
+        bash = shutil.which("bash")
+        if bash is None or shutil.which("tar") is None or shutil.which("gzip") is None:
+            self.skipTest("bash, tar or gzip not available")
+        with tempfile.TemporaryDirectory() as tmp:
+            root = Path(tmp)
+            (root / "bin").mkdir()
+            (root / "media" / "private_media").mkdir(parents=True)
+            (root / "media" / "private_media" / "a.pdf").write_bytes(b"%PDF-1.4")
+            stub = root / "bin" / "pg_dump"
+            stub.write_text(
+                "#!/usr/bin/env bash\n"
+                f'printf "%s\\n" "$@" > "{root}/args"\n'
+                f'env | grep -E "^PG(USER|PASSWORD|HOST|PORT|DATABASE)=" | sort > "{root}/pgenv"\n'
+                f'env | grep -c "^DATABASE_URL=" > "{root}/dburl" || true\n'
+                'echo "-- dump"\n',
+                encoding="utf-8",
+            )
+            stub.chmod(0o755)
+            env_file = root / "deanery.env"
+            env_file.write_text(
+                f"DATABASE_URL=postgres://deanery:{self.PASSWORD}@localhost:5432/deanery_trial\n"
+                f"PRIVATE_MEDIA_ROOT={root}/media/private_media\n",
+                encoding="utf-8",
+            )
+            env = {
+                "PATH": f"{root / 'bin'}{os.pathsep}{os.environ['PATH']}",
+                "BACKUP_DIR": str(root / "backups"),
+                "DEANERY_ENV_FILE": str(env_file),
+            }
+            result = subprocess.run(  # noqa: S603
+                [bash, str(BACKUP_SH)], env=env, capture_output=True, text=True, timeout=60
+            )
+            self.assertEqual(result.returncode, 0, result.stderr)
+            self.assertIn("backup ok:", result.stdout)
+            args = (root / "args").read_text(encoding="utf-8")
+            self.assertNotIn(self.PASSWORD, args)
+            self.assertEqual(args.split(), ["--no-owner", "--no-privileges"])
+            self.assertEqual(
+                (root / "pgenv").read_text(encoding="utf-8").split(),
+                [
+                    "PGDATABASE=deanery_trial",
+                    "PGHOST=localhost",
+                    f"PGPASSWORD={self.PASSWORD}",
+                    "PGPORT=5432",
+                    "PGUSER=deanery",
+                ],
+            )
+            self.assertEqual((root / "dburl").read_text(encoding="utf-8").strip(), "0")
+            names = sorted(p.name for p in (root / "backups").iterdir())
+            self.assertEqual(len(names), 2)
+            self.assertTrue(names[0].startswith("db-") and names[0].endswith(".sql.gz"))
+            self.assertTrue(names[1].startswith("media-") and names[1].endswith(".tar.gz"))
+
+    def test_bad_database_url_fails(self):
+        bash = shutil.which("bash")
+        if bash is None:
+            self.skipTest("bash not available")
+        with tempfile.TemporaryDirectory() as tmp:
+            env_file = Path(tmp) / "deanery.env"
+            env_file.write_text("DATABASE_URL=sqlite:///db.sqlite3\n", encoding="utf-8")
+            env = {
+                "PATH": os.environ["PATH"],
+                "BACKUP_DIR": str(Path(tmp) / "backups"),
+                "DEANERY_ENV_FILE": str(env_file),
+            }
+            result = subprocess.run(  # noqa: S603
+                [bash, str(BACKUP_SH)], env=env, capture_output=True, text=True, timeout=60
+            )
+            self.assertNotEqual(result.returncode, 0)
+            self.assertIn("DATABASE_URL must look like", result.stderr)
+            self.assertFalse((Path(tmp) / "backups").exists())
+
+
+class CiDependencyAuditTests(SimpleTestCase):
+    """TASK-016: pip-audit runs in CI in its own step; it is not a runtime dependency."""
+
+    def test_audit_step(self):
+        import yaml
+
+        ci = yaml.safe_load(_read(BASE_DIR / ".github" / "workflows" / "ci.yml"))
+        steps = {step.get("name"): step for step in ci["jobs"]["test"]["steps"]}
+        run = steps["Dependency audit"]["run"]
+        self.assertIn("pip install pip-audit==2.10.1", run)
+        self.assertIn("pip-audit --requirement requirements.txt", run)
+        self.assertNotIn("pip-audit", _read(BASE_DIR / "requirements.txt"))
````

## 8. Verification (Coder, then Reviewer)

```bash
.venv/bin/python manage.py test --parallel 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/python manage.py test --parallel 2 2>&1 | tee "$TMPDIR/test-p2-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/python scripts/run_tests_at.py 2027-03-01T12:00:00 2>&1 | tee "$TMPDIR/test-frozen-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/ruff check . && .venv/bin/ruff format --check .
bash -n deploy/backup.sh deploy/manage.sh
.venv/bin/gunicorn --check-config -c deploy/gunicorn.conf.py config.wsgi:application
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('CI YAML OK')"
test -x deploy/backup.sh && echo EXEC_OK
which nginx systemd-analyze pip-audit || echo "not available locally: say so in the REPORT"
git status --short
```

Migration on a seeded temporary database (never on the project `db.sqlite3`):

```bash
export DATABASE_URL="sqlite:///$TMPDIR/t016-mig.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/t016-mig-media" DEMO_PASSWORD=Local-Demo-Pass-2026
.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo && .venv/bin/python manage.py seed_demo
unset DATABASE_URL PRIVATE_MEDIA_ROOT DEMO_PASSWORD
```

Expected: `Ran 1181 tests … OK` three times; ruff clean; `GUNICORN` OK; `No changes detected`; `EXEC_OK`.
`git status` shows only the files of section 4, the new migration and `docs/tasks/TASK-016.md` (plus the Team
lead's `plan.md`). If you can run `pip-audit -r requirements.txt` in a temporary venv, add its output to the
REPORT; if not, say so. Never read `.env`. Report every failing run with the test name, Moscow time and a
traceback excerpt.

After APPROVE (Team lead, not the Coder): check every page in a browser for CSP errors (student, staff, admin),
then apply runbook step 21 on the server (`nginx -t`, `systemd-analyze verify`, `systemd-analyze security`).

## 9. Risks

- **nginx config not validated by nginx here** (section 5, item 11). Mitigation: `nginx -t` before reload in
  step 21; the old site file stays in place until `tee` overwrites it — keep a copy first
  (`sudo cp /etc/nginx/sites-available/deanery /root/deanery.nginx.bak`).
- **`ProtectSystem=strict` blocks an unknown write** → the unit fails or uploads fail. Mitigation: D14 list;
  step 21 uploads and downloads a PDF after the restart; rollback = previous unit file.
- **CSP breaks an untested admin widget** → the fallback in D6.
- **429 for jurors behind one NAT** if more than 10 sign in within seconds (D2) — they retry after 6 s.
- **pip-audit reports a new advisory later** → CI turns red; that is the purpose; fix by upgrading the pin.
