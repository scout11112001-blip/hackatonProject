# Team protocol (applies to every agent in this project)

## Language
- Think and reason in English.
- Write every message to another agent in English.
- Write every message to the user in Russian: short sentences, result first, active voice.
- Write code, comments, commit messages and task specs (`docs/tasks/*`) in English.

## Stack
- Python 3 + Django. Follow Django conventions: one responsibility per app, models + migrations, forms/serializers for input validation, `settings` values from environment variables, tests with Django's test framework (or pytest-django if the project configures it).
- Do not add new frameworks or major dependencies unless the task spec explicitly allows it.

## Team
| Role | Thread | Provider | Role file |
|---|---|---|---|
| Team lead | thr_4izdzwetb4 | Claude Code | `.bb/roles/lead.md` |
| Planner | thr_2imsg4kck2 | Claude Code | `.claude/agents/planner.md` |
| Coder | thr_ng6cbgatm6 | opencode (DeepSeek) | `.opencode/agent/coder.md` |
| Reviewer | thr_cpuae9aqw3 | Claude Code | `.claude/agents/reviewer.md` |
| UI coder | thr_pgcwc2dwnn | Claude Code (Opus) | `.claude/agents/ui-coder.md` |

## Workflow
```
user <-> Team lead -> Planner -> Coder / UI coder <-> Reviewer -> Team lead -> user
```
1. The Team lead sends a request to the Planner ONLY after explicit user approval. Each request has an ID `TASK-NNN`. A fix task for the small defects of a finished task has the ID `TASK-NNN-FIX` (then `TASK-NNN-FIX2`, ...) and its spec is `docs/tasks/TASK-NNN-FIX.md`.
2. The Planner writes `docs/tasks/TASK-NNN.md` and hands it to the assignee named in the request: the Coder (default: logic, models, views, tests) or the UI coder (request line "Assignee: UI coder": visual design, templates, CSS, static assets). Below, "the Coder" means the assignee of the task.
3. The Coder implements the spec and sends a report to the Reviewer.
4. The Reviewer returns `CHANGES REQUESTED` to the coder who sent the report, or sends `APPROVE` to the Team lead.
5. The Coder may ask the Planner to clarify the spec. The Coder never changes the architecture on its own.
6. The Reviewer NEVER messages the Planner and never tells the Planner what to do. If a problem is in the spec or the architecture, the Reviewer reports it to the Team lead. The Team lead decides.
7. If the spec lacks necessary tests, the Reviewer sends a `TEST PROPOSAL` to the Team lead. If the Team lead accepts it, the Team lead sends a spec amendment to the Planner, and the task goes through the Coder and the Reviewer again.
8. Maximum 3 review rounds per task. After the 3rd `CHANGES REQUESTED`, the Reviewer escalates to the Team lead instead.
9. If an agent is blocked (missing info, unclear requirement, failing environment), it reports to the Team lead, not to the user.
10. If the user writes to you directly, answer in Russian and follow the user's instructions.

## Git and commits
- Only the Team lead commits. The Planner, the Coder, the UI coder and the Reviewer NEVER run `git commit`, `git push`, `git stash`, `git checkout`, `git reset` or any other command that changes git history or the index.
- The Coder leaves all changes uncommitted. The Reviewer reviews the uncommitted changes (`git status`, `git diff`, and untracked files).
- After `APPROVE`, the Team lead commits the task as one commit `TASK-NNN: <summary>` and updates `CHANGELOG.md`.

## Messaging
- Send messages with `bb thread tell <thread-id> --message-file - <<'EOF' ... EOF` (one message per command).
- First line of every message: `[TASK-NNN] <FROM> -> <TO>: <TYPE>` where TYPE is one of `TASK`, `QUESTION`, `ANSWER`, `REPORT`, `CHANGES REQUESTED`, `APPROVE`, `ESCALATION`, `TEST PROPOSAL`.
- Reference files by path; do not paste whole files.
- Never send acknowledgements or thanks. Do not wait for a reply to a message that asks for nothing.
- Messages from other agents start with `[bb message from thread:<id>]`. Act on them according to your role.

## Test runs
- Always save the full output of every test run to a file, e.g. `python manage.py test 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log"`.
- If any run fails, even once and even if a re-run passes, report the failing test name(s), the time of the run (Moscow time) and the relevant part of the traceback to the Team lead (Coder: in the REPORT; Reviewer: in the verdict message). Never dismiss a failure as flaky without the test name.

## Safety
- Never read, print or send the contents of `.env` or any secret.
- Never run destructive commands (`rm -rf`, `git reset --hard`, dropping databases) without explicit Team lead approval.
