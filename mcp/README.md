# godot-locator-mcp

MCP server bridging AI agents to a running Godot game via the [`godot-locator`](../addons/godot-locator/) runtime plugin.

The plugin opens a WebSocket on the Godot side; this server speaks MCP on stdio and forwards tool calls over that socket. Use it from Claude Code, Claude Desktop, or any MCP-aware client.

## Install

```sh
uvx godot-locator-mcp
```

Or, in an MCP client config (Claude Desktop / Claude Code):

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

| Env | Description | Default |
| --- | ----------- | ------- |
| `GODOT_LOCATOR_HOST` | host the Godot game's locator service is bound to | `127.0.0.1` |
| `GODOT_LOCATOR_PORT` | port the Godot game's locator service is bound to | `8282` |

These are the same names the Godot-side plugin reads, so a single shell environment configures both ends.

## Tools

| Tool | Description |
| ---- | ----------- |
| `snapshot` | YAML-style dump of the current SceneTree. `tag_ref=true` by default — refs are emitted so subsequent calls can target nodes by `e<n>`. |
| `click` | Left-click the single node matching the locator. |
| `double_click` | Left double-click. |
| `right_click` | Right-click. |
| `fill` | Replace the text of a `LineEdit` / `TextEdit`. |

Locators are dicts; keys AND-match. Supported keys: `name`, `class`, `ref`.

```json
{"name": "Submit"}
{"class": "Button"}
{"ref": "e3"}
```

## Develop

```sh
cd mcp
uv sync
uv run pytest
```

Tests spawn a real headless Godot per case (requires `godot` on PATH or `GODOT_BIN=...`) and drive the MCP tool layer in-process via FastMCP's in-memory client. The test projects under `../tests/projects/` are reused.
