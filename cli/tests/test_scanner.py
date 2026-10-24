import pytest

from setmac import scanner


def rules(text):
    return {(f.rule, f.severity) for f in scanner.scan_text(text, "f")}


@pytest.mark.parametrize("text, rule", [
    ("token = ghp_" + "a1B2" * 9, "github-token"),
    ("github_pat_" + "A1b2C3d4E5f6G7h8I9j0K1", "github-token"),
    ("ANTHROPIC_API_KEY=sk-ant-" + "x" * 30, "api-key"),
    ("xoxb-1234567890-abcdef", "slack-token"),
    ("aws_access_key_id = AKIAABCDEFGHIJKLMNOP", "aws-key"),
    ("-----BEGIN RSA PRIVATE KEY-----", "private-key"),
    ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U", "jwt"),
    ("password: correct-horse-battery-staple", "assigned-secret"),
])
def test_high_rules(text, rule):
    assert (rule, "high") in rules(text)


@pytest.mark.parametrize("text, rule", [
    ("user.email = someone@example.com", "email"),
    ("source /Users/alice/.zprofile", "home-path"),
    ("Host build.lan", "local-host"),
    ("secret-ish: Zq8XvL2pRt9WbN4mKd7YhF3s", "high-entropy"),
])
def test_medium_rules(text, rule):
    assert (rule, "medium") in rules(text)


def test_ordinary_config_is_clean():
    text = "alias ll='ls -l'\nexport PATH=\"$HOME/.local/bin:$PATH\"\nsource /Users/Shared/env\nset -g mouse on\n"
    assert scanner.scan_text(text, "f") == []


def test_findings_never_show_the_value():
    value = "ghp_" + "a1B2" * 9
    finding = next(f for f in scanner.scan_text(f"x={value}", "zshrc") if f.rule == "github-token")
    assert value not in finding.describe()
    assert finding.snippet.startswith("ghp_") and "(40 chars)" in finding.snippet
    assert "github-token:zshrc" in finding.describe()  # how to allow it


def test_allow_file_and_accepted_medium(tmp_path):
    (tmp_path / ".setmac-scan-allow").write_text("# reviewed\nemail:git/*\n")
    findings = scanner.scan_text("email = me@example.com", "git/config") + scanner.scan_text("ghp_" + "a1B2" * 9, "zshrc")
    allow = scanner.load_allow(tmp_path)
    assert [f.rule for f in scanner.blocking(findings, allow)] == ["github-token"]
    assert scanner.blocking(scanner.scan_text("me@example.com", "other"), [], accept_medium=True) == []
