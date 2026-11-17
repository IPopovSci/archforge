from fixture.entities import Entity
from fixture.turn_lifecycle import advance


def test_unaffected_entity():
    assert advance(Entity(10)) == Entity(10)
