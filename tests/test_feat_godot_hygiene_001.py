"""Acceptance tests for FEAT-GODOT-HYGIENE-001: autoload registration
allowlists and absolute-path hygiene in the GDScript boundary checker."""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "fixture" / "godot"


def _run_cli(root):
    return subprocess.run([sys.executable, str(REPO / "scripts" / "godot_boundaries.py"),
                           str(root), "--policy", "godot.toml"], capture_output=True,
                          encoding="utf-8", errors="replace", timeout=60)


def test_autoload_allowlist_enforced():
    violated = _run_cli(FIXTURE)
    assert violated.returncode == 1
    assert "autoload GData registered without a policy row" in violated.stdout
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp)
        for name in ("data.gd", "stats.gd", "godot.toml", "project.godot"):
            (clean / name).write_bytes((FIXTURE / name).read_bytes())
        policy = (clean / "godot.toml").read_text(encoding="utf-8")
        (clean / "godot.toml").write_text(
            policy.replace('allowed = ["GUtil"]', 'allowed = ["GData"]'), encoding="utf-8")
        approved = _run_cli(clean)
        assert approved.returncode == 0, approved.stdout + approved.stderr
        assert "[OK] All GDScript modules validated!" in approved.stdout


def test_absolute_paths_rejected():
    violated = _run_cli(FIXTURE)
    assert violated.returncode == 1
    assert "absolute filesystem path 'E:/Temp/shot.png'" in violated.stdout
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp)
        for name in ("data.gd", "stats.gd", "godot.toml", "project.godot"):
            (clean / name).write_bytes((FIXTURE / name).read_bytes())
        policy = (clean / "godot.toml").read_text(encoding="utf-8")
        (clean / "godot.toml").write_text(
            policy.replace('allowed = ["GUtil"]', 'allowed = ["GData"]'), encoding="utf-8")
        approved = _run_cli(clean)
        assert approved.returncode == 0, approved.stdout + approved.stderr
        # the clean copy still contains res:// and user:// paths, which pass
        assert "user://saves" in (clean / "data.gd").read_text(encoding="utf-8")
        assert "absolute filesystem path" not in approved.stdout
