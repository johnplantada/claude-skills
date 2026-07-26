"""Primitives shared across the devenv skills' Python scripts.

Small, dependency-free helpers that nearly every skill needs — a lenient file read,
PATH probes, and a non-raising subprocess wrapper. Skill-*specific* logic (chezmoi
wrappers, `ghostty +validate-config`, brew queries, …) stays in each skill's
`_<skill>_common.py`, which imports these.

## Two output conventions every audit script follows

These exist because both failure modes below shipped real, confidently-wrong findings:

**1. Unparsed lines are reported, never swallowed** (`unparsed_line`). Scripts scrape
human-readable CLI output, and CLIs have format variants for subcases — `brew outdated`
prints `<` for formulae but `!=` for casks. A parser that returns a blank field for the
variant lets that blank flow into a comparison and produce a confident wrong answer. A
visible `unparsed<TAB><line>` row is honest and instantly debuggable; a silent blank is a
lie that reads as authoritative.

**2. Facts carry their provenance** (`fact`). Some state exists only in a particular
environment: shell activation lives in an rc file, which a non-interactive subprocess
never sources. Asking the wrong environment yields a real-looking answer that is simply
about the wrong thing — that is how a correctly-activated machine got reported as broken.
Tagging each fact with where it came from (`src=login-shell` vs `src=this-process`) makes
the whole class self-diagnosing at a glance.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def unparsed_line(raw: str, why: str = "") -> str:
    """The `unparsed` row for a line the parser recognized as in-scope but couldn't read.

    Emit this instead of returning a blank field. Callers put it straight in their output,
    so an unexpected CLI format shows up as a visible row in the report rather than a
    silently wrong verdict downstream.
    """
    suffix = f"\t{why}" if why else ""
    return f"unparsed\t{raw.strip()}{suffix}"


def fact(key: str, value: str, src: str = "") -> str:
    """A `key<TAB>value` report row, optionally tagged with where the value came from.

    `src` matters whenever the answer depends on WHICH environment was asked — shell
    activation, PATH resolution, anything an rc file sets. Use `src="login-shell"` when
    the value came from a real login shell and `src="this-process"` when it came from the
    script's own (non-interactive) environment, so a reader can tell a real finding from
    an artifact of how it was measured.
    """
    return f"{key}\t{value}" + (f"\tsrc={src}" if src else "")


def undetermined(key: str, why: str) -> str:
    """A row stating a check could NOT be run — distinct from the check passing.

    "No findings" and "couldn't look" print almost identically otherwise, and the second
    silently reads as healthy. Say so explicitly instead.
    """
    return f"{key}\tundetermined\t{why}"


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


def run(
    cmd: list[str], *, text: bool = True, timeout: float | None = None
) -> subprocess.CompletedProcess:
    """Run ``cmd``, capturing stdout+stderr; never raises on a non-zero exit.

    An optional ``timeout`` (seconds) guards against a wedged CLI; expiry is reported
    as returncode 124 (the ``timeout(1)`` convention) with whatever output was captured.
    """
    try:
        return subprocess.run(cmd, capture_output=True, text=text, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if exc.stdout is not None else ("" if text else b"")
        stderr = exc.stderr if exc.stderr is not None else ("" if text else b"")
        return subprocess.CompletedProcess(cmd, 124, stdout, stderr)


def run_rc(cmd: list[str], *, merge: bool = False, timeout: float | None = None) -> tuple[int, str]:
    """Run ``cmd``; return ``(returncode, output)``, or ``(1, "")`` if it can't launch.

    ``merge=True`` folds stderr into stdout (the ``2>&1`` cases); otherwise stderr is
    dropped (the ``2>/dev/null`` cases). Never raises on a non-zero exit. An optional
    ``timeout`` (seconds) reports expiry as rc 124 with the output captured so far.
    """
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if merge else subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
    except OSError:
        return 1, ""
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        return 124, stdout or ""
    return proc.returncode, proc.stdout


def run_out(cmd: list[str]) -> str:
    """Stdout of ``cmd`` (stderr dropped), or '' on any failure."""
    return run_rc(cmd)[1]
