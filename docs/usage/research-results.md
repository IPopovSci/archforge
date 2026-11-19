# First-run findings

**Structured generation.** The first architect response renamed the intent field and supplied compiler-owned metadata. Pydantic rejected it. Passing a role-specific output schema to Codex produced a valid ticket. The successful replay began with approved requirement IDs and prewritten acceptance examples. Creating meaningful acceptance criteria from a novel brief remains a separate test.

**Host integration.** OpenCode connected to the stdio server. Codex exposed it through the explicit project launcher. Its first unattended routing call required approval. Adding an accurate read-only annotation to that single pure function let the next call complete with the existing approval policy. OpenCode model sign-in is outside the current Codex setup.

**Model overhead.** The four successful fixture calls recorded 70,032 total input tokens and 374 output tokens across four completed turns. Their measured call times summed to 22.8 seconds. These are client-reported input totals, including any cached inputs. A compact ticket alone does not establish quota savings. A direct Codex baseline on the same work is needed for comparison.

**Verification boundary.** The verifier checks Git scope, revision, Tach, pytest status and requirement-linked passing tests. The reviewer evaluates what the tests actually prove. The live fixture controls the acceptance tests outside the implementing model. For general use, enforce protected baselines and approval for public API changes even inside allowed files. Tach's import checks alone cannot detect a changed signature.

**Decision layer and frameworks.** Deterministic rules enforce routing. The local inference measurements below use this baseline. Agent-spec interoperability and SIGIL execution remain open experiments.

## Self-hosting experiment

The first catalog covered only the three fixture modules. A search for compile_ticket missed harness.py. Adding the application modules to Tach policy and indexing tracked Python roots fixed this. Retrieval now returns the compiler source and can reuse the main installation from a linked worktree. A forbidden harness-to-server import failed Tach. A change to the arguments of a public function promoted a single-file diff to FULL. A real synthetic repo exercised approved and unapproved signatures, addition of a new component with reviewed dependency policy, and rejection of policy drift.

## Local decision model experiment

GLiNER2.5-Decide ran offline on four CPU threads on this Windows machine. Checkpoint revision `9d1bfb848cd16d93ee56ccbc59cd92bf0f284d90` matched the publisher's SHA-256. Thirteen hand-labeled engineering examples gave GLiNER 9 correct and the path rules 12 correct. Median classification took 282 ms after 4.5 s model load. Both systems missed the requested public API change in a single known file. The file-diff check and the up-front semantic review cover that case. This small suite measures routing agreement, with no estimate of cloud turns saved. GPU inference on the RX 9070 XT remains unbenchmarked. [GLiNER model card](https://huggingface.co/fastino/GLiNER2.5-Decide)

The experimental environment is separate from the harness. From the project root, run:

```powershell
$checkpoint = ".harness/models/gliner-9d1bfb848cd16d93ee56ccbc59cd92bf0f284d90"
.\.harness\decision-env\Scripts\python scripts/shadow_decisions.py $checkpoint
.\.harness\decision-env\Scripts\python scripts/shadow_decisions.py $checkpoint --request "Change the compiler ticket schema" --paths harness.py
```

## Selective use of multiple signals

A fresh Sol engineer implemented the advisory assessment as a harness task. Its independent verifier ran Tach and 23 tests. The assessment takes intended paths and optionally the Git diff from `--base`. Mandatory FULL changes, documentation-only changes and isolated tests bypass inference. Ambiguous STANDARD work can query GLiNER for a suggested promotion. Missing weights, classifier errors and unknown labels produce explicit abstentions. The deterministic floor, recommendation and disagreement are visible separately.

On a second set of 14 synthetic requests, seven required FULL review. Three examples supplied small before/after source pairs for computing observed interface impact. Each treatment used the same cases:

| Treatment | Correct | Missed FULL | Unnecessary FULL | Classifier calls per 14 |
|---|---:|---:|---:|---:|
| Path rules | 10 | 4 | 0 | 0 |
| Paths and observed impact | 12 | 2 | 0 | 0 |
| GLiNER alone | 6 | 5 | 0 | 14 |
| Deterministic evidence with selective GLiNER | 13 | 1 | 0 | 5 |

The paired evaluation ran GLiNER once per case and reused each prediction to calculate what the selective policy would do. GLiNER helped flag a proposed versioned report format. Both the deterministic and selective methods missed a new plugin lifecycle proposed within one file. This is evidence for a trial on actual tasks. The sample is too small to estimate generalization, cloud savings or subscription impact.

```powershell
.\.harness\decision-env\Scripts\python scripts/shadow_decisions.py $checkpoint --benchmark-selective
.\.harness\decision-env\Scripts\python scripts/shadow_decisions.py $checkpoint --base HEAD --request "Design a versioned report format" --paths server.py
```

For another machine, create a virtualenv under .harness/decision-env, install `gliner2[local]==2.1.0`, `torch==2.15.0` and `transformers==5.23.0`, and use Hugging Face's `hf download fastino/GLiNER2.5-Decide --revision 9d1bfb848cd16d93ee56ccbc59cd92bf0f284d90 --local-dir <checkpoint-directory>`. The local installation also retains the complete environment freeze in .harness/decision-env.lock and the measured rows in .harness/shadow-results.json.

Jev's 4B and 0.8B releases are adapters requiring their corresponding base checkpoints. Their model cards specify CC BY-NC 4.0. They were evaluated for fit from their published interfaces and remain uninstalled and unbenchmarked. [4B model card](https://huggingface.co/JevAgentHarness/AgentDecision-4B) · [0.8B model card](https://huggingface.co/JevAgentHarness/AgentDecision-0.8B)

## Deem-4B decision experiments on the landed assess seam

Deem-4B (JevAlt, Apache-2.0, fine-tuned from Intern-Decision-4B) is a System One decision model: it answers typed questions (Choice, Score, Noul) over a Jev-compatible `POST /v1/systemone` endpoint with calibrated per-option probabilities, spending one output token per decision. The staged Q4_K_M GGUF (2.71 GB, quant parity report and `calibration.json` retained in `.harness/models/deem-4b-q4km-8f30f44881052e93e7bede109e694d4052382833/`) answered the open unknowns of FEAT-DECIDE-LOCAL-001: the candidate model and both runtimes work. `jevalt serve` (isolated `.harness/systemone-env`, freeze in `.harness/systemone-env.lock`) implements `/v1/systemone` over llama.cpp on CPU and loads the published calibration; one caveat for offline setups: calibration is fetched by hub repo id, so a local-only install must load it at the driver level. The plain llama.cpp b12521 Vulkan server (`-ngl 99`, RX 9070 XT) covers the naive chat-completions protocol on GPU. This confirms a System One-compatible local server covers the same question types the seam asks, with calibrated abstention available.

Both frozen suites from the GLiNER experiments were replayed unchanged through the landed floor-first band. Every row is in `.harness/deem-routing-results.json`; per-request latencies are medians over the suite.

| Treatment | Correct | Missed FULL | Unnecessary FULL | Calls | Median latency |
|---|---:|---:|---:|---:|---:|
| Path rules (13-case suite, recorded) | 12/13 | 1 | 0 | 0 | 0 |
| GLiNER alone (13-case, recorded) | 9/13 | 4 | 0 | 13 | 282 ms CPU |
| Deem alone (typed, 13-case) | **13/13** | **0** | **0** | 13 | 2.1 s CPU |
| Path rules (14-case suite, recorded) | 10/14 | 4 | 0 | 0 | 0 |
| Rules + observed impact (recorded) | 12/14 | 2 | 0 | 0 | 0 |
| GLiNER alone (14-case, recorded) | 6/14 | 5 | 0 | 14 | 282 ms CPU |
| Deem alone (typed, 14-case) | 12/14 | 2 | 0 | 14 | 2.2 s CPU |
| Floor + selective GLiNER (recorded) | 13/14 | 1 | 0 | 5 | 282 ms CPU |
| Floor + selective Deem (typed) | **14/14** | **0** | **0** | 5 | 2.2 s CPU |
| Floor + selective Deem (chat, GPU) | **14/14** | **0** | **0** | 5 | 592 ms GPU |

Deem alone caught the public-schema, agent-policy and design-bible cases that both GLiNER and the path rules missed. Its two suite-B misses are exactly the two public-signature changes the deterministic public-API digest covers: floor and model each catch what the other misses, and the union is complete. No call fell below the published 90% conformal choice threshold (0.505); the lowest-confidence answer (0.378) was still correct, so the calibrated abstention path remains unexercised on these suites. The model card's warning that planted instructions flip 14% of answers is a direct endorsement of the landed design: authorization stays in deterministic code, the model only advises inside the band.

**GLiNER placement verdict.** On routing evidence Deem dominates GLiNER everywhere at acceptable cost: 13/13 vs 9/13 alone, 14/14 vs 13/14 selective, with 2.1 s CPU (typed) or 0.6 s (chat on GPU) against GLiNER's 282 ms CPU — all far below a cloud reasoning turn, and the in-band policy calls it on only 5 of 14 tasks. Recommendation: demote GLiNER from the routing slot and keep it for its original handoff role (multi-label capability and action classification, where its zero-shot labeling is the right shape), and promote a Deem adapter behind the landed `AdvisoryProvider` seam. Both stay pluggable; the seam keeps the floor deterministic.

**Alternative-use probe.** A second frozen probe tested the compact-evidence review job on six real verification outputs (demo replay artifacts from `.harness/runs` plus the FEAT-DECIDE-SEAM-001 verification with two structural failure variants): choice-with-criteria scored 6/6 on satisfied/unsatisfied, Score tracked severity on five of six, and bare Noul proved unreliable for satisfaction predicates (0.42 on a passing case). A local first-pass triage before a cloud final review is plausible but needs a larger frozen suite before any workflow role; rows are in `.harness/evidence-triage-results.json`.

Caveats: both suites are small, synthetic and hand-labeled, and their category wording shaped the criteria in the prompts, so 13/13 and 14/14 are evidence of fit on these suites, not a generalization or cloud-savings estimate. Reproduction:

```powershell
.\.harness\systemone-env\Scripts\jevalt.exe serve --model mertkayacs/Deem-4B-GGUF --file <local Deem-4B-Q4_K_M.gguf> --port 8020
.\.venv\Scripts\python .harness\experiments\deem_routing.py
.\.venv\Scripts\python .harness\experiments\evidence_triage.py
```

Next steps (parked): FEAT-DECIDE-ADAPT-001 registers the wiring and its gate. The larger suite must come from real engineering requests, and the calibrated abstention path is still unexercised: no call reached a conformal threshold, so a suite that triggers abstention is a prerequisite for trusting it. The typed protocol is CPU-only through jevalt's llama.cpp backend; the Vulkan chat protocol is the GPU option at equal accuracy on these suites. The evidence-triage probe needs a larger frozen suite before the compact-evidence review gains a local first-pass gate. Both servers were left running for continuation: jevalt on 127.0.0.1:8020 and llama-server on 8010.

## Trail and embedding retrieval

The study froze 35 observed function candidates at Git revision `228066d5fa95ef33ae677338365a53c1adc62579`, four exact-name targets and eight behavioral questions before running inference. Dense and TF-IDF methods saw the same symbol text. The operational Trail CLI baseline retains rank positions occupied by files or test symbols. Each question has one designated target, so another useful function can still count as a miss.

| Method | Exact target first, of 4 | Behavioral target in top three, of 8 |
|---|---:|---:|
| Trail ask | 4 | 1 |
| Word and bigram TF-IDF | 2 | 2 |
| MiniLM | 2 | 5 |
| BGE-small | 3 | 4 |
| Trail + MiniLM reciprocal rank fusion | 3 | 4 |
| Trail + BGE reciprocal rank fusion | 4 | 3 |

MiniLM found the turn-ticking implementation first for a question about remaining lifetime and damage. It ranked the fresh-engineer session launcher thirteenth on a question that TF-IDF answered first. The experimental lookup answers exact symbol names and IDs from a Trail snapshot. Other questions search the whole eligible function corpus with MiniLM. This avoids dropping candidates that never appeared in Trail's initial lexical results. The live corpus includes the experimental module and methods, whereas the benchmark excluded both. Treat the small frozen study as an indication of where to try each tool.

The routing comparison used 13 labeled nearest-neighbor exemplars and 14 separate test prompts. With the intended-path minimum, TF-IDF scored 11/14, MiniLM 10/14 and BGE 11/14. Each missed one FULL task. They produced two, three and two unnecessary FULL recommendations respectively. The earlier selective GLiNER experiment also had diff evidence for some cases. Keep embeddings optional for retrieval while collecting real engineering queries.

### Reproduce the offline study

Use the separate decision environment with the previously listed Torch and Transformers versions, plus `scikit-learn==1.9.1` and `nodejs-wheel==24.19.0`. The tested dependency freeze is in `.harness/embedding-env.lock`. Use the official model IDs and revisions below. HF's CLI can download only the root tokenizer files, config and safetensors weights.

```powershell
$miniRev = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
$bgeRev = '5c38ec7c405ec4b44b94cc5a9bb96e735b38267a'
$mini = ".harness/models/minilm-$miniRev"
$bge = ".harness/models/bge-$bgeRev"
.\.harness\decision-env\Scripts\hf download sentence-transformers/all-MiniLM-L6-v2 --revision $miniRev --local-dir $mini --include 'config.json' 'tokenizer*.json' 'special_tokens_map.json' 'vocab.txt' 'model.safetensors'
.\.harness\decision-env\Scripts\hf download BAAI/bge-small-en-v1.5 --revision $bgeRev --local-dir $bge --include 'config.json' 'tokenizer*.json' 'special_tokens_map.json' 'vocab.txt' 'model.safetensors'
.\.harness\decision-env\Scripts\python scripts/shadow_decisions.py --embedding-study $mini $bge
```

Run the experiment script by absolute path from a clean checkout of the frozen corpus to reproduce the original comparison. Use absolute model paths in that case. The recorded per-query ranks, timings and revision are in `.harness/embedding-results.json`. Both checkpoints passed SHA-256 verification and ran on CPU with local files only. [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) and [BGE model card](https://huggingface.co/BAAI/bge-small-en-v1.5)

### Checkout and framework probes

A live Codex MCP call successfully routed a request in a second worktree containing an unrelated README edit. Its dirty compilation correctly failed. The clean companion compiled the same ticket while the unrelated edit retained its original hash. This covered a noninteractive Codex process.

Agent-spec 1.4.0 built with a project-local Rust toolchain. The upstream note-app gated plan produced two requirement entries and its two Rust contract tests passed. A fresh import passed its drift check. The checked-in fixture failed that check; the diff included an accepted requirement that fresh import emits as proposed. Provider manifest validation passed. The runtime conformance probe using Git Bash exceeded two minutes, requiring cleanup of its runner and helper. A Trail-to-agent-spec runtime adapter remains unverified. [Agent-spec provider kit](https://github.com/ZhangHanDong/agent-spec/blob/v1.4.0/docs/code-graph-provider-kit.md)

SIGIL 0.7.16's npm package rejected native Windows. Its official installer uses Docker or a Linux WSL distribution. After enabling SVM, upgrading Docker Desktop to 29.9.3, and removing the stale internal distributions, the rebuilt Linux engine passed `hello-world`. The pinned GHCR image rejected anonymous access, so SIGIL was built locally from the tagged source with its pinned Jac 0.37.25 runtime. The persistent container is running with state, graph, and skills volumes, and only this project is mounted at `/host`. Its official `writing-plans` AG-IR gate passed with `gate: ok (1919 lines lowered)`. Project-local path forwarding works from PowerShell through `scripts/sigil.cmd`. Model connection and an end-to-end new `SKILL.md` compile remain open.

### Paired benchmark setup

`benchmarks/tasks.json` defines ten seeded engineering tasks: one FAST documentation repair, four STANDARD contained fixes, and five FULL policy or architecture repairs. Each task has a fixed request, target file, Trail query, seeded defect, focused acceptance test, and command. `scripts/benchmark.py --dry-run` created a disposable worktree for every task, applied the seed, and confirmed all ten focused tests failed before any model call. That validates the benchmark’s starting state.

The first paired model run used Codex with Sol for the FAST documentation task. Baseline and Trail-context treatments both repaired the seeded defect and passed the focused test:

| Treatment | Passed | Seconds | Input tokens | Cached input | Output |
|---|---:|---:|---:|---:|---:|
| Baseline | 1/1 | 68.87 | 79,703 | 59,008 | 2,688 |
| Trail context | 1/1 | 80.82 | 119,927 | 98,176 | 2,952 |

The sample was then extended to one STANDARD repair and one FULL architecture repair. Across the three completed paired tasks, baseline and Trail context both passed 3/3:

| Treatment | Passed | Total seconds | Input tokens | Cached input | Output |
|---|---:|---:|---:|---:|---:|
| Baseline | 3/3 | 268.41 | 393,113 | 338,432 | 10,048 |
| Trail context | 3/3 | 289.24 | 481,471 | 405,760 | 10,249 |

Trail context was slower and used more input tokens on these three seeded repairs while producing the same pass count. After correcting a flawed review-binding acceptance test, the full ten-task Codex run completed:

| Treatment | Passed | Total seconds | Input tokens | Cached input | Output |
|---|---:|---:|---:|---:|---:|
| Baseline | 10/10 | 1,373.49 | 1,634,896 | 1,413,888 | 54,434 |
| Trail context | 10/10 | 1,409.45 | 1,895,062 | 1,624,704 | 54,752 |

Trail context added 35.96 seconds and 260,166 input tokens while producing the same 10/10 pass count on this deliberately broken suite. This is evidence that the harness improves reproducibility and evidence capture, not that Trail context improves repair quality or cost on this seed set. The corrected review-binding rerun passed 1/1 for both treatments. The OpenCode comparison remains open.
