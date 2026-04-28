# Godot plugin

The `godot-locator` addon is the runtime piece that lives inside your Godot
project. It opens a WebSocket and answers JSON-RPC-ish requests describing /
manipulating the live SceneTree.

## Install

Copy `addons/godot-locator/` into your project, then enable the plugin under
**Project Settings → Plugins**. Enabling the plugin registers a `Locator`
autoload — the autoload is the part that actually runs at game time.

## Configuration

| Env | Default | Description |
| --- | --- | --- |
| `GODOT_LOCATOR_HOST` | `127.0.0.1` | Bind address. |
| `GODOT_LOCATOR_PORT` | `8282` | TCP port. |
| `GODOT_LOCATOR_SERVER_ENABLED` | `1` | Set to `0` to disable the server (e.g. in production builds). |

## Wire protocol

Requests:

```json
{"id": 1, "method": "snapshot", "params": {}}
```

Responses:

```json
{"id": 1, "result": "..."}
{"id": 1, "error": "message"}
```

You don't need to speak the wire directly — see the [Python client](python.md)
for an idiomatic wrapper.

## Methods

<!-- TODO: enumerate the runtime methods supported by `server.gd` (snapshot, click, type, wait_for, …). -->
