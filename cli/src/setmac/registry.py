"""Load and query the tools.json manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import click

from setmac import profile
from setmac.output import emit_profile_error
from setmac.validate import Problem, validate_tools

# Exit code when the active profile cannot be loaded or merged.
EXIT_PROFILE = 3


@dataclass
class CheckSpec:
    command: str | None = None
    path: str | None = None
    version_command: str | None = None


@dataclass
class InstallSpec:
    method: str  # brew_formula, brew_cask, mise, mas, defaults, script, custom, config
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
class DefaultSpec:
    """One `defaults write` setting."""

    domain: str
    key: str
    type: str  # bool, int, float, string
    value: bool | int | float | str
    current_host: bool = False


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
    defaults: list[DefaultSpec] = field(default_factory=list)
    # Apps to restart (killall) after defaults change, e.g. Dock, Finder.
    restart: list[str] = field(default_factory=list)
    # Manual step left after install, shown in the app (e.g. a permission to grant).
    post_install: str | None = None
    # Directory holding this tool's config files when they come from a profile.
    configs_root: Path | None = None


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
        defaults=[
            DefaultSpec(
                domain=d["domain"],
                key=d["key"],
                type=d["type"],
                value=d["value"],
                current_host=d.get("current_host", False),
            )
            for d in data.get("defaults", [])
        ],
        restart=data.get("restart", []),
        post_install=data.get("post_install"),
    )


class ManifestError(ValueError):
    """A manifest with problems; `problems` holds them as structured records."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("Invalid tools.json:\n  " + "\n  ".join(str(p) for p in problems))


class Registry:
    """Loads a manifest (the catalog, or a profile merged with it) and answers queries."""

    def __init__(
        self,
        manifest_path: Path | None = None,
        *,
        data: dict | None = None,
        configs_roots: dict[str, Path] | None = None,
        sensitive_ok: set[str] | None = None,
    ):
        if data is None:
            with open(manifest_path or profile.catalog_path()) as f:
                data = json.load(f)

        self.version = data.get("version", "0.0.0")
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.data = data
        self.sensitive_ok = sensitive_ok or set()
        self.tools: list[Tool] = [_parse_tool(t) for t in data.get("tools", [])]
        for tool in self.tools:
            tool.configs_root = (configs_roots or {}).get(tool.id)
        self._by_id: dict[str, Tool] = {t.id: t for t in self.tools}
        problems = self.validation_problems()
        if problems:
            raise ManifestError(problems)

    @classmethod
    def for_profile(cls, spec: str | None = None) -> Registry:
        """The active profile (or `spec`) merged with the catalog."""
        resolved = profile.resolve(spec)
        return cls(data=resolved.manifest, configs_roots=resolved.configs_roots, sensitive_ok=resolved.sensitive_ok)

    def problems(self) -> list[str]:
        """Manifest mistakes that would break installing, one message each."""
        return [str(p) for p in self.validation_problems()]

    def validation_problems(self) -> list[Problem]:
        """Manifest mistakes as structured {code, tool_id, field, message} records."""
        return validate_tools(self.tools, sensitive_ok=self.sensitive_ok)

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


def get_registry(ctx: click.Context | None = None) -> Registry:
    """The registry for the active profile: `--profile`, SETMAC_PROFILE, the pointer, or minimal.

    A profile that cannot be used is reported as a `profile_error` event and exits 3.
    """
    root = ctx.find_root() if ctx else None
    flag = (root.obj or {}).get("profile") if root else None
    spec, _ = profile.active_spec(flag)
    try:
        return Registry.for_profile(spec)
    except (profile.ProfileError, ManifestError) as e:
        emit_profile_error(spec, e.problems)
        raise SystemExit(EXIT_PROFILE) from e
