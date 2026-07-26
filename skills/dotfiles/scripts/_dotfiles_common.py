"""Shared helpers for the dotfiles skill scripts. Stdlib only.

Single source of truth for the `chezmoi` / `git` subprocess wrappers and the small
filesystem walkers the scripts need. All the process/IO isolation lives here so the
callers' logic stays as pure, directly-testable functions. A path/CLI change is a
one-file edit; the module name is unique (`_dotfiles_common`) to avoid colliding with
other skills' helpers on `sys.path`.
"""

from __future__ import annotations

import os
import sys
from fnmatch import fnmatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_available  # noqa: E402
from lib.devenv_common import run_out as _out  # noqa: E402
from lib.devenv_common import run_rc as _run  # noqa: E402


def chezmoi_available() -> bool:
    """True if `chezmoi` is on PATH."""
    return command_available("chezmoi")


# --- chezmoi wrappers ----------------------------------------------------------

def chezmoi_version() -> str:
    """First line of `chezmoi --version` (empty if unavailable)."""
    lines = _out(["chezmoi", "--version"]).splitlines()
    return lines[0] if lines else ""


def chezmoi_source_path() -> str:
    """`chezmoi source-path`, trailing whitespace stripped ('' when unresolved)."""
    return _out(["chezmoi", "source-path"]).strip()


def chezmoi_managed(include: str) -> str:
    """Raw stdout of `chezmoi managed --include=<include>`."""
    return _out(["chezmoi", "managed", f"--include={include}"])


def chezmoi_status() -> str:
    """Raw stdout of `chezmoi status`."""
    return _out(["chezmoi", "status"])


def chezmoi_diff() -> str:
    """Raw stdout of `chezmoi diff`."""
    return _out(["chezmoi", "diff"])


def chezmoi_doctor() -> str:
    """Raw stdout of `chezmoi doctor`."""
    return _out(["chezmoi", "doctor"])


def chezmoi_unmanaged() -> str:
    """Raw stdout of `chezmoi unmanaged`."""
    return _out(["chezmoi", "unmanaged"])


# --- git wrappers (operating on the source repo) -------------------------------

def git_porcelain(src: str) -> str:
    """`git -C <src> status --porcelain` stdout ('' on failure)."""
    return _out(["git", "-C", src, "status", "--porcelain"])


def git_head_short(src: str) -> str:
    """Short HEAD of the source repo, or 'no commits yet' if there is none."""
    rc, out = _run(["git", "-C", src, "rev-parse", "--short", "HEAD"])
    if rc == 0 and out.strip():
        return out.strip()
    return "no commits yet"


def git_remote_url(src: str) -> str:
    """origin remote URL ('' when there is no remote)."""
    return _out(["git", "-C", src, "remote", "get-url", "origin"]).strip()


def is_git_repo(src: str) -> bool:
    """True if `<src>/.git` is a directory."""
    return bool(src) and (Path(src) / ".git").is_dir()


# --- filesystem walkers --------------------------------------------------------

def find_files(root: str, pattern: str) -> list[str]:
    """Paths under `root` whose basename matches the glob `pattern`, skipping any
    `.git` directory (equivalent to `find <root> -name <pattern> -not -path '*/.git/*'`)."""
    if not Path(root).is_dir():
        return []
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for name in filenames:
            if fnmatch(name, pattern):
                out.append(os.path.join(dirpath, name))
    return out


def iter_files(target: str):
    """Yield every file under `target` (a dir walked recursively, or `target` itself if
    it is a file), skipping `.git` directories. Mirrors the scanners' file selection."""
    if os.path.isfile(target):
        yield target
        return
    for dirpath, dirnames, filenames in os.walk(target):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for name in filenames:
            yield os.path.join(dirpath, name)


def read_text_skip_binary(path: str) -> str | None:
    """File contents as text, or None if it can't be read or is binary (contains a NUL
    byte). Matches `grep -I`, which skips binary files."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    return data.decode("utf-8", errors="replace")
