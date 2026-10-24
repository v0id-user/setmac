"""JSON-line output protocol for GUI communication."""

import json
import sys
import threading

_lock = threading.Lock()


def emit(
    type: str,
    tool: str | None = None,
    message: str | None = None,
    status: str | None = None,
    version: str | None = None,
):
    """Emit a single JSON line to stdout. Flush immediately for real-time streaming."""
    payload = {"type": type}
    if tool is not None:
        payload["tool"] = tool
    if message is not None:
        payload["message"] = message
    if status is not None:
        payload["status"] = status
    if version is not None:
        payload["version"] = version
    line = json.dumps(payload)
    with _lock:
        print(line, flush=True)


def emit_status(tool: str, status: str, version: str | None = None):
    emit("status", tool=tool, status=status, version=version)


def emit_progress(tool: str, message: str):
    emit("progress", tool=tool, message=message, status="installing")


def emit_log(message: str, tool: str | None = None):
    emit("log", tool=tool, message=message)


def emit_error(tool: str, message: str):
    emit("error", tool=tool, message=message, status="error")


def emit_complete(tool: str, version: str | None = None):
    emit("complete", tool=tool, status="installed", version=version)


def emit_skipped(tool: str, reason: str):
    """A tool that was not attempted. `status` names the reason, e.g. needs_admin.

    Sent after the matching `error` line, which carries the human-readable message.
    """
    emit("skipped", tool=tool, status=reason)


def emit_summary(message: str, failed: list[str]):
    """Final line of an install run. `failed` lists tool ids that failed or were skipped."""
    line = json.dumps({"type": "summary", "message": message, "failed": failed})
    with _lock:
        print(line, flush=True)


def emit_profile_error(profile: str, problems: list) -> None:
    """The active profile cannot be used. `problems` are validate.Problem records.

    Followed by a plain `error` line without a tool, which the app already shows.
    """
    message = f"Profile '{profile}' cannot be used: " + "; ".join(str(p) for p in problems)
    payload = {
        "type": "profile_error",
        "profile": profile,
        "message": message,
        "problems": [
            {"code": p.code, "tool_id": p.tool_id, "field": p.field, "message": p.message} for p in problems
        ],
    }
    line = json.dumps(payload)
    with _lock:
        print(line, flush=True)
    emit("error", message=message, status="error")


def emit_manifest(profile: str, manifest: dict) -> None:
    """The active profile merged with the catalog, as the app's tool list."""
    line = json.dumps({"type": "manifest", "profile": profile, "manifest": manifest})
    with _lock:
        print(line, flush=True)


def emit_configs(configs: list[dict]) -> None:
    """The profile's dotfiles from `configs list --json`: id, tool, source, target, is_dir,
    and status (missing, identical or differs compared with the file on this Mac)."""
    line = json.dumps({"type": "configs", "configs": configs})
    with _lock:
        print(line, flush=True)


def emit_auth_required(tool: str, message: str):
    """Emit auth_required so the app can prompt for admin password."""
    emit("auth_required", tool=tool, message=message)


def emit_config_status(tool: str, source: str, target: str, status: str):
    """Emit config_status for GUI: bundled, system, bundled+system, or missing."""
    payload = {
        "type": "config_status",
        "tool": tool,
        "source": source,
        "target": target,
        "status": status,
    }
    line = json.dumps(payload)
    with _lock:
        print(line, flush=True)
