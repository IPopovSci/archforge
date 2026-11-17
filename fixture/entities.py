from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    health: int
    poison: tuple[int, ...] = ()
