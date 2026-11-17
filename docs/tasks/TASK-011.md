# TASK-011: production readiness — gunicorn, nginx, systemd, PostgreSQL CI, deploy runbook

Author: Planner. Status: ready for implementation (includes the Team lead's amendment: 1 vCPU / 1 GB RAM / 10 GB disk).
Base commit: `d9d8e55`. Related: `plan.md` 6b, `README.md` "Deployment notes", `config/settings.py`, `config/env_utils.py`, `accounts/throttling.py`.

The agents have no server access. This task only adds files to the repository and documents the manual deployment. Target: Ubuntu 24.04, 1 vCPU, 1 GB RAM, 10 GB disk, one domain with HTTPS, until 2026-11-28.

---

## 1. Acceptance criteria
| ID | Criterion |
|---|---|
| AC1 | `gunicorn==26.2.0` in `requirements.txt`; `deploy/gunicorn.conf.py`: bind `127.0.0.1:8000` (env `GUNICORN_BIND`), workers from env `GUNICORN_WORKERS` (default 2), timeout 30, graceful timeout 30, access/error log to stdout/stderr (journal), control socket disabled. |
| AC2 | `deploy/nginx/deanery-bootstrap.conf` (HTTP only, for the first certificate) and `deploy/nginx/deanery.conf` (HTTP → HTTPS redirect, ACME path, TLS, proxy to `127.0.0.1:8000` with `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `client_max_body_size 20m`, no `root`/`alias` except the ACME webroot, no static or private-media location, no headers that Django already sets). |
| AC3 | `deploy/systemd/deanery.service` (non-root `<APP_USER>`, `EnvironmentFile=/etc/deanery/deanery.env`, `Restart=on-failure`, hardening options); `deploy/journald/50-deanery.conf` (`SystemMaxUse=200M`); `deploy/backup.sh` (gzip `pg_dump` + tar of `PRIVATE_MEDIA_ROOT`, keeps 7 days); `deploy/cron/deanery-backup`; `deploy/manage.sh` (runs `manage.py` with the env file); `deploy/ssh/10-deanery-hardening.conf`. |
| AC4 | `.env.production.example` lists every env variable the project reads (settings, management commands, gunicorn config) with a comment; `DEBUG=false`; `CLIENT_IP_HEADER=X-Real-IP` (matches nginx); PostgreSQL `DATABASE_URL`; `CSRF_TRUSTED_ORIGINS=https://example.com`; only placeholders. `check --deploy --fail-level WARNING` passes with exactly these values (test). |
| AC5 | CI job `test-postgres` with service `postgres:16` runs check, makemigrations check, the full suite, `run_tests_at.py`, migrate + seed twice on PostgreSQL; the SQLite job stays. CI also runs `gunicorn --check-config` and `bash -n deploy/*.sh`. |
| AC6 | `docs/DEPLOY.md` runbook (English, numbered, copy-paste commands) covering every step in section 4.9, including swap first, journald limit, resources section, trial vs final database, one-time `seed_demo` on 2026-11-22, HSTS raise procedure. `README.md` "Deployment notes" points to it. |
| AC7 | Tests (section 6): nginx template rules, env coverage, deploy check with example values, gunicorn config values, systemd unit rules, no secrets / real IPs in `deploy/`, `.env.production.example`, `docs/DEPLOY.md`, shell syntax. |
| AC8 | Any PostgreSQL-only failure found by the PostgreSQL run is fixed minimally and listed in the `REPORT`. |

## 2. Out of scope
Logging in to the server, Docker/Kubernetes, CDN, monitoring, e-mail, the visual theme, changing Django security settings (only documentation of how to raise HSTS).

## 3. Design decisions
**D1. gunicorn 26.2.0.** Released 2026-08-24, no runtime dependencies, Python ≥ 3.10. The newer 27.x line is one week old (27.0.0 on 2026-11-10, 27.0.1 on 2026-11-12) — too fresh for a deploy this week. Verified locally (9.6): `--check-config` passes, 2 workers boot, `/health/` → 200. Version 26 starts a "control server" in `$HOME/.gunicorn`; the config disables it (`control_socket_disable = True`), which also suits `ProtectHome=` in systemd.

**D2. Workers.** Default 2 for 1 vCPU / 1 GB (each Django worker ≈ 60–90 MB RSS). Formula for a bigger server, documented in the config and the runbook: `workers = min(2 × vCPU + 1, (free RAM in MB − 300) / 90)`; set `GUNICORN_WORKERS` in the env file.

**D3. Loopback TCP, not a Unix socket.** `127.0.0.1:8000` needs no shared group or socket permissions between `www-data` and the app user, which removes a common manual-setup error. The port is not reachable from outside (loopback only; ufw allows only 22/80/443). Because only nginx can reach gunicorn, Django may trust `X-Forwarded-Proto` (`SECURE_PROXY_SSL_HEADER`) and `X-Real-IP` (`CLIENT_IP_HEADER`).

**D4. Static files stay with WhiteNoise.** WhiteNoise already serves hashed, compressed files with far-future cache headers (`CompressedManifestStaticFilesStorage` when `DEBUG=false`). nginx then needs no `root` for the app at all, so it cannot serve any file of the project directory — in particular not `PRIVATE_MEDIA_ROOT`. Cost on 1 vCPU is small for a prototype (static files are cached by browsers).

**D5. Client IP header = `X-Real-IP`.** nginx sets `proxy_set_header X-Real-IP $remote_addr;` (overwrites any client value). `accounts/throttling.py` reads it directly. `X-Forwarded-For` is also passed (standard), but not used for throttling.

**D6. Certificates: certbot webroot.** First a HTTP-only bootstrap config serves `/.well-known/acme-challenge/` from `/var/www/letsencrypt`; `certbot certonly --webroot` gets the certificate; then the full config is installed. Renewal uses the same webroot location (kept in the port-80 server) and the `certbot.timer` that the Ubuntu package installs; `--deploy-hook "systemctl reload nginx"` reloads nginx after renewal. The nginx config stays a tested file in the repo (the `--nginx` plugin would rewrite it).

**D7. nginx version.** Ubuntu 24.04 ships nginx 1.24: HTTP/2 is enabled with `listen 443 ssl http2;` (the separate `http2 on;` directive exists only since 1.25.1).

**D8. Env file.** `/etc/deanery/deanery.env`, owner `<APP_USER>`, mode 600 (systemd reads it as root; operators run `deploy/manage.sh` as the app user). Values must not need shell quoting: secrets are generated with `secrets.token_urlsafe` / `openssl rand -hex` (letters, digits, `-`, `_`); `DEMO_PASSWORD` uses only letters, digits, `-`, `_`, `.`. No `.env` file in the app directory.

**D9. Env coverage test parses the sources.** Parsing `config/settings.py` (`env.<type>("NAME"…)`), `os.environ.get("NAME"…)` in management commands and `deploy/gunicorn.conf.py` finds new variables automatically; a separate fixed list would silently go stale. A guard assertion requires the parser to find the 18 variables known today.

**D10. Trial database vs final database.** `seed_demo` creates announcements and chats only once, with dates relative to its first run. The trial deploy (now) therefore uses a throw-away database `deanery_trial` (and `/srv/deanery/private_media_trial`); on 2026-11-22 the runbook creates the final database `deanery` (and `/srv/deanery/private_media`), switches the env file, migrates, runs `seed_demo` once and restarts. No database is dropped during the jury period.

**D11. Resources (amendment).** Swap 1 GB before any `apt`/`pip`; journald capped at 200 MB; backups gzip-compressed and kept 7 days; nginx logs rotated by the stock `/etc/logrotate.d/nginx`; PostgreSQL stock settings (do not raise `shared_buffers`; default `max_connections`).

---

## 4. Files

### 4.1 List
Create: `deploy/gunicorn.conf.py`, `deploy/nginx/deanery-bootstrap.conf`, `deploy/nginx/deanery.conf`, `deploy/systemd/deanery.service`, `deploy/journald/50-deanery.conf`, `deploy/ssh/10-deanery-hardening.conf`, `deploy/cron/deanery-backup`, `deploy/backup.sh` (mode 755), `deploy/manage.sh` (mode 755), `.env.production.example`, `docs/DEPLOY.md`, `core/tests/test_deploy.py`.
Change: `requirements.txt` (+ `gunicorn==26.2.0`), `.github/workflows/ci.yml`, `README.md` ("Deployment notes": first bullet «Follow `docs/DEPLOY.md`.»; keep the other bullets).
Placeholders in all templates: `example.com` (domain) and `<APP_USER>` (Linux user, the runbook uses `deanery`). Fixed paths: app `/srv/deanery/app`, venv `/srv/deanery/venv`, media `/srv/deanery/private_media`, backups `/srv/deanery/backups`, env file `/etc/deanery/deanery.env`, ACME webroot `/var/www/letsencrypt`.
Note: `docs/` is excluded from ruff (TASK-006); `deploy/gunicorn.conf.py` is NOT excluded and must pass ruff.

### 4.2 `deploy/gunicorn.conf.py`
```python
"""gunicorn settings for the deanery prototype (loaded with -c deploy/gunicorn.conf.py).

Workers: 2 for 1 vCPU / 1 GB RAM. Bigger server: min(2 * vCPU + 1, (free RAM MB - 300) // 90),
set GUNICORN_WORKERS in /etc/deanery/deanery.env.
"""

import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = max(1, int(os.environ.get("GUNICORN_WORKERS", "2")))
timeout = 30
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
control_socket_disable = True
```

### 4.3 `deploy/nginx/deanery-bootstrap.conf`
```nginx
# Temporary HTTP-only site used once to obtain the first certificate (docs/DEPLOY.md step 13).
server {
    listen 80;
    listen [::]:80;
    server_name example.com;
    server_tokens off;

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        default_type "text/plain";
    }

    location / {
        return 503;
    }
}
```

### 4.4 `deploy/nginx/deanery.conf`
```nginx
# Deanery prototype. Static files are served by Django/WhiteNoise; nginx serves no project files.
# PRIVATE_MEDIA_ROOT must never get a location here (attachments go through Django access checks).
server {
    listen 80;
    listen [::]:80;
    server_name example.com;
    server_tokens off;

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        default_type "text/plain";
    }

    location / {
        return 301 https://$host$request_uri;
    }
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

    # Not set by Django; X-Frame-Options, nosniff, Referrer-Policy and HSTS come from Django.
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
    }
}
```

### 4.5 `deploy/systemd/deanery.service`
```ini
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
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/srv/deanery/private_media /srv/deanery/private_media_trial

[Install]
WantedBy=multi-user.target
```
(`ReadWritePaths` entries must exist before start; the runbook creates both directories. After the switch on 2026-11-22 the trial path stays harmlessly listed.)

### 4.6 Small files
- `deploy/journald/50-deanery.conf`:
```ini
[Journal]
SystemMaxUse=200M
SystemKeepFree=1G
MaxRetentionSec=14day
```
- `deploy/ssh/10-deanery-hardening.conf` (the name sorts before Ubuntu's `50-cloud-init.conf`; sshd uses the first value it reads):
```text
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
```
- `deploy/cron/deanery-backup` (installed to `/etc/cron.d/deanery-backup`; server time zone is Europe/Moscow, step 2):
```text
# Daily backup of PostgreSQL and PRIVATE_MEDIA_ROOT at 04:30 Moscow time.
30 4 * * * <APP_USER> /srv/deanery/app/deploy/backup.sh 2>&1 | logger -t deanery-backup
```
- `deploy/manage.sh`:
```bash
#!/usr/bin/env bash
# Run a Django management command with the production environment.
# Usage: sudo -u <APP_USER> /srv/deanery/app/deploy/manage.sh <command> [args]
set -euo pipefail
set -a
. /etc/deanery/deanery.env
set +a
cd /srv/deanery/app
exec /srv/deanery/venv/bin/python manage.py "$@"
```
- `deploy/backup.sh`:
```bash
#!/usr/bin/env bash
# Daily backup: gzip-compressed pg_dump + tar.gz of PRIVATE_MEDIA_ROOT; keeps KEEP_DAYS days.
set -euo pipefail
umask 077
BACKUP_DIR="${BACKUP_DIR:-/srv/deanery/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
set -a
. /etc/deanery/deanery.env
set +a
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip -9 > "$BACKUP_DIR/db-$STAMP.sql.gz"
tar -czf "$BACKUP_DIR/media-$STAMP.tar.gz" -C "$(dirname "$PRIVATE_MEDIA_ROOT")" "$(basename "$PRIVATE_MEDIA_ROOT")"
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'media-*.tar.gz' \) -mtime +"$((KEEP_DAYS - 1))" -delete
echo "backup ok: $STAMP"
```

### 4.7 `.env.production.example`
One block per variable: a `#` comment line(s), then `NAME=value`. Values (placeholders only):
```text
# Production. Copy to /etc/deanery/deanery.env (owner <APP_USER>, mode 600). Never commit real values.
# Values must not need shell quoting: letters, digits, '-', '_', '.', ':', '/', ',', '@' only.

# Must be false in production.
DEBUG=false
# Generate on the server: python3 -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=replace-me-with-secrets-token-urlsafe-50-generated-on-the-server
# The domain without scheme; comma-separated if several.
ALLOWED_HOSTS=example.com
# Full origin with https://
CSRF_TRUSTED_ORIGINS=https://example.com
# Non-obvious admin path, letters/digits/-/_ only, must end with "/".
ADMIN_URL=staff-panel-change-me/
# PostgreSQL. The runbook generates the password: openssl rand -hex 24
DATABASE_URL=postgres://deanery:REPLACE_ME_DB_PASSWORD@localhost:5432/deanery
# Outside the web root and outside the repository; nginx never serves it.
PRIVATE_MEDIA_ROOT=/srv/deanery/private_media
# nginx sets "proxy_set_header X-Real-IP $remote_addr;" (deploy/nginx/deanery.conf).
CLIENT_IP_HEADER=X-Real-IP
# HTTPS redirect in Django (nginx redirects too).
SECURE_SSL_REDIRECT=true
# Start small; raise to 31536000 after the site works over HTTPS (docs/DEPLOY.md, HSTS).
SECURE_HSTS_SECONDS=3600
# true is required by "check --deploy"; every subdomain of the domain must use HTTPS.
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
# Never true for this prototype (irreversible browser preload list).
SECURE_HSTS_PRELOAD=false
LOG_LEVEL=INFO
# Password of all demo accounts (seed_demo); letters, digits, '-', '_', '.' only; passes Django validators.
DEMO_PASSWORD=REPLACE_ME_DEMO_PASSWORD
# Login lockout per (username, IP).
LOGIN_FAILURE_LIMIT=5
LOGIN_LOCKOUT_SECONDS=900
# gunicorn (deploy/gunicorn.conf.py): 2 workers for 1 vCPU / 1 GB RAM.
GUNICORN_WORKERS=2
GUNICORN_BIND=127.0.0.1:8000
```

### 4.8 CI — `.github/workflows/ci.yml`
- Existing job `test`: add, after "Install dependencies": `- name: Shell syntax` → `run: bash -n deploy/backup.sh deploy/manage.sh`; `- name: gunicorn config` → `run: gunicorn --check-config -c deploy/gunicorn.conf.py config.wsgi:application`.
- New job `test-postgres` (same `runs-on`, `permissions` inherited):
```yaml
  test-postgres:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: deanery
          POSTGRES_PASSWORD: ci-only-postgres-password
          POSTGRES_DB: deanery
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U deanery"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      DEBUG: "true"
      SECRET_KEY: "ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop"
      DATABASE_URL: "postgres://deanery:ci-only-postgres-password@localhost:5432/deanery"
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
      - name: Django check
        run: python manage.py check --database default
      - name: Missing migrations
        run: python manage.py makemigrations --check --dry-run
      - name: Tests (PostgreSQL)
        run: python manage.py test
      - name: Tests with a frozen Moscow midnight clock (PostgreSQL)
        run: python scripts/run_tests_at.py 2026-11-18T00:00:00
      - name: Migrate and seed demo data twice (PostgreSQL)
        env:
          DEMO_PASSWORD: "ci-dummy-demo-password-2026"
        run: |
          python manage.py migrate --noinput
          python manage.py seed_demo
          python manage.py seed_demo
```
(The test runner creates `test_deanery`; the image's `POSTGRES_USER` is a superuser, so it may.)

### 4.9 `docs/DEPLOY.md` — required content and order
English, numbered steps; every step shows the exact commands in a `bash` block, run as the sudo user unless stated. Use shell variables set once in step 0: `DOMAIN=example.com`, `APP_USER=deanery`, `REPO_URL=<your repository URL>`. Sections:
0. **Before you start** — what you need (domain A record → server IP, SSH key created by the user: `ssh-keygen -t ed25519`, `ssh-copy-id`), the variables above, and a warning: keep one SSH session open until step 4 is verified.
1. **Swap first (1 GB RAM)** — `sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`; `echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab`; `echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-deanery-swap.conf && sudo sysctl --system`; check `free -h`. Must come before any `apt`/`pip` step.
2. **Time zone** — `sudo timedatectl set-timezone Europe/Moscow` (cron and logs in Moscow time).
3. **Packages** — `sudo apt update && sudo apt -y upgrade`; `sudo apt -y install python3.12-venv nginx postgresql certbot git ufw`.
4. **SSH: keys only** — copy `deploy/ssh/10-deanery-hardening.conf` (from the repo after step 7, or paste its 4 lines) to `/etc/ssh/sshd_config.d/`; `sudo sshd -t && sudo systemctl reload ssh`; verify `sudo sshd -T | grep -Ei 'passwordauthentication|permitrootlogin'`; open a NEW session with the key before closing the old one. (May be done right after step 7.)
5. **Firewall** — `sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable && sudo ufw status` (only 22, 80, 443).
6. **journald limit** — install `deploy/journald/50-deanery.conf` to `/etc/systemd/journald.conf.d/` (`sudo mkdir -p …`), `sudo systemctl restart systemd-journald`, check `journalctl --disk-usage`. nginx logs: rotated by the stock `/etc/logrotate.d/nginx` (no action).
7. **App user, directories, code** — `sudo adduser --system --group --home /srv/deanery --shell /bin/bash "$APP_USER"`; `sudo -u "$APP_USER" git clone "$REPO_URL" /srv/deanery/app`; `sudo -u "$APP_USER" mkdir -p /srv/deanery/private_media /srv/deanery/private_media_trial /srv/deanery/backups`; `sudo chmod 750 /srv/deanery/private_media /srv/deanery/private_media_trial && sudo chmod 700 /srv/deanery/backups`; `sudo mkdir -p /var/www/letsencrypt`.
8. **Python venv** — `sudo -u "$APP_USER" python3.12 -m venv /srv/deanery/venv`; `sudo -u "$APP_USER" /srv/deanery/venv/bin/pip install --upgrade pip`; `sudo -u "$APP_USER" /srv/deanery/venv/bin/pip install -r /srv/deanery/app/requirements.txt` (production requirements only).
9. **PostgreSQL (trial database)** — stock settings: do NOT raise `shared_buffers`, keep `max_connections`. `DB_PASS=$(openssl rand -hex 24)`; `sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE ROLE deanery LOGIN PASSWORD '$DB_PASS';" -c "CREATE DATABASE deanery_trial OWNER deanery ENCODING 'UTF8' TEMPLATE template0;"`.
10. **Environment file** — `sudo mkdir -p /etc/deanery`; build it from `.env.production.example` with `sed` replacing: `example.com` → `$DOMAIN`; `SECRET_KEY` → `$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")`; `REPLACE_ME_DB_PASSWORD` → `$DB_PASS`; database name `/deanery` → `/deanery_trial` and `PRIVATE_MEDIA_ROOT` → `/srv/deanery/private_media_trial` (trial, D10); `ADMIN_URL` → `staff-$(openssl rand -hex 6)/`; `DEMO_PASSWORD` → a password the user chooses (allowed characters, D8); write to `/etc/deanery/deanery.env`; `sudo chown "$APP_USER:$APP_USER" /etc/deanery/deanery.env && sudo chmod 600 /etc/deanery/deanery.env`; `unset DB_PASS`. Show the final file with `sudo -u "$APP_USER" grep -v -E 'SECRET_KEY|PASSWORD' /etc/deanery/deanery.env` (never print secrets).
11. **Django** — `M="sudo -u $APP_USER /srv/deanery/app/deploy/manage.sh"`; `$M migrate`; `$M collectstatic --noinput`; `$M check --deploy --fail-level WARNING`; `$M createsuperuser` (role must stay empty — Django superuser for the admin only).
12. **gunicorn + systemd** — copy `deploy/systemd/deanery.service` with `sed "s/<APP_USER>/$APP_USER/g"` to `/etc/systemd/system/deanery.service`; `sudo systemctl daemon-reload && sudo systemctl enable --now deanery`; check `systemctl status deanery`, `curl -s http://127.0.0.1:8000/health/` → `{"status": "ok"}` (Host header: `curl -s -H "Host: $DOMAIN" …`), `journalctl -u deanery -n 50`.
13. **nginx bootstrap + certificate** — install `deploy/nginx/deanery-bootstrap.conf` (with `sed "s/example.com/$DOMAIN/g"`) to `/etc/nginx/sites-available/deanery`, link to `sites-enabled`, remove `sites-enabled/default`, `sudo nginx -t && sudo systemctl reload nginx`; `sudo certbot certonly --webroot -w /var/www/letsencrypt -d "$DOMAIN" --email <your e-mail> --agree-tos --no-eff-email --deploy-hook "systemctl reload nginx"`.
14. **nginx full site** — replace with `deploy/nginx/deanery.conf` (same `sed`), `sudo nginx -t && sudo systemctl reload nginx`; auto-renewal: `systemctl list-timers certbot.timer` and `sudo certbot renew --dry-run`.
15. **Backups** — install `deploy/cron/deanery-backup` with `sed "s/<APP_USER>/$APP_USER/g"` to `/etc/cron.d/deanery-backup` (mode 644, root-owned); run once by hand `sudo -u "$APP_USER" /srv/deanery/app/deploy/backup.sh` and list `/srv/deanery/backups`; files older than 7 days are deleted by the script. Restore (short): `gunzip -c db-….sql.gz | psql "$DATABASE_URL"` into an empty database + `tar -xzf media-….tar.gz -C /srv/deanery` — always restore BOTH (README «Deployment notes»).
16. **Smoke check** — `curl -sI http://$DOMAIN/` → 301 to https; `curl -s https://$DOMAIN/health/` → ok; browser: login page, admin at `https://$DOMAIN/<ADMIN_URL>`; on the trial database run `$M seed_demo` (trial only) and open one page per role (student: Расписание, Заявки, Чат; staff: Заявки, Чаты); upload a PDF to a request (checks `client_max_body_size`); download it; `curl -s -o /dev/null -w '%{http_code}' https://$DOMAIN/private_media/` → 404 (no static route to private files).
17. **Final database on 2026-11-22 (once)** — create `deanery` DB owned by `deanery` (same role); edit the env file: database name `deanery_trial` → `deanery`, `PRIVATE_MEDIA_ROOT=/srv/deanery/private_media`; `$M migrate`; `$M seed_demo` (ONCE, no cron, needs `DEMO_PASSWORD`); `sudo systemctl restart deanery`; repeat step 16 (without seeding). Optionally drop `deanery_trial` and empty `private_media_trial` after 2026-11-28.
18. **Update procedure** — `sudo -u "$APP_USER" git -C /srv/deanery/app pull --ff-only`; `sudo -u "$APP_USER" /srv/deanery/venv/bin/pip install -r /srv/deanery/app/requirements.txt`; `$M migrate`; `$M collectstatic --noinput`; `$M check --deploy --fail-level WARNING`; `sudo systemctl restart deanery`; smoke check.
19. **HSTS** — after the site works over HTTPS for a day: set `SECURE_HSTS_SECONDS=31536000` in the env file, restart; never enable `SECURE_HSTS_PRELOAD`. Explain that a large value cannot be undone for visitors before it expires, so raise it only after HTTPS is confirmed.
20. **Resources** — expected memory: gunicorn master + 2 workers ≈ 200–250 MB, PostgreSQL ≈ 100–150 MB, nginx ≈ 10 MB, system ≈ 200 MB → ≈ 600 MB of 1 GB, swap covers peaks (pip install, migrations); disk: venv ≈ 150 MB, journal ≤ 200 MB, backups (7 days, gzip) small. Check: `free -h`, `df -h`, `journalctl --disk-usage`, `systemctl status deanery`. If pages are slow or memory is full, upgrade the hosting tariff and raise `GUNICORN_WORKERS` by the formula (D2).
21. **Troubleshooting** — 502 → `journalctl -u deanery`; 400 Bad Request → `ALLOWED_HOSTS`; CSRF failure → `CSRF_TRUSTED_ORIGINS` with https; 413 → `client_max_body_size`; locked logins → `CLIENT_IP_HEADER` and the `X-Real-IP` header.

---

## 5. Functions
No application code changes, except minimal PostgreSQL fixes if CI finds failures (AC8; each fix with a regression test that runs on both databases). `deploy/gunicorn.conf.py` is a settings module (4.2). Shell scripts: 4.6.

## 6. Test plan

### 6.0 Rules
All tests in new `core/tests/test_deploy.py`, `SimpleTestCase` unless stated; read files relative to `settings.BASE_DIR`; never read `.env`. Save every test log; report any failed or stalled run by test name and Moscow time.

### 6.1 Traceability
| AC | Tests |
|---|---|
| AC1 | `GunicornConfigTests::*`; CI `gunicorn --check-config` |
| AC2 | `NginxTemplateTests::*` |
| AC3 | `SystemdUnitTests::*`, `SmallFilesTests::*`, `ShellScriptTests::*` |
| AC4 | `EnvExampleTests::*` |
| AC5 | CI job `test-postgres` (runs on push; the Team lead reports its result) |
| AC6 | `RunbookTests::*` + Reviewer reading |
| AC7 | `SecretScanTests::*` |
| AC8 | `REPORT` + regression tests if any fix |

### 6.2 Test details
- `NginxTemplateTests`:
  - `test_full_config_body_size` (`client_max_body_size 20m;` occurs exactly once, inside the `listen 443` server block)
  - `test_no_project_files_served` (in both nginx files every `root`/`alias` directive equals `root /var/www/letsencrypt;`; no `alias` at all; no `private_media`, `PRIVATE_MEDIA`, `/srv/deanery`, `location /static`, `location /media` substrings)
  - `test_http_redirects_to_https` (`return 301 https://$host$request_uri;` in the port-80 server of `deanery.conf`)
  - `test_acme_location_in_both` (`location ^~ /.well-known/acme-challenge/` in both files)
  - `test_proxy_headers` (the four `proxy_set_header` lines from 4.4 and `proxy_pass http://127.0.0.1:8000;`)
  - `test_no_headers_owned_by_django` (no `add_header` with `X-Frame-Options`, `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`)
  - `test_http2_syntax_for_nginx_1_24` (`listen 443 ssl http2;`; no `http2 on;`)
  - `test_bootstrap_has_no_tls_server` (no `listen 443` in `deanery-bootstrap.conf`)
- `EnvExampleTests`:
  - `test_parser_finds_known_variables` (the parser over the three sources returns a superset of {DEBUG, SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, ADMIN_URL, LOGIN_FAILURE_LIMIT, LOGIN_LOCKOUT_SECONDS, CLIENT_IP_HEADER, DATABASE_URL, PRIVATE_MEDIA_ROOT, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS, SECURE_HSTS_INCLUDE_SUBDOMAINS, SECURE_HSTS_PRELOAD, LOG_LEVEL, DEMO_PASSWORD, GUNICORN_WORKERS, GUNICORN_BIND}). Parser: regex `env\.(?:str|bool|int|list|db)\(\s*"([A-Z][A-Z0-9_]*)"` over `config/settings.py`; regex `os\.environ(?:\.get\(|\[)\s*"([A-Z][A-Z0-9_]*)"` over `*/management/commands/*.py` and `deploy/gunicorn.conf.py`; ignore `DJANGO_SETTINGS_MODULE`.
  - `test_lists_every_env_variable` (parsed set ⊆ keys of `.env.production.example`; keys = lines matching `^([A-Z][A-Z0-9_]*)=`)
  - `test_every_variable_has_comment` (the line before each `NAME=` line is a `#` comment, or the variable belongs to a block that starts with a comment — simplest: each key line is preceded within 3 lines by a `#` line)
  - `test_production_values` (DEBUG=false; CLIENT_IP_HEADER=X-Real-IP and `proxy_set_header X-Real-IP` present in nginx; DATABASE_URL starts with `postgres://`; every CSRF_TRUSTED_ORIGINS item starts with `https://`; SECURE_HSTS_PRELOAD=false; GUNICORN_WORKERS=2)
  - `test_deploy_check_passes_with_example_values`: build `env = {"PATH": os.environ["PATH"], **example_values}` (no other variables); `subprocess.run([sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"], cwd=BASE_DIR, env=env, capture_output=True, text=True, timeout=120)` → return code 0 and «System check identified no issues» in stdout. (`environ.Env.read_env` never overrides variables that are already set, so a developer `.env` cannot change the result — django-environ 0.14 `read_env(overwrite=False)` uses `setdefault`.)
- `GunicornConfigTests` (load with `runpy.run_path(path)` inside `mock.patch.dict(os.environ, {...}, clear=False)` after removing `GUNICORN_*` keys): `test_defaults` (bind `127.0.0.1:8000`, workers 2, timeout 30, graceful_timeout 30, accesslog `-`, errorlog `-`, `control_socket_disable` True), `test_env_override` (`GUNICORN_WORKERS=3` → 3; `GUNICORN_BIND=127.0.0.1:9000`), `test_workers_at_least_one` (`"0"` → 1), `test_bind_is_loopback_by_default`.
- `SystemdUnitTests`: `test_runs_as_app_user` (`User=<APP_USER>`; no `User=root`), `test_restart_on_failure`, `test_environment_file_outside_repo` (`EnvironmentFile=/etc/deanery/deanery.env`), `test_exec_uses_repo_config` (`-c deploy/gunicorn.conf.py config.wsgi:application`), `test_hardening` (`NoNewPrivileges=true`, `ProtectSystem=full`, `PrivateTmp=true`).
- `SmallFilesTests`: `test_journald_limit` (`SystemMaxUse=200M`), `test_ssh_hardening` (`PasswordAuthentication no`; file name starts with `10-`), `test_cron_daily_backup` (one line, runs `deploy/backup.sh` as `<APP_USER>`, logs via `logger`).
- `ShellScriptTests`: `test_bash_syntax` (`bash -n` on `deploy/backup.sh` and `deploy/manage.sh`; skip if `shutil.which("bash")` is None), `test_scripts_executable` (`os.access(path, os.X_OK)`), `test_backup_rules` (`pg_dump`, `| gzip`, `KEEP_DAYS:-7`, `-mtime`, `-delete`, `tar -czf`, `PRIVATE_MEDIA_ROOT`), `test_manage_uses_env_file` (`. /etc/deanery/deanery.env`, `set -euo pipefail`).
- `SecretScanTests` over every file in `deploy/` (recursive) + `.env.production.example` + `docs/DEPLOY.md`:
  - `test_no_private_keys_or_known_tokens` (none of: `-----BEGIN` … `PRIVATE KEY-----`, `ssh-(rsa|ed25519|ecdsa)[^\n]* AAAA`, `AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9]{20,}`, `xox[baprs]-`)
  - `test_no_long_random_strings` (no run `[A-Za-z0-9+=]{32,}` — 32+ characters without `-`, `_`, `/`, `.`)
  - `test_secret_like_assignments_are_placeholders` (for `NAME=value` lines where NAME contains `SECRET`, `PASSWORD`, `TOKEN` or `KEY`: value is empty, or contains `REPLACE` / `replace-me` / `change-me` / `<`, or is a `$(...)` / `$VAR` shell expression; `DATABASE_URL` password part contains `REPLACE` or `$`)
  - `test_no_real_ip_addresses` (IPv4 pattern matches only `127.0.0.1` or `0.0.0.0`)
- `RunbookTests` (`docs/DEPLOY.md`): `test_swap_before_packages` (index of `fallocate` < index of `apt -y install`), `test_required_topics` (contains `vm.swappiness=10`, `SystemMaxUse`, `ufw`, `certbot certonly --webroot`, `certbot renew --dry-run`, `chmod 600`, `token_urlsafe`, `openssl rand -hex 24`, `check --deploy`, `collectstatic`, `seed_demo`, `2026-11-22`, `deanery_trial`, `shared_buffers`, `free -h`, `df -h`, `journalctl --disk-usage`, `SECURE_HSTS_SECONDS=31536000`, `PasswordAuthentication`), `test_no_daily_seed_cron` (no line containing both `cron` and `seed_demo`).

### 6.3 Access matrix
No views change. Not applicable.

### 6.4 Settings branches
Production branch covered by `test_deploy_check_passes_with_example_values`; the existing `core/tests/test_production_settings.py` stays.

### 6.5 Query count
Not applicable.

### 6.6 PostgreSQL run
Locally: no PostgreSQL server and the Docker daemon is not running on this machine (9.7), so the Coder cannot run the PostgreSQL suite before commit. The CI job is the PostgreSQL check. If the user starts Docker Desktop, the Coder may additionally run `docker run --rm -d -p 5432:5432 -e POSTGRES_USER=deanery -e POSTGRES_PASSWORD=ci-only-postgres-password -e POSTGRES_DB=deanery postgres:16` and the test commands with the CI `DATABASE_URL`, and report the result. Static review of PostgreSQL-sensitive code (no change required now): `select_for_update(of=("self",))` with outer joins (`notifications/services.py:85`, `chat/services.py:94`); plain `select_for_update()` with inner `select_related` (`petitions/services.py:51`); `.distinct()` with ordering (`academics/services.py:199,212,279`, `schedule/services.py:92,112`, `schedule/validation.py:40`); `number__regex` and the `startswith(Cast(floor))` check constraints (`university/models.py`); `schedule/tests/test_locking.py:75` takes the real-lock branch on PostgreSQL. Any CI failure → minimal fix in a follow-up (the Team lead decides: same task round or `TASK-011-FIX`).

---

## 7. Implementation order
1. `requirements.txt`, `deploy/gunicorn.conf.py` + `GunicornConfigTests` (if `pip install gunicorn==26.2.0` cannot reach PyPI on your machine, say so in the `REPORT`; the tests do not import gunicorn; CI installs it).
2. nginx, systemd, journald, ssh, cron, scripts (chmod 755) + tests.
3. `.env.production.example` + `EnvExampleTests`.
4. CI changes.
5. `docs/DEPLOY.md` + `RunbookTests` + `SecretScanTests`; README bullet.
6. `ruff format` on changed Python files only; section 8; `REPORT` to the Reviewer. Do not commit.

## 8. Verification
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
bash -n deploy/backup.sh deploy/manage.sh && echo "shell syntax ok"
node --check static/js/chat.js && echo "js syntax ok"
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
# optional, if gunicorn could be installed: gunicorn --check-config -c deploy/gunicorn.conf.py config.wsgi:application
export DATABASE_URL="sqlite:///$TMPDIR/task011.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task011-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
rm -f "$TMPDIR/task011.sqlite3"
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
git status --short
```
`nginx -t`: nginx is not installed on this machine (9.7) — not run; the Team lead runs `sudo nginx -t` on the server (runbook steps 13–14).
`REPORT`: output tails, test count (was 964), log file names, any failed or stalled run by test name and Moscow time, whether gunicorn was installed locally, PostgreSQL status (6.6), `git status`.

## 9. Feasibility check (2026-11-17 13:09 MSK on `d9d8e55`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — env reads in `config/settings.py` (lines 17–30, 89, 127, 144–148, 154: 15 variables) and `os.environ.get("DEMO_PASSWORD")` in `accounts/management/commands/seed_demo.py:20`; `config/env_utils.py` (`resolve_client_ip_header` accepts `X-Real-IP` → `HTTP_X_REAL_IP`; `resolve_admin_url` pattern); `accounts/throttling.py:23-37` (reads the configured header, `X-Forwarded-For` → last item); `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`, `SECURE_REDIRECT_EXEMPT = [r"^health/$"]`, WhiteNoise middleware and `CompressedManifestStaticFilesStorage` when `DEBUG=false` (`config/settings.py`); `/health/` view; `.env.example` (development); CI workflow (`test` job only, SQLite); README "Deployment notes"; `plan.md` 6b. OK.
3. No collisions — no `deploy/` directory, no `.env.production.example`, no `docs/DEPLOY.md`, no `core/tests/test_deploy.py`, no `test-postgres` CI job, no `gunicorn` in requirements. OK.
4. Migrations — none. OK.
5. Tools — PyPI via `pip` is unreachable from this sandbox (TLS error), but `curl` works: gunicorn metadata (latest 27.0.1 from 2026-11-12; 27.0.0 from 2026-11-10; 26.2.0 from 2026-08-24, `requires_python >=3.10`, no runtime dependencies). The 26.2.0 wheel (sha256 `bd249d0b3f7972f7432f0a6b6ff3b3ee2d129f70cd1ff6c09a9dd9e29a2b88e3`) was installed into a temporary venv. OK.
6. Framework / runtime — with the 4.2 config (temporary copy) against this project: `gunicorn --check-config` → OK; 2 workers boot; `GET /health/` → 200 with Django's security headers; gunicorn 26 tried to create `$HOME/.gunicorn` for its control server until `control_socket_disable = True` was added (then no error). `manage.py check --deploy --fail-level WARNING` with exactly the 4.7 values in a clean environment → «System check identified no issues (1 silenced)». django-environ 0.14 `read_env(overwrite=False)` uses `setdefault` (does not override). `security.W005` requires `SECURE_HSTS_INCLUDE_SUBDOMAINS=true` → kept true. nginx 1.24 (Ubuntu 24.04) needs `listen … ssl http2;` syntax (D7). OK.
7. Environment — no PostgreSQL server, `psql`, `nginx` or `gunicorn` installed locally; Docker CLI exists but the daemon is not running (`docker info` → socket not found). Local alternative: CI job (6.6). Not a blocker: the request allows "local or CI PostgreSQL if available".
8. Verification runnable — 9a.
9. Conflicts — none. D10 (trial database `deanery_trial`, final database `deanery` + one-time `seed_demo` on 2026-11-22) confirmed by the user via the Team lead on 2026-11-17. The GitHub remote exists; the user pushes, so the `test-postgres` CI job runs after the TASK-011 commit is pushed.
10. Assumptions / blockers — none.

### 9a. Verification results on the current tree
Logs `$TMPDIR/test-20261117-130935-t011-feas*.log`.
- `check` → no issues; `makemigrations --check --dry-run` → «No changes detected».
- `test` → `Ran 964 tests … OK`; `run_tests_at.py 2026-11-17T23:59:59` → 964 OK; `run_tests_at.py 2026-11-18T00:00:00` → 964 OK. No failed or stalled runs.
- `check --deploy --fail-level WARNING` → no issues (1 silenced); `ruff check .` → all passed; `ruff format --check .` → 183 files already formatted; `node --check static/js/chat.js` → ok; CI YAML ok.
- `seed_demo` twice on a temporary DB and PRIVATE_MEDIA_ROOT → OK (second run «Chat ready: 0 dialogs, 0 messages.»).

## 10. Risks
- **PostgreSQL-only failures** appear only in CI after the Team lead pushes; plan a quick fix round.
- **Lockout of SSH**: the runbook keeps a session open and verifies key login before closing it; `10-` file name beats `50-cloud-init.conf`.
- **Secrets in shell history / output**: generated inline into the env file; never echoed; the runbook shows the env file with secrets filtered out.
- **Memory**: 2 workers + PostgreSQL fit in 1 GB with swap; `max_requests` recycles workers to limit memory growth.
- **Certificate issuance** needs the DNS A record before step 13.
- **Trusted proxy headers**: safe only because gunicorn listens on loopback; never bind it to `0.0.0.0`.
