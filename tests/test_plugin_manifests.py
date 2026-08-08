"""Generic manifest guards for a marketplace that ships multiple isolated plugins."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def plugin_manifests() -> list[Path]:
    return sorted([ROOT / ".claude-plugin" / "plugin.json", *ROOT.glob("plugins/*/.claude-plugin/plugin.json")])


def test_every_plugin_manifest_has_portable_metadata():
    manifests = plugin_manifests()
    assert len(manifests) >= 2, "marketplace should exercise multi-plugin discovery"
    names = set()
    for path in manifests:
        data = json.loads(path.read_text())
        expected_name = "devenv" if path.parent.parent == ROOT else path.parent.parent.name
        assert data["name"] == expected_name
        assert data["name"] not in names
        names.add(data["name"])
        assert data.get("description", "").strip()
        assert SEMVER_RE.fullmatch(data.get("version", ""))
        assert data.get("author", {}).get("name", "").strip()


def test_marketplace_entries_resolve_to_unique_plugin_manifests():
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    entries = marketplace["plugins"]
    assert {entry["name"] for entry in entries} == {"devenv", "digital-twin"}
    assert len({entry["name"] for entry in entries}) == len(entries)
    for entry in entries:
        source = entry["source"]
        assert isinstance(source, str) and (source == "./" or source.startswith("./plugins/"))
        plugin_root = (ROOT / source).resolve()
        manifest = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text())
        assert manifest["name"] == entry["name"]


def test_nested_plugins_are_self_contained():
    for plugin in sorted((ROOT / "plugins").iterdir()):
        if not plugin.is_dir():
            continue
        for python_file in plugin.rglob("*.py"):
            source = python_file.read_text()
            assert "from lib.devenv_common" not in source
            assert "from skills." not in source


def test_digital_twin_plugin_contains_no_workspace_or_portfolio_specific_paths():
    plugin = ROOT / "plugins" / "digital-twin"
    forbidden = (
        "/Users/",
        "/home/",
        "C:\\Users\\",
        "john-plantada-portfolio",
        "claude-skills-digital-twin",
        "DIGITAL_TWIN_BUILDER_HANDOFF",
    )
    for path in plugin.rglob("*"):
        if not path.is_file() or path.suffix in {".pyc", ".png"}:
            continue
        text = path.read_text(errors="ignore")
        assert all(marker not in text for marker in forbidden), f"non-portable marker in {path.relative_to(ROOT)}"
