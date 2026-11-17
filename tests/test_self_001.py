import hashlib
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import harness as h


def test_tooling_modules():
    policy = tomllib.loads(Path("tach.toml").read_text())
    modules = {m["path"]: m["depends_on"] for m in policy["modules"]}
    assert modules["harness"] == []
    assert modules["server"] == ["harness"]
    assert "fixture.combat" in modules


def test_review_binding():
    ticket = h.Ticket.model_validate_json(Path("tickets/FEAT-042.json").read_bytes())
    scope = {"fixture/combat.py"}
    review = h.ReviewedDelta(version=1, revision="base", ticket_digest=h.ticket_digest(ticket),
        rationale="Approve the proposed policy", extra_paths=["tach.toml"], public_api={},
        file_digests={"tach.toml": hashlib.sha256(Path("tach.toml").read_bytes()).hexdigest()})
    h._validate_review(review, ticket, "base", scope)
    with pytest.raises(ValueError, match="different revision"):
        h._validate_review(review, ticket, "other", scope)
    with pytest.raises(ValueError, match="different revision or ticket"):
        h._validate_review(review, ticket.model_copy(update={"intent":"different"}), "base", scope)
    with pytest.raises(ValueError, match="reviewed file digests"):
        h._validate_review(review.model_copy(update={"file_digests":{}}), ticket, "base", scope)


def test_signature_gate(tmp_path):
    subprocess.run(["git","init","-q",str(tmp_path)], check=True)
    def revision(source):
        (tmp_path/"mod.py").write_text(source)
        h.git("add","mod.py",cwd=tmp_path)
        h.git("-c","user.name=Test","-c","user.email=test@localhost","commit","-qm","test",cwd=tmp_path)
        return h.git("rev-parse","HEAD",cwd=tmp_path)
    base = revision("def run(x): return x")
    same = revision("def run(x): return x + 1")
    changed = "def run(x, y): return x + y"
    head = revision(changed)
    ticket = h.Ticket.model_validate_json(Path("tickets/FEAT-042.json").read_bytes())
    task = h.Task(version=1, ticket=ticket, revision=base, scope=["mod.py"], acceptance_file="test.py",
                  checks=[], evidence=[])
    assert not h._api_changes(task,same,["mod.py"],tmp_path)
    assert h._api_changes(task,head,["mod.py"],tmp_path)
    review = h.ReviewedDelta(version=1,revision=base,ticket_digest=h.ticket_digest(ticket),
        rationale="Add an operand",extra_paths=[],public_api={"mod.py":h.public_api_digest(changed)})
    assert not h._api_changes(task.model_copy(update={"review":review}),head,["mod.py"],tmp_path)


def test_shadow_is_optional():
    loaded = "torch" in sys.modules
    from scripts.shadow_decisions import compare
    rows = compare(lambda *_: {"workflow":"unknown"})
    assert all(row["prediction"] is None for row in rows)
    assert rows[-1]["enforced"] == "STANDARD" and rows[-1]["expected"] == "FULL"
    assert ("torch" in sys.modules) == loaded


def test_self_hosted_contract(tmp_path, monkeypatch):
    """Real Trail, revision-bound compilation, Tach and two verification outcomes."""
    monkeypatch.chdir(tmp_path)
    h.git("init", "-q")
    Path("tests").mkdir()
    Path(".gitignore").write_text(".harness/\ngraft/\n__pycache__/\n.pytest_cache/\n")
    Path("tach.toml").write_text('source_roots=["."]\n[[modules]]\npath="compiler"\ndepends_on=[]\n')
    Path("compiler.py").write_text("def compile_ticket(value): return value\n")
    def commit(message):
        h.git("add", "-A")
        h.git("-c","user.name=Test","-c","user.email=test@localhost","commit","-qm",message)
    commit("baseline")
    base = h.clean_revision()
    ticket = h.Ticket(version=1,id="SELF-100",intent="compile_ticket accepts a default value",
        components=["compiler"],actions=["extend_behavior"],requirements={"REQ-A":"Default to zero"},unknowns=[])
    source = "def compile_ticket(value=0): return value\n"
    review = h.ReviewedDelta(version=1,revision=base,ticket_digest=h.ticket_digest(ticket),
        rationale="Approve optional argument",extra_paths=[],public_api={"compiler.py":h.public_api_digest(source)})
    plain = h.compile_ticket(ticket)
    approved = h.compile_ticket(ticket, review)
    assert any(item["pointer"].startswith("compiler.py") for item in approved["task"]["evidence"])
    Path("compiler.py").write_text(source)
    Path("tests/test_self_100.py").write_text("from compiler import compile_ticket\n"
        "def test_default(): assert compile_ticket() == 0\n")
    commit("implement approved signature")
    receipt = h.Receipt(version=1,requirement_test_links={"REQ-A":["tests/test_self_100.py::test_default"]})
    assert "Unapproved public interface" in h.verify(plain["contract"], tmp_path, receipt)["problems"][0]
    # Nested pytest should receive only this synthetic repository.
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    verified = h.verify(approved["contract"], tmp_path, receipt)
    assert verified["passed"], verified

    next_base = h.clean_revision()
    next_ticket = ticket.model_copy(update={"id":"SELF-101", "components":["review_summary"],
        "intent":"Expose review summary", "requirements":{"REQ-B":"Return an empty review count"}})
    with pytest.raises(ValueError, match="component references"):
        h.compile_ticket(next_ticket)
    policy = Path("tach.toml").read_bytes() + b'\n[[modules]]\npath="review_summary"\ndepends_on=[]\n'
    source = "def review_count(): return 0\n"
    delta = h.ReviewedDelta(version=1, revision=next_base, ticket_digest=h.ticket_digest(next_ticket),
        rationale="Create an independent review summary module", extra_paths=["review_summary.py","tach.toml"],
        public_api={"review_summary.py":h.public_api_digest(source)},
        file_digests={"tach.toml":hashlib.sha256(policy).hexdigest()})
    new_contract = h.compile_ticket(next_ticket, delta)
    Path("review_summary.py").write_text(source)
    Path("tach.toml").write_bytes(policy)
    Path("tests/test_self_101.py").write_text("from review_summary import review_count\n"
        "def test_count(): assert review_count() == 0\n")
    commit("implement independently reviewed module")
    links = h.Receipt(version=1,requirement_test_links={"REQ-B":["tests/test_self_101.py::test_count"]})
    verified = h.verify(new_contract["contract"],tmp_path,links)
    assert verified["passed"], verified
    # An extra dependency-policy edit requires a new review even when tests still pass.
    with Path("tach.toml").open("a") as f:
        f.write("\n# additional change\n")
    commit("exercise reviewed policy drift")
    assert any("reviewed content" in p for p in h.verify(new_contract["contract"],tmp_path,links)["problems"])
