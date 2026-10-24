"""Profile commands: see, choose and check which tools setmac installs."""

from __future__ import annotations

import json
import sys

import click

from pathlib import Path

from setmac import export, gitprofile, profile, trust
from setmac.output import emit_manifest, emit_profile_error, emit_profiles, emit_review
from setmac.registry import EXIT_PROFILE, ManifestError, Registry


def _spec(ctx: click.Context, spec: str | None) -> str:
    """The spec given to the command, else the active one (--profile, env, pointer, default)."""
    if spec:
        return spec
    return profile.active_spec((ctx.find_root().obj or {}).get("profile"))[0]


def _resolve(spec: str) -> tuple[profile.Resolved, Registry]:
    resolved = profile.resolve(spec)
    return resolved, _registry(resolved)


def _registry(resolved: profile.Resolved) -> Registry:
    return Registry(data=resolved.manifest, configs_roots=resolved.configs_roots, sensitive_ok=resolved.sensitive_ok)


def _resolve_or_exit(spec: str) -> tuple[profile.Resolved, Registry]:
    try:
        return _resolve(spec)
    except (profile.ProfileError, ManifestError) as e:
        emit_profile_error(spec, e.problems)
        raise SystemExit(EXIT_PROFILE) from e


def _confirm(question: str, expected_hash: str | None, actual_hash: str) -> None:
    """Ask on a terminal; without one, require the content hash the user reviewed."""
    if expected_hash is not None:
        if expected_hash != actual_hash:
            raise click.ClickException(f"the profile's content is {actual_hash}, not {expected_hash}; review it again")
        return
    if not sys.stdin.isatty():
        raise click.ClickException("no terminal to confirm on: pass --hash with the content hash `profile review` printed")
    click.confirm(question, abort=True)


@click.group("profile")
def profile_cmd():
    """Choose which tools setmac installs."""


@profile_cmd.command("list")
@click.option("--json", "as_json", is_flag=True, help="Print a `profiles` event")
@click.pass_context
def list_profiles(ctx: click.Context, as_json: bool):
    """List the starter profiles and show which profile is active."""
    spec, source = profile.active_spec((ctx.find_root().obj or {}).get("profile"))
    starters = [{"name": p.name, "description": p.data.get("description", "")} for p in profile.starters()]
    if as_json:
        emit_profiles(spec, source, starters)
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
        ident = trust.identity(resolved)
        emit_manifest(resolved.profile.name, resolved.manifest, spec=spec, trusted=trust.is_trusted(resolved),
                      content_hash=ident["content_hash"] if ident else None)
        return
    click.echo(" -> ".join(p.name for p in resolved.chain))
    click.echo(f"{len(registry.tools)} tools, in install order:")
    for tool in registry.install_order():
        click.echo(f"  {tool.id:22} {tool.install.method:12} {tool.name}")


@profile_cmd.command("use")
@click.argument("spec")
def use(spec: str):
    """Make SPEC the active profile (a starter name or a profile directory)."""
    resolved, registry = _resolve_or_exit(spec)
    profile.write_pointer(spec)
    click.echo(f"Active profile is now {resolved.profile.name} ({len(registry.tools)} tools).")
    if not trust.is_trusted(resolved):
        click.echo(f"It is not trusted yet: run `setmac profile review {spec}`, then `setmac profile trust {spec}`.")


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


@profile_cmd.command("review")
@click.argument("spec", required=False)
@click.option("--json", "as_json", is_flag=True, help="Print a `review` event")
@click.pass_context
def review(ctx: click.Context, spec: str | None, as_json: bool):
    """Print everything a profile would run or write, verbatim."""
    spec = _spec(ctx, spec)
    resolved, registry = _resolve_or_exit(spec)
    if as_json:
        ident = trust.identity(resolved)
        emit_review(spec, trust.review(resolved, registry), ident["content_hash"] if ident else None,
                    trust.is_trusted(resolved))
        return
    click.echo(trust.review(resolved, registry))
    click.echo("")
    if trust.is_trusted(resolved):
        click.echo("Trusted.")
    else:
        click.echo(f"Not trusted yet. To trust exactly this content: setmac profile trust {spec}")


@profile_cmd.command("trust")
@click.argument("spec", required=False)
@click.option("--hash", "expected", metavar="CONTENT_HASH", help="Trust only this exact content (needed without a terminal)")
@click.pass_context
def trust_profile(ctx: click.Context, spec: str | None, expected: str | None):
    """Allow setmac to run this profile's commands and write its dotfiles."""
    spec = _spec(ctx, spec)
    resolved, registry = _resolve_or_exit(spec)
    ident = trust.identity(resolved)
    if ident is None:
        click.echo(f"{spec} is a bundled starter; it is always trusted.")
        return
    if trust.is_trusted(resolved):
        click.echo(f"{spec} is already trusted.")
        return
    if expected is None and sys.stdin.isatty():
        click.echo(trust.review(resolved, registry) + "\n")
    _confirm("Trust this profile?", expected, ident["content_hash"])
    trust.record(resolved)
    click.echo(f"Trusted {spec} (content {ident['content_hash'][:12]}).")


@profile_cmd.command("update")
@click.argument("spec", required=False)
@click.option("--hash", "expected", metavar="CONTENT_HASH", help="Accept only this exact new content (needed without a terminal)")
@click.pass_context
def update(ctx: click.Context, spec: str | None, expected: str | None):
    """Move a git profile to the latest commit of its ref (or SPEC's #ref), after review."""
    spec = _spec(ctx, spec)
    if not gitprofile.is_git_url(spec):
        raise click.ClickException(f"{spec} is not a git profile; edit the folder and run `setmac profile trust` again")
    try:
        path, candidate, current = gitprofile.fetch_latest(spec, profile.STATE_DIR)
        located = profile.Located(path, "git", spec, candidate)
        resolved = profile.merge(profile.chain_at(located), json.loads(profile.catalog_path().read_text()), located)
        registry = _registry(resolved)
    except gitprofile.GitProfileError as e:
        emit_profile_error(spec, [e.problem])
        raise SystemExit(EXIT_PROFILE) from e
    except (profile.ProfileError, ManifestError) as e:
        emit_profile_error(spec, e.problems)
        raise SystemExit(EXIT_PROFILE) from e
    if current and current.sha == candidate.sha:
        click.echo(f"{candidate.url} is up to date at {candidate.sha[:12]}.")
        return
    click.echo(f"{candidate.url}: {current.sha[:12] if current else '(not locked)'} -> {candidate.sha[:12]}")
    if current:
        click.echo(gitprofile.diff_stat(profile.STATE_DIR, candidate.url, current.sha, candidate.sha))
    click.echo("")
    if expected is None and sys.stdin.isatty():
        click.echo(trust.review(resolved, registry) + "\n")
    _confirm("Move the lock to this commit and trust it?", expected, candidate.content_hash)
    gitprofile.write_lock(gitprofile.cache_root(profile.STATE_DIR, candidate.url), candidate)
    trust.record(resolved)
    click.echo(f"Locked {candidate.url} to {candidate.sha[:12]} and trusted it.")


@profile_cmd.command("export")
@click.option("--from-ref", "refs", multiple=True, required=True, metavar="REF",
              help="Git ref whose Resources/tools.json and Resources/configs hold the old setup (repeatable)")
@click.option("--repo", type=click.Path(file_okay=False, path_type=Path), default=".", help="Repository holding the refs")
@click.option("--out", type=click.Path(path_type=Path), required=True, help="New profile folder (outside the setmac repo)")
@click.option("--name", default="me", help="Profile name")
@click.option("--extends", "extends", default="minimal", help="Starter to build on")
@click.option("--home/--no-home", "use_home", default=True, help="Prefer the dotfiles on this Mac over the refs' copies")
@click.option("--accept-reviewed", is_flag=True, help="Write despite medium scanner findings you have reviewed")
def export_profile(refs, repo, out, name, extends, use_home, accept_reviewed):
    """Turn an old all-in-one setup (git refs) into a private profile folder."""
    try:
        report = export.build(repo, list(refs), out, name, extends, use_home, accept_reviewed)
    except export.ExportError as e:
        raise click.ClickException(str(e)) from e
    click.echo(f"Wrote {out}")
    click.echo(f"  {len(report.custom)} custom tools: {', '.join(report.custom) or '-'}")
    click.echo(f"  {len(report.added)} catalog tools added back")
    click.echo(f"  dotfiles from this Mac: {', '.join(report.from_home) or '-'}")
    click.echo(f"  dotfiles from the refs: {', '.join(report.from_ref) or '-'}")
    if report.differs:
        click.echo(f"  newer on this Mac than in the refs: {', '.join(report.differs)}")
    for line in report.dropped:
        click.echo(f"  dropped: {line}")
    for finding in report.findings:
        click.echo(f"  reviewed: {finding.describe()}")
    for line in report.shell_checks:
        click.echo(f"  {line}")
    click.echo("A git repository was initialised; review the files, then make the first signed commit yourself.")
