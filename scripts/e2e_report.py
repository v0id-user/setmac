"""Summarize a `setmac-cli install` JSON-line log and fail on unexpected results.

Usage: e2e_report.py LOG [--allow-failed id,id] [--expect-no-installs]
"""

import argparse
import json
import sys
from collections import defaultdict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log")
    parser.add_argument("--allow-failed", default="", help="Tool ids allowed to fail")
    parser.add_argument("--expect-no-installs", action="store_true", help="Second run: nothing should install")
    args = parser.parse_args()

    allowed = {t for t in args.allow_failed.split(",") if t}
    logs: dict[str, list[str]] = defaultdict(list)
    errors: dict[str, str] = {}
    installed: list[str] = []
    summary = None
    auth_prompts = 0

    with open(args.log) as f:
        for raw in f:
            raw = raw.strip()
            if not raw.startswith("{"):
                continue
            msg = json.loads(raw)
            tool = msg.get("tool") or "-"
            kind = msg["type"]
            if kind == "log":
                logs[tool].append(msg.get("message", ""))
            elif kind == "error":
                errors[tool] = msg.get("message", "")
            elif kind == "complete":
                installed.append(tool)
            elif kind == "auth_required":
                auth_prompts += 1
            elif kind == "summary":
                summary = msg

    print("## setmac end-to-end result\n")
    if summary is None:
        print("No summary line: the run crashed or was killed.")
        for line in logs["-"][-20:]:
            print("   ", line)
        return 1

    failed = summary.get("failed", [])
    print(f"Summary: {summary['message']}")
    print(f"Password prompts: {auth_prompts}")
    print(f"Installed this run ({len(installed)}): {', '.join(installed) or 'none'}\n")

    unexpected = [t for t in failed if t not in allowed]
    for tool in failed:
        tag = "expected" if tool in allowed else "UNEXPECTED"
        print(f"### {tool} failed ({tag}): {errors.get(tool, '')}")
        for line in logs[tool][-15:]:
            print("    " + line)
        print()

    ok = True
    if unexpected:
        print(f"Unexpected failures: {', '.join(unexpected)}")
        ok = False
    if auth_prompts > 1:
        print("The password was requested more than once.")
        ok = False
    if args.expect_no_installs and installed:
        print(f"Second run installed again (not idempotent): {', '.join(installed)}")
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
