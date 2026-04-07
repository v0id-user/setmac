"""Load and query the tools.json manifest."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CheckSpec:
    command: str | None = None
    path: str | None = None
    version_command: str | None = None


@dataclass
class InstallSpec:
    method: str  # brew_formula, brew_cask, script, custom, config
    target: str | None = None
    script: str | None = None
    url: str | None = None
    requires_admin: bool = False


@dataclass
class ConfigSpec:
    source: str
    target: str
    is_dir: bool = False


@dataclass
class Tool:
    id: str
    name: str
    description: str
    category: str
    icon: str
    icon_color: str
    depends_on: list[str]
    check: CheckSpec
    install: InstallSpec
    configs: list[ConfigSpec] = field(default_factory=list)
    versions: list[str] = field(default_factory=list)
    default_version: str | None = None


def _parse_tool(data: dict) -> Tool:
    check_data = data.get("check", {})
    install_data = data.get("install", {})
    configs_data = data.get("configs", [])

    return Tool(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        category=data.get("category", ""),
        icon=data.get("icon", ""),
        icon_color=data.get("icon_color", ""),
        depends_on=data.get("depends_on", []),
        check=CheckSpec(
            command=check_data.get("command"),
            path=check_data.get("path"),
            version_command=check_data.get("version_command"),
        ),
        install=InstallSpec(
            method=install_data.get("method", ""),
            target=install_data.get("target"),
            script=install_data.get("script"),
            url=install_data.get("url"),
            requires_admin=install_data.get("requires_admin", False),
        ),
        configs=[
            ConfigSpec(
                source=c["source"],
                target=c["target"],
                is_dir=c.get("is_dir", False),
            )
            for c in configs_data
        ],
        versions=data.get("versions", []),
        default_version=data.get("default_version"),
    )


class Registry:
    """Loads tools.json and provides query methods."""

    def __init__(self, manifest_path: Path | None = None):
        if manifest_path is None:
            if getattr(sys, "frozen", False):
                # Running as PyInstaller bundle
                manifest_path = Path(sys._MEIPASS) / "tools.json"
            else:
                # Dev mode: relative to source tree
                manifest_path = Path(__file__).parent.parent.parent.parent / "Resources" / "tools.json"

        with open(manifest_path) as f:
            data = json.load(f)

        self.version = data.get("version", "0.0.0")
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.tools: list[Tool] = [_parse_tool(t) for t in data.get("tools", [])]
        self._by_id: dict[str, Tool] = {t.id: t for t in self.tools}

    def get(self, tool_id: str) -> Tool | None:
        return self._by_id.get(tool_id)

    def by_category(self, category: str) -> list[Tool]:
        return [t for t in self.tools if t.category == category]

    def categories(self) -> list[str]:
        seen = []
        for t in self.tools:
            if t.category not in seen:
                seen.append(t.category)
        return seen

    def install_order(self, tool_ids: list[str] | None = None) -> list[Tool]:
        """Return tools in dependency-safe installation order (topological sort)."""
        if tool_ids is None:
            targets = set(t.id for t in self.tools)
        else:
            targets = set(tool_ids)
            # Add dependencies recursively
            queue = list(targets)
            while queue:
                tid = queue.pop(0)
                tool = self._by_id.get(tid)
                if tool:
                    for dep in tool.depends_on:
                        if dep not in targets:
                            targets.add(dep)
                            queue.append(dep)

        # Topological sort via Kahn's algorithm
        in_degree: dict[str, int] = {tid: 0 for tid in targets}
        for tid in targets:
            tool = self._by_id.get(tid)
            if tool:
                for dep in tool.depends_on:
                    if dep in targets:
                        in_degree[tid] = in_degree.get(tid, 0) + 1

        queue = [tid for tid in targets if in_degree.get(tid, 0) == 0]
        result: list[Tool] = []
        while queue:
            queue.sort()  # deterministic order
            tid = queue.pop(0)
            tool = self._by_id.get(tid)
            if tool:
                result.append(tool)
            for other_tid in targets:
                other = self._by_id.get(other_tid)
                if other and tid in other.depends_on:
                    in_degree[other_tid] -= 1
                    if in_degree[other_tid] == 0:
                        queue.append(other_tid)

        return result
