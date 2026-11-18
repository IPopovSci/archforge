class_name GData
extends RefCounted
## Sample derived from the 2026-11-18 one-shot experiment code.

const CLASSES := {
	"vanguard": {"hp_bonus": 15.0, "mp_bonus": 0.0},
	"arcanist": {"hp_bonus": 0.0, "mp_bonus": 20.0},
}

static func xp_next(level: int) -> int:
	return int(floor(100.0 * pow(float(level), 1.55)))
