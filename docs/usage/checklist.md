# Codex harness readiness

## Verified on Windows

- [x] Install the Python and Node dependencies locally with version locks. Python 3.14.3, Node 24.19.0, Trail 0.30.5, Tach 0.35.3, pytest 9.2.0 and Pydantic 2.14.3 ran here. `pip check` passed.
- [x] Launch signed-in Codex CLI 0.169.1 with the project MCP server. A live read-only routing call returned FAST for README.md.
- [x] Build the Trail graph, query Python source, check component mappings against Tach policy and generate revision-bound context.
- [x] Demonstrate FAST on a documentation edit and STANDARD on a contained repair in Git. The replay used zero cloud calls.
- [x] Reject a malformed ticket, fail on a forbidden dependency, fail the original behavior on new acceptance tests, and reject an out-of-scope attempt.
- [x] Run a FULL fixture using Astra for intent and final review and Sol for proposal and implementation. Both linked acceptance tests passed, along with nine regression and workflow tests. Tach passed. Final verdict was approve on candidate `423240fa5c9627aa60e317efbb759093652f77a7`.

The live artifacts are in `.harness/live/6fd4c3c3dc134e1da2b7018022b5bc9b/`. Compare red.json, review.json and decision.txt. This candidate lives in a separate Git worktree so the baseline remains replayable.

## Open before general-purpose use

- [x] Use one harness for the compiler, server, engineering scripts and fixture. Trail retrieves the compiler definition. Tach rejects a reverse dependency from the compiler to the server.
- [x] Compile and verify a synthetic new tool component against a reviewed policy. Exercise a public-signature change with and without approval, including rejection of policy drift.
- [ ] Verify normal interactive use on a second checkout, including starting with unrelated uncommitted user work. Compilation currently requires a clean tree.
- [ ] Benchmark baseline Codex, compiler-assisted Codex and decision-assisted Codex on the same 10–30 tasks by profile. Compare completion, time, turns, tokens and repair counts.
- [x] Run GLiNER locally against a labeled shadow suite and compare with rules. See research-results.md for the measured results and reproduction command.
- [x] Compare path rules, diff evidence, GLiNER and selective inference on a second suite. Confirm a deterministic request works with the model absent.
- [x] Pin delegated architect and reviewer invocations to Astra and engineering to Sol. Observe unique live thread IDs for both engineering phases and a separate self-development task.
- [x] Exercise the Windows unattended edit failure. The bounded edit command applied a real Sol change and ran independent checks. The shared verifier rejected unapproved API changes and a regression now covers removing ordinary public bindings.
- [ ] Benchmark alternative providers on real requests and compare agent-spec and SIGIL with the existing compiler.
- [x] Compare two offline embedding encoders with Trail, TF-IDF and rank fusion. Test a separate Trail extraction, vector-preparation process and warm semantic lookup.
- [x] Validate a live noninteractive Codex request on a second checkout with unrelated dirty work and compile in its clean companion.
- [x] Build and exercise agent-spec 1.4.0 planning and fixture tests. Windows conformance and SIGIL runtime validation remain open; see the research results.
- [x] Upgrade Docker Desktop to 29.9.3, rebuild its internal WSL distributions, run `hello-world`, and leave the Linux engine healthy.
- [x] Build and run SIGIL 0.7.16 locally from its pinned source. The persistent container is running, its deterministic official example gate passed, and project-local path forwarding works.
- [x] Add a ten-task paired benchmark suite covering FAST, STANDARD, and FULL work. Dry-run validation confirmed every seeded defect fails its focused test without spending model calls.
- [x] Exercise the paired benchmark runner end to end on one FAST task. Baseline and Trail-context treatments both passed, and the runner recorded per-task seconds, client, model, session ID, input tokens, output tokens, cached tokens, changed files, and focused test result.
- [x] Extend the paired sample to one STANDARD and one FULL seeded repair. Baseline and Trail context each passed all three sampled tasks.
- [x] Run the complete ten-task Codex suite. Baseline and Trail context each repaired 10/10 seeded defects.
- [ ] Compare OpenCode on the same ten tasks before drawing a cross-client cost or quality conclusion.
