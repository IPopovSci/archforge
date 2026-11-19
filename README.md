# Archforge

Archforge is the architecture harness developed in this repository: the Python CLI and stdio MCP server share the same compiler, Trail query adapter and routing rules. OpenCode and Codex can work on the same Git history and exchange the same compiled contract digest. The headless poison fixture is a repeatable acceptance case. The Lines design bible supplies an example of a binding document that deserves FULL review.

## Documentation

Documentation is layered, and each layer has one writer: binding intent lives in `AGENTS.md` and `docs/documentation-charter.md`; contracts live in `tickets/` and `tach.toml`; the observed layer is generated into `docs/usage/catalog.md` (`python scripts/doc_catalog.py render`) and never hand-written; code is the point of truth. `python scripts/doc_catalog.py check` fails on a stale generated catalog or on a documentation pointer that no longer resolves. Compiled verification runs the documentation gate by default: every FULL contract check list includes it, so documentation rot cannot pass through a merge.

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

From the repository root, start Codex with the project MCP server:

```powershell
.\.venv\Scripts\python scripts/codex_project.py
```

To start the installed OpenCode 2.x client, run `python scripts/opencode_project.py` in the activated environment. Both launchers select the native client for child tasks. Ask either client to call `route_task` on `README.md`. A working connection returns `FAST` from `rules-v1`. Both clients also have access to the Python CLI.

## Using another client

Any client with shell access can run the daily workflow below. For a client with stdio MCP support, configure the absolute project Python executable as its command, the absolute path to `server.py` as its argument, and the checkout root as its working directory. Give it the repository's `AGENTS.md` instructions. This also works for clients that use a different project instruction filename. Verification runs through the Python CLI in the trusted checkout.

To hand work between clients, share the baseline revision, compiled digest, candidate checkout and requirement receipt. Each client should run verification from the checkout holding the compiled artifact. On another machine, transfer the approved contract to `.harness/compiled/<digest>.json` along with the Git revisions and receipt.

Automated model delegation is optional. A new native client can publish a Python entry point in the `architecture_harness.clients` group under its client name. The entry point loads an adapter object with `model(role) -> str` and `run(role, model, prompt, cwd, schema) -> (session_id, answer, usage_events)`. The adapter owns authentication, pinned model selection, starting a fresh read-only session, and checking native completion. The shared launcher validates structured answers, rejects reused session IDs and applies scoped edits. Install the adapter in the project environment and select it with `--client <name>`. Use one explicitly selected client per task.

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

Run `python scripts/live_fixture.py` from a clean checkout to exercise the selected client as architect, engineer and reviewer. See the [setup checklist](docs/usage/checklist.md) and [first-run findings](docs/usage/research-results.md).

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

## Native client roles

OpenCode Go users can connect their subscription with `python scripts/opencode_project.py auth login`. The architect and reviewer default to GLM-5.3 and the engineer to GLM-5.3-Flash. Configure the native agents and foreground model in `opencode.json`. The shared launcher reads the selected role from that file. A failed role ends the task on the selected client.

Run `python scripts/roles.py engineer HOST-EXAMPLE --client opencode --prompt "Summarize the supplied requirement ..."` for a fresh OpenCode session. Use `--client codex` for a fresh Codex thread. From a project-launched session, omit the flag to inherit the client. For the live fixture launched from a standalone PowerShell, set `$env:HARNESS_CLIENT = 'opencode'` or `'codex'` before running `python scripts/live_fixture.py`. Both paths use the same contract, evidence and verification code. Unattended OpenCode roles receive their source and evidence in the request. Use the bounded `--edit-file` path below for engineering writes. Interactive sessions retain native client permissions. If your native executable is outside PATH, set HARNESS_OPENCODE to its absolute executable path.

For Codex, use the same role launcher. Architect and reviewer use GPT-6.2 Astra. Engineer uses GPT-6.2 Sol. Every invocation starts a separate ephemeral Codex thread. Supply the request, compiler evidence or verified review bundle explicitly. Task IDs group receipts across calls without loading previous conversations.

```powershell
.\.venv\Scripts\python scripts/roles.py engineer TASK-123 --prompt "Inspect the off-by-one in fixture/turn_lifecycle.py"
```

Architect and reviewer calls are read-only. For direct Codex engineering edits, use `--write --worktree <linked-checkout>` and the normal scope and verification gates. The default runs read-only. Each receipt in .harness/roles records the requested model, task, working directory, native client and session ID, usage events and outcome. Use the interactive session for coordination. The role launcher owns model selection for delegated tasks.

On machines where unattended Codex shell tools cannot start, use the bounded STANDARD edit path. Supply an existing declared Python module, a clean linked worktree, and the task. Python gives a fresh read-only engineer process that file, validates the returned interface, applies the edit, and runs Tach and pytest. The edit receipt records the actual changed file and checks. A failing candidate stays in its worktree for inspection.

```powershell
.\.venv\Scripts\python scripts/roles.py engineer TASK-124 --worktree <linked-checkout> --edit-file fixture/combat.py --prompt "Preserve existing stacks when applying poison"
```

## Paired benchmark

`benchmarks/tasks.json` defines ten seeded engineering tasks across FAST, STANDARD, and FULL work. Each task has a fixed request, target file, Trail query, seeded defect, focused acceptance test, and command. `scripts/benchmark.py --dry-run` validates every seed in a disposable Git worktree without model calls:

```powershell
.\.venv\Scripts\python scripts/benchmark.py --dry-run
```

To compare a plain model prompt with a Trail-context prompt on the same task:

```powershell
.\.venv\Scripts\python scripts/benchmark.py --client codex --tasks docs-codex
```

Use `--client opencode` to run the same paired suite through the OpenCode adapter. Each run writes per-task client, model, session ID, timing, token totals, changed files, focused test result, and receipt to `.harness/benchmark/results/`.
