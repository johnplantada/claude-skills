"""Shared helpers for the runtime-versions skill scripts. Stdlib only.

The subprocess / filesystem / PATH interactions used across the skill's diagnostics
(running `mise`, `brew`, `pyenv`, resolving binaries on PATH, sourcing `nvm.sh`) live
here, so the callers' logic stays as pure, directly-testable functions. All read-only:
these observe, never mutate.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_available as have
from lib.devenv_common import command_path as command_v
from lib.devenv_common import fact, read_text, run, undetermined

HOME = Path.home()

# The rc files a login shell may source, in the order shells consult them.
RC_FILES = [
    HOME / ".zshrc",
    HOME / ".zprofile",
    HOME / ".zshenv",
    HOME / ".bashrc",
    HOME / ".bash_profile",
    HOME / ".profile",
    HOME / ".config" / "fish" / "config.fish",
]


def which_all(tool: str) -> list[str]:
    """Every executable named `tool` on PATH, in PATH order (like `which -a tool`)."""
    found: list[str] = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        cand = os.path.join(d, tool)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            found.append(cand)
    return found


def realpath(path: str) -> str:
    """Follow symlinks to the real file (macOS mise/brew shims are symlinks)."""
    return os.path.realpath(path)


def tilde(path: str) -> str:
    """Collapse a leading $HOME to `~`, matching bash `${f/#$HOME/~}`."""
    home = str(HOME)
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


def nvm_default_version() -> str | None:
    """Best-effort `nvm version default`: source nvm.sh in a subshell and query it.

    nvm is a shell function, not a binary, so it must be sourced. Returns None when no
    usable nvm.sh is found; otherwise the reported default (or '(unknown)').
    """
    candidates = [HOME / ".nvm" / "nvm.sh", Path("/opt/homebrew/opt/nvm/nvm.sh")]
    nvm_sh = next((p for p in candidates if p.is_file() and p.stat().st_size > 0), None)
    if nvm_sh is None:
        return None
    # Pass HOME (via env) and the nvm.sh path (via argv $1), never interpolated into the
    # shell string — no value from Python can smuggle shell metacharacters into bash.
    script = (
        'export NVM_DIR="$HOME/.nvm"; . "$1" >/dev/null 2>&1; '
        "nvm version default 2>/dev/null"
    )
    env = {**os.environ, "HOME": str(HOME)}
    proc = subprocess.run(
        ["bash", "-c", script, "bash", str(nvm_sh)], env=env, capture_output=True, text=True
    )
    out = proc.stdout.strip()
    return out or "(unknown)"


def login_shell_resolve(binary: str, shell_args: list[str], script: str) -> subprocess.CompletedProcess:
    """Run `script` in a fresh login shell from an EMPTY environment (`env -i`).

    Only HOME and TERM are seeded, so the shell rebuilds PATH from its own login rc —
    resolution exactly as a new login would, not polluted by the current session. The
    shell binary is resolved to an absolute path by the caller before we clear the env
    (env's fallback PATH is only /usr/bin:/bin, so a Homebrew shell would vanish).
    """
    env = {"HOME": str(HOME), "TERM": "xterm"}
    return subprocess.run(
        [binary, *shell_args, "-c", script], env=env, capture_output=True, text=True
    )
