"""Shared helpers for the identity-profiles skill scripts. Stdlib only.

Single source of truth for the `git` / `ssh` / `gh` wrappers this skill needs, so a CLI
change is a one-file edit. Every subprocess and filesystem call lives here; the callers'
parsing, analysis, and formatting stay pure, directly-testable functions.

SECRETS: this skill reads PUBLIC key material only. `*.pub` files and `allowed_signers`
are public by design. A PRIVATE key is only ever referenced by PATH (as `ssh -G` reports
it) so paths can be compared — its bytes are never opened, printed, or returned. Key
hygiene itself (permissions, passphrases, the agent) belongs to the `ssh-config` skill.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_available, read_text
from lib.devenv_common import run as _run

# A `git config` probe runs against a user-supplied tree; a wedged filesystem (an
# unmounted network home) would otherwise hang the whole audit.
GIT_TIMEOUT = 10.0
SSH_TIMEOUT = 10.0


def expand(path: str) -> str:
    """`~` and `$VAR` expanded; '' stays ''. Not resolved against the filesystem."""
    return os.path.expandvars(os.path.expanduser(path)) if path else ""


def config_get(key: str, cwd: str | None = None, *, as_bool: bool = False) -> str:
    """`git [-C cwd] config --get <key>` — the RESOLVED value, stripped; '' if unset.

    `as_bool=True` adds `--type=bool`, which NORMALIZES git's several spellings of true
    (`1`, `yes`, `on`, `true`) to the literal `true`. Reading a boolean raw is a trap: a
    user who wrote `commit.gpgsign = 1` gets back `"1"`, and a caller comparing against
    `"true"` concludes signing is off — silently skipping every check that depends on it.
    """
    cmd = ["git"]
    if cwd is not None:
        cmd += ["-C", cwd]
    cmd += ["config"]
    if as_bool:
        cmd += ["--type=bool"]
    cmd += ["--get", key]
    return _run(cmd, timeout=GIT_TIMEOUT).stdout.strip()


def global_includeif_rules() -> list[str]:
    """Lines from `git config --global --get-regexp '^includeif\\.'` (empty if none)."""
    proc = _run(["git", "config", "--global", "--get-regexp", r"^includeif\."], timeout=GIT_TIMEOUT)
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def is_git_repo(path: str) -> bool:
    """True if `git -C path rev-parse --is-inside-work-tree` succeeds."""
    return _run(["git", "-C", path, "rev-parse", "--is-inside-work-tree"], timeout=GIT_TIMEOUT).returncode == 0


def remote_url(cwd: str, remote: str = "origin") -> str:
    """`git -C cwd remote get-url <remote>`, stripped; '' if there is no such remote."""
    proc = _run(["git", "-C", cwd, "remote", "get-url", remote], timeout=GIT_TIMEOUT)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def find_repo_in(tree: str, *, max_entries: int = 200) -> str:
    """Path of a git repo at or one level below `tree`, or '' if none is found.

    `includeIf "gitdir:"` only takes effect when git is evaluated from inside a real
    repository, so an audit of a tree needs one to probe with. Scans at most
    `max_entries` children so a huge directory can't stall the sweep.
    """
    root = expand(tree)
    if not os.path.isdir(root):
        return ""
    if os.path.isdir(os.path.join(root, ".git")):
        return root
    try:
        with os.scandir(root) as entries:
            for count, entry in enumerate(sorted(entries, key=lambda e: e.name)):
                if count >= max_entries:
                    break
                if entry.is_dir() and os.path.isdir(os.path.join(entry.path, ".git")):
                    return entry.path
    except OSError:
        return ""
    return ""


def ssh_g(host: str) -> tuple[int, str]:
    """Run `ssh -G <host>` (resolve the effective ssh config). Return (returncode, stdout)."""
    proc = _run(["ssh", "-G", host], timeout=SSH_TIMEOUT)
    return proc.returncode, proc.stdout


def ssh_probe_identity(alias: str) -> tuple[int, str]:
    """Ask the git host over ssh which account this alias authenticates as.

    Network call, opt-in only (`profile_resolve.py --probe-remote`). GitHub/GitLab answer
    a shell request with a banner naming the authenticated user and exit non-zero by
    design, so BOTH streams and the code are returned for the caller to parse.

    Strictly READ-ONLY, which the option set enforces:
    - `StrictHostKeyChecking=yes` refuses an unknown host instead of trusting it. The
      earlier `accept-new` silently APPENDED the host key to `~/.ssh/known_hosts` — a
      write, from a script documented as an inspector, and a tool whose job is verifying
      identity should never auto-trust an identity it has not seen before.
    - `UpdateHostKeys=no` stops OpenSSH ≥8.5 from learning additional host keys for an
      already-trusted host, which is the other path that writes to known_hosts.
    - `BatchMode=yes` guarantees it never blocks on a prompt.

    An unknown host therefore fails with "Host key verification failed." — a finding the
    caller reports, not a silent success.
    """
    proc = _run(
        [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=yes",
            "-o", "UpdateHostKeys=no",
            "-T", f"git@{alias}",
        ],
        timeout=SSH_TIMEOUT,
    )
    return proc.returncode, f"{proc.stdout}\n{proc.stderr}".strip()


def gh_auth_status() -> tuple[bool, str]:
    """(gh_installed, raw `gh auth status` output with stderr merged).

    `gh` prints its status to stderr and exits non-zero when logged out, so both streams
    are captured and the exit code is deliberately ignored.
    """
    if not command_available("gh"):
        return False, ""
    proc = _run(["gh", "auth", "status"], timeout=SSH_TIMEOUT)
    return True, f"{proc.stdout}\n{proc.stderr}".strip()


def read_pub(path: str) -> str:
    """Contents of a PUBLIC key file ('' if missing). Never called on a private key."""
    return read_text(expand(path))


def read_allowed_signers(path: str) -> str:
    """Contents of the `allowed_signers` file ('' if unset or missing). Public data."""
    return read_text(expand(path)) if path else ""
