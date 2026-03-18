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
