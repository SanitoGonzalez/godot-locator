class_name CharCounter extends Control

const MAX_CHARS: int = 20

var current: int = 0


func _ready() -> void:
	var input := get_node_or_null("../NameInput") as LineEdit
	if input != null:
		current = input.text.length()
		input.text_changed.connect(_on_text_changed)


func _on_text_changed(new_text: String) -> void:
	current = new_text.length()


func _godot_locator_format() -> Dictionary:
	return {
		"text": "%d/%d" % [current, MAX_CHARS],
		"attrs": {"max": str(MAX_CHARS)},
		"flags": ["full"] if current >= MAX_CHARS else [],
	}
