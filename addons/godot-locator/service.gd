extends Node

## Runtime locator service. Registered as the `Locator` autoload by the
## EditorPlugin in `godot_locator.gd`. Listens on a local WebSocket and
## answers JSON-RPC-ish requests from an external MCP bridge.

const ENV_PORT := "GODOT_LOCATOR_PORT"
const ENV_HOST := "GODOT_LOCATOR_HOST"
const DEFAULT_PORT := 8282
const DEFAULT_HOST := "127.0.0.1"

## Custom-format hook. A node implementing `_godot_locator_format() -> Dictionary`
## can contribute extra `{text, attrs, flags}` to its snapshot line.
## C# users can use the PascalCase `_GodotLocatorFormat()` instead — Godot's
## .NET binding registers public methods under their C# name verbatim.
const FORMAT_METHOD := "_godot_locator_format"
const FORMAT_METHOD_CS := "_GodotLocatorFormat"

var _server := TCPServer.new()
var _peers: Array[WebSocketPeer] = []
var _port: int = DEFAULT_PORT
var _host: String = DEFAULT_HOST

# Stable ref ids: instance_id → sequential ref number, persistent across calls
# so a ref handed out by snapshot keeps pointing at the same node for later
# locate/control calls.
var _ref_by_iid: Dictionary = {}
var _ref_counter: int = 0


func _ready() -> void:
	var env_port := OS.get_environment(ENV_PORT)
	if env_port != "":
		_port = int(env_port)

	var env_host := OS.get_environment(ENV_HOST)
	if env_host != "":
		_host = env_host

	var err := _server.listen(_port, _host)
	if err != OK:
		push_error("godot-locator: listen on %s:%d failed (%s)" % [_host, _port, error_string(err)])
		set_process(false)
		return

	if _host == "0.0.0.0" or _host == "::" or _host == "*":
		push_warning("godot-locator: bound to %s — service is reachable off-host. Use only on trusted networks." % _host)

	print("godot-locator: ws://%s:%d" % [_host, _port])


func _exit_tree() -> void:
	for peer in _peers:
		peer.close()
	_server.stop()


func _process(_delta: float) -> void:
	while _server.is_connection_available():
		var stream := _server.take_connection()
		var peer := WebSocketPeer.new()
		peer.accept_stream(stream)
		_peers.append(peer)

	for i in range(_peers.size() - 1, -1, -1):
		var peer := _peers[i]
		peer.poll()
		match peer.get_ready_state():
			WebSocketPeer.STATE_OPEN:
				while peer.get_available_packet_count() > 0:
					_handle_packet(peer, peer.get_packet())
			WebSocketPeer.STATE_CLOSED:
				_peers.remove_at(i)


func _handle_packet(peer: WebSocketPeer, data: PackedByteArray) -> void:
	var text := data.get_string_from_utf8()
	var msg: Variant = JSON.parse_string(text)
	if typeof(msg) != TYPE_DICTIONARY:
		_send(peer, {"error": "invalid request"})
		return

	var id: Variant = msg.get("id")
	var method: String = msg.get("method", "")
	var params: Dictionary = msg.get("params", {})

	var result: Variant
	var err: Variant = null
	# Methods can throw via push_error; we wrap each dispatch defensively.
	if method == "":
		err = "missing method"
	else:
		result = _dispatch(method, params)
		if result is Dictionary and result.has("__error"):
			err = result["__error"]
			result = null

	var response := {"id": id}
	if err != null:
		response["error"] = err
	else:
		response["result"] = result
	_send(peer, response)


func _send(peer: WebSocketPeer, payload: Dictionary) -> void:
	peer.send_text(JSON.stringify(payload))


# --- dispatch -----------------------------------------------------------------

func _dispatch(method: String, params: Dictionary) -> Variant:
	match method:
		"snapshot": return _snapshot(params)
		"locate":   return _locate(params)
		"count":    return _count(params)
		"click":           return _click(params)
		"double_click":    return _double_click(params)
		"right_click":     return _right_click(params)
		"hover":           return _hover(params)
		"focus":           return _focus(params)
		"fill":            return _fill(params)
		"press_key":       return _press_key(params)
		"drag_to":         return _drag_to(params)
		"scroll":          return _scroll(params)
		_: return {"__error": "unknown method: %s" % method}


# --- query (stubs, fill in incrementally) -------------------------------------

func _snapshot(params: Dictionary) -> Variant:
	var max_depth: int = int(params.get("depth", 0))
	var skip_invisible: bool = bool(params.get("skip_invisible", true))

	var lines := PackedStringArray()
	for child in get_tree().root.get_children():
		_walk_ui(child, 0, max_depth, skip_invisible, lines)
	return "\n".join(lines)


# Emit only Control nodes. Non-Control ancestors (Window, CanvasLayer, Node2D…)
# are traversed transparently so Controls nested under them still appear, at
# the same depth as their nearest Control ancestor.
func _walk_ui(node: Node, control_depth: int, max_depth: int, skip_invisible: bool, lines: PackedStringArray) -> void:
	if not (node is Control):
		for child in node.get_children():
			_walk_ui(child, control_depth, max_depth, skip_invisible, lines)
		return

	var ctrl: Control = node
	if skip_invisible and not ctrl.is_visible_in_tree():
		return

	var indent := "  ".repeat(control_depth)
	var label := _format_control(ctrl)

	if max_depth > 0 and control_depth >= max_depth - 1:
		lines.append("%s- %s" % [indent, label])
		return

	var children := PackedStringArray()
	for child in node.get_children():
		_walk_ui(child, control_depth + 1, max_depth, skip_invisible, children)

	if children.is_empty():
		lines.append("%s- %s" % [indent, label])
	else:
		lines.append("%s- %s:" % [indent, label])
		lines.append_array(children)


func _format_control(ctrl: Control) -> String:
	var parts := PackedStringArray()
	parts.append(_class_name(ctrl))

	var custom_method := _custom_format_method(ctrl)
	var has_custom: bool = custom_method != ""
	var needs_ref: bool = has_custom or ctrl is LineEdit or ctrl is TextEdit or ctrl is BaseButton
	var node_name := str(ctrl.name)
	if node_name != "" or needs_ref:
		var bits := PackedStringArray()
		if node_name != "":
			bits.append(node_name)
		if needs_ref:
			bits.append("ref=" + _ref_for(ctrl))
		parts.append("[%s]" % " ".join(bits))

	var custom: Dictionary = {}
	if has_custom:
		var v: Variant = ctrl.call(custom_method)
		if v is Dictionary:
			custom = v

	# Positional "text": custom override first, then class defaults.
	var text := ""
	if custom.has("text"):
		text = str(custom["text"])
	elif ctrl is Label or ctrl is Button:
		text = ctrl.text
	elif ctrl is RichTextLabel:
		text = (ctrl as RichTextLabel).get_parsed_text()
	if text != "":
		parts.append('"%s"' % _escape(text))

	if ctrl is LineEdit or ctrl is TextEdit:
		parts.append('placeholder="%s"' % _escape(ctrl.placeholder_text))
		parts.append('text="%s"' % _escape(ctrl.text))

	if custom.has("attrs") and custom["attrs"] is Dictionary:
		var attrs: Dictionary = custom["attrs"]
		for k in attrs:
			parts.append('%s="%s"' % [str(k), _escape(str(attrs[k]))])

	if ctrl is BaseButton and (ctrl as BaseButton).disabled:
		parts.append("disabled")

	if custom.has("flags") and custom["flags"] is Array:
		for f in custom["flags"]:
			parts.append(str(f))

	return " ".join(parts)


func _class_name(node: Node) -> String:
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


func _ref_for(node: Node) -> String:
	var iid := node.get_instance_id()
	if not _ref_by_iid.has(iid):
		_ref_counter += 1
		_ref_by_iid[iid] = _ref_counter
	return "e%d" % _ref_by_iid[iid]


func _escape(s: String) -> String:
	return s.replace("\\", "\\\\").replace('"', '\\"')


func _locate(_params: Dictionary) -> Variant:
	return {"todo": "resolve locator chain to refs"}


func _count(_params: Dictionary) -> Variant:
	return 0


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
		if _class_name(node) != want and node.get_class() != want:
			return false
	if loc.has("ref"):
		var want_ref: String = str(loc["ref"])
		var iid := node.get_instance_id()
		if not _ref_by_iid.has(iid) or "e%d" % _ref_by_iid[iid] != want_ref:
			return false
	return true


# --- control ------------------------------------------------------------------

func _click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	_push_mouse_click(resolved, MOUSE_BUTTON_LEFT, false)
	return null


func _double_click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	_push_mouse_click(resolved, MOUSE_BUTTON_LEFT, false)
	_push_mouse_click(resolved, MOUSE_BUTTON_LEFT, true)
	return null


func _right_click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	_push_mouse_click(resolved, MOUSE_BUTTON_RIGHT, false)
	return null


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


func _hover(_params: Dictionary) -> Variant:
	return {"todo": true}


func _focus(_params: Dictionary) -> Variant:
	return {"todo": true}


func _fill(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	var text: String = str(params.get("text", ""))
	if resolved is LineEdit:
		var le: LineEdit = resolved
		le.grab_focus()
		le.text = text
		le.caret_column = text.length()
		# `text` setter doesn't fire text_changed — emit manually so listeners
		# (e.g. CharCounter) see the new value.
		le.text_changed.emit(text)
		return null
	if resolved is TextEdit:
		var te: TextEdit = resolved
		te.grab_focus()
		te.text = text
		te.text_changed.emit()
		return null
	return {"__error": "fill: node is not LineEdit/TextEdit (got %s)" % resolved.get_class()}


func _press_key(_params: Dictionary) -> Variant:
	return {"todo": true}


func _drag_to(_params: Dictionary) -> Variant:
	return {"todo": true}


func _scroll(_params: Dictionary) -> Variant:
	return {"todo": true}
