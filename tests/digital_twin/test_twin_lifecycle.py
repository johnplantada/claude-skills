"""Private snapshot, career-assistant, feedback, and maintenance lifecycle tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import career_twin as ct
import compile_private_snapshot as cps
import init_workspace as iw
import migrate_workspace as mw
import update_bundle as ub
import validate_bundle as vb
from _bundle_common import CURRENT_STATE_FILE, POLICY_VERSION, SCHEMA_VERSION, TEMPLATE_FILES


def source_record(content: bytes) -> dict[str, Any]:
    return {
        "source_id": "source-resume",
        "source_occurrence_id": "occ-resume-original",
        "supersedes_occurrence_id": "",
        "observed_at": "2026-01-01T00:00:00Z",
        "owner_title": "Synthetic resume",
        "origin": "owner-selected://resume",
        "media_type": "text/plain",
        "source_kind": "document",
        "content_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
        "derived_from_source_ids": [],
        "independence_group": "group-resume",
        "independence_review_state": "owner_confirmed",
        "authorship": "owner",
        "confidentiality": "private",
        "third_party_content": "none",
        "processing_purpose": "synthetic lifecycle test",
        "retention_preference": "owner_managed",
        "processing_consent": "confirmed",
        "publication_rights": "restricted",
        "lifecycle_state": "active",
        "content_state": "external",
    }


def approved_claim(source: dict[str, Any]) -> dict[str, Any]:
    claim = {
        "claim_id": "claim-delivery",
        "revision": 1,
        "wording": "The owner delivered Project Atlas.",
        "category": "accomplishment",
        "dates": [],
        "entities": ["Project Atlas"],
        "evidence_edges": [
            {
                "edge_id": "edge-resume-delivery",
                "source_occurrence_id": source["source_occurrence_id"],
                "coordinate": "experience item one",
                "excerpt": "",
                "span_hash": "",
                "source_role": "corroboration",
                "support": "supports",
                "status": "active",
            }
        ],
        "depends_on_claim_ids": [],
        "proposed_strength": "limited",
        "max_strength": "limited",
        "uncertainty": [],
        "conflicts": [],
        "flags": {"privacy": False, "third_party": False, "contact_authorized": False},
        "metric": None,
        "visibility": "internal",
        "confidentiality": "private",
        "publication_rights": "restricted",
        "review_state": "approved",
        "approval": None,
    }
    digest = vb.evidence_graph_digest(claim, {source["source_occurrence_id"]: source})
    claim["approval"] = {
        "exact_wording": claim["wording"],
        "claim_revision": claim["revision"],
        "evidence_graph_digest": digest,
        "approved_strength": "limited",
        "visibility": "internal",
        "confidentiality": "private",
        "publication_rights": "restricted",
        "metric": None,
        "reviewed_at": "2026-01-01",
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
    }
    return claim


def install_approved_workspace(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "private-twin"
    source_file = tmp_path / "resume.txt"
    source_file.write_bytes(b"original synthetic resume")
    assert iw.main([str(workspace)]) == 0
    source = source_record(source_file.read_bytes())
    claim = approved_claim(source)
    (workspace / "sources/source-manifest.json").write_text(
        json.dumps(
            {
                "schema": "digital-twin/source-manifest",
                "schema_version": SCHEMA_VERSION,
                "policy_version": POLICY_VERSION,
                "sources": [source],
            }
        )
    )
    (workspace / "candidates/claims.json").write_text(
        json.dumps(
            {
                "schema": "digital-twin/claims",
                "schema_version": SCHEMA_VERSION,
                "policy_version": POLICY_VERSION,
                "claims": [claim],
            }
        )
    )
    (workspace / "publication/approved-records.json").write_text(
        json.dumps(
            {
                "schema": "digital-twin/approved-records",
                "schema_version": SCHEMA_VERSION,
                "policy_version": POLICY_VERSION,
                "records": [
                    {
                        "record_id": "record-delivery",
                        "claim_id": claim["claim_id"],
                        "claim_revision": 1,
                        "wording": claim["wording"],
                        "evidence_strength": "limited",
                        "visibility": "internal",
                        "approval_digest": claim["approval"]["evidence_graph_digest"],
                        "state": "active",
                    }
                ],
            }
        )
    )
    assert vb.main([str(workspace)]) == 0
    return workspace, source_file


def test_compile_query_and_feedback_preserve_the_mutation_boundary(tmp_path: Path, capsys):
    workspace, _source_file = install_approved_workspace(tmp_path)
    capsys.readouterr()

    assert cps.main([str(workspace), "--format", "json"]) == 0
    compiled = json.loads(capsys.readouterr().out)
    state_before = json.loads((workspace / CURRENT_STATE_FILE).read_text())
    claims_before = (workspace / "candidates/claims.json").read_bytes()
    assert state_before["serving_state"] == "ready"
    assert compiled["record_count"] == 1

    assert ct.main(["query", str(workspace), "What did I deliver?", "--format", "json"]) == 0
    response = json.loads(capsys.readouterr().out)
    assert response["record_ids"] == ["record-delivery"]
    assert response["snapshot_id"] == compiled["snapshot_id"]
    assert response["abstained"] is False

    assert (
        ct.main(
            [
                "feedback",
                str(workspace),
                "--response-id",
                response["response_id"],
                "--category",
                "outdated",
                "--record-id",
                "record-delivery",
                "--confirm",
                "--format",
                "json",
            ]
        )
        == 0
    )
    feedback_report = json.loads(capsys.readouterr().out)
    feedback = json.loads((workspace / "feedback/owner-inbox.jsonl").read_text().strip())
    assert feedback["feedback_id"] == feedback_report["feedback_id"]
    assert feedback["status"] == "new"
    assert (workspace / "candidates/claims.json").read_bytes() == claims_before
    assert json.loads((workspace / CURRENT_STATE_FILE).read_text()) == state_before


def test_snapshot_integrity_report_does_not_expose_workspace_path(tmp_path: Path, capsys):
    workspace, _source_file = install_approved_workspace(tmp_path)
    capsys.readouterr()
    assert cps.main([str(workspace)]) == 0
    capsys.readouterr()
    state = json.loads((workspace / CURRENT_STATE_FILE).read_text())
    records_path = workspace / "snapshots" / state["current_private_snapshot_id"] / "records.json"
    records = json.loads(records_path.read_text())
    records["records"] = []
    records_path.write_text(json.dumps(records))

    assert vb.main([str(workspace), "--format", "json"]) == 1
    report = capsys.readouterr().out
    assert "snapshot-integrity-failure" in report
    assert str(workspace) not in report


def test_changed_source_apply_blocks_serving_and_invalidates_dependencies(tmp_path: Path, capsys):
    workspace, source_file = install_approved_workspace(tmp_path)
    assert cps.main([str(workspace)]) == 0
    capsys.readouterr()
    source_file.write_bytes(b"changed synthetic resume")

    assert (
        ub.main(
            [
                "plan",
                str(workspace),
                "--source-id",
                "source-resume",
                "--file",
                str(source_file),
                "--format",
                "json",
            ]
        )
        == 0
    )
    plan_report = json.loads(capsys.readouterr().out)
    assert plan_report["status"] == "changed"
    assert str(source_file) not in json.dumps(plan_report)

    assert ub.main(["apply", str(workspace), "--plan", plan_report["update_id"], "--confirm", "--format", "json"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["status"] == "awaiting_owner_review"
    state = json.loads((workspace / CURRENT_STATE_FILE).read_text())
    assert state["serving_state"] == "review_required"
    assert state["blocked_record_ids"] == ["record-delivery"]

    sources = json.loads((workspace / "sources/source-manifest.json").read_text())["sources"]
    assert len(sources) == 2
    assert sources[-1]["source_id"] == "source-resume"
    assert sources[-1]["supersedes_occurrence_id"] == "occ-resume-original"
    claim = json.loads((workspace / "candidates/claims.json").read_text())["claims"][0]
    assert claim["review_state"] == "pending"
    assert claim["approval"] is None
    assert claim["evidence_edges"][0]["status"] == "stale"
    record = json.loads((workspace / "publication/approved-records.json").read_text())["records"][0]
    assert record["state"] == "stale"

    assert ct.main(["query", str(workspace), "What did I deliver?"]) == 1
    assert "snapshot_unavailable" in capsys.readouterr().out


def test_apply_refuses_source_changed_after_plan_without_blocking_serving(tmp_path: Path, capsys):
    workspace, source_file = install_approved_workspace(tmp_path)
    assert cps.main([str(workspace)]) == 0
    capsys.readouterr()
    source_file.write_bytes(b"first changed version")
    assert ub.main(["plan", str(workspace), "--source-id", "source-resume", "--file", str(source_file)]) == 0
    update_id = capsys.readouterr().out.split("update_id=", 1)[1].split("\t", 1)[0]
    source_file.write_bytes(b"second changed version")

    assert ub.main(["apply", str(workspace), "--plan", update_id, "--confirm"]) == 1
    assert "selected source changed after planning" in capsys.readouterr().err
    state = json.loads((workspace / CURRENT_STATE_FILE).read_text())
    assert state["serving_state"] == "ready"
    assert len(json.loads((workspace / "sources/source-manifest.json").read_text())["sources"]) == 1


def test_unchanged_source_is_idempotent_noop_and_lock_refusal_is_non_mutating(tmp_path: Path, capsys):
    workspace, source_file = install_approved_workspace(tmp_path)
    assert cps.main([str(workspace)]) == 0
    capsys.readouterr()
    assert ub.main(["plan", str(workspace), "--source-id", "source-resume", "--file", str(source_file)]) == 0
    plan_output = capsys.readouterr().out
    update_id = plan_output.split("update_id=", 1)[1].split("\t", 1)[0]
    assert "status=unchanged" in plan_output

    lock = workspace / "locks/update.lock"
    lock.write_text("update-competing\n")
    state_before = (workspace / CURRENT_STATE_FILE).read_bytes()
    assert ub.main(["apply", str(workspace), "--plan", update_id, "--confirm"]) == 1
    assert "another update holds" in capsys.readouterr().err
    assert (workspace / CURRENT_STATE_FILE).read_bytes() == state_before
    lock.unlink()

    assert ub.main(["apply", str(workspace), "--plan", update_id, "--confirm", "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "completed"
    assert len(json.loads((workspace / "sources/source-manifest.json").read_text())["sources"]) == 1
    assert json.loads((workspace / CURRENT_STATE_FILE).read_text())["serving_state"] == "ready"

    assert ub.main(["apply", str(workspace), "--plan", update_id, "--confirm", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"


def test_explicit_migration_invalidates_legacy_approvals_and_creates_state(tmp_path: Path, capsys):
    workspace, _source_file = install_approved_workspace(tmp_path)
    capsys.readouterr()
    for relative in TEMPLATE_FILES:
        if relative == CURRENT_STATE_FILE:
            continue
        path = workspace / relative
        document = json.loads(path.read_text())
        document["schema_version"] = "0.1.0"
        if "policy_version" in document:
            document["policy_version"] = "0.1.0"
        path.write_text(json.dumps(document))
    source = json.loads((workspace / "sources/source-manifest.json").read_text())
    source["sources"][0].pop("supersedes_occurrence_id")
    source["sources"][0].pop("observed_at")
    (workspace / "sources/source-manifest.json").write_text(json.dumps(source))
    (workspace / CURRENT_STATE_FILE).unlink()

    assert mw.main([str(workspace), "--confirm", "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "migrated"
    assert report["invalidated_approvals"] == 1
    state = json.loads((workspace / CURRENT_STATE_FILE).read_text())
    assert state["schema_version"] == SCHEMA_VERSION
    assert state["serving_state"] == "uncompiled"
    claim = json.loads((workspace / "candidates/claims.json").read_text())["claims"][0]
    assert claim["review_state"] == "pending"
    assert claim["approval"] is None
    assert vb.main([str(workspace)]) == 0
