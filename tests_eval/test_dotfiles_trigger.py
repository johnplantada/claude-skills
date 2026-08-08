"""Trigger eval for the dotfiles skill — does the DESCRIPTION route the right requests?

A skill's frontmatter description is its triggering mechanism. This eval presents the
model with the REAL roster (every skill's name + description parsed live from
skills/*/SKILL.md, so the eval always tests what actually ships) plus 12 realistic user
queries — 6 that should route to dotfiles and 6 near-misses that share vocabulary
(secrets, config files, chezmoi-adjacent tasks) but belong to a sibling skill or no
skill at all.

Three `claude -p` calls classify all queries and each query takes the MAJORITY verdict
(single-call routing is measurably flaky — observed pass/fail/pass across identical
runs); grading is then a mechanical comparison against trigger_evals.json. Aggregate
accuracy must clear `pass_threshold` (0.8) — a threshold rather than per-query asserts,
so the tier fails on regressions, not residual noise. The failure message lists exactly
which queries misrouted (with vote counts), so a red run is immediately actionable.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_MODEL = os.environ.get("CLAUDE_EVAL_MODEL", "sonnet")
EVALS = json.loads((Path(__file__).parent / "trigger_evals.json").read_text())

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)


def skill_roster() -> list[tuple[str, str]]:
    """(name, description) for every shipped skill, parsed from SKILL.md frontmatter."""
    roster: list[tuple[str, str]] = []
    skill_files = [*ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("plugins/*/skills/*/SKILL.md")]
    for skill_md in sorted(skill_files):
        m = _FRONTMATTER_RE.match(skill_md.read_text())
        if not m:
            continue
        fields = dict(
            line.split(":", 1)
            for line in m.group(1).splitlines()
            if ":" in line and not line.startswith(" ")
        )
        name = fields.get("name", "").strip()
        desc = fields.get("description", "").strip()
        if name and desc:
            roster.append((name, desc))
    return roster


def classification_prompt() -> str:
    roster = "\n".join(f"- {name}: {desc}" for name, desc in skill_roster())
    queries = "\n".join(f'{q["id"]}. {q["query"]}' for q in EVALS["queries"])
    return (
        "You are routing user requests to skills. Available skills:\n\n"
        f"{roster}\n\n"
        "For each numbered user request below, decide which ONE skill you would consult "
        "first to handle it, or \"none\" if no listed skill fits.\n\n"
        f"{queries}\n\n"
        "Reply with ONLY a JSON array, no prose, one object per request: "
        '[{"id": 1, "skill": "<skill-name-or-none>"}, ...]'
    )


def parse_verdicts(text: str) -> dict[int, str]:
    """id -> bare skill name. Models sometimes echo a plugin-qualified name
    (`devenv:dotfiles`); grading compares the bare final segment."""
    m = re.search(r"\[.*\]", text, re.DOTALL)
    assert m, f"no JSON array in model reply:\n{text}"
    return {
        int(v["id"]): str(v.get("skill", "none")).strip().lower().rsplit(":", 1)[-1]
        for v in json.loads(m.group(0))
    }


VOTES = 3


def one_classification_round() -> dict[int, str]:
    proc = subprocess.run(
        ["claude", "-p", classification_prompt(),
         "--output-format", "json", "--model", EVAL_MODEL, "--max-turns", "1"],
        capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL,
    )
    assert proc.returncode == 0, f"claude run failed:\n{proc.stderr[-2000:]}"
    return parse_verdicts(json.loads(proc.stdout).get("result", ""))


def test_trigger_routing_meets_threshold():
    rounds = [one_classification_round() for _ in range(VOTES)]

    misses: list[str] = []
    for q in EVALS["queries"]:
        votes_here = sum(r.get(q["id"]) == EVALS["skill_name"] for r in rounds)
        routed_here = votes_here * 2 > VOTES  # majority
        if routed_here != q["should_trigger"]:
            got = [r.get(q["id"], "(missing)") for r in rounds]
            want = EVALS["skill_name"] if q["should_trigger"] else f"not {EVALS['skill_name']}"
            misses.append(f'  q{q["id"]} -> {got} (wanted {want}): {q["query"][:70]}')

    accuracy = 1 - len(misses) / len(EVALS["queries"])
    assert accuracy >= EVALS["pass_threshold"], (
        f"trigger accuracy {accuracy:.0%} below threshold {EVALS['pass_threshold']:.0%} "
        f"(majority of {VOTES} votes/query); misroutes:\n" + "\n".join(misses)
    )
