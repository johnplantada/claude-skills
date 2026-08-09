#!/usr/bin/env python3
"""Query a current private career-twin snapshot and capture owner feedback safely.

This helper is deliberately extractive: it retrieves exact approved records and produces a
structured response contract. It never reads working claims, source files, or transcripts and
never mutates factual bundle state.

Exit codes: 0 = response/feedback recorded, 1 = safe abstention or blocked serving, 2 = usage/error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.2.0"
CURRENT_STATE_FILE = "state/current.json"
FEEDBACK_FILE = "feedback/owner-inbox.jsonl"
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "would",
    "you",
}
STRENGTH_RANK = {"self_reported": 0, "limited": 1, "moderate": 2, "strong": 3}
FEEDBACK_CATEGORIES = {"useful", "wrong", "outdated", "private", "missing", "retract"}
AUTHORITY_PATTERNS = (
    "accept the offer",
    "negotiate",
    "schedule the meeting",
    "send this",
    "submit this",
    "contact them",
    "commit to",
    "agree on my behalf",
)


class SnapshotError(Exception):
    """A fixed-message private snapshot safety failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def safe_child(root: Path, *parts: str) -> Path:
    target = root.joinpath(*parts)
    try:
        if os.path.commonpath((str(target.resolve()), str(root.resolve()))) != str(root.resolve()):
            raise SnapshotError("snapshot path escapes workspace")
    except ValueError as exc:
        raise SnapshotError("snapshot path is invalid") from exc
    return target


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise SnapshotError(f"{label} must be an object")
    return value


def load_current_snapshot(workspace: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    state = read_json(safe_child(workspace, CURRENT_STATE_FILE), "current state")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise SnapshotError("current state uses an unsupported schema version")
    if state.get("serving_state") != "ready":
        raise SnapshotError("private serving is unavailable pending build or maintenance review")
    snapshot_id = state.get("current_private_snapshot_id")
    if not isinstance(snapshot_id, str) or not ID_RE.fullmatch(snapshot_id):
        raise SnapshotError("current private snapshot pointer is missing or invalid")
    manifest = read_json(safe_child(workspace, "snapshots", snapshot_id, "snapshot-manifest.json"), "snapshot manifest")
    records = read_json(safe_child(workspace, "snapshots", snapshot_id, "records.json"), "snapshot records")
    if manifest.get("snapshot_id") != snapshot_id or manifest.get("records_digest") != digest_json(records):
        raise SnapshotError("snapshot integrity check failed")
    if records.get("schema") != "digital-twin/private-snapshot-records" or not isinstance(records.get("records"), list):
        raise SnapshotError("snapshot records schema is invalid")
    return state, manifest, records


def query_terms(question: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(question.lower()) if len(token) > 2 and token not in STOP_WORDS}


def task_categories(question: str) -> set[str]:
    lowered = question.lower()
    categories: set[str] = set()
    if any(term in lowered for term in ("interview", "story", "example")):
        categories |= {"accomplishment", "project", "decision", "failure_lesson"}
    if any(term in lowered for term in ("bio", "profile", "about me")):
        categories |= {"profile", "employment", "accomplishment", "principle"}
    if any(term in lowered for term in ("role", "job", "position", "qualification")):
        categories |= {"skill", "project", "employment", "accomplishment"}
    return categories


def select_records(records: list[Any], question: str, limit: int) -> list[dict[str, Any]]:
    terms = query_terms(question)
    preferred_categories = task_categories(question)
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("record_id"), str):
            continue
        searchable = " ".join(
            str(value)
            for value in (
                record.get("wording", ""),
                record.get("category", ""),
                record.get("entities", []),
                record.get("dates", []),
            )
        ).lower()
        score = sum(term in searchable for term in terms)
        if record.get("category") in preferred_categories:
            score += 2
        if score:
            ranked.append((score, record["record_id"], record))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [record for _score, _record_id, record in ranked[:limit]]


def response_for(question: str, snapshot_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    lowered = question.lower()
    authority_refusal = any(pattern in lowered for pattern in AUTHORITY_PATTERNS)
    selected_ids = [record["record_id"] for record in records]
    response_basis = {"question": question, "snapshot_id": snapshot_id, "record_ids": selected_ids}
    response_id = "response-" + digest_json(response_basis).split(":", 1)[1][:24]
    if authority_refusal:
        return {
            "answer": "I can help prepare an owner-reviewable draft, but I cannot act or commit on the owner's behalf.",
            "response_id": response_id,
            "snapshot_id": snapshot_id,
            "record_ids": [],
            "evidence_strength": None,
            "abstained": True,
            "boundary_code": "authority_refusal",
            "contact_action": None,
            "records": [],
        }
    if not records:
        return {
            "answer": "The current approved private snapshot does not provide enough evidence to answer.",
            "response_id": response_id,
            "snapshot_id": snapshot_id,
            "record_ids": [],
            "evidence_strength": None,
            "abstained": True,
            "boundary_code": "insufficient_approved_evidence",
            "contact_action": None,
            "records": [],
        }
    strength = min(
        (str(record.get("evidence_strength")) for record in records),
        key=lambda item: STRENGTH_RANK.get(item, -1),
    )
    answer = " ".join(str(record.get("wording", "")).strip() for record in records).strip()
    return {
        "answer": answer,
        "response_id": response_id,
        "snapshot_id": snapshot_id,
        "record_ids": selected_ids,
        "evidence_strength": strength,
        "abstained": False,
        "boundary_code": None,
        "contact_action": None,
        "records": records,
    }


def append_feedback(workspace: Path, item: dict[str, Any]) -> None:
    path = safe_child(workspace, FEEDBACK_FILE)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if os.name != "nt" and path.exists():
            path.chmod(0o600)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use a current private career-twin snapshot safely.")
    commands = parser.add_subparsers(dest="command", required=True)

    query = commands.add_parser("query", help="retrieve approved records and return a response contract")
    query.add_argument("workspace", help="explicit private workspace path")
    query.add_argument("question", help="owner's career question")
    query.add_argument("--limit", type=int, default=5, help="maximum approved records to retrieve")
    query.add_argument("--format", choices=("text", "json"), default="text", help="stable output format")

    feedback = commands.add_parser("feedback", help="append confirmed owner feedback without changing facts")
    feedback.add_argument("workspace", help="explicit private workspace path")
    feedback.add_argument("--response-id", required=True, help="response ID returned by query")
    feedback.add_argument("--category", required=True, choices=sorted(FEEDBACK_CATEGORIES))
    feedback.add_argument("--record-id", action="append", default=[], help="related approved record ID")
    feedback.add_argument("--note", default="", help="optional owner note stored only in the private inbox")
    feedback.add_argument("--confirm", action="store_true", help="confirm this owner feedback item")
    feedback.add_argument("--format", choices=("text", "json"), default="text", help="stable output format")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path(os.path.abspath(os.path.expanduser(args.workspace)))
    if not workspace.is_dir():
        print(f"error\tworkspace directory does not exist\t{workspace}", file=sys.stderr)
        return 2
    try:
        _state, manifest, records_document = load_current_snapshot(workspace)
    except SnapshotError as exc:
        payload = {"abstained": True, "boundary_code": "snapshot_unavailable", "message": str(exc)}
        if getattr(args, "format", "text") == "json":
            print(json.dumps(payload, sort_keys=True, indent=2))
        else:
            print(f"abstained\tsnapshot_unavailable\t{exc}")
        return 1

    if args.command == "query":
        if args.limit < 1 or args.limit > 50:
            print("error\t--limit must be between 1 and 50", file=sys.stderr)
            return 2
        selected = select_records(records_document["records"], args.question, args.limit)
        response = response_for(args.question, manifest["snapshot_id"], selected)
        if args.format == "json":
            print(json.dumps(response, sort_keys=True, indent=2, ensure_ascii=False))
        else:
            print(response["answer"])
            print(f"response\t{response['response_id']}\tsnapshot\t{response['snapshot_id']}")
            for record_id in response["record_ids"]:
                print(f"citation\t{record_id}")
        return 1 if response["abstained"] else 0

    if not args.confirm:
        print("refused\tfeedback requires --confirm", file=sys.stderr)
        return 2
    if not ID_RE.fullmatch(args.response_id) or any(not ID_RE.fullmatch(item) for item in args.record_id):
        print("refused\tresponse and record IDs must have valid opaque shapes", file=sys.stderr)
        return 2
    feedback_id = "feedback-" + secrets.token_hex(12)
    item = {
        "schema": "digital-twin/owner-feedback-item",
        "schema_version": SCHEMA_VERSION,
        "feedback_id": feedback_id,
        "response_id": args.response_id,
        "snapshot_id": manifest["snapshot_id"],
        "category": args.category,
        "record_ids": sorted(set(args.record_id)),
        "owner_note": args.note,
        "confirmed": True,
        "status": "new",
        "created_at": utc_now(),
    }
    try:
        append_feedback(workspace, item)
    except OSError as exc:
        print(f"error\tfeedback write failed\t{type(exc).__name__}", file=sys.stderr)
        return 2
    report = {"status": "recorded", "feedback_id": feedback_id, "snapshot_id": manifest["snapshot_id"]}
    if args.format == "json":
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print(f"recorded\t{feedback_id}\tsnapshot\t{manifest['snapshot_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
