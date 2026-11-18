"""Acceptance tests for FEAT-DOC-LAYER-001: the generated documentation
layer — catalog rendering, staleness and pointer gates, advisory stats."""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location("doc_catalog", REPO / "scripts" / "doc_catalog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DOC = _module()


def test_catalog_renders_from_repository_state():
    data = DOC.build(REPO)
    assert "harness" in data["modules"]
    assert "compile_ticket" in data["modules"]["harness"]["public"]
    doc_ticket = next(t for t in data["tickets"] if t["id"] == "FEAT-DOC-LAYER-001")
    assert doc_ticket["acceptance"] == "tests/test_feat_doc_layer_001.py"
    first = DOC.render(data, "0" * 40)
    second = DOC.render(DOC.build(REPO), "0" * 40)
    assert first == second
    assert "rendered from revision" in first
    assert "| harness | `harness.py` |" in first


def test_check_flags_stale_catalog():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "tach.toml").write_bytes((REPO / "tach.toml").read_bytes())
        target = root / "docs/usage/catalog.md"
        target.parent.mkdir(parents=True)
        fresh = DOC.render(DOC.build(root), "0" * 40)
        stale = fresh.replace("| harness |", "| harnessXX |")
        target.write_text(stale, encoding="utf-8")
        assert any("stale" in problem for problem in DOC.check(root))
        target.write_text(fresh, encoding="utf-8")
        assert DOC.check(root) == []


def test_check_flags_broken_documentation_pointers():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "tach.toml").write_bytes((REPO / "tach.toml").read_bytes())
        target = root / "docs/usage/catalog.md"
        target.parent.mkdir(parents=True)
        target.write_text(DOC.render(DOC.build(root), "0" * 40), encoding="utf-8")
        (root / "README.md").write_text(
            "See `gone/missing.py` and bare `missing.py` prose and `harness.py`.\n",
            encoding="utf-8")
        problems = DOC.check(root)
        assert any("references missing path `gone/missing.py`" in problem for problem in problems)
        assert not any("`missing.py`" in problem for problem in problems)
        assert not any("`harness.py`" in problem for problem in problems)
        assert DOC.check(REPO) == []


def test_stats_report_drift_and_comment_density():
    report = DOC.stats(REPO)
    assert set(report) == {"drift", "comments"}
    assert "harness" in report["comments"]
    assert report["comments"]["scripts.doc_catalog"]["comment_lines"] > 0
    for row in report["drift"]:
        assert set(row) == {"document", "overlap", "sentence"}
        assert row["overlap"] >= 0.6
    assert DOC._jaccard("same words here now", "same words here now") == 1.0
    assert DOC._jaccard("alpha beta", "gamma delta") == 0.0
