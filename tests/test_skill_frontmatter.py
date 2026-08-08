"""SKILL.md structure — the guard over the files that ARE the product.

The 13 SKILL.md files are what this repo ships, and until this suite existed nothing
read them. `./check` tested Python and script references; `claude plugin validate
--strict` checks the plugin MANIFEST, not skills. Deleting the `name:` field from a
shipped skill passed both.

That gap was not hypothetical: four skills had frontmatter that no strict YAML parser
could read, because a `": "` inside an unquoted description makes YAML treat the rest as
a nested mapping. Claude Code's own parser was lenient enough to load them, so they
worked here and failed everywhere else — the worst kind of bug for a published repo.

What is asserted, and why each one earns its place:

  1. frontmatter parses as YAML — the bug above, catchable no other way,
  2. `name` and `description` exist and are non-empty — a skill missing either is
     silently unreachable rather than loudly broken,
  3. `description` stays within budget — it is the ONLY always-on text, paid for in
     every session whether or not the skill is used,
  4. `allowed-tools` is a string when present — a list silently changes its meaning,
  5. relative markdown links resolve — the routing between SKILL.md and reference/ IS
     the progressive-disclosure design; a dead link breaks the workflow, and the
     script-reference guard in test_docs_consistency.py does not cover markdown links.

Pure filesystem reads — no subprocesses, safe everywhere.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from _skill_discovery import reference_markdown, skill_directories

ROOT = Path(__file__).resolve().parent.parent
SKILLS = skill_directories(ROOT)

# Descriptions are always-on context. The longest shipped one sits near 1000 chars; the
# cap is a ceiling that catches runaway growth, not a target to write against.
MAX_DESCRIPTION = 1400

# `[text](target)` where target is not a URL, an anchor, or a mail link.
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?://|#|mailto:)([^)]+)\)")


def frontmatter(skill: Path) -> str:
    """The raw YAML block between the leading `---` fences ('' if absent)."""
    text = (skill / "SKILL.md").read_text()
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def parsed(skill: Path) -> dict:
    """Frontmatter as a dict. Raises if the YAML is invalid — which is the point."""
    data = yaml.safe_load(frontmatter(skill))
    return data if isinstance(data, dict) else {}


def markdown_files(skill: Path) -> list[Path]:
    docs = [skill / "SKILL.md", skill / "README.md"]
    docs += reference_markdown(skill)
    return [d for d in docs if d.is_file()]


# --- frontmatter ---------------------------------------------------------------


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_skill_md_exists(skill: Path):
    assert (skill / "SKILL.md").is_file(), f"{skill.name} has no SKILL.md"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_frontmatter_is_valid_yaml(skill: Path):
    """The regression: a `": "` in an unquoted description silently breaks every strict
    parser while Claude Code's lenient one still loads the skill."""
    raw = frontmatter(skill)
    assert raw.strip(), f"{skill.name}/SKILL.md has no --- frontmatter block"
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        problem = str(exc).split("\n")[0]
        pytest.fail(
            f"{skill.name}/SKILL.md frontmatter is not valid YAML: {problem}. "
            'A ": " inside an unquoted value is the usual cause — use " — " or quote the value.'
        )
    assert isinstance(data, dict), f"{skill.name} frontmatter parsed to {type(data).__name__}, not a mapping"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_name_and_description_are_present_and_non_empty(skill: Path):
    data = parsed(skill)
    for field in ("name", "description"):
        assert field in data, f"{skill.name} frontmatter has no '{field}' — the skill is silently unreachable"
        assert str(data[field]).strip(), f"{skill.name} has an empty '{field}'"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_description_stays_within_the_always_on_budget(skill: Path):
    description = str(parsed(skill).get("description", ""))
    assert len(description) <= MAX_DESCRIPTION, (
        f"{skill.name} description is {len(description)} chars (cap {MAX_DESCRIPTION}). "
        "It is loaded in every session whether or not the skill runs."
    )


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_allowed_tools_is_a_string_when_present(skill: Path):
    """A list here silently changes meaning; the field is a comma-separated string."""
    tools = parsed(skill).get("allowed-tools")
    if tools is not None:
        assert isinstance(tools, str), f"{skill.name} allowed-tools is {type(tools).__name__}, expected a string"


# --- the routing between SKILL.md and reference/ -------------------------------


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_relative_markdown_links_resolve(skill: Path):
    """Progressive disclosure IS these links; a dead one dead-ends the workflow.

    test_docs_consistency.py guards `scripts/*.py` references, so this covers the other
    half — and it is not theoretical: terminal-theme's SKILL.md linked `upgrade.md`
    when the file lives at `reference/upgrade.md`.
    """
    broken = []
    for doc in markdown_files(skill):
        for target in _MD_LINK_RE.findall(doc.read_text()):
            path = (doc.parent / target.split("#", 1)[0]).resolve()
            if not path.exists():
                broken.append(f"{doc.relative_to(ROOT)} -> {target}")
    assert not broken, "broken relative links:\n  " + "\n  ".join(broken)
