#!/usr/bin/env python3
"""agent_status.py [ssh-dir] — ssh-agent / keychain identity inspector. Fingerprints only.

Lists the identities the running agent holds (`ssh-add -l`, never the key body) and
cross-references them against the *.pub keys on disk so you can see, at a glance:
  - which on-disk keys are loaded vs not, and
  - any loaded identity that has no matching public key on disk.
Emits `label: value` lines; stable order, greppable. Part of the ssh-config skill.

SECRETS: reads only fingerprints (agent) and *.pub files (safe). No private key is ever touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

import _ssh_common as sc


def agent_fingerprints(agent_out: str) -> list[str]:
    """Column 2 of each non-empty `ssh-add -l` line — the SHA256 fingerprints. Mirrors
    `awk 'NF{print $2}'`: non-empty lines only, the second whitespace field."""
    fps: list[str] = []
    for line in agent_out.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        fps.append(parts[1] if len(parts) >= 2 else "")
    return fps


def pub_fingerprint(keygen_line: str) -> str:
    """Second field of an `ssh-keygen -lf` line (the fingerprint), or '' if empty."""
    parts = keygen_line.split()
    return parts[1] if len(parts) >= 2 else ""


def agent_section(ok: bool, rc: int, agent_out: str) -> list[str]:
    """The `== agent ==` block: state line plus one `loaded:` line per identity."""
    lines = ["== agent =="]
    if ok:
        lines.append("state: running with identities")
        for line in agent_out.splitlines():
            if line:
                lines.append(f"loaded: {line}")
    elif rc == 1:
        lines.append("state: running but EMPTY (no identities loaded)")
    else:
        lines.append("state: no agent reachable (SSH_AUTH_SOCK unset or agent down)")
    return lines


def disk_section(ssh_dir: str, entries: list[tuple[str, str]], agent_fps: list[str]) -> list[str]:
    """The `== on-disk public keys vs agent ==` block. `entries` is (pub-name, fp) in
    display order; fp is '' when the .pub is unreadable."""
    lines = ["", "== on-disk public keys vs agent =="]
    if not entries:
        lines.append(f"(no *.pub keys in {ssh_dir})")
        return lines
    for name, fp in entries:
        if fp and fp in agent_fps:
            lines.append(f"{name}: LOADED  ({fp})")
        else:
            lines.append(f"{name}: not-loaded  ({fp or 'unreadable'})")
    return lines


def orphan_section(disk_fps: list[str], agent_fps: list[str]) -> list[str]:
    """The `== loaded identities with no *.pub on disk ==` block — agent fingerprints
    that match no on-disk public key. Only emitted when the agent holds identities."""
    if not agent_fps:
        return []
    lines = ["", "== loaded identities with no *.pub on disk =="]
    for fp in agent_fps:
        if fp and fp not in disk_fps:
            lines.append(f"orphan: {fp}")
    return lines


def build_report(ok: bool, rc: int, agent_out: str, ssh_dir: str,
                 entries: list[tuple[str, str]]) -> list[str]:
    """Assemble the full greppable report from already-collected inputs (pure)."""
    agent_fps = agent_fingerprints(agent_out)
    disk_fps = [fp for _, fp in entries if fp]
    lines = agent_section(ok, rc, agent_out)
    lines += disk_section(ssh_dir, entries, agent_fps)
    lines += orphan_section(disk_fps, agent_fps)
    return lines


def collect_entries(ssh_dir: Path) -> list[tuple[str, str]]:
    """(pub-name, fingerprint) for each *.pub in ssh_dir, sorted. IO wrapper."""
    entries: list[tuple[str, str]] = []
    for pub in sorted(ssh_dir.glob("*.pub")):
        entries.append((pub.name, pub_fingerprint(sc.keygen_line(pub))))
    return entries


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    ssh_dir = Path(args[0]) if args else sc.SSH_DIR

    ok, rc, agent_out = sc.agent_identities()
    entries = collect_entries(ssh_dir)
    lines = build_report(ok, rc, agent_out, str(ssh_dir), entries)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
