"""Shared helpers for the shell-sync skill scripts. Stdlib only.

All the subprocess/IO lives here so the callers' logic stays as pure, directly
testable functions. The one footgun this centralizes: a shell launched *inside*
another session inherits the parent's ``$PATH`` and pollutes the audit, so every
shell here is run under a wiped environment (the Python equivalent of
``env -i HOME=$HOME TERM=xterm fish_greeting='' <bin> -l -i -c '…'``) — you read
the TRUE login state, not one polluted by whatever launched the script.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, List

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import read_text  # noqa: E402  — shared primitive, re-exported for callers


def resolve_bin(shell: str) -> str | None:
    """Absolute path to the shell binary, or None if it isn't installed.

    Resolved up front so a caller can look it up *before* it would run anything in
    a wiped environment (which has no ``PATH`` to find the binary again).
    """
    return shutil.which(shell)


def clean_env() -> dict[str, str]:
    """The minimal login environment every shell here runs under.

    Mirrors ``env -i HOME=$HOME TERM=xterm fish_greeting=''`` — the parent session
    is stripped so the resolved state is the shell's own login config, nothing
    inherited. ``fish_greeting=''`` is set unconditionally (harmless for zsh, and
    it is what the bash `dump-env` did, so zsh's ``env`` dump shows the same
    ``fish_greeting=`` line the mirror denylist expects to filter).
    """
    return {"HOME": os.environ.get("HOME", ""), "TERM": "xterm", "fish_greeting": ""}


def run_login(binary: str, cmd: str, combine_stderr: bool = False) -> str:
    """Run ``binary -l -i -c cmd`` under a wiped login environment; return stdout.

    A non-zero exit never raises — the bash originals all trailed ``|| true`` — so
    a shell that errors on some rc line still yields whatever it printed. With
    ``combine_stderr`` the shell's stderr is folded into the returned text (used by
    the startup-cleanliness probe, which greps the shell's own error output).
    """
    stderr = subprocess.STDOUT if combine_stderr else subprocess.DEVNULL
    try:
        proc = subprocess.run(
            [binary, "-l", "-i", "-c", cmd],
            env=clean_env(),
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
        )
    except OSError:
        return ""
    return proc.stdout or ""


def dedupe_existing(entries: List[str], is_dir: Callable[[str], bool] = os.path.isdir) -> List[str]:
    """Order-preserving PATH cleanup: drop blanks, later duplicates, and dead dirs.

    Pure given the ``is_dir`` predicate (injected so tests need no real filesystem).
    Shared by ``path_doctor`` (the ``--plan`` PATH) and ``mirror_plan`` (the PATH
    block) so both clean PATH the same way.
    """
    out: List[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not entry or entry in seen:
            continue
        seen.add(entry)
        if is_dir(entry):
            out.append(entry)
    return out
