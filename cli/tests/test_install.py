import json

import pytest
from click.testing import CliRunner

from setmac import askpass
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


def cask_tool(tmp_path, check):
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({"tools": [{
        "id": "app", "name": "App", "depends_on": [], "check": check,
        "install": {"method": "brew_cask", "target": "app"},
    }]}))
    return Registry(manifest).get("app")


def test_brew_cask_with_a_path_trusts_the_path(monkeypatch, tmp_path):
    # brew lists a cask whose install stopped before the .app was copied.
    app = tmp_path / "App.app"
    tool = cask_tool(tmp_path, {"path": str(app)})
    monkeypatch.setattr(base, "_brew_inventory", lambda: {"formula": set(), "cask": {"app"}})
    assert base.check_tool(tool) == (False, None)

    # Installed by hand, outside brew.
    app.mkdir()
    monkeypatch.setattr(base, "_brew_inventory", lambda: {"formula": set(), "cask": set()})
    assert base.check_tool(tool)[0] is True


def test_brew_cask_without_a_path_uses_brew_or_the_command(monkeypatch, tmp_path):
    tool = cask_tool(tmp_path, {"command": "false"})
    monkeypatch.setattr(base, "_brew_inventory", lambda: {"formula": set(), "cask": set()})
    assert base.check_tool(tool)[0] is False
    monkeypatch.setattr(base, "_brew_inventory", lambda: {"formula": set(), "cask": {"app"}})
    assert base.check_tool(tool)[0] is True


def admin_manifest(tmp_path):
    root, child, plain = tmp_path / "root", tmp_path / "child", tmp_path / "plain"
    tools = [
        script_tool("root", root, f"touch {root}"),
        script_tool("child", child, f"touch {child}", deps=["root"]),
        script_tool("plain", plain, f"touch {plain}"),
    ]
    tools[0]["install"]["requires_admin"] = True
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({"tools": tools}))
    return Registry(manifest), root, child, plain


def test_admin_tools_are_skipped_when_the_password_is_refused(monkeypatch, tmp_path, capsys):
    registry, root, child, plain = admin_manifest(tmp_path)
    prompts = []
    monkeypatch.setattr(askpass, "sudo_ready", lambda: False)
    monkeypatch.setattr(askpass, "_read_password", lambda tool, msg: prompts.append(tool) or "")

    failed = install_mod.install_tools(registry.install_order(), registry, apply_dotfiles=False)

    assert failed == ["root", "child"]
    assert prompts == ["root"]  # asked once, up front, for the first admin tool
    assert plain.exists() and not root.exists() and not child.exists()
    out = events(capsys)
    assert {"type": "skipped", "tool": "root", "status": "needs_admin"} in out
    error = next(e for e in out if e["type"] == "error" and e["tool"] == "root")
    assert error["status"] == "error" and "admin password" in error["message"]
    assert out[-1]["failed"] == ["root", "child"]


def test_admin_tools_run_when_sudo_works_without_a_prompt(monkeypatch, tmp_path, capsys):
    registry, root, child, plain = admin_manifest(tmp_path)
    monkeypatch.setattr(askpass, "sudo_ready", lambda: True)
    monkeypatch.setattr(askpass, "_read_password", lambda tool, msg: pytest.fail("should not prompt"))

    assert install_mod.install_tools(registry.install_order(), registry, apply_dotfiles=False) == []
    assert root.exists() and child.exists()
    assert not any(e["type"] in ("skipped", "auth_required") for e in events(capsys))


def test_dry_run_lists_admin_tools_and_changes_nothing(monkeypatch, tmp_path):
    registry, root, child, plain = admin_manifest(tmp_path)
    monkeypatch.setattr(install_mod, "Registry", lambda: registry)

    result = CliRunner().invoke(install_mod.install_cmd, ["all", "--dry-run"])

    assert result.exit_code == 0, result.output
    out = [json.loads(line) for line in result.output.splitlines()]
    assert {"type": "status", "tool": "root", "status": "not_installed"} in out
    logs = [e["message"] for e in out if e["type"] == "log"]
    assert "Would install 3 tool(s): plain, root, child" in logs
    assert "Needs an admin password: root" in logs
    assert not (root.exists() or child.exists() or plain.exists())
