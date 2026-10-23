"""Config capture and apply commands."""

import filecmp
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import click

from setmac.output import emit_config_status, emit_error, emit_log
from setmac.registry import Registry


# Files that capture leaves out, so they never count as a difference either.
CAPTURE_IGNORE = ["__pycache__", ".git", "*.pyc", "lazy-lock.json"]


# Where a packaged build captures to: the app bundle is read-only and replaced on update.
USER_CONFIGS = Path(os.path.expanduser("~/Library/Application Support/setmac/configs"))


def _capture_dir() -> Path:
    """Where `capture` writes: the repo in dev mode, Application Support when packaged."""
    if getattr(sys, "frozen", False):
        return USER_CONFIGS
    return _configs_dir()


def _configs_dir() -> Path:
    """Where configs are read from. A packaged build prefers configs you captured."""
    if getattr(sys, "frozen", False):
        if USER_CONFIGS.exists():
            return USER_CONFIGS
        # Inside the .app: Contents/MacOS/setmac-cli -> Contents/Resources/configs.
        app_configs = Path(os.path.dirname(sys.executable)).parent / "Resources" / "configs"
        if app_configs.exists():
            return app_configs
        # Standalone setmac-cli: configs are embedded by PyInstaller.
        return Path(sys._MEIPASS) / "configs"
    # Dev mode: relative to source tree
    return Path(__file__).parent.parent.parent.parent.parent / "Resources" / "configs"


def _all_configs(registry: Registry):
    """Yield (tool, config_spec) for all tools that have configs."""
    for tool in registry.tools:
        for config in tool.configs:
            yield tool, config


@click.group("configs")
def configs_cmd():
    """Manage dotfiles and configuration files."""
    pass


@configs_cmd.command("capture")
def capture():
    """Capture current system configs into the project bundle."""
    registry = Registry()
    configs_dir = _capture_dir()
    configs_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for tool, config in _all_configs(registry):
        source = Path(os.path.expanduser(config.source))
        target = configs_dir / config.target

        if not source.exists():
            emit_log(f"Skipping {config.source} (not found)", tool=tool.id)
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if config.is_dir:
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target, ignore=shutil.ignore_patterns(*CAPTURE_IGNORE))
            else:
                shutil.copy2(source, target)
        except OSError as e:
            emit_error(tool.id, f"Could not capture {config.source}: {e}")
            continue

        emit_log(f"Captured {config.source}", tool=tool.id)
        count += 1

    emit_log(f"Captured {count} config(s) to {configs_dir}")


@configs_cmd.command("apply")
@click.option("--dry-run", is_flag=True, help="Show what would be copied")
def apply(dry_run):
    """Apply bundled configs to system locations."""
    apply_configs(Registry(), dry_run=dry_run)


def _same(a: Path, b: Path) -> bool:
    if a.is_dir() and b.is_dir():
        ignored = {p.name for pattern in CAPTURE_IGNORE for p in [*a.glob(pattern), *b.glob(pattern)]}
        cmp = filecmp.dircmp(a, b, ignore=sorted(ignored))
        return not (cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files) and all(
            _same(a / d, b / d) for d in cmp.common_dirs
        )
    if a.is_file() and b.is_file():
        return filecmp.cmp(a, b, shallow=False)
    return False


def apply_configs(registry: Registry, skip_tools: set[str] | None = None, dry_run: bool = False) -> int:
    """Copy bundled configs into place, backing up anything they replace.

    Configs belonging to tools in `skip_tools` (failed installs) are left alone,
    so a shell config never points at something that is not there.
    """
    configs_dir = _configs_dir()
    if not configs_dir.exists():
        emit_error("configs", f"No configs directory at {configs_dir}. Run 'setmac configs capture' first.")
        return 0

    skip_tools = skip_tools or set()
    backup_dir = Path(os.path.expanduser("~/.config/setmac-backup")) / datetime.now().strftime("%Y%m%d-%H%M%S")
    count = 0
    for tool, config in _all_configs(registry):
        source = configs_dir / config.target
        target = Path(os.path.expanduser(config.source))

        if tool.id in skip_tools:
            emit_log(f"Skipping {config.source}: {tool.name} did not install", tool=tool.id)
            continue
        if not source.exists():
            emit_log(f"Skipping {config.target} (not in bundle)", tool=tool.id)
            continue
        if target.exists() and _same(source, target):
            emit_log(f"{config.source} is already up to date", tool=tool.id)
            continue
        if dry_run:
            emit_log(f"Would copy {source} -> {target}", tool=tool.id)
            count += 1
            continue

        try:
            if target.exists() or target.is_symlink():
                backup_path = backup_dir / config.target
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(backup_path))
                emit_log(f"Backed up {target} -> {backup_path}", tool=tool.id)

            target.parent.mkdir(parents=True, exist_ok=True)
            if config.is_dir:
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
        except OSError as e:
            emit_error(tool.id, f"Could not apply {config.source}: {e}")
            continue

        emit_log(f"Applied {config.source}", tool=tool.id)
        count += 1

    if dry_run:
        emit_log(f"Dry run: {count} config(s) would be applied")
    else:
        emit_log(f"Applied {count} config(s). Backups in {backup_dir}" if count else "Configs already up to date")
    return count


@configs_cmd.command("list")
def list_configs():
    """List all config files and their status."""
    registry = Registry()
    configs_dir = _configs_dir()

    for tool, config in _all_configs(registry):
        source = Path(os.path.expanduser(config.source))
        bundled = (configs_dir / config.target).exists()
        system = source.exists()

        status = "bundled+system" if bundled and system else "bundled" if bundled else "system" if system else "missing"
        emit_config_status(tool.id, config.source, config.target, status)
        emit_log(f"[{status}] {config.source} -> {config.target}", tool=tool.id)
