"""Acceptance tests for FEAT-PHASES-001: the development-order policy and the
fundamentals-first principle recorded in agent instructions."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_agents_md_records_development_order():
    text = " ".join((REPO / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "Development order: finish the design before field-testing it." in text
    assert "further improvement costs more than it returns" in text
    assert "its own failure list, which is evidence for the next cycle" in text
    assert "Benchmarks and comparisons wait for that point; do not propose them early." in text


def test_agents_md_records_fundamentals_first():
    text = " ".join((REPO / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "Fundamentals first: the harness core stays language-neutral." in text
    assert "pluggable adapters, never as core structure" in text
    assert "Do not shape core design decisions around one language." in text
