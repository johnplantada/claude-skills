"""Shared helpers for the git-setup skill scripts. Stdlib only.

Single source of truth for the thin `git` (and `uname`/`command -v`) wrappers, so a
CLI change is a one-file edit. The subprocess calls live here; the callers' logic
stays as pure, directly-testable functions.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_path as command_v  # noqa: E402
from lib.devenv_common import run as _run  # noqa: E402


def uname_s() -> str:
    """Kernel name, e.g. 'Darwin' / 'Linux' — the `uname -s` value."""
    try:
        return os.uname().sysname
    except AttributeError:  # non-POSIX fallback
        proc = _run(["uname", "-s"])
        return proc.stdout.strip()


def git_version() -> str:
    """The bare version string from `git --version` (third whitespace field)."""
    proc = _run(["git", "--version"])
    parts = proc.stdout.split()
    return parts[2] if len(parts) >= 3 else ""


def getg(key: str) -> str:
    """`git config --global --get <key>`, stripped; '' if unset."""
    proc = _run(["git", "config", "--global", "--get", key])
    return proc.stdout.strip()


def config_get(key: str, cwd: str | None = None) -> str:
    """`git [-C cwd] config --get <key>` — the RESOLVED value, stripped; '' if unset."""
    cmd = ["git"]
    if cwd is not None:
        cmd += ["-C", cwd]
    cmd += ["config", "--get", key]
    return _run(cmd).stdout.strip()


def get_regexp_global(pattern: str) -> list[str]:
    """Lines from `git config --global --get-regexp <pattern>` (empty list if none)."""
    proc = _run(["git", "config", "--global", "--get-regexp", pattern])
    return [ln for ln in proc.stdout.splitlines() if ln]


def config_list_show_origin(cwd: str | None = None) -> str:
    """Raw `git [-C cwd] config --list --show-origin` output."""
    cmd = ["git"]
    if cwd is not None:
        cmd += ["-C", cwd]
    cmd += ["config", "--list", "--show-origin"]
    return _run(cmd).stdout


def is_inside_work_tree(cwd: str) -> bool:
    """True if `git -C cwd rev-parse --is-inside-work-tree` succeeds."""
    proc = _run(["git", "-C", cwd, "rev-parse", "--is-inside-work-tree"])
    return proc.returncode == 0


def show_toplevel(cwd: str) -> str:
    """`git -C cwd rev-parse --show-toplevel`, stripped; '?' on failure."""
    proc = _run(["git", "-C", cwd, "rev-parse", "--show-toplevel"])
    return proc.stdout.strip() if proc.returncode == 0 else "?"
