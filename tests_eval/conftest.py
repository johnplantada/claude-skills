"""Gate direct skill-following evals; an opted-in run must execute tests.

RUN_SKILL_EVALS=1 and a claude CLI on PATH are required. Real evals spend tokens;
unit tests of this reporting code use synthetic reports and never call a model.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
import uuid
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(__file__).parent / "results"
_outcomes: dict[str, str] = {}
_executed: set[str] = set()
_eval_nodeids: set[str] = set()


def pytest_collection_modifyitems(config, items):
    items = [item for item in items if Path(item.path).resolve().is_relative_to(Path(__file__).resolve().parent)]
    _eval_nodeids.update(item.nodeid for item in items)
    if os.environ.get("RUN_SKILL_EVALS") != "1":
        skip = pytest.mark.skip(reason="LLM evals are opt-in: set RUN_SKILL_EVALS=1")
        for item in items:
            item.add_marker(skip)
    elif shutil.which("claude") is None:
        skip = pytest.mark.skip(reason="claude CLI not on PATH")
        for item in items:
            item.add_marker(skip)


def pytest_runtest_logreport(report):
    if report.nodeid not in _eval_nodeids:
        return
    if report.when == "call":
        _executed.add(report.nodeid)
        # A skip inside the test body is not an executed behavior assertion.
        if report.skipped:
            _executed.discard(report.nodeid)
    # Preserve a failure even if a later phase reports a different outcome.
    if (report.when == "call" or report.failed or report.skipped) and _outcomes.get(report.nodeid) != "failed":
        _outcomes[report.nodeid] = report.outcome


def command_output(argv: list[str], cwd: Path | None = None) -> str | None:
    """Bounded provenance lookup; unavailable metadata never becomes a pass."""
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def pytest_sessionfinish(session, exitstatus):
    """Always retain opt-in receipts, including all-skipped and collection failures."""
    if os.environ.get("RUN_SKILL_EVALS") != "1":
        return
    if not _executed and exitstatus == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    effective_status = int(session.exitstatus)
    cli = shutil.which("claude")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    git_status = command_output(["git", "status", "--porcelain"], ROOT)
    record = {
        "timestamp_utc": stamp,
        "verification_scope": "direct-skill-following; installed-plugin routing/hooks unverified",
        "model": os.environ.get("CLAUDE_EVAL_MODEL", "sonnet"),
        "git_sha": command_output(["git", "rev-parse", "HEAD"], ROOT),
        "git_dirty": None if git_status is None else bool(git_status),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "claude_cli_path": cli,
        "claude_cli_version": command_output([cli, "--version"]) if cli else None,
        "collected": len(_eval_nodeids),
        "executed": len(_executed),
        "counts": {key: Counter(_outcomes.values())[key] for key in ("passed", "failed", "skipped")},
        "exit_status": effective_status,
        "status": "not_executed" if not _executed else ("passed" if effective_status == 0 else "failed"),
        "outcomes": dict(sorted(_outcomes.items())),
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    receipt = RESULTS_DIR / f"{stamp}-{uuid.uuid4().hex[:8]}.json"
    receipt.write_text(json.dumps(record, indent=2) + "\n")
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter:
        reporter.write_sep("=", f"evals: {record['status']}; executed={len(_executed)}, "
                           f"skipped={record['counts']['skipped']}; receipt={receipt}")
