"""Shared helpers for the macos-defaults skill scripts. Stdlib only.

Single source of truth for the thin `defaults` / `killall` / `bash` subprocess
wrappers, so a CLI change is a one-file edit. The subprocess and file IO live here;
the callers' parsing / classification / formatting stay as pure, directly-testable
functions in the individual scripts.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
# Re-exported for this skill's scripts (F401/E402 waived for _*.py in pyproject).
from lib.devenv_common import fact, undetermined, unparsed_line


def read_key(domain: str, key: str) -> tuple[bool, str]:
    """`defaults read <domain> <key>` → (ok, value).

    A missing key exits non-zero; we return (False, "") for it rather than raising,
    mirroring the bash `if val=$(… 2>/dev/null)` guard. The value has trailing
    newlines stripped, matching shell command substitution.
    """
    proc = subprocess.run(
        ["defaults", "read", domain, key], capture_output=True, text=True
    )
    if proc.returncode != 0:
        return False, ""
    return True, proc.stdout.rstrip("\n")


def read_domain(domain: str) -> tuple[bool, str]:
    """`defaults read <domain>` → (ok, full stdout). Used for domain backups."""
    proc = subprocess.run(
        ["defaults", "read", domain], capture_output=True, text=True
    )
    return proc.returncode == 0, proc.stdout


def find(term: str) -> str:
    """`defaults find <term>` → stdout (non-zero exit swallowed, like `|| true`)."""
    proc = subprocess.run(["defaults", "find", term], capture_output=True, text=True)
    return proc.stdout


def domains() -> str:
    """`defaults domains` → stdout (a single comma-separated line)."""
    proc = subprocess.run(["defaults", "domains"], capture_output=True, text=True)
    return proc.stdout


def run_bash(script: Path) -> int:
    """Run `bash <script>` and return its exit code. MUTATING."""
    return subprocess.run(["bash", str(script)]).returncode


def killall(names: list[str]) -> None:
    """`killall <names…>`; a not-running app is harmless (swallowed, like `|| true`)."""
    subprocess.run(["killall", *names], capture_output=True, text=True)
