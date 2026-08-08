"""Shared plumbing for the behavior evals — one place for the claude -p mechanics.

Every behavior eval is the same shape: headless `claude -p` told to follow a skill,
stream-json transcript captured, mechanical assertions on it. The helpers here keep the
per-skill test files down to fixtures + assertions.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_MODEL = os.environ.get("CLAUDE_EVAL_MODEL", "sonnet")
TIMEOUT_S = 600

# `cd *` is needed because the skills tell the agent to run their scripts from the
# skill directory (`cd <skill>/scripts && python3 …`); a bare `Bash(python3 *)` prefix
# rule blocks that compound and stalls the run on a permission ask.
BASE_TOOLS = ["Read", "Glob", "Grep", "Bash(python3 *)", "Bash(cd *)", "Bash(ls *)"]


def run_skill_task(
    prompt: str, cwd: Path, extra_tools: list[str] | None = None
) -> tuple[int, str]:
    """One headless skill-following run; returns (exit code, full transcript text).

    stream-json + --verbose emits every message and tool call, so the captured stdout
    IS the transcript the assertions grep. --max-turns bounds cost.
    """
    proc = subprocess.run(
        [
            "claude", "-p", prompt,
            "--output-format", "stream-json", "--verbose",
            "--model", EVAL_MODEL,
            "--max-turns", "25",
            "--add-dir", str(ROOT),
            "--allowedTools", *BASE_TOOLS, *(extra_tools or []),
        ],
        capture_output=True, text=True, timeout=TIMEOUT_S, cwd=cwd,
        stdin=subprocess.DEVNULL,
    )
    return proc.returncode, proc.stdout + proc.stderr


def skill_prompt(skill: str, task: str) -> str:
    candidates = [ROOT / "skills" / skill / "SKILL.md", *ROOT.glob(f"plugins/*/skills/{skill}/SKILL.md")]
    skill_md = next((candidate for candidate in candidates if candidate.is_file()), candidates[0])
    return f"Read the skill at {skill_md} and follow it for this task: {task}"


def final_result(transcript: str) -> str:
    """The run's final answer text, from the stream-json `result` event ('' if absent)."""
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            return event.get("result") or ""
    return ""


def bash_commands(transcript: str) -> list[str]:
    """Every Bash command the agent actually EXECUTED (tool_use blocks), in order.

    Assertions about what the agent did (vs merely talked about) must look here — the
    final answer legitimately *mentions* commands it deliberately did not run.
    """
    commands: list[str] = []
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        content = (event or {}).get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Bash":
                commands.append(str(block.get("input", {}).get("command", "")))
    return commands
