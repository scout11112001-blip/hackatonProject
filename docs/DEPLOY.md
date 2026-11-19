# Deployment runbook

Production deployment of the Deanery prototype on Ubuntu 24.04 (2 vCPU, ~2 GB
RAM, 20 GB disk, 512 MB swap from the provider), one domain with HTTPS, serving
until 2026-11-28.

The agents have no server access; this runbook documents the manual steps. Run
every command as the sudo user unless a step says otherwise. Keep one SSH
session open until step 4 is verified, so you do not lock yourself out.

Set the shell variables once, then reuse them in every step:

```bash
DOMAIN=example.com
APP_USER=deanery
REPO_URL=<your repository URL>
```

## 0. Before you start

You need:

- a domain whose `A` record already points at the server IP;
- an SSH key you created and installed on the server:

```bash
ssh-keygen -t ed25519
ssh-copy-id "$APP_USER"@<server-ip>
```

Keep one SSH session open until step 4 (SSH hardening) is verified.

## 1. Memory and swap check

The provider already created a 512 MB swap. Check that it is active; do not
create or resize swap.

```bash
swapon --show && free -h
```

## 2. Time zone

Cron and logs use Moscow time.

```bash
sudo timedatectl set-timezone Europe/Moscow
```

## 3. Packages

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install python3.12-venv nginx postgresql certbot git ufw
```

## 4. SSH: keys only

Copy `deploy/ssh/10-deanery-hardening.conf` (in the cloned repo, at
`/srv/deanery/app/deploy/ssh/10-deanery-hardening.conf`) to
`/etc/ssh/sshd_config.d/`; the `10-` name sorts before Ubuntu's
`50-cloud-init.conf`, so it wins. The file sets `PasswordAuthentication no`,
`PermitRootLogin prohibit-password` and `PubkeyAuthentication yes`. This step
may be done right after step 6, once the repo is cloned.

```bash
sudo install -m 644 /srv/deanery/app/deploy/ssh/10-deanery-hardening.conf /etc/ssh/sshd_config.d/
sudo sshd -t && sudo systemctl reload ssh
sudo sshd -T | grep -Ei 'passwordauthentication|permitrootlogin'
```

Open a **new** SSH session with your key and verify it logs in before closing
the old one.

## 5. Firewall

Only SSH, HTTP and HTTPS.

```bash
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable && sudo ufw status
```

## 6. App user, directories, code

```bash
sudo adduser --system --group --home /srv/deanery --shell /bin/bash "$APP_USER"
sudo -u "$APP_USER" git clone "$REPO_URL" /srv/deanery/app
sudo -u "$APP_USER" mkdir -p /srv/deanery/private_media /srv/deanery/private_media_trial /srv/deanery/backups
sudo chmod 750 /srv/deanery/private_media /srv/deanery/private_media_trial && sudo chmod 700 /srv/deanery/backups
sudo mkdir -p /var/www/letsencrypt
```

## 7. Python venv

```bash
sudo -u "$APP_USER" python3.12 -m venv /srv/deanery/venv
sudo -u "$APP_USER" /srv/deanery/venv/bin/pip install --upgrade pip
sudo -u "$APP_USER" /srv/deanery/venv/bin/pip install -r /srv/deanery/app/requirements.txt
```

## 8. PostgreSQL (trial database)

```bash
DB_PASS=$(openssl rand -hex 24)
sudo -u postgres psql -v ON_ERROR_STOP=1 \
  -c "CREATE ROLE deanery LOGIN PASSWORD '$DB_PASS';" \
  -c "CREATE DATABASE deanery_trial OWNER deanery ENCODING 'UTF8' TEMPLATE template0;"
```

## 9. Environment file

Build `/etc/deanery/deanery.env` from
`/srv/deanery/app/.env.production.example`, replacing the placeholders. Values
must not need shell quoting.

```bash
sudo mkdir -p /etc/deanery
SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
ADMIN_PATH="staff-$(openssl rand -hex 6)/"
DEMO_PW=<a password you choose, letters/digits/-/_/. only>
sed -e "s/example\.com/$DOMAIN/g" \
    -e "s|replace-me-with-secrets-token-urlsafe-50-generated-on-the-server|$SECRET|" \
    -e "s|REPLACE_ME_DB_PASSWORD|$DB_PASS|" \
    -e "s|@localhost:5432/deanery$|@localhost:5432/deanery_trial|" \
    -e "s|^PRIVATE_MEDIA_ROOT=.*|PRIVATE_MEDIA_ROOT=/srv/deanery/private_media_trial|" \
    -e "s|staff-panel-change-me/|$ADMIN_PATH|" \
    -e "s|REPLACE_ME_DEMO_PASSWORD|$DEMO_PW|" \
    /srv/deanery/app/.env.production.example | sudo tee /etc/deanery/deanery.env > /dev/null
sudo chown "$APP_USER:$APP_USER" /etc/deanery/deanery.env && sudo chmod 600 /etc/deanery/deanery.env
unset DB_PASS SECRET DEMO_PW
```

Show the final file without printing secrets:

```bash
sudo -u "$APP_USER" grep -v -E 'SECRET_KEY|PASSWORD' /etc/deanery/deanery.env
```

## 10. Django

```bash
M="sudo -u $APP_USER /srv/deanery/app/deploy/manage.sh"
$M migrate
$M collectstatic --noinput
$M check --deploy --fail-level WARNING
$M createsuperuser
```

Leave the superuser role empty — a Django superuser is for the admin only.

## 11. gunicorn + systemd

```bash
sed "s/<APP_USER>/$APP_USER/g" /srv/deanery/app/deploy/systemd/deanery.service | sudo tee /etc/systemd/system/deanery.service > /dev/null
sudo systemctl daemon-reload && sudo systemctl enable --now deanery
systemctl status deanery
curl -s -H "Host: $DOMAIN" http://127.0.0.1:8000/health/
journalctl -u deanery -n 50
```

`/health/` should return `{"status": "ok"}`.

## 12. nginx bootstrap + certificate

```bash
sed "s/example.com/$DOMAIN/g" /srv/deanery/app/deploy/nginx/deanery-bootstrap.conf | sudo tee /etc/nginx/sites-available/deanery > /dev/null
sudo ln -sf /etc/nginx/sites-available/deanery /etc/nginx/sites-enabled/deanery
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certonly --webroot -w /var/www/letsencrypt -d "$DOMAIN" --email <your e-mail> --agree-tos --no-eff-email --deploy-hook "systemctl reload nginx"
```

## 13. nginx full site

```bash
sed "s/example.com/$DOMAIN/g" /srv/deanery/app/deploy/nginx/deanery.conf | sudo tee /etc/nginx/sites-available/deanery > /dev/null
sudo nginx -t && sudo systemctl reload nginx
systemctl list-timers certbot.timer
sudo certbot renew --dry-run
```

## 14. Backups

```bash
sed "s/<APP_USER>/$APP_USER/g" /srv/deanery/app/deploy/cron/deanery-backup | sudo tee /etc/cron.d/deanery-backup > /dev/null
sudo chmod 644 /etc/cron.d/deanery-backup
sudo -u "$APP_USER" /srv/deanery/app/deploy/backup.sh
ls -l /srv/deanery/backups
```

Files older than 7 days are deleted by the script. To restore into an empty
target database (always restore the database and the media together):

```bash
sudo -u "$APP_USER" bash -c 'set -a; . /etc/deanery/deanery.env; gunzip -c /srv/deanery/backups/db-<STAMP>.sql.gz | psql "$DATABASE_URL"'
sudo -u "$APP_USER" bash -c 'tar -xzf /srv/deanery/backups/media-<STAMP>.tar.gz -C /srv/deanery'
```

## 15. Smoke check

```bash
curl -sI http://$DOMAIN/ | head -1
curl -s https://$DOMAIN/health/
curl -s -o /dev/null -w '%{http_code}' https://$DOMAIN/private_media/
```

Expected: `http://` → 301 to https; `/health/` → ok; `/private_media/` → 404.
In the browser: the login page, the admin at `https://$DOMAIN/<ADMIN_URL>`.
On the **trial** database run `$M seed_demo` once, then open one page per role
(student: Расписание, Заявки, Чат; staff: Заявки, Чаты); upload a PDF to a
request (checks `client_max_body_size`) and download it.

## 16. Final database on 2026-11-22 (once)

Create the final database (the `deanery` role already exists from step 8):

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE deanery OWNER deanery ENCODING 'UTF8' TEMPLATE template0;"
```

Switch the env file from the trial database to the final one (this runs days
later, in a new shell, so re-define `M`):

```bash
sudo sed -i \
  -e 's|@localhost:5432/deanery_trial$|@localhost:5432/deanery|' \
  -e 's|^PRIVATE_MEDIA_ROOT=.*|PRIVATE_MEDIA_ROOT=/srv/deanery/private_media|' \
  /etc/deanery/deanery.env
M="sudo -u $APP_USER /srv/deanery/app/deploy/manage.sh"
$M migrate
$M seed_demo
sudo systemctl restart deanery
```

Run `seed_demo` exactly once; do not schedule it as a recurring job. Repeat
step 15 (without seeding). Optionally drop `deanery_trial` and empty
`private_media_trial` after 2026-11-28.

## 17. Update procedure

```bash
sudo -u "$APP_USER" git -C /srv/deanery/app pull --ff-only
sudo -u "$APP_USER" /srv/deanery/venv/bin/pip install -r /srv/deanery/app/requirements.txt
$M migrate
$M collectstatic --noinput
$M check --deploy --fail-level WARNING
sudo systemctl restart deanery
```

Then repeat the smoke check (step 15).

## 18. HSTS

After the site works over HTTPS for a day, raise the HSTS max-age in the env
file and restart:

```bash
sudo sed -i 's/^SECURE_HSTS_SECONDS=.*/SECURE_HSTS_SECONDS=31536000/' /etc/deanery/deanery.env
sudo systemctl restart deanery
curl -sI https://$DOMAIN/ | grep -i strict-transport
```

A large value cannot be undone for visitors before it expires, so raise it only
after HTTPS is confirmed. Never enable `SECURE_HSTS_PRELOAD` (it is an
irreversible browser-list commitment for this prototype).

## 19. Resources

Server: 2 vCPU, ~2 GB RAM (1.9 GB usable), 20 GB disk, 512 MB swap from the
provider.

Workers: `GUNICORN_WORKERS=5` by the formula
`min(2 × vCPU + 1, (free RAM MB − 300) / 90)` = min(5, 13) = 5.

Expected memory: gunicorn master + 5 workers ≈ 350–500 MB (≈ 60–90 MB per
worker), PostgreSQL ≈ 150–200 MB (shared memory and up to 5 connections),
nginx ≈ 10 MB, system ≈ 250 MB → ≈ 750–950 MB of 1.9 GB. The rest holds the
file cache and the peaks of `pip install`, `migrate` and `collectstatic`; the
swap covers rare peaks.

Disk: system and packages ≈ 4 GB, code ≈ 50 MB, venv ≈ 150 MB, PostgreSQL data
(trial and final databases) ≈ 100 MB, backups (7 days, gzip) small, journal at
most ≈ 2 GB → at most ≈ 7 GB of 20 GB. Logs: journald uses the systemd
defaults (at most 10% of the file system, at most 4 GB; it keeps 15% of the
file system free). nginx logs are rotated by the stock
`/etc/logrotate.d/nginx`.

```bash
free -h
swapon --show
df -h
journalctl --disk-usage
systemctl status deanery
```

If pages are slow or memory is full (`free -h` shows little available memory
and the swap is in use), lower `GUNICORN_WORKERS` in `/etc/deanery/deanery.env`
and run `sudo systemctl restart deanery`. On a bigger server raise it by the
same formula.

## 20. Troubleshooting

- 502 Bad Gateway → `journalctl -u deanery`.
- 400 Bad Request → check `ALLOWED_HOSTS`.
- CSRF failure → `CSRF_TRUSTED_ORIGINS` must use `https://`.
- 413 Request Entity Too Large → `client_max_body_size` (20m).
- Locked logins / wrong client IP → `CLIENT_IP_HEADER` and the `X-Real-IP`
  header set by nginx.
