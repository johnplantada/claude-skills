"""Deterministic packaging and contract checks for the architecture-review plugin."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "architecture-review"
SKILL = PLUGIN / "skills" / "review-architecture-plan"
SKILL_MD = SKILL / "SKILL.md"
METHOD = SKILL / "references" / "review-method.md"
REPORT = SKILL / "references" / "report-template.md"
EVALS = SKILL / "evals" / "evals.json"
MAX_DESCRIPTION = 1400

_MD_LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?://|#|mailto:)([^)]+)\)")
_LOCAL_ABSOLUTE_PATH_RE = re.compile(r"(?:/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\\\Users\\\\[^\\\s]+)")


def _frontmatter() -> dict:
    text = SKILL_MD.read_text()
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    parts = text.split("---", 2)
    assert len(parts) == 3, "SKILL.md frontmatter must have opening and closing fences"
    data = yaml.safe_load(parts[1])
    assert isinstance(data, dict), "SKILL.md frontmatter must parse to a mapping"
    return data


def test_skill_frontmatter_is_valid_and_minimal():
    data = _frontmatter()
    assert set(data) == {"name", "description"}
    assert data["name"] == SKILL.name
    assert isinstance(data["description"], str) and data["description"].strip()


def test_description_stays_within_budget_and_defines_boundaries():
    description = _frontmatter()["description"]
    assert len(description) <= MAX_DESCRIPTION
    for trigger in ("architecture plans", "system-design proposals", "ADRs", "implementation readiness"):
        assert trigger in description
    for near_miss in ("code-diff review", "proofreading", "implementation-only", "from scratch"):
        assert near_miss in description


def test_skill_is_concise_and_uses_progressive_disclosure():
    text = SKILL_MD.read_text()
    assert len(text.splitlines()) < 500
    assert "references/review-method.md" in text
    assert "references/report-template.md" in text


def test_all_relative_markdown_links_in_plugin_resolve():
    broken = []
    for document in sorted(PLUGIN.rglob("*.md")):
        for target in _MD_LINK_RE.findall(document.read_text()):
            relative_target = target.split("#", 1)[0]
            if relative_target and not (document.parent / relative_target).resolve().exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not broken, "broken relative links:\n  " + "\n  ".join(broken)


def test_plugin_and_marketplace_manifests_are_valid_and_isolated():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == PLUGIN.name
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert manifest["description"].strip()
    assert manifest["author"]["name"].strip()

    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert marketplace["name"] == "devenv-marketplace"
    assert "plugins" in marketplace["metadata"]["description"].lower()
    entries = marketplace["plugins"]
    assert len({entry["name"] for entry in entries}) == len(entries)
    by_name = {entry["name"]: entry for entry in entries}
    assert by_name["devenv"]["source"] == "./"
    assert by_name["architecture-review"]["source"] == "./plugins/architecture-review"
    assert (ROOT / by_name["architecture-review"]["source"]).resolve() == PLUGIN.resolve()
    assert (PLUGIN / ".claude-plugin" / "plugin.json").is_file()
    assert not (ROOT / "skills" / "review-architecture-plan").exists()


def test_report_template_has_the_required_sections_and_finding_fields():
    text = REPORT.read_text()
    sections = [
        "# Verdict",
        "# What is strong",
        "# Blocking findings",
        "# Important improvements",
        "# Required invariants and decisions",
        "# Recommended rollout",
        "# Verification performed",
        "# Recommended next action",
    ]
    positions = [text.index(section) for section in sections]
    assert positions == sorted(positions)
    for verdict in ("Ready", "Ready with required changes", "Not ready"):
        assert verdict in text
    for field in ("Priority", "Evidence", "Consequence", "Required resolution"):
        assert f"**{field}:**" in text


def test_review_method_covers_the_required_architecture_dimensions():
    text = METHOD.read_text().lower()
    required_concepts = (
        "functional and non-functional requirements",
        "canonical contracts and sources of truth",
        "trust and authorization boundaries",
        "provenance and evidence integrity",
        "privacy and information lifecycle",
        "lifecycle and failure behavior",
        "storage and data-model fitness",
        "api and service boundaries",
        "observability and sensitive logging",
        "operating limits",
        "testing and release gates",
        "implementation phases",
        "alternatives and trade-offs",
    )
    for concept in required_concepts:
        assert concept in text


def test_evals_cover_behavior_and_near_miss_triggers():
    data = json.loads(EVALS.read_text())
    assert data["skill_name"] == SKILL.name
    assert len(data["evals"]) >= 3
    required_assertion_fragments = (
        "readiness verdict",
        "fixture paths",
        "separated from important improvements",
        "invariant includes acceptance evidence",
        "requirements are exposed",
        "vertical slice",
        "no fixture file is created, edited, or deleted",
    )
    for case in data["evals"]:
        assertions = "\n".join(case["assertions"]).lower()
        for fragment in required_assertion_fragments:
            assert fragment in assertions, f"{case['eval_name']} lacks assertion: {fragment}"
        assert case["files"], f"{case['eval_name']} has no synthetic fixture"

    near_misses = {case["category"]: case for case in data["trigger_cases"] if not case["should_trigger"]}
    assert set(near_misses) == {
        "code-diff-review",
        "proofreading",
        "approved-plan-implementation",
        "plan-generation",
    }


def test_plugin_is_general_purpose_and_contains_no_local_project_paths():
    plugin_text = "\n".join(
        path.read_text() for path in sorted(PLUGIN.rglob("*")) if path.is_file() and path.suffix in {".json", ".md"}
    )
    assert not _LOCAL_ABSOLUTE_PATH_RE.search(plugin_text)
    blocked_project_name = "-".join(("john", "plantada", "portfolio"))
    assert blocked_project_name not in plugin_text.lower()
    assert "portfolio" not in plugin_text.lower()
