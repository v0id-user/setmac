"""macOS settings applied with `defaults write`. Idempotent: only differing values are written."""

from __future__ import annotations

import subprocess

from setmac.output import emit_log
from setmac.registry import DefaultSpec, Tool


def _base(spec: DefaultSpec) -> list[str]:
    cmd = ["defaults"]
    if spec.current_host:
        cmd.append("-currentHost")
    return cmd


def _read(spec: DefaultSpec) -> str | None:
    result = subprocess.run(
        _base(spec) + ["read", spec.domain, spec.key], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def matches(spec: DefaultSpec) -> bool:
    current = _read(spec)
    if current is None:
        return False
    if spec.type == "bool":
        return current in ("1", "0") and (current == "1") == bool(spec.value)
    if spec.type in ("int", "float"):
        try:
            return float(current) == float(spec.value)
        except ValueError:
            return False
    return current == str(spec.value)


def pending(tool: Tool) -> list[DefaultSpec]:
    return [spec for spec in tool.defaults if not matches(spec)]


def _value_args(spec: DefaultSpec) -> list[str]:
    if spec.type == "bool":
        return ["-bool", "true" if spec.value else "false"]
    return [f"-{spec.type}", str(spec.value)]


def apply(tool: Tool) -> bool:
    """Write every setting that differs, then restart the apps that read them."""
    changed = pending(tool)
    for spec in changed:
        cmd = _base(spec) + ["write", spec.domain, spec.key] + _value_args(spec)
        emit_log("$ " + " ".join(cmd), tool=tool.id)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            emit_log(result.stderr.strip() or f"defaults write failed for {spec.key}", tool=tool.id)
            return False
    if changed:
        for app in tool.restart:
            subprocess.run(["killall", app], capture_output=True)
    return True
