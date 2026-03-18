"""Config capture and apply commands."""

import os
import sys
import shutil
from pathlib import Path

import click

from setmac.output import emit_complete, emit_config_status, emit_error, emit_log, emit_progress
from setmac.registry import Registry


def _configs_dir() -> Path:
    """Get the configs directory in the project or app bundle."""
    if getattr(sys, "frozen", False):
        # Running inside .app bundle: Contents/MacOS/setmac -> Contents/Resources/configs
        return Path(os.path.dirname(sys.executable)).parent / "Resources" / "configs"
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
    configs_dir = _configs_dir()
    configs_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for tool, config in _all_configs(registry):
        source = Path(os.path.expanduser(config.source))
        target = configs_dir / config.target

        if not source.exists():
            emit_log(f"Skipping {config.source} (not found)", tool=tool.id)
            continue

        emit_progress(tool.id, f"Capturing {config.source}")

        target.parent.mkdir(parents=True, exist_ok=True)

        if config.is_dir:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target, ignore=shutil.ignore_patterns(
                "__pycache__", ".git", "*.pyc", "lazy-lock.json"
            ))
        else:
            shutil.copy2(source, target)

        emit_complete(tool.id)
        count += 1

    emit_log(f"Captured {count} config(s) to {configs_dir}")


@configs_cmd.command("apply")
@click.option("--dry-run", is_flag=True, help="Show what would be copied")
def apply(dry_run):
    """Apply bundled configs to system locations."""
    registry = Registry()
    configs_dir = _configs_dir()

    if not configs_dir.exists():
        emit_error("configs", "No configs directory found. Run 'setmac configs capture' first.")
        return

    backup_dir = Path(os.path.expanduser("~/.config/setmac-backup"))

    count = 0
    for tool, config in _all_configs(registry):
        source = configs_dir / config.target
        target = Path(os.path.expanduser(config.source))

        if not source.exists():
            emit_log(f"Skipping {config.target} (not in bundle)", tool=tool.id)
            continue

        if dry_run:
            emit_log(f"Would copy {source} -> {target}", tool=tool.id)
            continue

        # Backup existing
        if target.exists():
            backup_path = backup_dir / config.target
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            if config.is_dir:
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(target, backup_path)
            else:
                shutil.copy2(target, backup_path)
            emit_log(f"Backed up {target} -> {backup_path}", tool=tool.id)

        # Apply
        target.parent.mkdir(parents=True, exist_ok=True)
        if config.is_dir:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

        emit_complete(tool.id)
        count += 1

    if dry_run:
        emit_log(f"Dry run: {count} config(s) would be applied")
    else:
        emit_log(f"Applied {count} config(s). Backups in {backup_dir}")


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
