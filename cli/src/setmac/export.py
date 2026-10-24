"""Turn an old all-in-one manifest (from git refs) into a private profile folder.

Tools no longer in the public catalog become the profile's custom_tools; catalog tools
the old manifest used are added back, with their old dotfiles as overrides. Each
dotfile is copied from this Mac when it exists there (it is the newest), else from the
ref. Everything is staged, scanned and validated before the folder is written.
"""

from __future__ import annotations

import copy
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from setmac import profile, scanner
from setmac.registry import Registry

# Copied folders leave these out (caches, lock files, nested repositories).
IGNORE = ["__pycache__", ".git", "*.pyc", "lazy-lock.json", ".DS_Store"]
PUBLIC_REPO_NAMES = ("v0id-user/setmac", "v0id-user/setmac.git")


class ExportError(Exception):
    pass


@dataclass
class Report:
    custom: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    from_home: list[str] = field(default_factory=list)
    from_ref: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    differs: list[str] = field(default_factory=list)
    findings: list[scanner.Finding] = field(default_factory=list)
    shell_checks: list[str] = field(default_factory=list)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def _origin(path: Path) -> str:
    existing = path
    while not existing.exists():
        existing = existing.parent
    result = _git(existing, "remote", "get-url", "origin")
    return result.stdout.decode().strip() if result.returncode == 0 else ""


def _toplevel(path: Path) -> Path | None:
    existing = path
    while not existing.exists():
        existing = existing.parent
    result = _git(existing, "rev-parse", "--show-toplevel")
    return Path(result.stdout.decode().strip()).resolve() if result.returncode == 0 else None


def check_destination(out: Path, repo: Path) -> None:
    out = out.expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise ExportError(f"{out} is not empty")
    if _origin(out).removesuffix("/").endswith(PUBLIC_REPO_NAMES):
        raise ExportError(f"{out} is inside a clone of the public setmac repository")
    top = _toplevel(repo)
    if top and (out == top or top in out.parents):
        raise ExportError(f"{out} is inside {top}; write the private profile outside the setmac repository")


def old_tools(repo: Path, refs: list[str]) -> dict[str, dict]:
    """Every tool in the refs' Resources/tools.json, the first ref winning on an id clash."""
    tools: dict[str, dict] = {}
    for ref in refs:
        result = _git(repo, "show", f"{ref}:Resources/tools.json")
        if result.returncode != 0:
            raise ExportError(f"{ref} has no Resources/tools.json: {result.stderr.decode().strip()}")
        for tool in json.loads(result.stdout)["tools"]:
            tools.setdefault(tool["id"], tool)
    return tools


def _ref_configs(repo: Path, refs: list[str], into: Path) -> list[Path]:
    """Extract each ref's Resources/configs into into/<n>/, in ref order."""
    roots = []
    for n, ref in enumerate(refs):
        root = into / str(n)
        root.mkdir(parents=True)
        result = _git(repo, "archive", "--format=tar", ref, "Resources/configs")
        if result.returncode == 0:
            with tarfile.open(fileobj=io.BytesIO(result.stdout)) as tar:
                tar.extractall(root, filter="data")
        roots.append(root / "Resources" / "configs")
    return roots


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, symlinks=True, ignore=shutil.ignore_patterns(*IGNORE))
    else:
        shutil.copy2(src, dst, follow_symlinks=False)


def _same(a: Path, b: Path) -> bool:
    if a.is_file() and b.is_file():
        return a.read_bytes() == b.read_bytes()
    if a.is_dir() and b.is_dir():
        files = lambda root: {p.relative_to(root): p.read_bytes() for p in root.rglob("*")
                              if p.is_file() and not any(part in IGNORE for part in p.relative_to(root).parts)}
        return files(a) == files(b)
    return False


def build(repo: Path, refs: list[str], out: Path, name: str, extends: str,
          use_home: bool = True, accept_reviewed: bool = False) -> Report:
    check_destination(out, repo)
    catalog = json.loads(profile.catalog_path().read_text())
    catalog_ids = {t["id"] for t in catalog["tools"]}
    old = old_tools(repo, refs)
    report = Report()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ref_roots = _ref_configs(repo, refs, tmp_path / "refs")
        stage = tmp_path / "profile"
        configs_dir = stage / "configs"
        configs_dir.mkdir(parents=True)

        def bring(config: dict, tool_id: str) -> bool:
            """Copy one dotfile into the stage; False when it exists nowhere."""
            target, live = config["target"], Path(config["source"]).expanduser()
            ref_copy = next((root / target for root in ref_roots if (root / target).exists()), None)
            label = f"{config['source']} ({tool_id})"
            if use_home and (live.exists() and not live.is_symlink()):
                _copy(live, configs_dir / target)
                report.from_home.append(label)
                if ref_copy is not None and not _same(live, ref_copy):
                    report.differs.append(label)
                return True
            if ref_copy is not None:
                _copy(ref_copy, configs_dir / target)
                report.from_ref.append(label)
                return True
            report.dropped.append(f"{label}: not on this Mac or in {', '.join(refs)}")
            return False

        custom_tools, overrides, add = [], {}, []
        for tool_id, tool in old.items():
            kept = [c for c in tool.get("configs", []) if bring(c, tool_id)]
            if tool_id in catalog_ids:
                add.append(tool_id)
                if kept:
                    overrides[tool_id] = {"configs": kept}
                continue
            entry = copy.deepcopy(tool)
            if entry.get("configs"):
                entry["configs"] = kept
                if not kept and entry["install"].get("method") == "config":
                    report.dropped.append(f"{tool_id}: a config-only tool with no files left")
                    continue
            custom_tools.append(entry)
        # Personal tools may depend on each other or on catalog tools; keep only reachable ones.
        custom_ids = {t["id"] for t in custom_tools}
        for tool in custom_tools:
            tool["depends_on"] = [d for d in tool.get("depends_on", []) if d in custom_ids or d in catalog_ids]
        report.custom = sorted(custom_ids)
        report.added = sorted(add)

        data = {
            "schema": 1,
            "name": name,
            "description": f"{name}'s Mac, exported from {', '.join(refs)}",
            "extends": extends,
            "tools": {"add": sorted(add)},
            "custom_tools": custom_tools,
            "overrides": overrides,
            "configs_dir": "configs",
        }
        (stage / "profile.json").write_text(json.dumps(data, indent=2) + "\n")
        (stage / ".setmacignore").write_text("# Files `setmac configs capture` leaves out.\n*.log\n.DS_Store\n")

        report.findings = scanner.scan(configs_dir, "configs")
        high = [f for f in report.findings if f.severity == scanner.HIGH]
        if high:
            raise ExportError("secrets found; nothing was written:\n  " + "\n  ".join(f.describe() for f in high))
        if report.findings and not accept_reviewed:
            raise ExportError("personal data found; review it, then rerun with --accept-reviewed:\n  "
                              + "\n  ".join(f.describe() for f in report.findings))

        try:
            located = profile.Located(stage, "dir", str(stage))
            resolved = profile.merge(profile.chain_at(located), catalog, located)
            Registry(data=resolved.manifest, configs_roots=resolved.configs_roots, sensitive_ok=resolved.sensitive_ok)
        except (profile.ProfileError, ValueError) as e:
            raise ExportError(f"the exported profile would not be valid: {e}") from e

        for zshrc in [p for p in configs_dir.rglob("*") if p.is_file() and p.name.lstrip(".") == "zshrc"]:
            result = subprocess.run(["zsh", "-n", str(zshrc)], capture_output=True, text=True)
            rel = zshrc.relative_to(stage).as_posix()
            report.shell_checks.append(f"{rel}: " + ("syntax OK" if result.returncode == 0 else result.stderr.strip()))

        out = out.expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.rmdir()
        shutil.copytree(stage, out, symlinks=True)
    subprocess.run(["git", "init", "-q", str(out)], check=True)
    return report
