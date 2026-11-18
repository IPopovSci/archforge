# First-run findings

**Structured generation.** The first architect response renamed the intent field and supplied compiler-owned metadata. Pydantic rejected it. Passing a role-specific output schema to Codex produced a valid ticket. The successful replay began with approved requirement IDs and prewritten acceptance examples. Creating meaningful acceptance criteria from a novel brief remains a separate test.

**Host integration.** OpenCode connected to the stdio server. Codex exposed it through the explicit project launcher. Its first unattended routing call required approval. Adding an accurate read-only annotation to that single pure function let the next call complete with the existing approval policy. OpenCode model sign-in is outside the current Codex setup.

**Model overhead.** The four successful fixture calls recorded 70,032 total input tokens and 374 output tokens across four completed turns. Their measured call times summed to 22.8 seconds. These are client-reported input totals, including any cached inputs. A compact ticket alone does not establish quota savings. A direct Codex baseline on the same work is needed for comparison.

**Verification boundary.** The verifier checks Git scope, revision, Tach, pytest status and requirement-linked passing tests. The reviewer evaluates what the tests actually prove. The live fixture controls the acceptance tests outside the implementing model. For general use, enforce protected baselines and approval for public API changes even inside allowed files. Tach's import checks alone cannot detect a changed signature.

**Decision layer and frameworks.** The runnable provider uses deterministic rules. Local inference latency, abstention quality, agent-spec interoperability and SIGIL execution have yet to be measured. The first slice supplies a reproducible baseline for those experiments.

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

For another machine, create a virtualenv under .harness/decision-env, install `gliner2[local]==2.1.0`, `torch==2.15.0` and `transformers==5.23.0`, and use Hugging Face's `hf download fastino/GLiNER2.5-Decide --revision 9d1bfb848cd16d93ee56ccbc59cd92bf0f284d90 --local-dir <checkpoint-directory>`. The local installation also retains the complete environment freeze in .harness/decision-env.lock and the measured rows in .harness/shadow-results.json.

Jev's 4B and 0.8B releases are adapters requiring their corresponding base checkpoints. Their model cards specify CC BY-NC 4.0. They were evaluated for fit from their published interfaces and remain uninstalled and unbenchmarked. [4B model card](https://huggingface.co/JevAgentHarness/AgentDecision-4B) · [0.8B model card](https://huggingface.co/JevAgentHarness/AgentDecision-0.8B)
