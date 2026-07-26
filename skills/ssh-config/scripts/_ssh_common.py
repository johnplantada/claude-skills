"""Shared helpers for the ssh-config skill scripts. Stdlib only.

Single source of truth for the `stat` / `ssh-keygen` / `ssh-add` / `ssh -G` wrappers,
so a CLI change is a one-file edit. Every subprocess/IO call lives here; the callers'
parsing, analysis, and formatting stay as pure, directly-testable functions.

SECRETS: a private key is a secret. Nothing here ever prints, cats, echoes, or returns
private-key bytes. Key metadata comes from the PUBLIC `*.pub` (`ssh-keygen -lf`), from
`stat`, or from the EXIT CODE of `ssh-keygen -y -P '' -f <key>` (its public output is
discarded to /dev/null). Private keys are only detected by a header match — never read
into any returned value.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SSH_DIR = Path.home() / ".ssh"


def perms(path: Path | str) -> str:
    """macOS `stat -f '%A'` -> octal permission string, or '???' if it can't be read."""
    proc = subprocess.run(
        ["stat", "-f", "%A", str(path)], capture_output=True, text=True
    )
    out = proc.stdout.strip()
    return out if proc.returncode == 0 and out else "???"


def agent_identities() -> tuple[bool, int, str]:
    """Run `ssh-add -l`. Return (ok, returncode, stripped_stdout).

    rc 0 = agent up with identities, 1 = agent up but empty, 2 = no agent reachable.
    Only fingerprints are read — never key material.
    """
    proc = subprocess.run(["ssh-add", "-l"], capture_output=True, text=True)
    return proc.returncode == 0, proc.returncode, proc.stdout.strip()


def keygen_line(pub: Path | str) -> str:
    """`ssh-keygen -lf <pub>` -> its one-line output ('<bits> <fp> <comment> (<TYPE>)'),
    or '' if the public key can't be read. Operates on the PUBLIC half only."""
    proc = subprocess.run(
        ["ssh-keygen", "-lf", str(pub)], capture_output=True, text=True
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def is_private_key(path: Path | str) -> bool:
    """True if the file looks like a private key (its header carries 'PRIVATE KEY').

    Mirrors `grep -ql 'PRIVATE KEY'`: the bytes are inspected for the header match only
    and are NEVER returned or printed — no key material leaves this function.
    """
    try:
        with open(path, "r", errors="ignore") as fh:
            return "PRIVATE KEY" in fh.read()
    except OSError:
        return False


def is_unprotected(key: Path | str) -> bool:
    """True if the private key has NO passphrase, inferred from the exit code of
    `ssh-keygen -y -P '' -f <key>`. All output (including the public key it would print)
    is discarded — only pass/fail is observed, never the key material."""
    proc = subprocess.run(
        ["ssh-keygen", "-y", "-P", "", "-f", str(key)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def ssh_g(host: str) -> tuple[int, str]:
    """Run `ssh -G <host>` (resolve effective config). Return (returncode, stdout)."""
    proc = subprocess.run(["ssh", "-G", host], capture_output=True, text=True)
    return proc.returncode, proc.stdout


def read_text(path: Path | str) -> str:
    """File contents, or '' if it doesn't exist / can't be read."""
    try:
        return Path(path).read_text()
    except OSError:
        return ""
