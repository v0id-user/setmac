"""Profiles: which catalog tools to install, plus a person's own tools and dotfiles.

A profile is a directory holding `profile.json` (schema 1). The catalog
(`Resources/tools.json`) defines every public tool; a profile picks from it,
extends another profile, overrides catalog entries, and adds its own tools.

Which profile is active, first match wins:
  1. `--profile <spec>` on the command line
  2. the SETMAC_PROFILE environment variable
  3. the pointer file written by `setmac profile use`
  4. the built-in `minimal` starter

A spec is a starter name (`web`), an absolute or `~` path to a profile directory, or a
git URL with an optional `#<branch, tag or sha>` (see gitprofile.py). Profiles that are
not bundled starters must be trusted before setmac runs anything from them (trust.py).
"""

from __future__ import annotations

import copy
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from setmac import gitprofile
from setmac.validate import Problem

SCHEMA = 1
DEFAULT_PROFILE = "minimal"
# How many `extends` hops a profile may take before it reaches its root.
MAX_EXTENDS = 3
STATE_DIR = Path(os.path.expanduser("~/Library/Application Support/setmac"))
POINTER = STATE_DIR / "active-profile"

PROFILE_KEYS = {
    "schema", "name", "description", "extends", "tools", "overrides", "custom_tools",
    "categories", "configs_dir", "macos_defaults", "sensitive_ok", "notes", "metadata",
}
# Defaults filled into every tool of a merged manifest, so the app can always decode it.
TOOL_DEFAULTS = {"description": "", "category": "other", "icon": "shippingbox", "icon_color": "gray", "depends_on": []}


class ProfileError(Exception):
    """A profile that cannot be used, with every problem found."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("\n".join(str(p) for p in problems))


@dataclass
class Profile:
    name: str
    root: Path
    data: dict
    bundled: bool

    @property
    def extends(self) -> str | None:
        return self.data.get("extends")

    @property
    def configs_root(self) -> Path | None:
        configs_dir = self.data.get("configs_dir")
        return self.root / configs_dir if configs_dir else None


@dataclass
class Located:
    """Where a spec points: a bundled starter, a local directory, or a pinned git checkout."""

    path: Path
    kind: str  # "starter", "dir" or "git"
    spec: str
    lock: gitprofile.Lock | None = None

    @property
    def bundled(self) -> bool:
        return self.kind == "starter"


@dataclass
class Resolved:
    """A profile merged with the catalog: the manifest the CLI and the app use."""

    chain: list[Profile]
    source: Located
    manifest: dict
    # Where each tool's config files live, for tools whose configs come from a profile.
    configs_roots: dict[str, Path] = field(default_factory=dict)
    sensitive_ok: set[str] = field(default_factory=set)

    @property
    def profile(self) -> Profile:
        return self.chain[-1]


# ─── Locations ────────────────────────────────────────────────


def _resources() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent.parent / "Resources"


def catalog_path() -> Path:
    return _resources() / "tools.json"


def starters_dir() -> Path:
    return _resources() / "profiles"


def starters() -> list[Profile]:
    found = []
    for path in sorted(starters_dir().glob("*/profile.json")):
        found.append(load(path.parent, bundled=True))
    return found


# ─── Choosing the active profile ──────────────────────────────


def active_spec(flag: str | None = None) -> tuple[str, str]:
    """(spec, where it came from): flag, env, pointer or default."""
    if flag:
        return flag, "flag"
    env = os.environ.get("SETMAC_PROFILE", "").strip()
    if env:
        return env, "env"
    pointer = read_pointer()
    if pointer:
        return pointer, "pointer"
    return DEFAULT_PROFILE, "default"


def read_pointer() -> str | None:
    try:
        return POINTER.read_text().strip() or None
    except OSError:
        return None


def write_pointer(spec: str) -> None:
    POINTER.parent.mkdir(parents=True, exist_ok=True)
    POINTER.write_text(spec + "\n")


def locate(spec: str) -> Located:
    """The directory a spec points at. A git spec is cloned and pinned on first use."""
    if gitprofile.is_git_url(spec):
        try:
            path, lock = gitprofile.checkout(spec, STATE_DIR)
        except gitprofile.GitProfileError as e:
            raise ProfileError([e.problem]) from e
        if not (path / "profile.json").is_file():
            raise ProfileError([Problem("profile_not_found", None, "profile", f"{spec} has no profile.json at its root")])
        return Located(path, "git", spec, lock)
    if "/" in spec or spec.startswith("~"):
        path = Path(os.path.expanduser(spec))
        if not path.is_absolute():
            raise ProfileError([Problem("relative_spec", None, "profile", f"use an absolute or ~ path for a profile directory: {spec}")])
        bundled = False
    else:
        path = starters_dir() / spec
        bundled = True
    if not (path / "profile.json").is_file():
        known = ", ".join(p.name for p in starters()) or "none"
        what = f"no profile.json in {path}" if not bundled else f"no starter profile named '{spec}' (starters: {known})"
        raise ProfileError([Problem("profile_not_found", None, "profile", what)])
    return Located(path.resolve(), "starter" if bundled else "dir", spec)


# ─── Loading ──────────────────────────────────────────────────


def load(root: Path, bundled: bool = False) -> Profile:
    path = root / "profile.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise ProfileError([Problem("unreadable_profile", None, "profile", f"cannot read {path}: {e}")]) from e
    problems = _shape_problems(data, path)
    if problems:
        raise ProfileError(problems)
    return Profile(name=data["name"], root=root, data=data, bundled=bundled)


def _shape_problems(data: object, path: Path) -> list[Problem]:
    def bad(code: str, field_name: str, message: str) -> Problem:
        return Problem(code, None, field_name, f"{path}: {message}")

    if not isinstance(data, dict):
        return [bad("invalid_profile", "profile", "must be a JSON object")]
    found = []
    if data.get("schema") != SCHEMA:
        found.append(bad("unsupported_schema", "schema", f"schema must be {SCHEMA}, got {data.get('schema')!r}"))
    if not isinstance(data.get("name"), str) or not data["name"]:
        found.append(bad("missing_field", "name", "needs a name"))
    for key in sorted(set(data) - PROFILE_KEYS):
        found.append(bad("unknown_field", key, f"unknown field '{key}'"))
    tools = data.get("tools", {})
    if not isinstance(tools, dict) or set(tools) - {"add", "remove"}:
        found.append(bad("invalid_field", "tools", 'tools must be {"add": [...], "remove": [...]}'))
    else:
        for key in ("add", "remove"):
            if not _str_list(tools.get(key, [])):
                found.append(bad("invalid_field", f"tools.{key}", f"tools.{key} must be a list of tool ids"))
    for key, kind in (("overrides", dict), ("custom_tools", list), ("categories", list), ("metadata", dict)):
        if key in data and not isinstance(data[key], kind):
            found.append(bad("invalid_field", key, f"{key} must be a {'list' if kind is list else 'object'}"))
    if "custom_tools" in data and isinstance(data["custom_tools"], list):
        for i, tool in enumerate(data["custom_tools"]):
            if not isinstance(tool, dict) or not isinstance(tool.get("id"), str):
                found.append(bad("invalid_field", f"custom_tools[{i}]", f"custom_tools[{i}] needs an id"))
    if "sensitive_ok" in data and not _str_list(data["sensitive_ok"]):
        found.append(bad("invalid_field", "sensitive_ok", "sensitive_ok must be a list of ~/ paths"))
    if "configs_dir" in data:
        configs_dir = data["configs_dir"]
        if not isinstance(configs_dir, str) or os.path.isabs(configs_dir) or ".." in Path(configs_dir).parts:
            found.append(bad("invalid_field", "configs_dir", "configs_dir must be a relative path inside the profile"))
    macos = data.get("macos_defaults", {})
    if not isinstance(macos, dict) or not isinstance(macos.get("enabled", False), bool):
        found.append(bad("invalid_field", "macos_defaults", 'macos_defaults must be {"enabled": true|false}'))
    extends = data.get("extends")
    if extends is not None and not isinstance(extends, str):
        found.append(bad("invalid_field", "extends", "extends must be a starter name or a relative path"))
    return found


def _str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def load_chain(spec: str) -> tuple[list[Profile], Located]:
    """The profile and the profiles it extends (root first), and where the spec points."""
    located = locate(spec)
    return chain_at(located), located


def chain_at(located: Located) -> list[Profile]:
    """The profile at `located` and the profiles it extends, root first."""
    chain = [load(located.path, located.bundled)]
    seen = {located.path}
    while chain[0].extends:
        child = chain[0]
        if len(chain) > MAX_EXTENDS:
            raise ProfileError([Problem("extends_too_deep", None, "extends", f"'{chain[-1].name}' extends more than {MAX_EXTENDS} levels")])
        parent_root, parent_bundled = _locate_parent(child)
        if parent_root in seen:
            names = " -> ".join(p.name for p in reversed(chain))
            raise ProfileError([Problem("extends_cycle", None, "extends", f"profiles extend each other in a loop: {names} -> {child.extends}")])
        seen.add(parent_root)
        chain.insert(0, load(parent_root, parent_bundled))
    return chain


def _locate_parent(child: Profile) -> tuple[Path, bool]:
    ref = child.extends
    if "/" not in ref:
        starter = locate(ref)
        return starter.path, starter.bundled
    if os.path.isabs(ref) or ref.startswith("~") or ".." in Path(ref).parts:
        raise ProfileError([Problem("invalid_extends", None, "extends", f"'{child.name}' extends '{ref}': use a starter name or a path inside the profile")])
    path = (child.root / ref).resolve()
    if not path.is_relative_to(child.root.resolve()):
        raise ProfileError([Problem("invalid_extends", None, "extends", f"'{child.name}' extends '{ref}', which resolves outside the profile")])
    if not (path / "profile.json").is_file():
        raise ProfileError([Problem("profile_not_found", None, "extends", f"'{child.name}' extends '{ref}', which has no profile.json")])
    return path, child.bundled


# ─── Merging with the catalog ─────────────────────────────────


def resolve(spec: str | None = None, catalog: dict | None = None) -> Resolved:
    """Load the profile for `spec` (or the active one) and merge it with the catalog."""
    if spec is None:
        spec, _ = active_spec()
    chain, located = load_chain(spec)
    if catalog is None:
        catalog = json.loads(catalog_path().read_text())
    return merge(chain, catalog, located)


def merge(chain: list[Profile], catalog: dict, source: Located) -> Resolved:
    """Apply each profile in the chain, root first, to a selection from the catalog."""
    catalog_tools = {t["id"]: t for t in catalog.get("tools", [])}
    problems: list[Problem] = []
    selected: list[str] = []
    removed: set[str] = set()
    custom: dict[str, dict] = {}
    overrides: dict[str, dict] = {}
    configs_roots: dict[str, Path] = {}
    categories: dict[str, dict] = {}
    sensitive_ok: set[str] = set()
    macos_defaults = False

    def known(tool_id: str) -> bool:
        return tool_id in catalog_tools or tool_id in custom

    for profile in chain:
        data = profile.data
        where = f"profile '{profile.name}'"
        for tool in data.get("custom_tools", []):
            tool_id = tool["id"]
            if tool_id in catalog_tools:
                problems.append(Problem("duplicate_id", tool_id, "custom_tools", f"{where}: custom tool '{tool_id}' clashes with a catalog tool; use overrides to change it"))
                continue
            custom[tool_id] = copy.deepcopy(tool)
            if tool.get("configs"):
                configs_roots[tool_id] = profile.configs_root or profile.root
            if tool_id not in selected:
                selected.append(tool_id)
            removed.discard(tool_id)
        for tool_id in data.get("tools", {}).get("add", []):
            if not known(tool_id):
                problems.append(Problem("unknown_tool", tool_id, "tools.add", f"{where} adds unknown tool '{tool_id}'"))
            elif tool_id not in selected:
                selected.append(tool_id)
            removed.discard(tool_id)
        for tool_id in data.get("tools", {}).get("remove", []):
            if not known(tool_id):
                problems.append(Problem("unknown_tool", tool_id, "tools.remove", f"{where} removes unknown tool '{tool_id}'"))
            if tool_id in selected:
                selected.remove(tool_id)
            removed.add(tool_id)
        for tool_id, patch in data.get("overrides", {}).items():
            if not known(tool_id) or not isinstance(patch, dict):
                problems.append(Problem("unknown_tool", tool_id, "overrides", f"{where} overrides unknown tool '{tool_id}'"))
                continue
            if "id" in patch and patch["id"] != tool_id:
                problems.append(Problem("invalid_field", tool_id, "overrides", f"{where} cannot change the id of '{tool_id}'"))
                continue
            overrides[tool_id] = _merge_patch(overrides.get(tool_id, {}), patch)
            if patch.get("configs"):
                configs_roots[tool_id] = profile.configs_root or profile.root
        for category in data.get("categories", []):
            if isinstance(category, dict) and isinstance(category.get("id"), str):
                categories[category["id"]] = category
        sensitive_ok.update(data.get("sensitive_ok", []))
        if "macos_defaults" in data:
            macos_defaults = data["macos_defaults"].get("enabled", False)

    def definition(tool_id: str) -> dict:
        base = catalog_tools.get(tool_id) or custom[tool_id]
        return _merge_patch(base, overrides.get(tool_id, {}))

    # macOS settings are opt-in: `defaults` tools are in only when the profile enables them.
    for tool_id in catalog_tools:
        is_defaults = definition(tool_id).get("install", {}).get("method") == "defaults"
        if is_defaults and macos_defaults and tool_id not in selected and tool_id not in removed:
            selected.append(tool_id)
        elif is_defaults and not macos_defaults and tool_id in selected:
            selected.remove(tool_id)

    # Pull in dependencies; a dependency the profile removed is a hard error.
    queue = list(selected)
    while queue:
        tool_id = queue.pop(0)
        for dep in definition(tool_id).get("depends_on", []):
            if dep in removed:
                problems.append(Problem("removed_dependency", tool_id, "tools.remove", f"'{tool_id}' depends on '{dep}', which the profile removes"))
            elif dep not in selected and known(dep):
                selected.append(dep)
                queue.append(dep)

    if problems:
        raise ProfileError(problems)

    # Catalog order first, then the profile's own tools in the order they were declared.
    order = [tid for tid in catalog_tools if tid in selected] + [tid for tid in custom if tid in selected]
    tools = [{**TOOL_DEFAULTS, **definition(tid)} for tid in order]
    profile = chain[-1]
    manifest = {
        "version": catalog.get("version", "0.0.0"),
        "name": profile.name,
        "description": profile.data.get("description", ""),
        "tools": tools,
    }
    if catalog.get("author"):
        manifest["author"] = catalog["author"]
    if categories:
        manifest["categories"] = list(categories.values())
    return Resolved(chain=chain, source=source, manifest=manifest, configs_roots=configs_roots, sensitive_ok=sensitive_ok)


def _merge_patch(base: dict, patch: dict) -> dict:
    """Copy of `base` with `patch` applied; nested objects (install, check) merge one level deep."""
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **copy.deepcopy(value)}
        else:
            merged[key] = copy.deepcopy(value)
    return merged
