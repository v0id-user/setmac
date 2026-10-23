import json

from setmac.commands import install as install_mod
from setmac.installers import base
from setmac.registry import Registry


def events(capsys):
    return [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]


def script_tool(tid, marker, script, deps=()):
    return {
        "id": tid,
        "name": tid,
        "depends_on": list(deps),
        "check": {"path": str(marker)},
        "install": {"method": "script", "script": script},
    }


def test_failure_skips_dependents_and_reports_summary(tmp_path, capsys):
    ok, bad, child = tmp_path / "ok", tmp_path / "bad", tmp_path / "child"
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({"tools": [
        script_tool("ok", ok, f"echo hello && touch {ok}"),
        script_tool("bad", bad, "echo boom; exit 3"),
        script_tool("child", child, f"touch {child}", deps=["bad"]),
    ]}))
    registry = Registry(manifest)

    failed = install_mod.install_tools(registry.install_order(), registry, apply_dotfiles=False)

    assert failed == ["bad", "child"]
    assert ok.exists() and not child.exists()
    out = events(capsys)
    assert {"type": "log", "tool": "ok", "message": "hello"} in out
    assert any(e["type"] == "complete" and e["tool"] == "ok" for e in out)
    skipped = next(e for e in out if e.get("tool") == "child" and e["type"] == "error")
    assert "needs bad" in skipped["message"]
    summary = out[-1]
    assert summary["type"] == "summary" and summary["failed"] == ["bad", "child"]


def test_installer_that_passes_but_check_fails_is_an_error(tmp_path, capsys):
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({"tools": [script_tool("liar", tmp_path / "never", "true")]}))
    registry = Registry(manifest)

    assert install_mod.install_tools(registry.tools, registry, apply_dotfiles=False) == ["liar"]
    assert not any(e["type"] == "complete" for e in events(capsys))


def test_brew_formula_ignores_stub_commands(monkeypatch, tmp_path):
    # /usr/bin/git exists on a fresh Mac, but brew git is not installed.
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({"tools": [{
        "id": "git", "name": "Git", "depends_on": [],
        "check": {"command": "true"},
        "install": {"method": "brew_formula", "target": "git"},
    }]}))
    git = Registry(manifest).get("git")

    monkeypatch.setattr(base, "_brew_inventory", lambda: {"formula": set(), "cask": set()})
    assert base.check_tool(git) == (False, None)

    monkeypatch.setattr(base, "_brew_inventory", lambda: {"formula": {"git"}, "cask": set()})
    assert base.check_tool(git)[0] is True
