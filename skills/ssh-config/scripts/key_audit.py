#!/usr/bin/env python3
"""key_audit.py [ssh-dir] — SSH key-hygiene auditor. Metadata ONLY, never key material.

For every PRIVATE key found in ~/.ssh (default; override with an arg), reports:
  perms, type, bits, comment, fingerprint (all from the PUBLIC half or `stat`),
  whether it is passphrase-protected, and whether it is loaded in the agent.
Emits `label: value` lines under a `== key: <name> ==` header; stable order, greppable.
Part of the ssh-config skill.

SECRETS: a private key is a secret. This script NEVER prints, cats, or echoes private-key
bytes. Type/bits/fingerprint/comment come from the *.pub. Passphrase protection is inferred
from the EXIT CODE of `ssh-keygen -y -P '' -f <key>` (its public output is discarded); only
pass/fail is observed. Private keys are discovered via a header match, never read into output.
Perms come from `stat`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import _ssh_common as sc
from agent_status import agent_fingerprints

# Files that are never private keys — skip without inspecting.
_SKIP_NAMES = {"config", "config.bak"}


def parse_keygen_line(line: str) -> tuple[str, str, str, str]:
    """Split an `ssh-keygen -lf` line into (bits, fingerprint, type, comment).

    Format: '<bits> <fp> <comment...> (<TYPE>)'. Mirrors the awk/sed field extraction of
    the original: bits = field 1, fingerprint = field 2, type = text in the trailing
    parentheses, comment = the remaining middle fields (trailing '(TYPE)' stripped)."""
    parts = line.split()
    bits = parts[0] if parts else ""
    fp = parts[1] if len(parts) >= 2 else ""
    m = re.search(r"\(([^)]*)\)$", line)
    ktype = m.group(1) if m else line
    rest = " ".join(parts[2:])
    rest = re.sub(r" *\([^)]*\)$", "", rest)
    comment = rest.lstrip(" ")
    return bits, fp, ktype, comment


def classify_strength(ktype: str, bits: str) -> str:
    """The `strength: …` verdict line for a key of the given type/bit-size."""
    if ktype == "ED25519":
        return "strength: ok (ed25519 — preferred)"
    if ktype == "RSA":
        try:
            ok = int(bits) >= 3072
        except ValueError:
            ok = False
        if ok:
            return f"strength: acceptable (rsa {bits} — consider ed25519)"
        return f"strength: WEAK (rsa {bits} < 3072 — rotate; see keys.md)"
    if ktype == "DSA":
        return "strength: WEAK (dsa — rotate; see keys.md)"
    if ktype == "ECDSA":
        return "strength: review (ecdsa — prefer ed25519)"
    return f"strength: unknown ({ktype})"


def _perm_note(actual: str, expected: str, bad: str) -> str:
    return f"{actual} " + ("(ok)" if actual == expected else bad)


def dir_header(ssh_dir: str, dir_perms: str) -> list[str]:
    """The `== ssh dir ==` block."""
    return [
        "== ssh dir ==",
        f"path: {ssh_dir}",
        "perms: " + _perm_note(dir_perms, "700", "(SHOULD be 700)"),
    ]


def key_block(name: str, path: str, key_perms: str, pub_exists: bool,
              pub_perms: str, keygen_line: str, agent_fps: list[str],
              unprotected: bool) -> list[str]:
    """The `== key: <name> ==` block, from already-collected inputs (pure)."""
    lines = [
        "",
        f"== key: {name} ==",
        f"path: {path}",
        "perms: " + _perm_note(key_perms, "600",
                               "(SHOULD be 600 — ssh ignores loose keys)"),
    ]
    if pub_exists:
        lines.append("pub_perms: " + _perm_note(pub_perms, "644", "(prefer 644)"))
        if keygen_line.strip():
            bits, fp, ktype, comment = parse_keygen_line(keygen_line)
            lines.append(f"type: {ktype}")
            lines.append(f"bits: {bits}")
            lines.append(f"fingerprint: {fp}")
            lines.append(f"comment: {comment or '(none)'}")
            lines.append(classify_strength(ktype, bits))
            lines.append("in_agent: " + ("yes" if fp and fp in agent_fps else "no"))
        else:
            lines.append(f"type: (could not read {path}.pub)")
    else:
        lines.append(
            f"pub: MISSING ({path}.pub) — type/fingerprint unavailable without "
            "reading the private key (skipped by design)"
        )
    lines.append(
        "passphrase: "
        + ("NONE (unprotected — a stolen copy is instant compromise)"
           if unprotected else "protected")
    )
    return lines


def _is_candidate(path: Path) -> bool:
    """True if `path` is a file that could be a private key (not a .pub / known_hosts /
    config / backup / authorized_keys). Mirrors the case-glob skip list of the original."""
    name = path.name
    if name.endswith(".pub") or name.endswith(".bak"):
        return False
    if "known_hosts" in name or "authorized_keys" in name:
        return False
    return name not in _SKIP_NAMES


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    ssh_dir = Path(args[0]) if args else sc.SSH_DIR
    if not ssh_dir.is_dir():
        print(f"no such dir: {ssh_dir}", file=sys.stderr)
        return 1

    ok, _rc, agent_out = sc.agent_identities()
    agent_fps = agent_fingerprints(agent_out) if ok else []

    out = dir_header(str(ssh_dir), sc.perms(ssh_dir))

    for f in sorted(ssh_dir.iterdir()):
        if not f.is_file() or not _is_candidate(f):
            continue
        if not sc.is_private_key(f):
            continue
        pub = Path(f"{f}.pub")
        pub_exists = pub.is_file()
        out += key_block(
            name=f.name,
            path=str(f),
            key_perms=sc.perms(f),
            pub_exists=pub_exists,
            pub_perms=sc.perms(pub) if pub_exists else "",
            keygen_line=sc.keygen_line(pub) if pub_exists else "",
            agent_fps=agent_fps,
            unprotected=sc.is_unprotected(f),
        )

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
