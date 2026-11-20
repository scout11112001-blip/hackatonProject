"""Deployment artefacts: gunicorn, nginx, systemd, scripts, env example, runbook.

These tests read repository files relative to ``settings.BASE_DIR`` and never
read a developer ``.env``. They are safe to run on any machine (no server,
no nginx, no gunicorn, no PostgreSQL required).
"""

import os
import re
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase

BASE_DIR = Path(settings.BASE_DIR)
DEPLOY_DIR = BASE_DIR / "deploy"

NGINX_CONF = DEPLOY_DIR / "nginx" / "deanery.conf"
NGINX_BOOTSTRAP = DEPLOY_DIR / "nginx" / "deanery-bootstrap.conf"
GUNICORN_CONF = DEPLOY_DIR / "gunicorn.conf.py"
SYSTEMD_UNIT = DEPLOY_DIR / "systemd" / "deanery.service"
SSH_HARDENING = DEPLOY_DIR / "ssh" / "10-deanery-hardening.conf"
CRON = DEPLOY_DIR / "cron" / "deanery-backup"
BACKUP_SH = DEPLOY_DIR / "backup.sh"
MANAGE_SH = DEPLOY_DIR / "manage.sh"

ENV_EXAMPLE = BASE_DIR / ".env.production.example"
DEPLOY_MD = BASE_DIR / "docs" / "DEPLOY.md"

# The sed `-e` rules of the "Environment file" step (docs/DEPLOY.md); kept here so the
# test can run them.
ENV_FILE_SED_EXPRS = (
    "s/example\\.com/$DOMAIN/g",
    "s|replace-me-with-secrets-token-urlsafe-50-generated-on-the-server|$SECRET|",
    "s|REPLACE_ME_DB_PASSWORD|$DB_PASS|",
    "s|@localhost:5432/deanery$|@localhost:5432/deanery_trial|",
    "s|^PRIVATE_MEDIA_ROOT=.*|PRIVATE_MEDIA_ROOT=/srv/deanery/private_media_trial|",
    "s|staff-panel-change-me/|$ADMIN_PATH|",
    "s|REPLACE_ME_DEMO_PASSWORD|$DEMO_PW|",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class GunicornConfigTests(SimpleTestCase):
    def _load_config(self, overrides: dict[str, str] | None = None):
        base = {k: v for k, v in os.environ.items() if not k.startswith("GUNICORN_")}
        base.update(overrides or {})
        with mock.patch.dict(os.environ, base, clear=True):
            return runpy.run_path(str(GUNICORN_CONF))

    def test_defaults(self):
        cfg = self._load_config()
        self.assertEqual(cfg["bind"], "127.0.0.1:8000")
        self.assertEqual(cfg["workers"], 5)  # TASK-015: 2 vCPU / ~2 GB server
        self.assertEqual(cfg["timeout"], 30)
        self.assertEqual(cfg["graceful_timeout"], 30)
        self.assertEqual(cfg["accesslog"], "-")
        self.assertEqual(cfg["errorlog"], "-")
        self.assertIs(cfg["control_socket_disable"], True)
        # TASK-016 (PT1-F13): trust only X-Forwarded-Proto.
        self.assertEqual(cfg["secure_scheme_headers"], {"X-FORWARDED-PROTO": "https"})

    def test_env_override(self):
        cfg = self._load_config({"GUNICORN_WORKERS": "3", "GUNICORN_BIND": "127.0.0.1:9000"})
        self.assertEqual(cfg["workers"], 3)
        self.assertEqual(cfg["bind"], "127.0.0.1:9000")

    def test_workers_at_least_one(self):
        cfg = self._load_config({"GUNICORN_WORKERS": "0"})
        self.assertEqual(cfg["workers"], 1)

    def test_bind_is_loopback_by_default(self):
        self.assertEqual(self._load_config()["bind"], "127.0.0.1:8000")


class NginxTemplateTests(SimpleTestCase):
    def test_full_config_body_size(self):
        text = _read(NGINX_CONF)
        self.assertEqual(text.count("client_max_body_size 20m;"), 1)
        self.assertGreater(
            text.index("client_max_body_size 20m;"), text.index("listen 443 ssl http2;")
        )

    def test_no_project_files_served(self):
        for path in (NGINX_CONF, NGINX_BOOTSTRAP):
            text = _read(path)
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("root ") or stripped.startswith("alias "):
                    self.assertEqual(stripped, "root /var/www/letsencrypt;", path.name)
            self.assertNotIn("alias ", text, path.name)
            # Forbidden only in directives, not in the "# PRIVATE_MEDIA_ROOT must never…" comment.
            active = "\n".join(
                line for line in text.splitlines() if not line.lstrip().startswith("#")
            )
            for forbidden in (
                "private_media",
                "PRIVATE_MEDIA",
                "/srv/deanery",
                "location /static",
                "location /media",
            ):
                self.assertNotIn(forbidden, active, f"{path.name}: {forbidden}")

    def test_http_redirects_to_https(self):
        # TASK-016 (PT1-F4): the redirect target is the fixed domain, never $host.
        text = _read(NGINX_CONF)
        self.assertEqual(text.count("return 301 https://example.com$request_uri;"), 2)
        self.assertNotIn("$host$request_uri", text)

    def test_catch_all_servers(self):
        text = _read(NGINX_CONF)
        for line in (
            "listen 80 default_server;",
            "listen [::]:80 default_server;",
            "return 444;",
            "listen 443 ssl http2 default_server;",
            "listen [::]:443 ssl http2 default_server;",
            "ssl_reject_handshake on;",
        ):
            self.assertEqual(text.count(line), 1, line)
        self.assertEqual(text.count("server_name _;"), 2)

    def test_www_redirect_and_acme(self):
        text = _read(NGINX_CONF)
        self.assertIn("server_name example.com www.example.com;", text)
        self.assertIn("server_name www.example.com;", text)
        self.assertIn("server_name example.com www.example.com;", _read(NGINX_BOOTSTRAP))

    def test_login_rate_limit(self):
        text = _read(NGINX_CONF)
        for line in (
            "POST    $binary_remote_addr;",
            'default "";',
            "limit_req_zone $deanery_login_key zone=deanery_login:10m rate=10r/m;",
            "limit_req zone=deanery_login burst=10 nodelay;",
            "limit_req_status 429;",
            "limit_conn_zone $binary_remote_addr zone=deanery_conn:10m;",
            "limit_conn deanery_conn 20;",
            "limit_conn_status 429;",
        ):
            self.assertEqual(text.count(line), 1, line)

    def test_login_location_pattern(self):
        match = re.search(r"location ~ (\S+) \{", _read(NGINX_CONF))
        self.assertIsNotNone(match)
        pattern = re.compile(match.group(1))
        for path in ("/login/", "/staff-1a2b3c/login/", "/a/b_c/login/", "/admin/login/"):
            self.assertIsNotNone(pattern.search(path), path)
        for path in ("/login/x", "/logout/", "/loginx/", "/profile/", "/login"):
            self.assertIsNone(pattern.search(path), path)

    def test_proxy_headers_at_server_level(self):
        lines = _read(NGINX_CONF).splitlines()
        headers = [line for line in lines if "proxy_set_header" in line]
        self.assertEqual(len(headers), 4)
        for line in headers:
            self.assertTrue(line.startswith("    proxy_set_header"), line)
            self.assertFalse(line.startswith("        "), line)
        self.assertEqual(sum("proxy_pass http://127.0.0.1:8000;" in line for line in lines), 2)

    def test_acme_location_in_both(self):
        for path in (NGINX_CONF, NGINX_BOOTSTRAP):
            self.assertIn("location ^~ /.well-known/acme-challenge/", _read(path), path.name)

    def test_proxy_headers(self):
        text = _read(NGINX_CONF)
        for header in (
            "proxy_set_header Host $host;",
            "proxy_set_header X-Real-IP $remote_addr;",
            "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "proxy_set_header X-Forwarded-Proto $scheme;",
            "proxy_pass http://127.0.0.1:8000;",
        ):
            self.assertIn(header, text)

    def test_no_headers_owned_by_django(self):
        owned = (
            "X-Frame-Options",
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "Referrer-Policy",
        )
        for line in _read(NGINX_CONF).splitlines():
            if "add_header" in line:
                for header in owned:
                    self.assertNotIn(header, line)

    def test_http2_syntax_for_nginx_1_24(self):
        text = _read(NGINX_CONF)
        self.assertIn("listen 443 ssl http2;", text)
        self.assertNotIn("http2 on;", text)

    def test_bootstrap_has_no_tls_server(self):
        self.assertNotIn("listen 443", _read(NGINX_BOOTSTRAP))


def _parsed_env_variables() -> set[str]:
    env_call = re.compile(r'env\.(?:str|bool|int|list|db)\(\s*"([A-Z][A-Z0-9_]*)"')
    os_env = re.compile(r'os\.environ(?:\.get\(|\[)\s*"([A-Z][A-Z0-9_]*)"')
    names: set[str] = set()
    names.update(env_call.findall(_read(BASE_DIR / "config" / "settings.py")))
    for path in BASE_DIR.glob("*/management/commands/*.py"):
        names.update(os_env.findall(_read(path)))
    names.update(os_env.findall(_read(GUNICORN_CONF)))
    names.discard("DJANGO_SETTINGS_MODULE")
    return names


def _parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line)
        if m:
            values[m.group(1)] = m.group(2)
    return values


def _example_values() -> dict[str, str]:
    return _parse_env(_read(ENV_EXAMPLE))


class EnvExampleTests(SimpleTestCase):
    KNOWN = {
        "DEBUG",
        "SECRET_KEY",
        "ALLOWED_HOSTS",
        "CSRF_TRUSTED_ORIGINS",
        "ADMIN_URL",
        "LOGIN_FAILURE_LIMIT",
        "LOGIN_LOCKOUT_SECONDS",
        "CLIENT_IP_HEADER",
        "DATABASE_URL",
        "PRIVATE_MEDIA_ROOT",
        "SECURE_SSL_REDIRECT",
        "SECURE_HSTS_SECONDS",
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        "SECURE_HSTS_PRELOAD",
        "LOG_LEVEL",
        "DEMO_PASSWORD",
        "GUNICORN_WORKERS",
        "GUNICORN_BIND",
    }

    def test_parser_finds_known_variables(self):
        self.assertTrue(self.KNOWN <= _parsed_env_variables())

    def test_lists_every_env_variable(self):
        self.assertTrue(_parsed_env_variables() <= set(_example_values()))

    def test_every_variable_has_comment(self):
        lines = _read(ENV_EXAMPLE).splitlines()
        key_lines = [i for i, line in enumerate(lines) if re.match(r"^[A-Z][A-Z0-9_]*=", line)]
        for i in key_lines:
            self.assertTrue(
                any(lines[j].lstrip().startswith("#") for j in (i - 1, i - 2, i - 3) if j >= 0),
                f"line {i + 1} has no comment within 3 lines",
            )

    def test_production_values(self):
        values = _example_values()
        self.assertEqual(values["DEBUG"], "false")
        self.assertEqual(values["CLIENT_IP_HEADER"], "X-Real-IP")
        self.assertIn("proxy_set_header X-Real-IP", _read(NGINX_CONF))
        self.assertTrue(values["DATABASE_URL"].startswith("postgres://"))
        for origin in values["CSRF_TRUSTED_ORIGINS"].split(","):
            self.assertTrue(origin.startswith("https://"))
        self.assertEqual(values["SECURE_HSTS_PRELOAD"], "false")
        self.assertEqual(values["GUNICORN_WORKERS"], "5")  # TASK-015: 2 vCPU / ~2 GB server

    def test_deploy_check_passes_with_example_values(self):
        env = {"PATH": os.environ["PATH"], **_example_values()}
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
            cwd=str(BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("System check identified no issues", result.stdout)


class SystemdUnitTests(SimpleTestCase):
    def test_runs_as_app_user(self):
        unit = _read(SYSTEMD_UNIT)
        self.assertIn("User=<APP_USER>", unit)
        self.assertNotIn("User=root", unit)

    def test_restart_on_failure(self):
        self.assertIn("Restart=on-failure", _read(SYSTEMD_UNIT))

    def test_environment_file_outside_repo(self):
        self.assertIn("EnvironmentFile=/etc/deanery/deanery.env", _read(SYSTEMD_UNIT))

    def test_exec_uses_repo_config(self):
        self.assertIn("-c deploy/gunicorn.conf.py config.wsgi:application", _read(SYSTEMD_UNIT))

    def test_hardening(self):
        # TASK-016 (PT1-F13): ProtectSystem=strict and more sandboxing.
        lines = _read(SYSTEMD_UNIT).splitlines()
        for line in (
            "NoNewPrivileges=true",
            "PrivateTmp=true",
            "PrivateDevices=true",
            "ProtectSystem=strict",
            "ProtectHome=true",
            "ProtectKernelTunables=true",
            "ProtectControlGroups=true",
            "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX",
            "CapabilityBoundingSet=",
            "ReadWritePaths=/srv/deanery/private_media /srv/deanery/private_media_trial",
        ):
            self.assertIn(line, lines)
        self.assertNotIn("ProtectSystem=full", lines)
        self.assertEqual(sum(line.startswith("ReadWritePaths=") for line in lines), 1)


class SmallFilesTests(SimpleTestCase):
    def test_ssh_hardening(self):
        self.assertIn("PasswordAuthentication no", _read(SSH_HARDENING))
        self.assertTrue(SSH_HARDENING.name.startswith("10-"))

    def test_cron_daily_backup(self):
        lines = [
            line
            for line in _read(CRON).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(len(lines), 1)
        self.assertIn("deploy/backup.sh", lines[0])
        self.assertIn("<APP_USER>", lines[0])
        self.assertIn("logger", lines[0])


class ShellScriptTests(SimpleTestCase):
    def test_bash_syntax(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash not available")
        result = subprocess.run(  # noqa: S603
            [bash, "-n", str(BACKUP_SH), str(MANAGE_SH)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_scripts_executable(self):
        self.assertTrue(os.access(BACKUP_SH, os.X_OK))
        self.assertTrue(os.access(MANAGE_SH, os.X_OK))

    def test_backup_rules(self):
        backup = _read(BACKUP_SH)
        for fragment in (
            "pg_dump",
            "| gzip",
            "KEEP_DAYS:-7",
            "-mtime",
            "-delete",
            "tar -czf",
            "PRIVATE_MEDIA_ROOT",
        ):
            self.assertIn(fragment, backup)

    def test_backup_runs_from_root_directory(self):
        # TASK-015-FIX: "sudo -u <APP_USER> backup.sh" from /root failed in find.
        lines = [line.strip() for line in _read(BACKUP_SH).splitlines()]
        self.assertIn("cd /", lines)
        cd_index = lines.index("cd /")
        for command in ("pg_dump", "tar -czf", "find "):
            first = next(i for i, line in enumerate(lines) if line.startswith(command))
            self.assertLess(cd_index, first, command)

    def test_manage_uses_env_file(self):
        manage = _read(MANAGE_SH)
        self.assertIn(". /etc/deanery/deanery.env", manage)
        self.assertIn("set -euo pipefail", manage)


def _secret_scan_paths() -> list[Path]:
    paths = [
        p
        for p in DEPLOY_DIR.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]
    paths.extend([ENV_EXAMPLE, DEPLOY_MD])
    return paths


class SecretScanTests(SimpleTestCase):
    def test_no_private_keys_or_known_tokens(self):
        patterns = (
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
            r"ssh-(?:rsa|ed25519|ecdsa)[^\n]* AAAA",
            r"AKIA[0-9A-Z]{16}",
            r"ghp_[A-Za-z0-9]{20,}",
            r"xox[baprs]-",
        )
        for path in _secret_scan_paths():
            text = _read(path)
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, text), f"{path.name}: {pattern}")

    def test_no_long_random_strings(self):
        pattern = re.compile(r"[A-Za-z0-9+=]{32,}")
        for path in _secret_scan_paths():
            self.assertIsNone(pattern.search(_read(path)), path.name)

    def test_secret_like_assignments_are_placeholders(self):
        secret_name = re.compile(
            r"^([A-Za-z0-9_]*?(?:SECRET|PASSWORD|TOKEN|KEY)[A-Za-z0-9_]*)=(.*)$"
        )

        def is_placeholder(value: str) -> bool:
            return (
                value == ""
                or "REPLACE" in value
                or "replace-me" in value
                or "change-me" in value
                or "<" in value
                or value.startswith("$(")
                or value.startswith("$")
            )

        for path in _secret_scan_paths():
            for line in _read(path).splitlines():
                m = secret_name.match(line)
                if m:
                    self.assertTrue(is_placeholder(m.group(2)), f"{path.name}: {m.group(1)}")
                if line.startswith("DATABASE_URL="):
                    value = line[len("DATABASE_URL=") :]
                    self.assertTrue("REPLACE" in value or "$" in value, path.name)

    def test_no_real_ip_addresses(self):
        ipv4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
        allowed = {"127.0.0.1", "0.0.0.0"}  # noqa: S104
        for path in _secret_scan_paths():
            for match in ipv4.findall(_read(path)):
                self.assertIn(match, allowed, f"{path.name}: {match}")


class RunbookTests(SimpleTestCase):
    def test_swap_check_before_packages(self):
        text = _read(DEPLOY_MD)
        self.assertLess(text.index("swapon --show"), text.index("apt -y install"))

    def test_no_swap_creation(self):
        text = _read(DEPLOY_MD)
        for fragment in ("fallocate", "mkswap", "/etc/fstab", "vm.swappiness"):
            self.assertNotIn(fragment, text, fragment)

    def test_steps_numbered_consecutively(self):
        numbers = re.findall(r"^## (\d+)\. ", _read(DEPLOY_MD), re.MULTILINE)
        self.assertEqual(numbers, [str(i) for i in range(len(numbers))])

    def test_step_references(self):
        text = _read(DEPLOY_MD)
        titles = dict(re.findall(r"^## (\d+)\. (.+)$", text, re.MULTILINE))
        references = (
            (text, r"until step (\d+) is verified", "SSH: keys only"),
            (text, r"until step (\d+) \(SSH hardening\)", "SSH: keys only"),
            (text, r"right after step (\d+), once the repo", "App user, directories, code"),
            (text, r"already exists from step (\d+)\)", "PostgreSQL (trial database)"),
            (text, r"Repeat\s+step (\d+) \(without seeding\)", "Smoke check"),
            (text, r"repeat the smoke check \(step (\d+)\)", "Smoke check"),
            (
                _read(NGINX_BOOTSTRAP),
                r"docs/DEPLOY\.md step (\d+)\)",
                "nginx bootstrap + certificate",
            ),
        )
        for source, pattern, title in references:
            match = re.search(pattern, source)
            self.assertIsNotNone(match, pattern)
            self.assertEqual(titles.get(match.group(1)), title, pattern)

    def test_required_topics(self):
        text = _read(DEPLOY_MD)
        for topic in (
            "swapon --show",
            "ufw",
            "certbot certonly --webroot",
            "certbot renew --dry-run",
            "chmod 600",
            "token_urlsafe",
            "openssl rand -hex 24",
            "check --deploy",
            "collectstatic",
            "seed_demo",
            "2026-11-22",
            "deanery_trial",
            "free -h",
            "df -h",
            "journalctl --disk-usage",
            "SECURE_HSTS_SECONDS=31536000",
            "PasswordAuthentication",
        ):
            self.assertIn(topic, text, topic)

    def test_service_account_nologin(self):
        # TASK-016 (PT1-F6): no login shell and no SSH key for the service account.
        text = _read(DEPLOY_MD)
        self.assertIn('--shell /usr/sbin/nologin "$APP_USER"', text)
        self.assertNotIn("--shell /bin/bash", text)
        self.assertNotIn('ssh-copy-id "$APP_USER"', text)
        self.assertIn('sudo usermod --shell /usr/sbin/nologin "$APP_USER"', text)

    def test_certificate_for_www(self):
        self.assertIn('-d "$DOMAIN" -d "www.$DOMAIN"', _read(DEPLOY_MD))

    def test_demo_password_removed_after_seed(self):
        text = _read(DEPLOY_MD)
        section = text[text.index("## 16. ") : text.index("## 17. ")]
        removal = "sudo sed -i '/^DEMO_PASSWORD=/d' /etc/deanery/deanery.env"
        self.assertIn(removal, section)
        self.assertLess(section.index("$M seed_demo"), section.index(removal))
        self.assertLess(section.index(removal), section.index("sudo systemctl restart deanery"))
        # The app itself never reads DEMO_PASSWORD.
        self.assertNotIn("DEMO_PASSWORD", _read(BASE_DIR / "config" / "settings.py"))

    def test_no_daily_seed_cron(self):
        for line in _read(DEPLOY_MD).splitlines():
            if "cron" in line:
                self.assertNotIn("seed_demo", line)

    def test_env_file_sed_produces_trial_env(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash not available")
        doc = _read(DEPLOY_MD)
        for expr in ENV_FILE_SED_EXPRS:
            self.assertIn(expr, doc, f"missing sed rule: {expr}")
        sed_args = " ".join(f'-e "{expr}"' for expr in ENV_FILE_SED_EXPRS)
        script = (
            'export DOMAIN="deanery.example.org"; '
            'export SECRET="dummy-secret-value"; '
            'export DB_PASS="dummy-db-pass"; '
            'export ADMIN_PATH="staff-dummy1234/"; '
            'export DEMO_PW="dummy-demo-pass"; '
            f"sed {sed_args} {shlex.quote(str(ENV_EXAMPLE))}"
        )
        result = subprocess.run(  # noqa: S603
            [bash, "-c", script], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        values = _parse_env(result.stdout)
        self.assertEqual(
            values["DATABASE_URL"], "postgres://deanery:dummy-db-pass@localhost:5432/deanery_trial"
        )
        self.assertEqual(values["PRIVATE_MEDIA_ROOT"], "/srv/deanery/private_media_trial")
        self.assertEqual(values["ALLOWED_HOSTS"], "deanery.example.org")
        for value in values.values():
            self.assertNotIn("REPLACE", value)
            self.assertNotIn("replace-me", value)
            self.assertNotIn("change-me", value)

    def test_no_relative_deploy_paths(self):
        for line in _read(DEPLOY_MD).splitlines():
            stripped = line.strip()
            self.assertFalse(
                stripped.startswith("sudo install -m 644 deploy/"), f"relative path: {stripped}"
            )
            if stripped.startswith("sed "):
                self.assertNotIn(" deploy/", stripped, f"relative path: {stripped}")


class OldServerLimitsTests(SimpleTestCase):
    """TASK-015: the server has 2 vCPU, ~2 GB RAM, a 20 GB disk and a provider swap."""

    FORBIDDEN = ("1 GB", "1 vCPU", "10 GB", "swapfile", "50-deanery.conf", "SystemMaxUse")

    def test_no_old_server_values(self):
        for path in _secret_scan_paths():
            text = _read(path)
            for fragment in self.FORBIDDEN:
                self.assertNotIn(fragment, text, f"{path.name}: {fragment}")

    def test_no_shared_buffers_warning(self):
        self.assertNotIn("shared_buffers", _read(DEPLOY_MD))

    def test_journald_override_removed(self):
        self.assertFalse((DEPLOY_DIR / "journald").exists())

    def test_resources_section(self):
        text = _read(DEPLOY_MD)
        section = text[text.index("## 19. Resources") : text.index("## 20. Troubleshooting")]
        for fragment in ("GUNICORN_WORKERS=5", "min(5, 13)", "512 MB", "20 GB", "10%"):
            self.assertIn(fragment, section, fragment)


class BackupScriptRunTests(SimpleTestCase):
    """TASK-016: run backup.sh with a stub pg_dump; the password never reaches the command line."""

    PASSWORD = "0123abcd4567ef89dummydbpass"

    def test_password_not_on_command_line(self):
        bash = shutil.which("bash")
        if bash is None or shutil.which("tar") is None or shutil.which("gzip") is None:
            self.skipTest("bash, tar or gzip not available")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            (root / "media" / "private_media").mkdir(parents=True)
            (root / "media" / "private_media" / "a.pdf").write_bytes(b"%PDF-1.4")
            stub = root / "bin" / "pg_dump"
            stub.write_text(
                "#!/usr/bin/env bash\n"
                f'printf "%s\\n" "$@" > "{root}/args"\n'
                f'env | grep -E "^PG(USER|PASSWORD|HOST|PORT|DATABASE)=" | sort > "{root}/pgenv"\n'
                f'env | grep -c "^DATABASE_URL=" > "{root}/dburl" || true\n'
                'echo "-- dump"\n',
                encoding="utf-8",
            )
            stub.chmod(0o755)
            env_file = root / "deanery.env"
            env_file.write_text(
                f"DATABASE_URL=postgres://deanery:{self.PASSWORD}@localhost:5432/deanery_trial\n"
                f"PRIVATE_MEDIA_ROOT={root}/media/private_media\n",
                encoding="utf-8",
            )
            env = {
                "PATH": f"{root / 'bin'}{os.pathsep}{os.environ['PATH']}",
                "BACKUP_DIR": str(root / "backups"),
                "DEANERY_ENV_FILE": str(env_file),
            }
            result = subprocess.run(  # noqa: S603
                [bash, str(BACKUP_SH)], env=env, capture_output=True, text=True, timeout=60
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("backup ok:", result.stdout)
            args = (root / "args").read_text(encoding="utf-8")
            self.assertNotIn(self.PASSWORD, args)
            self.assertEqual(args.split(), ["--no-owner", "--no-privileges"])
            self.assertEqual(
                (root / "pgenv").read_text(encoding="utf-8").split(),
                [
                    "PGDATABASE=deanery_trial",
                    "PGHOST=localhost",
                    f"PGPASSWORD={self.PASSWORD}",
                    "PGPORT=5432",
                    "PGUSER=deanery",
                ],
            )
            self.assertEqual((root / "dburl").read_text(encoding="utf-8").strip(), "0")
            names = sorted(p.name for p in (root / "backups").iterdir())
            self.assertEqual(len(names), 2)
            self.assertTrue(names[0].startswith("db-") and names[0].endswith(".sql.gz"))
            self.assertTrue(names[1].startswith("media-") and names[1].endswith(".tar.gz"))

    def test_bad_database_url_fails(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash not available")
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "deanery.env"
            env_file.write_text("DATABASE_URL=sqlite:///db.sqlite3\n", encoding="utf-8")
            env = {
                "PATH": os.environ["PATH"],
                "BACKUP_DIR": str(Path(tmp) / "backups"),
                "DEANERY_ENV_FILE": str(env_file),
            }
            result = subprocess.run(  # noqa: S603
                [bash, str(BACKUP_SH)], env=env, capture_output=True, text=True, timeout=60
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("DATABASE_URL must look like", result.stderr)
            self.assertFalse((Path(tmp) / "backups").exists())


class CiDependencyAuditTests(SimpleTestCase):
    """TASK-016: pip-audit runs in CI in its own step; it is not a runtime dependency."""

    def test_audit_step(self):
        import yaml

        ci = yaml.safe_load(_read(BASE_DIR / ".github" / "workflows" / "ci.yml"))
        steps = {step.get("name"): step for step in ci["jobs"]["test"]["steps"]}
        run = steps["Dependency audit"]["run"]
        self.assertIn("pip install pip-audit==2.10.1", run)
        self.assertIn("pip-audit --requirement requirements.txt", run)
        self.assertNotIn("pip-audit", _read(BASE_DIR / "requirements.txt"))
