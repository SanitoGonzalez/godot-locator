#!/usr/bin/env bash
# Single entry point for CLI agents and humans.
#   tests/run.sh             # run all tests
#   tests/run.sh -k snapshot # forward args to pytest
set -euo pipefail

cd "$(dirname "$0")"

GODOT_BIN="${GODOT_BIN:-godot}"

if ! command -v "$GODOT_BIN" >/dev/null 2>&1; then
	echo "error: '$GODOT_BIN' not on PATH. Install Godot 4.x or set GODOT_BIN." >&2
	exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "error: 'uv' not on PATH. Install: https://docs.astral.sh/uv/" >&2
	exit 2
fi

exec uv run --quiet pytest -q "$@"
