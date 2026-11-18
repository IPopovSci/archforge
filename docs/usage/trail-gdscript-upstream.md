# Upstreaming the Trail GDScript patch

Trail-Code 0.30.5 does not register the GDScript grammar, although the
`tree-sitter-wasm` bundle it depends on already ships `tree-sitter-gdscript`.
Upstream tracks the language as issue #299. This repository carries the
smallest possible local patch and restores it after every install
(`scripts/patch_trail.mjs` as the npm `postinstall`). This page holds the
contribution ready to file upstream; once merged, delete the patch, the
postinstall hook and this page.

## The exact change

One breadth-tier registry row in their src/graph/generic.ts (GENERIC_LANGS),
inserted after the glsl row:

```js
{ name: "gdscript", exts: [".gd"], wasm: "gdscript" }, // #293; gdscript is #299
```

One tags query at their src/graph/queries/gdscript.scm, using only node names from
the PrestonKnopp/tree-sitter-gdscript grammar (no query predicates, matching
the breadth tier's sanitizer):

```scheme
(class_name_statement
  (name) @name) @definition.class

(function_definition
  name: (name) @name) @definition.function

(constructor_definition
  "_init" @name) @definition.method

(class_definition
  name: (name) @name) @definition.class

(call
  (identifier) @name) @reference.call

(attribute_call
  (identifier) @name) @reference.call
```

## Validation evidence (2026-11-18)

- **Orama-Interactive/Pixelorama** (production app, 249 `.gd`, ~2.2 MB):
  253/253 files parse under `--strict`; 3449 definition nodes (3229 function,
  168 class, 52 method); zero files without symbols; retrieval queries return
  correct symbols.
- **godotengine/godot-demo-projects** (461 `.gd`, mixed Godot 3/4 idioms):
  497/497 files parse under `--strict`; 2099 definitions; the only symbol-less
  files are const/export-only or bare `extends` — not parse failures. Typed
  dictionaries, `@export` property setters, `&"StringName"` literals and
  `extends "res://..."` script paths all parse.
- A one-shot model-written game (16 `.gd`): 441 nodes, 1022 call edges; its
  headless selftest passes through the same tooling.

Grammar provenance: `tree-sitter-wasm` 2.0.4 resolves
`tree-sitter-wasm/gdscript/tree-sitter-gdscript.wasm` (MIT, PrestonKnopp
tree-sitter-gdscript), so no new dependency is required — the row activates
an already-bundled grammar, the same pattern as the glsl row merged for #293.

## Filing checklist

1. Fork trailhq/Trail-Code; add the row + query in a branch.
2. Open a PR or comment on issue #299 referencing the validation above.
3. On merge and release: drop `patches/trail/gdscript.scm`, the
   `scripts/patch_trail.mjs` applier, the package.json postinstall hook, the
   patch assertions in `tests/test_feat_gdscript_001.py`, and this page; bump
   the pinned version in package.json.
