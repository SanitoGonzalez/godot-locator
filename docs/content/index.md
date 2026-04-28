# Godot Locator

Playwright-style runtime locators for Godot Engine games. Drive a running game
from outside the engine — for AI agents, integration tests, or any tool that
wants to inspect and click around the SceneTree.

## What's in the project

| Component | What it is |
| --- | --- |
| [Godot plugin](plugin.md) | The `addons/godot-locator` plugin that opens a WebSocket on the running game and answers JSON-RPC requests. |
| [MCP server](mcp.md) | `godot-locator-mcp` — exposes the locator API to Claude / any MCP-aware AI agent. |
| [CLI](cli.md) | `godot-locator-cli` — drive the locator from a shell. |

New here? Start with [Getting started](getting-started.md).
