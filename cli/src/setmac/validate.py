"""Manifest validation rules.

Every rule reports a structured `Problem` so the CLI and the app can show
exactly which tool and field is wrong. `Registry.problems()` runs these and
refuses to load a manifest that has any.
"""

from __future__ import annotations

from dataclasses import dataclass
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


def validate_tools(tools: list[Tool]) -> list[Problem]:
    """All problems in a list of tools, in manifest order."""
    found: list[Problem] = []
    found += _unique_ids(tools)
    for tool in tools:
        found += _install_spec(tool)
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
