# TASK-019: nginx catch-all 443 closes, backup.sh without exported secrets and partial files, scan skips git-ignored files

Author: Planner. Assignee: Coder. Status: ready for implementation.
Base: HEAD 32ba5fc (the touched files are the same as in 5df4eae). Do not touch `plan.md` or `docs/REPORT.md`.

## 1. Goal and acceptance criteria

Three small, independent items: PT3-F7 and PT3-F6 from `docs/security/PENTEST-3.md`, and a test-environment
problem found during TASK-018.

| ID | Criterion |
|---|---|
| AC1 | `deploy/nginx/deanery.conf`: the catch-all `443 default_server` block ends with `return 444;` (like the port-80 catch-all). Both catch-all blocks have `server_name _;` and `return 444;`. |
| AC2 | `deploy/backup.sh` exports nothing from the env file: `gzip`, `tar` and `find` get no `SECRET_KEY`, `DEMO_PASSWORD`, `DATABASE_URL`, `PRIVATE_MEDIA_ROOT` and no `PG*`; `pg_dump` gets only the five `PG*` values (no other env-file value). |
| AC3 | `backup.sh` writes `db-*.sql.gz` and `media-*.tar.gz` as `*.part` in the same directory and renames them only after success; on failure the `.part` file is removed, no `backup ok` line, non-zero exit, old backups are not deleted. |
| AC4 | Existing behaviour stays: password never on the command line, works from any directory (`cd /`), `KEEP_DAYS` cleanup, messages, exit codes; `bash -n` passes. A missing `PRIVATE_MEDIA_ROOT` now fails before the dump (exit 1, message without values). |
| AC5 | The deploy file scans (`_secret_scan_paths`) skip files that git ignores (`.DS_Store`, `__pycache__`, `*.pyc`), still scan tracked and new untracked files, and a project binary file still fails loudly (`UnicodeDecodeError`). |
| AC6 | All verification commands pass. |

## 2. Out of scope

PT3-F6 item 3 (percent-encoded password; the runbook generates hex passwords), PT3-F7 items 2–3 (IPv6 /64
limits, a global login zone, `limit_conn 40`), `docs/DEPLOY.md` (commands do not change; `*.part` files never
stay), any Django code.

## 3. Design decisions

- **D1. Env file read in a subshell.** `env_value NAME` sources the env file inside `( ... )` and prints one
  value. The parsing is the same as before (`.` like `manage.sh`, quotes work), but `SECRET_KEY` and the
  other values never reach the main shell, and nothing is exported. The values live in lower-case shell
  variables (`db_url`, `media_root`, `pg_*`), so they cannot collide with inherited exported upper-case
  names. `unset DATABASE_URL` is no longer needed.
- **D2. `PG*` as a prefix of `pg_dump` only** (`PGUSER=… PGPASSWORD=… pg_dump …`): the values are in the
  environment of `pg_dump` alone (not `export`), not on its command line (PT1-F13 stays: arguments are only
  `--no-owner --no-privileges`).
- **D3. `*.part` + `trap … EXIT`.** `set -euo pipefail` stops at the failing step; the `EXIT` trap removes
  `"$db_file.part" "$media_file.part"` (no-op after a successful `mv`). The exit code is the failing command's;
  the trap does not change it. The `find` cleanup patterns (`db-*.sql.gz`, `media-*.tar.gz`) never match
  `*.part`, and cleanup runs only after both archives succeeded (old backups survive a failed run).
- **D4. `PRIVATE_MEDIA_ROOT` check** right after the URL check: before, a missing value failed at `tar`
  (unbound variable) after the dump was written. The URL check stays first, so `test_bad_database_url_fails`
  is unchanged.
- **D5. Scan list from git.** In a checkout, `git ls-files -z --cached --others --exclude-standard -- deploy`
  lists tracked files plus untracked files that are not ignored — exactly ".gitignore minus junk", and a new
  uncommitted deploy file (the Coder's work) is still scanned. Without `.git` (a `git archive` copy, used by
  the Pentester and the Planner) the fallback is `rglob` minus `.DS_Store`, `__pycache__`, `*.pyc`. A git
  error raises (`check=True`), so the scan never becomes silently empty. Listed binary files keep failing in
  `_read` with `UnicodeDecodeError`.

## 4. Files and functions

Change: `deploy/nginx/deanery.conf`, `deploy/backup.sh` (keep it executable: edit in place), `core/tests/test_deploy.py`.
Diffs are against HEAD; edit by hand, no git commands.

### F1. `deploy/nginx/deanery.conf`

````diff
--- a/deploy/nginx/deanery.conf
+++ b/deploy/nginx/deanery.conf
@@ -26,6 +26,8 @@
     server_name _;
     server_tokens off;
     ssl_reject_handshake on;
+    # SNI = the domain with a foreign Host header still lands here: close it too (PT3-F7).
+    return 444;
 }
 
 # HTTP for the domain and www: ACME challenges, everything else to the HTTPS domain.
````

### F2. `deploy/backup.sh` (whole file)

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

# One value of the env file, read in a subshell: the other values (SECRET_KEY, ...) never
# reach this shell, and nothing from the file is exported to the children (PT3-F6).
env_value() {
    (
        set +u
        . "$ENV_FILE" > /dev/null
        printf '%s' "${!1-}"
    )
}
db_url="$(env_value DATABASE_URL)"
media_root="$(env_value PRIVATE_MEDIA_ROOT)"

DB_URL_RE='^postgres(ql)?://([^:/@]+):([^@]+)@([^:/@]+):([0-9]+)/([^/?]+)$'
if [[ ! "$db_url" =~ $DB_URL_RE ]]; then
    echo "backup failed: DATABASE_URL must look like postgres://user:password@host:port/name" >&2
    exit 1
fi
pg_user="${BASH_REMATCH[2]}"
pg_password="${BASH_REMATCH[3]}"
pg_host="${BASH_REMATCH[4]}"
pg_port="${BASH_REMATCH[5]}"
pg_database="${BASH_REMATCH[6]}"
if [[ -z "$media_root" ]]; then
    echo "backup failed: PRIVATE_MEDIA_ROOT is not set in the env file" >&2
    exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
db_file="$BACKUP_DIR/db-$STAMP.sql.gz"
media_file="$BACKUP_DIR/media-$STAMP.tar.gz"
mkdir -p "$BACKUP_DIR"
# Write to *.part and rename only after success; a failed step leaves no partial file (PT3-F6).
trap 'rm -f -- "$db_file.part" "$media_file.part"' EXIT
# The PG* values go to pg_dump only, through the libpq environment, never on the command line
# (PT1-F13); gzip, tar and find do not get them.
PGUSER="$pg_user" PGPASSWORD="$pg_password" PGHOST="$pg_host" PGPORT="$pg_port" \
    PGDATABASE="$pg_database" pg_dump --no-owner --no-privileges | gzip -9 > "$db_file.part"
mv -- "$db_file.part" "$db_file"
tar -czf "$media_file.part" -C "$(dirname "$media_root")" "$(basename "$media_root")"
mv -- "$media_file.part" "$media_file"
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'media-*.tar.gz' \) -mtime +"$((KEEP_DAYS - 1))" -delete
echo "backup ok: $STAMP"
````

### F3. `core/tests/test_deploy.py`

New: `_server_blocks`, `NginxTemplateTests::test_every_catch_all_server_closes_connection`,
`ShellScriptTests::test_backup_exports_nothing_from_env_file`, `_repo_files` (used by `_secret_scan_paths`),
class `ScanFileListTests` (4 tests), class `BackupScriptEnvironmentTests` (4 tests). Changed:
`test_catch_all_servers` (`return 444;` twice), `test_backup_runs_from_root_directory` (the `pg_dump` line now
starts with the `PG*` prefix; comment lines are skipped).

````diff
--- a/core/tests/test_deploy.py
+++ b/core/tests/test_deploy.py
@@ -83,6 +83,23 @@
         self.assertEqual(self._load_config()["bind"], "127.0.0.1:8000")
 
 
+def _server_blocks(text: str) -> list[str]:
+    """Bodies of the top-level ``server { ... }`` blocks (brace matching, comments removed)."""
+    text = re.sub(r"#[^\n]*", "", text)
+    blocks = []
+    for match in re.finditer(r"^server\s*\{", text, flags=re.M):
+        depth = 0
+        for i in range(match.end() - 1, len(text)):
+            if text[i] == "{":
+                depth += 1
+            elif text[i] == "}":
+                depth -= 1
+                if depth == 0:
+                    blocks.append(text[match.end() : i])
+                    break
+    return blocks
+
+
 class NginxTemplateTests(SimpleTestCase):
     def test_full_config_body_size(self):
         text = _read(NGINX_CONF)
@@ -123,14 +140,24 @@
         for line in (
             "listen 80 default_server;",
             "listen [::]:80 default_server;",
-            "return 444;",
             "listen 443 ssl http2 default_server;",
             "listen [::]:443 ssl http2 default_server;",
             "ssl_reject_handshake on;",
         ):
             self.assertEqual(text.count(line), 1, line)
         self.assertEqual(text.count("server_name _;"), 2)
+        self.assertEqual(text.count("return 444;"), 2)
 
+    def test_every_catch_all_server_closes_connection(self):
+        # TASK-019 (PT3-F7): SNI = the domain with a foreign Host reaches the 443 catch-all.
+        blocks = [b for b in _server_blocks(_read(NGINX_CONF)) if "default_server" in b]
+        self.assertEqual(len(blocks), 2)
+        for block in blocks:
+            with self.subTest(block=block.split(";")[0]):
+                self.assertIn("server_name _;", block)
+                self.assertIn("return 444;", block)
+                self.assertNotIn("proxy_pass", block)
+
     def test_www_redirect_and_acme(self):
         text = _read(NGINX_CONF)
         self.assertIn("server_name example.com www.example.com;", text)
@@ -377,26 +404,126 @@
         lines = [line.strip() for line in _read(BACKUP_SH).splitlines()]
         self.assertIn("cd /", lines)
         cd_index = lines.index("cd /")
-        for command in ("pg_dump", "tar -czf", "find "):
-            first = next(i for i, line in enumerate(lines) if line.startswith(command))
+        commands = [(i, line) for i, line in enumerate(lines) if line and not line.startswith("#")]
+        for command in ("pg_dump ", "tar -czf", "find "):
+            first = next(i for i, line in commands if command in line)
             self.assertLess(cd_index, first, command)
 
+    def test_backup_exports_nothing_from_env_file(self):
+        # TASK-019 (PT3-F6): no "set -a", no "export"; the PG* values are pg_dump's prefix.
+        backup = _read(BACKUP_SH)
+        self.assertNotIn("set -a", backup)
+        self.assertIsNone(re.search(r"^\s*export\b", backup, flags=re.M))
+        self.assertIn('PGPASSWORD="$pg_password"', backup)
+
     def test_manage_uses_env_file(self):
         manage = _read(MANAGE_SH)
         self.assertIn(". /etc/deanery/deanery.env", manage)
         self.assertIn("set -euo pipefail", manage)
+
+
+def _repo_files(repo: Path, subdir: str) -> list[Path]:
+    """Files under ``repo/subdir`` that belong to the project (TASK-019).
+
+    In a git checkout: the tracked files plus the untracked files git does not ignore
+    (``git ls-files --cached --others --exclude-standard``), so a Finder ``.DS_Store`` or a
+    ``__pycache__`` is skipped while a new, not yet committed file is still scanned. Without a
+    checkout (a ``git archive`` copy): every file except ``.DS_Store``, ``__pycache__`` and
+    ``*.pyc``. Listed files are read as UTF-8, so a project binary file fails loudly.
+    """
+    git = shutil.which("git")
+    if git is not None and (repo / ".git").exists():
+        result = subprocess.run(  # noqa: S603
+            [git, "-C", str(repo), "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
+            + ["--", subdir],
+            capture_output=True,
+            check=True,
+        )
+        names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
+        return sorted(path for path in (repo / name for name in names) if path.is_file())
+    return sorted(
+        path
+        for path in (repo / subdir).rglob("*")
+        if path.is_file()
+        and "__pycache__" not in path.parts
+        and path.suffix != ".pyc"
+        and path.name != ".DS_Store"
+    )
 
 
 def _secret_scan_paths() -> list[Path]:
-    paths = [
-        p
-        for p in DEPLOY_DIR.rglob("*")
-        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
-    ]
+    paths = _repo_files(BASE_DIR, "deploy")
     paths.extend([ENV_EXAMPLE, DEPLOY_MD])
     return paths
+
+
+class ScanFileListTests(SimpleTestCase):
+    """TASK-019: OS junk next to the deploy files does not break the scans; project files count."""
+
+    def _tree(self, root: Path) -> None:
+        (root / ".gitignore").write_text(".DS_Store\n__pycache__/\n*.pyc\n", encoding="utf-8")
+        deploy = root / "deploy"
+        (deploy / "nginx").mkdir(parents=True)
+        (deploy / "__pycache__").mkdir()
+        (deploy / "a.conf").write_text("server {}\n", encoding="utf-8")
+        (deploy / "blob.bin").write_bytes(b"\xff\xfe\x00binary")
+
+    def _junk_and_new_file(self, root: Path) -> None:
+        deploy = root / "deploy"
+        (deploy / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1\xff")
+        (deploy / "nginx" / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1\xff")
+        (deploy / "__pycache__" / "x.cpython-312.pyc").write_bytes(b"\xff\x00")
+        (deploy / "new.sh").write_text("echo new\n", encoding="utf-8")
+
+    def _names(self, root: Path) -> list[str]:
+        return [path.relative_to(root).as_posix() for path in _repo_files(root, "deploy")]
+
+    def test_git_checkout_skips_ignored_files(self):
+        git = shutil.which("git")
+        if git is None:
+            self.skipTest("git not available")
+        with tempfile.TemporaryDirectory() as tmp:
+            root = Path(tmp)
+            self._tree(root)
+            for args in (["init", "-q"], ["add", ".gitignore", "deploy/a.conf", "deploy/blob.bin"]):
+                subprocess.run([git, "-C", str(root), *args], check=True)  # noqa: S603
+            self._junk_and_new_file(root)
+            self.assertEqual(
+                self._names(root), ["deploy/a.conf", "deploy/blob.bin", "deploy/new.sh"]
+            )
+
+    def test_archive_copy_skips_os_junk(self):
+        with tempfile.TemporaryDirectory() as tmp:
+            root = Path(tmp)
+            self._tree(root)
+            self._junk_and_new_file(root)
+            self.assertEqual(
+                self._names(root), ["deploy/a.conf", "deploy/blob.bin", "deploy/new.sh"]
+            )
+
+    def test_project_binary_fails_loudly(self):
+        with tempfile.TemporaryDirectory() as tmp:
+            root = Path(tmp)
+            self._tree(root)
+            blob = next(p for p in _repo_files(root, "deploy") if p.name == "blob.bin")
+            with self.assertRaises(UnicodeDecodeError):
+                _read(blob)
 
+    def test_real_scan_covers_deploy_files(self):
+        names = {path.relative_to(BASE_DIR).as_posix() for path in _secret_scan_paths()}
+        for name in (
+            "deploy/backup.sh",
+            "deploy/manage.sh",
+            "deploy/gunicorn.conf.py",
+            "deploy/nginx/deanery.conf",
+            "deploy/systemd/deanery.service",
+            ".env.production.example",
+            "docs/DEPLOY.md",
+        ):
+            self.assertIn(name, names)
+        self.assertFalse(any("__pycache__" in name or name.endswith(".DS_Store") for name in names))
 
+
 class SecretScanTests(SimpleTestCase):
     def test_no_private_keys_or_known_tokens(self):
         patterns = (
@@ -675,8 +802,117 @@
             self.assertNotEqual(result.returncode, 0)
             self.assertIn("DATABASE_URL must look like", result.stderr)
             self.assertFalse((Path(tmp) / "backups").exists())
+
+
+class BackupScriptEnvironmentTests(SimpleTestCase):
+    """TASK-019 (PT3-F6): children get no env-file values; a failed step leaves no partial file."""
+
+    PASSWORD = "0123abcd4567ef89dummydbpass"
+    SECRET = "dummy-secret-key-for-backup-env-test"
+    DEMO = "dummy-demo-password-for-backup-test"
+    ENV_FILE_NAMES = ("SECRET_KEY", "DEMO_PASSWORD", "DATABASE_URL", "PRIVATE_MEDIA_ROOT")
+    PG_NAMES = ("PGUSER", "PGPASSWORD", "PGHOST", "PGPORT", "PGDATABASE")
+
+    def setUp(self):
+        self.bash = shutil.which("bash")
+        self.real = {name: shutil.which(name) for name in ("gzip", "tar", "find")}
+        if self.bash is None or None in self.real.values():
+            self.skipTest("bash, gzip, tar or find not available")
+        self.root = Path(tempfile.mkdtemp())
+        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
+        (self.root / "bin").mkdir()
+        (self.root / "media" / "private_media").mkdir(parents=True)
+        (self.root / "media" / "private_media" / "a.pdf").write_bytes(b"%PDF-1.4")
+        self.backups = self.root / "backups"
+        self.backups.mkdir()
+        # An old backup: a failed run must not delete it.
+        self.old = self.backups / "db-20200101-000000.sql.gz"
+        self.old.write_bytes(b"old")
+        os.utime(self.old, (0, 0))
+        self.pg_dump('echo "-- dump"')
+        for name, real in self.real.items():
+            self._stub(name, f'env > "{self.root}/env-{name}"\nexec "{real}" "$@"')
 
+    def _stub(self, name: str, body: str) -> None:
+        stub = self.root / "bin" / name
+        stub.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
+        stub.chmod(0o755)
 
+    def pg_dump(self, body: str) -> None:
+        self._stub("pg_dump", f'env > "{self.root}/env-pg_dump"\n{body}')
+
+    def run_backup(self, media_line: bool = True) -> subprocess.CompletedProcess:
+        lines = [
+            f"SECRET_KEY={self.SECRET}",
+            f"DATABASE_URL=postgres://deanery:{self.PASSWORD}@localhost:5432/deanery_trial",
+            f"DEMO_PASSWORD={self.DEMO}",
+        ]
+        if media_line:
+            lines.append(f"PRIVATE_MEDIA_ROOT={self.root}/media/private_media")
+        env_file = self.root / "deanery.env"
+        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
+        env = {
+            "PATH": f"{self.root / 'bin'}{os.pathsep}{os.environ['PATH']}",
+            "BACKUP_DIR": str(self.backups),
+            "DEANERY_ENV_FILE": str(env_file),
+        }
+        return subprocess.run(  # noqa: S603
+            [self.bash, str(BACKUP_SH)], env=env, capture_output=True, text=True, timeout=60
+        )
+
+    def child_env(self, name: str) -> dict[str, str]:
+        text = (self.root / f"env-{name}").read_text(encoding="utf-8")
+        return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
+
+    def names(self) -> list[str]:
+        return sorted(path.name for path in self.backups.iterdir())
+
+    def test_children_get_no_env_file_values(self):
+        result = self.run_backup()
+        self.assertEqual(result.returncode, 0, result.stderr)
+        pg_env = self.child_env("pg_dump")
+        self.assertEqual(pg_env["PGPASSWORD"], self.PASSWORD)
+        self.assertEqual(pg_env["PGDATABASE"], "deanery_trial")
+        for name in ("gzip", "tar", "find"):
+            env = self.child_env(name)
+            for variable in self.ENV_FILE_NAMES + self.PG_NAMES:
+                with self.subTest(child=name, variable=variable):
+                    self.assertNotIn(variable, env)
+        for variable in self.ENV_FILE_NAMES:
+            with self.subTest(child="pg_dump", variable=variable):
+                self.assertNotIn(variable, pg_env)
+        for name in ("pg_dump", "gzip", "tar", "find"):
+            text = (self.root / f"env-{name}").read_text(encoding="utf-8")
+            self.assertNotIn(self.SECRET, text)
+            self.assertNotIn(self.DEMO, text)
+        self.assertEqual(len(self.names()), 2)  # the old backup was removed by KEEP_DAYS
+
+    def test_failed_pg_dump_leaves_no_dump(self):
+        self.pg_dump('echo "-- partial"\nexit 3')
+        result = self.run_backup()
+        self.assertNotEqual(result.returncode, 0)
+        self.assertNotIn("backup ok", result.stdout)
+        self.assertEqual(self.names(), [self.old.name])
+
+    def test_failed_tar_leaves_no_media_archive(self):
+        self._stub("tar", 'printf partial > "$2"\nexit 2')
+        result = self.run_backup()
+        self.assertNotEqual(result.returncode, 0)
+        self.assertNotIn("backup ok", result.stdout)
+        names = self.names()
+        self.assertEqual(len(names), 2, names)
+        self.assertEqual(names[0], self.old.name)
+        self.assertTrue(names[1].startswith("db-") and names[1].endswith(".sql.gz"), names)
+        self.assertFalse(any(name.endswith(".part") for name in names))
+
+    def test_missing_media_root_fails_before_dump(self):
+        result = self.run_backup(media_line=False)
+        self.assertEqual(result.returncode, 1)
+        self.assertIn("PRIVATE_MEDIA_ROOT is not set", result.stderr)
+        self.assertEqual(self.names(), [self.old.name])
+        self.assertFalse((self.root / "env-pg_dump").exists())
+
+
 class CiDependencyAuditTests(SimpleTestCase):
     """TASK-016: pip-audit runs in CI in its own step; it is not a runtime dependency."""
 
````

## 5. Feasibility check

1. **Full change applied** (copy `$TMPDIR/t019`): `manage.py test --parallel` → `Ran 1255 tests … OK`
   (`$TMPDIR/test-t019-full-20261122-012140.log`, 12:22 MSK 22.11); `--parallel 2` → 1255 OK
   (`$TMPDIR/test-t019-p2-20261122-012231.log`, 12:23 MSK). `ruff check .`, `ruff format --check .` clean;
   `bash -n deploy/backup.sh` OK; `makemigrations --check` → No changes; `check` → no issues.
2. **New tests on HEAD** (`$TMPDIR/test-t019-newtests-on-head-20261122-012035.log`): 7 tests fail as expected
   (34 failures with subtests): `test_catch_all_servers`, `test_every_catch_all_server_closes_connection` (443
   block), `test_backup_exports_nothing_from_env_file`, and all 4 `BackupScriptEnvironmentTests` (HEAD gives
   `SECRET_KEY`, `DEMO_PASSWORD`, `PRIVATE_MEDIA_ROOT` and `PG*` to `gzip`/`tar`/`find`, leaves a partial dump).
3. **`.DS_Store` reproduced**: HEAD copy + `deploy/.DS_Store` → 5 errors (`SecretScanTests` ×4,
   `OldServerLimitsTests::test_no_old_server_values`, `UnicodeDecodeError`). Changed copy + `.DS_Store` in
   `deploy/` and `deploy/nginx/` → 66 deploy tests OK (fallback path).
4. **Git path** (a `git clone` of the repository in `$TMPDIR`, changes copied in): `.DS_Store` skipped, an
   untracked new `deploy/new-untracked.sh` listed, deploy tests OK; a tracked (`git add`) binary
   `deploy/blob.bin` → the scan tests error with `UnicodeDecodeError` (loud).
5. **Mutations**: removing the `trap` line fails `test_failed_pg_dump_leaves_no_dump` and
   `test_failed_tar_leaves_no_media_archive`; adding `export PGPASSWORD=…` fails
   `test_backup_exports_nothing_from_env_file` and `test_children_get_no_env_file_values` (gzip, tar, find).
6. **Shell**: bash 3.2 (macOS) runs every test; the constructs (`${!1-}`, `[[ =~ ]]`, `BASH_REMATCH`, prefix
   assignments, `trap … EXIT`, `mv --`) are the same in bash 5 (server). nginx is not installed locally:
   `return 444;` after `ssl_reject_handshake on;` in a `server` block is valid (both are server-level
   directives); the Team lead runs `nginx -t` on install.
7. **Safety**: no `.env` read; env files in tests are dummy values in temporary directories; the project tree
   was not modified.

## 6. Test plan

| AC | Tests (`core/tests/test_deploy.py`) |
|---|---|
| AC1 | `NginxTemplateTests::test_catch_all_servers` (changed), `::test_every_catch_all_server_closes_connection` |
| AC2 | `BackupScriptEnvironmentTests::test_children_get_no_env_file_values`; `ShellScriptTests::test_backup_exports_nothing_from_env_file` |
| AC3 | `BackupScriptEnvironmentTests::test_failed_pg_dump_leaves_no_dump`, `::test_failed_tar_leaves_no_media_archive` |
| AC4 | `BackupScriptRunTests::test_password_not_on_command_line`, `::test_bad_database_url_fails` (unchanged); `ShellScriptTests::test_bash_syntax`, `::test_scripts_executable`, `::test_backup_rules` (unchanged), `::test_backup_runs_from_root_directory` (changed); `BackupScriptEnvironmentTests::test_missing_media_root_fails_before_dump`; KEEP_DAYS cleanup: `test_children_get_no_env_file_values` (the 2020 backup is deleted after success) |
| AC5 | `ScanFileListTests::test_git_checkout_skips_ignored_files`, `::test_archive_copy_skips_os_junk`, `::test_project_binary_fails_loudly`, `::test_real_scan_covers_deploy_files`; `SecretScanTests` and `OldServerLimitsTests` (unchanged, now via `_repo_files`) |

Test count: 1245 → 1255 (+10).

## 7. Verification (Coder, then Reviewer)

```bash
.venv/bin/python manage.py test --parallel 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/python manage.py test --parallel 2 2>&1 | tee "$TMPDIR/test-p2-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/ruff check . && .venv/bin/ruff format --check .
bash -n deploy/backup.sh && test -x deploy/backup.sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
git status --short
```

If a `--parallel` run ends with `TypeError: cannot pickle 'traceback' object`, a test failed: run
`manage.py test core.tests.test_deploy` serially and report the test name. Report test counts, log paths and
Moscow times. Never read `.env`; do not touch `plan.md` or `docs/REPORT.md`.

## 8. Risks

- `env_value` sources the env file twice (it was sourced before too; the file is trusted).
- On the server, a stale `*.part` can only remain if the script is killed with SIGKILL; the next run ignores
  it and `find` never deletes it (pattern). Harmless; remove by hand if seen.
