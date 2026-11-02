"""Run the shipped hook commands from a plugin path containing spaces.

Only disposable synthetic fixtures are used. No Claude session or model is started.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def packaged(tmp_path):
    plugin = tmp_path / "plugin with spaces"
    shutil.copytree(ROOT / "scripts", plugin / "scripts")
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    (binary_dir / "python3").symlink_to(sys.executable)
    return plugin, binary_dir


def run_hook(packaged, event, payload):
    plugin, binary_dir = packaged
    config = json.loads((ROOT / "hooks/hooks.json").read_text())
    command = config["hooks"][event][0]["hooks"][0]["command"]
    return subprocess.run(
        ["/bin/sh", "-c", command], input=payload, text=True, capture_output=True, timeout=5,
        env={"PATH": str(binary_dir), "CLAUDE_PLUGIN_ROOT": str(plugin)},
    )


@pytest.mark.parametrize("tool", ["Read", "Grep", "Bash"])
def test_packaged_guard_denies_synthetic_secret_path(packaged, tool):
    plugin, _ = packaged
    key = plugin / "synthetic home" / ".ssh" / "id_ed25519"
    key.parent.mkdir(parents=True)
    marker = "FAKE-CANARY-CONTENT-ONLY"
    key.write_text(marker)
    tool_input = {"Read": {"file_path": str(key)}, "Grep": {"path": str(key)},
                  "Bash": {"command": f"cat '{key}'"}}[tool]
    proc = run_hook(packaged, "PreToolUse", json.dumps({"tool_name": tool, "tool_input": tool_input}))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert marker not in proc.stdout + proc.stderr
    assert key.read_text() == marker


def test_packaged_guard_allows_public_key_and_fails_open_on_bad_input(packaged):
    for payload in ["not-json", json.dumps({"tool_name": "Read", "tool_input": {
        "file_path": str(packaged[0] / ".ssh" / "id_ed25519.pub")}})]:
        proc = run_hook(packaged, "PreToolUse", payload)
        assert proc.returncode == 0
        assert proc.stdout == ""


def test_packaged_stop_with_missing_chezmoi_is_silent(packaged):
    proc = run_hook(packaged, "Stop", "{}")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""


def test_packaged_stop_reports_synthetic_drift(packaged):
    _, binary_dir = packaged
    fake = binary_dir / "chezmoi"
    fake.write_text("#!/bin/sh\nprintf ' M .synthetic-config\\n'\n")
    fake.chmod(0o755)
    proc = run_hook(packaged, "Stop", "{}")
    assert proc.returncode == 0, proc.stderr
    message = json.loads(proc.stdout)["systemMessage"]
    assert "1 chezmoi-managed" in message and ".synthetic-config" in message


def test_packaged_hooks_require_python_on_path(packaged):
    (packaged[1] / "python3").unlink()
    proc = run_hook(packaged, "PreToolUse", "{}")
    assert proc.returncode != 0
    assert "python3" in proc.stderr and "not found" in proc.stderr


@pytest.mark.parametrize("script", ["skills/ghostty-config/scripts/show_effective.py",
                                    "skills/nvim-config/scripts/nvim_lua.py"])
def test_representative_missing_tool_through_single_skill_symlink(tmp_path, script):
    source = ROOT / script
    link = tmp_path / "consumer-skill"
    link.symlink_to(source.parent.parent, target_is_directory=True)
    proc = subprocess.run([sys.executable, str(link / "scripts" / source.name)],
                          text=True, capture_output=True, timeout=5,
                          env={"PATH": os.devnull, "XDG_CONFIG_HOME": str(tmp_path / "config")})
    assert proc.returncode == 3
    assert "not on PATH" in proc.stderr
    assert "Traceback" not in proc.stderr
