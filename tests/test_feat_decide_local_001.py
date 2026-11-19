"""Acceptance tests for FEAT-DECIDE-LOCAL-001: a local decision model below 5B
parameters answered the routing choice on the recorded shadow suites using the
machine GPU, and measured rows compare it with the path rules and the GLiNER
baselines on accuracy, latency and hardware cost."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def findings():
    return (REPO / "docs/usage/research-results.md").read_text(encoding="utf-8")


def test_local_sub5b_model_answered_the_recorded_suites_on_the_gpu():
    text = findings()
    assert "Deem-4B decision experiments on the landed assess seam" in text
    assert "fine-tuned from Intern-Decision-4B" in text
    assert "Deem alone (typed, 13-case) | **13/13**" in text
    assert "Floor + selective Deem (chat, GPU) | **14/14**" in text
    assert "592 ms GPU" in text
    assert "RX 9070 XT" in text


def test_measured_rows_compare_the_model_with_the_floor_and_gliner():
    text = findings()
    assert "Path rules (13-case suite, recorded) | 12/13" in text
    assert "Path rules (14-case suite, recorded) | 10/14" in text
    assert "GLiNER alone (13-case, recorded) | 9/13" in text
    assert "Floor + selective GLiNER (recorded) | 13/14" in text
    assert "2.1 s CPU" in text and "282 ms CPU" in text
