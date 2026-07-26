#!/usr/bin/env python3
"""What chezmoi manages, and where it drifts, in one view. Part of the dotfiles skill.

  dotfiles_inventory.py            # summary + managed files, each tagged with drift status
  dotfiles_inventory.py --dirs     # include managed directories too
  dotfiles_inventory.py --unmanaged  # ALSO list unmanaged candidates in $HOME (add-gaps)

Read-only. Collapses `chezmoi managed` + `chezmoi status` + a source-tree scan into
a stable, greppable listing so you don't re-run and re-correlate them by hand.

Output: summary `key<TAB>value` lines, then `managed:` rows as `<status><TAB><target>`
where <status> is the 2-char chezmoi status code (`--` = in sync, `MM` = differs, etc.).
"""

from __future__ import annotations

import re
import sys

import _dotfiles_common as dc

HELP = __doc__.strip()

_STATUS_PREFIX = re.compile(r"^.. ")


def status_code(status_text: str, target: str) -> str | None:
    """The 2-char chezmoi status code for `target` from `chezmoi status` output, or None
    if `target` is in sync (absent from the status listing). Status rows are
    ``<2-char> <path>``; the leading code+space is stripped and the remainder matched
    against the exact target path."""
    for line in status_text.splitlines():
        stripped = _STATUS_PREFIX.sub("", line, count=1)
        if stripped == target:
            return line[:2]
    return None


def managed_rows(managed_text: str, status_text: str) -> list[str]:
    """One ``<status><TAB><target>`` row per managed target, in listing order. In-sync
    targets get the `--` placeholder."""
    rows: list[str] = []
    for target in managed_text.splitlines():
        if target == "":
            continue
        code = status_code(status_text, target)
        rows.append(f"{code or '--'}\t{target}")
    return rows


def parse_args(args: list[str]) -> tuple[bool, bool]:
    """Return (want_dirs, want_unmanaged). Raises SystemExit for --help (0) or an
    unknown flag (2), preserving the bash script's messages and exit codes."""
    want_dirs = False
    want_unmanaged = False
    for a in args:
        if a == "--dirs":
            want_dirs = True
        elif a == "--unmanaged":
            want_unmanaged = True
        elif a in ("-h", "--help"):
            print(HELP)
            raise SystemExit(0)
        else:
            print(f"unknown arg: {a}", file=sys.stderr)
            print(HELP)
            raise SystemExit(2)
    return want_dirs, want_unmanaged


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    want_dirs, want_unmanaged = parse_args(args)

    if not dc.chezmoi_available():
        print("chezmoi_installed\tno", file=sys.stderr)
        return 1

    src = dc.chezmoi_source_path()
    if not (src and dc.is_git_repo(src)):
        print("not initialized — nothing managed yet (see reference/init.md)")
        return 0

    # Summary.
    print(f"managed_files\t{sum(1 for l in dc.chezmoi_managed('files').splitlines() if l)}")
    print(f"managed_dirs\t{sum(1 for l in dc.chezmoi_managed('dirs').splitlines() if l)}")
    print(f"templates\t{len(dc.find_files(src, '*.tmpl'))}")
    print(f"encrypted_files\t{len(dc.find_files(src, 'encrypted_*'))}")

    status = dc.chezmoi_status()

    print()
    print("managed:")
    include = "files,dirs" if want_dirs else "files"
    for row in managed_rows(dc.chezmoi_managed(include), status):
        print(row)

    if want_unmanaged:
        print()
        print("unmanaged (candidates in $HOME not tracked — review before adding):")
        for line in sorted(dc.chezmoi_unmanaged().splitlines()):
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
