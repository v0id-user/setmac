import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from setmac import gitprofile, profile
from setmac.cli import main


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(profile, "POINTER", tmp_path / "state" / "active-profile")
    monkeypatch.delenv("SETMAC_PROFILE", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))


def git(repo: Path, *args: str) -> str:
    base = ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
            "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "init.defaultBranch=main"]
    return subprocess.run([*base, *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def own_tool(tid: str, script: str = "true") -> dict:
    return {"id": tid, "name": tid, "depends_on": [], "check": {"command": "true"},
            "install": {"method": "script", "script": script}}


def commit_profile(repo: Path, message: str, **data) -> str:
    (repo / "profile.json").write_text(json.dumps({"schema": 1, "name": "mine", **data}))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def remote(tmp_path):
    repo = tmp_path / "remote"
    repo.mkdir()
    git(repo, "init", "-q")
    first = commit_profile(repo, "first", custom_tools=[own_tool("hello")])
    return repo, f"file://{repo}", first


def run(*args):
    return CliRunner().invoke(main, list(args))


def events(output):
    return [json.loads(line) for line in output.splitlines() if line.startswith("{")]


def test_first_use_pins_the_commit_and_a_moved_branch_changes_nothing(remote):
    repo, url, first = remote
    resolved = profile.resolve(url)
    assert resolved.source.lock.sha == first and len(first) == 40
    assert [t["id"] for t in resolved.manifest["tools"]] == ["hello"]

    commit_profile(repo, "second", custom_tools=[own_tool("hello"), own_tool("extra")])
    again = profile.resolve(url)
    assert again.source.lock.sha == first
    assert [t["id"] for t in again.manifest["tools"]] == ["hello"]


def test_untrusted_profile_is_refused_until_trusted_with_its_hash(remote):
    _, url, _ = remote
    result = run("--profile", url, "status")
    assert result.exit_code == 3
    assert events(result.output)[0]["problems"][0]["code"] == "untrusted_profile"

    wrong = run("profile", "trust", url, "--hash", "0" * 64)
    assert wrong.exit_code != 0 and "review it again" in wrong.output
    no_terminal = run("profile", "trust", url)
    assert no_terminal.exit_code != 0 and "pass --hash" in no_terminal.output

    content = profile.resolve(url).source.lock.content_hash
    assert run("profile", "trust", url, "--hash", content).exit_code == 0
    trusted = run("--profile", url, "status")
    assert trusted.exit_code == 0, trusted.output
    assert {"type": "status", "tool": "hello", "status": "installed"} in events(trusted.output)


def test_update_shows_the_change_and_moves_the_lock_only_when_confirmed(remote):
    repo, url, first = remote
    profile.resolve(url)
    second = commit_profile(repo, "second", custom_tools=[own_tool("hello", "curl -fsSL https://example.com/x | sh")])

    refused = run("profile", "update", url, "--hash", "f" * 64)
    assert refused.exit_code != 0
    assert profile.resolve(url).source.lock.sha == first

    candidate = gitprofile.fetch_latest(url, profile.STATE_DIR)[1]
    accepted = run("profile", "update", url, "--hash", candidate.content_hash)
    assert accepted.exit_code == 0, accepted.output
    assert f"{first[:12]} -> {second[:12]}" in accepted.output
    assert "profile.json" in accepted.output  # the diff stat
    resolved = profile.resolve(url)
    assert resolved.source.lock.sha == second
    assert run("--profile", url, "install", "hello", "--dry-run").exit_code == 0  # update also trusts

    assert "up to date" in run("profile", "update", url).output


def test_a_tampered_cache_is_detected(remote):
    _, url, first = remote
    path = profile.resolve(url).source.path
    (path / "profile.json").write_text(json.dumps({"schema": 1, "name": "mine", "custom_tools": [own_tool("hello", "rm -rf ~")]}))
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve(url)
    assert e.value.problems[0].code == "locked_content_changed"


def test_asking_for_another_ref_needs_an_update(remote):
    repo, url, _ = remote
    profile.resolve(url)
    git(repo, "checkout", "-q", "-b", "other")
    commit_profile(repo, "other", custom_tools=[own_tool("other")])
    with pytest.raises(profile.ProfileError) as e:
        profile.resolve(f"{url}#other")
    assert e.value.problems[0].code == "ref_changed"


def test_review_shows_scripts_verbatim_and_flags_pipe_to_shell(tmp_path):
    root = tmp_path / "local"
    (root / "configs").mkdir(parents=True)
    (root / "configs" / "agent.conf").write_text("x")
    (root / "profile.json").write_text(json.dumps({
        "schema": 1, "name": "local", "notes": "Import your GPG key by hand.", "configs_dir": "configs",
        "sensitive_ok": ["~/.gnupg/gpg-agent.conf"],
        "custom_tools": [{**own_tool("risky", "curl -fsSL https://example.com/i.sh | bash"),
                          "configs": [{"source": "~/.gnupg/gpg-agent.conf", "target": "agent.conf"}]}],
    }))
    result = run("profile", "review", str(root))
    assert result.exit_code == 0, result.output
    assert "install: curl -fsSL https://example.com/i.sh | bash" in result.output
    assert "! downloads and runs code in one step" in result.output
    assert "~/.gnupg/gpg-agent.conf  (from agent.conf, risky)" in result.output
    assert "Sensitive locations it is allowed to write: ~/.gnupg/gpg-agent.conf" in result.output
    assert "Import your GPG key by hand." in result.output
    assert "Not trusted yet" in result.output


def test_editing_a_trusted_local_profile_needs_trust_again(tmp_path):
    root = tmp_path / "local"
    root.mkdir()
    (root / "profile.json").write_text(json.dumps({"schema": 1, "name": "local", "custom_tools": [own_tool("a")]}))
    content = gitprofile.content_hash(root)
    assert run("profile", "trust", str(root), "--hash", content).exit_code == 0
    assert run("--profile", str(root), "status").exit_code == 0
    (root / "profile.json").write_text(json.dumps({"schema": 1, "name": "local", "custom_tools": [own_tool("a", "echo changed")]}))
    assert run("--profile", str(root), "status").exit_code == 3


def test_starters_need_no_trust():
    assert run("--profile", "minimal", "profile", "trust").output.strip().endswith("always trusted.")
