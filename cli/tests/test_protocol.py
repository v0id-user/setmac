"""Golden fixture for the JSON-line protocol the app parses.

Each line in fixtures/protocol.jsonl is the exact output of one emit_* call
below. A failure here means an event changed shape: the app may stop
understanding it. Add new event types or fields; don't rename or remove them.
"""

from pathlib import Path

from setmac import output
from setmac.validate import Problem

FIXTURE = Path(__file__).parent / "fixtures" / "protocol.jsonl"


def emit_every_event():
    output.emit_status("git", "installed", version="git version 2.50.0")
    output.emit_status("git", "not_installed")
    output.emit_progress("git", "Installing Git... (1/3)")
    output.emit_log("Installing 3 tool(s) in dependency order...")
    output.emit_log("$ brew install git", tool="git")
    output.emit_error("git", "Install of Git failed (see log)")
    output.emit_complete("git", version="git version 2.50.0")
    output.emit_skipped("rosetta", "needs_admin")
    output.emit_auth_required("rosetta", "Admin password required for installation")
    output.emit_config_status("zsh", "zshrc", "~/.zshrc", "bundled+system")
    output.emit_summary("1 installed, 1 already set up, 1 failed: rosetta", failed=["rosetta"])
    output.emit_profile_error("web", [Problem("unknown_tool", "nope", "tools.add", "profile 'web' adds unknown tool 'nope'")])
    output.emit_manifest("minimal", {"version": "1.0.0", "name": "minimal", "description": "", "tools": []})
    output.emit_manifest("me", {"version": "1", "name": "me", "description": "", "tools": []},
                         spec="~/me", trusted=False, content_hash="ab12")
    output.emit_profiles("web", "pointer", [{"name": "web", "description": "Web work"}])
    output.emit_review("~/me", "Profile: me", "ab12", False)
    output.emit_config_diff("zshrc", "-old\n+new\n")
    output.emit_backups([{"stamp": "20261024-101500", "ids": ["zshrc"]}])
    output.emit_configs([{"id": "zsh/zshrc", "tool": "zsh", "source": "~/.zshrc", "target": "zsh/zshrc", "is_dir": False, "status": "differs"}])


def test_events_match_the_golden_fixture(capsys):
    emit_every_event()
    assert capsys.readouterr().out.splitlines() == FIXTURE.read_text().splitlines()


def test_fixture_covers_every_emit_function():
    emitters = {name for name in dir(output) if name.startswith("emit_")}
    source = Path(__file__).read_text()
    assert {name for name in emitters if f"output.{name}(" not in source} == set()
