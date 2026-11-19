# TASK-015: deploy files for the new server (2 vCPU, ~2 GB RAM, 20 GB disk)

Author: Planner. Assignee: Coder. Status: ready for implementation.
Base: HEAD afed2a1 (clean tree; `plan.md` is the Team lead's file, do not touch it).

## 1. Goal

TASK-011 prepared the deploy for a small server (1 vCPU, 1 GB RAM, 10 GB disk). On 2026-11-19 the user moved to
another hosting: Ubuntu 24.04.4, 2 vCPU, 1.9 GB RAM, 20 GB disk, a 512 MB swap created by the provider
(swappiness 60). Remove the optimizations made for the old small server. **Documentation, deploy templates and
their tests only. No application code changes.**

### Acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | `docs/DEPLOY.md` header describes the new server: 2 vCPU, ~2 GB RAM, 20 GB disk, 512 MB swap from the provider. |
| AC2 | Step "1. Swap first (1 GB RAM)" is replaced by "1. Memory and swap check" with the one-line check `swapon --show && free -h`. The runbook never creates or resizes swap (no `fallocate`, `mkswap`, `/etc/fstab`, `vm.swappiness`). The check stays before `apt -y install`. |
| AC3 | `deploy/gunicorn.conf.py`: default workers 5, docstring with the formula result; env override `GUNICORN_WORKERS` kept. `.env.production.example`: comment updated, `GUNICORN_WORKERS=5`. |
| AC4 | The journald override is removed: file `deploy/journald/50-deanery.conf` and the directory `deploy/journald/` are deleted; the runbook step "6. journald limit" is deleted; the test that read the file is deleted. systemd defaults apply. The nginx logrotate sentence moves to "Resources". |
| AC5 | The PostgreSQL warning "do not raise `shared_buffers`, keep `max_connections`" is deleted. No tuning step is added. |
| AC6 | Steps are renumbered 0..20 with no gap; every cross-reference ("step N") points to the correct step, also the comment in `deploy/nginx/deanery-bootstrap.conf`. |
| AC7 | Section "Resources" (now step 19) is recalculated for 5 workers on ~2 GB / 20 GB (exact text in F1.9). |
| AC8 | Everything else is unchanged: backups (`KEEP_DAYS` 7), nginx templates (except the one comment in AC6), systemd unit, SSH hardening, firewall, HTTPS, HSTS, CI. |
| AC9 | `grep -rnE "1 GB\|1 vCPU\|10 GB\|swapfile\|50-deanery\.conf" docs/DEPLOY.md deploy/ .env.production.example --exclude-dir=__pycache__` prints nothing. |
| AC10 | Tests updated (section 7); full suite OK; ruff check and format check OK; `bash -n` and `gunicorn --check-config` OK. |

## 2. Out of scope

- Application code, settings, migrations, templates, static files.
- `CHANGELOG.md`, `plan.md`, `README.md` (README has no server sizes; the Team lead updates CHANGELOG), old specs in
  `docs/tasks/` (history, never edit them).
- `.github/workflows/ci.yml` (it has no journald or worker-count references; verified).
- PostgreSQL tuning, swap tuning, nginx/systemd changes, backup retention.

## 3. Design decisions

- **D1. Step 1 stays a step.** The swap step becomes "1. Memory and swap check". So steps 0–5 keep their numbers and
  the two "step 4" references (SSH hardening) need no change. Only the removal of step 6 (journald) shifts steps
  7–21 to 6–20.
- **D2. The swap check does not name the swap file.** The provider created it; the runbook only checks
  `swapon --show && free -h`. The word "swapfile" must not appear (AC9).
- **D3. Workers = 5.** Formula already in the runbook: `min(2 × vCPU + 1, (free RAM MB − 300) / 90)` =
  `min(5, 13)` = 5 (Team lead's numbers). Measured on HEAD (section 5, item 6): one Django worker peaks at
  ≈ 58 MB RSS after loading every simple page as a student and as staff (macOS, SQLite); on Linux with psycopg
  the TASK-011 estimate of 60–90 MB per worker holds. The project has no `CONN_MAX_AGE`, so each request opens and
  closes its own PostgreSQL connection: at most 5 concurrent connections, far below the stock
  `max_connections = 100`.
- **D4. journald defaults.** With no override, journald uses `SystemMaxUse` = 10% of the file system (capped at
  4 GB) and `SystemKeepFree` = 15% (journald.conf(5)). On 20 GB that is ≈ 2 GB at most. Nothing to install.
- **D5. Delete, do not empty.** Delete `deploy/journald/50-deanery.conf` with `rm` and the empty directory with
  `rmdir` (no `-r`, no `-f`, no `git rm`: only the Team lead changes the index). Git will show the file as deleted.
- **D6. Test names without step numbers.** The constant `STEP10_SED_EXPRS` and the test
  `test_step10_sed_produces_trial_env` are renamed to `ENV_FILE_SED_EXPRS` and
  `test_env_file_sed_produces_trial_env`, because the "Environment file" step becomes step 9 and any future
  renumbering must not make a name wrong. The sed rules themselves do not change.
- **D7. Guard tests.** New tests check the step numbering and every cross-reference by the target step's title, so
  a wrong renumbering fails a test (section 7).

## 4. Files and functions

Change: `docs/DEPLOY.md`, `deploy/gunicorn.conf.py`, `.env.production.example`,
`deploy/nginx/deanery-bootstrap.conf` (one comment), `core/tests/test_deploy.py`.
Delete: `deploy/journald/50-deanery.conf`, then the empty directory `deploy/journald/`.

Every "old" text below is an exact, unique match in HEAD afed2a1 (checked by a script that asserted count == 1 for
each replacement).

### F1. `docs/DEPLOY.md`

F1.1 Header, lines 3–4. Old:

```
Production deployment of the Deanery prototype on Ubuntu 24.04 (1 vCPU, 1 GB
RAM, 10 GB disk), one domain with HTTPS, serving until 2026-11-28.
```

New:

```
Production deployment of the Deanery prototype on Ubuntu 24.04 (2 vCPU, ~2 GB
RAM, 20 GB disk, 512 MB swap from the provider), one domain with HTTPS, serving
until 2026-11-28.
```

F1.2 Step 1, lines 32–41. Replace the whole section `## 1. Swap first (1 GB RAM)` up to and including its code block
(ending with `free -h` and the closing fence) with:

````
## 1. Memory and swap check

The provider already created a 512 MB swap. Check that it is active; do not
create or resize swap.

```bash
swapon --show && free -h
```
````

F1.3 Step 4 text, line 65: `may be done right after step 7, once the repo is cloned.` →
`may be done right after step 6, once the repo is cloned.`

F1.4 Delete step 6 completely, lines 84–103: from `## 6. journald limit` through the line
`nginx logs are rotated by the stock `/etc/logrotate.d/nginx` — no action.` and the blank line after it (that
sentence moves to Resources in F1.9). After the deletion, `## 5. Firewall`'s code block is followed by one blank
line and `## 6. App user, directories, code`.

F1.5 PostgreSQL step (old 9), lines 124–126: delete the two lines

```
Keep PostgreSQL stock settings: do **not** raise `shared_buffers`, keep
`max_connections`.
```

and the blank line after them, so the heading `## 8. PostgreSQL (trial database)` is followed by one blank line and
the code block.

F1.6 Renumber headings: `## 7.` → `## 6.`, `## 8.` → `## 7.`, … `## 21.` → `## 20.` (15 headings). Result:

| New | Title |
|---|---|
| 0 | Before you start |
| 1 | Memory and swap check |
| 2 | Time zone |
| 3 | Packages |
| 4 | SSH: keys only |
| 5 | Firewall |
| 6 | App user, directories, code |
| 7 | Python venv |
| 8 | PostgreSQL (trial database) |
| 9 | Environment file |
| 10 | Django |
| 11 | gunicorn + systemd |
| 12 | nginx bootstrap + certificate |
| 13 | nginx full site |
| 14 | Backups |
| 15 | Smoke check |
| 16 | Final database on 2026-11-22 (once) |
| 17 | Update procedure |
| 18 | HSTS |
| 19 | Resources |
| 20 | Troubleshooting |

F1.7 Cross-references (all of them; there are no others):

| Line (HEAD) | Old | New |
|---|---|---|
| 8 | `until step 4 is verified` | unchanged |
| 30 | `until step 4 (SSH hardening)` | unchanged |
| 65 | `right after step 7` | `right after step 6` (F1.3) |
| 87 | `(step 7)` | deleted with step 6 (F1.4) |
| 239 | `already exists from step 9)` | `already exists from step 8)` |
| 261 | `step 16 (without seeding)` | `step 15 (without seeding)` |
| 275 | `Then repeat the smoke check (step 16).` | `Then repeat the smoke check (step 15).` |

F1.8 Steps 2–18 otherwise stay byte-identical (the env-file sed block, backups, HSTS, smoke check text).

F1.9 Resources (new step 19). Keep the heading `## 19. Resources`. Replace the whole body (old lines 294–307, from
`Expected memory:` through `` `GUNICORN_WORKERS` by the formula `min(2 × vCPU + 1, (free RAM MB − 300) / 90)`. ``)
with exactly:

````
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
````

The "≈" and "–" and "→" and "×" and "−" characters are the same Unicode characters the file already uses.
Note: "1.9 GB", "~2 GB", "≈ 2 GB" and "20 GB" do not contain the forbidden substring "1 GB" or "10 GB" (AC9).

### F2. `deploy/gunicorn.conf.py`

Docstring lines 3–4, old:

```
Workers: 2 for 1 vCPU / 1 GB RAM. Bigger server: min(2 * vCPU + 1, (free RAM MB - 300) // 90),
set GUNICORN_WORKERS in /etc/deanery/deanery.env.
```

New:

```
Workers: 5 for 2 vCPU / ~2 GB RAM: min(2 * vCPU + 1, (free RAM MB - 300) // 90) = min(5, 13).
Other server: set GUNICORN_WORKERS in /etc/deanery/deanery.env by the same formula.
```

Line 10: `os.environ.get("GUNICORN_WORKERS", "2")` → `os.environ.get("GUNICORN_WORKERS", "5")`. Keep `max(1, int(...))`.
Nothing else changes in this file.

### F3. `.env.production.example`

Lines 34–35, old:

```
# gunicorn (deploy/gunicorn.conf.py): 2 workers for 1 vCPU / 1 GB RAM.
GUNICORN_WORKERS=2
```

New:

```
# gunicorn (deploy/gunicorn.conf.py): 5 workers for 2 vCPU / ~2 GB RAM (docs/DEPLOY.md, Resources).
GUNICORN_WORKERS=5
```

### F4. `deploy/nginx/deanery-bootstrap.conf`

Line 1: `(docs/DEPLOY.md step 13)` → `(docs/DEPLOY.md step 12)`. Nothing else changes.

### F5. Delete the journald override

```bash
rm deploy/journald/50-deanery.conf
rmdir deploy/journald
```

### F6. `core/tests/test_deploy.py`

See section 7 for the full list. Exact edits:

1. Delete the line `JOURNALD = DEPLOY_DIR / "journald" / "50-deanery.conf"`.
2. Replace the comment and constant name:
   ```python
   # The sed `-e` rules of the "Environment file" step (docs/DEPLOY.md); kept here so the
   # test can run them.
   ENV_FILE_SED_EXPRS = (
   ```
   and rename both uses of `STEP10_SED_EXPRS` in `test_step10_sed_produces_trial_env`, which is renamed to
   `test_env_file_sed_produces_trial_env`. Its body is otherwise unchanged.
3. `GunicornConfigTests.test_defaults`:
   `self.assertEqual(cfg["workers"], 5)  # TASK-015: 2 vCPU / ~2 GB server` (was 2).
   `test_env_override` stays (`"3"` → 3 still differs from the default).
4. `EnvExampleTests.test_production_values`:
   `self.assertEqual(values["GUNICORN_WORKERS"], "5")  # TASK-015: 2 vCPU / ~2 GB server` (was "2").
5. Delete `SmallFilesTests.test_journald_limit` (the file no longer exists; reason: TASK-015 AC4).
6. In `RunbookTests` replace `test_swap_before_packages` with these four methods:
   ```python
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
   ```
7. `RunbookTests.test_required_topics`: remove `"vm.swappiness=10"`, `"SystemMaxUse"` and `"shared_buffers"`;
   add `"swapon --show"` in place of `"vm.swappiness=10"` (first item). All other topics stay.
8. Append a new class at the end of the file:
   ```python
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
   ```
   `_secret_scan_paths()` already covers every file under `deploy/` (without `__pycache__`), `.env.production.example`
   and `docs/DEPLOY.md`, so it is the exact AC9 scope.

Run `ruff format core/tests/test_deploy.py` (never on `docs/`), then `ruff check .`.

## 5. Feasibility check

1. **Baseline** — HEAD afed2a1, copy made with `git archive HEAD | tar -x -C $TMPDIR/t015` (no `.env`), DEBUG=true
   and a dummy SECRET_KEY: `manage.py test --parallel` → `Ran 1134 tests … OK`
   (`$TMPDIR/test-t015-head-20261119-142001.log`, 01:20 MSK 20.11). OK.
2. **Full change applied** — a second copy (`$TMPDIR/t015b`) with F1–F6 applied by a script that asserted each old
   text occurs exactly once: `Ran 1140 tests … OK` (`$TMPDIR/test-t015b-20261119-141904.log`, 01:19 MSK 20.11).
   +6 = 8 new − 2 removed (`test_journald_limit`, `test_swap_before_packages`). OK.
3. **New tests fail on HEAD** — the new `test_deploy.py` against the HEAD files: 7 failures + 2 errors, exactly the
   expected ones: `test_defaults`, `test_production_values`, `test_required_topics`, `test_no_swap_creation`,
   `test_no_old_server_values`, `test_no_shared_buffers_warning`, `test_journald_override_removed` (FAIL);
   `test_swap_check_before_packages`, `test_resources_section` (ERROR: substring not found). The two guard tests
   `test_steps_numbered_consecutively` and `test_step_references` pass on HEAD, as intended (the old numbering is
   consistent); they fail if the renumbering in F1.6/F1.7 is wrong
   (`$TMPDIR/test-t015-newtests-on-head-20261119-142156.log`). OK.
4. **Lint** — on the changed copy: `ruff format core/tests/test_deploy.py` reformatted the long tuple in
   `test_step_references` (the code in F6.6 is the formatted result); then `ruff check .` → All checks passed;
   `ruff format --check .` → 193 files already formatted. OK.
5. **Deploy commands** — on the changed copy: `bash -n deploy/backup.sh deploy/manage.sh` OK;
   `gunicorn --check-config -c deploy/gunicorn.conf.py config.wsgi:application` OK; `manage.py check` → no issues;
   `makemigrations --check --dry-run` → No changes detected. `check --deploy` with the example values runs inside
   `EnvExampleTests.test_deploy_check_passes_with_example_values` (passed in item 2). OK.
6. **Runtime: 5 workers** — gunicorn 26.2.0 from the project venv with the changed config and no
   `GUNICORN_WORKERS` in the environment booted exactly 5 workers ("Booting worker" ×5), `/health/` →
   `{"status": "ok"}`. Memory: one worker process (`get_wsgi_application()` + every simple GET page as `student1`
   and `staff1`, 15 rounds) peaked at 58 MB RSS (45 MB after loading). OK.
7. **AC9 grep** — on the changed copy the AC9 command prints nothing. Also `grep` over the whole repo (without
   `.venv`, `.git`, `docs/tasks`, `docs/process`) finds the journald file name only in `core/tests/test_deploy.py`
   (handled in F6.1/F6.5); CI (`.github/workflows/ci.yml`) has no journald reference. OK.
8. **Step references** — every "step N" in `docs/DEPLOY.md` and the one in `deploy/nginx/deanery-bootstrap.conf`
   is listed in F1.7/F4 (grep `step [0-9]` over the repo outside `.venv`/`.git`/old specs). OK.
9. **systemd defaults** — journald.conf(5): `SystemMaxUse=` defaults to 10% of the file system size, capped at 4G;
   `SystemKeepFree=` defaults to 15%, capped at 4G. Ubuntu 24.04 keeps a persistent journal in `/var/log/journal`.
   OK.
10. **Safety** — no application code, no migration, no settings change; `.env` was never read (the copies had no
    `.env`); the only deletion is one tracked file and its empty directory (F5), no `git` index command. The
    working tree of the project was not modified by this check. OK.

## 6. Implementation order

1. F1 `docs/DEPLOY.md` (F1.1 → F1.9, top to bottom).
2. F2, F3, F4.
3. F5 (delete the file and the directory).
4. F6 tests, `ruff format core/tests/test_deploy.py`.
5. Verification (section 8).

## 7. Test plan

### Traceability

| AC | Test (`core/tests/test_deploy.py`) |
|---|---|
| AC1 | `OldServerLimitsTests::test_no_old_server_values` (no "1 vCPU"/"1 GB"/"10 GB"), `test_resources_section` |
| AC2 | `RunbookTests::test_swap_check_before_packages`, `RunbookTests::test_no_swap_creation`, `RunbookTests::test_required_topics` (`swapon --show`), `OldServerLimitsTests::test_no_old_server_values` ("swapfile") |
| AC3 | `GunicornConfigTests::test_defaults` (5), `GunicornConfigTests::test_env_override` (unchanged), `GunicornConfigTests::test_workers_at_least_one` (unchanged), `EnvExampleTests::test_production_values` ("5") |
| AC4 | `OldServerLimitsTests::test_journald_override_removed`, `OldServerLimitsTests::test_no_old_server_values` ("50-deanery.conf", "SystemMaxUse") |
| AC5 | `OldServerLimitsTests::test_no_shared_buffers_warning` |
| AC6 | `RunbookTests::test_steps_numbered_consecutively`, `RunbookTests::test_step_references` |
| AC7 | `OldServerLimitsTests::test_resources_section` |
| AC8 | all existing tests in `test_deploy.py` unchanged (nginx, systemd, SSH, cron, backup `KEEP_DAYS:-7`, secret scan, `test_env_file_sed_produces_trial_env`, `test_no_relative_deploy_paths`, `test_deploy_check_passes_with_example_values`) |
| AC9 | `OldServerLimitsTests::test_no_old_server_values` + the grep in section 8 |
| AC10 | section 8 commands |

### Changed tests (with reason)

| Test | Change | Reason |
|---|---|---|
| `GunicornConfigTests::test_defaults` | workers 2 → 5 | AC3, new server |
| `EnvExampleTests::test_production_values` | `GUNICORN_WORKERS` "2" → "5" | AC3 |
| `SmallFilesTests::test_journald_limit` | deleted | AC4, file removed |
| `RunbookTests::test_swap_before_packages` | replaced by `test_swap_check_before_packages` | AC2, no swap creation |
| `RunbookTests::test_required_topics` | −`vm.swappiness=10`, −`SystemMaxUse`, −`shared_buffers`, +`swapon --show` | AC2, AC4, AC5 |
| `RunbookTests::test_step10_sed_produces_trial_env` | renamed to `test_env_file_sed_produces_trial_env`, constant `ENV_FILE_SED_EXPRS` | D6, step number changes |

### Edge cases

- Substring traps: "1.9 GB", "~2 GB", "≈ 2 GB", "20 GB" must not match "1 GB"/"10 GB" (checked: they do not).
- "Repeat step 15" is split over two lines in the runbook (`Repeat\nstep 15`): the regex uses `\s+`.
- `deploy/__pycache__/` exists locally and is ignored by git; `_secret_scan_paths()` skips it.
- The env override still works: `GUNICORN_WORKERS=3` → 3, `"0"` → 1.
- The settings branches (DEBUG true/false), query counts, access matrix: not applicable (no application code).

Test count: 1134 → 1140.

## 8. Verification (Coder, then Reviewer)

```bash
.venv/bin/python manage.py test --parallel 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/ruff check . && .venv/bin/ruff format --check .
bash -n deploy/backup.sh deploy/manage.sh
.venv/bin/gunicorn --check-config -c deploy/gunicorn.conf.py config.wsgi:application
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('CI YAML OK')"
grep -rnE "1 GB|1 vCPU|10 GB|swapfile|50-deanery\.conf" docs/DEPLOY.md deploy/ .env.production.example --exclude-dir=__pycache__ || echo GREP_CLEAN
grep -n "^## " docs/DEPLOY.md
git status --short
```

Expected: `Ran 1140 tests … OK`; ruff clean; `GREP_CLEAN`; headings 0..20 as in F1.6; `git status` shows
`M .env.production.example`, `M core/tests/test_deploy.py`, `D deploy/journald/50-deanery.conf`,
`M deploy/gunicorn.conf.py`, `M deploy/nginx/deanery-bootstrap.conf`, `M docs/DEPLOY.md`, the new
`docs/tasks/TASK-015.md`, and the Team lead's `M plan.md`. If PyYAML is not installed, skip the YAML line and say
so in the REPORT (CI YAML is not changed by this task). `check --deploy` with the example values is covered by
`test_deploy_check_passes_with_example_values`; do not create a `.env` and never read the existing one.

Report the test count, the log path and the Moscow time of the run. Report every failing run with the test name.

## 9. Risks

- **Wrong renumbering** → caught by `test_steps_numbered_consecutively` and `test_step_references`.
- **Memory estimate**: 5 workers ≈ 350–500 MB is an estimate (58 MB per worker measured on macOS); the runbook tells
  the operator how to lower `GUNICORN_WORKERS` if memory is short (F1.9).
- **Journal size**: up to ≈ 2 GB by systemd defaults, fits the 20 GB disk with room for backups.
- **Leftover empty directory** `deploy/journald/` locally → `test_journald_override_removed` fails; use `rmdir`.
