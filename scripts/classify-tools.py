#!/usr/bin/env python3
"""List every tool in one or more manifests next to the public catalog, for sorting tools
into the catalog or a private profile.

Usage: python3 scripts/classify-tools.py <git-ref>... [--catalog Resources/tools.json]
Example: python3 scripts/classify-tools.py archive/pre-profiles archive/e2e

Prints one row per tool id: the refs it appears in, its install method, whether it needs
admin, and a proposed bucket: `catalog` when the catalog already has it, else `review`.
"""

import argparse
import json
import subprocess
from pathlib import Path


def manifest_at(ref: str) -> dict:
    text = subprocess.run(["git", "show", f"{ref}:Resources/tools.json"], check=True, capture_output=True, text=True).stdout
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("refs", nargs="+", help="git refs whose Resources/tools.json to read")
    parser.add_argument("--catalog", default="Resources/tools.json", type=Path)
    args = parser.parse_args()

    catalog = {t["id"] for t in json.loads(args.catalog.read_text())["tools"]}
    rows: dict[str, dict] = {}
    for ref in args.refs:
        for tool in manifest_at(ref)["tools"]:
            row = rows.setdefault(tool["id"], {"refs": [], "tool": tool})
            row["refs"].append(ref)

    print(f"{'id':24} {'method':13} {'admin':6} {'bucket':8} refs")
    for tool_id in sorted(rows, key=lambda t: (t in catalog, t)):
        tool = rows[tool_id]["tool"]
        install = tool.get("install", {})
        bucket = "catalog" if tool_id in catalog else "review"
        admin = "yes" if install.get("requires_admin") else ""
        print(f"{tool_id:24} {install.get('method', '?'):13} {admin:6} {bucket:8} {', '.join(rows[tool_id]['refs'])}")


if __name__ == "__main__":
    main()
