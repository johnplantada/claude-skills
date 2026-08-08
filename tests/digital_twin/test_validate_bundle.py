"""Bundle graph, evidence, approval, publication, deletion, and privacy invariants."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import init_workspace as iw
import validate_bundle as vb
from _bundle_common import REVIEW_LOG_FILE, TEMPLATE_FILES, template_text


def empty_documents() -> dict[str, Any]:
    return {target: json.loads(template_text(asset)) for target, asset in TEMPLATE_FILES.items()}


def synthetic_source(
    suffix: str,
    *,
    kind: str = "document",
    content_hash: str | None = None,
    independence_group: str | None = None,
    independence_review_state: str = "owner_confirmed",
) -> dict[str, Any]:
    return {
        "source_id": f"src-{suffix}",
        "source_occurrence_id": f"occ-{suffix}",
        "owner_title": f"Synthetic source {suffix}",
        "origin": f"owner-selected://{suffix}",
        "media_type": "text/plain",
        "source_kind": kind,
        "content_hash": content_hash
        if content_hash is not None
        else "sha256:" + hashlib.sha256(suffix.encode()).hexdigest(),
        "derived_from_source_ids": [],
        "independence_group": independence_group if independence_group is not None else f"group-{suffix}",
        "independence_review_state": independence_review_state,
        "authorship": "owner",
        "confidentiality": "public",
        "third_party_content": "none",
        "processing_purpose": "synthetic professional context test",
        "retention_preference": "owner_managed",
        "processing_consent": "confirmed",
        "publication_rights": "confirmed",
        "lifecycle_state": "active",
        "content_state": "external",
    }


def evidence_edge(source: dict[str, Any], suffix: str, role: str) -> dict[str, Any]:
    return {
        "edge_id": f"edge-{suffix}",
        "source_occurrence_id": source["source_occurrence_id"],
        "coordinate": f"section {suffix}",
        "excerpt": "",
        "span_hash": "",
        "source_role": role,
        "support": "supports",
        "status": "active",
    }


def synthetic_claim(
    sources_and_roles: list[tuple[dict[str, Any], str]],
    *,
    claim_id: str = "claim-alpha",
    visibility: str = "internal",
) -> dict[str, Any]:
    claim = {
        "claim_id": claim_id,
        "revision": 1,
        "wording": "The owner delivered a synthetic project outcome.",
        "category": "accomplishment",
        "dates": [],
        "entities": [],
        "evidence_edges": [
            evidence_edge(source, f"{index}-{source['source_id']}", role)
            for index, (source, role) in enumerate(sources_and_roles)
        ],
        "depends_on_claim_ids": [],
        "proposed_strength": "self_reported",
        "max_strength": "self_reported",
        "uncertainty": [],
        "conflicts": [],
        "flags": {"privacy": false_value(), "third_party": false_value(), "contact_authorized": false_value()},
        "metric": None,
        "visibility": visibility,
        "confidentiality": "public",
        "publication_rights": "confirmed",
        "review_state": "pending",
        "approval": None,
    }
    sources_by_occurrence = {source["source_occurrence_id"]: source for source, _role in sources_and_roles}
    ceiling = vb.evidence_ceiling(claim, sources_by_occurrence)
    claim["max_strength"] = ceiling
    claim["proposed_strength"] = ceiling
    return claim


def false_value() -> bool:
    """Keep fixture flags visibly synthetic and avoid magic truthy values."""
    return False


def approve_claim(claim: dict[str, Any], sources: list[dict[str, Any]]) -> None:
    by_occurrence = {source["source_occurrence_id"]: source for source in sources}
    claim["review_state"] = "approved"
    claim["approval"] = {
        "exact_wording": claim["wording"],
        "claim_revision": claim["revision"],
        "evidence_graph_digest": vb.evidence_graph_digest(claim, by_occurrence),
        "approved_strength": claim["proposed_strength"],
        "visibility": claim["visibility"],
        "confidentiality": claim["confidentiality"],
        "publication_rights": claim["publication_rights"],
        "metric": claim["metric"],
        "reviewed_at": "2026-01-01",
        "schema_version": "0.1.0",
        "policy_version": "0.1.0",
    }


def install_claim(documents: dict[str, Any], claim: dict[str, Any], sources: list[dict[str, Any]]) -> None:
    documents["sources/source-manifest.json"]["sources"] = sources
    documents["candidates/claims.json"]["claims"] = [claim]


def issue_codes(documents: dict[str, Any]) -> set[str]:
    return {finding.code for finding in vb.validate_documents(documents)}


def active_record(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": "record-alpha",
        "claim_id": claim["claim_id"],
        "claim_revision": claim["revision"],
        "wording": claim["wording"],
        "evidence_strength": claim["proposed_strength"],
        "visibility": claim["visibility"],
        "approval_digest": claim["approval"]["evidence_graph_digest"],
        "state": "active",
    }


def public_record(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "publication_id": "publication-alpha",
        "record_id": "record-alpha",
        "wording": claim["wording"],
        "visibility": "public",
        "state": "approved",
    }


def test_empty_starter_manifests_are_valid():
    assert vb.validate_documents(empty_documents()) == []


def test_load_bundle_reads_append_only_owner_decisions(tmp_path: Path):
    workspace = tmp_path / "private-twin"
    assert iw.main([str(workspace)]) == 0
    decision = {
        "decision_id": "decision-retract-alpha",
        "claim_id": "claim-alpha",
        "claim_revision": 1,
        "action": "retract",
        "evidence_graph_digest": "sha256:" + "a" * 64,
        "decided_at": "2026-01-03",
    }
    (workspace / REVIEW_LOG_FILE).write_text(json.dumps(decision) + "\n")

    documents, load_issues, fatal = vb.load_bundle(workspace)
    assert fatal is None
    assert load_issues == []
    assert documents[REVIEW_LOG_FILE] == [decision]


def test_evidence_ceiling_is_conservative_and_role_aware():
    self_report = synthetic_source("self", kind="interview_transcript", independence_review_state="unreviewed")
    document_a = synthetic_source("alpha")
    document_b = synthetic_source("bravo")

    assert (
        vb.evidence_ceiling(
            synthetic_claim([(self_report, "self_report")]), {self_report["source_occurrence_id"]: self_report}
        )
        == "self_reported"
    )
    assert (
        vb.evidence_ceiling(
            synthetic_claim([(document_a, "corroboration")]), {document_a["source_occurrence_id"]: document_a}
        )
        == "limited"
    )
    moderate = synthetic_claim([(document_a, "corroboration"), (document_b, "corroboration")])
    assert (
        vb.evidence_ceiling(moderate, {source["source_occurrence_id"]: source for source in (document_a, document_b)})
        == "moderate"
    )
    strong = synthetic_claim([(document_a, "authoritative"), (document_b, "corroboration")])
    assert (
        vb.evidence_ceiling(strong, {source["source_occurrence_id"]: source for source in (document_a, document_b)})
        == "strong"
    )


def test_interview_sources_remain_self_reported_even_when_edges_are_mislabeled():
    first = synthetic_source("interview-alpha", kind="interview_transcript")
    second = synthetic_source("interview-bravo", kind="interview_transcript")
    claim = synthetic_claim([(first, "authoritative"), (second, "corroboration")])
    sources = {source["source_occurrence_id"]: source for source in (first, second)}
    assert vb.evidence_ceiling(claim, sources) == "self_reported"

    documents = empty_documents()
    install_claim(documents, claim, [first, second])
    assert "invalid-self-report-role" in issue_codes(documents)


def test_duplicate_hashes_and_unknown_independence_do_not_multiply_support():
    shared_hash = "sha256:" + "d" * 64
    first = synthetic_source("alpha", content_hash=shared_hash)
    duplicate = synthetic_source("bravo", content_hash=shared_hash)
    unknown = synthetic_source("charlie", independence_review_state="unreviewed")

    duplicate_claim = synthetic_claim([(first, "corroboration"), (duplicate, "corroboration")])
    assert (
        vb.evidence_ceiling(duplicate_claim, {source["source_occurrence_id"]: source for source in (first, duplicate)})
        == "limited"
    )
    unknown_claim = synthetic_claim([(first, "corroboration"), (unknown, "corroboration")])
    assert (
        vb.evidence_ceiling(unknown_claim, {source["source_occurrence_id"]: source for source in (first, unknown)})
        == "limited"
    )

    shared_group = synthetic_source("delta", independence_group=first["independence_group"])
    shared_group_claim = synthetic_claim([(first, "corroboration"), (shared_group, "corroboration")])
    assert (
        vb.evidence_ceiling(
            shared_group_claim,
            {source["source_occurrence_id"]: source for source in (first, shared_group)},
        )
        == "limited"
    )

    derived = synthetic_source("echo")
    derived["derived_from_source_ids"] = [first["source_id"]]
    derived_claim = synthetic_claim([(first, "corroboration"), (derived, "corroboration")])
    assert (
        vb.evidence_ceiling(
            derived_claim,
            {source["source_occurrence_id"]: source for source in (first, derived)},
        )
        == "limited"
    )


def test_atomic_evidence_references_and_source_derivation_cycles_are_validated():
    documents = empty_documents()
    first = synthetic_source("alpha")
    second = synthetic_source("bravo")
    first["derived_from_source_ids"] = [second["source_id"]]
    second["derived_from_source_ids"] = [first["source_id"]]
    claim = synthetic_claim([(first, "corroboration")])
    claim["evidence_edges"][0]["source_occurrence_id"] = "occ-missing"
    install_claim(documents, claim, [first, second])

    codes = issue_codes(documents)
    assert "broken-evidence-reference" in codes
    assert "circular-source-derivation" in codes


def test_claim_dependency_cycle_is_rejected():
    documents = empty_documents()
    source = synthetic_source("alpha")
    first = synthetic_claim([(source, "corroboration")], claim_id="claim-alpha")
    second = synthetic_claim([(source, "corroboration")], claim_id="claim-bravo")
    first["depends_on_claim_ids"] = [second["claim_id"]]
    second["depends_on_claim_ids"] = [first["claim_id"]]
    documents["sources/source-manifest.json"]["sources"] = [source]
    documents["candidates/claims.json"]["claims"] = [first, second]
    assert {"claim-dependencies-not-supported", "circular-claim-dependency"} <= issue_codes(documents)


def test_approval_is_invalidated_by_wording_and_source_changes():
    source = synthetic_source("alpha")
    claim = synthetic_claim([(source, "corroboration")])
    approve_claim(claim, [source])
    documents = empty_documents()
    install_claim(documents, claim, [source])
    assert vb.validate_documents(documents) == []

    edited = copy.deepcopy(documents)
    edited["candidates/claims.json"]["claims"][0]["wording"] = "Changed after approval."
    assert "stale-approval" in issue_codes(edited)

    source_changed = copy.deepcopy(documents)
    source_changed["sources/source-manifest.json"]["sources"][0]["content_hash"] = "sha256:" + "f" * 64
    assert "stale-approval" in issue_codes(source_changed)

    evidence_changed = copy.deepcopy(documents)
    evidence_changed["candidates/claims.json"]["claims"][0]["evidence_edges"][0]["coordinate"] = "section changed"
    assert "stale-approval" in issue_codes(evidence_changed)


def test_latest_owner_retraction_overrides_inline_approval_and_records():
    source = synthetic_source("alpha")
    claim = synthetic_claim([(source, "corroboration")], visibility="public_candidate")
    approve_claim(claim, [source])
    documents = empty_documents()
    install_claim(documents, claim, [source])
    documents["publication/approved-records.json"]["records"] = [active_record(claim)]
    documents["publication/publication-manifest.json"].update(
        {"owner_review_state": "approved", "reviewed_at": "2026-01-02", "records": [public_record(claim)]}
    )
    documents[REVIEW_LOG_FILE] = [
        {
            "decision_id": "decision-retract-alpha",
            "claim_id": claim["claim_id"],
            "claim_revision": claim["revision"],
            "action": "retract",
            "evidence_graph_digest": claim["approval"]["evidence_graph_digest"],
            "decided_at": "2026-01-03",
        }
    ]

    codes = issue_codes(documents)
    assert {
        "approval-overridden-by-decision",
        "stale-approval",
        "stale-approved-record",
        "stale-publication-record",
    } <= codes


def test_publication_requires_exact_current_owner_approved_public_candidate():
    source = synthetic_source("alpha")
    claim = synthetic_claim([(source, "corroboration")], visibility="public_candidate")
    approve_claim(claim, [source])
    documents = empty_documents()
    install_claim(documents, claim, [source])
    documents["publication/approved-records.json"]["records"] = [active_record(claim)]
    documents["publication/publication-manifest.json"].update(
        {"owner_review_state": "approved", "reviewed_at": "2026-01-02", "records": [public_record(claim)]}
    )
    assert vb.validate_documents(documents) == []

    draft = copy.deepcopy(documents)
    draft["publication/publication-manifest.json"]["owner_review_state"] = "draft"
    assert "publication-not-owner-approved" in issue_codes(draft)

    candidate = copy.deepcopy(documents)
    candidate["publication/publication-manifest.json"]["records"][0]["state"] = "candidate"
    assert "publication-record-not-approved" in issue_codes(candidate)

    rewritten = copy.deepcopy(documents)
    rewritten["publication/publication-manifest.json"]["records"][0]["wording"] = "Composite rewrite."
    assert "public-wording-mismatch" in issue_codes(rewritten)


def test_private_claim_cannot_be_published_even_when_approved():
    source = synthetic_source("alpha")
    claim = synthetic_claim([(source, "corroboration")], visibility="private")
    approve_claim(claim, [source])
    documents = empty_documents()
    install_claim(documents, claim, [source])
    documents["publication/approved-records.json"]["records"] = [active_record(claim)]
    documents["publication/publication-manifest.json"].update(
        {"owner_review_state": "approved", "reviewed_at": "2026-01-02", "records": [public_record(claim)]}
    )
    assert "publication-ineligible" in issue_codes(documents)


def test_open_conflict_index_cannot_be_bypassed_by_omitting_claim_reverse_link():
    source = synthetic_source("alpha")
    claim = synthetic_claim([(source, "corroboration")], visibility="public_candidate")
    approve_claim(claim, [source])
    documents = empty_documents()
    install_claim(documents, claim, [source])
    documents["candidates/conflicts.json"]["conflicts"] = [
        {
            "conflict_id": "conflict-alpha",
            "claim_ids": [claim["claim_id"]],
            "summary": "Synthetic role conflict",
            "status": "open",
        }
    ]
    documents["publication/approved-records.json"]["records"] = [active_record(claim)]
    documents["publication/publication-manifest.json"].update(
        {"owner_review_state": "approved", "reviewed_at": "2026-01-02", "records": [public_record(claim)]}
    )

    codes = issue_codes(documents)
    assert {"asymmetric-conflict-reference", "publication-ineligible"} <= codes


def test_transcript_deletion_propagates_to_edge_approval_record_and_publication():
    transcript = synthetic_source("transcript", kind="interview_transcript", independence_review_state="unreviewed")
    claim = synthetic_claim([(transcript, "self_report")], visibility="public_candidate")
    approve_claim(claim, [transcript])
    documents = empty_documents()
    install_claim(documents, claim, [transcript])
    documents["publication/approved-records.json"]["records"] = [active_record(claim)]
    documents["publication/publication-manifest.json"].update(
        {"owner_review_state": "approved", "reviewed_at": "2026-01-02", "records": [public_record(claim)]}
    )

    deleted = documents["sources/source-manifest.json"]["sources"][0]
    deleted["lifecycle_state"] = "deleted"
    deleted["content_state"] = "deleted"
    codes = issue_codes(documents)
    assert {
        "stale-evidence-edge",
        "unsupported-claim",
        "stale-approval",
        "stale-approved-record",
        "stale-publication-record",
    } <= codes


def test_privacy_findings_never_echo_matched_value():
    documents = empty_documents()
    source = synthetic_source("alpha")
    canary = "ghp_" + "SYNTHETICCANARY000000000000"
    source["origin"] = f"owner-selected://credential/{canary}"
    documents["sources/source-manifest.json"]["sources"] = [source]

    findings = vb.validate_documents(documents)
    assert "privacy-possible-credential" in {finding.code for finding in findings}
    text_report = vb.report_text(findings)
    json_report = vb.report_json(findings)
    assert canary not in text_report
    assert canary not in json_report
    assert "possible-github-token" in text_report


def test_invalid_secret_shaped_identifier_is_not_echoed():
    documents = empty_documents()
    source = synthetic_source("alpha")
    canary = "ghp_" + "INVALIDIDENTIFIERCANARY000000"
    source["source_id"] = canary
    documents["sources/source-manifest.json"]["sources"] = [source]
    report = vb.report_text(vb.validate_documents(documents))
    assert "invalid-id" in report
    assert "privacy-possible-credential" in report
    assert canary not in report


def test_secret_shaped_object_key_is_redacted_from_field_path_and_reports():
    documents = empty_documents()
    source = synthetic_source("alpha")
    claim = synthetic_claim([(source, "corroboration")])
    canary = "ghp_" + "OBJECTKEYCANARY000000000000"
    claim["flags"][canary] = False
    install_claim(documents, claim, [source])

    findings = vb.validate_documents(documents)
    report = vb.report_text(findings)
    json_report = vb.report_json(findings)
    assert "privacy-possible-credential" in report
    assert "redacted-key" in report
    assert canary not in report
    assert canary not in json_report


def test_structured_type_errors_return_findings_instead_of_crashing():
    documents = empty_documents()
    source = synthetic_source("alpha")
    source["source_id"] = {"unexpected": "object"}
    source["source_occurrence_id"] = ["unexpected-list"]
    source["source_kind"] = {"unexpected": "object"}
    documents["sources/source-manifest.json"]["sources"] = [source]

    claim = synthetic_claim([])
    claim["claim_id"] = ["unexpected-list"]
    claim["category"] = {"unexpected": "object"}
    claim["evidence_edges"] = [
        {
            "edge_id": "edge-alpha",
            "source_occurrence_id": {"unexpected": "object"},
            "coordinate": "synthetic coordinate",
            "excerpt": "",
            "span_hash": "",
            "source_role": {"unexpected": "object"},
            "support": "supports",
            "status": "active",
        }
    ]
    documents["candidates/claims.json"]["claims"] = [claim]
    documents["publication/publication-manifest.json"]["owner_review_state"] = {"unexpected": "object"}

    findings = vb.validate_documents(documents)
    assert {"invalid-id", "invalid-enum", "broken-evidence-reference"} <= {finding.code for finding in findings}


def test_public_output_blocks_mailbox_addresses_and_raw_paths_without_echoing():
    documents = empty_documents()
    mailbox = "synthetic.person@example.invalid"
    raw_path = "/private/synthetic/transcript.md"
    documents["publication/publication-manifest.json"]["records"] = [
        {
            "publication_id": "publication-alpha",
            "record_id": "record-alpha",
            "wording": f"Contact {mailbox} using {raw_path}",
            "visibility": "public",
            "state": "candidate",
        }
    ]
    findings = vb.validate_documents(documents)
    codes = {finding.code for finding in findings}
    assert {"public-mailbox-address", "public-raw-path"} <= codes
    report = vb.report_text(findings)
    assert mailbox not in report
    assert raw_path not in report
