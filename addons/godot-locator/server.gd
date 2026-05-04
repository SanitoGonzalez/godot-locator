extends Node

## WebSocket transport for the runtime locator service. Owned as a child
## of the `Locator` autoload (see `locator.gd`). Listens on a local port
## and forwards JSON-RPC-ish requests to `locator.dispatch()`.

const ENV_PORT := "GODOT_LOCATOR_PORT"
const ENV_HOST := "GODOT_LOCATOR_HOST"
const ENV_SERVER_ENABLED := "GODOT_LOCATOR_SERVER_ENABLED"
const DEFAULT_PORT := 8282
const DEFAULT_HOST := "127.0.0.1"

var locator: Node

var _server := TCPServer.new()
var _peers: Array[WebSocketPeer] = []
var _port: int = DEFAULT_PORT
var _host: String = DEFAULT_HOST


func _ready() -> void:
	if OS.get_environment(ENV_SERVER_ENABLED).to_lower() == "false":
		# Locator's direct API stays callable from user code; only the wire is off.
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
		result = await locator.dispatch(method, params)
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
