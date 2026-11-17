from fixture.entities import Entity


def advance(entity: Entity) -> Entity:
    return Entity(entity.health - len(entity.poison), tuple(n - 1 for n in entity.poison if n > 1))
