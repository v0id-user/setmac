"""Base installer and generic dispatch based on tools.json install method."""

from __future__ import annotations

import os
import subprocess
import sys
import traceback

from setmac.output import (
    emit_auth_required,
    emit_complete,
    emit_error,
    emit_log,
    emit_progress,
    emit_status,
)
from setmac.registry import Tool


# ─── Shell environment ────────────────────────────────────────

_cached_env: dict[str, str] | None = None


def _shell_env() -> dict[str, str]:
    """Build a rich PATH that covers all common install locations. Cached."""
    global _cached_env
    if _cached_env is not None:
        return _cached_env
    env = os.environ.copy()
    home = os.path.expanduser("~")
    extra_paths = [
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
        "/usr/local/sbin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
        f"{home}/.bun/bin",
        f"{home}/.cargo/bin",
        f"{home}/.local/bin",
        f"{home}/.nvm/versions/node/default/bin",
        f"{home}/go/bin",
        "/usr/local/go/bin",
    ]
    current = env.get("PATH", "")
    env["PATH"] = ":".join(extra_paths) + ":" + current
    env["NONINTERACTIVE"] = "1"
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"
    _cached_env = env
    return env


def _run_quiet(cmd: str, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a shell command safely, never raising."""
    try:
        return subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_shell_env(),
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="timeout")
    except Exception:
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="error")


# ─── Check ────────────────────────────────────────────────────

def check_tool(tool: Tool) -> tuple[bool, str | None]:
    """Check if a tool is installed. Tries ALL methods (path + command) — any pass = installed."""
    installed = False

    # 1. Check by path (file or directory exists)
    if tool.check.path:
        expanded = os.path.expanduser(tool.check.path)
        if os.path.exists(expanded):
            installed = True

    # 2. Check by command (exit 0 = installed)
    if tool.check.command and not installed:
        result = _run_quiet(tool.check.command)
        if result.returncode == 0:
            installed = True

    # 3. For brew tools, also try `command -v <binary>` as fallback
    #    This catches tools installed via Xcode CLT, system, etc.
    if not installed and tool.install.target:
        binary = tool.install.target.split("@")[0]  # python@3.14 -> python
        result = _run_quiet(f"command -v {binary}")
        if result.returncode == 0:
            installed = True

    # 4. For cask apps, check common app paths
    if not installed and tool.install.method == "brew_cask":
        app_name = tool.name
        for base in ["/Applications", os.path.expanduser("~/Applications")]:
            if os.path.isdir(f"{base}/{app_name}.app"):
                installed = True
                break

    # Get version string if installed
    version = _get_version(tool) if installed else None

    return installed, version


def _get_version(tool: Tool) -> str | None:
    """Get version string, cleaning up ANSI codes and multi-line noise."""
    if not tool.check.version_command:
        return None

    result = _run_quiet(tool.check.version_command, timeout=10)
    if result.returncode != 0:
        return None

    raw = result.stdout.strip()
    if not raw:
        return None

    # Take first meaningful line, strip ANSI escape codes
    import re
    first_line = raw.split("\n")[0].strip()
    clean = re.sub(r"\x1b\[[0-9;]*m", "", first_line)

    # Truncate long versions
    if len(clean) > 80:
        clean = clean[:77] + "..."

    return clean


# ─── Install ──────────────────────────────────────────────────

def install_tool(tool: Tool) -> bool:
    """Install a tool based on its install method. Returns True on success."""
    method = tool.install.method

    try:
        if method == "brew_formula":
            return _brew_install(tool, cask=False)
        elif method == "brew_cask":
            return _brew_install(tool, cask=True)
        elif method in ("script", "custom"):
            return _script_install(tool)
        elif method == "config":
            emit_log("Config-only tool — use 'setmac configs apply'", tool=tool.id)
            return True
        else:
            emit_error(tool.id, f"Unknown install method: {method}")
            return False
    except Exception as e:
        emit_error(tool.id, f"Install failed: {e}")
        return False


def run_tool(tool: Tool) -> None:
    """Idempotent install: check first, install only if needed. Never crashes."""
    try:
        installed, version = check_tool(tool)
        if installed:
            emit_status(tool.id, "installed", version=version)
            return

        emit_progress(tool.id, f"Installing {tool.name}...")

        success = install_tool(tool)
        if success:
            # Re-check to confirm and get version
            rechecked, version = check_tool(tool)
            if rechecked:
                emit_complete(tool.id, version=version)
            else:
                # Install command succeeded but check still fails — likely needs shell restart
                emit_complete(tool.id, version="(restart shell to verify)")
        else:
            emit_error(tool.id, f"Failed to install {tool.name}")

    except Exception as e:
        emit_error(tool.id, f"Unexpected error: {e}")
        # Log traceback for debugging but don't crash
        emit_log(traceback.format_exc(), tool=tool.id)


# ─── Brew ─────────────────────────────────────────────────────

def _brew_install(tool: Tool, cask: bool) -> bool:
    """Install via Homebrew."""
    target = tool.install.target
    if not target:
        emit_error(tool.id, "No brew target specified in tools.json")
        return False

    cmd = ["brew", "install"]
    if cask:
        cmd.append("--cask")
    cmd.append(target)

    emit_log(f"$ {' '.join(cmd)}", tool=tool.id)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout for large installs
            env=_shell_env(),
        )
    except subprocess.TimeoutExpired:
        emit_error(tool.id, "brew install timed out after 10 minutes")
        return False

    _log_output(result, tool.id)
    return result.returncode == 0


# ─── Script ───────────────────────────────────────────────────

def _script_install(tool: Tool) -> bool:
    """Install via shell script or curl | bash."""
    if tool.install.url:
        script = f'curl -fsSL "{tool.install.url}" | bash'
    elif tool.install.script:
        script = tool.install.script
    else:
        emit_error(tool.id, "No script or URL specified in tools.json")
        return False

    emit_log(f"$ {script}", tool=tool.id)

    env = _shell_env()
    keepalive: subprocess.Popen | None = None
    if tool.install.requires_admin:
        password = _request_admin_password(tool)
        if not password:
            emit_error(tool.id, "Installation cancelled — no password provided")
            return False

        authenticated = _prime_sudo_credentials(tool, password, env)
        if not authenticated:
            return False
        keepalive = _start_sudo_keepalive(env)

    try:
        result = subprocess.run(
            script,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
    except subprocess.TimeoutExpired:
        emit_error(tool.id, "Script timed out after 10 minutes")
        return False
    finally:
        _stop_sudo_keepalive(keepalive)
        if tool.install.requires_admin:
            _invalidate_sudo_credentials(env)

    _log_output(result, tool.id)
    return result.returncode == 0


# ─── Helpers ──────────────────────────────────────────────────

def _log_output(result: subprocess.CompletedProcess, tool_id: str) -> None:
    """Log stdout/stderr lines, skipping empty ones."""
    for stream in [result.stdout, result.stderr]:
        if stream:
            for line in stream.strip().split("\n"):
                line = line.strip()
                if line:
                    emit_log(line, tool=tool_id)


def _request_admin_password(tool: Tool) -> str:
    """Request an admin password from the GUI or terminal."""
    emit_auth_required(tool.id, "Admin password required for installation")
    if sys.stdin.isatty():
        print("Admin password required. Enter password: ", end="", file=sys.stderr, flush=True)

    try:
        line = sys.stdin.readline()
    except Exception:
        return ""

    return line.strip() if line else ""


def _prime_sudo_credentials(tool: Tool, password: str, env: dict[str, str]) -> bool:
    """Validate the password in-memory and cache sudo for child processes."""
    try:
        result = subprocess.run(
            ["sudo", "-S", "-k", "-v"],
            input=password + "\n",
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    except subprocess.TimeoutExpired:
        emit_error(tool.id, "Admin authentication timed out")
        return False

    _log_output(result, tool.id)
    if result.returncode != 0:
        emit_error(tool.id, "Admin authentication failed")
        return False

    return True


def _start_sudo_keepalive(env: dict[str, str]) -> subprocess.Popen | None:
    """Keep sudo fresh while a long-running installer is active."""
    try:
        return subprocess.Popen(
            ["/bin/sh", "-c", "while true; do sudo -n -v >/dev/null 2>&1 || exit 0; sleep 60; done"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
    except Exception:
        return None


def _stop_sudo_keepalive(process: subprocess.Popen | None) -> None:
    """Best-effort cleanup for the keepalive helper."""
    if process is None:
        return
    try:
        process.terminate()
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
    except Exception:
        pass


def _invalidate_sudo_credentials(env: dict[str, str]) -> None:
    """Drop cached sudo credentials after privileged install flow ends."""
    try:
        subprocess.run(
            ["sudo", "-k"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            env=env,
        )
    except Exception:
        pass
