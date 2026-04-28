# tests

End-to-end tests that spawn a real Godot game with the `godot-locator` plugin
loaded and drive it via the Python client / MCP server / CLI.

## Requirements

- [`uv`](https://docs.astral.sh/uv/)
- `godot` on `PATH` (Godot .NET 4.6+)

## Running

```sh
cd tests
uv sync
uv run pytest
```
