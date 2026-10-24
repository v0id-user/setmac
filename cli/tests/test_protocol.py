"""Golden fixture for the JSON-line protocol the app parses.

Each line in fixtures/protocol.jsonl is the exact output of one emit_* call
below. A failure here means an event changed shape: the app may stop
understanding it. Add new event types or fields; don't rename or remove them.
"""

from pathlib import Path

from setmac import output

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


def test_events_match_the_golden_fixture(capsys):
    emit_every_event()
    assert capsys.readouterr().out.splitlines() == FIXTURE.read_text().splitlines()


def test_fixture_covers_every_emit_function():
    emitters = {name for name in dir(output) if name.startswith("emit_")}
    source = Path(__file__).read_text()
    assert {name for name in emitters if f"output.{name}(" not in source} == set()
