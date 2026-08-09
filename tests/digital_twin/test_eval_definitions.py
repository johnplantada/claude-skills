"""Deterministic guards over eval coverage; live model execution remains opt-in and paid."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVALS = json.loads(
    (ROOT / "plugins" / "digital-twin" / "skills" / "build-digital-twin" / "evals" / "evals.json").read_text()
)
SKILL_TEXT = (ROOT / "plugins" / "digital-twin" / "skills" / "build-digital-twin" / "SKILL.md").read_text()


def test_required_behavior_scenarios_are_present_with_deterministic_assertions():
    required = {
        "resume-only-honest-cold-start",
        "voice-interview-confirm-names-dates-metrics",
        "conflicting-role-descriptions",
        "strong-evidence-with-confidential-third-party-data",
        "broad-email-import-privacy-cost",
        "transcript-deletion-propagation",
        "impersonation-and-commitment-boundary",
    }
    evals = EVALS["evals"]
    assert {case["eval_name"] for case in evals} == required
    assert all(case["prompt"].strip() and case["expected_output"].strip() for case in evals)
    assert all(len(case["assertions"]) >= 5 for case in evals)

    assertions = " ".join(assertion for case in evals for assertion in case["assertions"]).lower()
    for invariant in (
        "model-processing disclosure",
        "one concise",
        "self_reported",
        "owner",
        "provenance",
        "conflict",
        "publication",
        "third-party",
        "deleted transcript",
        "impersonate",
    ):
        assert invariant in assertions


def test_trigger_cases_include_positive_requests_and_all_required_near_misses():
    cases = EVALS["trigger_cases"]
    assert sum(case["should_trigger"] for case in cases) >= 3
    assert {case.get("near_miss") for case in cases if not case["should_trigger"]} == {
        "ordinary resume editing",
        "industrial digital twin",
        "avatar creation",
        "voice cloning",
        "architecture review",
        "generic RAG implementation",
    }


def test_document_review_precedes_the_gap_driven_interview():
    assert SKILL_TEXT.index("### 2. Review the selected documents") < SKILL_TEXT.index(
        "### 4. Run the gap-driven interview"
    )
    cold_start = next(case for case in EVALS["evals"] if case["eval_name"] == "resume-only-honest-cold-start")
    assertions = " ".join(cold_start["assertions"]).lower()
    assert "before starting the interview" in assertions
    assert "documentary conflicts and coverage gaps" in assertions
