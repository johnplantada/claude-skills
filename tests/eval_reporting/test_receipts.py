"""Synthetic eval reporting regressions: no Claude process or paid model calls."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def harness(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / "tests_eval" / "conftest.py"
    spec = importlib.util.spec_from_file_location("eval_reporting_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._eval_nodeids.update({"a", "b"})
    monkeypatch.setenv("RUN_SKILL_EVALS", "1")
    monkeypatch.setattr(module, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    monkeypatch.setattr(module, "command_output", lambda *args: None)
    return module


def session(collected=2, status=0):
    return SimpleNamespace(testscollected=collected, exitstatus=status,
                           config=SimpleNamespace(pluginmanager=SimpleNamespace(get_plugin=lambda name: None)))


def report(harness, nodeid, when="call", outcome="passed"):
    harness.pytest_runtest_logreport(SimpleNamespace(
        nodeid=nodeid, when=when, outcome=outcome,
        failed=outcome == "failed", skipped=outcome == "skipped"))


def receipt(harness):
    return json.loads(next(harness.RESULTS_DIR.glob("*.json")).read_text())


def test_all_skipped_is_not_a_pass(harness):
    report(harness, "a", "setup", "skipped")
    report(harness, "b", "setup", "skipped")
    run = session()
    harness.pytest_sessionfinish(run, 0)
    result = receipt(harness)
    assert run.exitstatus == 1
    assert result["status"] == "not_executed"
    assert result["executed"] == 0
    assert result["counts"] == {"passed": 0, "failed": 0, "skipped": 2}
    assert result["claude_cli_version"] is None


def test_mixed_pass_and_skip_preserves_counts_and_provenance(harness, monkeypatch):
    monkeypatch.setattr(harness.shutil, "which", lambda name: "/synthetic/claude")
    monkeypatch.setattr(harness, "command_output", lambda argv, *args: {
        "status": " M README.md", "rev-parse": "a" * 40, "--version": "synthetic-cli 1.0"
    }[argv[1]])
    report(harness, "a")
    report(harness, "b", "setup", "skipped")
    run = session()
    harness.pytest_sessionfinish(run, 0)
    result = receipt(harness)
    assert result["status"] == "passed"
    assert result["counts"]["skipped"] == 1
    assert result["executed"] == 1
    assert result["git_sha"] == "a" * 40
    assert result["git_dirty"] is True
    assert result["claude_cli_version"] == "synthetic-cli 1.0"
    assert result["python_version"] and result["platform"]
    assert "installed-plugin" in result["verification_scope"]


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_failures_keep_nonzero_status(harness, phase):
    if phase == "teardown":
        report(harness, "a")
    report(harness, "a", phase, "failed")
    run = session(status=1)
    harness.pytest_sessionfinish(run, 1)
    assert run.exitstatus == 1
    assert receipt(harness)["counts"]["failed"] == 1


def test_skip_inside_test_is_not_execution(harness):
    report(harness, "a", outcome="skipped")
    run = session(collected=1)
    harness.pytest_sessionfinish(run, 0)
    assert run.exitstatus == 1
    assert receipt(harness)["executed"] == 0


def test_collection_error_is_preserved_and_receipt_does_not_collide(harness):
    run = session(collected=0, status=2)
    harness.pytest_sessionfinish(run, 2)
    harness.pytest_sessionfinish(run, 2)
    assert run.exitstatus == 2
    assert len(list(harness.RESULTS_DIR.glob("*.json"))) == 2


def test_no_opt_in_does_not_fail_or_write_receipt(harness, monkeypatch):
    monkeypatch.delenv("RUN_SKILL_EVALS")
    run = session()
    harness.pytest_sessionfinish(run, 0)
    assert run.exitstatus == 0
    assert not harness.RESULTS_DIR.exists()


def test_non_eval_reports_do_not_satisfy_execution(harness):
    report(harness, "tests/unit.py::test_unrelated")
    report(harness, "a", "setup", "skipped")
    run = session()
    harness.pytest_sessionfinish(run, 0)
    result = receipt(harness)
    assert run.exitstatus == 1
    assert result["executed"] == 0
    assert "tests/unit.py::test_unrelated" not in result["outcomes"]


def test_real_pytest_mixed_suite_missing_cli(tmp_path):
    """Exercise pytest's actual lifecycle with fake tests and an empty CLI PATH."""
    source = Path(__file__).resolve().parents[2] / "tests_eval" / "conftest.py"
    eval_dir = tmp_path / "tests_eval"
    eval_dir.mkdir()
    (eval_dir / "conftest.py").write_text(source.read_text())
    (eval_dir / "test_synthetic.py").write_text("def test_eval(): assert True\n")
    (tmp_path / "test_unit.py").write_text("def test_unit(): assert True\n")
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-c", str(tmp_path / "pytest.ini"), str(tmp_path)],
        cwd=tmp_path, capture_output=True, text=True, timeout=20,
        env={**os.environ, "PATH": str(tmp_path / "empty-path"),
             "RUN_SKILL_EVALS": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "1 passed, 1 skipped" in proc.stdout
    result = json.loads(next((eval_dir / "results").glob("*.json")).read_text())
    assert result["collected"] == 1
    assert result["executed"] == 0
    assert result["counts"] == {"passed": 0, "failed": 0, "skipped": 1}
    assert result["status"] == "not_executed"
