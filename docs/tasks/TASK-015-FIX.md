# TASK-015-FIX: demo idempotency test independent of parallel workers; backup script works from any directory

Author: Planner. Assignee: Coder. Status: ready for implementation.
Base: HEAD 915955f (clean tree except the Team lead's `plan.md`; do not touch it).

## 1. Goal

Two small defects found on 2026-11-20.

1. `petitions.tests.test_demo.PetitionsDemoTests.test_idempotent` fails sometimes under `--parallel`
   (`(8, 17, 2, 3, 124) != (8, 17, 2, 3, 127)`). `_count_files()` walks the whole private storage root. The test
   runner (TASK-013-FIX) gives all parallel workers one shared temporary root, so uploads from tests in other
   workers change the count between "before" and "after".
2. `deploy/backup.sh` started by hand with `sudo -u deanery …/backup.sh` from `/root` creates both backup files,
   then `find` fails ("Failed to restore initial working directory: /root: Permission denied") and the script
   exits non-zero (`set -e`). Cron is not affected.

### Acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | `test_idempotent` uses only the demo's own files: the sorted list of `PetitionAttachment.file` names, each of which exists in the private storage. Files of other tests in the shared root do not change the result. |
| AC2 | `test_idempotent` still proves that a second `seed_petitions_demo` run creates no new files: the storage `save` is spied during the second run and is never called; the file list is the same before and after (3 files); the four row counts are the same. |
| AC3 | `core/test_runner.py` is not changed. No other test counts files across the whole storage root (verified, section 5 item 7). |
| AC4 | `deploy/backup.sh` runs `cd /` right after `umask 077`, before any other work, with a one-line comment. Everything else in the script is byte-identical. |
| AC5 | The runbook's manual backup command in step 14 "Backups" (`sudo -u "$APP_USER" /srv/deanery/app/deploy/backup.sh`) stays unchanged and valid; `docs/DEPLOY.md` is not changed. |
| AC6 | A deploy test checks that `cd /` comes before `pg_dump`, `tar -czf` and `find`. `bash -n` stays green. |
| AC7 | Full suite OK; `manage.py test --parallel 2` three times, each OK, logs saved; ruff clean. |

## 2. Out of scope

- `core/test_runner.py` and the shared temporary root (per-worker roots are not needed).
- Any other line of `deploy/backup.sh` (`BACKUP_DIR`/`KEEP_DAYS` defaults, retention, names), the cron file,
  `docs/DEPLOY.md`, application code.
- Other tests in `petitions/tests/test_demo.py`.

## 3. Design decisions

- **D1. Demo files by reference, not by walk.** `_count_files()` is replaced by `_demo_files()`, which returns the
  sorted `PetitionAttachment.objects.values_list("file", flat=True)` list and asserts each name exists in the
  private storage. In `PetitionsDemoTests` all `PetitionAttachment` rows come from the demo (the test database is
  per worker, only the file root is shared), so this is exactly the demo's file set. Comparing the list (not only
  its length) also catches a re-seed that replaces a file.
- **D2. Spy on `storage.save` for "no new files".** The list alone cannot see an orphan file written without a
  row. `store_attachment` (`petitions/files.py:80–87`) writes every attachment with
  `get_private_storage().save(...)`, and `get_private_storage()` returns one module-level instance. So
  `mock.patch.object(storage, "save", wraps=storage.save)` around the second run, then `save.assert_not_called()`,
  proves no file is written by the re-seed, whatever other workers do (they are other processes with their own
  instance). Mutation check (section 5 item 4): if a demo petition is deleted before the re-seed, the spy records
  1 call.
- **D3. `cd /` at the start of `backup.sh`.** `find` saves and restores the start directory; when the app user
  cannot read it (`/root`), GNU find fails. `/` is readable by everyone. All paths in the script are absolute
  (`/etc/deanery/deanery.env`, default `BACKUP_DIR=/srv/deanery/backups`, `PRIVATE_MEDIA_ROOT` from the env file,
  `tar -C "$(dirname …)"`), so the change of directory changes nothing else. `cd "$BACKUP_DIR"` is not used:
  it would have to come after `mkdir -p` and would make a relative `BACKUP_DIR` wrong.
- **D4. Static test for the script.** The existing tests never execute `backup.sh` (it sources the fixed path
  `/etc/deanery/deanery.env` and needs `pg_dump`), so the new test checks the line order. The run itself was
  checked by hand (section 5 item 5).

## 4. Files and functions

Change: `petitions/tests/test_demo.py`, `deploy/backup.sh`, `core/tests/test_deploy.py`. Nothing else.
Every "old" text below is an exact, unique match in HEAD 915955f.

### F1. `petitions/tests/test_demo.py::PetitionsDemoTests._demo_files`

Replace the method `_count_files` (lines 35–40) with:

```python
    def _demo_files(self):
        # TASK-015-FIX: only the demo's own files. Parallel workers share one storage
        # root, so a walk over the whole root also counts other tests' uploads.
        storage = get_private_storage()
        names = sorted(PetitionAttachment.objects.values_list("file", flat=True))
        for name in names:
            self.assertTrue(storage.exists(name), name)
        return names
```

### F2. `petitions/tests/test_demo.py::PetitionsDemoTests.test_idempotent`

Replace the whole method (lines 106–122) with:

```python
    def test_idempotent(self):
        before = (
            Petition.objects.count(),
            PetitionStatusChange.objects.count(),
            PetitionComment.objects.count(),
            PetitionAttachment.objects.count(),
            self._demo_files(),
        )
        storage = get_private_storage()
        with mock.patch.object(storage, "save", wraps=storage.save) as save:
            seed_petitions_demo(D)
        after = (
            Petition.objects.count(),
            PetitionStatusChange.objects.count(),
            PetitionComment.objects.count(),
            PetitionAttachment.objects.count(),
            self._demo_files(),
        )
        self.assertEqual(before, after)
        self.assertEqual(len(before[-1]), 3)
        save.assert_not_called()
```

Imports stay as they are: `os` is still used by `test_command_output`; `mock` and `get_private_storage` are already
imported.

### F3. `deploy/backup.sh`

After line 4 `umask 077` insert two lines, so lines 3–6 read:

```bash
set -euo pipefail
umask 077
# Start from / so the script works from any directory (find restores the start directory).
cd /
```

No other change. The file mode stays 755 (edit in place; do not recreate the file).

### F4. `core/tests/test_deploy.py::ShellScriptTests.test_backup_runs_from_root_directory`

Insert this method in `ShellScriptTests`, directly before `test_manage_uses_env_file`:

```python
    def test_backup_runs_from_root_directory(self):
        # TASK-015-FIX: "sudo -u <APP_USER> backup.sh" from /root failed in find.
        lines = [line.strip() for line in _read(BACKUP_SH).splitlines()]
        self.assertIn("cd /", lines)
        cd_index = lines.index("cd /")
        for command in ("pg_dump", "tar -czf", "find "):
            first = next(i for i, line in enumerate(lines) if line.startswith(command))
            self.assertLess(cd_index, first, command)
```

`test_bash_syntax`, `test_scripts_executable` and `test_backup_rules` stay unchanged and must pass.

## 5. Feasibility check

1. **Baseline** — HEAD 915955f = TASK-015 (1140 tests OK, as reported for TASK-015). After this fix: 1141 (+1,
   F4; F1/F2 replace code inside an existing test).
2. **Change applied** — a copy of HEAD (`git archive HEAD | tar -x -C $TMPDIR/t015fixc`, no `.env`) with F1–F4
   applied by a script that asserted each old text occurs exactly once. `ruff check .` → All checks passed;
   `ruff format --check .` → 193 files already formatted; `bash -n deploy/backup.sh deploy/manage.sh` OK.
3. **Three `--parallel 2` runs** on the changed copy (DEBUG=true, dummy SECRET_KEY): each `Ran 1141 tests … OK`.
   Logs: `$TMPDIR/test-t015fix-p2-run1-20261119-144549.log` (01:47 MSK 20.11), `…-run2-20261119-144708.log`
   (01:48), `…-run3-20261119-144826.log` (01:49). No failure.
4. **The defect is reproduced and fixed deterministically** — a temporary subclass test (deleted afterwards)
   wrote one foreign PDF into the shared root with plain `open()` (like another worker) just before the second
   `seed_petitions_demo`. With the HEAD test: `AssertionError: Tuples differ: (8, 17, 2, 3, 3) != (8, 17, 2, 3, 4)`
   — the same failure as the Reviewer's. With F1/F2: OK. Mutation check of the spy: deleting one demo petition
   with a file before the re-seed → `save` called once (the spy works on the module-level storage instance).
5. **Backup script from an unreadable directory** — a copy of `backup.sh` with the env-file path pointed at a
   temporary env file and a stub `pg_dump`, started from a directory with mode 111 (enter but not read):
   HEAD version → both files created, then `find: -delete: forbidden when the current directory cannot be
   opened`, exit 1 (macOS BSD find; GNU find on the server gives the reported message, same cause). With F3 →
   `backup ok`, exit 0. Retention still works with F3: backup files dated 2026-11-01 were deleted, an unrelated
   `keep.txt` with the same date stayed.
6. **Script semantics** — every path in `backup.sh` is absolute (D3); the runbook command in step 14 calls the
   script by absolute path; cron calls it by absolute path. No change needed in `docs/DEPLOY.md` or the cron file.
7. **No other whole-root counters** — `grep` for `os.walk|rglob|listdir|scandir|glob(` and storage-root use in
   every test module: only `petitions/tests/test_demo.py::_count_files` walks the storage root.
   `petitions/tests/test_services.py:164` only checks a path prefix; `core/tests/test_storage.py` and
   `petitions/tests/test_downloads.py:172` check settings/paths, not counts. OK.
8. **Runner unchanged** — `core/test_runner.py` is not touched; `core/tests/test_storage.py::TestRunnerTests`
   passes in all three runs.
9. **No production code** — only two test files and one deploy script change; no migration; `manage.py check` and
   `makemigrations --check` are unaffected.
10. **Safety** — `.env` never read (the copy had none); no git index command; temporary files only under
    `$TMPDIR`; the project tree was not modified by this check.

## 6. Implementation order

1. F1, F2 (`petitions/tests/test_demo.py`).
2. F3 (`deploy/backup.sh`), F4 (`core/tests/test_deploy.py`).
3. `ruff format petitions/tests/test_demo.py core/tests/test_deploy.py` (never on `docs/`), `ruff check .`.
4. Verification (section 8).

## 7. Test plan

| AC | Test |
|---|---|
| AC1 | `petitions/tests/test_demo.py::PetitionsDemoTests::test_idempotent` (file list via `_demo_files`, each file exists) |
| AC2 | same test: equal tuples including the file list, `len == 3`, `save.assert_not_called()` |
| AC3 | review: `git diff --stat` shows no `core/test_runner.py`; `core/tests/test_storage.py::TestRunnerTests` unchanged and green |
| AC4 | `core/tests/test_deploy.py::ShellScriptTests::test_backup_runs_from_root_directory`, `ShellScriptTests::test_backup_rules` (unchanged fragments still present) |
| AC5 | `core/tests/test_deploy.py::RunbookTests` (unchanged, green); `git diff --stat` shows no `docs/DEPLOY.md` |
| AC6 | `ShellScriptTests::test_backup_runs_from_root_directory`, `ShellScriptTests::test_bash_syntax`, `ShellScriptTests::test_scripts_executable` |
| AC7 | section 8 |

Edge cases covered: a foreign file appears in the shared root during the test (D1, section 5 item 4); a re-seed
that writes an orphan file without a row (D2 spy); a re-seed that replaces a file (list comparison); the script
started from an unreadable directory (section 5 item 5). Access matrix, settings branches and query counts: not
applicable (tests and a shell script only).

Test count: 1140 → 1141.

## 8. Verification (Coder, then Reviewer)

```bash
for i in 1 2 3; do
  .venv/bin/python manage.py test --parallel 2 2>&1 | tee "$TMPDIR/test-p2-run$i-$(date +%Y%m%d-%H%M%S).log" | tail -3
done
.venv/bin/python manage.py test 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/ruff check . && .venv/bin/ruff format --check .
bash -n deploy/backup.sh deploy/manage.sh
.venv/bin/gunicorn --check-config -c deploy/gunicorn.conf.py config.wsgi:application
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
test -x deploy/backup.sh && echo EXEC_OK
git diff --stat
```

Expected: every run `Ran 1141 tests … OK`; ruff clean; `EXEC_OK`; `git diff --stat` lists only
`core/tests/test_deploy.py`, `deploy/backup.sh`, `petitions/tests/test_demo.py` (and the Team lead's `plan.md`),
plus the new `docs/tasks/TASK-015-FIX.md`. Report the log paths and the Moscow time of each run; report any
failure with the test name and a traceback excerpt, even if a re-run passes.

## 9. Risks

- **The spy depends on `store_attachment` using `get_private_storage()`** — true today (`petitions/files.py:80`).
  If the storage call ever changes, the mutation check in section 5 item 4 shows how to re-verify.
- **GNU vs BSD find messages differ**; the fix removes the cause (unreadable start directory) for both.
