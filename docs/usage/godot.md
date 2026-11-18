# Godot and GDScript support

The harness verification stack (Trail graph, Tach boundaries, pytest) is
Python-native. This page records what exists today for Godot projects, what
was validated against the real one-shot experiment
(`E:\projects\3d_diablo\experiment\2026-11-18_godot-one-shot`, 14 `src/*.gd`
files plus a headless selftest), and which follow-up tickets complete the
story.

## Trail indexes GDScript through a local patch

Trail 0.30.5 ships tree-sitter WASM grammars for a long tail of languages,
and its own source documents the recipe: *one registry row plus one
`queries/<name>.scm` tags file*. The `gdscript` grammar is already bundled in
`tree-sitter-wasm`, but the registry row is not (upstream issue #299).

The row and the tags query live in this repository and are restored by
`scripts/patch_trail.mjs`, wired as the npm `postinstall` hook so a fresh
`npm ci` re-applies them. The applier is idempotent and fails loudly if a
future trail-code upgrade moves the anchored source line, so an upgrade can
never silently drop GDScript indexing. Manual reapplication:

```powershell
.\.venv\Scripts\node.exe scripts\patch_trail.mjs .
```

Validated on the real experiment (a copy under `E:\Temp\opencode`):

```text
parsing 16/16: ... (all .gd files)
wiring: 441 nodes (406 function, 18 class, 16 file, 1 method), 1022 edges [gdscript]
```

The 18 class nodes are the 14 global `class_name` classes plus 4 inner
classes; the tags query captures `class_name`, `func`, inner `class` and
`_init` definitions and bare-name call references. A file upstream
(trailhq/Trail-Code #299) with the row plus `patches/trail/gdscript.scm`
would retire the local patch; file it when the Godot comparison campaign
starts.

## Boundary enforcement for GDScript

`scripts/godot_boundaries.py` enforces module dependencies like Tach, with a
tach-shaped policy file (`godot.toml`, `[[modules]]` with `path` and
`depends_on`). Module paths are files or directory prefixes; a file belongs to
the longest matching prefix and a file matching nothing is unmanaged.

Cross-file coupling in GDScript happens through global `class_name`
references (the one-shot code contains no `preload` at all), plus
`preload`/`load`/`extends` of `res://` scripts. All three are extracted;
identifier references over-approximate by design — any mention of another
module's `class_name` outside comments counts as a dependency, so the gate
cannot miss a real reference at the cost of occasional false edges from string
literals.

```powershell
.\.venv\Scripts\python scripts\godot_boundaries.py <project-root> --policy godot.toml
```

Validated against the experiment copy: the natural policy (modules `src`,
`tests` with `tests -> src`) passes; a strict file-level policy produces the
real dependency map as violations — `GData` and `GDUtil` are shared leaves
referenced by nearly every file, and the checker lists all 24 undeclared
edges with exit code 1.

`fixture/godot/` mirrors the Python poison fixture: `ui_bad.gd` uses `GStats`
and preloads `stats.gd` without a declared dependency, so
`godot_boundaries.py fixture/godot` fails until the policy row is added.

## Headless Godot checks

`scripts/godot_check.py` runs a command and reports `{"exit", "output"}` —
the same shape the verifier records for Tach and pytest, so a future
compiled-check integration consumes it unchanged:

```powershell
.\.venv\Scripts\python scripts\godot_check.py selftest <project> --godot <binary>
.\.venv\Scripts\python scripts\godot_check.py run --timeout 60 -- <any command>
```

Validated end to end against the experiment selftest (Godot 4.7.2):
`67 passed, 0 failed`, exit 0. A cold checkout first needs one import pass
to build the global class cache that `class_name` references resolve through
— a fresh copy without `.godot/` fails to parse the selftest until this runs:

```powershell
godot --headless --path <project> --import   # once, after a fresh clone
```

A Godot project consumed by the harness should encode that two-step in its
own check script; the adapter stays generic.

## What is deliberately not done yet

- `verify()` still hardcodes Tach plus pytest checks. Wiring the Godot
  boundary and headless checks into compiled contracts is a boundary change
  to the compiler and needs its own reviewed ticket.
- Multi-ticket dependency plans: `FEAT-DAG-001`.
- The OpenCode side of the paired benchmark: `BENCH-OPENCODE-001`.
- Local GPU decision models: `FEAT-DECIDE-LOCAL-001`.

Tickets live in `tickets/` and compile with `python harness.py compile
tickets/<id>.json` when work starts.
