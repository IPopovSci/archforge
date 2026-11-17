from dataclasses import replace

from fixture.entities import Entity


def apply_poison(entity: Entity) -> Entity:
    return replace(entity, poison=(5,))
