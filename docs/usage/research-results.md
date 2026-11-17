# First-run findings

**Structured generation.** The first architect response renamed the intent field and supplied compiler-owned metadata. Pydantic rejected it. Passing a role-specific output schema to Codex produced a valid ticket. The successful replay began with approved requirement IDs and prewritten acceptance examples. Creating meaningful acceptance criteria from a novel brief remains a separate test.

**Host integration.** OpenCode connected to the stdio server. Codex exposed it through the explicit project launcher. Its first unattended routing call required approval. Adding an accurate read-only annotation to that single pure function let the next call complete with the existing approval policy. OpenCode model sign-in is outside the current Codex setup.

**Model overhead.** The four successful fixture calls recorded 70,032 total input tokens and 374 output tokens across four completed turns. Their measured call times summed to 22.8 seconds. These are client-reported input totals, including any cached inputs. A compact ticket alone does not establish quota savings. A direct Codex baseline on the same work is needed for comparison.

**Verification boundary.** The verifier checks Git scope, revision, Tach, pytest status and requirement-linked passing tests. The reviewer evaluates what the tests actually prove. The live fixture controls the acceptance tests outside the implementing model. For general use, enforce protected baselines and approval for public API changes even inside allowed files. Tach's import checks alone cannot detect a changed signature.

**Decision layer and frameworks.** The runnable provider uses deterministic rules. Local inference latency, abstention quality, agent-spec interoperability and SIGIL execution have yet to be measured. The first slice supplies a reproducible baseline for those experiments.
