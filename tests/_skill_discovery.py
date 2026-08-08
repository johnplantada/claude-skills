"""Repository-wide skill discovery for root and isolated nested plugins."""

from pathlib import Path


def skill_directories(root: Path) -> list[Path]:
    patterns = ("skills/*/SKILL.md", "plugins/*/skills/*/SKILL.md")
    return sorted({skill_md.parent for pattern in patterns for skill_md in root.glob(pattern)})


def reference_markdown(skill: Path) -> list[Path]:
    docs: list[Path] = []
    for dirname in ("reference", "references"):
        directory = skill / dirname
        if directory.is_dir():
            docs.extend(sorted(directory.glob("*.md")))
    return docs
