#!/usr/bin/env python3
"""Detect when the INSTALLED fish mirror has fallen behind the canonical zsh —
i.e. zsh changed but the mirror wasn't re-generated. Answers "is
conf.d/00-shell-sync.fish still current?" without you eyeballing it. Read-only.
Part of the shell-sync skill.

It compares the installed mirror against a FRESH ``mirror_plan.py`` (the source of
truth, with all the tool-var/dead-path filtering), so this stays honest as the
generator improves — no duplicated denylist here.

Usage:
    mirror_drift.py                       # check the default mirror location
    mirror_drift.py ~/some/other.fish     # check a specific file

Greppable output (only drift lines are printed; a clean mirror prints just the
final in_sync line):
    stale_mtime<TAB>/path/to/zshconfig    a zsh config is NEWER than the mirror
    drift_env_stale<TAB>NAME=VALUE        mirror sets it; canonical no longer does
    drift_env_missing<TAB>NAME=VALUE      canonical sets it; mirror is missing it
    drift_path_stale<TAB>/dir             mirror has PATH dir; canonical doesn't
    drift_path_missing<TAB>/dir           canonical has PATH dir; mirror lacks it
    in_sync<TAB>yes|no                    final verdict (exit 0 if yes, 1 if no)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import _shell_common as sc

HERE = Path(__file__).resolve().parent
PLAN = HERE / "mirror_plan.py"


# --- pure logic: normalize a managed-file body to comparable sorted lines ------

def norm_env(text: str, home: str) -> List[str]:
    """``set -gx NAME value`` lines (not PATH) -> sorted unique ``NAME=value``,
    with ``$HOME`` expanded so a curated ``$HOME/x`` compares to a literal path."""
    out: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("set -gx "):
            continue
        if re.match(r"^set -gx PATH( |$)", line):
            continue
        parts = line.split(None, 3)
        if len(parts) < 3:
            continue
        name = parts[2]
        val = parts[3] if len(parts) > 3 else ""
        if val.startswith("'"):
            val = val[1:]
        if val.endswith("'"):
            val = val[:-1]
        val = val.replace("$HOME", home)
        out.add(f"{name}={val}")
    return sorted(out)


def norm_path(text: str, home: str) -> List[str]:
    """The PATH block (single- or continuation-line) -> one dir per line, sorted
    unique, ``$HOME`` expanded."""
    collected: List[str] = []
    active = False
    for line in text.splitlines():
        if line.startswith("set -gx PATH"):
            active = True
        if active:
            cont = line.endswith("\\")
            collected.append(re.sub(r"\\$", "", line))
            if not cont:
                active = False
    dirs: set[str] = set()
    for line in collected:
        line = re.sub(r"^set -gx PATH", "", line)
        for tok in line.split(" "):
            if tok:
                dirs.add(tok.replace("$HOME", home))
    return sorted(dirs)


def drift_lines(
    i_env: List[str], f_env: List[str], i_path: List[str], f_path: List[str]
) -> Tuple[List[str], bool]:
    """Compare installed vs fresh env/PATH sets; return (drift lines, any-drift)."""
    f_env_set, i_env_set = set(f_env), set(i_env)
    f_path_set, i_path_set = set(f_path), set(i_path)
    lines: List[str] = []
    lines += [f"drift_env_stale\t{x}" for x in i_env if x not in f_env_set]
    lines += [f"drift_env_missing\t{x}" for x in f_env if x not in i_env_set]
    lines += [f"drift_path_stale\t{x}" for x in i_path if x not in f_path_set]
    lines += [f"drift_path_missing\t{x}" for x in f_path if x not in i_path_set]
    return lines, bool(lines)


# --- IO ------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    home = os.environ.get("HOME", "")
    mirror = Path(args[0]) if args else Path(home) / ".config" / "fish" / "conf.d" / "00-shell-sync.fish"

    if not mirror.is_file():
        print(f"mirror-drift: no mirror at {mirror} (run the sync workflow first)", file=sys.stderr)
        return 3

    proc = subprocess.run([sys.executable, str(PLAN)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if proc.returncode != 0:
        print("mirror-drift: mirror-plan failed", file=sys.stderr)
        return 3
    fresh = proc.stdout
    installed = sc.read_text(mirror)

    drift = False
    lines: List[str] = []

    # staleness by mtime: any canonical zsh config newer than the mirror?
    mirror_mtime = mirror.stat().st_mtime
    for name in (".zshenv", ".zprofile", ".zshrc", ".zlogin"):
        z = Path(home) / name
        if z.is_file() and z.stat().st_mtime > mirror_mtime:
            lines.append(f"stale_mtime\t{z}")
            drift = True

    dlines, ddrift = drift_lines(
        norm_env(installed, home), norm_env(fresh, home),
        norm_path(installed, home), norm_path(fresh, home),
    )
    lines += dlines
    drift = drift or ddrift

    lines.append(f"in_sync\t{'no' if drift else 'yes'}")
    print("\n".join(lines))
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
