"""Trust for profiles that are not bundled starters.

A profile can run arbitrary shell (install scripts, check commands) and write dotfiles,
so setmac only runs one after the user has reviewed it. Trust is recorded for exactly
what was reviewed: a local directory or a git URL and commit, plus the hash of every
file in it. Any change to the files needs a new review.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from setmac import gitprofile, profile
from setmac.installers.base import install_command

# Install strings that download and run code in one step deserve a second look.
PIPE_TO_SHELL = re.compile(r"(curl|wget)[^|;&]*\|\s*(sudo\s+)?(ba|z)?sh\b|\$\((curl|wget)\b")


def identity(resolved: profile.Resolved) -> dict | None:
    """What trust is recorded for; None for bundled starters, which are always trusted."""
    source = resolved.source
    if source.bundled:
        return None
    if source.kind == "git":
        return {"kind": "git", "id": source.lock.url, "sha": source.lock.sha, "content_hash": source.lock.content_hash}
    return {"kind": "dir", "id": str(source.path), "sha": None, "content_hash": gitprofile.content_hash(source.path)}


def _store() -> list[dict]:
    try:
        return json.loads((profile.STATE_DIR / "trust.json").read_text()).get("trusted", [])
    except (OSError, ValueError):
        return []


def _same(a: dict, b: dict) -> bool:
    return all(a.get(k) == b.get(k) for k in ("kind", "id", "sha", "content_hash"))


def is_trusted(resolved: profile.Resolved) -> bool:
    ident = identity(resolved)
    return ident is None or any(_same(ident, entry) for entry in _store())


def record(resolved: profile.Resolved) -> None:
    ident = identity(resolved)
    if ident is None or is_trusted(resolved):
        return
    entries = _store() + [{**ident, "trusted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}]
    path = profile.STATE_DIR / "trust.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"trusted": entries}, indent=2) + "\n")


def review(resolved: profile.Resolved, registry) -> str:
    """Everything the profile makes setmac run or write, verbatim."""
    ident = identity(resolved)
    profile_tools = _profile_tool_ids(resolved)
    lines = [f"Profile: {resolved.profile.name}  ({' -> '.join(p.name for p in resolved.chain)})"]
    if resolved.source.kind == "git":
        lines.append(f"Source:  {resolved.source.lock.url} @ {resolved.source.lock.sha}")
    else:
        lines.append(f"Source:  {resolved.source.path}")
    if ident:
        lines.append(f"Content: {ident['content_hash']}")
    lines.append("")

    lines.append("Commands it runs (* = defined or changed by this profile):")
    for tool in registry.install_order():
        mark = "*" if tool.id in profile_tools else " "
        cmd = install_command(tool)
        shown = cmd if isinstance(cmd, str) or cmd is None else " ".join(cmd)
        admin = "  [admin]" if tool.install.requires_admin else ""
        lines.append(f" {mark} {tool.id}{admin}")
        if tool.install.method == "defaults":
            for d in tool.defaults:
                lines.append(f"      defaults write {d.domain} {d.key} -{d.type} {d.value}")
        elif shown:
            lines.append(f"      install: {shown}")
            if PIPE_TO_SHELL.search(shown):
                lines.append("      ! downloads and runs code in one step")
        for label, value in (("check", tool.check.command), ("version", tool.check.version_command)):
            if value and tool.id in profile_tools:
                lines.append(f"      {label}: {value}")
        if "/" in (tool.install.target or "") and tool.install.method.startswith("brew"):
            lines.append(f"      from tap: {tool.install.target.rsplit('/', 1)[0]}")
        if tool.post_install:
            lines.append(f"      then by hand: {tool.post_install}")

    configs = [(t, c) for t in registry.tools for c in t.configs]
    if configs:
        lines.append("")
        lines.append("Dotfiles it can write:")
        for tool, config in configs:
            lines.append(f"   {config.source}  (from {config.target}, {tool.id})")
    if resolved.sensitive_ok:
        lines.append("")
        lines.append("Sensitive locations it is allowed to write: " + ", ".join(sorted(resolved.sensitive_ok)))
    notes = [p.data["notes"] for p in resolved.chain if p.data.get("notes")]
    if notes:
        lines.append("")
        lines.append("Notes:")
        lines.extend(f"   {n}" for n in notes)
    return "\n".join(lines)


def _profile_tool_ids(resolved: profile.Resolved) -> set[str]:
    ids: set[str] = set()
    for p in resolved.chain:
        if p.bundled:
            continue
        ids.update(t["id"] for t in p.data.get("custom_tools", []))
        ids.update(p.data.get("overrides", {}))
    return ids
