extends Node2D

const FONT = preload("res://assets/fonts/VT323-Regular.ttf")
const BACK = preload("res://assets/card_back.svg")
var code := ""
var face_up := false
var vacant := true
var highlighted := false

func _draw() -> void:
	var rect := Rect2(-28, -39, 56, 78)
	if vacant:
		draw_rect(rect, Color("134a3c"))
		draw_rect(rect, Color("47836a"), false, 1)
		return
	draw_rect(Rect2(-25, -35, 56, 78), Color(0, 0, 0, 0.3))
	if not face_up:
		draw_texture_rect(BACK, rect, false)
		return
	draw_rect(rect, Color("ede8d3"))
	draw_rect(rect, Color("f6d577") if highlighted else Color("abaf9f"), false, 2)
	if code.is_empty():
		return
	var suit := code.right(1).to_lower()
	var ink := Color("b6384d") if suit in ["h", "d"] else Color("203446")
	var rank := code.left(-1)
	draw_string(FONT, Vector2(-22, -13), rank, HORIZONTAL_ALIGNMENT_LEFT, -1, 25, ink)
	draw_string(FONT, Vector2(12, 32), rank, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, ink)
	var center := Vector2(0, 8)
	match suit:
		"d":
			draw_colored_polygon(PackedVector2Array([center + Vector2(0,-14), center + Vector2(10,0), center + Vector2(0,14), center + Vector2(-10,0)]), ink)
		"h":
			draw_circle(center + Vector2(-5,-5), 7, ink)
			draw_circle(center + Vector2(5,-5), 7, ink)
			draw_colored_polygon(PackedVector2Array([center + Vector2(-12,-3),center + Vector2(12,-3),center + Vector2(0,13)]), ink)
		"s":
			draw_circle(center + Vector2(-5,2), 7, ink)
			draw_circle(center + Vector2(5,2), 7, ink)
			draw_colored_polygon(PackedVector2Array([center + Vector2(-12,1),center + Vector2(12,1),center + Vector2(0,-15)]), ink)
			draw_rect(Rect2(center + Vector2(-3,2), Vector2(6,14)), ink)
		"c":
			for offset in [Vector2(0,-8),Vector2(-7,1),Vector2(7,1)]:
				draw_circle(center + offset, 7, ink)
			draw_rect(Rect2(center + Vector2(-3,2), Vector2(6,14)), ink)

func reveal(value: String, seconds: float) -> void:
	code = value
	vacant = false
	var tween := create_tween()
	tween.tween_property(self, "scale:x", 0.03, seconds / 2)
	await tween.finished
	face_up = true
	queue_redraw()
	tween = create_tween()
	tween.tween_property(self, "scale:x", 1.0, seconds / 2)
	await tween.finished
