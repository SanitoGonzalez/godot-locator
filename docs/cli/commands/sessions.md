---
sidebar_position: 1
---

# Sessions

A session stores the connection details for a running Godot game so that separate CLI commands can share the same target without repeating specification every time.


## How It Works

Sessions are files stored in `~/.local/share/godot-locator/sessions/<name>.json`:

```json
{
  "endpoint": "ws://localhost:8282",
  "created_at": "2024-01-01T12:00:00Z"
}
```

Each CLI command opens a fresh WebSocket connection using the endpoint in the session file, does its work, then closes the socket. There is no persistent background process.

**Stale cleanup** — if a command connects and the server is unreachable (Godot has exited), the CLI deletes the session file automatically and exits with a clear error:

```
Session 'default' is stale — ws://localhost:8282 is not reachable.
Godot game has exited. Session removed.
```

**`launch` vs `attach`** — `launch` starts a new Godot process and attaches automatically, so it can store the process PID and detect exit immediately. `attach` connects to an already-running game and relies on the stale-on-connect detection above.


## Resolution Order

When a command runs, the session is resolved in this order:

1. `-s <name>` flag on the command line
2. `GODOT_LOCATOR_SESSION` environment variable
3. `default` session file


## Commands

| Command | Description |
| ------- | ----------- |
| `launch <path>` | Start a new Godot game and attach to it |
| `launch <path> --headed` | Launch with a visible window |
| `terminate` | Send shutdown to the game and remove the session |
| `attach --endpoint=<url>` | Connect to an already-running game |
| `attach --endpoint=<url> -s <name>` | Connect and save as a named session |
| `detach` | Remove the current session (alias for `sessions rm default`) |
| `sessions list` | Show all sessions with live/stale status |
| `sessions rm <name>` | Delete a session file |


## Examples

```sh
# Attach to a running game
godot-locator-cli attach --endpoint=ws://localhost:8282
godot-locator-cli snapshot
godot-locator-cli click e5

# Named sessions — useful when multiple games are running
godot-locator-cli attach --endpoint=ws://localhost:8282 -s debug
godot-locator-cli attach --endpoint=ws://localhost:9090 -s staging
godot-locator-cli -s debug snapshot
godot-locator-cli -s staging click e5

# Inspect sessions
godot-locator-cli sessions list

# Clean up
godot-locator-cli detach
godot-locator-cli terminate
```
