"""Install commands."""

from __future__ import annotations

import signal
import sys

import click

from setmac.askpass import AskpassServer
from setmac.commands.configs import apply_configs
from setmac.commands.status import status_cmd
from setmac.installers.base import Outcome, Runner, run_tool
from setmac.output import emit_error, emit_log, emit_summary
from setmac.registry import Registry, Tool

EXIT_SOME_FAILED = 2


@click.command("install")
@click.argument("tool_id")
@click.option("--category", "-c", is_flag=True, help="Treat TOOL_ID as a category name")
@click.option("--check", is_flag=True, help="Only check status, don't install")
@click.option("--no-configs", is_flag=True, help="With 'all', skip applying dotfiles at the end")
@click.pass_context
def install_cmd(ctx: click.Context, tool_id: str, category: bool, check: bool, no_configs: bool):
    """Install a tool, a category, or 'all'."""
    if check:
        ctx.invoke(status_cmd, tool_id=None if tool_id == "all" else tool_id)
        return

    registry = Registry()
    if tool_id == "all":
        tools = registry.install_order()
    elif category:
        members = registry.by_category(tool_id)
        if not members:
            emit_error(tool_id, f"No tools found in category: {tool_id}")
            raise SystemExit(1)
        tools = registry.install_order([t.id for t in members])
    else:
        if not registry.get(tool_id):
            emit_error(tool_id, f"Unknown tool: {tool_id}")
            raise SystemExit(1)
        tools = registry.install_order([tool_id])

    failed = install_tools(tools, registry, apply_dotfiles=tool_id == "all" and not no_configs)
    if failed:
        raise SystemExit(EXIT_SOME_FAILED)


def install_tools(tools: list[Tool], registry: Registry, apply_dotfiles: bool) -> list[str]:
    """Install tools in order. Returns the ids that failed or were skipped."""
    askpass = AskpassServer()
    runner = Runner(extra_env=askpass.env())

    def stop(signum, _frame):
        runner.terminate()
        askpass.close()
        emit_log("Cancelled")
        sys.exit(128 + signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    counts = {outcome: 0 for outcome in Outcome}
    failed: list[str] = []
    emit_log(f"Installing {len(tools)} tool(s) in dependency order...")
    try:
        for index, tool in enumerate(tools, start=1):
            emit_log(f"[{index}/{len(tools)}] {tool.name}", tool=tool.id)
            blocked = [dep for dep in tool.depends_on if dep in failed]
            if blocked:
                names = ", ".join(registry.get(d).name if registry.get(d) else d for d in blocked)
                emit_error(tool.id, f"Skipped: needs {names}, which did not install")
                failed.append(tool.id)
                continue
            outcome = run_tool(tool, runner)
            counts[outcome] += 1
            if outcome is Outcome.FAILED:
                failed.append(tool.id)

        if apply_dotfiles:
            apply_configs(registry, skip_tools=set(failed))
    finally:
        askpass.close()

    summary = f"{counts[Outcome.INSTALLED]} installed, {counts[Outcome.ALREADY]} already set up"
    if failed:
        summary += f", {len(failed)} failed: " + ", ".join(failed)
    emit_summary(summary, failed=failed)
    return failed
