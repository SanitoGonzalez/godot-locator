extends Node2D

const PLANE_SPEED := 180.0
const LASER_SPEED := 400.0
const LASER_INTERVAL := 0.6
const PLANE_W := 40.0
const PLANE_H := 20.0

var plane_y: float
var lasers: Array[Vector2] = []
var laser_timer := 0.0
var pressing_up := false
var pressing_down := false

func _ready() -> void:
	plane_y = get_viewport_rect().size.y / 2.0

func _process(delta: float) -> void:
	var size := get_viewport_rect().size

	pressing_up = Input.is_key_pressed(KEY_W)
	pressing_down = Input.is_key_pressed(KEY_S)

	if pressing_up:
		plane_y -= PLANE_SPEED * delta
	if pressing_down:
		plane_y += PLANE_SPEED * delta
	plane_y = clampf(plane_y, PLANE_H / 2.0 + 4.0, size.y - PLANE_H / 2.0 - 4.0)

	laser_timer -= delta
	if laser_timer <= 0.0:
		laser_timer = LASER_INTERVAL
		lasers.append(Vector2(80.0 + PLANE_W, plane_y))

	for i in range(lasers.size() - 1, -1, -1):
		lasers[i].x += LASER_SPEED * delta
		if lasers[i].x > size.x + 20.0:
			lasers.remove_at(i)

	queue_redraw()

func _draw() -> void:
	var size := get_viewport_rect().size

	# Background
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.05, 0.05, 0.18))

	# Stars (static decorative lines)
	for i in range(12):
		var sy := 30.0 + i * 46.0
		draw_line(Vector2(0.0, sy), Vector2(size.x, sy), Color(0.2, 0.2, 0.4, 0.3), 1.0)

	# Lasers
	for laser in lasers:
		draw_rect(Rect2(laser.x, laser.y - 3.0, 28.0, 6.0), Color(1.0, 0.3, 0.3))
		draw_rect(Rect2(laser.x, laser.y - 1.0, 28.0, 2.0), Color(1.0, 0.9, 0.9))

	# Plane body
	var px := 80.0
	var py := plane_y
	var body := PackedVector2Array([
		Vector2(px + PLANE_W, py),
		Vector2(px, py - PLANE_H / 2.0),
		Vector2(px - PLANE_W * 0.4, py),
		Vector2(px, py + PLANE_H / 2.0),
	])
	draw_colored_polygon(body, Color(0.4, 0.8, 1.0))
	# Cockpit
	draw_circle(Vector2(px + PLANE_W * 0.5, py), 5.0, Color(0.8, 1.0, 1.0))

	# Arrow indicators
	_draw_arrow(Vector2(size.x - 60.0, size.y - 90.0), true, pressing_up)
	_draw_arrow(Vector2(size.x - 60.0, size.y - 40.0), false, pressing_down)

func _draw_arrow(center: Vector2, is_up: bool, active: bool) -> void:
	var dir := 1.0 if is_up else -1.0
	var tip := center + Vector2(0.0, -18.0 * dir)
	var left := center + Vector2(-14.0, 6.0 * dir)
	var right := center + Vector2(14.0, 6.0 * dir)
	var col := Color(1.0, 0.85, 0.1) if active else Color(0.5, 0.5, 0.6)
	var outline := Color(1.0, 1.0, 1.0, 0.9) if active else Color(0.3, 0.3, 0.4, 0.7)
	draw_colored_polygon(PackedVector2Array([tip, left, right]), col)
	draw_polyline(PackedVector2Array([tip, left, right, tip]), outline, 2.0)
