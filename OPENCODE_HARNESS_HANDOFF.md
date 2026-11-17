# Schema-Driven, Decision-Assisted Coding Harness

**OpenCode implementation handoff — 15 November 2026**  
**Primary language:** Python · **LLM access:** ChatGPT subscription via OpenCode · **Interface:** OpenCode  
**Status:** architecture and implementation plan, not an already-working system

> **Instructions for the implementing OpenCode agent:** Read this document as the project brief. Start by inspecting the installed OpenCode version and its actual provider/plugin interfaces. Implement the first vertical slice before adding framework integrations. Preserve the model-independent schemas and decision-service abstraction. Do not claim a step or integration works without running it. At each milestone, produce a short receipt of what was installed, what ran, and what remains unresolved.

## 1. Objective and guiding idea

Build a **schema-driven development harness** for mostly Python-based, simulation-heavy games/projects. Complex features are designed with a strong OpenAI model and implemented with a smaller/medium OpenAI model; routine work must bypass the expensive ticket pipeline. A programmable middle layer will resolve the relevant code, architecture, tests, and work steps, using **small local decision models** for bounded choices whenever they can replace an otherwise unnecessary LLM reasoning/tool turn.

Optimization priorities, in order: **(1) correct and testable output; (2) fewer high-capability model calls and fewer tokens; (3) minimal context rot, redundant reading, and adherence failures; (4) faster end-to-end time.** Measure these rather than asserting savings. A ChatGPT subscription has usage limits; it is not interchangeable with OpenAI API credit. The initial design should not depend on separately billed APIs.

Core operating principle: **models supply judgment and implementation; schemas describe obligations; decision models choose among known actions; deterministic code retrieves, executes, validates, records and enforces.** The architecture/verification layer itself should have no generative-LLM dependency.

## 2. Intended flow

```text
REQUEST -> ROUTER (rules; optional local decision model)
   |-- FAST     -> direct edit -> lightweight checks -> diff -> done
   |-- STANDARD -> medium model + scoped Trail context -> Tach/pytest -> done
   `-- FULL
        |
        v
STRONG MODEL: brief prose + compact typed INTENT TICKET
        |   sees only a small generated capability/action catalog
        v
TASK COMPILER (Python/Pydantic) + DECISION SERVICE (local)
        |   validate/resolve capability IDs and references
        |   select bounded code evidence via Trail-code
        |   add compiler-owned checks, constraints and test obligations
        |   conflicting requirements -> short strong-model clarification
        v
COMPILED TASK (immutable revision + provenance + authorized scope)
        |
        v
MEDIUM MODEL: design implementation and propose architecture delta
        |   compiler validates structure and permitted scope
        |   material design change -> strong-model approval
        v
MEDIUM MODEL: implement within approved scope; emit change receipt
        |
        v
TACH + GRAPH CONFORMANCE + PYTEST + CONTRACT/PROPERTY TESTS
        |   structured diagnostics; bounded decision-directed repair
        v
COMPACT EVIDENCE -> STRONG MODEL: final intent/design review
        v
APPROVE / REVISE / MERGE + record evidence and telemetry

ALL PATHS: inspect actual changed files; promote if scope/impact grows.
```

**Cost control:** the strong model is **never a default prerequisite for small work**. On FULL tasks, it does *not* browse functions or design the routine implementation. It authors the feature intent/ticket and reviews material architectural changes and final evidence. The medium model writes algorithms and code. Decision models rank/choose **known** actions or context candidates; they are not asked to invent a whole new free-form specification. Deterministic obligations (e.g., “add acceptance tests”) never depend on classifier confidence.

### Task routing and lightweight bypass (required, not optional)

**Three execution profiles, chosen before any strong-model generation:**

| Profile | Typical work | Minimum process | Large-model call? |
|---|---|---|---|
| `FAST` | Typos, comments, README edits, formatting, low-impact generated files | Direct OpenCode edit; Git diff; narrowly scoped checks (if needed); short result | **No** |
| `STANDARD` | Localized bug, small contained feature, isolated refactor | Medium model + bounded Trail-code retrieval; focused pytest/Tach checks; change evidence | **No by default** |
| `FULL` | Cross-component feature, public-contract change, novel subsystem, architectural design | Typed strong-model ticket; task compilation; architecture review as required; full verification and final review | **Yes** |

Use **deterministic policy first** (paths affected, requested operation, known interfaces, task metadata). A local decision model may help choose among the three profiles when intent is ambiguous; it never overrides a mandatory promotion rule. The user can explicitly request a more thorough profile.

Classify **before** implementation and **recheck after** the actual diff or discovered impact. If a `FAST` task begins changing executable code or an architectural contract, **promote** it to `STANDARD` or `FULL` before completion. A docs-only ticket that changes externally binding specifications, architecture policies, or agent instructions may also warrant promotion despite the `.md` extension. A small code change can legitimately remain `STANDARD`; scope is more important than line count.

The router should not generate full tickets, manifests, execution bundles, or strong-model review requests for `FAST`. `STANDARD` may have an ephemeral minimal structured task (derived from the request) without persistent ticket proliferation. All paths preserve a clear diff and report actual checks. Test obligations and enforcement scale to the *impact*, not merely the request's wording.

**Example:** `Fix typo in README` -> `FAST` -> edit + diff; no tests, decision model, or architect. `Fix poison duration off-by-one` -> `STANDARD` -> locate affected symbols/tests via Trail-code -> medium-model fix -> pytest/Tach. `Introduce a new status-effect subsystem` -> `FULL` -> schema-first planning and architecture review.

## 3. The ticket-generation question — resolved design

**How can the strong model fill a schema without knowing which fields/actions/modules exist?** Give it a compact, generated **capability catalog** and a *fixed, versioned ticket schema*—not the whole repository. The catalog contains IDs, descriptions, allowed action types, relations, and relevant constraints. Generate it principally from **observed source structure** (Trail-code) plus a *minimal* versioned architecture policy; refresh automatically when the tree or policy changes. Never copy the source symbol inventory into a hand-maintained document. Supply only the relevant catalog slice (top-level capabilities plus candidates), not thousands of code symbols.

A good default is a **two-stage schema process**:

1. The strong model authors a concise prose statement and **minimal typed intent**: objective, requirement IDs, behavioral expectations, likely capability labels/IDs, constraints and acceptance examples. It does not invent function names or prescribe algorithms. Missing references may remain marked `unresolved` instead of being hallucinated.
2. Python validates and *compiles* that intent. Trail-code and generated catalog data resolve candidate IDs; explicit architectural policy fills in intent that code cannot infer. A local classifier/decision model ranks mappings among an allowed list. Deterministic policies fill protected fields such as `requires_tests`, `requires_tach_check`, `context_budget`, `must_review_arch_delta` and `allowed_operations`. If unresolved or contradictory, return a **short structured diagnostic** to the strong model; do not repeat the full design conversation.

A decision model such as GLiNER can classify a request into known capabilities/action categories. A Jev-style model can select a next action from a closed menu. Neither should be relied upon to freely generate an arbitrarily nested YAML/JSON document. Use the medium model for novel code-level solutions and the strong model only for genuinely novel design semantics.

## 4. Certain foundation: install and integrate these

| Tool | Why it is in the foundation | Concrete example / required proof |
|---|---|---|
| **OpenCode** | Main UI, subscription-authenticated OpenAI models, plugins/hooks, subagents and tool/API integration | Authenticate via `/connect` → OpenAI → **Sign in with ChatGPT**; select models with `/models`; demonstrate an interactive and a `opencode run` job |
| **Python 3 + Git** | Deterministic compiler, adapters, event log, worktree isolation, test harness | A task compiles into an immutable JSON artifact; attempt runs in a Git worktree |
| **Pydantic + JSON Schema** | Versioned typed input/output schemas; strict validation and generated catalogs | Reject nonexistent IDs, conflicting obligations and malformed receipts before invoking an LLM |
| **Trail-code (formerly Graft)** | Observed repository symbol/import/call graph; focused code queries; change-impact estimates | `trail build`, `trail ask "poison status effect" --json`, `trail skeleton ...`, `trail blast --format json` (use the installed version's syntax) |
| **Tach** | Enforce Python module dependencies and public interfaces against actual imports | `tach init`, then `tach check`; a forbidden import fails the build |
| **pytest** | Executable acceptance/regression checks, deterministic verification, structured diagnostics | `pytest -q`; verify a new poison stacking test and existing combat regression tests |
| **Local decision-service interface** | First-class integration point for cheap classification, context ranking, workflow choice and escalation | Implement `decide(state, allowed_actions) -> choice, scores, model_id, evidence`, initially with rule-based fallback; plug pretrained models in after the first three tools work |

### Suggested bootstrap, adjusted to the installed OS/version

```bash
# OpenCode — install using the current official instructions
npm install -g opencode-ai
opencode
# Inside OpenCode: /connect -> OpenAI -> Sign in with ChatGPT; /models

# Trail-code
npm install -g @trailhq/trail-code
trail init --dry-run    # inspect changes before wiring
trail init --no-global  # keep agent integration repo-local where possible
trail build             # deterministic only; no LLM pass
trail ask "turn resolution" --json

# Python foundation (within an isolated project environment)
python -m pip install pydantic tach pytest
tach init
tach check
pytest -q
```

Check official documentation before executing commands on Windows; pin working versions in the project. The `trail init` prompts/auto-wiring must be inspected: we want **OpenCode as the interface**, and do not want accidental subscription/model calls during setup. Plain `trail build` uses the deterministic parser; LLM-enriched `--deep` generation is not required. Initial testing should work without a graphical game engine.

**OpenCode integration:** prefer a *thin* OpenCode plugin or MCP adapter that exposes high-level functions (`compile_ticket`, `get_context`, `propose_architecture`, `verify_attempt`, `get_review_bundle`) and calls a separate Python harness service/CLI. Keep task logic in Python, not in a large TypeScript plugin. Verify the installed V2 plugin hook/API availability; public docs expose session-context and tool before/after hooks plus experimental typed decision generation. ChatGPT login **does not imply** free access to OpenCode Console's separately billed decision-model endpoint.

## 5. Canonical artifacts and ownership

All names below are **proposed project schemas**, not assertions that Trail-code, Tach, or agent-spec already use these exact formats. Pydantic models should define each schema and expose versioned JSON Schema. **Schemas are types, not a request to hand-author more documents.** `FAST` tasks need none of these persistent task artifacts; `STANDARD` tasks may use short-lived in-memory compiled state. For `FULL`, important intent, approvals, and receipts are versioned; transient graph snapshots and catalogs are regenerated or cached by content hash. Protect compiler-owned fields from agent writes.

**One-source-of-truth rule:** actual code is authoritative for *observed* modules, symbols, paths, imports and callers. A **small explicit policy** (for example `architecture/policy.yaml`) is authoritative only for *desired* boundaries, capability aliases/semantic intent, invariants and exceptions that cannot safely be inferred from code. Generate the capability catalog, path-to-component mappings, retrieval index, observed graph, and Tach rules from **code + that policy**. Do not hand-maintain mirrored function listings, dependency tables or code-level architecture descriptions. Rebuild on changed source revision and fail/flag if a generated artifact becomes stale. If a native Tach config must be the canonical rules file, make it the one authoritative policy store instead of creating a conflicting duplicate; investigate this in the first slice.

| Artifact | Authoritative writer | Role |
|---|---|---|
| `architecture/policy.yaml` (minimal) | Human/approved design-level changes | Intent-only boundaries, stable semantic names, invariants, explicit exceptions; **no mirror of code facts** |
| `catalog/capabilities.yaml` (generated) | Architecture compiler from source graph + policy | Current IDs, descriptions, ownership, relations, interfaces; **never edited manually** |
| `generated/observed-graph.json` (generated/cache) | Trail-code adapter | Actual source symbols/imports/calls, revision-stamped; disposable and regenerable |
| `tickets/FEAT-042.intent.yaml` | Strong model (plus human edits) | Prose intent, behavioral requirement IDs, constraints, candidate capabilities, examples |
| `compiled/FEAT-042.rev1.json` | Deterministic compiler | Resolved IDs, protected required checks, bounded context references, approved action types, hashes |
| `proposals/FEAT-042.arch-delta.json` | Medium model; validated/approved separately | Proposed changed components, public interfaces, declared deps and explicit rationale |
| `runs/FEAT-042.receipt.json` | Medium model + harness | Changed code/artifact references, requirement-to-test links; claims verified separately |
| `runs/FEAT-042.verification.json` | Test/architecture executor only | Authoritative test results, actual imports, architecture drift, source revision, evidence |
| `reviews/FEAT-042.bundle.json` | Harness only | Compact original intent + approved deltas + targeted diff + verified results |
| `runs/decisions.jsonl` | Harness | State, allowed choices, model prediction, fallback, action executed, outcome, latency |

**Example A — architect's intent ticket**

```yaml
schema_version: 1
id: FEAT-042
summary: Add stacking poison effects
intent: >
  Poison stacks additively and expires after five simulation turns.
  Expiration is deterministic for a fixed seed and action sequence.
capability_hints:
  - combat.status_effects
  - simulation.turn_lifecycle
requested_actions:
  - extend_behavior
  - modify_state_transition
requirements:
  - id: REQ-042-A
    statement: Each poison application increases total poison damage.
  - id: REQ-042-B
    statement: A poison stack expires after five turns.
acceptance_examples:
  - initial_stacks: 1
    action: apply_one_more_stack
    expected_stacks: 2
constraints:
  - Existing unrelated status effects retain behavior.
unknowns: []
```

`requested_actions` are **allowlisted catalog values**, not open-ended tool names. If new capability/action IDs are necessary, an explicit design-level proposal and catalog revision is required.

**Example B — protected compiled task**

```json
{
  "schema_version": 1,
  "task_id": "FEAT-042",
  "ticket_digest": "sha256:<computed>",
  "architecture_revision": "arch:12",
  "components": ["combat.status_effects", "simulation.turn_lifecycle"],
  "selected_evidence_ids": ["sym:apply_effect", "api:status_effects", "test:status_duration"],
  "permitted_operations": ["inspect_symbols", "propose_delta", "edit_owned_files", "run_tests"],
  "protected_obligations": {
    "acceptance_requirements": ["REQ-042-A", "REQ-042-B"],
    "new_acceptance_tests": true,
    "tach_check": true,
    "pytest": true,
    "architecture_review_if_delta": true
  },
  "context_limits": {"max_source_tokens": 4000, "max_graph_hops": 2}
}
```

All digest/version/threshold values here are illustrative. The compiler owns the values and verifies hashes against the actual tree. The medium model must not modify compiled obligations to make a failing run pass.

**Example C — architecture delta / implementer's proposed changes**

```json
{
  "task_id": "FEAT-042",
  "operations": [
    {"type": "extend_interface", "component": "combat.status_effects", "interface": "StatusEffect"},
    {"type": "declare_dependency", "from": "combat.status_effects", "to": "simulation.turn_lifecycle"}
  ],
  "needs_new_capability": false,
  "rationale": "Turn lifecycle must advance poison duration."
}
```

The architecture compiler validates this against the *desired* contract graph, then compares it with the *observed* Trail-code graph and Tach's import boundaries. A material contract/design change goes to the strong model **before** code implementation proceeds. A graph passing structural checks does **not** prove functional correctness; tests and behavioral evidence address that.

**Example D — decision and context retrieval**

```json
{
  "task_id": "FEAT-042",
  "phase": "context_enrichment",
  "state": {"candidate_symbols": 35, "source_read": false, "last_result": "graph_match"},
  "allowed_actions": ["read_top_symbols", "expand_callers", "fetch_tests", "delegate_to_engineer"],
  "selected_action": "read_top_symbols",
  "model": "local-decision-provider",
  "fallback": "deterministic_policy_if_low_confidence"
}
```

Query Trail-code once, keep the complete result **inside the harness**, and send only relevant signatures/code spans/relationship explanations to the medium model. Every returned excerpt includes path, symbol identifier, tree revision, and the reason it was retrieved. The medium agent can request bounded expansion instead of an unbounded repo dump.

**Example E — execution receipt and authoritative verification**

```json
{
  "task_id": "FEAT-042",
  "implementation_receipt": {
    "changed_components": ["combat.status_effects"],
    "requirement_test_links": {
      "REQ-042-A": ["tests/test_poison.py::test_additive_stacking"],
      "REQ-042-B": ["tests/test_poison.py::test_expiry_five_turns"]
    }
  },
  "verification": {
    "source_revision": "<actual-git-revision>",
    "tach": "pass",
    "pytest": "pass",
    "unmet_obligations": []
  }
}
```

Treat the medium model's receipt as **claims**. The verifier checks that named tests exist, ran on the right revision, and actually passed. It also verifies that expected requirement IDs were not dropped and that code changes conform to ownership and authorized scope. Final review presents the intent, approved architecture delta, targeted changed symbols and *verified* evidence—not the whole implementation transcript.

## 6. Architecture and context mechanics

Maintain **two logical graphs, not two manually maintained documents**:

- **Observed graph**: generated from source by Trail-code, refreshed incrementally and tied to a Git revision. Do **not** hand-author or edit symbol/dependency inventories.
- **Desired constraints**: a very small versioned policy containing only rules that cannot be derived from the code (e.g., forbidden cross-component dependencies, stable external capability names, invariants, exceptions). Derive module/path ownership from package layout/conventions by default, with explicit overrides only as needed.

Generate the capability catalog and any derived Tach configuration from the observed graph plus this policy; Tach then checks imports against real code. The custom adapter joins policy constraints to observed symbols via stable component/path/symbol IDs and reports mismatches. Avoid parallel sources of truth: if Tach's native file is kept as the policy source instead, generate other artifacts from it rather than also editing a competing architecture policy. **Document generation should be a build step, not a chore for humans or an LLM.**

**Four core questions to solve and measure:**

1. **Task compilation:** How to turn a prose+typed intent ticket into a deterministic, versioned, testable implementation contract? Reuse agent-spec-style requirement IDs, dependency DAG, execution bundles, traceability and evidence schemas where economical.
2. **Architecture representation:** What *minimal* intent-only policy is not derivable from code? Automatically extract actual components/symbols/dependencies and generate catalogs and Tach integration from it. Prove we do **not** maintain duplicate manually edited architecture documents.
3. **Context retrieval:** How to combine task requirements, catalog IDs, Trail-code graph, ranking and local decision models into a bounded package? Which retrievals are automatic, and which are incremental on demand?
4. **Verification:** How to produce meaningful test obligations from each requirement, run impacted tests, identify gaps, and return compact actionable failures? Structural validity is never equated with behavioral correctness.

**Important enforcement details:** default scoped writes derived from reviewed architecture; diff and dependency checks after edits; explicit `request_scope_expansion` rather than silently widening scope; allow bounded *reads* outside owned components when evidence is incomplete. For fast-moving simulation code, combine pytest with seeded scenarios and invariants. Start with a headless Python simulation; renderer/engine selection can remain separate.

## 7. Local decision models: core architectural requirement, model candidates experimental

The **decision layer is central to the objective**, even though the exact model and inference backend are not yet fixed. Start after basic Trail-code + Tach + pytest integration is working. Preserve a plugin interface from day one. Use GPU if practical; the Windows/AMD inference backend must be benchmarked rather than assumed.

| Candidate | Intended role | Notes / acceptance condition |
|---|---|---|
| **GLiNER2.5-Decide (340M)** | Multi-label task/capability classification, rank known actions, choose context profile | Apache 2.0; local CPU/GPU; outputs labels rather than arbitrary rich plans; start here for intake classification |
| **AgentDecision-4B** | Typed choices about next tool, context expansion, whether to delegate or stop | LoRA on Qwen3-4B, local; CC BY-NC 4.0; trained mostly on non-coding agents: must benchmark in shadow mode; 0.8B variant is fallback candidate |
| **OpenCode typed decision API / optional hosted Jev** | Experimental alternative transport and benchmark comparison | OpenCode has `experimental.generate.decisions`; hosted Console decision models may have separate billing and are **not** assumed included with ChatGPT login |

**Decision model jobs:** select context profile and graph expansion; classify requirements into existing architecture vocabulary; rank tool macros; decide whether deterministic diagnostic has enough evidence; choose bounded repair/inspect/escalate transitions; prune obsolete tool history before it reaches a cloud model. **Deterministic code** handles hard requirements, authorization, validity, tests, evidence/provenance and retry ceilings.

Build `DecisionProvider` interface with input `{state, allowed_actions, question_kind, constraints}` and output `{chosen_action, scores, provider, elapsed_ms}`. Record both predictions and the action/outcome. Start in **shadow mode**, where the model suggests but the existing workflow decides; promote narrow decisions one by one. Never interpret raw softmax confidence as calibrated correctness. Compare local latency + hardware overhead with the actual cloud reasoning turns saved.

## 8. Candidate integrations to investigate (important vs. optional)

### Core-path research: choose one or borrow heavily

- **agent-spec** — [repository](https://github.com/ZhangHanDong/agent-spec), [provider SDK](https://github.com/ZhangHanDong/agent-spec/blob/main/docs/code-graph-provider-kit.md). Shipped Requirement IR, task contracts, dependency planning, test obligations, provenance and execution bundles; built-in code graph is Rust-centric. **Experiment:** run the compiler on a tiny spec, inspect its versioned output schemas and test if Trail-code can satisfy the external provider protocol. Decision: adopt requirement compiler/schemas directly, or borrow them with a thin native Python compiler.
- **SIGIL** — [site/docs](https://sigilagent.com/), [instruction set](https://sigilagent.com/reference/ais-spec.html). Compiles declarative procedures into gated execution, with specific model-decision slots. **Experiment:** hand-author a minimal workflow (`resolve context -> verify requirement IDs -> run Tach -> pytest -> emit receipt`) and call it through OpenCode/MCP; compare complexity, runtime and model calls against a direct Python state machine. Decision: use its compiled runtime, or borrow its typed execution/control-flow design.
- **Architecture/compiler integration** — no proven one-command solution yet. Need a small adapter connecting requirement IDs and component contracts to Trail-code symbol references, Tach constraints, test selection and compiled task context. Reuse existing schemas aggressively; demonstrate one *end-to-end* vertical slice before committing to a framework dependency.
- **Decision provider benchmark** — GLiNER vs AgentDecision-4B/0.8B on our own allowed-action menus. Compare classification accuracy, abstention rate, task success, context tokens, cloud model turns and elapsed time. Model is a core layer; **model selection remains empirical**.

### Interesting / nice to have (after a working slice)

- **Hypothesis**: property-based and state-machine testing for simulation invariants and seeded action sequences; especially promising once a game system exists.
- **pytest-reportlog / pytest-testmon**: structured test events and impacted-test selection; use once baseline pytest collection and coverage mapping work.
- **LibCST**: exact Python structural transformations/automated migrations; useful when repetitive edits appear.
- **Context selection optimization**: learning-to-rank or boosted-tree routing over recorded task outcomes (no training prerequisite for the initial system).
- **Cached diagnostic macros**: convert recurring successful procedures into deterministic commands or SIGIL-like compiled steps.
- **Visualization and developer UI**: inspect graph deltas, requirement links and decision traces; not required to build the core system.

## 9. First vertical slice and implementation order

**Do not build the full system in one shot.** The first deliverable should be a tiny headless Python simulation with `combat`, `entities` and `turn_lifecycle`, plus a single feature ticket (stacking poison).

**Milestone A — environment:** OpenCode authenticated with ChatGPT; `opencode run` works; Trail-code builds and queries the Python repo; Tach rejects an intentional forbidden import; pytest runs and reports a deliberate failure; Pydantic validates a malformed ticket. Record exact installed versions and CLI output.

**Milestone B — schema/graph compiler:** Implement minimal Pydantic catalog, intent ticket, **minimal intent-only architecture policy**, compiled task and verification receipt. **Generate** catalogs/observed component mappings from actual code, not hand-maintained mirrors. Add Python glue for component ownership → Trail-code graph query → bounded context. Generate/check Tach constraints without treating `tach sync` as an automatic authorization of newly observed imports. Compiler must add immutable test obligations and reject unknown references or flag them for review.

**Milestone C — execution profiles and one real task:** Demonstrate `FAST` docs-only bypass and `STANDARD` contained bugfix with no large-model call. Then strong model produces the FEAT-042 intent from a compact catalog; compile a task; medium model proposes solution and architecture delta; approve/material change through review; implement in a worktree; run Tach+pytest; create verified receipt; strong model reviews **compact evidence**. One task passing end to end is the acceptance gate for proceeding.

**Milestone D — decision service:** Add GLiNER for task-profile routing and capability/action classification and a second Jev-style agent decision candidate; compare against rules on recorded context/tool transitions. Enable only choices that demonstrably reduce model turns or context while preserving task completion. Add test/diagnostic routing and bounded context expansion.

**Milestone E — compiler framework evaluation:** Evaluate agent-spec and SIGIL against the already-working vertical slice, using a clear adoption threshold: substantial reduction in custom code/maintenance without adding unbounded context or mandatory extra LLM calls.

## 10. Required benchmarks and guardrails

For each version, run the **same** 10–30 representative tasks with fixed source revisions and acceptance tests. Track: completed tasks / test passes; cloud turns; input/output/cached tokens where available; context injected per call; context expansions; decision latency and abstentions; end-to-end time; repair loops; subscription usage. Subscription usage is not dollar-denominated API cost; report both estimated token savings and quota impact when measurable. Compare at least baseline OpenCode, +Trail/Tach task compiler, and +decision routing. **Benchmark separately by FAST / STANDARD / FULL**; record the proportion of tasks that bypass the full pipeline, the number of generated versus manually edited artifacts, and whether generated catalogs stay synchronized after source changes.

Guardrails: retries have a fixed ceiling; architectural changes require explicit reviewed deltas; no silent test deletion or weaker acceptance requirements; final verification must run against the exact committed/worktree revision; source references and graph freshness must be traceable. Never hide test failures from the final reviewer. Avoid sending whole tool histories to the strong model.

**Deliverable expected from OpenCode initially:** a runnable repo with `README.md`, pinned environment setup, schemas, small Python task compiler, **minimal intent-only policy and automatically generated code-derived catalog**, example simulation and tests, Trail-code/Tach integration, a verified `FAST` bypass and one verified end-to-end `FULL` ticket. Then a short `RESEARCH_RESULTS.md` for agent-spec/SIGIL/decision-model integration experiments—not speculative infrastructure already presented as complete.

## Sources and current interfaces (verified 15 Nov 2026)

- [OpenCode provider login (ChatGPT subscription)](https://opencode.ai/docs/providers) · [CLI commands](https://opencode.ai/docs/cli/commands/) · [V2 plugin server hooks](https://opencode.ai/docs/build/plugins/server) · [typed decision endpoint](https://opencode.ai/docs/api)
- [Trail-code README: installation, deterministic graph, queries and blast radius](https://github.com/trailhq/Trail-Code)
- [Tach README](https://github.com/tach-org/tach) · [Tach commands](https://docs.gauge.sh/usage/commands/)
- [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) · [pytest](https://docs.pytest.org/)
- [agent-spec README](https://github.com/ZhangHanDong/agent-spec) · [changelog](https://github.com/ZhangHanDong/agent-spec/blob/main/CHANGELOG.md) · [external provider SDK](https://docs.rs/crate/agent-spec-code-graph-provider/latest)
- [SIGIL typed skill compiler](https://sigilagent.com/) · [instruction set](https://sigilagent.com/reference/ais-spec.html)
- [GLiNER2.5-Decide model card](https://huggingface.co/fastino/GLiNER2.5-Decide) · [AgentDecision-4B model card](https://huggingface.co/JevAgentHarness/AgentDecision-4B) · [JevAgentHarness](https://github.com/JevAgentHarness/JevAgentHarness)

*Interfaces and model availability may evolve. Before implementing adapters, inspect the exact installed release and its docs, and use version-pinned tests rather than assumptions.*
