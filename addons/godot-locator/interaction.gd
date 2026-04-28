extends Node

## Interactions (click / fill / press_key / …), describe, wait_for, and
## locator resolution. Owned by the `Locator` autoload (see `server.gd`)
## alongside `snapshot.gd`. Holds a back-ref to the snapshot module so it
## can issue refs and embed a fresh tree in interaction responses.

var snapshot_module: Node

# Monotonic counter bumped on every interaction response. Lets clients detect
# drift (e.g. context compaction lost the last-seen tree state) by passing
# their previously-seen value back; mismatches force a full snapshot in
# delta mode.
var _tree_version: int = 1


# --- public API (mirrored on the `Locator` autoload) --------------------------

## Synthesize a left-click at the node's center. `node` must be a Control or Node2D.
func click(node: Node) -> void:
	_push_mouse_click(node, MOUSE_BUTTON_LEFT, false)


## Synthesize a left-click followed by a `double_click=true` left-click.
func double_click(node: Node) -> void:
	_push_mouse_click(node, MOUSE_BUTTON_LEFT, false)
	_push_mouse_click(node, MOUSE_BUTTON_LEFT, true)


## Synthesize a right-click at the node's center.
func right_click(node: Node) -> void:
	_push_mouse_click(node, MOUSE_BUTTON_RIGHT, false)


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


# --- wire handlers ------------------------------------------------------------

func handle_locate(_params: Dictionary) -> Variant:
	return {"todo": "resolve locator chain to refs"}


func handle_count(_params: Dictionary) -> Variant:
	return 0


func handle_click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	click(resolved)
	return _interaction_response(params)


func handle_double_click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	double_click(resolved)
	return _interaction_response(params)


func handle_right_click(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	right_click(resolved)
	return _interaction_response(params)


func handle_hover(_params: Dictionary) -> Variant:
	return {"todo": true}


func handle_focus(_params: Dictionary) -> Variant:
	return {"todo": true}


func handle_fill(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	var text: String = str(params.get("text", ""))
	if not fill(resolved, text):
		return {"__error": "fill: node is not LineEdit/TextEdit (got %s)" % resolved.get_class()}
	return _interaction_response(params)


func handle_press_key(_params: Dictionary) -> Variant:
	return {"todo": true}


func handle_drag_to(_params: Dictionary) -> Variant:
	return {"todo": true}


func handle_scroll(_params: Dictionary) -> Variant:
	return {"todo": true}


# Triage tool: dump the targeted node's exported / editor-visible properties
# plus the raw `_godot_locator_format()` output. Used when an interaction
# produced no observable snapshot diff and the model needs to decide whether
# the handler ran but didn't mutate visible state.
func handle_describe(params: Dictionary) -> Variant:
	var resolved: Variant = _resolve_one(params)
	if resolved is Dictionary:
		return resolved
	var ctrl: Node = resolved

	var props: Dictionary = {}
	for p in ctrl.get_property_list():
		var usage := int(p.get("usage", 0))
		var keep := (usage & PROPERTY_USAGE_SCRIPT_VARIABLE) != 0 \
				 or (usage & PROPERTY_USAGE_EDITOR) != 0
		if not keep:
			continue
		var pname: String = p["name"]
		var v: Variant = ctrl.get(pname)
		# JSON.stringify can't serialize most non-primitive Variants — stringify
		# them to a human-readable repr so the response stays JSON-safe.
		match typeof(v):
			TYPE_NIL, TYPE_BOOL, TYPE_INT, TYPE_FLOAT, TYPE_STRING:
				props[pname] = v
			_:
				props[pname] = str(v)

	var custom: Variant = null
	var custom_method: String = snapshot_module.custom_format_method(ctrl)
	if custom_method != "":
		var cv: Variant = ctrl.call(custom_method)
		if cv is Dictionary:
			custom = cv

	return {
		"class": snapshot_module.class_name_of(ctrl),
		"name": str(ctrl.name),
		"ref": snapshot_module.ref_for(ctrl),
		"path": str(ctrl.get_path()),
		"properties": props,
		"custom_format": custom,
	}


# Poll the locator on `interval_ms` ticks until the predicate holds, or time
# out. Polling — instead of per-predicate signal subscription — keeps the
# implementation simple and works for non-signal-driven state changes
# (e.g. `_process`-updated labels). 50ms intervals are imperceptible.
func handle_wait_for(params: Dictionary) -> Variant:
	var loc: Variant = params.get("locator", null)
	if not (loc is Dictionary):
		return {"__error": "wait_for: 'locator' must be an object"}

	var timeout_ms: int = int(params.get("timeout_ms", 2000))
	var interval_ms: int = int(params.get("interval_ms", 50))

	var condition: Variant = _build_wait_condition(params)
	if condition is Dictionary:
		return condition  # error pass-through
	var pred: Callable = condition

	var deadline := Time.get_ticks_msec() + timeout_ms
	while Time.get_ticks_msec() < deadline:
		var matches := _resolve_locator(loc)
		if pred.call(matches):
			return _interaction_response(params)
		await get_tree().create_timer(interval_ms / 1000.0).timeout

	return {"__error": "wait_for: timeout after %dms — condition not met" % timeout_ms}


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
		if snapshot_module.class_name_of(node) != want and node.get_class() != want:
			return false
	if loc.has("text") and snapshot_module.node_text(node) != str(loc["text"]):
		return false
	if loc.has("ref"):
		var want_ref: String = str(loc["ref"])
		var iid := node.get_instance_id()
		var ref_by_iid: Dictionary = snapshot_module.ref_by_iid
		if not ref_by_iid.has(iid) or "e%d" % ref_by_iid[iid] != want_ref:
			return false
	return true


# --- wait_for predicates ------------------------------------------------------

# Build a predicate from `params`. Returns either a Callable(matches) -> bool
# or a `{"__error": ...}` dict if no condition was specified. Multiple
# conditions on the same call AND-combine.
func _build_wait_condition(params: Dictionary) -> Variant:
	var checks: Array[Callable] = []

	if params.has("count"):
		var want_count: int = int(params["count"])
		checks.append(func(matches): return matches.size() == want_count)

	if bool(params.get("exists", false)):
		checks.append(func(matches): return matches.size() >= 1)

	if bool(params.get("missing", false)):
		checks.append(func(matches): return matches.is_empty())

	if params.has("text"):
		var want_text: String = str(params["text"])
		checks.append(func(matches):
			return matches.size() == 1 and snapshot_module.node_text(matches[0]) == want_text
		)

	if params.has("text_contains"):
		var want_contains: String = str(params["text_contains"])
		checks.append(func(matches):
			return matches.size() == 1 and snapshot_module.node_text(matches[0]).find(want_contains) >= 0
		)

	if checks.is_empty():
		return {"__error": "wait_for: no condition specified (need text/text_contains/count/exists/missing)"}

	return func(matches):
		for c in checks:
			if not c.call(matches):
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
# `Snapshot.render()` which mirrors the wire default of false) — agents acting
# on the snapshot almost always want refs to address nodes in the next call.
func _interaction_response(params: Dictionary) -> Dictionary:
	_tree_version += 1
	var tag_ref: bool = bool(params.get("tag_ref", true))
	return {
		"snapshot": snapshot_module.render(0, true, tag_ref),
		"tree_version": _tree_version,
		"mode": "full",
	}
