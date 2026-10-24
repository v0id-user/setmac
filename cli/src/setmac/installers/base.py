"""Check and install tools based on their tools.json install method."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
import traceback
from enum import Enum

from setmac.installers import defaults
from setmac.output import emit_complete, emit_error, emit_log, emit_progress, emit_status
from setmac.registry import Tool

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class Outcome(Enum):
    ALREADY = "already"
    INSTALLED = "installed"
    FAILED = "failed"


# ─── Shell environment ────────────────────────────────────────


def shell_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for every subprocess: a PATH that covers all install locations."""
    env = os.environ.copy()
    home = os.path.expanduser("~")
    paths = [
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
        "/usr/local/sbin",
        f"{home}/.local/bin",
        f"{home}/.local/share/mise/shims",
        f"{home}/.bun/bin",
        f"{home}/.cargo/bin",
        f"{home}/go/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]
    env["PATH"] = ":".join(paths + [env.get("PATH", "")])
    env["NONINTERACTIVE"] = "1"
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"
    env["HOMEBREW_NO_ENV_HINTS"] = "1"
    env.pop("PYTHONHOME", None)
    if extra:
        env.update(extra)
    return env


def _run_quiet(cmd: str | list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    """Run a command for checking, never raising."""
    try:
        return subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=shell_env(),
            stdin=subprocess.DEVNULL,
        )
    except (subprocess.TimeoutExpired, OSError):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")


# ─── Homebrew inventory ───────────────────────────────────────

_brew_lock = threading.Lock()
_brew_cache: dict[str, set[str]] | None = None


def _brew_inventory() -> dict[str, set[str]]:
    """Installed formulae and casks, read once and cached until invalidated."""
    global _brew_cache
    with _brew_lock:
        if _brew_cache is None:
            inventory: dict[str, set[str]] = {"formula": set(), "cask": set()}
            for kind in ("formula", "cask"):
                result = _run_quiet(["brew", "list", f"--{kind}", "--full-name", "-1"], timeout=60)
                if result.returncode == 0:
                    for name in result.stdout.split():
                        inventory[kind].add(name)
                        inventory[kind].add(name.rsplit("/", 1)[-1])
            _brew_cache = inventory
        return _brew_cache


def invalidate_brew_cache() -> None:
    global _brew_cache
    with _brew_lock:
        _brew_cache = None


# ─── Check ────────────────────────────────────────────────────


def check_tool(tool: Tool) -> tuple[bool, str | None]:
    """Return (installed, version).

    Brew formulae count as installed only when brew lists them. A fresh Mac
    ships stub /usr/bin/git, python3 and ssh that pass `command -v` but only
    open the Command Line Tools dialog, so `command -v` can't be trusted for them.
    """
    method = tool.install.method
    if method == "brew_formula":
        installed = tool.install.target in _brew_inventory()["formula"]
    elif method == "brew_cask":
        if tool.check.path:
            # The app on disk is the truth: brew lists a cask whose install was
            # interrupted before the .app landed, and a hand-installed app counts.
            installed = _path_exists(tool.check.path)
        else:
            installed = tool.install.target in _brew_inventory()["cask"] or _command_ok(tool.check.command)
    elif method == "mise":
        installed = _command_ok(["mise", "where", tool.install.target])
    elif method == "mas":
        installed = _path_exists(tool.check.path) or tool.install.target in _mas_installed()
    elif method == "defaults":
        installed = not defaults.pending(tool)
    else:
        installed = _path_exists(tool.check.path) or _command_ok(tool.check.command)

    version = _get_version(tool) if installed else None
    return installed, version


def _path_exists(path: str | None) -> bool:
    return bool(path) and os.path.exists(os.path.expanduser(path))


def _command_ok(command: str | list[str] | None) -> bool:
    return bool(command) and _run_quiet(command).returncode == 0


def _mas_installed() -> set[str]:
    """App Store app ids reported by `mas list`."""
    result = _run_quiet(["mas", "list"], timeout=30)
    return {line.split()[0] for line in result.stdout.splitlines() if line.strip()}


def _get_version(tool: Tool) -> str | None:
    if not tool.check.version_command:
        return None
    result = _run_quiet(tool.check.version_command)
    if result.returncode != 0:
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    clean = ANSI.sub("", lines[0])
    return clean if len(clean) <= 80 else clean[:77] + "..."


# ─── Running installers ───────────────────────────────────────


class Runner:
    """Runs installer commands one at a time, streaming their output.

    Holds the child process so a cancel (SIGTERM from the app) can stop the
    whole process group instead of leaving brew running in the background.
    """

    def __init__(self, extra_env: dict[str, str] | None = None) -> None:
        self.extra_env = extra_env or {}
        self._proc: subprocess.Popen | None = None

    def run(self, cmd: str | list[str], tool_id: str) -> bool:
        shown = cmd if isinstance(cmd, str) else " ".join(cmd)
        emit_log(f"$ {shown}", tool=tool_id)
        try:
            self._proc = subprocess.Popen(
                cmd,
                shell=isinstance(cmd, str),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                errors="replace",
                bufsize=1,
                env=shell_env(self.extra_env),
                start_new_session=True,
            )
        except OSError as e:
            emit_error(tool_id, f"Could not start installer: {e}")
            return False

        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            # Progress bars redraw with \r; keep only the final state of each line.
            line = ANSI.sub("", raw.rstrip("\n").split("\r")[-1]).strip()
            if line:
                emit_log(line, tool=tool_id)
        code = self._proc.wait()
        self._proc = None
        if code != 0:
            emit_log(f"Exited with code {code}", tool=tool_id)
        return code == 0

    def terminate(self) -> None:
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=5)
        except (ProcessLookupError, PermissionError):
            pass
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def install_command(tool: Tool) -> str | list[str] | None:
    """The command that installs a tool, or None if the manifest entry is incomplete."""
    spec = tool.install
    if spec.method in ("brew_formula", "brew_cask"):
        if not spec.target:
            return None
        if spec.method == "brew_cask":
            if spec.target in _brew_inventory()["cask"]:
                # brew still lists the cask but its app is gone (an interrupted install or a
                # hand-deleted app). `brew install` would see it as installed and do nothing.
                return ["brew", "reinstall", "--cask", spec.target]
            return ["brew", "install", "--cask", spec.target]
        return ["brew", "install", spec.target]
    if spec.method == "mise":
        return ["mise", "use", "--global", "--yes", spec.target] if spec.target else None
    if spec.method == "mas":
        if not spec.target:
            return None
        # `install` covers apps on the account; `get` covers free apps it never had.
        # Some mas versions need root for both.
        app = spec.target
        return f"mas install {app} || mas get {app} || sudo -A mas get {app}"
    if spec.method in ("script", "custom"):
        if spec.url:
            return f'/bin/bash -c "$(curl -fsSL {spec.url})"'
        return spec.script
    return None


def run_tool(tool: Tool, runner: Runner, position: tuple[int, int] | None = None) -> Outcome:
    """Install a tool if missing, then confirm with a fresh check. Never raises.

    `position` is (index, total) in the run, shown in the progress message.
    """
    progress = f" ({position[0]}/{position[1]})" if position else ""
    try:
        installed, version = check_tool(tool)
        if installed:
            emit_status(tool.id, "installed", version=version)
            return Outcome.ALREADY

        if tool.install.method == "config":
            # Config-only entries are applied by the configs step.
            emit_status(tool.id, "not_installed")
            return Outcome.ALREADY

        emit_progress(tool.id, f"Installing {tool.name}...{progress}")
        if tool.install.method == "defaults":
            ok = defaults.apply(tool)
        else:
            cmd = install_command(tool)
            if cmd is None:
                emit_error(tool.id, f"tools.json has no install command for {tool.name}")
                return Outcome.FAILED
            ok = runner.run(cmd, tool.id)
        invalidate_brew_cache()
        if not ok:
            emit_error(tool.id, f"Install of {tool.name} failed (see log)")
            return Outcome.FAILED

        rechecked, version = check_tool(tool)
        if not rechecked:
            emit_error(tool.id, f"{tool.name} installer finished, but the check still fails")
            return Outcome.FAILED
        emit_complete(tool.id, version=version)
        return Outcome.INSTALLED
    except Exception as e:
        emit_error(tool.id, f"Unexpected error: {e}")
        emit_log(traceback.format_exc(), tool=tool.id)
        return Outcome.FAILED
