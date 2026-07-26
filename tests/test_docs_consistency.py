"""Docs ↔ scripts consistency — the guard against silent doc drift.

In a skills repo the markdown IS the program: SKILL.md and reference/*.md tell the
agent which scripts to run and how. A script rename, a removed flag, or a changed
behavior that the docs still describe ships green unless something reads the docs.
These tests do:

  1. every `scripts/<name>.py` a skill's docs mention exists in that skill,
  2. every public (non-underscore) script a skill ships is mentioned in its docs,
  3. every `--flag` written next to a script reference exists in that script's source,
  4. the hook command in hooks.json points at a real file.

Pure filesystem reads — no subprocesses, safe everywhere.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())

# A doc reference to a skill script: `scripts/<name>.py` (optionally prefixed with a path).
_SCRIPT_REF_RE = re.compile(r"scripts/([A-Za-z0-9_]+\.py)")
# Flags written in the same backtick span as a script reference.
_CODE_SPAN_RE = re.compile(r"`([^`]*scripts/[A-Za-z0-9_]+\.py[^`]*)`")
_FLAG_RE = re.compile(r"--[a-z][a-z-]*")

# Flags that are placeholders/examples, not literal script flags.
_FLAG_ALLOWLIST = {"--help"}


def _skill_docs(skill: Path) -> list[Path]:
    docs = [skill / "SKILL.md", skill / "README.md"]
    docs += sorted((skill / "reference").glob("*.md")) if (skill / "reference").is_dir() else []
    return [d for d in docs if d.is_file()]


def _doc_text(skill: Path) -> str:
    return "\n".join(d.read_text() for d in _skill_docs(skill))


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_every_script_reference_in_docs_exists(skill: Path):
    """Same-skill references must resolve locally; cross-skill runbooks (the devenv
    capstone) may point at a sibling skill's scripts, and plugin-level hooks live in
    the repo-root scripts/ — but the file must exist SOMEWHERE. This is the guard that
    catches a doc still using a renamed script's old name."""
    text = _doc_text(skill)
    scripts_dir = skill / "scripts"
    missing = {
        name for name in _SCRIPT_REF_RE.findall(text)
        if not (scripts_dir / name).is_file()
        and not (ROOT / "scripts" / name).is_file()
        and not any((other / "scripts" / name).is_file() for other in SKILLS)
    }
    assert not missing, f"{skill.name} docs reference scripts that don't exist: {sorted(missing)}"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_every_public_script_is_documented(skill: Path):
    scripts_dir = skill / "scripts"
    if not scripts_dir.is_dir():
        pytest.skip(f"{skill.name} ships no scripts")
    text = _doc_text(skill)
    undocumented = {
        p.name for p in scripts_dir.glob("*.py")
        if not p.name.startswith("_") and p.name not in text
    }
    assert not undocumented, f"{skill.name} ships scripts its docs never mention: {sorted(undocumented)}"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_flags_shown_next_to_a_script_exist_in_its_source(skill: Path):
    scripts_dir = skill / "scripts"
    if not scripts_dir.is_dir():
        pytest.skip(f"{skill.name} ships no scripts")
    stale: list[str] = []
    for doc in _skill_docs(skill):
        for span in _CODE_SPAN_RE.findall(doc.read_text()):
            m = _SCRIPT_REF_RE.search(span)
            script = scripts_dir / m.group(1) if m else None
            if script is None or not script.is_file():
                continue  # covered by test_every_script_reference_in_docs_exists
            source = script.read_text()
            for flag in _FLAG_RE.findall(span):
                if flag not in _FLAG_ALLOWLIST and flag not in source:
                    stale.append(f"{doc.relative_to(ROOT)}: {m.group(1)} has no {flag}")
    assert not stale, "docs show flags the script doesn't define:\n" + "\n".join(stale)


def test_plugin_and_project_versions_agree():
    """The two version strings must move together.

    Found by a live health sweep: the whole bash->Python migration shipped without a
    version bump, so an installed plugin cache at 0.1.0 had entirely different content
    than the 0.1.0 working tree — and no reason to ever refresh. A version is the only
    signal a consumer has that the content changed; a stale one silently serves docs
    that reference scripts which no longer exist.
    """
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    pyproject = re.search(
        r'^version\s*=\s*"([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.MULTILINE
    )
    assert pyproject, "pyproject.toml has no version"
    assert plugin == pyproject.group(1), (
        f"version mismatch: plugin.json={plugin} pyproject.toml={pyproject.group(1)} — "
        "bump both when shipping"
    )


def test_hook_command_points_at_a_real_file():
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text())
    commands = [
        h["command"]
        for group in hooks["hooks"].values()
        for entry in group
        for h in entry["hooks"]
        if h.get("type") == "command"
    ]
    assert commands, "hooks.json defines no command hooks"
    for cmd in commands:
        # e.g. "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/chezmoi_drift_check.py"
        path = cmd.split("${CLAUDE_PLUGIN_ROOT}/", 1)[-1]
        assert (ROOT / path).is_file(), f"hook command references a missing file: {cmd}"
