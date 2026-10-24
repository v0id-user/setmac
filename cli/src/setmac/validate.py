"""Manifest validation rules.

Every rule reports a structured `Problem` so the CLI and the app can show
exactly which tool and field is wrong. `Registry.problems()` runs these and
refuses to load a manifest that has any.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from setmac.installers import METHODS, SELF_CHECKING

if TYPE_CHECKING:
    from setmac.registry import Tool


@dataclass(frozen=True)
class Problem:
    code: str
    tool_id: str | None
    field: str | None
    message: str

    def __str__(self) -> str:
        return self.message


# Dotfile locations a profile may only write to when it lists them in `sensitive_ok`.
SENSITIVE = ("~/.ssh", "~/.gnupg", "~/.aws", "~/Library/LaunchAgents", "~/.config/gh")


def validate_tools(tools: list[Tool], sensitive_ok: set[str] | frozenset[str] = frozenset()) -> list[Problem]:
    """All problems in a list of tools, in manifest order."""
    found: list[Problem] = []
    found += _unique_ids(tools)
    for tool in tools:
        found += _install_spec(tool)
        found += _configs(tool, sensitive_ok)
    known = {t.id for t in tools}
    for tool in tools:
        for dep in tool.depends_on:
            if dep not in known:
                found.append(Problem(
                    "unknown_dependency", tool.id, "depends_on",
                    f"'{tool.id}' depends on unknown tool '{dep}'",
                ))
    if not found:
        found += _cycles(tools)
    return found


def _unique_ids(tools: list[Tool]) -> list[Problem]:
    found: list[Problem] = []
    seen: set[str] = set()
    for tool in tools:
        if tool.id in seen:
            found.append(Problem("duplicate_id", tool.id, "id", f"duplicate tool id '{tool.id}'"))
        seen.add(tool.id)
    return found


def _install_spec(tool: Tool) -> list[Problem]:
    method = tool.install.method
    if method not in METHODS:
        allowed = ", ".join(sorted(METHODS))
        return [Problem(
            "unknown_method", tool.id, "install.method",
            f"'{tool.id}' uses unknown install method '{method}' (expected one of: {allowed})",
        )]

    found: list[Problem] = []
    for name in METHODS[method]:
        if not getattr(tool.install, name):
            found.append(Problem(
                "missing_field", tool.id, f"install.{name}",
                f"'{tool.id}' ({method}) needs install.{name}",
            ))
    if method in ("script", "custom") and not (tool.install.script or tool.install.url):
        found.append(Problem(
            "missing_field", tool.id, "install.script",
            f"'{tool.id}' ({method}) needs install.script or install.url",
        ))
    if method == "defaults" and not tool.defaults:
        found.append(Problem(
            "missing_field", tool.id, "defaults",
            f"'{tool.id}' (defaults) needs a non-empty defaults list",
        ))
    # Config entries are applied by the configs step and never checked.
    if method not in SELF_CHECKING and method != "config" and not (tool.check.command or tool.check.path):
        found.append(Problem(
            "missing_field", tool.id, "check",
            f"'{tool.id}' ({method}) needs check.command or check.path",
        ))
    return found


def _configs(tool: Tool, sensitive_ok: set[str] | frozenset[str]) -> list[Problem]:
    """A config's `source` is where it lives on the Mac (~/...); its `target` is the
    copy under the profile's configs_dir. Neither may escape where it belongs."""
    found: list[Problem] = []
    home = os.path.realpath(os.path.expanduser("~"))
    for i, config in enumerate(tool.configs):
        field = f"configs[{i}]"
        source = config.source
        if not source.startswith("~/") or os.path.normpath(source) != source or ".." in Path(source).parts:
            found.append(Problem(
                "invalid_config_source", tool.id, f"{field}.source",
                f"'{tool.id}' config source must be a plain ~/ path, got '{source}'",
            ))
        else:
            if _escapes(os.path.expanduser(source), home):
                found.append(Problem(
                    "config_outside_home", tool.id, f"{field}.source",
                    f"'{tool.id}' config source '{source}' resolves outside your home directory",
                ))
            if _is_sensitive(source) and not any(_within(source, ok) for ok in sensitive_ok):
                found.append(Problem(
                    "sensitive_config", tool.id, f"{field}.source",
                    f"'{tool.id}' writes to '{source}', a sensitive location; list it in the profile's sensitive_ok to allow it",
                ))
        target = config.target
        if os.path.isabs(target) or ".." in Path(target).parts or not target:
            found.append(Problem(
                "invalid_config_target", tool.id, f"{field}.target",
                f"'{tool.id}' config target must be a path inside the configs folder, got '{target}'",
            ))
        elif tool.configs_root is not None:
            stored = tool.configs_root / target
            if not stored.exists():
                found.append(Problem(
                    "missing_config_file", tool.id, f"{field}.target",
                    f"'{tool.id}' config '{target}' is not in {tool.configs_root}",
                ))
            elif _escapes(str(stored), os.path.realpath(tool.configs_root)):
                found.append(Problem(
                    "config_outside_profile", tool.id, f"{field}.target",
                    f"'{tool.id}' config '{target}' resolves outside {tool.configs_root}",
                ))
    return found


def _within(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix.rstrip("/") + "/")


def _is_sensitive(source: str) -> bool:
    return any(_within(source, s) for s in SENSITIVE)


def _escapes(path: str, root: str) -> bool:
    """Whether the longest existing part of `path`, with symlinks resolved, is outside `root`."""
    existing = Path(path)
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    return not _within(os.path.realpath(existing), root)


def _cycles(tools: list[Tool]) -> list[Problem]:
    """Tools that can never be ordered because their dependencies loop."""
    remaining = {t.id: set(t.depends_on) for t in tools}
    while True:
        ready = [tid for tid, deps in remaining.items() if not deps]
        if not ready:
            break
        for tid in ready:
            del remaining[tid]
        for deps in remaining.values():
            deps.difference_update(ready)
    if not remaining:
        return []
    stuck = sorted(remaining)
    return [Problem(
        "dependency_cycle", stuck[0], "depends_on",
        "dependency cycle among: " + ", ".join(stuck),
    )]
