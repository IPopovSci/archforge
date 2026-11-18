"""Acceptance tests for FEAT-AGENT-RULES-001: external-communication rules
for agents and the guarded upstream filing path."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_agents_md_requires_advance_approval_for_public_posts():
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "External communication" in text
    assert "explicit advance approval" in text
    assert "agent-filed" in text
    assert "credential authorizes reading, not public speech" in text
    assert "plain words rather than tool jargon" in text
    assert "tired reader" in text
    assert ".harness/filings/" in text


def test_upstream_filing_checks_policy_and_defaults_to_manual():
    text = " ".join((REPO / "docs/usage/trail-gdscript-upstream.md")
                    .read_text(encoding="utf-8").split())
    assert "contributing and issue policy" in text
    assert "explicit advance approval" in text
    assert "manual filing by the user" in text
    assert "show the final content and destination once more before sending" in text
