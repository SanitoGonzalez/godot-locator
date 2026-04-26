"""CLI entrypoint for `godot-locator-mcp` (declared in pyproject.toml).

Defaults to stdio transport, which is what Claude Desktop / Claude Code
consume when this server is launched via `uvx godot-locator-mcp`.
"""

from __future__ import annotations

from .server import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
