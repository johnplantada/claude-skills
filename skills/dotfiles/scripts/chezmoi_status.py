#!/usr/bin/env python3
"""Discover the real chezmoi environment + health. Run FIRST. Part of the dotfiles skill.

No arguments. Prints one `key<TAB>value` line per fact (greppable, stable order),
then any doctor warning/error rows as `doctor_issue<TAB>...`. Replaces the
hand-composed discovery block in SKILL.md and reference/*.md.

Degrades gracefully: if chezmoi is not installed it prints
`chezmoi_installed<TAB>no` and exits 0 (nothing else to inspect).
All reads are read-only (source-path, doctor, status, diff, managed, git remote).
"""

from __future__ import annotations

import sys
from pathlib import Path

import _dotfiles_common as dc


def count_nonblank_lines(text: str) -> int:
    """Number of lines with at least one character — equivalent to `grep -c .`."""
    return sum(1 for line in text.splitlines() if line != "")


def count_diff_blocks(text: str) -> int:
    """Number of lines beginning `diff ` — equivalent to `grep -cE '^diff '`."""
    return sum(1 for line in text.splitlines() if line.startswith("diff "))


def worktree_state(porcelain: str) -> str:
    """Human label for the source worktree from `git status --porcelain` output."""
    if porcelain.strip() != "":
        return "dirty (uncommitted changes in source)"
    return "clean"


def parse_doctor(text: str) -> tuple[dict[str, int], list[str]]:
    """Summarize `chezmoi doctor` output.

    Skips the header row, tallies rows by their first field (RESULT), and returns
    ``(counts, issue_lines)`` where `issue_lines` are the whitespace-normalized
    ``doctor_issue<TAB>...`` rows for every warning/error (info rows are optional-tool
    noise and are not surfaced individually).
    """
    counts = {"ok": 0, "info": 0, "warning": 0, "error": 0}
    issues: list[str] = []
    for line in text.splitlines()[1:]:  # NR>1: skip the header row
        fields = line.split()
        if not fields:
            continue
        result = fields[0]
        if result in counts:
            counts[result] += 1
        if result in ("warning", "error"):
            issues.append("doctor_issue\t" + " ".join(fields))
    return counts, issues


def collect() -> list[str]:
    """Build the full greppable report as an ordered list of output lines."""
    lines: list[str] = []

    if not dc.chezmoi_available():
        lines.append("chezmoi_installed\tno")
        lines.append("hint\tinstall with: brew install chezmoi")
        return lines

    lines.append("chezmoi_installed\tyes")
    lines.append(f"chezmoi_version\t{dc.chezmoi_version()}")

    # `chezmoi source-path` prints a path even when uninitialized — the .git test is
    # the real "is this set up?" check.
    src = dc.chezmoi_source_path()
    lines.append(f"source_dir\t{src or '(unknown)'}")

    if src and dc.is_git_repo(src):
        lines.append("initialized\tyes")
        lines.append(f"source_worktree\t{worktree_state(dc.git_porcelain(src))}")
        lines.append(f"source_head\t{dc.git_head_short(src)}")
        remote = dc.git_remote_url(src)
        lines.append(f"source_remote\t{remote or '(none — no remote; changes stay local)'}")
    else:
        lines.append("initialized\tno")
        lines.append("hint\tnot initialized — this is an `init` job (see reference/init.md)")
        return lines

    # Config file (may legitimately be absent — chezmoi works without one).
    cfg = Path.home() / ".config" / "chezmoi" / "chezmoi.toml"
    lines.append(f"config_file\t{cfg}" if cfg.is_file() else "config_file\t(none — defaults)")

    # Inventory shape (files vs dirs). Empty listing is a valid answer.
    lines.append(f"managed_files\t{count_nonblank_lines(dc.chezmoi_managed('files'))}")
    lines.append(f"managed_dirs\t{count_nonblank_lines(dc.chezmoi_managed('dirs'))}")

    lines.append(f"templates\t{len(dc.find_files(src, '*.tmpl'))}")
    lines.append(f"encrypted_files\t{len(dc.find_files(src, 'encrypted_*'))}")
    ignore = Path(src) / ".chezmoiignore"
    lines.append("chezmoiignore\tpresent" if ignore.is_file() else "chezmoiignore\tabsent")

    # Drift: chezmoi status lines (0 = source and home agree); chezmoi diff files pending.
    status = dc.chezmoi_status()
    drift = 0 if status == "" else count_nonblank_lines(status)
    diff = count_diff_blocks(dc.chezmoi_diff())
    lines.append(f"status_drift\t{drift}\t(0 = in sync)")
    lines.append(f"diff_pending\t{diff}\t(files apply would change)")

    # Doctor summary + surface only warning/error rows.
    counts, issues = parse_doctor(dc.chezmoi_doctor())
    lines.append(
        f"doctor\tok={counts['ok']} info={counts['info']} "
        f"warning={counts['warning']} error={counts['error']}"
    )
    lines.extend(issues)
    return lines


def main(argv: list[str] | None = None) -> int:
    print("\n".join(collect()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
