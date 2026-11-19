"""Acceptance tests for FEAT-DECIDE-SEAM-001: the advisory assessment seam
with a deterministic floor, a provider consulted only in the ambiguous
STANDARD band, explicit abstentions and the recorded decision log."""
import json
import subprocess
import sys
from pathlib import Path

import harness as h

REPO = Path(__file__).resolve().parents[1]

FIELDS = {"request", "paths", "observed", "floor", "provider", "prediction",
          "abstained", "abstention_reason", "disagreement", "recommendation"}


class StubProvider:
    def __init__(self, choice="FULL", error=None):
        self.choice = choice
        self.error = error
        self.calls = []

    def decide(self, request, allowed_actions):
        self.calls.append((request, list(allowed_actions)))
        if self.error:
            raise self.error
        return {"choice": self.choice, "provider": "stub-v1"}


def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("tests").mkdir()
    Path("tach.toml").write_text('source_roots=["."]\n[[modules]]\npath="tool"\ndepends_on=[]\n')
    Path("tool.py").write_text("def build(): return 7\n")


def commit(message):
    h.git("add", "-A")
    h.git("-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-qm", message)


def test_docs_only_floor_returns_without_a_model_call(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    stub = StubProvider()
    row = h.assess("docs wording tweak", ["README.md"], provider=stub)
    assert row["floor"] == "FAST"
    assert row["recommendation"] == "FAST"
    assert row["provider"] is None and row["prediction"] is None
    assert not row["abstained"] and row["abstention_reason"] is None
    assert stub.calls == []


def test_mandatory_full_floor_ignores_lower_advisory(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    stub = StubProvider(choice="FAST")
    row = h.assess("two components move together", ["tool.py", "notes.md"], provider=stub)
    assert row["floor"] == "FULL" and row["recommendation"] == "FULL"
    assert stub.calls == [] and row["prediction"] is None and not row["abstained"]


def test_tests_only_standard_skips_the_provider(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    stub = StubProvider(choice="FULL")
    row = h.assess("extend a test", ["tests/test_tool.py"], provider=stub)
    assert row["floor"] == "STANDARD" and row["recommendation"] == "STANDARD"
    assert stub.calls == [] and not row["abstained"]


def test_ambiguous_standard_without_provider_abstains_explicitly(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    row = h.assess("touch tool.py", ["tool.py"])
    assert row["floor"] == "STANDARD" and row["recommendation"] == "STANDARD"
    assert row["abstained"] and row["abstention_reason"] == "model_unavailable"
    assert row["provider"] is None and row["prediction"] is None and not row["disagreement"]


def test_failing_provider_abstains_with_reason(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    stub = StubProvider(error=RuntimeError("model down"))
    row = h.assess("touch tool.py", ["tool.py"], provider=stub)
    assert row["floor"] == "STANDARD" and row["recommendation"] == "STANDARD"
    assert row["abstained"] and "provider_failed" in row["abstention_reason"]
    assert "RuntimeError" in row["abstention_reason"]
    assert stub.calls == [("touch tool.py", ["FAST", "STANDARD", "FULL"])]


def test_provider_promotion_records_disagreement(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    stub = StubProvider(choice="FULL")
    row = h.assess("touch tool.py", ["tool.py"], provider=stub)
    assert row["provider"] == "stub-v1" and row["prediction"] == "FULL"
    assert row["disagreement"] and not row["abstained"]
    assert row["floor"] == "STANDARD" and row["recommendation"] == "FULL"


def test_observed_full_impact_promotes_the_floor_without_a_model_call(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    h.git("init", "-q")
    commit("baseline")
    base = h.clean_revision()
    Path("tool.py").write_text("def build(artifact): return artifact\n")
    stub = StubProvider(choice="FAST")
    row = h.assess("change the tool signature", ["tool.py"], base=base, provider=stub)
    assert row["observed"] == "FULL" and row["floor"] == "FULL"
    assert row["recommendation"] == "FULL" and stub.calls == []


def test_each_assessment_appends_one_decision_log_line(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    log = Path(".harness/decisions.jsonl")
    h.assess("docs wording tweak", ["README.md"])
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and set(rows[0]) == FIELDS
    assert rows[0]["request"] == "docs wording tweak" and rows[0]["paths"] == ["README.md"]
    h.assess("touch tool.py", ["tool.py"])
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2 and rows[1]["abstained"] is True


def test_cli_assess_returns_the_recorded_row(tmp_path, monkeypatch):
    workspace(tmp_path, monkeypatch)
    h.git("init", "-q")
    commit("baseline")
    base = h.clean_revision()
    done = subprocess.run([sys.executable, str(REPO / "harness.py"), "assess",
                           "touch tool.py", "tool.py", "--base", base],
                          capture_output=True, encoding="utf-8", cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    row = json.loads(done.stdout)
    assert row["request"] == "touch tool.py" and row["paths"] == ["tool.py"]
    assert row["observed"] is None and row["floor"] == "STANDARD"
    assert row["abstained"] and row["abstention_reason"] == "model_unavailable"
    lines = Path(".harness/decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and json.loads(lines[0]) == row
