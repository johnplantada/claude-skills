"""Shared helpers for the credential-store skill scripts. Stdlib only.

Single source of truth for the filesystem and CLI probes this skill needs, so a change
is a one-file edit. Every subprocess and IO call lives here; the callers' parsing,
classification, and formatting stay pure, directly-testable functions.

SECRETS — the whole contract of this skill:

A credential's VALUE never leaves this module. Files are opened only to classify what is
in them, and every function here returns metadata: a bool, a rule name, a path, a mode, a
line number. Nothing returns, prints, or logs matched text. This mirrors `grep -l` (and
the `is_private_key` helper in `ssh-config`): the bytes are inspected, the match is never
surfaced.

The callers keep that property structurally rather than by care — `scan_assignments`
discards the right-hand side of an assignment the moment it has been classified, so a
finding cannot carry a value even if a later formatter tried to print one. Operations
that need real plaintext (writing a secret into a store, unlocking a manager) run OUT OF
BAND — the user runs them; the value must not round-trip through the model.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_available
from lib.devenv_common import run as _run

CLI_TIMEOUT = 10.0

HOME = Path.home()

# Shell startup files an exported credential would live in. Order is stable so reports
# are diffable; missing files are simply skipped.
SHELL_RC_FILES = (
    "~/.zshenv", "~/.zprofile", "~/.zshrc", "~/.zlogin",
    "~/.bash_profile", "~/.bashrc", "~/.profile",
    "~/.config/fish/config.fish",
)
SHELL_RC_GLOBS = ("~/.config/fish/conf.d/*.fish",)

# Files that are credential-bearing by LOCATION — existence alone is the finding, so
# these are never opened. (path, what it holds)
SECRET_BY_LOCATION = (
    ("~/.aws/credentials", "AWS access keys"),
    ("~/.netrc", "machine passwords"),
    ("~/.git-credentials", "git HTTPS credentials in cleartext"),
    ("~/.pypirc", "PyPI upload tokens"),
)

# Files that only SOMETIMES hold a credential, so a marker decides. The pattern is used
# for a boolean/rule-name answer only — the match itself is never captured.
CONDITIONAL_SECRET_FILES = (
    ("~/.npmrc", re.compile(r"_authToken\s*="), "an npm _authToken"),
    ("~/.docker/config.json", re.compile(r'"auth"\s*:\s*"[A-Za-z0-9+/=]+"'), "a docker registry auth blob"),
    ("~/.config/gh/hosts.yml", re.compile(r"oauth_token:"), "a gh oauth token in cleartext"),
)


def expand(path: str) -> str:
    """`~` and `$VAR` expanded; '' stays ''."""
    return os.path.expandvars(os.path.expanduser(path)) if path else ""


def existing_shell_rc_files() -> list[str]:
    """Every shell startup file that exists on this machine, in a stable order."""
    found = [p for raw in SHELL_RC_FILES if os.path.isfile(p := expand(raw))]
    for raw in SHELL_RC_GLOBS:
        base = Path(expand(raw)).parent
        pattern = Path(raw).name
        if base.is_dir():
            found += [str(p) for p in sorted(base.glob(pattern)) if p.is_file()]
    return found


def read_lines(path: str) -> list[str]:
    """Lines of a config file, leniently decoded ('' -> [] if unreadable).

    The caller classifies each line and keeps only metadata; no line read here is ever
    returned to a report intact.
    """
    try:
        return Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return []


def file_mode(path: str) -> str:
    """Octal permission string for `path` ('???' if it can't be stat'd)."""
    try:
        return f"{os.stat(path).st_mode & 0o777:04o}"
    except OSError:
        return "???"


def matches_marker(path: str, pattern: re.Pattern) -> bool:
    """True if `path` contains `pattern`. The MATCH IS NEVER RETURNED — only this bool.

    Mirrors `grep -q`: enough to decide a finding, incapable of surfacing the secret.
    """
    try:
        with open(path, errors="replace") as fh:
            return any(pattern.search(line) for line in fh)
    except OSError:
        return False


def git_credential_helper() -> str:
    """`git config --global --get credential.helper`, stripped; '' if unset."""
    return _run(["git", "config", "--global", "--get", "credential.helper"], timeout=CLI_TIMEOUT).stdout.strip()


def gh_auth_raw() -> tuple[bool, str]:
    """(gh_installed, raw `gh auth status` output). Names accounts + storage, never a token.

    `gh` prints to stderr and exits non-zero when logged out, so both streams are merged
    and the exit code is ignored. `gh auth status` does not print the token unless asked
    with `--show-token`, which this skill never does.
    """
    if not command_available("gh"):
        return False, ""
    proc = _run(["gh", "auth", "status"], timeout=CLI_TIMEOUT)
    return True, f"{proc.stdout}\n{proc.stderr}".strip()


def op_accounts() -> tuple[bool, str]:
    """(op_installed, raw `op account list` output) — account metadata, never an item."""
    if not command_available("op"):
        return False, ""
    proc = _run(["op", "account", "list", "--format=json"], timeout=CLI_TIMEOUT)
    return True, proc.stdout.strip() if proc.returncode == 0 else ""


def keychain_available() -> bool:
    """True if the macOS keychain CLI is usable. Never queries an actual item."""
    if not command_available("security"):
        return False
    proc = subprocess.run(
        ["security", "list-keychains"], capture_output=True, text=True, timeout=CLI_TIMEOUT
    )
    return proc.returncode == 0


def chezmoi_encryption() -> str:
    """The `encryption =` value from chezmoi's config ('' if unset/absent).

    Reads only the encryption BACKEND name (`age`, `gpg`) — never the identity file it
    points at, and never a key.
    """
    for candidate in ("~/.config/chezmoi/chezmoi.toml", "~/.config/chezmoi/chezmoi.yaml"):
        path = expand(candidate)
        if not os.path.isfile(path):
            continue
        for line in read_lines(path):
            match = re.match(r"\s*encryption\s*[:=]\s*[\"']?(\w+)", line)
            if match:
                return match.group(1)
    return ""
