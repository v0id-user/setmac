"""Install commands."""

from __future__ import annotations

import signal
import sys

import click

from setmac.askpass import AskpassServer
from setmac.commands.configs import apply_configs
from setmac.commands.status import status_cmd
from setmac.installers.base import Outcome, Runner, check_tool, run_tool
from setmac.output import emit_error, emit_log, emit_skipped, emit_status, emit_summary
from setmac.registry import Registry, Tool, get_registry

EXIT_SOME_FAILED = 2


@click.command("install")
@click.argument("tool_ids", nargs=-1, required=True)
@click.option("--category", "-c", is_flag=True, help="Treat TOOL_ID as a category name")
@click.option("--check", is_flag=True, help="Only check status, don't install")
@click.option("--no-configs", is_flag=True, help="With 'all', skip applying dotfiles at the end")
@click.option("--dry-run", is_flag=True, help="List what would be installed and what needs admin; change nothing")
@click.pass_context
def install_cmd(
    ctx: click.Context, tool_ids: tuple[str, ...], category: bool, check: bool, no_configs: bool, dry_run: bool
):
    """Install tools by id, a category (with -c), or 'all'."""
    everything = tool_ids == ("all",)
    if check:
        for tid in [None] if everything else tool_ids:
            ctx.invoke(status_cmd, tool_id=tid)
        return

    registry = get_registry(ctx)
    if everything:
        tools = registry.install_order()
    elif category:
        members = [t for name in tool_ids for t in registry.by_category(name)]
        if not members:
            emit_error(tool_ids[0], f"No tools found in category: {', '.join(tool_ids)}")
            raise SystemExit(1)
        tools = registry.install_order([t.id for t in members])
    else:
        unknown = [tid for tid in tool_ids if not registry.get(tid)]
        if unknown:
            emit_error(unknown[0], f"Unknown tool: {', '.join(unknown)}")
            raise SystemExit(1)
        tools = registry.install_order(list(tool_ids))

    apply_dotfiles = everything and not no_configs
    if dry_run:
        plan_tools(tools, apply_dotfiles)
        return
    failed = install_tools(tools, registry, apply_dotfiles)
    if failed:
        raise SystemExit(EXIT_SOME_FAILED)


def pending_admin(tools: list[Tool]) -> list[Tool]:
    """Tools marked requires_admin that are not installed yet."""
    return [t for t in tools if t.install.requires_admin and not check_tool(t)[0]]


def plan_tools(tools: list[Tool], apply_dotfiles: bool) -> None:
    """Report what an install run would do, without running anything."""
    missing: list[Tool] = []
    for tool in tools:
        installed, version = check_tool(tool)
        emit_status(tool.id, "installed" if installed else "not_installed", version=version)
        if not installed and tool.install.method != "config":
            missing.append(tool)
    if missing:
        emit_log(f"Would install {len(missing)} tool(s): " + ", ".join(t.id for t in missing))
    else:
        emit_log("Nothing to install")
    admin = [t.id for t in missing if t.install.requires_admin]
    if admin:
        emit_log("Needs an admin password: " + ", ".join(admin))
    if apply_dotfiles and any(t.configs for t in tools):
        emit_log("Would apply dotfiles at the end")


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
    next_steps: list[str] = []
    emit_log(f"Installing {len(tools)} tool(s) in dependency order...")
    try:
        # Ask for the password up front instead of mid-run, and skip admin tools
        # cleanly when it is refused instead of letting their installers hang.
        needs_admin = {t.id for t in pending_admin(tools)}
        admin_ok = True
        if needs_admin:
            emit_log("Needs an admin password: " + ", ".join(t.id for t in tools if t.id in needs_admin))
            admin_ok = askpass.ensure_admin(next(t.id for t in tools if t.id in needs_admin))
        for index, tool in enumerate(tools, start=1):
            emit_log(f"[{index}/{len(tools)}] {tool.name}", tool=tool.id)
            blocked = [dep for dep in tool.depends_on if dep in failed]
            if blocked:
                names = ", ".join(registry.get(d).name if registry.get(d) else d for d in blocked)
                emit_error(tool.id, f"Skipped: needs {names}, which did not install")
                failed.append(tool.id)
                continue
            if tool.id in needs_admin and not admin_ok:
                emit_error(tool.id, f"Skipped: {tool.name} needs an admin password")
                emit_skipped(tool.id, "needs_admin")
                failed.append(tool.id)
                continue
            outcome = run_tool(tool, runner, position=(index, len(tools)))
            counts[outcome] += 1
            if outcome is Outcome.FAILED:
                failed.append(tool.id)
            elif outcome is Outcome.INSTALLED and tool.post_install:
                next_steps.append(f"{tool.name}: {tool.post_install}")

        if apply_dotfiles:
            apply_configs(registry, skip_tools=set(failed))
    finally:
        askpass.close()

    if next_steps:
        emit_log("Finish setup by hand:")
        for step in next_steps:
            emit_log(f"  • {step}")

    summary = f"{counts[Outcome.INSTALLED]} installed, {counts[Outcome.ALREADY]} already set up"
    if failed:
        summary += f", {len(failed)} failed: " + ", ".join(failed)
    emit_summary(summary, failed=failed)
    return failed
