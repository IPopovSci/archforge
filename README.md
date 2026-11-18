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

## Developing the harness itself

For an exact function name, use the Trail catalog. For a question phrased in terms of behavior, the optional local lookup can consume a saved Trail snapshot and rank its functions with MiniLM. From a clean project root:

```powershell
$lookup = 'scripts/shadow_decisions.py'
$mini = (Get-Item .harness/models/minilm-1110a243fdf4706b3f48f1d95db1a4f5529b4d41).FullName
.\.venv\Scripts\python $lookup --snapshot
.\.venv\Scripts\python $lookup --lookup diff_paths
.\.harness\decision-env\Scripts\python $lookup $mini --prepare-lookup
.\.harness\decision-env\Scripts\python $lookup $mini --lookup "Find edits someone made that Git is not tracking yet"
```

The four commands can run at different times. An exact match returns observed symbol references using the core environment. Behavioral lookup prepares any missing inputs on demand. A warm query reports `snapshot_reused` and `vectors_reused`, loads MiniLM in that process and encodes the question. Each result includes the Git revision, symbol, source span and a bounded excerpt. [Model setup and measurements](docs/usage/research-results.md#trail-and-embedding-retrieval)

Run `python harness.py context compile_ticket` to locate the compiler, or use `retrieve_context` from Codex. The catalog includes the compiler, MCP adapter, engineering scripts and synthetic simulation. FAST and STANDARD work can use the normal checkout. For FULL work, a linked Git worktree lets the reviewer run the trusted compiler against a committed candidate, including when the candidate changes the verifier. The installation and Git object database are shared.

For a reviewed boundary change, the reviewer supplies `python harness.py compile <ticket> --review <delta.json>` from the trusted checkout. Use `python harness.py schema` for the ReviewedDelta fields, `python harness.py ticket-digest <ticket>` for its ticket binding, and `git rev-parse HEAD` for the baseline. Use `api-digest <proposed-source>` for the approved public signature and SHA-256 of the exact proposed policy bytes for `file_digests`. A new module requires its proposed file and tach.toml in `extra_paths`. The acceptance test `test_self_hosted_contract` exercises the whole workflow, including approval of a new module and rejection of an extra policy edit.

The interface check covers statically declared functions, methods, classes and annotated public fields. Review behavior, runtime exports, decorators' actual effects and semantic changes in the diff. Reviewer-owned inputs and the verifier must run from a trusted checkout.

## Codex roles

Use the role launcher when assigning a new engineering task. Architect and reviewer use GPT-6.2 Astra. Engineer uses GPT-6.2 Sol. Every invocation starts a separate ephemeral Codex thread. Supply the request, compiler evidence or verified review bundle explicitly. Task IDs group receipts across calls without loading previous conversations.

```powershell
.\.venv\Scripts\python scripts/codex_role.py engineer TASK-123 --prompt "Inspect the off-by-one in fixture/turn_lifecycle.py"
```

Architect and reviewer calls are read-only. For engineering edits, use `--write --worktree <linked-checkout>` and the normal scope and verification gates. The default runs read-only. Each receipt in .harness/roles records the requested model, task, working directory, Codex thread ID, usage events and outcome. Use the interactive session for coordination. The role launcher owns model selection for delegated tasks.

On machines where unattended Codex shell tools cannot start, use the bounded STANDARD edit path. Supply an existing declared Python module, a clean linked worktree, and the task. Python gives a fresh read-only Sol process that file, validates the returned interface, applies the edit, and runs Tach and pytest. The edit receipt records the actual changed file and checks. A failing candidate stays in its worktree for inspection.

```powershell
.\.venv\Scripts\python scripts/codex_role.py engineer TASK-124 --worktree <linked-checkout> --edit-file fixture/combat.py --prompt "Preserve existing stacks when applying poison"
```
