class_name GStats
extends RefCounted
## Sample derived from the 2026-11-18 one-shot experiment code.

static func max_hp(ch: Dictionary) -> float:
	var base: Dictionary = GData.CLASSES[ch["cls"]]
	return 40.0 + 2.0 * ch["attrs"]["vit"] + float(base["hp_bonus"])
