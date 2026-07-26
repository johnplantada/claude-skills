#!/usr/bin/env python3
"""mise_status.py — mise health + inventory in one call. No arguments. READ-ONLY.

Collapses the `mise doctor` / `mise ls` / `mise current` block from verification.md
(Health) + SKILL.md discovery into greppable output. If mise is not installed it says
so and exits 0 — safe to run on any machine.

    mise_installed   yes(<version>) | no
    mise_activated   yes | no | unknown   (from `mise doctor` — off = a shell-init/shell-sync fix)
    mise_shims_dir   the shims directory activation must put on PATH
    mise_problems    count of problems `mise doctor` reports (0 = clean)
    current: …       one line per tool in effect for THIS dir, with its source file
    installed: …     one line per installed tool@version (Active marked by mise)
"""

from __future__ import annotations

import re
import sys

import _runtime_common as rc

_ACTIVATED_YES = re.compile(r"activated: *yes|mise is active|is activated", re.IGNORECASE)
_ACTIVATED_NO = re.compile(r"activated: *no|not activated|is not active", re.IGNORECASE)
_PROBLEM = re.compile(r"problem|error|warning", re.IGNORECASE)


def classify_activation(doctor: str) -> str:
    """The `mise_activated` value derived from `mise doctor` output.

    Phrasing varies across mise versions, so both an affirmative and a negative form are
    matched; anything else is reported as unknown rather than guessed.
    """
    if _ACTIVATED_YES.search(doctor):
        return "yes"
    if _ACTIVATED_NO.search(doctor):
        return "no (shell init missing — a shell-sync fix, not a reinstall)"
    return "unknown (inspect `mise doctor` output)"


def extract_shims_dir(doctor: str, home: str) -> str:
    """The shims directory `mise doctor` names, or the documented default."""
    for line in doctor.splitlines():
        if re.search("shims", line, re.IGNORECASE):
            stripped = line.lstrip()
            if stripped:
                return stripped
            break
    return f"{home}/.local/share/mise/shims (default)"


def count_problems(doctor: str) -> int:
    """How many lines of `mise doctor` flag a problem/error/warning (0 = clean)."""
    return sum(1 for line in doctor.splitlines() if _PROBLEM.search(line))


def prefixed(text: str, prefix: str) -> list[str]:
    """Each line of `text` with `prefix` prepended (mirrors `sed 's/^/prefix/'`)."""
    return [prefix + line for line in text.splitlines()]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    if not rc.have("mise"):
        print("mise_installed\tno")
        print("note\tinstall via the brew-doctor skill (brew install mise), then re-run")
        return 0

    ver = (rc.run(["mise", "--version"]).stdout.splitlines() or [""])[0]
    print(f"mise_installed\tyes ({ver})")

    doc = rc.run(["mise", "doctor"])
    doctor = doc.stdout + doc.stderr
    print(f"mise_activated\t{classify_activation(doctor)}")
    print(f"mise_shims_dir\t{extract_shims_dir(doctor, str(rc.HOME))}")
    print(f"mise_problems\t{count_problems(doctor)}")

    print("-- mise current (versions in effect here + source file) --")
    cur = rc.run(["mise", "current"])
    if cur.returncode != 0:
        print("current: (none resolved for this dir)")
    else:
        for line in prefixed(cur.stdout, "current: "):
            print(line)

    print("-- mise ls (installed; Active per mise) --")
    ls = rc.run(["mise", "ls"])
    if ls.returncode != 0:
        print("installed: (none)")
    else:
        for line in prefixed(ls.stdout, "installed: "):
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
