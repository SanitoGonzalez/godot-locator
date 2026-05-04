extends Node

## Runtime locator API. Registered as the `Locator` autoload by the
## EditorPlugin in `plugin.gd`. Holds ref tracking, structured snapshot,
## ref resolution, and input synthesis. The WebSocket transport in
## `server.gd` is a thin child node that delegates wire methods here.

## Custom-format hook. A node implementing `_godot_locator_format() -> Dictionary`
## can contribute extra `{text, attrs, flags}` to its snapshot entry.
## C# users can use the PascalCase `_GodotLocatorFormat()` instead — Godot's
## .NET binding registers public methods under their C# name verbatim.
const FORMAT_METHOD := "_godot_locator_format"
const FORMAT_METHOD_CS := "_GodotLocatorFormat"

## Env flag that opts a game process into the `evaluate` wire method.
## Eval has full GDScript-expression access to the running game; gating it
## prevents accidental enablement in shipping builds.
const EVAL_ENV := "GODOT_LOCATOR_EVAL_ENABLED"

const ServerModule := preload("res://addons/godot-locator/server.gd")

## Game-defined context bundled with every snapshot. Set to a Callable
## returning a Dictionary (e.g. `func(): return {"hp": "100/200"}`); the
## result is attached as `snapshot.context`. Non-Dictionary returns and
## invalid callables are silently dropped.
var context_provider: Callable = Callable()

# Stable ref ids: instance_id → sequential ref number, persistent across
# calls so a ref handed out by snapshot keeps pointing at the same node
# for later click/fill calls.
var _snapshot_ref_by_iid: Dictionary = {}
var _snapshot_ref_counter: int = 0
# Monotonic counter bumped on every interaction response. Lets users detect drift
var _snapshot_version: int = 1

var _server: Node


func _ready() -> void:
	_server = ServerModule.new()
	_server.name = "Server"
	_server.locator = self
	add_child(_server)


## Build a structured snapshot of the SceneTree. 
## Only `Control` nodes are emitted; non-Control parents are walked through transparently.
func snapshot(depth: int = 0, show_invisible: bool = false) -> Dictionary:
	var nodes: Array = []
	for child in get_tree().root.get_children():
		_snapshot_walk(child, 0, depth, show_invisible, nodes)
	var result: Dictionary = {"tree": nodes}
	
	if context_provider.is_valid():
		var v: Variant = context_provider.call()
		if v is Dictionary:
			result["context"] = v
	
	return result


## Synthesize a click at the node's center. Control or Node2D.
## `button` is a Godot `MOUSE_BUTTON_*` constant.
func click(node: Node, button: int = MOUSE_BUTTON_LEFT) -> void:
	_push_mouse_click(node, button, false)


## Synthesize a double-click at the node's center. Control or Node2D.
## `button` is a Godot `MOUSE_BUTTON_*` constant.
func double_click(node: Node, button: int = MOUSE_BUTTON_LEFT) -> void:
	_push_mouse_click(node, button, true)


## Replace `node.text` with `text` (clears, then types). `node` must be a
## LineEdit or TextEdit — calling on anything else returns false.
func fill(node: Node, text: String) -> bool:
	if node is LineEdit:
		var le: LineEdit = node
		le.grab_focus()
		le.text = text
		le.caret_column = text.length()
		# `text` setter doesn't fire text_changed — emit manually so listeners
		# (e.g. CharCounter) see the new value.
		le.text_changed.emit(text)
		return true
	if node is TextEdit:
		var te: TextEdit = node
		te.grab_focus()
		te.text = text
		te.text_changed.emit()
		return true
	return false


## Synthesize keyboard input into the currently-focused Control. Pushes one
## InputEventKey per character with `unicode` set; LineEdit/TextEdit consume
## these via their normal `_gui_input` path. Returns false if no Control is
## focused.
func type(text: String) -> bool:
	var vp := get_viewport()
	if vp == null or vp.gui_get_focus_owner() == null:
		return false
	for c in text:
		var event := InputEventKey.new()
		event.pressed = true
		event.unicode = c.unicode_at(0)
		vp.push_input(event)
	return true


## Synthesize a press+release of a single keyboard key. `key_name` accepts
## anything `OS.find_keycode_from_string` understands ("Enter", "Escape",
## "F1", "A", "Left"), case-insensitively. Also accepts `arrow*` aliases
## ("arrowleft" → Left). Returns false on unknown names.
func press(key_name: String) -> bool:
	var keycode := _parse_key(key_name)
	if keycode == 0:
		return false
	var vp := get_viewport()
	if vp == null:
		return false
	var down := InputEventKey.new()
	down.keycode = keycode
	down.physical_keycode = keycode
	down.pressed = true
	var up := InputEventKey.new()
	up.keycode = keycode
	up.physical_keycode = keycode
	up.pressed = false
	vp.push_input(down)
	vp.push_input(up)
	return true


## Drive a Godot input action by name. `mode` is "tap" (default; press +
## release on the same call), "hold" (press only — leaves the action held),
## or "release". Returns false if the action isn't in `InputMap`.
func action(name: String, mode: String = "tap") -> bool:
	if not InputMap.has_action(name):
		return false
	match mode:
		"tap":
			Input.action_press(name)
			Input.action_release(name)
		"hold":
			Input.action_press(name)
		"release":
			Input.action_release(name)
		_:
			return false
	return true


## Capture a viewport screenshot. When `target` is a Control, crops to its
## global rect. `format` is "png" or "jpeg". Returns a dict
## `{format, width, height, data}` where `data` is base64-encoded bytes.
func screenshot(target: Node = null, format: String = "png") -> Dictionary:
	var vp := get_viewport()
	if vp == null:
		return {"__error": "no viewport"}
	var img: Image = vp.get_texture().get_image()
	if target != null and target is Control:
		var rect := (target as Control).get_global_rect()
		var vp_rect := Rect2(Vector2.ZERO, vp.get_visible_rect().size)
		rect = rect.intersection(vp_rect)
		if rect.size.x <= 0 or rect.size.y <= 0:
			return {"__error": "target rect is outside the viewport"}
		img = img.get_region(Rect2i(rect.position, rect.size))
	var bytes: PackedByteArray
	match format:
		"png":  bytes = img.save_png_to_buffer()
		"jpeg": bytes = img.save_jpg_to_buffer(0.85)
		_: return {"__error": "format must be png or jpeg, got %s" % format}
	return {
		"format": format,
		"width": img.get_width(),
		"height": img.get_height(),
		"data": Marshalls.raw_to_base64(bytes),
	}


## Evaluate a single GDScript expression. When `node` is provided, exposes
## it as the input variable `node`. Gated by `GODOT_LOCATOR_EVAL_ENABLED`
## — eval has full game-state access, so it must be opted into per process.
## Note: GDScript syntax only; on C# projects use `node.get_name()`, not
## `node.GetName()`.
func evaluate(code: String, node: Node = null) -> Variant:
	if OS.get_environment(EVAL_ENV).to_lower() != "true":
		return {"__error": "eval is disabled — set %s=true on the game process to enable" % EVAL_ENV}
	var expr := Expression.new()
	var inputs := PackedStringArray()
	var values: Array = []
	if node != null:
		inputs.append("node")
		values.append(node)
	var parse_err := expr.parse(code, inputs)
	if parse_err != OK:
		return {"__error": "parse: %s" % expr.get_error_text()}
	var result: Variant = expr.execute(values, self, true)
	if expr.has_execute_failed():
		return {"__error": "execute: %s" % expr.get_error_text()}
	return {"value": result}


func _parse_key(name: String) -> int:
	var n := name.strip_edges().to_lower()
	if n == "":
		return 0
	if n.begins_with("arrow"):
		n = n.substr(5)
	# OS.find_keycode_from_string is case-sensitive on the leading char for
	# multi-letter names ("Enter" works, "enter" doesn't), so capitalize.
	var k := OS.find_keycode_from_string(n.capitalize())
	if k == 0:
		return 0
	return k & KEY_CODE_MASK


# --- wire dispatch ------------------------------------------------------------

func dispatch(method: String, params: Dictionary) -> Variant:
	match method:
		"snapshot":     return _handle_snapshot(params)
		"click":        return _handle_click(params)
		"double_click": return _handle_double_click(params)
		"fill":         return _handle_fill(params)
		"type":         return _handle_type(params)
		"press":        return _handle_press(params)
		"action":       return _handle_action(params)
		"screenshot":   return _handle_screenshot(params)
		"evaluate":     return _handle_evaluate(params)
		_: return {"__error": "unknown method: %s" % method}


func _handle_snapshot(params: Dictionary) -> Variant:
	return snapshot(
		int(params.get("depth", 0)),
		bool(params.get("show_invisible", false)),
	)


func _handle_click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_ref(params)
	if resolved is Dictionary:
		return resolved
	var button: Variant = _parse_button(params)
	if button is Dictionary:
		return button
	click(resolved, button)
	return _interaction_response(params)


func _handle_double_click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_ref(params)
	if resolved is Dictionary:
		return resolved
	var button: Variant = _parse_button(params)
	if button is Dictionary:
		return button
	double_click(resolved, button)
	return _interaction_response(params)


func _parse_button(params: Dictionary) -> Variant:
	var name: String = str(params.get("button", "left"))
	match name:
		"left":   return MOUSE_BUTTON_LEFT
		"right":  return MOUSE_BUTTON_RIGHT
		"middle": return MOUSE_BUTTON_MIDDLE
	return {"__error": "button must be left/right/middle, got %s" % name}


func _handle_fill(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_ref(params)
	if resolved is Dictionary:
		return resolved
	var text: String = str(params.get("text", ""))
	if not fill(resolved, text):
		return {"__error": "fill: node is not LineEdit/TextEdit (got %s)" % resolved.get_class()}
	return _interaction_response(params)


func _handle_type(params: Dictionary) -> Variant:
	var text: String = str(params.get("text", ""))
	if not type(text):
		return {"__error": "type: no Control is focused to receive keyboard input"}
	return _interaction_response(params)


func _handle_press(params: Dictionary) -> Variant:
	var key_name: String = str(params.get("key", ""))
	if key_name == "":
		return {"__error": "key is required (e.g. \"enter\", \"escape\", \"arrowleft\", \"f1\")"}
	if not press(key_name):
		return {"__error": "press: unknown key \"%s\"" % key_name}
	return _interaction_response(params)


func _handle_action(params: Dictionary) -> Variant:
	var action_name: String = str(params.get("name", ""))
	if action_name == "":
		return {"__error": "action name is required"}
	if not InputMap.has_action(action_name):
		return {"__error": "unknown action: \"%s\" (not in InputMap)" % action_name}
	var mode: String = str(params.get("mode", "tap"))
	if not action(action_name, mode):
		return {"__error": "action mode must be tap/hold/release, got \"%s\"" % mode}
	return _interaction_response(params)


func _handle_screenshot(params: Dictionary) -> Variant:
	var target: Node = null
	var ref_val: Variant = params.get("ref", null)
	if ref_val is String and ref_val != "":
		var resolved: Variant = _resolve_ref(params)
		if resolved is Dictionary:
			return resolved
		target = resolved
	var fmt: String = str(params.get("format", "png"))
	return screenshot(target, fmt)


func _handle_evaluate(params: Dictionary) -> Variant:
	var code: String = str(params.get("expression", ""))
	if code == "":
		return {"__error": "expression is required"}
	var node: Node = null
	var ref_val: Variant = params.get("ref", null)
	if ref_val is String and ref_val != "":
		var resolved: Variant = _resolve_ref(params)
		if resolved is Dictionary:
			return resolved
		node = resolved
	return evaluate(code, node)


func _snapshot_walk(node: Node, depth: int, max_depth: int, show_invisible: bool, out: Array) -> void:
	if not (node is Control):
		for child in node.get_children():
			_snapshot_walk(child, depth, max_depth, show_invisible, out)
		return

	var control: Control = node
	if !show_invisible and not control.is_visible_in_tree():
		return

	var entry := _snapshot_format(control)
	var children: Array = []
	if max_depth == 0 or depth < max_depth - 1:
		for child in node.get_children():
			_snapshot_walk(child, depth + 1, max_depth, show_invisible, children)
	entry["children"] = children
	out.append(entry)


func _snapshot_format(control: Control) -> Dictionary:
	var entry: Dictionary = {"class": _class_name_of(control)}

	var node_name := str(control.name)
	if node_name != "":
		entry["name"] = node_name

	var method := _custom_format_method(control)
	var has_custom := method != ""
	var custom: Dictionary = {}
	if has_custom:
		var v: Variant = control.call(method)
		if v is Dictionary:
			custom = v

	# Positional text: custom override → Label/Button → RichTextLabel →
	# LineEdit/TextEdit current content (the user-meaningful "current value").
	var text := ""
	if custom.has("text"):
		text = str(custom["text"])
	elif control is Label or control is Button:
		text = control.text
	elif control is RichTextLabel:
		text = (control as RichTextLabel).get_parsed_text()
	elif control is LineEdit or control is TextEdit:
		text = control.text
	if text != "":
		entry["text"] = text

	var needs_ref: bool = has_custom or control is LineEdit or control is TextEdit or control is BaseButton
	if needs_ref:
		entry["ref"] = _snapshot_ref(control)

	var attrs: Dictionary = {}
	if control is LineEdit or control is TextEdit:
		var ph: String = control.placeholder_text
		if ph != "":
			attrs["placeholder"] = ph
	if custom.has("attrs") and custom["attrs"] is Dictionary:
		var custom_attrs: Dictionary = custom["attrs"]
		for k in custom_attrs:
			var raw: Variant = custom_attrs[k]
			if raw == null:
				continue
			attrs[str(k)] = raw
	if not attrs.is_empty():
		entry["attrs"] = attrs

	var flags: Array = []
	if control is BaseButton and (control as BaseButton).disabled:
		flags.append("disabled")
	if custom.has("flags") and custom["flags"] is Array:
		for f in custom["flags"]:
			flags.append(str(f))
	if not flags.is_empty():
		entry["flags"] = flags

	return entry


func _snapshot_ref(node: Node) -> String:
	var iid := node.get_instance_id()
	if not _snapshot_ref_by_iid.has(iid):
		_snapshot_ref_counter += 1
		_snapshot_ref_by_iid[iid] = _snapshot_ref_counter
	return "e%d" % _snapshot_ref_by_iid[iid]


func _class_name_of(node: Node) -> String:
	var script := node.get_script()
	if script is Script:
		var s: Script = script
		# GDScript fills get_global_name() from `class_name`.
		var gname: String = s.get_global_name()
		if gname != "":
			return gname
		var path := s.resource_path
		if path != "":
			# Catches GDScripts registered via the editor without `class_name`.
			for entry in ProjectSettings.get_global_class_list():
				if entry.get("path", "") == path:
					return entry.get("class", "")
			# CSharpScript: in 4.6 neither get_global_name() nor the global
			# class list expose the user class. Fall back to the C# convention
			# "one public class per file, name matches the filename".
			if path.ends_with(".cs"):
				return path.get_file().get_basename()
	return node.get_class()


func _custom_format_method(node: Node) -> String:
	if node.has_method(FORMAT_METHOD):
		return FORMAT_METHOD
	if node.has_method(FORMAT_METHOD_CS):
		return FORMAT_METHOD_CS
	return ""


# --- ref resolution -----------------------------------------------------------

# Resolve `params.ref` to a live node, or return an `__error` dict.
# Refs are handed out by `snapshot()` and survive across calls until the
# referenced node is freed.
func _resolve_ref(params: Dictionary) -> Variant:
	var ref: Variant = params.get("ref", null)
	if not (ref is String) or ref == "":
		return {"__error": "ref is required (e.g. \"e15\")"}
	for iid in _snapshot_ref_by_iid:
		if "e%d" % _snapshot_ref_by_iid[iid] == ref:
			var node: Object = instance_from_id(iid)
			if node == null or not (node is Node):
				return {"__error": "ref %s points to a freed node" % ref}
			return node
	return {"__error": "unknown ref: %s" % ref}


# --- input synthesis ----------------------------------------------------------

func _push_mouse_click(node: Node, button: int, double: bool) -> void:
	var pos := _node_center(node)
	var press := InputEventMouseButton.new()
	press.button_index = button
	press.pressed = true
	press.position = pos
	press.global_position = pos
	press.button_mask = 1 << (button - 1)
	press.double_click = double

	var release := InputEventMouseButton.new()
	release.button_index = button
	release.pressed = false
	release.position = pos
	release.global_position = pos

	var vp := node.get_viewport()
	if vp == null:
		vp = get_viewport()
	# in_local_coords=true: Control.get_global_rect() is already viewport-local.
	vp.push_input(press, true)
	vp.push_input(release, true)


func _node_center(node: Node) -> Vector2:
	if node is Control:
		var rect := (node as Control).get_global_rect()
		return rect.position + rect.size * 0.5
	if node is Node2D:
		return (node as Node2D).global_position
	return Vector2.ZERO


# --- response builder ---------------------------------------------------------

# Bundle the post-interaction state into a single response so callers don't
# need a follow-up snapshot.
func _interaction_response(params: Dictionary) -> Dictionary:
	_snapshot_version += 1
	return {
		"snapshot": snapshot(0, false),
		"version": _snapshot_version,
		"mode": "full",
	}
