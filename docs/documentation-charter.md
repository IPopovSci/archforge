# Documentation charter

This repository's documentation is a four-layer system. Every documentation
fact has exactly one home; every other mention is a pointer. The layers:

| Layer | Answers | Writer | Home | Gate |
|---|---|---|---|---|
| L0 — binding | Why it exists, what must stay true | humans, via reviewed tickets | `AGENTS.md`, `OPENCODE_HARNESS_HANDOFF.md`, `docs/documentation-charter.md`, `project_example/lines-master-design-bible.md` | Router sends changes to FULL review |
| L1 — contracts | What is obligated, what is allowed | tickets, compiled contracts, policy files | `tickets/`, `.harness/compiled/`, `tach.toml`, `fixture/godot/godot.toml` | Compiler + verifier |
| L2 — observed | What actually is there | **generated only** | `docs/usage/catalog.md` | `scripts/doc_catalog.py check` fails on staleness |
| L3 — point truth | What this exact function does | code and docstrings | source files | Review; narration is deleted |

Rules, enforced or measured programmatically:

1. **L2 is never hand-written.** `docs/usage/catalog.md` is generated from
   the Tach policy, the AST and `tickets/`. Editing it by hand is a mistake
   by definition; `doc_catalog.py check` fails until a fresh render replaces
   the edit.
2. **Pointers must resolve.** Hand documentation (README, AGENTS, charter,
   docs pages) may reference repository paths freely — that is the zoom
   lattice — but `doc_catalog.py check` fails when a referenced path does
   not exist. Links rot no further than the next gate run.
3. **Restate nothing.** When a hand document and the generated catalog agree
   sentence-for-sentence, the hand sentence should become a pointer.
   `doc_catalog.py stats` reports the highest-overlap sentences as advisory
   drift numbers.
4. **Comments carry invariants, not narration.** A comment earns its place
   by stating a why, a constraint, or a reference (requirement ID, spec
   section, pointer). Comments that restate the next line are deleted in
   review. `stats` reports comment density and non-referential comment
   counts per module as visible numbers, not gates.
5. **Placement implies review weight.** `README.md` and `docs/usage/*.md`
   route FAST (usage notes, generated pages). Anything binding lives
   outside `docs/usage/` and routes FULL — the router itself is a
   documentation-governance rule.

Wiring L2 gates into compiled verification checks is deliberately parked as
a boundary-change ticket until the check-list generalization lands.
