extends Node

## Runtime locator server. Registered as the `Locator` autoload by the
## EditorPlugin in `plugin.gd`. Listens on a local WebSocket and answers
## JSON-RPC-ish requests from an external MCP bridge.
##
## Owns two sibling modules added as children:
##   - `snapshot_module` (snapshot.gd): tree rendering + ref tracking.
##   - `interaction_module` (interaction.gd): click / fill / wait_for / …
##
## Public API on this autoload mirrors the most common module methods so
## user code can call `Locator.snapshot()` / `Locator.click(node)` directly.

const ENV_PORT := "GODOT_LOCATOR_PORT"
const ENV_HOST := "GODOT_LOCATOR_HOST"
const ENV_SERVER_ENABLED := "GODOT_LOCATOR_SERVER_ENABLED"
const DEFAULT_PORT := 8282
const DEFAULT_HOST := "127.0.0.1"

const SnapshotModule := preload("res://addons/godot-locator/snapshot.gd")
const InteractionModule := preload("res://addons/godot-locator/interaction.gd")

var _server := TCPServer.new()
var _peers: Array[WebSocketPeer] = []
var _port: int = DEFAULT_PORT
var _host: String = DEFAULT_HOST

var snapshot_module: Node
var interaction_module: Node


func _ready() -> void:
	snapshot_module = SnapshotModule.new()
	snapshot_module.name = "Snapshot"
	add_child(snapshot_module)

	interaction_module = InteractionModule.new()
	interaction_module.name = "Interaction"
	interaction_module.snapshot_module = snapshot_module
	add_child(interaction_module)

	# Server defaults on; only the literal `false` (case-insensitive) disables it.
	if OS.get_environment(ENV_SERVER_ENABLED).to_lower() == "false":
		# Public API stays callable from user code; only the WebSocket is off.
		set_process(false)
		return

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
	if method == "":
		err = "missing method"
	else:
		# `await` covers both sync handlers (returns the value as-is) and
		# coroutine handlers like `wait_for` that suspend on a timer.
		result = await _dispatch(method, params)
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


func _dispatch(method: String, params: Dictionary) -> Variant:
	match method:
		"snapshot":     return snapshot_module.handle_snapshot(params)
		"locate":       return interaction_module.handle_locate(params)
		"count":        return interaction_module.handle_count(params)
		"click":        return interaction_module.handle_click(params)
		"double_click": return interaction_module.handle_double_click(params)
		"right_click":  return interaction_module.handle_right_click(params)
		"hover":        return interaction_module.handle_hover(params)
		"focus":        return interaction_module.handle_focus(params)
		"fill":         return interaction_module.handle_fill(params)
		"press_key":    return interaction_module.handle_press_key(params)
		"drag_to":      return interaction_module.handle_drag_to(params)
		"scroll":       return interaction_module.handle_scroll(params)
		"describe":     return interaction_module.handle_describe(params)
		"wait_for":     return await interaction_module.handle_wait_for(params)
		_: return {"__error": "unknown method: %s" % method}


# --- public API forwarders ----------------------------------------------------

## Render the current SceneTree as a YAML-style snapshot string.
## See README → Snapshot for the line format. `depth=0` means no limit.
func snapshot(depth: int = 0, skip_invisible: bool = true, tag_ref: bool = false) -> String:
	return snapshot_module.render(depth, skip_invisible, tag_ref)


## Synthesize a left-click at the node's center. `node` must be a Control or Node2D.
func click(node: Node) -> void:
	interaction_module.click(node)


## Synthesize a left-click followed by a `double_click=true` left-click.
func double_click(node: Node) -> void:
	interaction_module.double_click(node)


## Synthesize a right-click at the node's center.
func right_click(node: Node) -> void:
	interaction_module.right_click(node)


## Replace `node.text` with `text`. Returns false if `node` is not LineEdit/TextEdit.
func fill(node: Node, text: String) -> bool:
	return interaction_module.fill(node, text)
