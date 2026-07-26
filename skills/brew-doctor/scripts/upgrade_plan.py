#!/usr/bin/env python3
"""Read-only, PLAN-ONLY gated upgrade planner. Part of the brew-doctor skill.

Turns `brew outdated` into a gated plan: snapshots current versions to a TEMP file,
flags fragile / major-version bumps (from config + a built-in heuristic), separates
already-pinned (auto-skipped) from safe-to-upgrade, and PRINTS the command sequence
to run — it does NOT run `brew update/upgrade/pin/cleanup`. You review the plan, then
run the commands yourself after confirming.

Usage:
    upgrade_plan.py              # plan for all outdated formulae + casks

Fragile set = config.toml [brew-doctor] pinned + built-in (editors, LSPs, databases,
runtimes) + any bump that crosses a major version. Fragile & unpinned => the plan
proposes `brew pin` BEFORE upgrading, so it can't bump unattended.
"""

from __future__ import annotations

import re
import sys
import tempfile

import _brew_common as bc

# Built-in version-sensitive keywords whose config commonly breaks on a major bump.
FRAGILE_BUILTIN = [
    "neovim", "vim", "postgresql", "mongodb", "mysql", "redis", "node", "python",
    "ruby", "go", "rust", "lua-language-server", "gopls", "pyright", "rust-analyzer", "terraform",
]


# --- pure helpers ------------------------------------------------------------

def is_fragile(name: str, fragile: list[str]) -> bool:
    """Case-insensitive substring match of `name` against the fragile set."""
    lower = name.lower()
    return any(tok.lower() in lower for tok in fragile)


def major(version: str) -> str:
    """Major component: strip a leading `v`, then everything from the first `._-`."""
    version = re.sub(r"^v", "", version)
    return re.sub(r"[._-].*$", "", version)


def parse_outdated_line(line: str) -> tuple[str, str, str]:
    """Parse a `brew outdated --verbose` line -> (name, old, new).

    Formulae print `name (old) < new`; CASKS print `name (old) != new`. Splitting on
    `< ` alone left `new` empty for casks, and an empty new version compares unequal to
    any old major — manufacturing a phantom "major-bump" verdict. Accept both separators.
    """
    name = line.split()[0] if line.split() else ""
    m = re.match(r"^[^(]*\(([^)]*)\)", line)
    old = m.group(1) if m else line
    after = re.split(r" (?:<|!=) ", line, maxsplit=1)
    new = after[1].split()[0] if len(after) > 1 and after[1].split() else ""
    return name, old, new


def classify(
    name: str, old: str, new: str, pinned: list[str], fragile: list[str]
) -> tuple[str, str]:
    """Classify one outdated formula: return (category, plan_line).

    category is 'gated' (already pinned), 'to_pin' (fragile/major & unpinned), or 'safe'.
    """
    flags = ""
    if major(old) != major(new):
        flags = "major-bump"
    if is_fragile(name, fragile):
        flags = f"{flags},fragile" if flags else "fragile"

    if name in pinned:
        line = f"  plan: {name}\t{old} -> {new}\tPINNED — auto-skipped by `brew upgrade` (gated ✅)"
        return "gated", line
    if flags:
        line = f"  plan: {name}\t{old} -> {new}\t{flags} — UNPINNED: pin before upgrading"
        return "to_pin", line
    line = f"  plan: {name}\t{old} -> {new}\tsafe to upgrade"
    return "safe", line


def count_nonempty(text: str) -> int:
    """Number of non-empty lines — the `grep -c .` count."""
    return sum(1 for line in text.splitlines() if line)


def join_trailing(lines: list[str], default: str) -> str:
    """Join lines the way `tr '\\n' ' '` does, or `default` when empty."""
    if not lines:
        return default
    return "".join(f"{line} " for line in lines)


def build_commands(
    to_pin: list[str], safe: list[str], has_out: bool, has_cout: bool, snap: str
) -> list[str]:
    """The recommended (but NOT executed) command sequence."""
    out = ["", "== recommended commands (review, then run yourself) =="]
    out.append("brew update                      # refresh metadata first (this plan used cached data)")
    if to_pin:
        out.append(
            "brew pin" + "".join(f" {n}" for n in to_pin) + "   # gate fragile/major bumps before upgrading"
        )
    if safe:
        out.append("brew upgrade" + "".join(f" {n}" for n in safe) + "   # upgrade the safe ones by name")
    if not safe and not to_pin and has_out:
        out.append("# all outdated formulae are already pinned — nothing to upgrade unattended")
    if has_cout:
        out.append("brew upgrade --cask <cask>       # casks individually; skip self-updating ones")
    out.append(f"brew doctor && diff <(brew list --versions) {snap}   # verify: what actually changed")
    out.append("# then drive any upgraded editor/runtime (chain nvim-config / shell-sync verify),")
    out.append("# and: brew autoremove && brew cleanup   (confirm the autoremove list first)")
    return out


# --- main (I/O via _brew_common) ---------------------------------------------

def main(argv: list[str] | None = None) -> int:
    if not bc.brew_available():
        print("upgrade-plan: brew not on PATH", file=sys.stderr)
        return 3

    with tempfile.NamedTemporaryFile(
        mode="w", prefix="brew_versions.", delete=False
    ) as snap_file:
        snap_file.write(bc.brew("list", "--versions"))
        snap = snap_file.name

    out: list[str] = [f"snapshot\t{snap}"]

    pinned = bc.brew("list", "--pinned").split()
    out.append(f"currently_pinned\t{join_trailing(pinned, '(none)')}")

    fragile = FRAGILE_BUILTIN + bc.config_array("brew-doctor", "pinned").split()

    # `--formula` matters: a bare `brew outdated --verbose` lists casks too, so a cask
    # would land in the FORMULA plan and be told to `brew pin` — which only works on
    # formulae. Casks get their own section below.
    outdated = bc.brew("outdated", "--verbose", "--formula")
    out.append(f"outdated_formulae\t{count_nonempty(outdated)}")

    to_pin: list[str] = []
    safe: list[str] = []
    for line in outdated.splitlines():
        if not line:
            continue
        name, old, new = parse_outdated_line(line)
        if not (name and old and new):
            # A blank field means an unrecognized format variant. Reporting it beats
            # classifying on a blank — that is precisely how a missing cask version
            # became a phantom "major-bump" with impossible `brew pin` advice.
            out.append(bc.unparsed_line(line, "unrecognized `brew outdated` format"))
            continue
        category, plan_line = classify(name, old, new, pinned, fragile)
        out.append(plan_line)
        if category == "to_pin":
            to_pin.append(name)
        elif category == "safe":
            safe.append(name)

    cout = [ln for ln in bc.brew("outdated", "--cask").splitlines() if ln]
    out.append(f"outdated_casks\t{len(cout)}")
    out.extend(f"  outdated_cask: {line}" for line in cout)

    out.extend(build_commands(to_pin, safe, bool(count_nonempty(outdated)), bool(cout), snap))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
