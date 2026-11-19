"""Acceptance tests for FEAT-DECIDE-ADAPT-001: the Deem-4B advisory adapter
wired behind the landed assess seam over both local transports, constructed
only by an explicit advisory request, with calibrated System One abstention,
recorded consults, and GLiNER's placement carried on the recorded evidence."""
import json
import sys
from pathlib import Path

import pytest

import harness as h
from scripts import shadow_decisions as shadow

REPO = Path(__file__).resolve().parents[1]
PROFILES = ["FAST", "STANDARD", "FULL"]


def _workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("tests").mkdir()
    Path("tach.toml").write_text('source_roots=["."]\n[[modules]]\npath="tool"\ndepends_on=[]\n')
    Path("tool.py").write_text("def build(): return 7\n")


def _typed_body(choice, probabilities):
    return {"answers": {"profile": {"choice": choice, "probabilities": probabilities,
                                    "confidence": probabilities.get(choice, 0.0)}}, "usage": {}}


def _chat_body(text):
    return {"choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1}}


def _stub(monkeypatch, body):
    calls = []

    def fake_post(url, payload, timeout=240):
        calls.append((url, payload))
        return body, 12.5

    monkeypatch.setattr(shadow, "_advisory_post", fake_post)
    return calls


def test_systemone_transport_satisfies_the_advisory_contract(monkeypatch):
    calls = _stub(monkeypatch, _typed_body("FULL", {"FAST": 0.04, "STANDARD": 0.11, "FULL": 0.85}))
    raw = shadow.DeemAdvisory("systemone").decide("rework the compiler schema", PROFILES)
    assert raw["provider"] == "deem-4b-q4km-systemone" and raw["choice"] == "FULL"
    assert raw["probabilities"]["FULL"] >= shadow.DEEM_CONFORMAL_90
    url, payload = calls[0]
    assert url == shadow.DEEM_ENDPOINTS["systemone"]
    assert payload["questions"]["profile"]["criteria"] == shadow.ADVISORY_CRITERIA
    assert payload["reasoning"] == "off"


def test_systemone_abstains_below_the_conformal_threshold(monkeypatch):
    _stub(monkeypatch, _typed_body("STANDARD", {"FAST": 0.34, "STANDARD": 0.40, "FULL": 0.26}))
    raw = shadow.DeemAdvisory("systemone").decide("touch tool.py", PROFILES)
    assert raw["choice"] is None
    assert raw["abstention"] == "below_conformal_threshold"


def test_answers_outside_the_profile_menu_abstain(monkeypatch):
    _stub(monkeypatch, _typed_body("MEDIUM", {"MEDIUM": 0.9, "STANDARD": 0.1}))
    raw = shadow.DeemAdvisory("systemone").decide("touch tool.py", PROFILES)
    assert raw["choice"] is None and raw["abstention"] == "outside_allowed_actions"


def test_chat_transport_parses_a_single_profile_word(monkeypatch):
    calls = _stub(monkeypatch, _chat_body("FULL"))
    provider = shadow.DeemAdvisory("chat", endpoint="http://gpu.local/v1/chat/completions")
    raw = provider.decide("design a new subsystem", PROFILES)
    assert raw["provider"] == "deem-4b-q4km-chat" and raw["choice"] == "FULL"
    assert calls[0][0] == "http://gpu.local/v1/chat/completions"
    assert calls[0][1]["temperature"] == 0
    assert "design a new subsystem" in calls[0][1]["messages"][0]["content"]


def test_chat_abstains_on_an_unparseable_answer(monkeypatch):
    _stub(monkeypatch, _chat_body("Perhaps a deeper look is warranted."))
    raw = shadow.DeemAdvisory("chat").decide("touch tool.py", PROFILES)
    assert raw["choice"] is None and raw["abstention"] == "unparseable_answer"


def test_unknown_protocol_is_rejected():
    with pytest.raises(ValueError, match="carrier-pigeon"):
        shadow.DeemAdvisory("carrier-pigeon")


def test_consults_are_recorded_in_the_decision_log(tmp_path, monkeypatch):
    _workspace(tmp_path, monkeypatch)
    _stub(monkeypatch, _chat_body("STANDARD"))
    row = h.assess("touch tool.py", ["tool.py"], provider=shadow.DeemAdvisory("chat"))
    assert row["provider"] == "deem-4b-q4km-chat" and row["prediction"] == "STANDARD"
    assert row["recommendation"] == "STANDARD" and not row["abstained"]
    logged = json.loads(Path(".harness/decisions.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert logged["provider"] == "deem-4b-q4km-chat" and logged["prediction"] == "STANDARD"


def test_calibrated_abstention_keeps_the_deterministic_floor(tmp_path, monkeypatch):
    _workspace(tmp_path, monkeypatch)
    _stub(monkeypatch, _typed_body("FULL", {"FAST": 0.30, "STANDARD": 0.42, "FULL": 0.28}))
    row = h.assess("touch tool.py", ["tool.py"], provider=shadow.DeemAdvisory("systemone"))
    assert row["floor"] == "STANDARD" and row["recommendation"] == "STANDARD"
    assert row["abstained"] and row["provider"] == "deem-4b-q4km-systemone"
    assert not row["disagreement"]


def test_a_lower_advisory_prediction_never_lowers_the_floor(tmp_path, monkeypatch):
    _workspace(tmp_path, monkeypatch)
    _stub(monkeypatch, _chat_body("FAST"))
    row = h.assess("touch tool.py", ["tool.py"], provider=shadow.DeemAdvisory("chat"))
    assert row["floor"] == "STANDARD" and row["recommendation"] == "STANDARD"
    assert row["prediction"] == "FAST" and row["disagreement"]


def test_transport_failure_records_an_explicit_abstention(tmp_path, monkeypatch):
    _workspace(tmp_path, monkeypatch)

    def unreachable(url, payload, timeout=240):
        raise OSError("server unreachable")

    monkeypatch.setattr(shadow, "_advisory_post", unreachable)
    row = h.assess("touch tool.py", ["tool.py"], provider=shadow.DeemAdvisory("chat"))
    assert row["floor"] == "STANDARD" and row["recommendation"] == "STANDARD"
    assert row["abstained"] and "provider_failed (OSError)" in row["abstention_reason"]


def test_no_advisory_without_the_explicit_request(tmp_path, monkeypatch, capsys):
    _workspace(tmp_path, monkeypatch)

    def untouched(url, payload, timeout=240):
        raise AssertionError("the advisory transport must not be touched")

    monkeypatch.setattr(shadow, "_advisory_post", untouched)
    monkeypatch.setattr(sys, "argv", ["shadow_decisions.py", "--request", "touch tool.py",
                                      "--paths", "tool.py"])
    shadow.main()
    row = json.loads(capsys.readouterr().out)
    assert row["floor"] == "STANDARD" and row["abstained"]
    assert row["abstention_reason"] == "model_unavailable"
    assert not Path(".harness/decisions.jsonl").exists()


def test_advisory_flags_are_rejected_without_the_explicit_request(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["shadow_decisions.py", "--request", "touch tool.py",
                                      "--paths", "tool.py", "--protocol", "chat"])
    with pytest.raises(SystemExit):
        shadow.main()
    assert "--protocol and --endpoint require --advisory" in capsys.readouterr().err


def test_advisory_requires_request_and_paths(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["shadow_decisions.py", "--advisory", "deem"])
    with pytest.raises(SystemExit):
        shadow.main()
    assert "--advisory requires --request and --paths" in capsys.readouterr().err


def test_advisory_rejects_a_gliner_checkpoint(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["shadow_decisions.py", "gliner-dir", "--request",
                                      "touch tool.py", "--paths", "tool.py",
                                      "--advisory", "deem"])
    with pytest.raises(SystemExit):
        shadow.main()
    assert "--advisory cannot be combined with a GLiNER checkpoint" in capsys.readouterr().err


def test_explicit_advisory_request_consults_through_the_seam(tmp_path, monkeypatch, capsys):
    _workspace(tmp_path, monkeypatch)
    _stub(monkeypatch, _chat_body("FULL"))
    monkeypatch.setattr(sys, "argv", ["shadow_decisions.py", "--request",
                                      "rework the tool and its adapter together",
                                      "--paths", "tool.py", "--advisory", "deem",
                                      "--protocol", "chat"])
    shadow.main()
    row = json.loads(capsys.readouterr().out)
    assert row["floor"] == "STANDARD" and row["recommendation"] == "FULL"
    assert row["provider"] == "deem-4b-q4km-chat" and row["prediction"] == "FULL"
    logged = json.loads(Path(".harness/decisions.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert logged == row


def test_gliner_placement_is_recorded_from_measured_evidence():
    ticket = json.loads((REPO / "tickets/FEAT-DECIDE-ADAPT-001.json").read_text(encoding="utf-8"))
    placement = ticket["requirements"]["REQ-ADAPT-C"]
    assert "GLiNER" in placement and "no routing or capability-ranking role" in placement
    assert "cheap frequent binary gates" in placement and "pending the same larger suite" in placement
    assert ticket["unknowns"] == []
    findings = (REPO / "docs/usage/research-results.md").read_text(encoding="utf-8")
    assert "GLiNER stays installed as the cheap-gate candidate" in findings
    assert "demote GLiNER from the routing slot" in findings
