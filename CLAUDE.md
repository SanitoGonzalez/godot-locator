# Godot Locator

## Project Structure

- **addons/godot-locator/**: a Godot plugin serves/provides locator methods via web socket.
- **docs/**
- **packages/godot-locator-cli/**: a locator CLI client written in Python
- **packages/godot-locator-core/**: a core package shared with `godot-locator-cli`, `godot-locator-mcp`.
- **packages/godot-locator-mcp/**: a MCP server for locator written in Python, `FastMCP`.
- **tests/**: integration tests launch Godot game and interact with cli and mcp.
- **website/**: `docusaurus` powered docs website sourced with `docs/`.

## Comment style

Default to **no comments**. Add one only when the WHY is non-obvious — a hidden constraint, a subtle invariant, a workaround, or surprising behavior.

When in doubt, delete it.
