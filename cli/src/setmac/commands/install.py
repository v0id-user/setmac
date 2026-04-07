"""Install commands."""

import click

from setmac.installers.base import run_tool
from setmac.output import emit_error, emit_log
from setmac.registry import Registry


@click.command("install")
@click.argument("tool_id")
@click.option("--category", "-c", is_flag=True, help="Treat TOOL_ID as a category name")
@click.option("--check", is_flag=True, help="Only check status, don't install")
@click.option("--version", "-v", default=None, help="Version to install (for versioned tools)")
def install_cmd(tool_id, category, check, version):
    """Install a tool, category, or 'all'."""
    registry = Registry()

    if check:
        # Delegate to status
        from setmac.commands.status import status_cmd
        from click.testing import CliRunner

        runner = CliRunner()
        runner.invoke(status_cmd, [tool_id] if tool_id != "all" else [])
        return

    if tool_id == "all":
        tools = registry.install_order()
        emit_log(f"Installing {len(tools)} tools in dependency order...")
        for tool in tools:
            run_tool(tool)
        return

    if category:
        tools = registry.by_category(tool_id)
        if not tools:
            emit_error(tool_id, f"No tools found in category: {tool_id}")
            raise SystemExit(1)
        # Get install order for just this category's tools
        ordered = registry.install_order([t.id for t in tools])
        emit_log(f"Installing {len(ordered)} tools from '{tool_id}' category...")
        for tool in ordered:
            run_tool(tool)
        return

    tool = registry.get(tool_id)
    if not tool:
        emit_error(tool_id, f"Unknown tool: {tool_id}")
        raise SystemExit(1)

    # Install dependencies first (without version override), then the target with the version
    ordered = registry.install_order([tool_id])
    for t in ordered:
        run_tool(t, version=version if t.id == tool_id else None)
