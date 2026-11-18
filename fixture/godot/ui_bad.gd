extends CanvasLayer
## Deliberate boundary violation: uses GStats without a declared dependency
## and preloads data.gd undeclared — the GDScript counterpart of the poison
## fixture's forbidden import.

var _data := preload("res://data.gd")
const SHOT_PATH := "E:/Temp/shot.png"

func report(ch: Dictionary) -> String:
	return "hp %s" % str(GStats.max_hp(ch))
