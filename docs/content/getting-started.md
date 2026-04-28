# Getting started

## Install the plugin

Copy `addons/godot-locator/` into your Godot project's `addons/` directory,
then enable it in **Project → Project Settings → Plugins**. Enabling the
plugin registers a `Locator` autoload that runs in every play session.

```
your-project/
  addons/
    godot-locator/
  project.godot
```

## Run your game

Launch your game normally (editor play, exported binary, or `godot --path …`
on the CLI). The plugin's `Locator` autoload binds a WebSocket on
`127.0.0.1:8282` by default. Override via env:

| Variable | Default | Meaning |
| --- | --- | --- |
| `GODOT_LOCATOR_HOST` | `127.0.0.1` | Bind address. |
| `GODOT_LOCATOR_PORT` | `8282` | Bind port. |

## Pick a client

- **AI agent / Claude**: install [the MCP server](mcp.md) — `uvx godot-locator-mcp`.
- **Shell / scripts**: install [the CLI](cli.md).
- **Custom Python**: use [`godot-locator-client`](python.md) directly.

All three speak the same wire to the plugin.
