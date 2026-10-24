import json
import os
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from setmac import gitprofile, profile
from setmac.cli import main
from setmac.commands import configs


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(profile, "POINTER", tmp_path / "state" / "active-profile")
    monkeypatch.delenv("SETMAC_PROFILE", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def dots(tmp_path, home):
    """A trusted local profile with a file and a folder dotfile."""
    root = tmp_path / "me"
    (root / "configs" / "app").mkdir(parents=True)
    (root / "configs" / "zshrc").write_text("profile zshrc\n")
    (root / "configs" / "app" / "settings").write_text("profile settings\n")
    (root / "profile.json").write_text(json.dumps({
        "schema": 1, "name": "me", "configs_dir": "configs",
        "custom_tools": [{
            "id": "dots", "name": "Dots", "depends_on": [], "check": {"command": "true"},
            "install": {"method": "script", "script": "true"},
            "configs": [{"source": "~/.zshrc", "target": "zshrc"},
                        {"source": "~/.config/app", "target": "app", "is_dir": True}],
        }],
    }))
    trust(root)
    return root


def trust(root: Path):
    assert run("profile", "trust", str(root), "--hash", gitprofile.content_hash(root)).exit_code == 0


def run(*args, input=None):
    return CliRunner().invoke(main, list(args), input=input)


def statuses(root):
    result = run("--profile", str(root), "configs", "list", "--json")
    assert result.exit_code == 0, result.output
    return {c["id"]: c["status"] for c in json.loads(result.output)["configs"]}


def test_install_all_never_touches_an_existing_dotfile(dots, home):
    (home / ".zshrc").write_bytes(b"mine\x00exact bytes\n")
    result = run("--profile", str(dots), "install", "all")
    assert result.exit_code == 0, result.output
    assert (home / ".zshrc").read_bytes() == b"mine\x00exact bytes\n"
    assert not (home / ".config" / "setmac-backup").exists()


def test_list_reports_missing_identical_and_differs(dots, home):
    assert statuses(dots) == {"zshrc": "missing", "app": "missing"}
    (home / ".zshrc").write_text("profile zshrc\n")
    (home / ".config" / "app").mkdir(parents=True)
    (home / ".config" / "app" / "settings").write_text("mine\n")
    assert statuses(dots) == {"zshrc": "identical", "app": "differs"}


def test_apply_needs_a_choice_without_a_terminal(dots, home):
    (home / ".zshrc").write_text("mine\n")
    result = run("--profile", str(dots), "configs", "apply")
    assert result.exit_code != 0 and "pass --yes" in result.output
    assert (home / ".zshrc").read_text() == "mine\n"


def test_apply_only_backs_up_and_restore_round_trips(dots, home):
    (home / ".zshrc").write_text("mine\n")
    os.chmod(home / ".zshrc", 0o600)
    result = run("--profile", str(dots), "configs", "apply", "--only", "zshrc", "--yes")
    assert result.exit_code == 0, result.output
    assert (home / ".zshrc").read_text() == "profile zshrc\n"
    assert not (home / ".config" / "app").exists()  # not chosen

    backups = list((home / ".config" / "setmac-backup").iterdir())
    assert len(backups) == 1
    manifest = json.loads((backups[0] / "manifest.json").read_text())
    assert manifest["entries"] == [{"id": "zshrc", "source": "~/.zshrc", "backup": "zshrc"}]
    assert (backups[0] / "zshrc").read_text() == "mine\n"
    assert oct((backups[0] / "zshrc").stat().st_mode & 0o777) == oct(0o600)  # mode kept

    # Applying a file that did not exist, then restoring, removes it again.
    assert run("--profile", str(dots), "configs", "apply", "--only", "app", "--yes").exit_code == 0
    assert (home / ".config" / "app" / "settings").read_text() == "profile settings\n"
    assert run("configs", "restore", "latest").exit_code == 0
    assert not (home / ".config" / "app").exists()

    assert run("configs", "restore", backups[0].name).exit_code == 0
    assert (home / ".zshrc").read_text() == "mine\n"
    names = run("configs", "backups").output
    assert "before-restore" in names  # the state before each restore is kept too


def test_apply_moves_a_symlink_instead_of_following_it(dots, home, tmp_path):
    precious = tmp_path / "precious"
    precious.write_text("do not overwrite\n")
    os.symlink(precious, home / ".zshrc")
    assert run("--profile", str(dots), "configs", "apply", "--only", "zshrc", "--yes").exit_code == 0
    assert precious.read_text() == "do not overwrite\n"
    assert not (home / ".zshrc").is_symlink()
    backup = next((home / ".config" / "setmac-backup").glob("*/zshrc"))
    assert backup.is_symlink() and os.readlink(backup) == str(precious)


def test_install_with_configs_applies_after_installing(dots, home):
    result = run("--profile", str(dots), "install", "all", "--with-configs", "--yes")
    assert result.exit_code == 0, result.output
    assert (home / ".zshrc").read_text() == "profile zshrc\n"


def test_diff_shows_the_change(dots, home):
    (home / ".zshrc").write_text("mine\n")
    result = run("--profile", str(dots), "configs", "diff", "zshrc")
    assert "-mine" in result.output and "+profile zshrc" in result.output


def test_capture_scans_ignores_and_refuses_unsafe_places(dots, home):
    (home / ".zshrc").write_text("export TOKEN=ghp_" + "a1B2" * 9 + "\n")
    blocked = run("--profile", str(dots), "configs", "capture", "zshrc")
    assert blocked.exit_code != 0 and "github-token at zshrc:1" in blocked.output
    assert "a1B2" * 9 not in blocked.output  # redacted
    assert (dots / "configs" / "zshrc").read_text() == "profile zshrc\n"

    (home / ".zshrc").write_text("alias ll='ls -l'\n")
    (home / ".config" / "app").mkdir(parents=True)
    (home / ".config" / "app" / "settings").write_text("ok\n")
    (home / ".config" / "app" / "cache.db").write_text("junk\n")
    (dots / ".setmacignore").write_text("*.db\n")
    trust(dots)
    result = run("--profile", str(dots), "configs", "capture")
    assert result.exit_code == 0, result.output
    assert (dots / "configs" / "zshrc").read_text() == "alias ll='ls -l'\n"
    assert not (dots / "configs" / "app" / "cache.db").exists()

    starter = run("--profile", "minimal", "configs", "capture")
    assert starter.exit_code != 0 and "bundled starter" in starter.output


def test_capture_refuses_a_clone_of_the_public_repo(dots):
    subprocess.run(["git", "init", "-q", str(dots)], check=True)
    subprocess.run(["git", "-C", str(dots), "remote", "add", "origin", "git@github.com:v0id-user/setmac.git"], check=True)
    trust(dots)
    result = run("--profile", str(dots), "configs", "capture")
    assert result.exit_code != 0 and "public setmac repository" in result.output


def test_apply_refuses_a_profile_that_ships_a_secret(dots, home):
    (dots / "configs" / "zshrc").write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n")
    trust(dots)
    result = run("--profile", str(dots), "configs", "apply", "--yes")
    assert result.exit_code != 0 and "private-key" in result.output
    assert not (home / ".zshrc").exists()
    (dots / ".setmac-scan-allow").write_text("private-key:zshrc\n")
    trust(dots)
    assert run("--profile", str(dots), "configs", "apply", "--yes").exit_code == 0


def test_json_events_for_the_app(dots, home, tmp_path):
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    (fresh / "profile.json").write_text(json.dumps({"schema": 1, "name": "fresh"}))
    shown = json.loads(run("--profile", str(fresh), "profile", "show", "--json").output)
    assert shown["trusted"] is False and len(shown["content_hash"]) == 64 and shown["spec"] == str(fresh)
    review = json.loads(run("--profile", str(fresh), "profile", "review", "--json").output)
    assert review["type"] == "review" and review["content_hash"] == shown["content_hash"]
    assert json.loads(run("--profile", str(dots), "profile", "show", "--json").output)["trusted"] is True
    starter = json.loads(run("--profile", "web", "profile", "show", "--json").output)
    assert starter["trusted"] is True and "content_hash" not in starter

    (home / ".zshrc").write_text("mine\n")
    diff = json.loads(run("--profile", str(dots), "configs", "diff", "zshrc", "--json").output)
    assert diff == {"type": "config_diff", "id": "zshrc", "diff": diff["diff"]} and "+profile zshrc" in diff["diff"]
    assert json.loads(run("configs", "backups", "--json").output) == {"type": "backups", "backups": []}
    run("--profile", str(dots), "configs", "apply", "--only", "zshrc", "--yes")
    backups = json.loads(run("configs", "backups", "--json").output)["backups"]
    assert [b["ids"] for b in backups] == [["zshrc"]]

    listed = json.loads(run("profile", "list", "--json").output)
    assert listed["type"] == "profiles" and listed["source"] == "default"
