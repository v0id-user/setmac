import json
import os
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from setmac import profile
from setmac.cli import main
from setmac.registry import ManifestError, Registry

RESOURCES = Path(__file__).parents[2] / "Resources"
CATALOG = json.loads((RESOURCES / "tools.json").read_text())


def tool(tid, deps=(), method="script", **extra):
    return {"id": tid, "name": tid, "depends_on": list(deps), "check": {"command": "true"},
            "install": {"method": method, "script": "true"}, **extra}


SMALL_CATALOG = {"version": "1", "name": "catalog", "description": "", "tools": [
    tool("base"), tool("git", ["base"]), tool("node", ["base"]), tool("app", ["base"]),
    {"id": "settings", "name": "settings", "depends_on": [], "install": {"method": "defaults"},
     "defaults": [{"domain": "d", "key": "k", "type": "bool", "value": True}]},
]}


def write_profile(root: Path, **data) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "profile.json").write_text(json.dumps({"schema": 1, "name": root.name, **data}))
    return root


def merged_ids(spec):
    return [t["id"] for t in profile.resolve(spec, catalog=SMALL_CATALOG).manifest["tools"]]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """No real pointer file or SETMAC_PROFILE, and a throwaway home."""
    monkeypatch.setattr(profile, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(profile, "POINTER", tmp_path / "state" / "active-profile")
    monkeypatch.delenv("SETMAC_PROFILE", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


# ─── Resolution ───────────────────────────────────────────────


def test_active_profile_order(monkeypatch):
    assert profile.active_spec() == ("minimal", "default")
    profile.write_pointer("web")
    assert profile.active_spec() == ("web", "pointer")
    monkeypatch.setenv("SETMAC_PROFILE", "backend")
    assert profile.active_spec() == ("backend", "env")
    assert profile.active_spec("mobile") == ("mobile", "flag")


def test_profile_flag_env_and_pointer_reach_the_commands(monkeypatch):
    def shown(*args):
        result = CliRunner().invoke(main, [*args, "profile", "show", "--json"])
        assert result.exit_code == 0, result.output
        return json.loads(result.output)["profile"]

    assert shown() == "minimal"
    assert CliRunner().invoke(main, ["profile", "use", "web"]).exit_code == 0
    assert shown() == "web"
    monkeypatch.setenv("SETMAC_PROFILE", "backend")
    assert shown() == "backend"
    assert shown("--profile", "mobile") == "mobile"


def test_unusable_profile_reports_profile_error_and_exits_3(tmp_path):
    bad = write_profile(tmp_path / "bad", tools={"add": ["no-such-tool"]})
    result = CliRunner().invoke(main, ["--profile", str(bad), "status"])
    assert result.exit_code == 3
    events = [json.loads(line) for line in result.output.splitlines()]
    assert events[0]["type"] == "profile_error"
    assert events[0]["problems"][0]["code"] == "unknown_tool"
    assert events[1] == {"type": "error", "message": events[0]["message"], "status": "error"}


def test_use_refuses_a_broken_profile_and_keeps_the_old_pointer(tmp_path):
    profile.write_pointer("web")
    bad = write_profile(tmp_path / "bad", tools={"add": ["no-such-tool"]})
    assert CliRunner().invoke(main, ["profile", "use", str(bad)]).exit_code == 3
    assert profile.read_pointer() == "web"


def test_specs_that_are_ambiguous_or_missing():
    for spec, code in [("relative/dir", "relative_spec"),
                       ("no-such-starter", "profile_not_found")]:
        with pytest.raises(profile.ProfileError) as e:
            profile.locate(spec)
        assert e.value.problems[0].code == code, spec


# ─── Merging ──────────────────────────────────────────────────


def test_add_pulls_in_dependencies_in_catalog_order(tmp_path):
    p = write_profile(tmp_path / "p", tools={"add": ["node", "git"]})
    assert merged_ids(str(p)) == ["base", "git", "node"]


def test_extends_add_and_remove(tmp_path):
    write_profile(tmp_path / "repo" / "parent", tools={"add": ["git", "node"]})
    child = write_profile(tmp_path / "repo" / "child", extends="../parent", tools={"remove": ["node"]})
    # `..` is not allowed in extends; a nested parent is.
    with pytest.raises(profile.ProfileError, match="use a starter name or a path inside the profile"):
        merged_ids(str(child))
    write_profile(child / "base", tools={"add": ["git", "node"]})
    # A bare name means a starter; a profile in this folder needs a path: ./base.
    write_profile(child, extends="./base", tools={"remove": ["node"], "add": ["app"]})
    assert merged_ids(str(child)) == ["base", "git", "app"]


def test_removing_a_dependency_is_an_error_naming_both(tmp_path):
    p = write_profile(tmp_path / "p", tools={"add": ["git"], "remove": ["base"]})
    with pytest.raises(profile.ProfileError, match="'git' depends on 'base', which the profile removes"):
        merged_ids(str(p))


def test_extends_cycle_and_depth(tmp_path):
    a = tmp_path / "a"
    write_profile(a, extends="./b")
    write_profile(a / "b", extends="./c")
    write_profile(a / "b" / "c", extends="./d")
    write_profile(a / "b" / "c" / "d", extends="./e")
    write_profile(a / "b" / "c" / "d" / "e")
    with pytest.raises(profile.ProfileError) as e:
        profile.load_chain(str(a))
    assert e.value.problems[0].code == "extends_too_deep"

    loop = write_profile(tmp_path / "loop", extends="./.")
    with pytest.raises(profile.ProfileError) as e:
        profile.load_chain(str(loop))
    assert e.value.problems[0].code == "extends_cycle"

    # A symlink cannot lead a parent outside the profile (and so cannot loop back either).
    escape = write_profile(tmp_path / "escape", extends="./inner")
    write_profile(escape / "inner", extends="./up")
    os.symlink(escape, escape / "inner" / "up")
    with pytest.raises(profile.ProfileError) as e:
        profile.load_chain(str(escape))
    assert e.value.problems[0].code == "invalid_extends"


def test_custom_tools_overrides_and_collisions(tmp_path):
    p = write_profile(tmp_path / "p", custom_tools=[tool("mine", ["git"])],
                      overrides={"git": {"name": "Git (mine)", "install": {"script": "echo hi"}}})
    resolved = profile.resolve(str(p), catalog=SMALL_CATALOG)
    by_id = {t["id"]: t for t in resolved.manifest["tools"]}
    assert list(by_id) == ["base", "git", "mine"]
    assert by_id["git"]["name"] == "Git (mine)"
    assert by_id["git"]["install"] == {"method": "script", "script": "echo hi"}  # merged, not replaced

    clash = write_profile(tmp_path / "clash", custom_tools=[tool("git")])
    with pytest.raises(profile.ProfileError) as e:
        merged_ids(str(clash))
    assert e.value.problems[0].code == "duplicate_id"


def test_macos_settings_are_opt_in(tmp_path):
    off = write_profile(tmp_path / "off", tools={"add": ["git", "settings"]})
    assert "settings" not in merged_ids(str(off))
    on = write_profile(tmp_path / "on", tools={"add": ["git"]}, macos_defaults={"enabled": True})
    assert "settings" in merged_ids(str(on))


def test_shape_problems_are_reported_together(tmp_path):
    p = write_profile(tmp_path / "p", schema=2, colour="blue", tools={"add": "git"})
    with pytest.raises(profile.ProfileError) as e:
        profile.load(p)
    assert {x.code for x in e.value.problems} == {"unsupported_schema", "unknown_field", "invalid_field"}


def test_merged_tools_always_have_the_fields_the_app_needs(tmp_path):
    p = write_profile(tmp_path / "p", custom_tools=[{"id": "bare", "name": "Bare", "check": {"command": "true"},
                                                    "install": {"method": "script", "script": "true"}}])
    bare = profile.resolve(str(p), catalog=SMALL_CATALOG).manifest["tools"][-1]
    assert {"description", "category", "icon", "icon_color", "depends_on"} <= set(bare)


# ─── Config path rules ────────────────────────────────────────


def config_profile(root, source, target="f", make_target=True, **extra):
    if make_target:
        (root / "configs").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "f").write_text("x")
    return write_profile(root, configs_dir="configs", custom_tools=[
        tool("dots", configs=[{"source": source, "target": target}])], **extra)


def config_problems(spec):
    resolved = profile.resolve(str(spec), catalog=SMALL_CATALOG)
    with pytest.raises(ManifestError) as e:
        Registry(data=resolved.manifest, configs_roots=resolved.configs_roots, sensitive_ok=resolved.sensitive_ok)
    return {p.code for p in e.value.problems}


@pytest.mark.parametrize("source, target, code", [
    ("~/../etc/passwd", "f", "invalid_config_source"),
    ("/etc/hosts", "f", "invalid_config_source"),
    ("~/.ssh/config", "f", "sensitive_config"),
    ("~/.zshrc", "../f", "invalid_config_target"),
    ("~/.zshrc", "/abs/f", "invalid_config_target"),
    ("~/.zshrc", "missing", "missing_config_file"),
])
def test_config_paths_are_checked(tmp_path, source, target, code):
    assert code in config_problems(config_profile(tmp_path / "p", source, target))


def test_symlink_out_of_home_is_rejected(tmp_path, isolated):
    os.symlink("/tmp", isolated / "escape")
    assert "config_outside_home" in config_problems(config_profile(tmp_path / "p", "~/escape/x"))


def test_sensitive_ok_allows_a_listed_location(tmp_path):
    p = config_profile(tmp_path / "p", "~/.gnupg/gpg-agent.conf", sensitive_ok=["~/.gnupg/gpg-agent.conf"])
    resolved = profile.resolve(str(p), catalog=SMALL_CATALOG)
    registry = Registry(data=resolved.manifest, configs_roots=resolved.configs_roots, sensitive_ok=resolved.sensitive_ok)
    assert registry.get("dots").configs_root == (tmp_path / "p" / "configs").resolve()


# ─── The shipped catalog and starters stay neutral ────────────


def test_shipped_starters_are_valid_and_use_only_catalog_tools():
    catalog_ids = {t["id"] for t in CATALOG["tools"]}
    starters = profile.starters()
    assert {s.name for s in starters} == {"minimal", "web", "backend", "mobile"}
    for starter in starters:
        Registry.for_profile(starter.name)
        tools = starter.data.get("tools", {})
        assert set(tools.get("add", []) + tools.get("remove", [])) <= catalog_ids, starter.name
        assert not starter.data.get("custom_tools") and not starter.data.get("configs_dir"), starter.name
        assert not starter.data.get("macos_defaults", {}).get("enabled"), starter.name


def test_catalog_ships_no_dotfiles():
    assert [t["id"] for t in CATALOG["tools"] if t.get("configs")] == []


def test_resources_hold_no_personal_data():
    assert not (RESOURCES / "configs").exists(), "dotfiles belong in a profile, not in Resources"
    scanned = [p for p in RESOURCES.rglob("*") if p.is_file()
               and p.suffix in {".json", ".plist", ".entitlements", ".md", ".txt"}]
    assert scanned
    for path in scanned:
        text = path.read_text()
        assert "/Users/" not in text, path
        assert "Desktop/Scripts" not in text, path
        emails = set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b", text)) - {"hey@v0id.me"}
        assert not emails, (path, emails)
