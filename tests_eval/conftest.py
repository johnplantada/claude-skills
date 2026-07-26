"""Gate for the LLM eval tier.

These tests spawn real `claude -p` runs — they cost tokens and take minutes, so they
never run implicitly. Two conditions to run:

    RUN_SKILL_EVALS=1 python3 -m pytest tests_eval -q

  1. RUN_SKILL_EVALS=1 in the environment (the explicit opt-in), and
  2. the `claude` CLI on PATH.

Model defaults to `sonnet`; override with CLAUDE_EVAL_MODEL (e.g. `haiku` for a cheap
smoke of the harness itself, or an exact model id to pin grading across time).
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

import pytest

RESULTS_DIR = Path(__file__).parent / "results"
_outcomes: dict[str, str] = {}


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_SKILL_EVALS") != "1":
        skip = pytest.mark.skip(reason="LLM evals are opt-in: set RUN_SKILL_EVALS=1")
        for item in items:
            item.add_marker(skip)
    elif shutil.which("claude") is None:
        skip = pytest.mark.skip(reason="claude CLI not on PATH")
        for item in items:
            item.add_marker(skip)


def pytest_runtest_logreport(report):
    if report.when == "call":
        _outcomes[report.nodeid] = report.outcome


def pytest_sessionfinish(session, exitstatus):
    """Provenance: an eval pass is only meaningful with the model + date attached.

    Every non-skipped run appends a results file (gitignored — local artifacts, not
    fixtures), so "the evals passed" is a checkable record, not a memory.
    """
    if not _outcomes:
        return
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    record = {
        "timestamp_utc": stamp,
        "model": os.environ.get("CLAUDE_EVAL_MODEL", "sonnet"),
        "outcomes": dict(sorted(_outcomes.items())),
    }
    (RESULTS_DIR / f"{stamp}.json").write_text(json.dumps(record, indent=2) + "\n")
