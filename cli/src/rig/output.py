"""JSON-line output protocol for GUI communication."""

import json
import sys


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
    print(json.dumps(payload), flush=True)


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
