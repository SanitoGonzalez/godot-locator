class_name NumberPad extends Control

const COLS := 3
const ROWS := 3
const CELL := Vector2(56, 56)
const GAP := 4.0

var _selected: Dictionary = {}
var _drag_active := false
var _drag_paints_on := true
var _drag_origin_pos := Vector2.ZERO
var _selection_at_drag_start: Dictionary = {}

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_drag_active = true
			_drag_origin_pos = event.position
			_selection_at_drag_start = _selected.duplicate()
			var n := _cell_at(event.position)
			_drag_paints_on = true if n <= 0 else not _selected.get(n, false)
			_apply_drag_rect(event.position)
		else:
			_drag_active = false
	elif event is InputEventMouseMotion and _drag_active:
		_apply_drag_rect(event.position)

func _apply_drag_rect(current_pos: Vector2) -> void:
	var x_min := minf(_drag_origin_pos.x, current_pos.x)
	var y_min := minf(_drag_origin_pos.y, current_pos.y)
	var x_max := maxf(_drag_origin_pos.x, current_pos.x)
	var y_max := maxf(_drag_origin_pos.y, current_pos.y)
	var step := CELL + Vector2(GAP, GAP)
	var new_sel: Dictionary = _selection_at_drag_start.duplicate()
	for r in ROWS:
		for c in COLS:
			var cx := c * step.x
			var cy := r * step.y
			if cx > x_max or cx + CELL.x < x_min or cy > y_max or cy + CELL.y < y_min:
				continue
			var n := r * COLS + c + 1
			if _drag_paints_on:
				new_sel[n] = true
			else:
				new_sel.erase(n)
	if new_sel.hash() != _selected.hash():
		_selected = new_sel
		_sync_buttons()

func _cell_at(pos: Vector2) -> int:
	var c := int(pos.x / (CELL.x + GAP))
	var r := int(pos.y / (CELL.y + GAP))
	if c < 0 or c >= COLS or r < 0 or r >= ROWS:
		return -1
	var inside := pos - Vector2(c, r) * (CELL + Vector2(GAP, GAP))
	if inside.x > CELL.x or inside.y > CELL.y:
		return -1
	return r * COLS + c + 1

func _sync_buttons() -> void:
	for i in range(1, 10):
		var btn := get_node("Cell%d" % i) as Button
		btn.button_pressed = _selected.get(i, false)

func _godot_locator_format() -> Dictionary:
	var help := "3x3 grid of toggle cells. Drag from one cell to another to select the bounding rectangle; dragging from a selected cell deselects instead. Use the `drag` command between two Cell refs."
	var nums: Array = _selected.keys()

	if nums.is_empty():
		return {"text": "drag and drop to select number buttons", "description": help}

	nums.sort()
	var parts: PackedStringArray = []
	for n in nums:
		parts.append(str(n))
	return {"text": "selected: " + ", ".join(parts), "description": help}
