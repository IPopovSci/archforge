"""Enforce GDScript module boundaries the way Tach enforces Python imports.

Cross-file coupling in GDScript happens through global ``class_name``
references and ``preload``/``load``/``extends`` of ``res://`` scripts. This
checker maps ``.gd`` files onto modules declared in a tach-shaped policy
(``[[modules]]`` with ``path`` and ``depends_on``) and rejects undeclared
cross-module references with exit code 1, mirroring ``tach check``.

Module paths are files or directory prefixes relative to the project root; a
file belongs to the module with the longest matching prefix, and a file
matching no module is unmanaged. Identifier references over-approximate on
purpose: any mention of another module's ``class_name`` outside comments is
treated as a dependency, so the gate can never miss a real reference at the
cost of occasional false edges from string literals.
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

CLASS_NAME = re.compile(r"^\s*class_name\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SCRIPT_URL = re.compile(r"""(?:preload|load)\s*\(\s*"([^"]+\.gd)"|^\s*extends\s+"([^"]+\.gd)\"""",
                        re.MULTILINE)
COMMENT_LINE = re.compile(r"^\s*#", re.MULTILINE)
AUTOLOAD_SECTION = re.compile(r"^\[autoload\]\s*$([\s\S]*?)(?=^\[|\Z)", re.MULTILINE)
AUTOLOAD_ROW = re.compile(r"""^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"(\*?)(res://[^"]+)\"""",
                         re.MULTILINE)
ABSOLUTE_PATH = re.compile(r"""["']([A-Za-z]:[\\/][^"']*)["']""")


def scan(root):
    """Return {relative path: {classes, references, script_imports}} for every .gd file."""
    root = Path(root)
    files = {}
    for path in sorted(root.rglob("*.gd")):
        source = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(root).as_posix()
        urls = [a or b for a, b in SCRIPT_URL.findall(source)]
        files[rel] = {
            "classes": CLASS_NAME.findall(source),
            "references": set(IDENTIFIER.findall(COMMENT_LINE.sub("", source))),
            "script_imports": [u.removeprefix("res://") for u in urls],
        }
    return files


def module_of(path, modules):
    """Index of the module owning path (longest prefix), or None when unmanaged."""
    best, best_len = None, -1
    for index, module in enumerate(modules):
        base = module["path"].rstrip("/")
        if path == base or path.startswith(base + "/"):
            if len(base) > best_len:
                best, best_len = index, len(base)
    return best


def registered_autoloads(root):
    """Names registered in project.godot's [autoload] section."""
    project = Path(root) / "project.godot"
    if not project.is_file():
        return []
    source = project.read_text(encoding="utf-8", errors="replace")
    section = AUTOLOAD_SECTION.search(source)
    if not section:
        return []
    return [name for name, _, _ in AUTOLOAD_ROW.findall(section.group(1))]


def _hygiene_problems(root, files, policy):
    """Autoload allowlist and absolute-path problems; both are gate-style rules."""
    allowed = policy.get("autoloads", {}).get("allowed", [])
    problems = [f"project.godot: autoload {name} registered without a policy row "
                f"([autoloads] allowed={sorted(allowed)})"
                for name in registered_autoloads(root) if name not in allowed]
    for rel in files:
        if rel.startswith("tests/"):
            continue
        source = COMMENT_LINE.sub("", Path(root, rel).read_text(encoding="utf-8",
                                                                errors="replace"))
        match = ABSOLUTE_PATH.search(source)
        if match:
            problems.append(f"{rel}: absolute filesystem path '{match.group(1)}' "
                            f"(use res:// or user://)")
    return problems


def check(root, policy):
    """Return tach-style boundary problems for the .gd files under root."""
    modules = policy["modules"]
    if len({m["path"] for m in modules}) != len(modules):
        return ["Duplicate module declaration in policy"]
    files = scan(root)
    class_map = {}
    problems = []
    for rel, info in files.items():
        for cls in info["classes"]:
            if cls in class_map:
                problems.append(f"{rel}: class_name {cls} is already declared in {class_map[cls]}")
            class_map[cls] = rel
    for rel, info in files.items():
        index = module_of(rel, modules)
        if index is None:
            problems.append(f"{rel}: not covered by any declared module")
            continue
        declared = set(modules[index]["depends_on"])
        edges = {target: Path(target).stem for target in info["script_imports"]
                 if target in files}
        for target in info["script_imports"]:
            if target not in files:
                problems.append(f"{rel}: imports missing script {target}")
        for identifier in sorted(info["references"]):
            target = class_map.get(identifier)
            if target is not None and target != rel:
                edges[target] = identifier
        for target, label in sorted(edges.items()):
            other = module_of(target, modules)
            if other is None:
                problems.append(f"{rel}: references script {target} outside any declared module")
            elif other != index and modules[other]["path"] not in declared:
                problems.append(
                    f"{rel}: cannot use '{label}' from module '{modules[other]['path']}'; "
                    f"module '{modules[index]['path']}' does not depend on it")
    problems.extend(_hygiene_problems(root, files, policy))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", help="Godot project root to check")
    parser.add_argument("--policy", default="godot.toml", help="boundary policy file (TOML)")
    args = parser.parse_args(argv)
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = Path(args.root) / policy_path
    problems = check(args.root, tomllib.loads(policy_path.read_text(encoding="utf-8")))
    if problems:
        print("GDScript Internal Dependencies")
        for problem in problems:
            print(f"[FAIL] {problem}")
        print("\nTo allow a new dependency, add it to depends_on in the boundary policy.")
        return 1
    print("[OK] All GDScript modules validated!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
