extends VBoxContainer


func _ready() -> void:
	$Submit.pressed.connect(_on_submit_pressed)
	$ClickPad.gui_input.connect(_on_click_pad_input)


func _on_submit_pressed() -> void:
	$Status.text = "submitted: " + $NameInput.text


func _on_click_pad_input(event: InputEvent) -> void:
	if not (event is InputEventMouseButton):
		return
	var mb := event as InputEventMouseButton
	if not mb.pressed:
		return
	if mb.button_index == MOUSE_BUTTON_LEFT and mb.double_click:
		$Status.text = "double-clicked"
	elif mb.button_index == MOUSE_BUTTON_RIGHT:
		$Status.text = "right-clicked"
