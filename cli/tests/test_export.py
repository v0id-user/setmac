import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from setmac import export, profile
from setmac.cli import main


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "user.name=Test",
                    "-c", "user.email=test@example.invalid", "-c", "init.defaultBranch=main", *args],
                   cwd=repo, check=True, capture_output=True)


@pytest.fixture
def old_repo(tmp_path, monkeypatch):
    """A repo whose `old` tag has an all-in-one manifest with a catalog and a personal tool."""
    monkeypatch.setattr(profile, "STATE_DIR", tmp_path / "state")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = tmp_path / "setmac"
    (repo / "Resources" / "configs").mkdir(parents=True)
    tools = [
        {"id": "git", "name": "Git", "depends_on": [], "install": {"method": "brew_formula", "target": "git"},
         "configs": [{"source": "~/.gitconfig", "target": "gitconfig"}]},
        {"id": "myapp", "name": "My App", "depends_on": ["git", "gone"], "check": {"path": "/Applications/My App.app"},
         "install": {"method": "brew_cask", "target": "myapp"}, "configs": [{"source": "~/.myapprc", "target": "myapprc"}]},
        {"id": "ghost", "name": "Ghost", "depends_on": [], "install": {"method": "config"},
         "configs": [{"source": "~/.ghostrc", "target": "ghostrc"}]},
    ]
    (repo / "Resources" / "tools.json").write_text(json.dumps({"tools": tools}))
    (repo / "Resources" / "configs" / "gitconfig").write_text("[core]\n\teditor = vim\n")
    (repo / "Resources" / "configs" / "myapprc").write_text("old setting\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "old")
    git(repo, "tag", "old")
    return repo, home


def build(repo, out, **kw):
    return export.build(repo, ["old"], out, "me", "minimal", **kw)


def test_export_splits_catalog_and_personal_tools(old_repo, tmp_path):
    repo, home = old_repo
    (home / ".myapprc").write_text("newer setting\n")
    out = tmp_path / "me"
    report = build(repo, out)

    data = json.loads((out / "profile.json").read_text())
    assert [t["id"] for t in data["custom_tools"]] == ["myapp"]
    assert data["custom_tools"][0]["depends_on"] == ["git"]  # a dependency that is gone is dropped
    assert data["tools"]["add"] == ["git"]
    assert data["overrides"] == {"git": {"configs": [{"source": "~/.gitconfig", "target": "gitconfig"}]}}
    assert (out / "configs" / "myapprc").read_text() == "newer setting\n"  # this Mac wins
    assert (out / "configs" / "gitconfig").read_text().startswith("[core]")  # else the ref
    assert report.differs == ["~/.myapprc (myapp)"]
    assert any("ghost" in line for line in report.dropped)
    assert (out / ".git").is_dir()
    assert profile.resolve(str(out)).profile.name == "me"
    assert CliRunner().invoke(main, ["profile", "validate", str(out)]).exit_code == 0


def test_export_refuses_unsafe_destinations(old_repo, tmp_path):
    repo, _ = old_repo
    with pytest.raises(export.ExportError, match="inside"):
        build(repo, repo / "private")
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "file").write_text("x")
    with pytest.raises(export.ExportError, match="not empty"):
        build(repo, busy)


def test_export_stops_on_secrets_and_asks_about_personal_data(old_repo, tmp_path):
    repo, home = old_repo
    (home / ".myapprc").write_text("token = ghp_" + "a1B2" * 9 + "\n")
    with pytest.raises(export.ExportError, match="secrets found"):
        build(repo, tmp_path / "a")
    assert not (tmp_path / "a").exists()

    (home / ".myapprc").write_text("owner = someone@example.com\n")
    with pytest.raises(export.ExportError, match="--accept-reviewed"):
        build(repo, tmp_path / "b")
    report = build(repo, tmp_path / "b", accept_reviewed=True)
    assert [f.rule for f in report.findings] == ["email"]
