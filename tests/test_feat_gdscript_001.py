"""Acceptance tests for FEAT-GDSCRIPT-001: GDScript Trail indexing, patch
persistence, Godot boundary enforcement and the headless check adapter."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import harness

REPO = Path(__file__).resolve().parents[1]
NODE = harness.BIN / ("node.exe" if os.name == "nt" else "node")
TRAIL_ENTRY = Path("node_modules/@trailhq/trail-code/dist/bin/trail.js")

SAMPLE = """class_name GSample
extends RefCounted

func _init() -> void:
	pass

static func xp_next(level: int) -> int:
	return int(floor(100.0 * pow(float(level), 1.55)))

func total(ch: Dictionary) -> float:
	return GSample.xp_next(3) + float(ch["hp"])
"""


def _main_root():
    common = harness.git("rev-parse", "--path-format=absolute", "--git-common-dir",
                         cwd=harness.INSTALL)
    return Path(common).parent


def _trail_js():
    local = REPO / TRAIL_ENTRY
    return local if local.exists() else _main_root() / TRAIL_ENTRY


def test_trail_indexes_gdscript_symbols():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "game").mkdir()
        (root / "game" / "sample.gd").write_text(SAMPLE, encoding="utf-8")
        harness.run("git", "init", "-q", cwd=root)
        result = subprocess.run([NODE, _trail_js(), "build", "--strict", "--no-gitignore",
                                 "--no-ignore", "--only-dir", "game"], cwd=root,
                                capture_output=True, encoding="utf-8", errors="replace",
                                timeout=180)
        assert result.returncode == 0, result.stdout + result.stderr
        graph = json.loads((root / "graft" / ".graph" / "wiring.json").read_text(encoding="utf-8"))
        assert any(n["kind"] == "file" and n.get("path") == "game/sample.gd"
                   for n in graph["nodes"])
        names_by_kind = {}
        for node in graph["nodes"]:
            names_by_kind.setdefault(node["kind"], set()).add(node.get("name"))
        assert "GSample" in names_by_kind.get("class", set())
        assert "xp_next" in names_by_kind.get("function", set())
        assert "_init" in names_by_kind.get("method", set())


def test_patch_trail_restores_and_is_idempotent():
    applier = REPO / "scripts" / "patch_trail.mjs"
    main_root = _main_root()
    for _ in range(2):
        result = subprocess.run([NODE, applier, str(main_root)], capture_output=True,
                                encoding="utf-8", errors="replace", timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        assert ("gdscript row already present" in result.stdout
                or "added gdscript row" in result.stdout)
    installed = main_root / "node_modules/@trailhq/trail-code/dist/graph/generic.js"
    assert '{ name: "gdscript"' in installed.read_text(encoding="utf-8")
    query = main_root / "node_modules/@trailhq/trail-code/dist/graph/queries/gdscript.scm"
    assert query.is_file()
    assert query.read_text(encoding="utf-8") == (REPO / "patches/trail/gdscript.scm").read_text(
        encoding="utf-8")


def test_boundaries_reject_undeclared_and_approve_declared():
    fixture = REPO / "fixture" / "godot"

    def run_cli(root):
        return subprocess.run([sys.executable, str(REPO / "scripts" / "godot_boundaries.py"),
                               str(root), "--policy", "godot.toml"], capture_output=True,
                              encoding="utf-8", errors="replace", timeout=60)

    violated = run_cli(fixture)
    assert violated.returncode == 1
    assert "ui_bad.gd" in violated.stdout
    assert "GStats" in violated.stdout
    assert "data.gd" in violated.stdout
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp)
        for name in ("data.gd", "stats.gd", "godot.toml"):
            (clean / name).write_bytes((fixture / name).read_bytes())
        approved = run_cli(clean)
        assert approved.returncode == 0, approved.stdout + approved.stderr
        assert "[OK] All GDScript modules validated!" in approved.stdout


def test_godot_check_reports_exit_output_and_timeout():
    adapter = REPO / "scripts" / "godot_check.py"

    def run_adapter(*cli):
        result = subprocess.run([sys.executable, str(adapter), *cli], capture_output=True,
                                encoding="utf-8", errors="replace", timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    ok = run_adapter("run", "--timeout", "60", "--", sys.executable, "-c", "print('marker')")
    assert ok["exit"] == 0
    assert "marker" in ok["output"]
    failed = run_adapter("run", "--timeout", "60", "--", sys.executable, "-c",
                         "raise SystemExit(7)")
    assert failed["exit"] == 7
    missing = run_adapter("run", "--timeout", "60", "--", "definitely-not-a-command-xyz")
    assert missing["exit"] == 126
    assert "failed to start" in missing["output"]
    stalled = run_adapter("run", "--timeout", "1", "--", sys.executable, "-c",
                          "import time; time.sleep(30)")
    assert stalled["exit"] == 124
    assert "timed out" in stalled["output"]
