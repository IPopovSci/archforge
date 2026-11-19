import json

import pytest

from scripts import benchmark


def test_load_tasks():
    tasks = benchmark.load_tasks()
    assert len(tasks) >= 10
    assert {task["profile"] for task in tasks} >= {"FAST", "STANDARD", "FULL"}
    assert all(task["file"] and task["test_file"] and task["test_command"] for task in tasks)


def test_token_totals():
    usage = [
        {"input": 10, "output": 2, "cacheRead": 4},
        {"input_tokens": 5, "output_tokens": 1, "cached_input_tokens": 3},
    ]
    assert benchmark.token_totals(usage) == {"input": 15, "output": 3, "cached": 7}


def test_prompt_separates_treatments():
    task = {"request": "fix", "file": "app.py"}
    baseline = benchmark._prompt(task, "x", None)
    context = benchmark._prompt(task, "x", [{"pointer": "app.py:L1"}])
    assert "evidence" not in baseline
    assert "evidence" in context


def test_summary_counts_profiles():
    rows = [
        {"treatment":"baseline", "profile":"FAST", "passed":True, "seconds":1.0,
         "tokens":{"input":1,"output":1,"cached":0}},
        {"treatment":"context", "profile":"FULL", "passed":False, "seconds":2.0,
         "tokens":{"input":2,"output":2,"cached":1}},
    ]
    summary = benchmark._summary(rows)
    assert summary["baseline"]["FAST"]["passed"] == 1
    assert summary["context"]["missed_full"] == 1


def test_routed_treatment_is_registered():
    assert "routed" in benchmark.TREATMENTS


def test_routed_context_decision_scales_with_recommendation():
    fast = {"recommendation": "FAST"}
    standard = {"recommendation": "STANDARD"}
    full = {"recommendation": "FULL"}
    assert benchmark._routed_context_decision(fast) is False
    assert benchmark._routed_context_decision(standard) is True
    assert benchmark._routed_context_decision(full) is True
