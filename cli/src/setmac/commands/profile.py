"""Profile commands: see, choose and check which tools setmac installs."""

from __future__ import annotations

import json

import click

from setmac import profile
from setmac.output import emit_manifest, emit_profile_error
from setmac.registry import EXIT_PROFILE, ManifestError, Registry


def _spec(ctx: click.Context, spec: str | None) -> str:
    """The spec given to the command, else the active one (--profile, env, pointer, default)."""
    if spec:
        return spec
    return profile.active_spec((ctx.find_root().obj or {}).get("profile"))[0]


def _resolve(spec: str) -> tuple[profile.Resolved, Registry]:
    resolved = profile.resolve(spec)
    registry = Registry(data=resolved.manifest, configs_roots=resolved.configs_roots, sensitive_ok=resolved.sensitive_ok)
    return resolved, registry


@click.group("profile")
def profile_cmd():
    """Choose which tools setmac installs."""


@profile_cmd.command("list")
@click.option("--json", "as_json", is_flag=True, help="Print one JSON object")
@click.pass_context
def list_profiles(ctx: click.Context, as_json: bool):
    """List the starter profiles and show which profile is active."""
    spec, source = profile.active_spec((ctx.find_root().obj or {}).get("profile"))
    starters = [{"name": p.name, "description": p.data.get("description", "")} for p in profile.starters()]
    if as_json:
        click.echo(json.dumps({"active": spec, "source": source, "starters": starters}))
        return
    click.echo(f"Active profile: {spec} (from {source})\n")
    click.echo("Starter profiles:")
    for starter in starters:
        mark = "*" if starter["name"] == spec else " "
        click.echo(f" {mark} {starter['name']:10} {starter['description']}")


@profile_cmd.command("show")
@click.argument("spec", required=False)
@click.option("--json", "as_json", is_flag=True, help="Print the merged manifest as a `manifest` event")
@click.pass_context
def show(ctx: click.Context, spec: str | None, as_json: bool):
    """Show the tools a profile installs (the active profile by default)."""
    spec = _spec(ctx, spec)
    try:
        resolved, registry = _resolve(spec)
    except (profile.ProfileError, ManifestError) as e:
        emit_profile_error(spec, e.problems)
        raise SystemExit(EXIT_PROFILE) from e
    if as_json:
        emit_manifest(resolved.profile.name, resolved.manifest)
        return
    click.echo(" -> ".join(p.name for p in resolved.chain))
    click.echo(f"{len(registry.tools)} tools, in install order:")
    for tool in registry.install_order():
        click.echo(f"  {tool.id:22} {tool.install.method:12} {tool.name}")


@profile_cmd.command("use")
@click.argument("spec")
def use(spec: str):
    """Make SPEC the active profile (a starter name or a profile directory)."""
    try:
        resolved, registry = _resolve(spec)
    except (profile.ProfileError, ManifestError) as e:
        emit_profile_error(spec, e.problems)
        raise SystemExit(EXIT_PROFILE) from e
    profile.write_pointer(spec)
    click.echo(f"Active profile is now {resolved.profile.name} ({len(registry.tools)} tools).")


@profile_cmd.command("validate")
@click.argument("spec", required=False)
@click.option("--json", "as_json", is_flag=True, help="Print the problems as JSON")
@click.pass_context
def validate(ctx: click.Context, spec: str | None, as_json: bool):
    """Check a profile for problems without installing anything. Exits 1 if it has any."""
    spec = _spec(ctx, spec)
    try:
        _resolve(spec)
        problems = []
    except (profile.ProfileError, ManifestError) as e:
        problems = e.problems
    if as_json:
        click.echo(json.dumps([
            {"code": p.code, "tool_id": p.tool_id, "field": p.field, "message": p.message} for p in problems
        ]))
    elif problems:
        click.echo(f"{spec}: {len(problems)} problem(s)")
        for p in problems:
            click.echo(f"  [{p.code}] {p.message}")
    else:
        click.echo(f"{spec}: no problems")
    if problems:
        raise SystemExit(1)
