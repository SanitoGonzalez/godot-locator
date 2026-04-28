# MCP server

`godot-locator-mcp` exposes the locator API to AI agents over the
[Model Context Protocol](https://modelcontextprotocol.io). Use it from Claude
Desktop, Claude Code, or any MCP-aware client.

## Install

```sh
uvx godot-locator-mcp
```

Or, in an MCP client config:

```json
{
  "mcpServers": {
    "godot-locator": {
      "command": "uvx",
      "args": ["godot-locator-mcp"]
    }
  }
}
```

## Configuration

| Env | Default | Description |
| --- | --- | --- |
| `GODOT_LOCATOR_HOST` | `127.0.0.1` | Host the Godot game's locator service is bound to. |
| `GODOT_LOCATOR_PORT` | `8282` | Port the Godot game's locator service is bound to. |
| `GODOT_LOCATOR_MCP_CAPABILITIES` | — | Comma-separated extra capability tags (`core` is always on). |
| `GODOT_LOCATOR_MCP_SNAPSHOT_MODE` | `full` | Snapshot payload in interaction responses: `full`, `none`, or `delta` (reserved). |

The host/port names match what the Godot-side plugin reads, so a single shell
environment configures both ends.

## Tools

| Tool | Description |
| --- | --- |
| `snapshot` | YAML-style dump of the current SceneTree. |
| `screenshot` | Capture the framebuffer (or a specific node). |
| `click` | Click a node by reference. |
| `type` | Replace the text of a `LineEdit` / `TextEdit`. |
| `wait_for` | Poll until a locator predicate holds. |
| `evaluate` | Run a GDScript expression on the scene or a node. |
| `mouse_*` | Lower-level mouse primitives (`move_xy`, `click_xy`, `drag_xy`, `down`, `up`, `wheel`). |

<!-- TODO: per-tool argument tables once the surface stabilizes. -->

## Refs

References (`e1`, `e2`, …) only exist after a `snapshot` call. They're stable
for the lifetime of the running game. Start every interaction session with
`snapshot()`.
