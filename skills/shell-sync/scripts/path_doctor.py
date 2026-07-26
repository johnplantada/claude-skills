#!/usr/bin/env python3
"""Audit one shell's resolved PATH: duplicates (in order), dead entries
(directories that don't exist), and installed-but-not-on-PATH tool dirs.

Collapses the awk/``[ -d ]``/usual-suspects loops the path workflow re-derives.
Default shell = zsh. Read-only; changes nothing. Part of the shell-sync skill.

Usage:
    path_doctor.py [zsh|fish] [--plan]

    path_doctor.py              # audit zsh's PATH, print findings
    path_doctor.py fish         # audit fish's PATH
    path_doctor.py --plan       # + emit a deduped, dead-stripped PATH as a repair PLAN (stdout only)

Findings are greppable, stable order:
    entry<TAB>NN<TAB>/dir              every PATH entry, in order
    dup<TAB>/dir                       appears more than once (keep first)
    dead<TAB>/dir                      directory does not exist (dead/placeholder)
    missing_tool_dir<TAB>/dir<TAB>N    exists w/ N execs but NOT on PATH
--plan prints, to stdout only, the cleaned ordered PATH — it NEVER writes any
config file. Apply it yourself after review.
"""

from __future__ import annotations

import os
import sys
from typing import Callable, List

import _shell_common as sc
import dump_env

USAGE = "\n".join((__doc__ or "").splitlines()[2:25])

# The usual tool bin dirs a session forgets to add. Only those present are reported.
def suspect_dirs(home: str) -> List[str]:
    """The candidate tool bin dirs, ``$HOME`` expanded — a plain ordered list."""
    return [
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
        f"{home}/.local/bin",
        f"{home}/.cargo/bin",
        f"{home}/go/bin",
        f"{home}/.asdf/shims",
        f"{home}/.rbenv/shims",
        f"{home}/.pyenv/shims",
        f"{home}/.fnm",
    ]


# --- pure logic ----------------------------------------------------------------

def entry_lines(path_lines: List[str]) -> List[str]:
    """Every non-empty PATH entry, numbered in order: ``entry<TAB>NN<TAB>/dir``."""
    out: List[str] = []
    n = 0
    for entry in path_lines:
        if not entry.strip():
            continue
        n += 1
        out.append(f"entry\t{n:02d}\t{entry}")
    return out


def dup_lines(path_lines: List[str]) -> List[str]:
    """Entries that appear more than once (first kept; later flagged, in order)."""
    out: List[str] = []
    seen: set[str] = set()
    for entry in path_lines:
        if not entry.strip():
            continue
        if entry in seen:
            out.append(f"dup\t{entry}")
        else:
            seen.add(entry)
    return out


def dead_lines(path_lines: List[str], is_dir: Callable[[str], bool]) -> List[str]:
    """Entries whose directory does not exist (dead/placeholder)."""
    return [f"dead\t{entry}" for entry in path_lines if entry.strip() and not is_dir(entry)]


def missing_tool_dir_lines(
    path_lines: List[str],
    suspects: List[str],
    is_dir: Callable[[str], bool],
    exec_count: Callable[[str], int],
) -> List[str]:
    """Present tool bin dirs that are NOT on PATH: ``missing_tool_dir<TAB>/dir<TAB>N execs``."""
    on_path = set(path_lines)
    out: List[str] = []
    for d in suspects:
        if not d:
            continue
        if not is_dir(d):
            continue
        if d not in on_path:
            out.append(f"missing_tool_dir\t{d}\t{exec_count(d)} execs")
    return out


def plan_lines(shell: str, clean: List[str]) -> List[str]:
    """The ``--plan`` repair block: a header + the cleaned PATH as a set/export line."""
    header = "-- repair plan (review, then apply by hand) --"
    if shell == "fish":
        body = f"set -gx PATH {' '.join(clean)}"
    else:
        body = f'export PATH="{":".join(clean)}"'
    return [header, body]


# --- IO ------------------------------------------------------------------------

def _exec_count(d: str) -> int:
    """Number of entries in a dir (the bash version's ``ls | wc -l``)."""
    try:
        return len(os.listdir(d))
    except OSError:
        return 0


def main(argv: List[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    shell = "zsh"
    plan = False
    for a in args:
        if a in ("zsh", "fish"):
            shell = a
        elif a == "--plan":
            plan = True
        elif a in ("-h", "--help"):
            print(USAGE)
            return 0
        else:
            print(f"path-doctor: unknown arg '{a}'", file=sys.stderr)
            return 2

    binary = sc.resolve_bin(shell)
    if not binary:
        print(f"path-doctor: could not read {shell} PATH", file=sys.stderr)
        return 3
    path_lines = dump_env.resolve_section(shell, "path", binary)

    out: List[str] = []
    out += entry_lines(path_lines)
    out += dup_lines(path_lines)
    out += dead_lines(path_lines, os.path.isdir)
    out += missing_tool_dir_lines(
        path_lines, suspect_dirs(os.environ.get("HOME", "")), os.path.isdir, _exec_count
    )
    if plan:
        clean = sc.dedupe_existing(path_lines)
        out += plan_lines(shell, clean)

    if out:
        print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
