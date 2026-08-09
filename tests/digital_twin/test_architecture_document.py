"""Guards for the user-facing digital-twin architecture proposal."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "digital-twin"
ARCHITECTURE = PLUGIN / "docs" / "design-and-architecture.md"
SERVING = PLUGIN / "docs" / "serving-and-feedback.md"


def test_architecture_document_is_linked_and_visually_explains_the_system():
    text = ARCHITECTURE.read_text()
    plugin_readme = (PLUGIN / "README.md").read_text()

    assert "docs/design-and-architecture.md" in plugin_readme
    assert "docs/serving-and-feedback.md" in plugin_readme
    assert text.count("```mermaid") >= 5
    for diagram in ("flowchart", "erDiagram", "stateDiagram-v2", "sequenceDiagram"):
        assert diagram in text


def test_architecture_document_distinguishes_current_state_from_proposal():
    text = ARCHITECTURE.read_text()

    assert "| Status | Proposed |" in text
    assert "## Current versus proposed capability" in text
    assert "Plan/apply transaction | Not implemented" in text
    assert "current-snapshot pointer changes only after complete validation" in text


def test_serving_document_separates_private_assistant_from_public_chat():
    text = SERVING.read_text()
    architecture = ARCHITECTURE.read_text()

    assert text.count("```mermaid") >= 5
    assert "serving-and-feedback.md" in architecture
    assert "Private career assistant" in text
    assert "Public website chat" in text
    assert "The public runtime must have no network route" in text
    assert "Visitor feedback" in text
    assert "Before public website launch" in text
