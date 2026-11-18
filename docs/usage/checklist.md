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
- [ ] Benchmark alternative providers on real requests and compare agent-spec and SIGIL with the existing compiler.
