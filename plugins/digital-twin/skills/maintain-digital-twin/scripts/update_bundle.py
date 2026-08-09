#!/usr/bin/env python3
"""Plan, apply, and report owner-controlled source refreshes for a private twin.

Plans and reports are metadata-only. Apply blocks serving before invalidation, creates a new source
occurrence, marks dependencies stale, and waits for the normal owner review and snapshot compiler.

Exit codes: 0 = success/no-op, 1 = refused/stale/review required, 2 = usage/filesystem failure.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BUILD_SCRIPTS = Path(__file__).resolve().parents[2] / "build-digital-twin" / "scripts"
if str(BUILD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(BUILD_SCRIPTS))

import validate_bundle as validator  # noqa: E402
from _bundle_common import (  # noqa: E402
    CURRENT_STATE_FILE,
    POLICY_VERSION,
    REVIEW_LOG_FILE,
    SCHEMA_VERSION,
    chmod_private,
    digest_json,
)
from compile_private_snapshot import governed_bundle_digest  # noqa: E402

PLAN_SCHEMA = "digital-twin/update-plan"
SESSION_SCHEMA = "digital-twin/update-session"
EVENT_SCHEMA = "digital-twin/update-event"


class UpdateRefusal(Exception):
    """A safe, fixed-message transaction refusal."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    chmod_private(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        chmod_private(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def append_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    if not entries:
        return
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if os.name != "nt" and path.exists():
            path.chmod(0o600)


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateRefusal(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise UpdateRefusal(f"{label} must be a JSON object")
    return value


def load_valid_bundle(workspace: Path) -> dict[str, Any]:
    documents, load_issues, fatal = validator.load_bundle(workspace)
    if fatal:
        raise UpdateRefusal("bundle cannot be loaded safely")
    issues = validator.sorted_issues([*load_issues, *validator.validate_documents(documents)])
    if issues:
        raise UpdateRefusal("bundle has validation findings; resolve them before planning")
    return documents


def current_occurrence(sources: list[Any], source_id: str) -> dict[str, Any]:
    candidates = [source for source in sources if isinstance(source, dict) and source.get("source_id") == source_id]
    if not candidates:
        raise UpdateRefusal("logical source ID does not exist")
    superseded = {
        source.get("supersedes_occurrence_id")
        for source in candidates
        if isinstance(source.get("supersedes_occurrence_id"), str) and source.get("supersedes_occurrence_id")
    }
    leaves = [source for source in candidates if source.get("source_occurrence_id") not in superseded]
    if len(leaves) != 1:
        raise UpdateRefusal("logical source history has no unique current occurrence")
    return leaves[0]


def plan_digest(plan: dict[str, Any]) -> str:
    bound = {key: value for key, value in plan.items() if key != "plan_digest"}
    return digest_json(bound)


def safe_plan_report(plan: dict[str, Any]) -> dict[str, Any]:
    change = plan["source_changes"][0]
    return {
        "status": change["status"],
        "update_id": plan["update_id"],
        "base_snapshot_id": plan["base_snapshot_id"],
        "source_id": change["source_id"],
        "current_occurrence_id": change["current_occurrence_id"],
        "impacted_claim_count": len(plan["impacted_claim_ids"]),
        "impacted_record_count": len(plan["impacted_record_ids"]),
        "planned_actions": plan["planned_actions"],
        "plan_digest": plan["plan_digest"],
    }


def create_plan(workspace: Path, source_id: str, selected_file: Path) -> dict[str, Any]:
    documents = load_valid_bundle(workspace)
    if not selected_file.is_file() or selected_file.is_symlink():
        raise UpdateRefusal("selected source must be an explicit regular file")
    observed_hash = sha256_file(selected_file)
    occurrence = current_occurrence(documents["sources/source-manifest.json"]["sources"], source_id)
    current_id = occurrence["source_occurrence_id"]
    changed = occurrence.get("content_hash") != observed_hash
    claims = documents["candidates/claims.json"]["claims"]
    impacted_claim_ids = sorted(
        claim["claim_id"]
        for claim in claims
        if isinstance(claim, dict)
        and any(
            isinstance(edge, dict) and edge.get("source_occurrence_id") == current_id and edge.get("status") == "active"
            for edge in claim.get("evidence_edges", [])
        )
    )
    impacted_record_ids = sorted(
        record["record_id"]
        for record in documents["publication/approved-records.json"]["records"]
        if isinstance(record, dict) and record.get("claim_id") in impacted_claim_ids and record.get("state") == "active"
    )
    state = documents[CURRENT_STATE_FILE]
    seed = {
        "base_bundle_digest": governed_bundle_digest(documents),
        "base_snapshot_id": state.get("current_private_snapshot_id", ""),
        "base_workspace_revision": state.get("workspace_revision", 0),
        "source_id": source_id,
        "current_occurrence_id": current_id,
        "observed_hash": observed_hash,
    }
    update_id = "update-" + digest_json(seed).split(":", 1)[1][:24]
    plan = {
        "schema": PLAN_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "update_id": update_id,
        "created_at": utc_now(),
        "base_snapshot_id": state.get("current_private_snapshot_id", ""),
        "base_workspace_revision": state.get("workspace_revision", 0),
        "base_bundle_digest": seed["base_bundle_digest"],
        "trigger": "owner_selected_source_refresh",
        "source_file": str(selected_file.resolve()),
        "source_changes": [
            {
                "source_id": source_id,
                "current_occurrence_id": current_id,
                "previous_hash": occurrence.get("content_hash", ""),
                "observed_hash": observed_hash,
                "status": "changed" if changed else "unchanged",
            }
        ],
        "impacted_claim_ids": impacted_claim_ids if changed else [],
        "impacted_record_ids": impacted_record_ids if changed else [],
        "planned_actions": (
            ["create_source_occurrence", "invalidate_dependencies", "block_private_serving", "owner_delta_review"]
            if changed
            else []
        ),
        "plan_digest": "",
    }
    plan["plan_digest"] = plan_digest(plan)
    target = workspace / "updates" / "plans" / f"{update_id}.json"
    if target.exists():
        existing = read_json(target, "existing update plan")
        if existing.get("plan_digest") != plan["plan_digest"]:
            raise UpdateRefusal("existing update ID has a different digest")
        return existing
    atomic_json(target, plan)
    return plan


def acquire_lock(workspace: Path, update_id: str) -> tuple[int, Path]:
    path = workspace / "locks" / "update.lock"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise UpdateRefusal("another update holds the workspace lock") from exc
    os.write(descriptor, (update_id + "\n").encode())
    os.fsync(descriptor)
    return descriptor, path


def apply_plan(workspace: Path, update_id: str) -> dict[str, Any]:
    plan_path = workspace / "updates" / "plans" / f"{update_id}.json"
    plan = read_json(plan_path, "update plan")
    if plan.get("schema") != PLAN_SCHEMA or plan.get("update_id") != update_id:
        raise UpdateRefusal("update plan identity is invalid")
    if plan.get("plan_digest") != plan_digest(plan):
        raise UpdateRefusal("update plan digest does not match its contents")

    session_path = workspace / "updates" / "sessions" / f"{update_id}.json"
    if session_path.exists():
        session = read_json(session_path, "update session")
        if session.get("status") in {"completed", "awaiting_owner_review"}:
            return {
                "status": session["status"],
                "update_id": update_id,
                "new_occurrence_id": session.get("new_occurrence_id", ""),
                "invalidated_claim_count": session.get("invalidated_claim_count", 0),
                "invalidated_record_count": session.get("invalidated_record_count", 0),
            }

    descriptor, lock_path = acquire_lock(workspace, update_id)
    session: dict[str, Any] | None = None
    try:
        documents = load_valid_bundle(workspace)
        state = documents[CURRENT_STATE_FILE]
        if (
            state.get("workspace_revision") != plan.get("base_workspace_revision")
            or state.get("current_private_snapshot_id") != plan.get("base_snapshot_id")
            or governed_bundle_digest(documents) != plan.get("base_bundle_digest")
        ):
            raise UpdateRefusal("update plan is stale relative to the current workspace")
        selected_file = Path(str(plan.get("source_file", "")))
        change = plan["source_changes"][0]
        if (
            not selected_file.is_file()
            or selected_file.is_symlink()
            or sha256_file(selected_file) != change["observed_hash"]
        ):
            raise UpdateRefusal("selected source changed after planning")

        started_at = utc_now()
        session = {
            "schema": SESSION_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "policy_version": POLICY_VERSION,
            "update_id": update_id,
            "plan_digest": plan["plan_digest"],
            "status": "started",
            "started_at": started_at,
            "finished_at": "",
            "previous_occurrence_id": change["current_occurrence_id"],
            "new_occurrence_id": "",
            "invalidated_claim_count": 0,
            "invalidated_record_count": 0,
        }
        atomic_json(session_path, session)
        append_jsonl(
            workspace / "updates" / "events.jsonl",
            [{"schema": EVENT_SCHEMA, "update_id": update_id, "event": "started", "at": started_at}],
        )

        if change["status"] == "unchanged":
            session.update({"status": "completed", "finished_at": utc_now()})
            atomic_json(session_path, session)
            append_jsonl(
                workspace / "updates" / "events.jsonl",
                [
                    {
                        "schema": EVENT_SCHEMA,
                        "update_id": update_id,
                        "event": "completed_noop",
                        "at": session["finished_at"],
                    }
                ],
            )
            return {
                "status": "completed",
                "update_id": update_id,
                "new_occurrence_id": "",
                "invalidated_claim_count": 0,
                "invalidated_record_count": 0,
            }

        blocked_state = copy.deepcopy(state)
        blocked_state.update(
            {
                "workspace_revision": int(state["workspace_revision"]) + 1,
                "serving_state": "review_required",
                "pending_update_id": update_id,
                "blocked_record_ids": plan["impacted_record_ids"],
            }
        )
        atomic_json(workspace / CURRENT_STATE_FILE, blocked_state)

        sources_document = copy.deepcopy(documents["sources/source-manifest.json"])
        claims_document = copy.deepcopy(documents["candidates/claims.json"])
        approved_document = copy.deepcopy(documents["publication/approved-records.json"])
        publication_document = copy.deepcopy(documents["publication/publication-manifest.json"])
        evals_document = copy.deepcopy(documents["evals/private-evals.json"])
        previous = current_occurrence(sources_document["sources"], change["source_id"])
        occurrence_seed = f"{update_id}:{change['observed_hash']}"
        new_occurrence_id = "occ-" + hashlib.sha256(occurrence_seed.encode()).hexdigest()[:24]
        new_occurrence = copy.deepcopy(previous)
        new_occurrence.update(
            {
                "source_occurrence_id": new_occurrence_id,
                "supersedes_occurrence_id": previous["source_occurrence_id"],
                "observed_at": started_at,
                "content_hash": change["observed_hash"],
            }
        )
        sources_document["sources"].append(new_occurrence)

        impacted_claims = set(plan["impacted_claim_ids"])
        impacted_records = set(plan["impacted_record_ids"])
        decisions = []
        for claim in claims_document["claims"]:
            if not isinstance(claim, dict) or claim.get("claim_id") not in impacted_claims:
                continue
            for edge in claim.get("evidence_edges", []):
                if isinstance(edge, dict) and edge.get("source_occurrence_id") == change["current_occurrence_id"]:
                    edge["status"] = "stale"
            claim["review_state"] = "pending"
            claim["approval"] = None
            decisions.append(
                {
                    "decision_id": "decision-"
                    + hashlib.sha256(f"{update_id}:{claim['claim_id']}".encode()).hexdigest()[:24],
                    "claim_id": claim["claim_id"],
                    "claim_revision": claim["revision"],
                    "action": "defer",
                    "evidence_graph_digest": "",
                    "decided_at": started_at,
                }
            )
        for record in approved_document["records"]:
            if isinstance(record, dict) and record.get("record_id") in impacted_records:
                record["state"] = "stale"
        publication_changed = False
        for record in publication_document["records"]:
            if isinstance(record, dict) and record.get("record_id") in impacted_records:
                record["state"] = "retracted"
                publication_changed = True
        if publication_changed:
            publication_document["owner_review_state"] = "retracted"
        for evaluation in evals_document.get("evaluations", []):
            if not isinstance(evaluation, dict):
                continue
            referenced = set(evaluation.get("approved_record_ids", [])) | set(evaluation.get("record_ids", []))
            if referenced & impacted_records:
                evaluation["review_state"] = "draft"
                evaluation["stale_reason"] = "approved_record_invalidated"

        for relative, value in (
            ("sources/source-manifest.json", sources_document),
            ("candidates/claims.json", claims_document),
            ("publication/approved-records.json", approved_document),
            ("publication/publication-manifest.json", publication_document),
            ("evals/private-evals.json", evals_document),
        ):
            atomic_json(workspace / relative, value)
        append_jsonl(workspace / REVIEW_LOG_FILE, decisions)

        session.update(
            {
                "status": "awaiting_owner_review",
                "finished_at": utc_now(),
                "new_occurrence_id": new_occurrence_id,
                "invalidated_claim_count": len(impacted_claims),
                "invalidated_record_count": len(impacted_records),
            }
        )
        atomic_json(session_path, session)
        append_jsonl(
            workspace / "updates" / "events.jsonl",
            [
                {
                    "schema": EVENT_SCHEMA,
                    "update_id": update_id,
                    "event": "awaiting_owner_review",
                    "at": session["finished_at"],
                }
            ],
        )
        return {
            "status": session["status"],
            "update_id": update_id,
            "new_occurrence_id": new_occurrence_id,
            "invalidated_claim_count": len(impacted_claims),
            "invalidated_record_count": len(impacted_records),
        }
    except (OSError, KeyError, TypeError, ValueError):
        if session is not None and session.get("status") != "completed":
            session.update({"status": "failed", "finished_at": utc_now()})
            with suppress(OSError):
                atomic_json(session_path, session)
                append_jsonl(
                    workspace / "updates" / "events.jsonl",
                    [
                        {
                            "schema": EVENT_SCHEMA,
                            "update_id": update_id,
                            "event": "failed",
                            "at": session["finished_at"],
                        }
                    ],
                )
        raise
    finally:
        os.close(descriptor)
        with suppress(FileNotFoundError):
            lock_path.unlink()


def workspace_status(workspace: Path) -> dict[str, Any]:
    state = read_json(workspace / CURRENT_STATE_FILE, "current state")
    sessions = []
    sessions_dir = workspace / "updates" / "sessions"
    if sessions_dir.is_dir():
        for path in sorted(sessions_dir.glob("update-*.json")):
            try:
                session = read_json(path, "update session")
            except UpdateRefusal:
                continue
            sessions.append({"update_id": session.get("update_id", ""), "status": session.get("status", "unknown")})
    return {
        "workspace_revision": state.get("workspace_revision"),
        "current_private_snapshot_id": state.get("current_private_snapshot_id"),
        "serving_state": state.get("serving_state"),
        "pending_update_id": state.get("pending_update_id"),
        "blocked_record_count": len(state.get("blocked_record_ids", [])),
        "sessions": sessions,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan and apply governed digital-twin source refreshes.")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="hash an explicit source and create a metadata-only plan")
    plan.add_argument("workspace", help="explicit private workspace path")
    plan.add_argument("--source-id", required=True, help="stable logical source ID")
    plan.add_argument("--file", required=True, help="explicit owner-selected source file")
    plan.add_argument("--format", choices=("text", "json"), default="text", help="safe report format")
    apply = commands.add_parser("apply", help="apply a confirmed update plan")
    apply.add_argument("workspace", help="explicit private workspace path")
    apply.add_argument("--plan", required=True, help="opaque update plan ID")
    apply.add_argument("--confirm", action="store_true", help="confirm mutation and conservative invalidation")
    apply.add_argument("--format", choices=("text", "json"), default="text", help="safe report format")
    status = commands.add_parser("status", help="report serving and update state")
    status.add_argument("workspace", help="explicit private workspace path")
    status.add_argument("--format", choices=("text", "json"), default="text", help="safe report format")
    return parser


def print_report(report: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print("\t".join(f"{key}={value}" for key, value in report.items() if key != "sessions"))
        for session in report.get("sessions", []):
            print(f"session\t{session['update_id']}\t{session['status']}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path(os.path.abspath(os.path.expanduser(args.workspace)))
    if not workspace.is_dir():
        print(f"error\tworkspace directory does not exist\t{workspace}", file=sys.stderr)
        return 2
    try:
        if args.command == "plan":
            if not validator.ID_RE.fullmatch(args.source_id):
                raise UpdateRefusal("logical source ID has invalid shape")
            report = safe_plan_report(
                create_plan(workspace, args.source_id, Path(os.path.abspath(os.path.expanduser(args.file))))
            )
        elif args.command == "apply":
            if not args.confirm:
                print("refused\tapply requires --confirm", file=sys.stderr)
                return 2
            if not validator.ID_RE.fullmatch(args.plan):
                raise UpdateRefusal("update plan ID has invalid shape")
            report = apply_plan(workspace, args.plan)
        else:
            report = workspace_status(workspace)
    except UpdateRefusal as exc:
        print(f"refused\t{exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error\tupdate operation failed\t{type(exc).__name__}", file=sys.stderr)
        return 2
    print_report(report, args.format)
    return 0


if __name__ == "__main__":
    sys.exit(main())
