#!/usr/bin/env python3
"""Read-only Brewfile drift report. Part of the brew-doctor skill.

Answers "is my tracked Brewfile honest against what's actually installed?" in one
call. READ-ONLY: `brew bundle check/list`, a `brew bundle cleanup` DRY-RUN (no
--force is ever passed here), and a `brew bundle dump` to a TEMP path. It never
writes the real Brewfile and never uninstalls anything.

Usage:
    brewfile_status.py                 # resolve path from config / ~/Brewfile
    brewfile_status.py --file ~/dotfiles/Brewfile

Path precedence: --file > config.toml [brew-doctor] brewfile > ~/Brewfile.
Output: satisfied Y/N, plus the two drift lists —
    only_in_brewfile = declared but NOT installed (a `brew bundle` would install)
    only_installed   = installed but NOT declared (a cleanup --force would REMOVE)
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

import _brew_common as bc

_ENTRY_RE = re.compile(r"^(tap|brew|cask|mas|vscode) ")


# --- pure helpers ------------------------------------------------------------

def resolve_brewfile(file_arg: str, config_value: str, home: str) -> str:
    """Pick the Brewfile: --file > config > ~/Brewfile, expanding a leading ~."""
    path = file_arg or config_value or f"{home}/Brewfile"
    if path.startswith("~"):
        path = home + path[1:]
    return path


def entries(text: str) -> list[str]:
    """Declarative Brewfile entry lines (tap/brew/cask/mas/vscode), comments
    stripped, sorted and de-duplicated — the old `grep | sed | sort -u`."""
    found = set()
    for line in text.splitlines():
        if _ENTRY_RE.match(line):
            found.add(re.sub(r"\s*#.*$", "", line))
    return sorted(found)


def only_in_first(a: list[str], b: list[str]) -> list[str]:
    """Sorted entries in `a` but not `b` (the old `comm -23`)."""
    return sorted(set(a) - set(b))


def only_in_second(a: list[str], b: list[str]) -> list[str]:
    """Sorted entries in `b` but not `a` (the old `comm -13`)."""
    return sorted(set(b) - set(a))


def parse_check_gaps(text: str) -> list[str]:
    """The gap lines from `brew bundle check --verbose` (the old `grep -E '→|needs'`)."""
    return [line for line in text.splitlines() if "→" in line or "needs" in line]


# --- main (I/O via _brew_common) ---------------------------------------------

def _parse_args(args: list[str]) -> str:
    file_arg = ""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--file":
            if i + 1 >= len(args):
                print("--file needs a path", file=sys.stderr)
                sys.exit(2)
            file_arg = args[i + 1]
            i += 2
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        else:
            print(f"unknown arg: {arg}", file=sys.stderr)
            sys.exit(2)
    return file_arg


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    file_arg = _parse_args(args)
    if not bc.brew_available():
        print("brewfile-status: brew not on PATH", file=sys.stderr)
        return 3

    path = resolve_brewfile(file_arg, bc.config_str("brew-doctor", "brewfile"), str(Path.home()))
    out: list[str] = [f"brewfile_path\t{path}"]

    if not Path(path).is_file():
        out.append(
            f"brewfile_exists\tno — none tracked yet (dump one: brew bundle dump --file={path})"
        )
        print("\n".join(out))
        return 0
    out.append("brewfile_exists\tyes")

    if bc.brew_ok("bundle", "check", f"--file={path}"):
        out.append("bundle_check\tsatisfied (Brewfile deps all installed)")
    else:
        out.append("bundle_check\tGAPS (declared but missing/outdated):")
        verbose = bc.brew("bundle", "check", f"--file={path}", "--verbose", merge=True)
        out.extend(f"  {line}" for line in parse_check_gaps(verbose))

    with tempfile.NamedTemporaryFile(prefix="brewfile.", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        bc.brew("bundle", "dump", f"--file={tmp_path}", "--force")
        file_entries = entries(bc.read_text(Path(path)))
        dump_entries = entries(bc.read_text(Path(tmp_path)))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    only_file = only_in_first(file_entries, dump_entries)
    only_inst = only_in_second(file_entries, dump_entries)

    out.append(f"only_in_brewfile_count\t{len(only_file)}")
    out.extend(f"  only_in_brewfile: {line}" for line in only_file)
    out.append(f"only_installed_count\t{len(only_inst)}")
    out.extend(f"  only_installed: {line}" for line in only_inst)
    out.append(
        f"prune_cmd\tbrew bundle cleanup --file={path} --force  "
        "(uninstalls the only_installed set)"
    )
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
