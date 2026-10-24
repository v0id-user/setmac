"""Dotfiles: see what differs, apply chosen files with a backup, restore, and capture.

Dotfiles come only from the active profile: a config's `source` is the file on the Mac
(`~/...`) and its `target` is the copy under the profile's configs_dir. Nothing is
replaced without being chosen: on a terminal each file is confirmed, otherwise `--yes`
is required. Every replaced file is moved to ~/.config/setmac-backup/<timestamp>/ with a
manifest, so `configs restore` can undo an apply.
"""

from __future__ import annotations

import difflib
import filecmp
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import click

from setmac import scanner
from setmac.output import emit_config_status, emit_configs, emit_error, emit_log
from setmac.registry import Registry, Tool, get_registry

# Files capture leaves out, so they never count as a difference either.
CAPTURE_IGNORE = ["__pycache__", ".git", "*.pyc", "lazy-lock.json", ".DS_Store"]
# The public setmac repository: a profile inside a clone of it must never receive captures.
PUBLIC_REPO_NAMES = ("v0id-user/setmac", "v0id-user/setmac.git")


def backup_root() -> Path:
    return Path(os.path.expanduser("~/.config/setmac-backup"))


def _new_backup_dir(suffix: str = "") -> Path:
    """A backup folder named by the time, never reusing an existing name."""
    base = datetime.now().strftime("%Y%m%d-%H%M%S") + suffix
    path, n = backup_root() / base, 2
    while path.exists():
        path, n = backup_root() / f"{base}-{n}", n + 1
    return path


@dataclass
class Entry:
    id: str
    tool: Tool
    source: str  # ~/... on the Mac
    target: str  # path under the profile's configs_dir
    is_dir: bool

    @property
    def live(self) -> Path:
        return Path(os.path.expanduser(self.source))

    @property
    def stored(self) -> Path | None:
        return self.tool.configs_root / self.target if self.tool.configs_root else None

    def status(self) -> str:
        if not (self.live.exists() or self.live.is_symlink()):
            return "missing"
        return "identical" if self.stored and _same(self.stored, self.live) else "differs"


def entries(registry: Registry) -> list[Entry]:
    found = [Entry(c.target, t, c.source, c.target, c.is_dir) for t in registry.tools for c in t.configs]
    ids = [e.id for e in found]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise click.ClickException("two configs share a target: " + ", ".join(duplicates))
    return found


def _select(all_entries: list[Entry], only: str | None) -> list[Entry]:
    if not only:
        return all_entries
    wanted = [i.strip() for i in only.split(",") if i.strip()]
    unknown = [i for i in wanted if i not in {e.id for e in all_entries}]
    if unknown:
        raise click.ClickException(f"no config with id {', '.join(unknown)} (see `setmac configs list`)")
    return [e for e in all_entries if e.id in wanted]


def _ignored(name: str, rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(rel, p) for p in patterns)


def _same(a: Path, b: Path, patterns: list[str] = CAPTURE_IGNORE) -> bool:
    if a.is_symlink() or b.is_symlink():
        return a.is_symlink() and b.is_symlink() and os.readlink(a) == os.readlink(b)
    if a.is_dir() and b.is_dir():
        names = {*os.listdir(a), *os.listdir(b)}
        cmp = filecmp.dircmp(a, b, ignore=[n for n in names if _ignored(n, n, patterns)])
        return not (cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files) and all(
            _same(a / d, b / d, patterns) for d in cmp.common_dirs
        )
    if a.is_file() and b.is_file():
        return filecmp.cmp(a, b, shallow=False)
    return False


def _copy(src: Path, dst: Path, patterns: list[str] | None = None) -> None:
    """Copy without following symlinks, keeping modes."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
        os.symlink(os.readlink(src), dst)
    elif src.is_dir():
        ignore = None
        if patterns:
            def ignore(directory, names):
                rel = Path(directory).relative_to(src)
                return [n for n in names if _ignored(n, (rel / n).as_posix(), patterns)]
        shutil.copytree(src, dst, symlinks=True, ignore=ignore)
    else:
        shutil.copy2(src, dst, follow_symlinks=False)


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text().splitlines(keepends=True) if path.is_file() else []
    except UnicodeDecodeError:
        return ["(binary file)\n"]


def _diff_text(old: Path, new: Path, old_label: str, new_label: str) -> str:
    """Unified diff for files; for folders, each differing file's diff or which side has it."""
    if not (old.is_dir() or new.is_dir()):
        return "".join(difflib.unified_diff(_read_lines(old), _read_lines(new), old_label, new_label))
    names = sorted({p.relative_to(root).as_posix() for root in (old, new) if root.is_dir()
                    for p in root.rglob("*") if p.is_file()})
    parts = []
    for name in names:
        a, b = old / name, new / name
        if a.is_file() and b.is_file():
            if not filecmp.cmp(a, b, shallow=False):
                parts.append(_diff_text(a, b, f"{old_label}/{name}", f"{new_label}/{name}"))
        else:
            parts.append(f"only in {new_label if b.is_file() else old_label}: {name}\n")
    return "".join(parts)


def _profile_root(registry: Registry) -> Path | None:
    resolved = getattr(registry, "resolved", None)
    return resolved.source.path if resolved else None


@click.group("configs")
def configs_cmd():
    """Manage dotfiles and configuration files."""


@configs_cmd.command("list")
@click.option("--json", "as_json", is_flag=True, help="Print a `configs` event: id, tool, source, target, status")
@click.pass_context
def list_configs(ctx, as_json):
    """List the profile's dotfiles and whether each matches the file on this Mac."""
    found = entries(get_registry(ctx))
    if as_json:
        emit_configs([{"id": e.id, "tool": e.tool.id, "source": e.source, "target": e.target,
                       "is_dir": e.is_dir, "status": e.status()} for e in found])
        return
    for e in found:
        stored = bool(e.stored and e.stored.exists())
        system = e.live.exists()
        legacy = "bundled+system" if stored and system else "bundled" if stored else "system" if system else "missing"
        emit_config_status(e.tool.id, e.source, e.target, legacy)
        emit_log(f"[{e.status()}] {e.source}  ({e.id})", tool=e.tool.id)


@configs_cmd.command("diff")
@click.argument("config_id")
@click.pass_context
def diff(ctx, config_id):
    """Show how the file on this Mac differs from the profile's copy."""
    entry = _select(entries(get_registry(ctx)), config_id)[0]
    if entry.stored is None:
        raise click.ClickException(f"{config_id} has no copy in the profile")
    text = _diff_text(entry.live, entry.stored, entry.source, f"profile/{entry.target}")
    click.echo(text or f"{entry.source} matches the profile.", nl=not text)


@configs_cmd.command("apply")
@click.option("--only", metavar="IDS", help="Comma-separated config ids (see `configs list`)")
@click.option("--yes", "assume_yes", is_flag=True, help="Replace without asking (required without a terminal)")
@click.option("--dry-run", is_flag=True, help="Show what would change")
@click.pass_context
def apply(ctx, only, assume_yes, dry_run):
    """Copy the profile's dotfiles into place, backing up what they replace."""
    apply_configs(get_registry(ctx, require_trust=True), only=only, assume_yes=assume_yes, dry_run=dry_run)


def apply_configs(
    registry: Registry,
    skip_tools: set[str] | None = None,
    dry_run: bool = False,
    only: str | None = None,
    assume_yes: bool = False,
) -> int:
    """Apply chosen configs. Returns how many were (or would be) applied.

    Configs of tools in `skip_tools` (failed installs) are left alone, so a shell config
    never points at something that is not there.
    """
    chosen = _select(entries(registry), only)
    interactive = sys.stdin.isatty() and not assume_yes
    if not (dry_run or assume_yes or interactive):
        raise click.ClickException("no terminal to confirm on: pass --yes (and --only to pick files)")

    stored = [e for e in chosen if e.stored and e.stored.exists()]
    findings = [f for e in stored for f in scanner.scan(e.stored, e.target)]
    blocked = scanner.blocking(findings, scanner.load_allow(_profile_root(registry)), accept_medium=True)
    if blocked:
        for f in blocked:
            emit_error("configs", f.describe())
        raise click.ClickException(f"{len(blocked)} secret(s) found in the profile's dotfiles; nothing was applied")

    backup_dir = _new_backup_dir()
    stamp = backup_dir.name
    manifest: list[dict] = []
    count = 0
    for entry in chosen:
        tool = entry.tool
        if tool.id in (skip_tools or set()):
            emit_log(f"Skipping {entry.source}: {tool.name} did not install", tool=tool.id)
            continue
        if entry.stored is None or not entry.stored.exists():
            emit_log(f"Skipping {entry.source}: not in the profile", tool=tool.id)
            continue
        status = entry.status()
        if status == "identical":
            emit_log(f"{entry.source} is already up to date", tool=tool.id)
            continue
        verb = "replace" if status == "differs" else "create"
        if dry_run:
            emit_log(f"Would {verb} {entry.source} ({entry.id})", tool=tool.id)
            count += 1
            continue
        if interactive:
            click.echo(_diff_text(entry.live, entry.stored, entry.source, f"profile/{entry.target}"), err=True)
            if not click.confirm(f"{verb.capitalize()} {entry.source}?", default=False, err=True):
                emit_log(f"Left {entry.source} unchanged", tool=tool.id)
                continue
        try:
            backup = None
            if status == "differs":
                backup = backup_dir / entry.id
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(entry.live), str(backup))
                emit_log(f"Backed up {entry.live} -> {backup}", tool=tool.id)
            _copy(entry.stored, entry.live)
        except OSError as e:
            emit_error(tool.id, f"Could not apply {entry.source}: {e}")
            continue
        manifest.append({"id": entry.id, "source": entry.source, "backup": entry.id if backup else None})
        emit_log(f"Applied {entry.source}", tool=tool.id)
        count += 1

    if manifest:
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "manifest.json").write_text(json.dumps({"created": stamp, "entries": manifest}, indent=2) + "\n")
    if dry_run:
        emit_log(f"Dry run: {count} config(s) would be applied")
    elif count:
        emit_log(f"Applied {count} config(s). Undo with `setmac configs restore {stamp}`")
    else:
        emit_log("Nothing applied")
    return count


@configs_cmd.command("backups")
def backups():
    """List the backups that `configs apply` and `configs restore` made."""
    found = sorted(backup_root().glob("*/manifest.json"), reverse=True)
    if not found:
        click.echo("No backups.")
    for path in found:
        data = json.loads(path.read_text())
        click.echo(f"{path.parent.name}: " + ", ".join(e["id"] for e in data["entries"]))


@configs_cmd.command("restore")
@click.argument("stamp")
@click.option("--only", metavar="IDS", help="Comma-separated config ids to restore")
def restore(stamp, only):
    """Undo an apply: put back the files from backup STAMP (or `latest`).

    Files the apply created are removed. The current files are backed up first.
    """
    root = backup_root()
    if stamp == "latest":
        stamps = sorted(p.parent.name for p in root.glob("*/manifest.json") if "-before-restore" not in p.parent.name)
        if not stamps:
            raise click.ClickException("no backups to restore")
        stamp = stamps[-1]
    path = root / stamp / "manifest.json"
    if not path.is_file():
        raise click.ClickException(f"no backup named {stamp} (see `setmac configs backups`)")
    items = json.loads(path.read_text())["entries"]
    if only:
        wanted = {i.strip() for i in only.split(",")}
        items = [i for i in items if i["id"] in wanted]

    safety = _new_backup_dir("-before-restore")
    saved = []
    for item in items:
        live = Path(os.path.expanduser(item["source"]))
        present = live.exists() or live.is_symlink()
        if present:
            _copy(live, safety / item["id"])
        saved.append({"id": item["id"], "source": item["source"], "backup": item["id"] if present else None})
    if saved:
        safety.mkdir(parents=True, exist_ok=True)
        (safety / "manifest.json").write_text(json.dumps({"created": safety.name, "entries": saved}, indent=2) + "\n")

    for item in items:
        live = Path(os.path.expanduser(item["source"]))
        _remove(live)
        if item["backup"]:
            _copy(root / stamp / item["backup"], live)
            emit_log(f"Restored {item['source']}")
        else:
            emit_log(f"Removed {item['source']} (it did not exist before)")
    emit_log(f"Restored {len(items)} config(s) from {stamp}. What they replaced is in {safety.name}")


def _inside_public_repo(path: Path) -> bool:
    try:
        url = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return False
    return url.removesuffix("/").endswith(PUBLIC_REPO_NAMES)


def _ignore_patterns(profile_root: Path) -> list[str]:
    patterns = list(CAPTURE_IGNORE)
    for path in (profile_root / ".setmacignore", Path(os.path.expanduser("~/.config/setmac/ignore"))):
        try:
            patterns += [line.strip() for line in path.read_text().splitlines()
                         if line.strip() and not line.startswith("#")]
        except OSError:
            pass
    return patterns


@configs_cmd.command("capture")
@click.argument("config_ids", nargs=-1)
@click.option("--accept-medium", is_flag=True, help="Capture despite emails, home paths and other personal data")
@click.pass_context
def capture(ctx, config_ids, accept_medium):
    """Copy dotfiles from this Mac into your own profile (all, or CONFIG_IDS).

    Only into a local profile folder: never a starter, a pinned git checkout, or a clone
    of the public setmac repository. Everything is scanned for secrets first.
    """
    registry = get_registry(ctx, require_trust=True)
    source = registry.resolved.source
    if source.kind == "starter":
        raise click.ClickException("the active profile is a bundled starter; capture into your own profile folder")
    if source.kind == "git":
        raise click.ClickException("the active profile is a pinned git checkout; capture into a local clone of it and push")
    if _inside_public_repo(source.path):
        raise click.ClickException(f"{source.path} is inside a clone of the public setmac repository; use a private profile")

    chosen = _select(entries(registry), ",".join(config_ids) if config_ids else None)
    patterns = _ignore_patterns(source.path)
    with tempfile.TemporaryDirectory() as staging_dir:
        staging = Path(staging_dir)
        staged: list[tuple[Entry, Path]] = []
        for entry in chosen:
            if not (entry.live.exists() or entry.live.is_symlink()):
                emit_log(f"Skipping {entry.source} (not on this Mac)", tool=entry.tool.id)
                continue
            if _ignored(entry.live.name, entry.target, patterns):
                emit_log(f"Skipping {entry.source} (ignored)", tool=entry.tool.id)
                continue
            if entry.stored is None:
                emit_error(entry.tool.id, f"{entry.tool.id} has no configs_dir to capture into")
                continue
            copy = staging / entry.id
            _copy(entry.live, copy, patterns)
            staged.append((entry, copy))

        findings = [f for entry, copy in staged for f in scanner.scan(copy, entry.target)]
        blocked = scanner.blocking(findings, scanner.load_allow(source.path), accept_medium=accept_medium)
        if blocked:
            for f in blocked:
                emit_error("configs", f.describe())
            raise click.ClickException(f"{len(blocked)} finding(s) block the capture; nothing was written")

        for entry, copy in staged:
            _remove(entry.stored)
            _copy(copy, entry.stored)
            emit_log(f"Captured {entry.source} -> {entry.stored}", tool=entry.tool.id)
    emit_log(f"Captured {len(staged)} config(s). The profile changed, so trust it again: `setmac profile trust`")
