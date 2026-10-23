import json
from pathlib import Path

import pytest

from setmac.registry import Registry

MANIFEST = Path(__file__).parents[2] / "Resources" / "tools.json"
METHODS = {"brew_formula", "brew_cask", "mise", "mas", "defaults", "script", "custom", "config"}
# Methods whose installed check comes from the method itself, not check.command/path.
SELF_CHECKING = {"brew_formula", "brew_cask", "mise", "mas", "defaults"}


def write_manifest(tmp_path, tools):
    path = tmp_path / "tools.json"
    path.write_text(json.dumps({"version": "1", "tools": tools}))
    return path


def tool(tid, deps=(), **install):
    return {
        "id": tid,
        "name": tid,
        "depends_on": list(deps),
        "install": install or {"method": "script", "script": "true"},
    }


def test_shipped_manifest_is_valid():
    registry = Registry(MANIFEST)
    assert registry.problems() == []
    for t in registry.tools:
        assert t.install.method in METHODS, t.id
        if t.install.method in ("brew_formula", "brew_cask", "mise", "mas"):
            assert t.install.target, t.id
        if t.install.method == "defaults":
            assert t.defaults, t.id
        if t.install.method in ("script", "custom"):
            assert t.install.script or t.install.url, t.id
        assert t.check.command or t.check.path or t.install.method in SELF_CHECKING, t.id


def test_shipped_manifest_orders_essentials_first():
    order = [t.id for t in Registry(MANIFEST).install_order()]
    assert order.index("xcode-clt") < order.index("homebrew") < order.index("git")


def test_install_order_puts_dependencies_first(tmp_path):
    path = write_manifest(tmp_path, [tool("c", ["b"]), tool("b", ["a"]), tool("a")])
    registry = Registry(path)
    assert [t.id for t in registry.install_order(["c"])] == ["a", "b", "c"]


@pytest.mark.parametrize(
    "tools, message",
    [
        ([tool("a"), tool("a")], "duplicate tool id 'a'"),
        ([tool("a", ["missing"])], "unknown tool 'missing'"),
        ([tool("a", ["b"]), tool("b", ["a"])], "dependency cycle among: a, b"),
    ],
)
def test_invalid_manifests_are_rejected(tmp_path, tools, message):
    with pytest.raises(ValueError, match=message):
        Registry(write_manifest(tmp_path, tools))
