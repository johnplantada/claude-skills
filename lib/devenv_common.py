"""Primitives shared across the devenv skills' Python scripts.

Small, dependency-free helpers that nearly every skill needs — a lenient file read,
PATH probes, and a non-raising subprocess wrapper. Skill-*specific* logic (chezmoi
wrappers, `ghostty +validate-config`, brew queries, …) stays in each skill's
`_<skill>_common.py`, which imports these.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def read_text(path: str | Path) -> str:
    """File contents, or '' if it doesn't exist / can't be read.

    Decodes leniently (``errors="replace"``) so a binary or odd-encoding file degrades
    to a searchable string instead of raising — matching how `grep` still scans it.
    """
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return ""


def command_available(name: str) -> bool:
    """True if ``name`` resolves on PATH (like ``command -v name``)."""
    return shutil.which(name) is not None


def command_path(name: str) -> str:
    """Absolute path of ``name`` on PATH, or '' if it isn't found."""
    return shutil.which(name) or ""


def run(cmd: list[str], *, text: bool = True) -> subprocess.CompletedProcess:
    """Run ``cmd``, capturing stdout+stderr; never raises on a non-zero exit."""
    return subprocess.run(cmd, capture_output=True, text=text)
