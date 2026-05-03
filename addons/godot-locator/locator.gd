extends Node

## Runtime locator API. Registered as the `Locator` autoload by the
## EditorPlugin in `plugin.gd`. Holds ref tracking, structured snapshot,
## locator resolution, and input synthesis. The WebSocket transport in
## `server.gd` is a thin child node that delegates wire methods here.

## Custom-format hook. A node implementing `_godot_locator_format() -> Dictionary`
## can contribute extra `{text, attrs, flags}` to its snapshot entry.
## C# users can use the PascalCase `_GodotLocatorFormat()` instead — Godot's
## .NET binding registers public methods under their C# name verbatim.
const FORMAT_METHOD := "_godot_locator_format"
const FORMAT_METHOD_CS := "_GodotLocatorFormat"

const ServerModule := preload("res://addons/godot-locator/server.gd")

## Game-defined context bundled with every snapshot. Set to a Callable
## returning a Dictionary (e.g. `func(): return {"hp": "100/200"}`); the
## result is attached as `snapshot.context`. Non-Dictionary returns and
## invalid callables are silently dropped.
var context_provider: Callable = Callable()

# Stable ref ids: instance_id → sequential ref number, persistent across
# calls so a ref handed out by snapshot keeps pointing at the same node
# for later locate/control calls.
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


## Synthesize a left-click at the node's center. Control or Node2D.
func click(node: Node) -> void:
	_push_mouse_click(node, MOUSE_BUTTON_LEFT, false)


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


# --- wire dispatch ------------------------------------------------------------

func dispatch(method: String, params: Dictionary) -> Variant:
	match method:
		"snapshot": return _handle_snapshot(params)
		"click":    return _handle_click(params)
		"fill":     return _handle_fill(params)
		_: return {"__error": "unknown method: %s" % method}


func _handle_snapshot(params: Dictionary) -> Variant:
	return snapshot(
		int(params.get("depth", 0)),
		bool(params.get("show_invisible", false)),
	)


func _handle_click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	click(resolved)
	return _interaction_response(params)


func _handle_fill(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	var text: String = str(params.get("text", ""))
	if not fill(resolved, text):
		return {"__error": "fill: node is not LineEdit/TextEdit (got %s)" % resolved.get_class()}
	return _interaction_response(params)


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


# Visible text content of a node, for `text:` locator matches.
func _node_text(node: Node) -> String:
	if node is Label or node is Button or node is CheckBox:
		return node.text
	if node is RichTextLabel:
		return (node as RichTextLabel).get_parsed_text()
	return ""


# --- locator resolution -------------------------------------------------------

# Resolve `params.locator` to exactly one node, or return an `__error` dict.
# The control verbs all funnel through here so the "single match required"
# contract from the README is enforced in one place.
func _resolve_one(params: Dictionary) -> Variant:
	var loc: Variant = params.get("locator", null)
	if not (loc is Dictionary):
		return {"__error": "locator must be an object, got %s" % JSON.stringify(loc)}
	var matches := _resolve_locator(loc)
	if matches.is_empty():
		return {"__error": "no matches for locator: %s" % JSON.stringify(loc)}
	if matches.size() > 1:
		return {"__error": "expected a single match, got %d for locator: %s" % [matches.size(), JSON.stringify(loc)]}
	return matches[0]


func _resolve_locator(loc: Dictionary) -> Array:
	var matches: Array = []
	for child in get_tree().root.get_children():
		_walk_match(child, loc, matches)
	return matches


func _walk_match(node: Node, loc: Dictionary, out: Array) -> void:
	if _node_matches(node, loc):
		out.append(node)
	for child in node.get_children():
		_walk_match(child, loc, out)


func _node_matches(node: Node, loc: Dictionary) -> bool:
	if loc.has("name") and str(node.name) != str(loc["name"]):
		return false
	if loc.has("class"):
		var want: String = str(loc["class"])
		if _class_name_of(node) != want and node.get_class() != want:
			return false
	if loc.has("text") and _node_text(node) != str(loc["text"]):
		return false
	if loc.has("ref"):
		var want_ref: String = str(loc["ref"])
		var iid := node.get_instance_id()
		if not _snapshot_ref_by_iid.has(iid) or "e%d" % _snapshot_ref_by_iid[iid] != want_ref:
			return false
	return true


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
# need a follow-up snapshot. `tag_ref` defaults to true here (unlike
# `snapshot()` which mirrors the wire default of false) — agents acting on
# the snapshot almost always want refs to address nodes in the next call.
func _interaction_response(params: Dictionary) -> Dictionary:
	_snapshot_version += 1
	return {
		"snapshot": snapshot(0, false),
		"version": _snapshot_version,
		"mode": "full",
	}
