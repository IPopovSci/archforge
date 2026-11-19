"""Acceptance tests for FEAT-NAMING-001: the Archforge naming rule in agent
instructions and the repository's front-door presentation."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_agents_md_names_the_project_archforge():
    text = " ".join((REPO / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "Naming: this repository's harness is called Archforge." in text
    assert "The bare word harness means an agent harness" in text
    assert "OpenCode, Codex, Claude Code" in text
    assert "Use Archforge in speech, tickets, documents and reports" in text


def test_readme_presents_the_project_as_archforge():
    lines = (REPO / "README.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# Archforge"
    text = " ".join(lines[1:6])
    assert "Archforge is the architecture harness developed in this repository" in text
