"""Acceptance tests for FEAT-VERIFY-CHECKS-001: the named check registry,
default documentation gating inside compiled contracts, and ticket-declared
language-adapter checks."""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import harness as h

REPO = Path(__file__).resolve().parents[1]


def test_registry_defines_pluggable_named_checks():
    commands = h.check_commands(Path("report.xml"))
    assert set(commands) == {"tach", "pytest", "doc_gates", "godot_boundaries"}
    assert commands["doc_gates"] == [sys.executable, "scripts/doc_catalog.py", "check", "."]
    assert commands["godot_boundaries"] == [sys.executable, "scripts/godot_boundaries.py", ".", "--policy", "godot.toml"]
    assert "--junitxml" in commands["pytest"]
    assert h.STRUCTURAL_CHECKS == ("requirement links", "scope")
    assert h.DEFAULT_CHECKS == ("tach", "pytest", "requirement links", "scope", "doc_gates")


def test_compile_rejects_unknown_and_structural_check_names():
    def ticket(checks):
        return h.Ticket(version=1, id="VCDOC-900", intent="scratch",
                        components=["tool"], actions=["extend_behavior"],
                        requirements={"REQ-S-A": "scratch"}, unknowns=[], checks=checks)
    with pytest.raises(ValueError, match="Unknown check names"):
        h.compile_ticket(ticket(["nope"]))
    with pytest.raises(ValueError, match="not ticket-declarable"):
        h.compile_ticket(ticket(["scope"]))
    with pytest.raises(ValueError, match="not ticket-declarable"):
        h.compile_ticket(ticket(["requirement links"]))


def test_doc_gate_blocks_stale_catalog_then_verifies_repair(tmp_path, monkeypatch):
    """End to end in a synthetic repository: a hand-edited generated catalog
    fails verification through the default doc_gates check, a fresh render
    passes, and a ticket-declared check folds into the contract list."""
    monkeypatch.chdir(tmp_path)
    h.git("init", "-q")
    Path("tests").mkdir()
    Path(".gitignore").write_text(".harness/\ngraft/\nscripts/\n__pycache__/\n.pytest_cache/\n")
    Path("tach.toml").write_text('source_roots=["."]\n[[modules]]\npath="tool"\ndepends_on=[]\n')
    Path("tool.py").write_text("def build(): return 7\n")
    Path("scripts").mkdir()
    shutil.copy(REPO / "scripts" / "doc_catalog.py", "scripts/doc_catalog.py")
    subprocess.run([sys.executable, "scripts/doc_catalog.py", "render", "."], check=True)
    def commit(message):
        h.git("add", "-A")
        h.git("-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-qm", message)
    commit("baseline")
    base = h.clean_revision()
    ticket = h.Ticket(version=1, id="VCDOC-100", intent="tool build returns seven",
                      components=["tool"], actions=["extend_behavior"],
                      requirements={"REQ-A": "tool build returns seven"}, unknowns=[])
    receipt = h.Receipt(version=1, requirement_test_links={"REQ-A": ["tests/test_vcdoc_100.py::test_default"]})
    acceptance = Path("tests/test_vcdoc_100.py")
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    catalog = Path("docs/usage/catalog.md")
    broken = catalog.read_bytes().replace(b"| tool |", b"| toolXX |")
    stale = h.ReviewedDelta(version=1, revision=base, ticket_digest=h.ticket_digest(ticket),
        rationale="Approve the tool change with a stale catalog to exercise the doc gate",
        extra_paths=["docs/usage/catalog.md"], public_api={},
        file_digests={"docs/usage/catalog.md": hashlib.sha256(broken).hexdigest()})
    blocked = h.compile_ticket(ticket, stale)
    catalog.write_bytes(broken)
    acceptance.write_text("from tool import build\n\ndef test_default(): assert build() == 7\n")
    commit("candidate with stale generated catalog")
    failed = h.verify(blocked["contract"], tmp_path, receipt)
    assert not failed["passed"]
    assert "doc_gates failed" in failed["problems"]
    assert failed["checks"]["doc_gates"]["exit"] == 1
    assert failed["checks"]["pytest"]["exit"] == 0
    acceptance.unlink()
    subprocess.run([sys.executable, "scripts/doc_catalog.py", "render", "."], check=True)
    commit("repair the generated catalog")
    fresh = h.ReviewedDelta(version=1, revision=h.clean_revision(), ticket_digest=h.ticket_digest(ticket),
        rationale="Approve the repaired generated catalog",
        extra_paths=["docs/usage/catalog.md"], public_api={},
        file_digests={"docs/usage/catalog.md": hashlib.sha256(catalog.read_bytes()).hexdigest()})
    repaired = h.compile_ticket(ticket, fresh)
    acceptance.write_text("from tool import build\n\ndef test_default(): assert build() == 7\n")
    commit("candidate with fresh catalog")
    verified = h.verify(repaired["contract"], tmp_path, receipt)
    assert verified["passed"], verified
    assert verified["checks"]["doc_gates"]["exit"] == 0
    declared = ticket.model_copy(update={"id": "VCDOC-101", "checks": ["godot_boundaries"],
                                         "requirements": {"REQ-B": "declared checks fold into contracts"}})
    folded = h.compile_ticket(declared)
    assert "godot_boundaries" in folded["task"]["checks"]
    assert folded["task"]["checks"].count("doc_gates") == 1


def test_charter_records_wiring_and_handoff_exemption():
    text = " ".join((REPO / "docs" / "documentation-charter.md").read_text(encoding="utf-8").split())
    assert "L2 gates are wired into compiled verification" in text
    assert "exempt from the pointer gate" in text
    assert "root `godot.toml` convention" in text
