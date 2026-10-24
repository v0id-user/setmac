"""Profiles from git: `<url>` or `<url>#<branch, tag or sha>`.

The first use clones the repository with the system git (so SSH keys and credential
helpers work), pins the exact commit and the content's hash in a lock file, and caches
the checkout. Later uses read the lock: a moved branch or a rewritten tag changes
nothing until `setmac profile update`.

Layout under ~/Library/Application Support/setmac/profiles/<slug>/:
    profile.lock.json   {"url", "ref", "sha", "content_hash"}
    <sha>/              the checkout at that commit
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from setmac.validate import Problem

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass
class Lock:
    url: str
    ref: str | None
    sha: str
    content_hash: str


class GitProfileError(Exception):
    def __init__(self, code: str, message: str):
        self.problem = Problem(code, None, "profile", message)
        super().__init__(message)


def is_git_url(spec: str) -> bool:
    return "://" in spec or spec.startswith("git@") or spec.split("#")[0].endswith(".git")


def split_spec(spec: str) -> tuple[str, str | None]:
    url, _, ref = spec.partition("#")
    return url, ref or None


def cache_root(state_dir: Path, url: str) -> Path:
    """A readable, collision-free folder name for a URL."""
    readable = re.sub(r"[^A-Za-z0-9._-]+", "-", url.split("://")[-1].removeprefix("git@")).strip("-")[-60:]
    return state_dir / "profiles" / f"{readable}-{hashlib.sha256(url.encode()).hexdigest()[:12]}"


def content_hash(root: Path) -> str:
    """SHA-256 over every file in the profile (paths and bytes), ignoring .git.

    Symlinks count by their target text, so a link cannot smuggle in content unseen.
    """
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if ".git" not in p.relative_to(root).parts):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            digest.update(f"L {rel}\0{os.readlink(path)}\0".encode())
        elif path.is_file():
            digest.update(f"F {rel}\0".encode())
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def read_lock(root: Path) -> Lock | None:
    try:
        data = json.loads((root / "profile.lock.json").read_text())
        return Lock(data["url"], data.get("ref"), data["sha"], data["content_hash"])
    except (OSError, ValueError, KeyError):
        return None


def write_lock(root: Path, lock: Lock) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "profile.lock.json").write_text(json.dumps(lock.__dict__, indent=2) + "\n")


def _git(*args: str, cwd: Path | None = None) -> str:
    env = {**os.environ}
    if not sys.stdin.isatty():
        # From the app there is nobody to answer a prompt; fail instead of hanging.
        env["GIT_TERMINAL_PROMPT"] = "0"
        env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise GitProfileError("git_failed", f"git {args[0]} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def _clone(url: str, into: Path) -> None:
    _git("clone", "--quiet", "--no-checkout", url, str(into))


def _resolve_ref(repo: Path, ref: str | None) -> str:
    candidates = ["HEAD"] if ref is None else [ref, f"origin/{ref}"]
    for candidate in candidates:
        try:
            return _git("rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}", cwd=repo)
        except GitProfileError:
            continue
    raise GitProfileError("unknown_ref", f"'{ref}' is not a branch, tag or commit in the profile repository")


def _checkout(url: str, ref: str | None, root: Path, sha: str | None = None) -> tuple[str, Path]:
    """Clone `url`, check out `sha` (or what `ref` points at), and cache it under root/<sha>."""
    root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="clone-", dir=root))
    try:
        _clone(url, work / "repo")
        repo = work / "repo"
        target = sha or _resolve_ref(repo, ref)
        if sha:
            _git("cat-file", "-e", f"{sha}^{{commit}}", cwd=repo)
        _git("checkout", "--quiet", "--detach", target, cwd=repo)
        final = root / target
        if final.exists():
            shutil.rmtree(final)
        repo.rename(final)
        return target, final
    finally:
        shutil.rmtree(work, ignore_errors=True)


def checkout(spec: str, state_dir: Path) -> tuple[Path, Lock]:
    """The local checkout for a git spec, pinned by its lock (created on first use)."""
    url, ref = split_spec(spec)
    root = cache_root(state_dir, url)
    lock = read_lock(root)
    if lock is None:
        sha, path = _checkout(url, ref, root)
        lock = Lock(url, ref, sha, content_hash(path))
        write_lock(root, lock)
        return path, lock
    if ref is not None and ref != lock.ref and ref != lock.sha:
        raise GitProfileError(
            "ref_changed",
            f"{url} is locked to {lock.ref or 'its default branch'} at {lock.sha[:12]}; "
            f"run `setmac profile update {spec}` to move it to {ref}",
        )
    path = root / lock.sha
    if not path.is_dir():
        _, path = _checkout(url, None, root, sha=lock.sha)
    actual = content_hash(path)
    if actual != lock.content_hash:
        raise GitProfileError(
            "locked_content_changed",
            f"the cached checkout of {url} at {lock.sha[:12]} no longer matches its lock "
            f"(content {actual[:12]}, expected {lock.content_hash[:12]}); delete {path} to fetch it again",
        )
    return path, lock


def fetch_latest(spec: str, state_dir: Path) -> tuple[Path, Lock, Lock | None]:
    """Check out what the spec's ref (or the locked ref) points at now, without moving the lock.

    Returns (checkout, candidate lock, current lock).
    """
    url, ref = split_spec(spec)
    root = cache_root(state_dir, url)
    current = read_lock(root)
    wanted = ref if ref is not None else (current.ref if current else None)
    sha, path = _checkout(url, wanted, root)
    return path, Lock(url, wanted, sha, content_hash(path)), current


def diff_stat(state_dir: Path, url: str, old_sha: str, new_sha: str) -> str:
    """`git diff --stat` between two cached checkouts' commits."""
    new_repo = cache_root(state_dir, url) / new_sha
    try:
        return _git("diff", "--stat", old_sha, new_sha, cwd=new_repo)
    except GitProfileError:
        return "(the old commit is not in the new checkout's history; showing the full review below)"
