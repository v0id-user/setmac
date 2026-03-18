"""Status checking commands."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import click

from setmac.installers.base import check_tool
from setmac.output import emit_status
from setmac.registry import Registry


def _check_one(tool):
    """Check a single tool. Returns (tool_id, installed, version)."""
    installed, version = check_tool(tool)
    return tool.id, installed, version


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
        # Check all tools in parallel — ~10x faster than sequential
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = {pool.submit(_check_one, tool): tool for tool in registry.tools}
            for future in as_completed(futures):
                tool_id, installed, version = future.result()
                emit_status(tool_id, "installed" if installed else "not_installed", version=version)
