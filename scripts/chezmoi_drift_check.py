#!/usr/bin/env python3
"""devenv plugin Stop hook — a non-blocking chezmoi drift reminder.

Fires when Claude finishes a response. If chezmoi-managed dotfiles have drifted
from the source (e.g. a skill just edited a config), it prints ONE reminder so
the change doesn't silently escape version control. It NEVER writes, commits, or
blocks — you decide when to sync (via /dotfiles or `chezmoi re-add` + commit).

Reads the Stop-hook JSON on stdin (ignored). Emits a user-visible reminder via
the hook's `systemMessage` JSON output on stdout when there is drift, else prints
nothing. Always exits 0 (a Stop hook that exits non-zero would block the stop).

The pure `build_reminder` function turns `chezmoi status` output into the
reminder string and is what the tests exercise directly; the subprocess call is
isolated in `chezmoi_status`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def build_reminder(status: str) -> str | None:
    """Turn raw `chezmoi status` output into the drift reminder, or None if in sync.

    `chezmoi status` prints one line per managed file that differs, formatted as
    "XY <path>" — two status columns plus a space, then the path. The path starts
    at character index 3, so slicing there keeps paths that contain spaces intact.
    An empty (or all-blank) status means nothing has drifted.
    """
    files = [line[3:] for line in status.splitlines() if line.strip()]
    if not files:
        return None
    n = len(files)
    joined = ", ".join(files)
    return (
        f"⚠ dotfiles drift: {n} chezmoi-managed file(s) changed ({joined}). "
        "Run /dotfiles or 'chezmoi re-add' + commit to sync."
    )


def chezmoi_available() -> bool:
    return shutil.which("chezmoi") is not None


def chezmoi_status() -> str:
    """Return `chezmoi status` stdout, or '' if it fails."""
    try:
        proc = subprocess.run(["chezmoi", "status"], capture_output=True, text=True)
    except OSError:
        return ""
    return proc.stdout


def main(argv: list[str] | None = None) -> int:
    # Drain stdin so the caller's pipe closes cleanly; the payload is unused.
    try:
        sys.stdin.read()
    except OSError:
        pass

    if not chezmoi_available():
        return 0

    reminder = build_reminder(chezmoi_status())
    if reminder is not None:
        print(json.dumps({"systemMessage": reminder}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
