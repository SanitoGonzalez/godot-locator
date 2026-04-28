# CLI

`godot-locator-cli` drives a running Godot game from a shell. Same wire as the
[Python client](python.md) and the [MCP server](mcp.md), different surface.

!!! warning "Work in progress"
    The CLI is a stub today. Commands and flags below are the intended shape;
    expect them to land incrementally.

## Install

```sh
uv tool install godot-locator-cli
```

## Configuration

| Env | Default | Description |
| --- | --- | --- |
| `GODOT_LOCATOR_HOST` | `127.0.0.1` | Host the Godot game's locator service is bound to. |
| `GODOT_LOCATOR_PORT` | `8282` | Port the Godot game's locator service is bound to. |

## Commands

<!-- TODO: enumerate as the CLI grows. Likely surface:
     godot-locator-cli snapshot
     godot-locator-cli click <ref>
     godot-locator-cli type <ref> <text>
     godot-locator-cli evaluate <expression>
-->
