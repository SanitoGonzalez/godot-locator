extends Control

var submitted_name: String = ""
var submitted_email: String = ""

@onready var name_input: LineEdit = $MarginContainer/VBoxContainer/FormPanel/FormBox/NameInput
@onready var email_input: LineEdit = $MarginContainer/VBoxContainer/FormPanel/FormBox/EmailInput
@onready var submit_button: Button = $MarginContainer/VBoxContainer/Actions/SubmitButton
@onready var cancel_button: Button = $MarginContainer/VBoxContainer/Actions/CancelButton
@onready var close_button: Button = $MarginContainer/VBoxContainer/Header/CloseButton

func _ready() -> void:
	Locator.context_provider = func():
		return {"description": "This is a custom context description", "emoji": "😎"}
	
	name_input.text_changed.connect(_on_input_changed)
	email_input.text_changed.connect(_on_input_changed)
	cancel_button.pressed.connect(_on_cancel)
	submit_button.pressed.connect(_on_submit)
	close_button.pressed.connect(_on_close)
	
func _godot_locator_format() -> Dictionary:
	return {
		"text": "this is a custom text",
		"attrs": {"submitted_name": submitted_name, "submitted_email": submitted_email},
		"flags": ["this is a custom tag"],
	}

func _on_input_changed(_text: String) -> void:
	submit_button.disabled = name_input.text.is_empty() or email_input.text.is_empty()

func _on_cancel() -> void:
	name_input.clear()
	email_input.clear()
	submit_button.disabled = true

func _on_close() -> void:
	get_tree().quit()

func _on_submit() -> void:
	submitted_name = name_input.text
	submitted_email = email_input.text
	name_input.clear()
	email_input.clear()
