"""Guards for the user-facing digital-twin architecture proposal."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "digital-twin"
ARCHITECTURE = PLUGIN / "docs" / "design-and-architecture.md"


def test_architecture_document_is_linked_and_visually_explains_the_system():
    text = ARCHITECTURE.read_text()
    plugin_readme = (PLUGIN / "README.md").read_text()

    assert "docs/design-and-architecture.md" in plugin_readme
    assert text.count("```mermaid") >= 5
    for diagram in ("flowchart", "erDiagram", "stateDiagram-v2", "sequenceDiagram"):
        assert diagram in text


def test_architecture_document_distinguishes_current_state_from_proposal():
    text = ARCHITECTURE.read_text()

    assert "**Status:** Proposed" in text
    assert "## Current versus proposed capability" in text
    assert "Plan/apply transaction | Not implemented" in text
    assert "current-snapshot pointer changes only after complete validation" in text
