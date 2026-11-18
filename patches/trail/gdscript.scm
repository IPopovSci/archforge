; GDScript tags query for the Trail breadth tier.
; Node names follow the PrestonKnopp/tree-sitter-gdscript grammar bundled in
; tree-sitter-wasm. Restored by scripts/patch_trail.mjs until upstream
; trail-code merges GDScript support (tracked upstream as issue #299).

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
