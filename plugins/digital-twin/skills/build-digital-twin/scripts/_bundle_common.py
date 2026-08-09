"""Shared, plugin-local bundle constants and deterministic serialization.

This module deliberately imports nothing from the repository's other plugin. Installed Claude
plugins are copied independently, so every runtime dependency must remain inside digital-twin.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.2.0"
POLICY_VERSION = "0.2.0"

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = SKILL_ROOT / "assets"

WORKSPACE_DIRECTORIES = (
    "sources",
    "interviews",
    "candidates",
    "reviews",
    "context",
    "context/projects",
    "context/decisions",
    "publication",
    "evals",
    "evals/reports",
    "feedback",
    "updates",
    "updates/plans",
    "updates/sessions",
    "snapshots",
    "state",
    "locks",
)

TEMPLATE_FILES = {
    "sources/source-manifest.json": "source-manifest.template.json",
    "candidates/claims.json": "claims.template.json",
    "candidates/conflicts.json": "conflicts.template.json",
    "candidates/coverage.json": "coverage.template.json",
    "publication/approved-records.json": "approved-records.template.json",
    "publication/publication-manifest.json": "publication-manifest.template.json",
    "evals/private-evals.json": "private-evals.template.json",
    "state/current.json": "current-state.template.json",
}

EMPTY_FILES = (
    "reviews/decisions.jsonl",
    "context/profile.md",
    "context/timeline.md",
    "context/principles.md",
    "context/voice.md",
    "context/boundaries.md",
    "context/faq.md",
    "feedback/owner-inbox.jsonl",
    "updates/events.jsonl",
)

VALIDATION_FILES = (
    "sources/source-manifest.json",
    "candidates/claims.json",
    "candidates/conflicts.json",
    "candidates/coverage.json",
    "publication/approved-records.json",
    "publication/publication-manifest.json",
    "evals/private-evals.json",
    "state/current.json",
)

REVIEW_LOG_FILE = "reviews/decisions.jsonl"
CURRENT_STATE_FILE = "state/current.json"


def canonical_json(value: Any) -> str:
    """Serialize digest-bound logical data without whitespace or platform variance."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_json(value: Any) -> str:
    """Return a prefixed SHA-256 digest for a canonical JSON value."""
    payload = canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def template_text(asset_name: str) -> str:
    """Read and parse a bundled starter template, returning its exact text."""
    text = (ASSET_ROOT / asset_name).read_text(encoding="utf-8")
    json.loads(text)
    return text


def expected_file_text() -> dict[str, str]:
    """All files in a pristine initialized workspace and their exact contents."""
    files = {target: template_text(asset) for target, asset in TEMPLATE_FILES.items()}
    files.update({target: "" for target in EMPTY_FILES})
    return files


def chmod_private(path: Path, mode: int) -> None:
    """Apply a restrictive POSIX mode; Windows has no equivalent permission model."""
    if os.name != "nt":
        path.chmod(mode)
