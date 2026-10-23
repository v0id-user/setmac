from pathlib import Path

from setmac.commands.brewfile import render_brewfile
from setmac.installers import base, defaults
from setmac.registry import DefaultSpec, Registry

MANIFEST = Path(__file__).parents[2] / "Resources" / "tools.json"


def test_install_commands_for_new_methods():
    registry = Registry(MANIFEST)
    assert base.install_command(registry.get("node")) == ["mise", "use", "--global", "--yes", "node@lts"]
    assert base.install_command(registry.get("keynote")).startswith("mas install 409183694")
    assert base.install_command(registry.get("git")) == ["brew", "install", "git"]


def test_brewfile_lists_brew_and_app_store_tools():
    text = render_brewfile(Registry(MANIFEST))
    assert 'brew "git"' in text
    assert 'cask "ghostty"' in text
    assert 'mas "Keynote", id: 409183694' in text
    assert "node" not in text  # runtimes come from mise


def test_defaults_compare_by_type(monkeypatch):
    current = {"autohide": "1", "tilesize": "43", "style": "Nlsv", "margins": "0"}
    monkeypatch.setattr(defaults, "_read", lambda spec: current.get(spec.key))
    assert defaults.matches(DefaultSpec("com.apple.dock", "autohide", "bool", True))
    assert defaults.matches(DefaultSpec("com.apple.dock", "tilesize", "float", 43.0))
    assert defaults.matches(DefaultSpec("com.apple.finder", "style", "string", "Nlsv"))
    assert defaults.matches(DefaultSpec("x", "margins", "bool", False))
    assert not defaults.matches(DefaultSpec("x", "margins", "bool", True))
    assert not defaults.matches(DefaultSpec("x", "unset", "bool", False))
