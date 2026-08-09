#!/usr/bin/env python3
"""Compile a validated private career-twin snapshot from current approved records.

The compiler never reads raw sources or transcripts and never approves candidates. It writes a
content-addressed snapshot and atomically advances the private current-state pointer.

Exit codes: 0 = compiled/current no-op, 1 = bundle findings, 2 = usage or filesystem failure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import validate_bundle as validator
from _bundle_common import (
    CURRENT_STATE_FILE,
    POLICY_VERSION,
    REVIEW_LOG_FILE,
    SCHEMA_VERSION,
    VALIDATION_FILES,
    chmod_private,
    digest_json,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def governed_bundle_digest(documents: dict[str, Any]) -> str:
    """Digest factual/review state without the mutable serving pointer."""
    included = {
        name: documents.get(name) for name in (*VALIDATION_FILES, REVIEW_LOG_FILE) if name != CURRENT_STATE_FILE
    }
    return digest_json(included)


def private_records(documents: dict[str, Any]) -> dict[str, Any]:
    """Create the minimal owner-only serving record set from validated active records."""
    claims = {
        claim["claim_id"]: claim
        for claim in documents["candidates/claims.json"]["claims"]
        if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str)
    }
    records = []
    for approved in documents["publication/approved-records.json"]["records"]:
        if not isinstance(approved, dict) or approved.get("state") != "active":
            continue
        claim = claims.get(approved.get("claim_id"), {})
        provenance = [
            {
                "source_occurrence_id": edge.get("source_occurrence_id"),
                "coordinate": edge.get("coordinate"),
                "source_role": edge.get("source_role"),
            }
            for edge in claim.get("evidence_edges", [])
            if isinstance(edge, dict) and edge.get("status") == "active" and edge.get("support") == "supports"
        ]
        records.append(
            {
                "record_id": approved["record_id"],
                "claim_id": approved["claim_id"],
                "claim_revision": approved["claim_revision"],
                "wording": approved["wording"],
                "category": claim.get("category"),
                "dates": claim.get("dates", []),
                "entities": claim.get("entities", []),
                "uncertainty": claim.get("uncertainty", []),
                "evidence_strength": approved["evidence_strength"],
                "visibility": approved["visibility"],
                "approval_digest": approved["approval_digest"],
                "provenance": provenance,
            }
        )
    records.sort(key=lambda item: item["record_id"])
    return {
        "schema": "digital-twin/private-snapshot-records",
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "records": records,
    }


def atomic_json(path: Path, value: Any) -> None:
    """Write canonical formatted JSON through a restrictive temporary sibling."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    chmod_private(path.parent, 0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        chmod_private(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def compile_snapshot(workspace: Path) -> tuple[dict[str, Any] | None, list[validator.Issue], str | None]:
    """Validate, compile, and activate one content-addressed private snapshot."""
    documents, load_issues, fatal = validator.load_bundle(workspace)
    if fatal:
        return None, [], fatal
    issues = validator.sorted_issues([*load_issues, *validator.validate_documents(documents)])
    if issues:
        return None, issues, None

    records = private_records(documents)
    records_digest = digest_json(records)
    snapshot_id = "snapshot-" + records_digest.split(":", 1)[1][:24]
    state = dict(documents[CURRENT_STATE_FILE])
    parent_snapshot_id = state.get("current_private_snapshot_id", "")
    snapshot_dir = workspace / "snapshots" / snapshot_id
    manifest_path = snapshot_dir / "snapshot-manifest.json"
    records_path = snapshot_dir / "records.json"

    if snapshot_dir.exists():
        try:
            existing_records = json.loads(records_path.read_text(encoding="utf-8"))
            existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return None, [], f"error\tunreadable existing snapshot\t{type(exc).__name__}"
        if digest_json(existing_records) != records_digest or existing_manifest.get("snapshot_id") != snapshot_id:
            return None, [], "error\tsnapshot ID collision or corrupted existing snapshot"
        created_at = existing_manifest.get("created_at", "")
    else:
        created_at = utc_now()
        snapshot_dir.mkdir(mode=0o700, parents=False)
        chmod_private(snapshot_dir, 0o700)
        atomic_json(records_path, records)
        manifest = {
            "schema": "digital-twin/private-snapshot-manifest",
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "snapshot_id": snapshot_id,
            "parent_snapshot_id": parent_snapshot_id,
            "created_at": created_at,
            "source_bundle_digest": governed_bundle_digest(documents),
            "records_digest": records_digest,
            "record_ids": [record["record_id"] for record in records["records"]],
            "state": "current",
        }
        atomic_json(manifest_path, manifest)

    pointer_changed = parent_snapshot_id != snapshot_id or state.get("serving_state") != "ready"
    if pointer_changed:
        state.update(
            {
                "workspace_revision": int(state.get("workspace_revision", 0)) + 1,
                "current_private_snapshot_id": snapshot_id,
                "serving_state": "ready",
                "pending_update_id": "",
                "blocked_record_ids": [],
            }
        )
        atomic_json(workspace / CURRENT_STATE_FILE, state)

    result = {
        "status": "compiled" if pointer_changed else "current",
        "snapshot_id": snapshot_id,
        "record_count": len(records["records"]),
        "records_digest": records_digest,
        "created_at": created_at,
    }
    return result, [], None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile and activate a validated private twin snapshot.")
    parser.add_argument("workspace", help="explicit digital-twin workspace path")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="stable report format")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path(os.path.abspath(os.path.expanduser(args.workspace)))
    if not workspace.is_dir():
        print(f"error\tworkspace directory does not exist\t{workspace}", file=sys.stderr)
        return 2
    result, issues, fatal = compile_snapshot(workspace)
    if fatal:
        print(fatal, file=sys.stderr)
        return 2
    if issues:
        print(validator.report_json(issues) if args.format == "json" else validator.report_text(issues))
        return 1
    assert result is not None
    if args.format == "json":
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print(
            f"{result['status']}\t{result['snapshot_id']}\t"
            f"{result['record_count']} approved records\t{result['records_digest']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
