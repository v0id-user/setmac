"""Status checking commands."""

import click

from rig.installers.base import check_tool
from rig.output import emit_status
from rig.registry import Registry


@click.command("status")
@click.argument("tool_id", required=False)
def status_cmd(tool_id):
    """Check install status of tools. Omit TOOL_ID to check all."""
    registry = Registry()

    if tool_id:
        tool = registry.get(tool_id)
        if not tool:
            click.echo(f"Unknown tool: {tool_id}", err=True)
            raise SystemExit(1)
        installed, version = check_tool(tool)
        emit_status(tool.id, "installed" if installed else "not_installed", version=version)
    else:
        for tool in registry.tools:
            installed, version = check_tool(tool)
            emit_status(tool.id, "installed" if installed else "not_installed", version=version)
