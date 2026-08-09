#!/usr/bin/env python3
"""Explicitly migrate a digital-twin workspace from schema 0.1.0 to 0.2.0.

Migration preserves candidate and source content but conservatively invalidates approvals and
publication because their policy-bound digests predate snapshot and maintenance controls.

Exit codes: 0 = migrated/current no-op, 1 = refused unsupported state, 2 = usage/filesystem failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import update_bundle as updater
from _bundle_common import (
    CURRENT_STATE_FILE,
    EMPTY_FILES,
    POLICY_VERSION,
    REVIEW_LOG_FILE,
    SCHEMA_VERSION,
    TEMPLATE_FILES,
    WORKSPACE_DIRECTORIES,
    chmod_private,
)

FROM_VERSION = "0.1.0"


class MigrationRefusal(Exception):
    """A safe fixed-message migration refusal."""


def load_document(workspace: Path, relative: str) -> dict[str, Any]:
    path = workspace / relative
    if not path.is_file():
        raise MigrationRefusal("required legacy document is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationRefusal("legacy structured document is unreadable") from exc
    if not isinstance(value, dict):
        raise MigrationRefusal("legacy structured document must be an object")
    return value


def migrate_documents(workspace: Path, migrated_at: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    relatives = [relative for relative in TEMPLATE_FILES if relative != CURRENT_STATE_FILE]
    documents = {relative: load_document(workspace, relative) for relative in relatives}
    versions = {document.get("schema_version") for document in documents.values()}
    if versions == {SCHEMA_VERSION}:
        return documents, []
    if not versions <= {FROM_VERSION, SCHEMA_VERSION}:
        raise MigrationRefusal("workspace schema version is not supported by this migration")

    for document in documents.values():
        document["schema_version"] = SCHEMA_VERSION
        if "policy_version" in document:
            document["policy_version"] = POLICY_VERSION

    sources = documents["sources/source-manifest.json"].get("sources", [])
    for source in sources:
        if not isinstance(source, dict):
            continue
        source.setdefault("supersedes_occurrence_id", "")
        source.setdefault("observed_at", migrated_at)

    decisions = []
    claims = documents["candidates/claims.json"].get("claims", [])
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("review_state") != "approved":
            continue
        claim["review_state"] = "pending"
        claim["approval"] = None
        decision_seed = f"migration:{claim.get('claim_id', '')}:{claim.get('revision', '')}"
        decisions.append(
            {
                "decision_id": "decision-" + hashlib.sha256(decision_seed.encode()).hexdigest()[:24],
                "claim_id": claim.get("claim_id", ""),
                "claim_revision": claim.get("revision", 0),
                "action": "defer",
                "evidence_graph_digest": "",
                "decided_at": migrated_at,
            }
        )
    for record in documents["publication/approved-records.json"].get("records", []):
        if isinstance(record, dict) and record.get("state") == "active":
            record["state"] = "stale"
    publication = documents["publication/publication-manifest.json"]
    publication_changed = False
    for record in publication.get("records", []):
        if isinstance(record, dict) and record.get("state") != "retracted":
            record["state"] = "retracted"
            publication_changed = True
    if publication_changed:
        publication["owner_review_state"] = "retracted"
    for evaluation in documents["evals/private-evals.json"].get("evaluations", []):
        if isinstance(evaluation, dict) and evaluation.get("review_state") == "approved":
            evaluation["review_state"] = "draft"
            evaluation["stale_reason"] = "schema_policy_migration"
    return documents, decisions


def existing_decision_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    identifiers = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict) and isinstance(value.get("decision_id"), str):
                    identifiers.add(value["decision_id"])
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationRefusal("legacy review log is unreadable") from exc
    return identifiers


def migrate_workspace(workspace: Path) -> dict[str, Any]:
    state_path = workspace / CURRENT_STATE_FILE
    if state_path.is_file():
        state = load_document(workspace, CURRENT_STATE_FILE)
        if state.get("schema_version") == SCHEMA_VERSION:
            return {"status": "current", "schema_version": SCHEMA_VERSION, "invalidated_approvals": 0}
        if state.get("schema_version") not in {FROM_VERSION, None}:
            raise MigrationRefusal("current-state schema version is unsupported")

    migrated_at = updater.utc_now()
    documents, decisions = migrate_documents(workspace, migrated_at)
    for relative in WORKSPACE_DIRECTORIES:
        directory = workspace / relative
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        chmod_private(directory, 0o700)
    for relative in EMPTY_FILES:
        path = workspace / relative
        if not path.exists():
            path.touch(mode=0o600)
            chmod_private(path, 0o600)
    for relative, document in documents.items():
        updater.atomic_json(workspace / relative, document)

    seen = existing_decision_ids(workspace / REVIEW_LOG_FILE)
    updater.append_jsonl(
        workspace / REVIEW_LOG_FILE,
        [decision for decision in decisions if decision["decision_id"] not in seen],
    )
    state = {
        "schema": "digital-twin/current-state",
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "workspace_revision": 1,
        "current_private_snapshot_id": "",
        "serving_state": "uncompiled",
        "pending_update_id": "",
        "blocked_record_ids": [],
    }
    updater.atomic_json(state_path, state)
    return {
        "status": "migrated",
        "from_schema_version": FROM_VERSION,
        "schema_version": SCHEMA_VERSION,
        "invalidated_approvals": len(decisions),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Explicitly migrate a private twin workspace to schema 0.2.0.")
    parser.add_argument("workspace", help="explicit private workspace path")
    parser.add_argument("--confirm", action="store_true", help="confirm migration and approval invalidation")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="safe report format")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.confirm:
        print("refused\tmigration requires --confirm", file=sys.stderr)
        return 2
    workspace = Path(os.path.abspath(os.path.expanduser(args.workspace)))
    if not workspace.is_dir():
        print(f"error\tworkspace directory does not exist\t{workspace}", file=sys.stderr)
        return 2
    try:
        report = migrate_workspace(workspace)
    except MigrationRefusal as exc:
        print(f"refused\t{exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error\tmigration failed\t{type(exc).__name__}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print("\t".join(f"{key}={value}" for key, value in report.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
