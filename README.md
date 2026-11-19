# Archforge

Archforge is a verification and routing harness for AI-assisted software development: a deterministic Python layer that sits between your coding agent — OpenCode, Codex, or any client with a shell — and your Git repository. It answers the questions a raw agent session leaves open:

- **How much process does this change deserve?** Route every request to a FAST, STANDARD or FULL profile before any expensive model is involved.
- **What exactly was approved?** Compile approved intent into an immutable, versioned contract with requirement IDs, authorized scope and protected test obligations.
- **Can the result be proven without trusting the model?** Verify in an isolated Git worktree with deterministic checks — revision, scope, module policy, requirement-linked passing tests — and hand the reviewer compact evidence instead of a transcript.

The core principle: **models supply judgment and implementation; deterministic code retrieves, validates, records and enforces.** No acceptance decision depends on a model's self-report.

Archforge ships as a Python CLI (`harness.py`) and a stdio MCP server (`server.py`) that share the same compiler, Trail code-graph adapter and routing rules. OpenCode and Codex can therefore work on the same Git history and hand each other the same compiled contract digest. It self-hosts: the harness verifies changes to itself, and its acceptance tests cover the whole workflow, including rejection of unapproved public-API and policy edits.

## How a task flows

| Profile | Typical work | What happens | Large-model call |
|---|---|---|---|
| **FAST** | Typos, docs, formatting, low-impact files | Direct edit, scoped checks, reviewed diff | No |
| **STANDARD** | Contained bug fix or small feature | Bounded Trail context, focused pytest and Tach | No by default |
| **FULL** | Public contracts, new subsystems, architecture | Typed ticket → compiled contract → isolated attempt → verified evidence → review | Yes |

For FULL, the pipeline is:

1. An architect — a strong model or a human — authors a typed intent ticket against a small, generated capability catalog, never the whole repository. Requirement IDs and acceptance examples are fixed up front.
2. `python harness.py compile <ticket>` validates the ticket, checks its components against the fresh Trail graph, and emits an immutable compiled contract with authorized scope, protected obligations and a digest.
3. The engineer (a medium model, or you) implements in a detached Git worktree at the compiled revision. Material architecture deltas go back for approval before code proceeds.
4. `python harness.py verify <digest> <attempt> <receipt>`, run from the trusted checkout, checks Git scope and revision, Tach module policy, pytest status and requirement-linked passing tests, and emits a compact review bundle.
5. The reviewer approves against the verified evidence. The digest makes the entire run reproducible on any machine.

Every path rechecks the actual diff before finishing: a FAST task that starts touching executable code or a contract is promoted. A public contract change always needs FULL review.

## The tools underneath

You do not need to know these tools to use Archforge; this is what they are and how they interact.

| Tool | What it is | What it does here |
|---|---|---|
| **Tach** (pip, pinned in `requirements.lock`) | A module-boundary checker for Python. `tach.toml` is the single dependency policy: it declares every module and what each may import. | `tach check` fails on any undeclared import. Archforge also builds its capability catalog from the same policy, so ticket components are always real, policy-owned modules — and any boundary or policy edit routes to FULL. |
| **Trail** (`@trailhq/trail-code`, npm, pinned in `package.json`) | A code-graph search engine that indexes the repository into symbols and their relationships. | Archforge never hands a model the whole repository. `harness.py context <query>` returns a few bounded source excerpts with file-and-line pointers, and every compiled contract carries Trail evidence frozen at its baseline revision. A local patch (`scripts/patch_trail.mjs`, run by `npm ci`) keeps GDScript indexing working. |
| **pytest** (pip) | The standard Python test runner. | The deterministic test gate: FULL contracts demand requirement-linked passing acceptance tests, so a green suite is the proof, not a model's self-report. |
| **Pydantic** (pip) | Typed data models for Python. | The ticket, contract, receipt and catalog formats are typed and validated — malformed intent fails schema validation before any model call. |
| **MCP** (pip, `mcp` package) | Model Context Protocol — a stdio standard for connecting tools to agent clients. | `server.py` exposes the same operations as the CLI (route, compile, verify, …) so OpenCode and Codex drive the identical workflow through their MCP support. |
| **jsonschema** (pip) | JSON schema validation. | Validates structured worker answers during role delegation, such as the bounded engineer edit. |
| **opencode-ai** (npm) | The OpenCode agent client. | What the launchers and role delegation actually spawn for live architect/engineer/reviewer work. |

How they fit together: Tach defines the module world, Trail retrieves bounded evidence from it, Pydantic freezes approved intent into immutable contracts, and pytest plus the structural checks prove the result. The models only ever supply judgment and implementation. Python tools are pinned in `requirements.lock`, Node tools in `package.json`.

## Local decision models — advisors, not deciders

Routing has a deterministic floor: path rules, diff evidence and observed interface impact. On top of that sits a pluggable advisory seam where small local models can vote, and a model is consulted only when a request lands in the ambiguous STANDARD band:

- **Deem-4B** — a typed decision model that answers closed-menu questions with calibrated probabilities. On frozen routing suites it beat both the path rules alone and GLiNER, and it is the candidate for the ambiguous-band vote and capability ranking.
- **GLiNER2.5-Decide** — a fast zero-shot labeler. It lost the routing and capability-ranking comparisons, but tied Deem on evidence triage at a seventh of the latency and a fraction of the memory, making it the candidate for cheap, frequent binary gates.

Both stay optional: the workflow runs with no model installed, and default activation is gated on a larger frozen suite of real engineering requests (`tickets/FEAT-DECIDE-ADAPT-001.json`). Measured comparisons and reproduction commands are in [docs/usage/research-results.md](docs/usage/research-results.md).

Language tooling follows the same rule: it enters as pluggable adapters, never as core structure. The Godot boundary adapter is the first one — see [docs/usage/godot.md](docs/usage/godot.md).

## Repository layout

| Path | What it is |
|---|---|
| `harness.py` | The CLI: `route`, `assess`, `catalog`, `context`, `compile`, `verify`, `recheck`, `schema`, `ticket-digest`, `api-digest` |
| `server.py` | stdio MCP server exposing the same operations |
| `tickets/` | Versioned intent tickets; `python harness.py schema` prints the ticket format |
| `tach.toml` | The single source of module dependency policy |
| `fixture/` | Headless turn-based combat simulation; the seeded poison defect is the repeatable acceptance case |
| `project_example/first_person_dungeon_arpg_design.md` | Example binding document that deserves FULL review |
| `scripts/` | Client launchers, role delegation, benchmarks, documentation gates, offline model experiments |
| `benchmarks/tasks.json` | Ten seeded engineering tasks for paired model comparisons |
| `docs/` | Documentation charter and usage pages |
| `.harness/` | Local, untracked evidence: compiled contracts, run artifacts, decision logs, model checkpoints |

## Setup (Windows)

From the repository root with Python 3.14 x64 and Git installed:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
. .\scripts\activate.ps1
npm.exe ci
python -m pytest -q
tach check
```

Start Codex or the installed OpenCode 2.x client with the project MCP server:

```powershell
.\.venv\Scripts\python scripts/codex_project.py
.\.venv\Scripts\python scripts/opencode_project.py
```

Both launchers select the native client for child tasks. Ask either client to call `route_task` on `README.md` — a working connection returns `FAST` from `rules-v1`.

## Daily workflow

```powershell
python harness.py route README.md
python harness.py route fixture/combat.py
python harness.py route project_example/first_person_dungeon_arpg_design.md
python harness.py catalog
python harness.py context "poison damage"
python harness.py assess "poison damage" fixture/turn_lifecycle.py --base HEAD
python harness.py schema
python harness.py compile tickets/FEAT-042.json
python scripts/demo.py
```

FAST records a diff. STANDARD retrieves a bounded context, then runs focused pytest and Tach. Capture the starting commit before edits and run `python harness.py recheck <starting-commit>` before finishing. Assess a request before implementation with `python harness.py assess <request> <paths> [--base <rev>]`: the deterministic floor comes from path rules and observed interface impact, a decision provider votes only inside the ambiguous STANDARD band, and every assessment is recorded under `.harness`.

For FULL, start from a clean committed tree. Give the architect the catalog and ticket schema, resolve unknowns, compile the approved intent and retain the returned digest. Have the engineer describe intended changes and review any material delta before creating an attempt with `git worktree add --detach <path> <compiled-revision>`. Commit the candidate in that worktree, then run verification from the original checkout:

```powershell
python harness.py verify <contract-digest> <attempt-directory> examples/receipt.json
```

Passing tests establish that linked examples ran; human or model judgment still determines whether they cover the intent. Run `python scripts/demo.py` to replay a baseline failure, a passing implementation, a forbidden import and a scope failure. Run `python scripts/live_fixture.py` from a clean checkout to exercise the selected client as architect, engineer and reviewer. See the [setup checklist](docs/usage/checklist.md) and [first-run findings](docs/usage/research-results.md).

## Working with agent clients

Any client with shell access can run the daily workflow through the Python CLI. A client with stdio MCP support should use the project Python executable as its command, `server.py` as its argument, and the checkout root as its working directory. To hand work between clients or machines, share the baseline revision, the compiled digest (`.harness/compiled/<digest>.json`), the candidate checkout and the requirement receipt.

`scripts/roles.py` starts a fresh, ephemeral agent session per task. Architect and reviewer calls are read-only; the engineer can write through a bounded `--edit-file` path that validates the returned interface and runs Tach and pytest on a clean linked worktree:

```powershell
.\.venv\Scripts\python scripts/roles.py engineer TASK-123 --prompt "Inspect the off-by-one in fixture/turn_lifecycle.py"
```

OpenCode roles default to GLM-5.3 (architect, reviewer) and GLM-5.3-Flash (engineer); Codex roles pin Astra for architect and reviewer and Sol for engineering. Every receipt — model, task, session ID, usage, outcome — is recorded under `.harness/roles`.

## Developing Archforge itself

Use `python harness.py catalog` for exact symbol lookup, and `python harness.py context compile_ticket` to locate the compiler. FAST and STANDARD work can use the normal checkout; for FULL work a linked Git worktree lets the reviewer run the trusted compiler against a committed candidate, including when the candidate changes the verifier itself.

Boundary changes — a new module, a public signature, a dependency policy edit — go through a reviewed delta: the reviewer supplies `python harness.py compile <ticket> --review <delta.json>` from the trusted checkout. Use `python harness.py schema` for the ReviewedDelta fields, `python harness.py ticket-digest <ticket>` for the ticket binding, `git rev-parse HEAD` for the baseline and `python harness.py api-digest <proposed-source>` for the approved public signature. A new module requires its proposed file and tach.toml in `extra_paths`. The acceptance test `test_self_hosted_contract` exercises the whole workflow, including approval of a new module and rejection of an extra policy edit.

For questions phrased in terms of behavior rather than an exact name, an optional local lookup ranks a saved Trail snapshot with MiniLM. [Model setup and measurements](docs/usage/research-results.md#trail-and-embedding-retrieval)

## Paired benchmark

`benchmarks/tasks.json` seeds ten tasks across FAST, STANDARD and FULL work, each with a fixed request, seeded defect, focused acceptance test and command. Validate every seed without model calls:

```powershell
.\.venv\Scripts\python scripts/benchmark.py --dry-run
```

To compare a plain model prompt with a Trail-context prompt on the same tasks:

```powershell
.\.venv\Scripts\python scripts/benchmark.py --client codex --tasks docs-codex
```

Use `--client opencode` for the same suite through the OpenCode adapter. Each run records per-task client, model, session ID, timing, tokens, changed files, test results and receipts under `.harness/benchmark/results/`.

## Status and evidence

Archforge works on itself: its catalog covers the compiler, MCP adapter, engineering scripts and fixture, a forbidden compiler-to-server import fails Tach, and a public-signature change promotes a single-file diff to FULL. Open work is tracked in the [setup checklist](docs/usage/checklist.md):

- End-to-end FULL fixtures have passed live through the role launcher, with independent verification of every claim.
- Decision-model experiments (Deem-4B, GLiNER, offline embeddings) are measured and recorded, with default activation gated on a larger frozen suite rather than assumed.
- A ten-task paired benchmark completed on Codex; the OpenCode comparison is open.
- Framework evaluations (agent-spec, SIGIL) are recorded probes, not adopted dependencies.

All measured rows and reproduction commands live in [docs/usage/research-results.md](docs/usage/research-results.md).

## Documentation

Documentation is a four-layer system with one writer per layer; see [docs/documentation-charter.md](docs/documentation-charter.md). Binding intent lives in `AGENTS.md` and the charter; contracts live in `tickets/` and `tach.toml`; the observed catalog at [docs/usage/catalog.md](docs/usage/catalog.md) is generated (`python scripts/doc_catalog.py render`) and never hand-written; code is the point of truth. Compiled verification runs the documentation gate by default, so documentation rot cannot pass through a merge.
