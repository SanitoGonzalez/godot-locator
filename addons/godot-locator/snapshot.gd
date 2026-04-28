extends Node

## Snapshot rendering + ref tracking. Owned by the `Locator` autoload
## (see `server.gd`) alongside `interaction.gd`.

## Custom-format hook. A node implementing `_godot_locator_format() -> Dictionary`
## can contribute extra `{text, attrs, flags}` to its snapshot line.
## C# users can use the PascalCase `_GodotLocatorFormat()` instead — Godot's
## .NET binding registers public methods under their C# name verbatim.
const FORMAT_METHOD := "_godot_locator_format"
const FORMAT_METHOD_CS := "_GodotLocatorFormat"

# Stable ref ids: instance_id → sequential ref number, persistent across calls
# so a ref handed out by snapshot keeps pointing at the same node for later
# locate/control calls. Read by `interaction.gd` when matching `{ref: "eN"}`.
var ref_by_iid: Dictionary = {}
var _ref_counter: int = 0


## Render the current SceneTree as a YAML-style snapshot string.
## See README → Snapshot for the line format. `depth=0` means no limit.
## `tag_ref=true` opts into emitting `ref=eN` markers (Playwright-style — refs
## are off by default; tools that intend to act on the snapshot ask for them).
func render(depth: int = 0, skip_invisible: bool = true, tag_ref: bool = false) -> String:
	var lines := PackedStringArray()
	for child in get_tree().root.get_children():
		_walk_ui(child, 0, depth, skip_invisible, tag_ref, lines)
	return "\n".join(lines)


func handle_snapshot(params: Dictionary) -> Variant:
	return render(
		int(params.get("depth", 0)),
		bool(params.get("skip_invisible", true)),
		bool(params.get("tag_ref", false)),
	)


# Visible text content of a node, for `text:` locator matches. Mirrors
# README's `get_by_text` scope. CheckBox extends Button so `is Button`
# already catches it; the explicit name is documentation.
func node_text(node: Node) -> String:
	if node is Label or node is Button or node is CheckBox:
		return node.text
	if node is RichTextLabel:
		return (node as RichTextLabel).get_parsed_text()
	return ""


func ref_for(node: Node) -> String:
	var iid := node.get_instance_id()
	if not ref_by_iid.has(iid):
		_ref_counter += 1
		ref_by_iid[iid] = _ref_counter
	return "e%d" % ref_by_iid[iid]


func class_name_of(node: Node) -> String:
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


func custom_format_method(node: Node) -> String:
	if node.has_method(FORMAT_METHOD):
		return FORMAT_METHOD
	if node.has_method(FORMAT_METHOD_CS):
		return FORMAT_METHOD_CS
	return ""


# Emit only Control nodes. Non-Control ancestors (Window, CanvasLayer, Node2D…)
# are traversed transparently so Controls nested under them still appear, at
# the same depth as their nearest Control ancestor.
func _walk_ui(node: Node, control_depth: int, max_depth: int, skip_invisible: bool, tag_ref: bool, lines: PackedStringArray) -> void:
	if not (node is Control):
		for child in node.get_children():
			_walk_ui(child, control_depth, max_depth, skip_invisible, tag_ref, lines)
		return

	var ctrl: Control = node
	if skip_invisible and not ctrl.is_visible_in_tree():
		return

	var indent := "  ".repeat(control_depth)
	var label := _format_control(ctrl, tag_ref)

	if max_depth > 0 and control_depth >= max_depth - 1:
		lines.append("%s- %s" % [indent, label])
		return

	var children := PackedStringArray()
	for child in node.get_children():
		_walk_ui(child, control_depth + 1, max_depth, skip_invisible, tag_ref, children)

	if children.is_empty():
		lines.append("%s- %s" % [indent, label])
	else:
		lines.append("%s- %s:" % [indent, label])
		lines.append_array(children)


func _format_control(ctrl: Control, tag_ref: bool) -> String:
	# Format: `Class [#Name] ["text"] [ref=eN, k=v, k="v", flag]`.
	# Brackets carry attributes (Playwright-style); the node name is a
	# CSS-id-style suffix on the class. Empty/default values are dropped.
	var parts := PackedStringArray()
	parts.append(class_name_of(ctrl))

	var node_name := str(ctrl.name)
	if node_name != "":
		parts.append("#" + node_name)

	var custom_method := custom_format_method(ctrl)
	var has_custom: bool = custom_method != ""
	var custom: Dictionary = {}
	if has_custom:
		var v: Variant = ctrl.call(custom_method)
		if v is Dictionary:
			custom = v

	# Positional text: custom override → Label/Button → RichTextLabel →
	# LineEdit/TextEdit current content (the user-meaningful "current value",
	# matching how Playwright's textbox snapshot reads).
	var text := ""
	if custom.has("text"):
		text = str(custom["text"])
	elif ctrl is Label or ctrl is Button:
		text = ctrl.text
	elif ctrl is RichTextLabel:
		text = (ctrl as RichTextLabel).get_parsed_text()
	elif ctrl is LineEdit or ctrl is TextEdit:
		text = ctrl.text
	if text != "":
		parts.append('"%s"' % _escape(text))

	var needs_ref: bool = tag_ref and (has_custom or ctrl is LineEdit or ctrl is TextEdit or ctrl is BaseButton)
	var bracket_items := PackedStringArray()

	if needs_ref:
		bracket_items.append("ref=" + ref_for(ctrl))

	if ctrl is LineEdit or ctrl is TextEdit:
		var ph: String = ctrl.placeholder_text
		if ph != "":
			bracket_items.append('placeholder="%s"' % _escape(ph))

	if custom.has("attrs") and custom["attrs"] is Dictionary:
		var attrs: Dictionary = custom["attrs"]
		for k in attrs:
			var raw: Variant = attrs[k]
			if raw == null:
				continue
			bracket_items.append("%s=%s" % [str(k), _format_attr_value(raw)])

	if ctrl is BaseButton and (ctrl as BaseButton).disabled:
		bracket_items.append("disabled")

	if custom.has("flags") and custom["flags"] is Array:
		for f in custom["flags"]:
			bracket_items.append(str(f))

	if not bracket_items.is_empty():
		parts.append("[%s]" % ", ".join(bracket_items))

	return " ".join(parts)


# Render an attr value: numeric/bool unquoted, anything else quoted.
func _format_attr_value(v: Variant) -> String:
	match typeof(v):
		TYPE_INT, TYPE_FLOAT:
			return str(v)
		TYPE_BOOL:
			return "true" if v else "false"
		_:
			return '"%s"' % _escape(str(v))


func _escape(s: String) -> String:
	return s.replace("\\", "\\\\").replace('"', '\\"')
