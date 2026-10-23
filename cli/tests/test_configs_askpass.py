import json
import subprocess
import sys

import pytest

from setmac import askpass
from setmac.commands import configs
from setmac.registry import Registry


def test_apply_backs_up_once_and_is_idempotent(tmp_path, monkeypatch):
    home, bundle = tmp_path / "home", tmp_path / "bundle"
    home.mkdir()
    bundle.mkdir()
    (bundle / "zshrc").write_text("new\n")
    (home / ".zshrc").write_text("old\n")
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({"tools": [{
        "id": "zsh", "name": "zsh", "depends_on": [],
        "install": {"method": "config"},
        "configs": [{"source": "~/.zshrc", "target": "zshrc"}],
    }]}))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(configs, "_configs_dir", lambda: bundle)
    registry = Registry(manifest)

    assert configs.apply_configs(registry) == 1
    assert (home / ".zshrc").read_text() == "new\n"
    backups = list((home / ".config" / "setmac-backup").glob("*/zshrc"))
    assert [b.read_text() for b in backups] == ["old\n"]

    # A second run changes nothing and makes no second backup.
    assert configs.apply_configs(registry) == 0
    assert len(list((home / ".config" / "setmac-backup").iterdir())) == 1


def test_apply_skips_configs_of_failed_tools(tmp_path, monkeypatch):
    home, bundle = tmp_path / "home", tmp_path / "bundle"
    home.mkdir()
    bundle.mkdir()
    (bundle / "zshrc").write_text("new\n")
    manifest = tmp_path / "tools.json"
    manifest.write_text(json.dumps({"tools": [{
        "id": "ohmyzsh", "name": "Oh My Zsh", "depends_on": [],
        "install": {"method": "config"},
        "configs": [{"source": "~/.zshrc", "target": "zshrc"}],
    }]}))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(configs, "_configs_dir", lambda: bundle)

    assert configs.apply_configs(Registry(manifest), skip_tools={"ohmyzsh"}) == 0
    assert not (home / ".zshrc").exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="the askpass helper uses macOS nc -U")
def test_askpass_helper_returns_verified_password(monkeypatch):
    prompts = []
    monkeypatch.setattr(askpass, "_read_password", lambda tool, msg: prompts.append(msg) or ["bad", "good"][len(prompts) - 1])
    monkeypatch.setattr(askpass, "_verify", lambda pw: pw == "good")
    server = askpass.AskpassServer()
    try:
        env = server.env()
        for _ in range(2):
            out = subprocess.run([env["SUDO_ASKPASS"], "Password:"], env={**env, "PATH": "/usr/bin:/bin"},
                                 capture_output=True, text=True, timeout=10)
            assert out.stdout == "good\n"
        assert prompts == ["Admin password required for installation", "Wrong password. Try again."]
    finally:
        server.close()
