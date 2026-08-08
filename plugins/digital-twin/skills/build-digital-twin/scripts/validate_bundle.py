#!/usr/bin/env python3
"""Validate a professional digital-twin bundle without exposing sensitive values.

The validator reads only known structured manifests. Findings contain fixed messages and logical
JSON paths; suspected secret or private values are never included in output.

Exit codes: 0 = valid, 1 = validation/review findings, 2 = usage or unreadable input.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _bundle_common import POLICY_VERSION, REVIEW_LOG_FILE, SCHEMA_VERSION, VALIDATION_FILES, digest_json

ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
HASH_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")

SOURCE_KINDS = {"document", "interview_transcript", "reviewed_owner_statement", "public_web", "other"}
AUTHORSHIP = {"owner", "third_party", "mixed", "unknown"}
CONFIDENTIALITY = {"public", "sanitized", "private", "confidential", "restricted"}
THIRD_PARTY = {"none", "limited", "substantial", "unknown"}
RETENTION = {"session", "until_review", "owner_managed", "delete_after_extraction", "manifest_only"}
CONSENT = {"not_confirmed", "confirmed", "withdrawn"}
RIGHTS = {"not_confirmed", "confirmed", "restricted", "not_applicable"}
LIFECYCLE = {"inventoried", "active", "withdrawn", "deleted", "retracted"}
CONTENT_STATE = {"external", "retained", "deleted"}
INDEPENDENCE_REVIEW = {"unreviewed", "owner_confirmed", "not_independent"}

CATEGORIES = {
    "profile",
    "timeline",
    "employment",
    "education",
    "project",
    "skill",
    "accomplishment",
    "decision",
    "principle",
    "failure_lesson",
    "voice",
    "faq",
    "boundary",
    "contact_path",
}
SOURCE_ROLES = {"discovery", "self_report", "corroboration", "authoritative", "style_only"}
SUPPORT_DIRECTIONS = {"supports", "contradicts", "context_only"}
EDGE_STATES = {"active", "stale", "retracted"}
STRENGTHS = {"self_reported", "limited", "moderate", "strong"}
STRENGTH_RANK = {"unsupported": -1, "self_reported": 0, "limited": 1, "moderate": 2, "strong": 3}
VISIBILITY = {"private", "restricted", "internal", "public_candidate"}
REVIEW_STATES = {"pending", "rejected", "deferred", "approved"}
RECORD_STATES = {"active", "stale", "retracted"}
PUBLICATION_STATES = {"candidate", "approved", "retracted"}
CONFLICT_STATES = {"open", "resolved", "deferred"}
DECISION_ACTIONS = {"approve", "edit", "split", "merge", "reject", "defer", "retract"}
COVERAGE_STATES = {"missing", "self_reported", "weak", "conflicted", "reviewed", "approved"}

EXPECTED_SCHEMAS = {
    "sources/source-manifest.json": "digital-twin/source-manifest",
    "candidates/claims.json": "digital-twin/claims",
    "candidates/conflicts.json": "digital-twin/conflicts",
    "candidates/coverage.json": "digital-twin/coverage",
    "publication/approved-records.json": "digital-twin/approved-records",
    "publication/publication-manifest.json": "digital-twin/publication-manifest",
    "evals/private-evals.json": "digital-twin/private-evals",
}


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    document: str
    field_path: str
    message: str


def issue(code: str, document: str, field_path: str, message: str, severity: str = "error") -> Issue:
    return Issue(severity, code, document, field_path, message)


def sorted_issues(issues: Iterable[Issue]) -> list[Issue]:
    return sorted(issues, key=lambda item: (item.severity, item.code, item.document, item.field_path))


def is_object(value: Any) -> bool:
    return isinstance(value, dict)


def is_string(value: Any) -> bool:
    return isinstance(value, str)


def nonempty_string(value: Any) -> bool:
    return is_string(value) and bool(value.strip())


def path_at(base: str, *parts: Any) -> str:
    suffix = "/".join(str(part) for part in parts)
    return f"{base}/{suffix}" if suffix else base


def require_fields(value: dict[str, Any], fields: Iterable[str], document: str, base: str) -> list[Issue]:
    return [
        issue("missing-field", document, path_at(base, field), "required field is missing")
        for field in fields
        if field not in value
    ]


def check_enum(value: Any, allowed: set[str], document: str, field_path: str) -> list[Issue]:
    if not is_string(value) or value not in allowed:
        return [issue("invalid-enum", document, field_path, "field has an unsupported enum value")]
    return []


def validate_header(document: str, value: Any) -> list[Issue]:
    if not is_object(value):
        return [issue("invalid-document", document, "/", "document must be a JSON object")]
    issues: list[Issue] = []
    if value.get("schema") != EXPECTED_SCHEMAS[document]:
        issues.append(issue("invalid-schema", document, "/schema", "schema identifier does not match document"))
    if value.get("schema_version") != SCHEMA_VERSION:
        issues.append(issue("invalid-schema-version", document, "/schema_version", "unsupported schema version"))
    if (
        document
        in {
            "sources/source-manifest.json",
            "candidates/claims.json",
            "publication/approved-records.json",
            "publication/publication-manifest.json",
        }
        and value.get("policy_version") != POLICY_VERSION
    ):
        issues.append(issue("invalid-policy-version", document, "/policy_version", "unsupported policy version"))
    return issues


SECRET_PATTERNS = (
    ("possible-private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("possible-github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}")),
    ("possible-aws-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("possible-slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("possible-session-token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    (
        "possible-credential-assignment",
        re.compile(r"(?i)(?:api[_ -]?key|secret|token|password|cookie)\s*[:=]\s*\S{6,}"),
    ),
)
HIGH_RISK_PATTERNS = (
    ("possible-government-id", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
    ("possible-payment-card", re.compile(r"(?<!\d)(?:\d[ -]?){13,18}\d(?!\d)")),
)
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
ABSOLUTE_PATH_RE = re.compile(r"(?:^|\s)(?:/|[A-Za-z]:[\\/])")
SAFE_PATH_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def safe_path_key(key: Any, index: int) -> str:
    """Use a schema-like key in reports, otherwise a positional placeholder."""
    text = str(key)
    sensitive = (
        any(pattern.search(text) for _category, pattern in (*SECRET_PATTERNS, *HIGH_RISK_PATTERNS))
        or EMAIL_RE.search(text)
        or ABSOLUTE_PATH_RE.search(text)
    )
    return text if SAFE_PATH_KEY_RE.fullmatch(text) and not sensitive else f"redacted-key-{index}"


def walk_values(value: Any, base: str = "") -> Iterable[tuple[str, Any]]:
    """Yield values and keys using paths that cannot echo an untrusted object key."""
    yield base or "/", value
    if isinstance(value, dict):
        for index, key in enumerate(sorted(value, key=str)):
            component = safe_path_key(key, index)
            key_path = path_at(base, component)
            yield path_at(key_path, "object-key"), str(key)
            yield from walk_values(value[key], key_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_values(item, path_at(base, index))


def privacy_issues(documents: dict[str, Any]) -> list[Issue]:
    findings: list[Issue] = []
    for document, data in documents.items():
        public_doc = document == "publication/publication-manifest.json"
        for field_path, value in walk_values(data):
            if isinstance(value, float):
                findings.append(
                    issue("float-not-allowed", document, field_path, "floating-point values are not digest-safe")
                )
            if not isinstance(value, str):
                continue
            field_name = field_path.rsplit("/", 1)[-1]
            digest_metadata = field_name in {
                "content_hash",
                "span_hash",
                "evidence_graph_digest",
                "approval_digest",
            }
            for category, pattern in SECRET_PATTERNS:
                if pattern.search(value):
                    findings.append(
                        issue(
                            "privacy-possible-credential",
                            document,
                            field_path,
                            f"owner review required for category {category}",
                            severity="review",
                        )
                    )
            for category, pattern in () if digest_metadata else HIGH_RISK_PATTERNS:
                if pattern.search(value):
                    findings.append(
                        issue(
                            "privacy-high-risk-personal-data",
                            document,
                            field_path,
                            f"owner review required for category {category}",
                            severity="review",
                        )
                    )
            if public_doc and EMAIL_RE.search(value):
                findings.append(
                    issue(
                        "public-mailbox-address",
                        document,
                        field_path,
                        "public output must not contain a mailbox address",
                    )
                )
            if public_doc and ABSOLUTE_PATH_RE.search(value):
                findings.append(
                    issue("public-raw-path", document, field_path, "public output must not contain a raw path")
                )
    return findings


def validate_sources(data: Any) -> tuple[list[Issue], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    document = "sources/source-manifest.json"
    issues = validate_header(document, data)
    if not is_object(data):
        return issues, {}, {}
    sources = data.get("sources")
    if not isinstance(sources, list):
        issues.append(issue("invalid-type", document, "/sources", "sources must be an array"))
        return issues, {}, {}

    by_occurrence: dict[str, dict[str, Any]] = {}
    by_source: dict[str, dict[str, Any]] = {}
    required = (
        "source_id",
        "source_occurrence_id",
        "owner_title",
        "origin",
        "media_type",
        "source_kind",
        "content_hash",
        "derived_from_source_ids",
        "independence_group",
        "independence_review_state",
        "authorship",
        "confidentiality",
        "third_party_content",
        "processing_purpose",
        "retention_preference",
        "processing_consent",
        "publication_rights",
        "lifecycle_state",
        "content_state",
    )
    for index, source in enumerate(sources):
        base = f"/sources/{index}"
        if not is_object(source):
            issues.append(issue("invalid-type", document, base, "source occurrence must be an object"))
            continue
        issues.extend(require_fields(source, required, document, base))
        source_id = source.get("source_id")
        occurrence_id = source.get("source_occurrence_id")
        for field, value in (("source_id", source_id), ("source_occurrence_id", occurrence_id)):
            if not nonempty_string(value) or not ID_RE.fullmatch(value):
                issues.append(issue("invalid-id", document, path_at(base, field), "identifier has invalid shape"))
        if nonempty_string(source_id):
            if source_id in by_source:
                issues.append(issue("duplicate-id", document, path_at(base, "source_id"), "source ID is duplicated"))
            else:
                by_source[source_id] = source
        if nonempty_string(occurrence_id):
            if occurrence_id in by_occurrence:
                issues.append(
                    issue(
                        "duplicate-id",
                        document,
                        path_at(base, "source_occurrence_id"),
                        "occurrence ID is duplicated",
                    )
                )
            else:
                by_occurrence[occurrence_id] = source

        for field in ("owner_title", "origin", "media_type", "processing_purpose"):
            if not nonempty_string(source.get(field)):
                issues.append(issue("invalid-type", document, path_at(base, field), "field must be a non-empty string"))
        content_hash = source.get("content_hash")
        if content_hash != "" and (not is_string(content_hash) or not HASH_RE.fullmatch(content_hash)):
            issues.append(
                issue("invalid-hash", document, path_at(base, "content_hash"), "content hash must be SHA-256")
            )
        derived = source.get("derived_from_source_ids")
        if not isinstance(derived, list) or not all(nonempty_string(item) for item in derived):
            issues.append(
                issue(
                    "invalid-type",
                    document,
                    path_at(base, "derived_from_source_ids"),
                    "derivation IDs must be an array",
                )
            )
        if not is_string(source.get("independence_group")):
            issues.append(
                issue(
                    "invalid-type", document, path_at(base, "independence_group"), "independence group must be a string"
                )
            )
        for field, allowed in (
            ("source_kind", SOURCE_KINDS),
            ("independence_review_state", INDEPENDENCE_REVIEW),
            ("authorship", AUTHORSHIP),
            ("confidentiality", CONFIDENTIALITY),
            ("third_party_content", THIRD_PARTY),
            ("retention_preference", RETENTION),
            ("processing_consent", CONSENT),
            ("publication_rights", RIGHTS),
            ("lifecycle_state", LIFECYCLE),
            ("content_state", CONTENT_STATE),
        ):
            issues.extend(check_enum(source.get(field), allowed, document, path_at(base, field)))

    for index, source in enumerate(sources):
        if not is_object(source) or not isinstance(source.get("derived_from_source_ids"), list):
            continue
        for dep_index, source_id in enumerate(source["derived_from_source_ids"]):
            if not nonempty_string(source_id) or not ID_RE.fullmatch(source_id):
                issues.append(
                    issue(
                        "invalid-id",
                        document,
                        f"/sources/{index}/derived_from_source_ids/{dep_index}",
                        "identifier has invalid shape",
                    )
                )
                continue
            if source_id not in by_source:
                issues.append(
                    issue(
                        "broken-source-derivation",
                        document,
                        f"/sources/{index}/derived_from_source_ids/{dep_index}",
                        "derived source reference does not resolve",
                    )
                )

    graph = {
        source_id: [
            dep for dep in source.get("derived_from_source_ids", []) if nonempty_string(dep) and dep in by_source
        ]
        for source_id, source in by_source.items()
    }
    issues.extend(cycle_issues(graph, document, "/sources", "circular-source-derivation"))
    return issues, by_occurrence, by_source


def cycle_issues(graph: dict[str, list[str]], document: str, base: str, code: str) -> list[Issue]:
    """Detect directed cycles without putting possibly sensitive IDs into output."""
    visiting: set[str] = set()
    visited: set[str] = set()
    found = False

    def visit(node: str) -> None:
        nonlocal found
        if node in visiting:
            found = True
            return
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, []):
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
    return [issue(code, document, base, "dependency graph contains a cycle")] if found else []


def source_is_eligible(source: dict[str, Any] | None) -> bool:
    return bool(
        source
        and source.get("processing_consent") == "confirmed"
        and source.get("lifecycle_state") == "active"
        and source.get("content_state") in {"external", "retained"}
    )


def effective_source_role(edge: dict[str, Any], source: dict[str, Any]) -> str:
    """Interview transcripts and reviewed owner statements remain self-report evidence."""
    if source.get("source_kind") in {"interview_transcript", "reviewed_owner_statement"}:
        return "self_report"
    return str(edge.get("source_role", ""))


def eligible_support_edges(
    claim: dict[str, Any], sources_by_occurrence: dict[str, dict[str, Any]]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    eligible: list[tuple[dict[str, Any], dict[str, Any]]] = []
    edges = claim.get("evidence_edges", [])
    if not isinstance(edges, list):
        return eligible
    for edge in edges:
        if not is_object(edge):
            continue
        occurrence_id = edge.get("source_occurrence_id")
        source = sources_by_occurrence.get(occurrence_id) if nonempty_string(occurrence_id) else None
        if (
            edge.get("status") == "active"
            and edge.get("support") == "supports"
            and source_is_eligible(source)
            and effective_source_role(edge, source) in {"self_report", "corroboration", "authoritative"}
        ):
            eligible.append((edge, source))
    return eligible


def derivation_roots(
    source: dict[str, Any], sources_by_id: dict[str, dict[str, Any]], visiting: set[str] | None = None
) -> set[str]:
    """Return ultimate source IDs so circular/copied summaries cannot multiply support."""
    source_id = str(source.get("source_id", ""))
    seen = set() if visiting is None else set(visiting)
    if source_id in seen:
        return {source_id}
    seen.add(source_id)
    dependencies = source.get("derived_from_source_ids")
    if not isinstance(dependencies, list) or not dependencies:
        return {source_id}
    roots: set[str] = set()
    for dependency in dependencies:
        if not nonempty_string(dependency):
            continue
        parent = sources_by_id.get(dependency)
        roots.update(derivation_roots(parent, sources_by_id, seen) if parent else {str(dependency)})
    return roots


def evidence_ceiling(claim: dict[str, Any], sources_by_occurrence: dict[str, dict[str, Any]]) -> str:
    """Conservative strength ceiling; duplicate/unknown-independent sources do not multiply support."""
    eligible = eligible_support_edges(claim, sources_by_occurrence)
    if not eligible:
        return "unsupported"
    documentary = [(edge, source) for edge, source in eligible if effective_source_role(edge, source) != "self_report"]
    if not documentary:
        return "self_reported"

    ceiling = "limited"
    sources_by_id = {
        str(source.get("source_id")): source
        for source in sources_by_occurrence.values()
        if nonempty_string(source.get("source_id"))
    }
    independent_pairs: list[tuple[tuple[dict[str, Any], dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]]] = []
    for left_index, left in enumerate(documentary):
        left_source = left[1]
        if (
            left_source.get("independence_review_state") != "owner_confirmed"
            or not nonempty_string(left_source.get("independence_group"))
            or not HASH_RE.fullmatch(str(left_source.get("content_hash", "")))
        ):
            continue
        for right in documentary[left_index + 1 :]:
            right_source = right[1]
            if (
                right_source.get("independence_review_state") == "owner_confirmed"
                and nonempty_string(right_source.get("independence_group"))
                and HASH_RE.fullmatch(str(right_source.get("content_hash", "")))
                and left_source["independence_group"] != right_source["independence_group"]
                and left_source["content_hash"] != right_source["content_hash"]
                and derivation_roots(left_source, sources_by_id).isdisjoint(
                    derivation_roots(right_source, sources_by_id)
                )
            ):
                independent_pairs.append((left, right))
    if independent_pairs:
        ceiling = "moderate"
        for pair in independent_pairs:
            for edge, source in pair:
                coordinate = str(edge.get("coordinate", "")).strip().lower()
                bounded = coordinate and "unavailable" not in coordinate and "unknown" not in coordinate
                if effective_source_role(edge, source) == "authoritative" and bounded:
                    return "strong"
    return ceiling


def evidence_graph_digest(claim: dict[str, Any], sources_by_occurrence: dict[str, dict[str, Any]]) -> str:
    """Consistency token binding the claim revision to its complete evidence/source snapshot."""
    edges = claim.get("evidence_edges", []) if isinstance(claim.get("evidence_edges"), list) else []
    edge_snapshots = sorted(
        [edge for edge in edges if isinstance(edge, dict)], key=lambda edge: str(edge.get("edge_id", ""))
    )
    occurrence_ids = sorted(
        {
            str(edge.get("source_occurrence_id"))
            for edge in edge_snapshots
            if nonempty_string(edge.get("source_occurrence_id"))
        }
    )
    source_snapshots = []
    bound_source_fields = (
        "source_id",
        "source_occurrence_id",
        "content_hash",
        "derived_from_source_ids",
        "independence_group",
        "independence_review_state",
        "processing_consent",
        "lifecycle_state",
        "content_state",
        "confidentiality",
        "third_party_content",
        "publication_rights",
    )
    for occurrence_id in occurrence_ids:
        source = sources_by_occurrence.get(occurrence_id)
        if source is None:
            source_snapshots.append({"source_occurrence_id": occurrence_id, "missing": True})
        else:
            source_snapshots.append({field: source.get(field) for field in bound_source_fields})
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "claim_id": claim.get("claim_id"),
        "revision": claim.get("revision"),
        "wording": claim.get("wording"),
        "category": claim.get("category"),
        "visibility": claim.get("visibility"),
        "confidentiality": claim.get("confidentiality"),
        "publication_rights": claim.get("publication_rights"),
        "metric": claim.get("metric"),
        "flags": claim.get("flags"),
        "conflicts": claim.get("conflicts"),
        "depends_on_claim_ids": claim.get("depends_on_claim_ids"),
        "proposed_strength": claim.get("proposed_strength"),
        "max_strength": claim.get("max_strength"),
        "evidence_edges": edge_snapshots,
        "sources": source_snapshots,
    }
    return digest_json(snapshot)


def approval_is_current(
    claim: dict[str, Any], sources_by_occurrence: dict[str, dict[str, Any]], calculated_ceiling: str
) -> bool:
    approval = claim.get("approval")
    if claim.get("review_state") != "approved" or not is_object(approval):
        return False
    expected = {
        "exact_wording": claim.get("wording"),
        "claim_revision": claim.get("revision"),
        "evidence_graph_digest": evidence_graph_digest(claim, sources_by_occurrence),
        "approved_strength": claim.get("proposed_strength"),
        "visibility": claim.get("visibility"),
        "confidentiality": claim.get("confidentiality"),
        "publication_rights": claim.get("publication_rights"),
        "metric": claim.get("metric"),
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
    }
    return (
        all(approval.get(field) == value for field, value in expected.items())
        and nonempty_string(approval.get("reviewed_at"))
        and STRENGTH_RANK.get(str(claim.get("proposed_strength")), 99) <= STRENGTH_RANK[calculated_ceiling]
    )


def validate_decisions(data: Any) -> tuple[list[Issue], dict[str, dict[str, Any]]]:
    """Validate the append-order review log and return the latest decision per claim."""
    document = REVIEW_LOG_FILE
    issues: list[Issue] = []
    latest: dict[str, dict[str, Any]] = {}
    if data is None:
        return issues, latest
    if not isinstance(data, list):
        return [issue("invalid-type", document, "/", "decision log must contain JSON objects")], latest
    seen_decisions: set[str] = set()
    required = (
        "decision_id",
        "claim_id",
        "claim_revision",
        "action",
        "evidence_graph_digest",
        "decided_at",
    )
    for index, decision in enumerate(data):
        base = f"/decisions/{index}"
        if not is_object(decision):
            issues.append(issue("invalid-type", document, base, "decision entry must be an object"))
            continue
        issues.extend(require_fields(decision, required, document, base))
        decision_id = decision.get("decision_id")
        claim_id = decision.get("claim_id")
        for field, value in (("decision_id", decision_id), ("claim_id", claim_id)):
            if not nonempty_string(value) or not ID_RE.fullmatch(value):
                issues.append(issue("invalid-id", document, path_at(base, field), "identifier has invalid shape"))
        if nonempty_string(decision_id):
            if decision_id in seen_decisions:
                issues.append(
                    issue("duplicate-id", document, path_at(base, "decision_id"), "decision ID is duplicated")
                )
            seen_decisions.add(decision_id)
        revision = decision.get("claim_revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            issues.append(
                issue("invalid-revision", document, path_at(base, "claim_revision"), "revision must be positive")
            )
        issues.extend(check_enum(decision.get("action"), DECISION_ACTIONS, document, path_at(base, "action")))
        digest = decision.get("evidence_graph_digest")
        if not is_string(digest) or (digest != "" and not HASH_RE.fullmatch(digest)):
            issues.append(
                issue(
                    "invalid-hash",
                    document,
                    path_at(base, "evidence_graph_digest"),
                    "decision digest must be SHA-256 or empty",
                )
            )
        if decision.get("action") == "approve" and not nonempty_string(digest):
            issues.append(
                issue(
                    "missing-approval-digest",
                    document,
                    path_at(base, "evidence_graph_digest"),
                    "approve decision requires a digest",
                )
            )
        if not nonempty_string(decision.get("decided_at")):
            issues.append(issue("invalid-type", document, path_at(base, "decided_at"), "decision time is required"))
        if nonempty_string(claim_id):
            latest[claim_id] = decision
    return issues, latest


def validate_conflicts(data: Any) -> tuple[list[Issue], dict[str, dict[str, Any]]]:
    document = "candidates/conflicts.json"
    issues = validate_header(document, data)
    by_id: dict[str, dict[str, Any]] = {}
    if not is_object(data):
        return issues, by_id
    conflicts = data.get("conflicts")
    if not isinstance(conflicts, list):
        issues.append(issue("invalid-type", document, "/conflicts", "conflicts must be an array"))
        return issues, by_id
    for index, conflict in enumerate(conflicts):
        base = f"/conflicts/{index}"
        if not is_object(conflict):
            issues.append(issue("invalid-type", document, base, "conflict must be an object"))
            continue
        issues.extend(require_fields(conflict, ("conflict_id", "claim_ids", "summary", "status"), document, base))
        conflict_id = conflict.get("conflict_id")
        if not nonempty_string(conflict_id) or not ID_RE.fullmatch(conflict_id):
            issues.append(issue("invalid-id", document, path_at(base, "conflict_id"), "identifier has invalid shape"))
        elif conflict_id in by_id:
            issues.append(issue("duplicate-id", document, path_at(base, "conflict_id"), "conflict ID is duplicated"))
        else:
            by_id[conflict_id] = conflict
        claim_ids = conflict.get("claim_ids")
        if not isinstance(claim_ids, list):
            issues.append(issue("invalid-type", document, path_at(base, "claim_ids"), "claim IDs must be an array"))
        else:
            if not claim_ids:
                issues.append(
                    issue(
                        "invalid-conflict",
                        document,
                        path_at(base, "claim_ids"),
                        "conflict must name at least one claim",
                    )
                )
            if all(is_string(claim_id) for claim_id in claim_ids) and len(set(claim_ids)) != len(claim_ids):
                issues.append(
                    issue(
                        "duplicate-conflict-claim",
                        document,
                        path_at(base, "claim_ids"),
                        "conflict repeats a claim reference",
                    )
                )
            for claim_index, claim_id in enumerate(claim_ids):
                if not nonempty_string(claim_id) or not ID_RE.fullmatch(claim_id):
                    issues.append(
                        issue(
                            "invalid-id",
                            document,
                            path_at(base, "claim_ids", claim_index),
                            "identifier has invalid shape",
                        )
                    )
        if not nonempty_string(conflict.get("summary")):
            issues.append(issue("invalid-type", document, path_at(base, "summary"), "summary must be non-empty"))
        issues.extend(check_enum(conflict.get("status"), CONFLICT_STATES, document, path_at(base, "status")))
    return issues, by_id


def validate_conflict_links(
    conflicts_by_id: dict[str, dict[str, Any]], claims_by_id: dict[str, dict[str, Any]]
) -> list[Issue]:
    """Require resolvable, bidirectional claim/conflict links."""
    issues: list[Issue] = []
    document = "candidates/conflicts.json"
    for conflict_id, conflict in conflicts_by_id.items():
        claim_ids = conflict.get("claim_ids", []) if isinstance(conflict.get("claim_ids"), list) else []
        for claim_id in claim_ids:
            if not nonempty_string(claim_id):
                continue
            claim = claims_by_id.get(claim_id)
            if claim is None:
                issues.append(
                    issue("broken-conflict-claim", document, "/conflicts", "conflict claim reference does not resolve")
                )
            elif not isinstance(claim.get("conflicts"), list) or conflict_id not in claim["conflicts"]:
                issues.append(
                    issue(
                        "asymmetric-conflict-reference",
                        document,
                        "/conflicts",
                        "claim and conflict must reference each other",
                    )
                )
    for claim_id, claim in claims_by_id.items():
        claim_conflicts = claim.get("conflicts") if isinstance(claim.get("conflicts"), list) else []
        for conflict_id in claim_conflicts:
            if not nonempty_string(conflict_id):
                continue
            conflict = conflicts_by_id.get(conflict_id)
            if conflict is not None and (
                not isinstance(conflict.get("claim_ids"), list) or claim_id not in conflict["claim_ids"]
            ):
                issues.append(
                    issue(
                        "asymmetric-conflict-reference",
                        document,
                        "/conflicts",
                        "claim and conflict must reference each other",
                    )
                )
    return issues


def validate_claims(
    data: Any,
    sources_by_occurrence: dict[str, dict[str, Any]],
    conflicts_by_id: dict[str, dict[str, Any]],
    latest_decisions: dict[str, dict[str, Any]],
) -> tuple[list[Issue], dict[str, dict[str, Any]], set[str]]:
    document = "candidates/claims.json"
    issues = validate_header(document, data)
    by_id: dict[str, dict[str, Any]] = {}
    current_approvals: set[str] = set()
    if not is_object(data):
        return issues, by_id, current_approvals
    claims = data.get("claims")
    if not isinstance(claims, list):
        issues.append(issue("invalid-type", document, "/claims", "claims must be an array"))
        return issues, by_id, current_approvals

    required = (
        "claim_id",
        "revision",
        "wording",
        "category",
        "dates",
        "entities",
        "evidence_edges",
        "depends_on_claim_ids",
        "proposed_strength",
        "max_strength",
        "uncertainty",
        "conflicts",
        "flags",
        "metric",
        "visibility",
        "confidentiality",
        "publication_rights",
        "review_state",
        "approval",
    )
    for index, claim in enumerate(claims):
        base = f"/claims/{index}"
        if not is_object(claim):
            issues.append(issue("invalid-type", document, base, "claim must be an object"))
            continue
        issues.extend(require_fields(claim, required, document, base))
        claim_id = claim.get("claim_id")
        if not nonempty_string(claim_id) or not ID_RE.fullmatch(claim_id):
            issues.append(issue("invalid-id", document, path_at(base, "claim_id"), "identifier has invalid shape"))
        elif claim_id in by_id:
            issues.append(issue("duplicate-id", document, path_at(base, "claim_id"), "claim ID is duplicated"))
        else:
            by_id[claim_id] = claim
        if (
            not isinstance(claim.get("revision"), int)
            or isinstance(claim.get("revision"), bool)
            or claim["revision"] < 1
        ):
            issues.append(
                issue("invalid-revision", document, path_at(base, "revision"), "revision must be a positive integer")
            )
        if not nonempty_string(claim.get("wording")):
            issues.append(issue("invalid-type", document, path_at(base, "wording"), "wording must be non-empty"))
        for field in ("dates", "entities", "depends_on_claim_ids", "uncertainty", "conflicts"):
            if not isinstance(claim.get(field), list):
                issues.append(issue("invalid-type", document, path_at(base, field), "field must be an array"))
        if isinstance(claim.get("depends_on_claim_ids"), list) and claim["depends_on_claim_ids"]:
            issues.append(
                issue(
                    "claim-dependencies-not-supported",
                    document,
                    path_at(base, "depends_on_claim_ids"),
                    "claim dependencies are reserved and must be empty in schema version 0.1.0",
                )
            )
        if not is_object(claim.get("flags")):
            issues.append(issue("invalid-type", document, path_at(base, "flags"), "flags must be an object"))
        if claim.get("metric") is not None and not is_object(claim.get("metric")):
            issues.append(issue("invalid-type", document, path_at(base, "metric"), "metric must be null or an object"))
        for field, allowed in (
            ("category", CATEGORIES),
            ("proposed_strength", STRENGTHS),
            ("max_strength", STRENGTHS),
            ("visibility", VISIBILITY),
            ("confidentiality", CONFIDENTIALITY),
            ("publication_rights", RIGHTS),
            ("review_state", REVIEW_STATES),
        ):
            issues.extend(check_enum(claim.get(field), allowed, document, path_at(base, field)))

        edges = claim.get("evidence_edges")
        if not isinstance(edges, list):
            issues.append(
                issue("invalid-type", document, path_at(base, "evidence_edges"), "evidence edges must be an array")
            )
            edges = []
        seen_edges: set[str] = set()
        seen_relationships: set[tuple[Any, ...]] = set()
        for edge_index, edge in enumerate(edges):
            edge_base = path_at(base, "evidence_edges", edge_index)
            if not is_object(edge):
                issues.append(issue("invalid-type", document, edge_base, "evidence edge must be an object"))
                continue
            issues.extend(
                require_fields(
                    edge,
                    (
                        "edge_id",
                        "source_occurrence_id",
                        "coordinate",
                        "excerpt",
                        "span_hash",
                        "source_role",
                        "support",
                        "status",
                    ),
                    document,
                    edge_base,
                )
            )
            edge_id = edge.get("edge_id")
            if not nonempty_string(edge_id) or not ID_RE.fullmatch(edge_id):
                issues.append(
                    issue("invalid-id", document, path_at(edge_base, "edge_id"), "identifier has invalid shape")
                )
            elif edge_id in seen_edges:
                issues.append(
                    issue("duplicate-edge", document, path_at(edge_base, "edge_id"), "evidence edge is duplicated")
                )
            else:
                seen_edges.add(edge_id)
            occurrence_id = edge.get("source_occurrence_id")
            valid_occurrence_id = nonempty_string(occurrence_id)
            if not valid_occurrence_id or occurrence_id not in sources_by_occurrence:
                issues.append(
                    issue(
                        "broken-evidence-reference",
                        document,
                        path_at(edge_base, "source_occurrence_id"),
                        "source reference does not resolve",
                    )
                )
            relationship = tuple(
                str(value)
                for value in (
                    occurrence_id,
                    edge.get("coordinate"),
                    edge.get("source_role"),
                    edge.get("support"),
                )
            )
            if relationship in seen_relationships:
                issues.append(
                    issue("duplicate-evidence-relationship", document, edge_base, "evidence relationship is duplicated")
                )
            seen_relationships.add(relationship)
            if not nonempty_string(edge.get("coordinate")):
                issues.append(
                    issue(
                        "invalid-provenance",
                        document,
                        path_at(edge_base, "coordinate"),
                        "coordinate or limitation is required",
                    )
                )
            if not is_string(edge.get("excerpt")):
                issues.append(
                    issue("invalid-type", document, path_at(edge_base, "excerpt"), "excerpt must be a string")
                )
            span_hash = edge.get("span_hash")
            if span_hash != "" and (not is_string(span_hash) or not HASH_RE.fullmatch(span_hash)):
                issues.append(
                    issue("invalid-hash", document, path_at(edge_base, "span_hash"), "span hash must be SHA-256")
                )
            issues.extend(
                check_enum(edge.get("source_role"), SOURCE_ROLES, document, path_at(edge_base, "source_role"))
            )
            issues.extend(check_enum(edge.get("support"), SUPPORT_DIRECTIONS, document, path_at(edge_base, "support")))
            issues.extend(check_enum(edge.get("status"), EDGE_STATES, document, path_at(edge_base, "status")))
            source = sources_by_occurrence.get(occurrence_id) if valid_occurrence_id else None
            if (
                source is not None
                and source.get("source_kind") in {"interview_transcript", "reviewed_owner_statement"}
                and edge.get("support") == "supports"
                and edge.get("source_role") != "self_report"
            ):
                issues.append(
                    issue(
                        "invalid-self-report-role",
                        document,
                        path_at(edge_base, "source_role"),
                        "interview-derived evidence must use the self-report role",
                    )
                )
            if edge.get("status") == "active" and source is not None and not source_is_eligible(source):
                issues.append(
                    issue(
                        "stale-evidence-edge",
                        document,
                        path_at(edge_base, "status"),
                        "active edge references ineligible source state",
                    )
                )

        calculated = evidence_ceiling(claim, sources_by_occurrence)
        if calculated == "unsupported":
            issues.append(
                issue(
                    "unsupported-claim",
                    document,
                    path_at(base, "evidence_edges"),
                    "claim has no eligible factual support",
                )
            )
        elif claim.get("max_strength") != calculated:
            issues.append(
                issue(
                    "incorrect-evidence-ceiling",
                    document,
                    path_at(base, "max_strength"),
                    "stored ceiling does not match eligible independent evidence",
                )
            )
        proposed = str(claim.get("proposed_strength"))
        if proposed in STRENGTH_RANK and STRENGTH_RANK[proposed] > STRENGTH_RANK[calculated]:
            issues.append(
                issue(
                    "evidence-strength-exceeds-ceiling",
                    document,
                    path_at(base, "proposed_strength"),
                    "proposed strength exceeds calculated ceiling",
                )
            )

        conflict_ids = claim.get("conflicts", []) if isinstance(claim.get("conflicts"), list) else []
        for conflict_index, conflict_id in enumerate(conflict_ids):
            if not nonempty_string(conflict_id) or not ID_RE.fullmatch(conflict_id):
                issues.append(
                    issue(
                        "invalid-id",
                        document,
                        path_at(base, "conflicts", conflict_index),
                        "identifier has invalid shape",
                    )
                )
                continue
            if conflict_id not in conflicts_by_id:
                issues.append(
                    issue(
                        "broken-conflict-reference",
                        document,
                        path_at(base, "conflicts", conflict_index),
                        "conflict reference does not resolve",
                    )
                )

        current = approval_is_current(claim, sources_by_occurrence, calculated)
        decision = latest_decisions.get(claim_id) if nonempty_string(claim_id) else None
        if decision is not None:
            if decision.get("action") != "approve":
                if claim.get("review_state") == "approved":
                    issues.append(
                        issue(
                            "approval-overridden-by-decision",
                            document,
                            path_at(base, "approval"),
                            "latest owner decision invalidates active approval",
                        )
                    )
                current = False
            else:
                decision_matches = decision.get("claim_revision") == claim.get("revision") and decision.get(
                    "evidence_graph_digest"
                ) == evidence_graph_digest(claim, sources_by_occurrence)
                if not decision_matches or claim.get("review_state") != "approved":
                    issues.append(
                        issue(
                            "decision-claim-mismatch",
                            document,
                            path_at(base, "approval"),
                            "latest approve decision does not match current claim state",
                        )
                    )
                current = current and decision_matches
        if claim.get("review_state") == "approved":
            if not current:
                issues.append(
                    issue(
                        "stale-approval",
                        document,
                        path_at(base, "approval"),
                        "approval does not match current claim/evidence state",
                    )
                )
            elif nonempty_string(claim_id):
                current_approvals.add(claim_id)
        elif claim.get("approval") is not None:
            issues.append(
                issue(
                    "unexpected-approval",
                    document,
                    path_at(base, "approval"),
                    "non-approved claim must not carry an active approval",
                )
            )

    for index, claim in enumerate(claims):
        if not is_object(claim) or not isinstance(claim.get("depends_on_claim_ids"), list):
            continue
        for dep_index, dependency in enumerate(claim["depends_on_claim_ids"]):
            if not nonempty_string(dependency) or not ID_RE.fullmatch(dependency):
                issues.append(
                    issue(
                        "invalid-id",
                        document,
                        f"/claims/{index}/depends_on_claim_ids/{dep_index}",
                        "identifier has invalid shape",
                    )
                )
                continue
            if dependency not in by_id:
                issues.append(
                    issue(
                        "broken-claim-dependency",
                        document,
                        f"/claims/{index}/depends_on_claim_ids/{dep_index}",
                        "claim dependency does not resolve",
                    )
                )
    graph = {
        claim_id: [dep for dep in dependencies if nonempty_string(dep) and dep in by_id]
        for claim_id, claim in by_id.items()
        for dependencies in [
            claim.get("depends_on_claim_ids") if isinstance(claim.get("depends_on_claim_ids"), list) else []
        ]
    }
    issues.extend(cycle_issues(graph, document, "/claims", "circular-claim-dependency"))
    for claim_id in latest_decisions:
        if claim_id not in by_id:
            issues.append(
                issue(
                    "broken-decision-claim",
                    REVIEW_LOG_FILE,
                    "/decisions",
                    "decision claim reference does not resolve",
                )
            )
    return issues, by_id, current_approvals


def validate_coverage(data: Any) -> list[Issue]:
    document = "candidates/coverage.json"
    issues = validate_header(document, data)
    if not is_object(data):
        return issues
    categories = data.get("categories")
    if not is_object(categories):
        issues.append(issue("invalid-type", document, "/categories", "coverage categories must be an object"))
        return issues
    for index, (name, state) in enumerate(categories.items()):
        issues.extend(check_enum(state, COVERAGE_STATES, document, path_at("/categories", safe_path_key(name, index))))
    return issues


def validate_evals(data: Any) -> list[Issue]:
    document = "evals/private-evals.json"
    issues = validate_header(document, data)
    if is_object(data) and not isinstance(data.get("evaluations"), list):
        issues.append(issue("invalid-type", document, "/evaluations", "evaluations must be an array"))
    return issues


def validate_approved_records(
    data: Any,
    claims_by_id: dict[str, dict[str, Any]],
    current_approvals: set[str],
) -> tuple[list[Issue], dict[str, dict[str, Any]]]:
    document = "publication/approved-records.json"
    issues = validate_header(document, data)
    by_id: dict[str, dict[str, Any]] = {}
    if not is_object(data):
        return issues, by_id
    records = data.get("records")
    if not isinstance(records, list):
        issues.append(issue("invalid-type", document, "/records", "records must be an array"))
        return issues, by_id
    required = (
        "record_id",
        "claim_id",
        "claim_revision",
        "wording",
        "evidence_strength",
        "visibility",
        "approval_digest",
        "state",
    )
    for index, record in enumerate(records):
        base = f"/records/{index}"
        if not is_object(record):
            issues.append(issue("invalid-type", document, base, "approved record must be an object"))
            continue
        issues.extend(require_fields(record, required, document, base))
        record_id = record.get("record_id")
        if not nonempty_string(record_id) or not ID_RE.fullmatch(record_id):
            issues.append(issue("invalid-id", document, path_at(base, "record_id"), "identifier has invalid shape"))
        elif record_id in by_id:
            issues.append(issue("duplicate-id", document, path_at(base, "record_id"), "record ID is duplicated"))
        else:
            by_id[record_id] = record
        issues.extend(check_enum(record.get("state"), RECORD_STATES, document, path_at(base, "state")))
        claim_id = record.get("claim_id")
        claim = claims_by_id.get(claim_id) if nonempty_string(claim_id) else None
        if claim is None:
            issues.append(
                issue(
                    "broken-approved-record",
                    document,
                    path_at(base, "claim_id"),
                    "approved claim reference does not resolve",
                )
            )
            continue
        active = record.get("state") == "active"
        matches = (
            record.get("claim_revision") == claim.get("revision")
            and record.get("wording") == claim.get("wording")
            and record.get("evidence_strength") == claim.get("proposed_strength")
            and record.get("visibility") == claim.get("visibility")
            and is_object(claim.get("approval"))
            and record.get("approval_digest") == claim["approval"].get("evidence_graph_digest")
        )
        if active and (not nonempty_string(claim_id) or claim_id not in current_approvals):
            issues.append(
                issue("stale-approved-record", document, base, "active record references a non-current approval")
            )
        if active and not matches:
            issues.append(
                issue(
                    "approved-record-mismatch",
                    document,
                    base,
                    "active record does not match exact approved claim state",
                )
            )
    return issues, by_id


def has_open_conflict(claim_id: str, claim: dict[str, Any], conflicts_by_id: dict[str, dict[str, Any]]) -> bool:
    claim_conflicts = claim.get("conflicts") if isinstance(claim.get("conflicts"), list) else []
    named_by_claim = {conflict_id for conflict_id in claim_conflicts if nonempty_string(conflict_id)}
    named_by_index = {
        conflict_id
        for conflict_id, conflict in conflicts_by_id.items()
        if isinstance(conflict.get("claim_ids"), list) and claim_id in conflict["claim_ids"]
    }
    return any(
        conflicts_by_id.get(conflict_id, {}).get("status") != "resolved"
        for conflict_id in named_by_claim | named_by_index
    )


def public_source_eligible(claim: dict[str, Any], sources_by_occurrence: dict[str, dict[str, Any]]) -> bool:
    edges = claim.get("evidence_edges", []) if isinstance(claim.get("evidence_edges"), list) else []
    for edge in edges:
        if not is_object(edge) or edge.get("support") != "supports" or edge.get("status") != "active":
            continue
        occurrence_id = edge.get("source_occurrence_id")
        source = sources_by_occurrence.get(occurrence_id) if nonempty_string(occurrence_id) else None
        if (
            not source_is_eligible(source)
            or source.get("confidentiality") not in {"public", "sanitized"}
            or source.get("third_party_content") in {"substantial", "unknown"}
            or source.get("publication_rights") != "confirmed"
        ):
            return False
    return True


def validate_publication(
    data: Any,
    approved_by_id: dict[str, dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
    current_approvals: set[str],
    sources_by_occurrence: dict[str, dict[str, Any]],
    conflicts_by_id: dict[str, dict[str, Any]],
) -> list[Issue]:
    document = "publication/publication-manifest.json"
    issues = validate_header(document, data)
    if not is_object(data):
        return issues
    issues.extend(require_fields(data, ("owner_review_state", "reviewed_at", "records"), document, "/"))
    if not is_string(data.get("owner_review_state")) or data.get("owner_review_state") not in {
        "draft",
        "approved",
        "retracted",
    }:
        issues.append(issue("invalid-enum", document, "/owner_review_state", "owner review state is unsupported"))
    records = data.get("records")
    if not isinstance(records, list):
        issues.append(issue("invalid-type", document, "/records", "publication records must be an array"))
        return issues
    seen_ids: set[str] = set()
    allowed_fields = {"publication_id", "record_id", "wording", "visibility", "state"}
    for index, record in enumerate(records):
        base = f"/records/{index}"
        if not is_object(record):
            issues.append(issue("invalid-type", document, base, "publication record must be an object"))
            continue
        issues.extend(require_fields(record, allowed_fields, document, base))
        extra = set(record) - allowed_fields
        if extra:
            issues.append(issue("public-extra-fields", document, base, "public record contains unsupported fields"))
        publication_id = record.get("publication_id")
        if not nonempty_string(publication_id) or not ID_RE.fullmatch(publication_id):
            issues.append(
                issue("invalid-id", document, path_at(base, "publication_id"), "identifier has invalid shape")
            )
        elif publication_id in seen_ids:
            issues.append(
                issue("duplicate-id", document, path_at(base, "publication_id"), "publication ID is duplicated")
            )
        else:
            seen_ids.add(publication_id)
        if record.get("visibility") != "public":
            issues.append(
                issue(
                    "invalid-public-visibility",
                    document,
                    path_at(base, "visibility"),
                    "published record visibility must be public",
                )
            )
        issues.extend(check_enum(record.get("state"), PUBLICATION_STATES, document, path_at(base, "state")))
        if record.get("state") == "retracted":
            continue
        if record.get("state") != "approved":
            issues.append(
                issue(
                    "publication-record-not-approved",
                    document,
                    path_at(base, "state"),
                    "publication record requires explicit owner-approved state",
                )
            )
        if data.get("owner_review_state") != "approved" or not nonempty_string(data.get("reviewed_at")):
            issues.append(
                issue("publication-not-owner-approved", document, base, "publication requires separate owner approval")
            )
        record_id = record.get("record_id")
        approved = approved_by_id.get(record_id) if nonempty_string(record_id) else None
        if approved is None or approved.get("state") != "active":
            issues.append(
                issue(
                    "broken-publication-record",
                    document,
                    path_at(base, "record_id"),
                    "active approved record reference is required",
                )
            )
            continue
        approved_claim_id = approved.get("claim_id")
        claim = claims_by_id.get(approved_claim_id) if nonempty_string(approved_claim_id) else None
        if claim is None:
            issues.append(
                issue(
                    "broken-publication-claim",
                    document,
                    path_at(base, "record_id"),
                    "approved claim reference is unavailable",
                )
            )
            continue
        if not nonempty_string(approved_claim_id) or approved_claim_id not in current_approvals:
            issues.append(issue("stale-publication-record", document, base, "publication depends on a stale approval"))
        if record.get("wording") != approved.get("wording") or record.get("wording") != claim.get("wording"):
            issues.append(
                issue(
                    "public-wording-mismatch",
                    document,
                    path_at(base, "wording"),
                    "public wording must exactly match approved atomic wording",
                )
            )
        if (
            claim.get("visibility") != "public_candidate"
            or claim.get("confidentiality") not in {"public", "sanitized"}
            or claim.get("publication_rights") != "confirmed"
            or has_open_conflict(str(claim.get("claim_id", "")), claim, conflicts_by_id)
            or not public_source_eligible(claim, sources_by_occurrence)
        ):
            issues.append(
                issue(
                    "publication-ineligible",
                    document,
                    base,
                    "claim fails visibility, rights, conflict, or source privacy gate",
                )
            )
    return issues


def validate_documents(documents: dict[str, Any]) -> list[Issue]:
    """Pure bundle validation over already-loaded known documents."""
    issues: list[Issue] = []
    source_issues, sources_by_occurrence, _sources_by_id = validate_sources(
        documents.get("sources/source-manifest.json")
    )
    issues.extend(source_issues)
    conflict_issues, conflicts_by_id = validate_conflicts(documents.get("candidates/conflicts.json"))
    issues.extend(conflict_issues)
    decision_issues, latest_decisions = validate_decisions(documents.get(REVIEW_LOG_FILE))
    issues.extend(decision_issues)
    claim_issues, claims_by_id, current_approvals = validate_claims(
        documents.get("candidates/claims.json"),
        sources_by_occurrence,
        conflicts_by_id,
        latest_decisions,
    )
    issues.extend(claim_issues)
    issues.extend(validate_conflict_links(conflicts_by_id, claims_by_id))
    issues.extend(validate_coverage(documents.get("candidates/coverage.json")))
    issues.extend(validate_evals(documents.get("evals/private-evals.json")))
    approved_issues, approved_by_id = validate_approved_records(
        documents.get("publication/approved-records.json"), claims_by_id, current_approvals
    )
    issues.extend(approved_issues)
    issues.extend(
        validate_publication(
            documents.get("publication/publication-manifest.json"),
            approved_by_id,
            claims_by_id,
            current_approvals,
            sources_by_occurrence,
            conflicts_by_id,
        )
    )
    issues.extend(privacy_issues(documents))
    return sorted_issues(issues)


def path_inside(child: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath((str(child), str(parent))) == str(parent)
    except ValueError:
        return False


def load_bundle(workspace: Path) -> tuple[dict[str, Any], list[Issue], str | None]:
    """Read only known structured files; never read transcripts, sources, or context prose."""
    documents: dict[str, Any] = {}
    issues: list[Issue] = []
    root = workspace.resolve()
    for relative in VALIDATION_FILES:
        target = workspace / relative
        if not target.is_file():
            issues.append(issue("missing-document", relative, "/", "required bundle document is missing"))
            continue
        if not path_inside(target.resolve(), root):
            return documents, issues, f"refused\tvalidation document escapes workspace\t{relative}"
        try:
            documents[relative] = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return documents, issues, f"error\tunreadable structured document\t{relative}\t{type(exc).__name__}"

    review_log = workspace / REVIEW_LOG_FILE
    if not review_log.is_file():
        issues.append(issue("missing-document", REVIEW_LOG_FILE, "/", "required review log is missing"))
    elif not path_inside(review_log.resolve(), root):
        return documents, issues, f"refused\tvalidation document escapes workspace\t{REVIEW_LOG_FILE}"
    else:
        decisions = []
        line_number = 0
        try:
            lines = review_log.read_text(encoding="utf-8").splitlines()
            for line_number, line in enumerate(lines, start=1):
                if line.strip():
                    decisions.append(json.loads(line))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return (
                documents,
                issues,
                f"error\tunreadable structured document\t{REVIEW_LOG_FILE}\tline-{line_number}\t{type(exc).__name__}",
            )
        documents[REVIEW_LOG_FILE] = decisions
    return documents, issues, None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a digital-twin bundle with metadata-only privacy findings.")
    parser.add_argument("workspace", help="explicit digital-twin workspace path")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="stable report format")
    return parser


def report_json(issues: list[Issue]) -> str:
    payload = {
        "valid": not issues,
        "summary": {
            "errors": sum(item.severity == "error" for item in issues),
            "review": sum(item.severity == "review" for item in issues),
        },
        "issues": [asdict(item) for item in issues],
    }
    return json.dumps(payload, sort_keys=True, indent=2)


def report_text(issues: list[Issue]) -> str:
    if not issues:
        return "valid\t0 findings"
    lines = [f"invalid\t{len(issues)} findings"]
    lines.extend(f"{item.severity}\t{item.code}\t{item.document}#{item.field_path}\t{item.message}" for item in issues)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path(os.path.abspath(os.path.expanduser(args.workspace)))
    if not workspace.is_dir():
        print(f"error\tworkspace directory does not exist\t{workspace}", file=sys.stderr)
        return 2
    documents, load_issues, fatal = load_bundle(workspace)
    if fatal:
        print(fatal, file=sys.stderr)
        return 2
    issues = sorted_issues([*load_issues, *validate_documents(documents)])
    print(report_json(issues) if args.format == "json" else report_text(issues))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
