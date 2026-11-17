import pytest
from pydantic import ValidationError

from harness import RuleProvider, Ticket, profile


@pytest.mark.parametrize(("paths", "expected"), [
    (["README.md"], "FAST"),
    (["fixture/combat.py", "tests/test_regression.py"], "STANDARD"),
    (["fixture/entities.py", "fixture/combat.py"], "FULL"),
    (["project_example/lines-master-design-bible.md"], "FULL"),
    (["AGENTS.md"], "FULL"),
    (["README.md", "tach.toml"], "FULL"),
])
def test_route(paths, expected):
    assert profile(paths) == expected


def test_mandatory_promotion():
    with pytest.raises(ValueError):
        RuleProvider().decide(["tach.toml"], ["FAST", "STANDARD"])


def test_invalid_ticket():
    with pytest.raises(ValidationError):
        Ticket.model_validate({"version": 1, "checks": []})
