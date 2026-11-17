# Architecture harness

The Python CLI and stdio MCP server share the same compiler, Trail query adapter and routing rules. OpenCode and Codex can work on the same Git history and exchange the same compiled contract digest. The headless poison fixture is a repeatable acceptance case. The Lines design bible supplies an example of a binding document that deserves FULL review.

## Windows setup

From the repository root with Python 3.14 x64 and Git installed:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
. .\scripts\activate.ps1
npm.exe ci
python -m pytest -q
tach check
```

Codex is the active client. From the repository root, start a session with the project MCP server:

```powershell
.\.venv\Scripts\python scripts/codex_project.py
```

Ask Codex to call `route_task` on `README.md`. A working connection returns `FAST` from `rules-v1`. The launcher passes this project's server configuration for that session. The Python CLI also works in an existing Codex session. OpenCode is an optional adapter for a future switch.

## Daily workflow

```powershell
python harness.py route README.md
python harness.py route fixture/combat.py
python harness.py route project_example/lines-master-design-bible.md
python harness.py catalog
python harness.py context "poison damage"
python harness.py schema
python harness.py compile tickets/FEAT-042.json
python scripts/demo.py
```

FAST records a diff. STANDARD retrieves a bounded context, then runs focused pytest and Tach. Capture the starting commit before edits and run `python harness.py recheck <starting-commit>` before finishing. Consider the union of the initial profile, new information and actual changes. A public contract change always needs FULL review.

For FULL, start from a clean committed tree. Give the architect the catalog and ticket schema, resolve unknowns, compile the approved intent and retain the returned digest. `tach.toml` is the sole source of module dependency policy. The compiler checks its modules against the fresh Trail graph. Have the engineer describe intended changes and review any material delta before creating an attempt with `git worktree add --detach <path> <compiled-revision>`. Commit the candidate in that worktree. Run the verifier from the original checkout:

```powershell
python harness.py verify <contract-digest> <attempt-directory> examples/receipt.json
```

Review requirements against the tests and implementation diff at the reported candidate revision. Passing tests establish that linked examples ran. Human or model judgment still determines whether they cover the intent. Keep the compiler checkout, approved digest and test environment under reviewer control. Use the demo to replay a baseline failure, passing implementation, forbidden import and scope failure. Every replay retains a separate local worktree and evidence under .harness/runs. Only the revision in review.json is the passing candidate.

Run `python scripts/live_fixture.py` from a clean checkout to exercise Codex as architect, engineer and reviewer using your ChatGPT subscription. See the [setup checklist](docs/usage/checklist.md) and [first-run findings](docs/usage/research-results.md).
