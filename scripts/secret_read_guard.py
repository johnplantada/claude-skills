#!/usr/bin/env python3
"""devenv plugin PreToolUse hook — MECHANICALLY deny reading secret-by-location files.

The skills' contract ("a secret's value never enters the model's context") was enforced
by instructions plus metadata-only scripts. Instructions bend: an eval caught an agent
running the scanner correctly and then grepping the flagged file "to confirm" — one
read undoes the whole guarantee. This hook turns the unambiguous half of the contract
into a wall: tool calls that would ingest a file that is a secret BY LOCATION (private
keys, .netrc, .aws/credentials, gh/hosts.yml — raw paths or their chezmoi source
encodings) are denied before they run, with a reason pointing at the metadata-only
alternative.

Scope, deliberately narrow:
  - Only unambiguous secret-by-location paths. Generic files that merely CONTAIN a
    token (an env.sh, a config with a key= line) cannot be path-classified — that class
    stays with secret_scan.py + the skills' instructions.
  - ~/.ssh/config, known_hosts, authorized_keys, allowed_signers, and *.pub stay
    readable: the ssh-config skill legitimately edits/audits them (Edit requires Read).
  - The skills' own Python scripts are unaffected — they read files in-process, and by
    contract emit metadata only.

Covered tools: Read (file_path), Grep (a secret file as the search target), and Bash
commands that pipe a secret file through a reader (cat/grep/head/…, `chezmoi cat`).

Fail-open by design: on any unexpected input this prints nothing and exits 0 (allow).
A guard that bricks every tool call on a schema change is worse than one that misses;
the prose + scanner layers remain underneath.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

# Basenames under an .ssh dir that are NOT key material — everything else there is
# treated as a private key (keys outnumber non-keys and mis-listing a new key name
# open = leak, closed = a permission prompt).
_SSH_SAFE_RE = re.compile(
    r"^(config|config\.d|known_hosts[^/]*|authorized_keys[^/]*|allowed_signers|.*\.pub)$"
)
# An .ssh directory segment, raw (`.ssh`) or chezmoi-source-encoded (`private_dot_ssh`,
# `dot_ssh`, `encrypted_dot_ssh`).
_SSH_DIR_RE = re.compile(r"(^|/)(private_|encrypted_)?(dot_|\.)ssh$")

# Non-ssh files that are secrets by location, matched on the path tail. Mirrors the
# secret_scan.py location rules (raw + chezmoi encodings).
_SECRET_TAIL_RE = re.compile(
    r"(^|/)(private_|encrypted_)?(dot_|\.|_)netrc$"
    r"|(^|/)(dot_|\.)aws/credentials$"
    r"|/gh/hosts\.ya?ml$"
    r"|\.(pem|p12|pfx)$"
)

# Bash commands whose FIRST word ingests file contents into output.
_READER_CMDS = {
    "cat", "grep", "egrep", "fgrep", "rg", "ag", "head", "tail", "less", "more",
    "strings", "awk", "sed", "xxd", "hexdump", "base64", "od", "bat",
}


def is_secret_path(path: str) -> bool:
    """True when `path` is a secret BY LOCATION (never by content)."""
    if not path:
        return False
    path = path.rstrip("/")
    parent, _, base = path.rpartition("/")
    if _SSH_DIR_RE.search(parent) and not _SSH_SAFE_RE.match(base):
        return True
    return bool(_SECRET_TAIL_RE.search(path))


def bash_reason(command: str) -> str | None:
    """A denial reason if `command` pipes a secret-by-location file through a reader."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return None
    secret_args = [t for t in tokens if not t.startswith("-") and is_secret_path(t)]
    if not secret_args:
        return None
    head = tokens[0].rsplit("/", 1)[-1]
    if head in _READER_CMDS or (head == "chezmoi" and len(tokens) > 1 and tokens[1] == "cat"):
        return f"'{head}' would print the contents of {secret_args[0]}"
    return None


def evaluate(tool_name: str, tool_input: dict) -> str | None:
    """The denial reason for this tool call, or None to allow. Pure — tests hit this."""
    if tool_name == "Read":
        path = str(tool_input.get("file_path", ""))
        if is_secret_path(path):
            return f"Read of {path}"
    elif tool_name == "Grep":
        path = str(tool_input.get("path", ""))
        if is_secret_path(path):
            return f"Grep over {path}"
    elif tool_name == "Bash":
        return bash_reason(str(tool_input.get("command", "")))
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        reason = evaluate(
            str(payload.get("tool_name", "")),
            payload.get("tool_input") or {},
        )
    except Exception:
        return 0  # fail-open: never brick tool calls on unexpected input
    if reason is None:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"devenv secret-read guard: {reason} — this file is a secret by "
                "location, and its value must never enter the model's context. Use the "
                "metadata-only scripts instead (secret_scan.py, key_audit.py: paths, "
                "rule names, fingerprints, exit codes). If the plaintext is truly "
                "needed, ask the user to handle it out of band."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
