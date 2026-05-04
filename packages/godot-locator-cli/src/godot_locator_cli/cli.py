"""Top-level entry point. All `LocatorError` subclasses funnel through
`main()` so individual commands don't repeat error handling.
"""

from __future__ import annotations

import sys

import click

from godot_locator_core import (
    ENV_SESSION,
    LocatorError,
    SessionStaleError,
)

from . import output
from .commands.attach import attach_cmd, detach_cmd
from .commands.evaluate import eval_cmd
from .commands.interaction import (
    action_cmd,
    click_cmd,
    dblclick_cmd,
    fill_cmd,
    press_cmd,
    type_cmd,
)
from .commands.launch import launch_cmd, terminate_cmd
from .commands.screenshot import screenshot_cmd
from .commands.sessions import sessions_group
from .commands.snapshot import snapshot_cmd


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-s",
    "--session",
    "session_name",
    default=None,
    envvar=ENV_SESSION,
    help=f"Session name to use (default: 'default'; env: {ENV_SESSION}).",
)
@click.version_option(package_name="godot-locator-cli")
@click.pass_context
def root(ctx: click.Context, session_name: str | None) -> None:
    """Bridge AI agents to a running Godot game.

    Run `godot-locator-cli attach --endpoint=ws://localhost:8282` first, then
    use `snapshot`, `click`, etc. See `--help` on each subcommand for details.
    """
    ctx.ensure_object(dict)
    ctx.obj["session"] = session_name


root.add_command(launch_cmd)
root.add_command(terminate_cmd)
root.add_command(attach_cmd)
root.add_command(detach_cmd)
root.add_command(sessions_group)
root.add_command(snapshot_cmd)
root.add_command(screenshot_cmd)
root.add_command(click_cmd)
root.add_command(dblclick_cmd)
root.add_command(fill_cmd)
root.add_command(type_cmd)
root.add_command(press_cmd)
root.add_command(action_cmd)
root.add_command(eval_cmd)


def main() -> None:
    """CLI entry point. Centralizes error handling so commands don't repeat it."""
    try:
        root(standalone_mode=False)
    except SessionStaleError as e:
        # Spec format — agents grep for this exact message.
        output.emit_error(str(e))
        sys.exit(1)
    except LocatorError as e:
        output.emit_error(f"error: {e}")
        sys.exit(1)
    except click.exceptions.Abort:
        sys.exit(130)
    except click.exceptions.Exit as e:
        sys.exit(e.exit_code)
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
