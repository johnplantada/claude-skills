#!/usr/bin/env python3
"""ssh_config_audit.py [host] — ~/.ssh/config auditor + effective-config resolver.

With no arg: audits the config FILE — perms on ~/.ssh + config + config.d, the Host
aliases declared, Include directives, hardening settings present/absent, weak settings,
and known_hosts state. With a [host] arg: additionally runs `ssh -G <host>` and prints
the resolved effective settings that actually decide auth for that host.
Emits `label: value` lines; stable order, greppable. Part of the ssh-config skill.

SECRETS: never prints the config verbatim (it can hold private HostName/User). It reports
Host *aliases*, IdentityFile *filenames*, and which hardening options are set — not their
host/user values. `ssh -G <host>` output is shown only for a host YOU pass explicitly.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import _ssh_common as sc

# Hardening options to report as present/absent (order is stable output).
_HARDENING = [
    "IdentitiesOnly", "AddKeysToAgent", "UseKeychain",
    "IdentityFile", "HashKnownHosts", "ServerAliveInterval",
]

# ssh -G keys whose resolved values actually decide auth — the only ones surfaced.
_RESOLVED_KEYS = (
    "hostname", "user", "port", "identityfile", "identitiesonly",
    "addkeystoagent", "usekeychain", "stricthostkeychecking",
)


def host_aliases(text: str) -> str:
    """The Host aliases declared, space-joined with a trailing space (mirrors the
    `grep … | sed 's/^\\s*[Hh]ost\\s+//' | tr '\\n' ' '` pipeline). '' if none."""
    out: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*host\s", line, re.IGNORECASE):
            out.append(re.sub(r"^\s*[Hh]ost\s+", "", line))
    return " ".join(out) + " " if out else ""


def include_dirs(text: str) -> str:
    """The Include directives, space-joined with a trailing space. '' if none."""
    out: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*include\s", line, re.IGNORECASE):
            out.append(re.sub(r"^\s*[Ii]nclude\s+", "", line))
    return " ".join(out) + " " if out else ""


def option_count(text: str, opt: str) -> int:
    """How many lines set `opt` (case-insensitive, `opt` followed by whitespace)."""
    pat = re.compile(r"^\s*" + re.escape(opt) + r"\s", re.IGNORECASE)
    return sum(1 for line in text.splitlines() if pat.match(line))


def weak_settings(text: str) -> str:
    """Dangerous settings present, as `<lineno>:<line>` entries joined+terminated by ';'
    (mirrors `grep -inE … | sed 's/:[0-9]+:/ → /' | tr '\\n' ';'`). '' if none."""
    pat = re.compile(
        r"^\s*(StrictHostKeyChecking\s+no|CheckHostIP\s+no|PasswordAuthentication\s+yes)",
        re.IGNORECASE,
    )
    entries: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        if pat.match(line):
            entries.append(re.sub(r":[0-9]+:", " → ", f"{i}:{line}"))
    return ";".join(entries) + ";" if entries else ""


def filter_resolved(ssh_g_out: str) -> list[str]:
    """The `ssh -G` lines whose keyword is one of the auth-deciding settings."""
    out: list[str] = []
    for line in ssh_g_out.splitlines():
        head = line.split(" ", 1)[0].lower()
        if head in _RESOLVED_KEYS and " " in line:
            out.append(line)
    return out


def permissions_section(ssh_dir: Path) -> list[str]:
    """The `== permissions ==` block (IO: stat on ~/.ssh, config, config.d + members)."""
    cfg = ssh_dir / "config"
    confd = ssh_dir / "config.d"
    lines = ["== permissions =="]
    for p in (ssh_dir, cfg, confd):
        if p.exists():
            lines.append(f"{p.name}: {sc.perms(p)} ({p})")
    if confd.is_dir():
        for f in sorted(confd.iterdir()):
            if f.is_file():
                lines.append(f"config.d/{f.name}: {sc.perms(f)}")
    return lines


def config_section(cfg: Path) -> list[str]:
    """The `== config file ==` block (pure analysis over the config text)."""
    lines = ["", "== config file =="]
    if not cfg.is_file():
        lines.append("state: MISSING — no ~/.ssh/config yet (see setup.md)")
        return lines
    text = sc.read_text(cfg)
    lines.append("state: present")
    lines.append(f"host_blocks: {host_aliases(text) or '(none)'}")
    lines.append(f"include: {include_dirs(text) or '(none — monolithic config)'}")
    for opt in _HARDENING:
        n = option_count(text, opt)
        lines.append(f"opt_{opt}: set ({n} block(s))" if n > 0 else f"opt_{opt}: ABSENT")
    lines.append(f"weak_settings: {weak_settings(text) or '(none found)'}")
    return lines


def known_hosts_section(ssh_dir: Path) -> list[str]:
    """The `== known_hosts ==` block."""
    kh = ssh_dir / "known_hosts"
    lines = ["", "== known_hosts =="]
    if kh.is_file():
        entries = sc.read_text(kh).count("\n")
        lines.append(f"known_hosts: present ({entries} entries)")
    else:
        lines.append("known_hosts: ABSENT (every host will be TOFU-prompted)")
    return lines


def resolved_section(host: str, rc: int, ssh_g_out: str) -> list[str]:
    """The `== ssh -G <host> ==` block. Prints one `resolved:` line per auth-deciding
    setting; a failure line when ssh -G failed or matched nothing (pipefail semantics)."""
    lines = ["", f"== ssh -G {host} (effective, resolved) =="]
    matched = filter_resolved(ssh_g_out)
    for line in matched:
        lines.append(f"resolved: {line}")
    if rc != 0 or not matched:
        lines.append(f"resolved: (ssh -G failed for {host})")
    return lines


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    host = args[0] if args else ""
    ssh_dir = sc.SSH_DIR
    cfg = ssh_dir / "config"

    lines = permissions_section(ssh_dir)
    lines += config_section(cfg)
    lines += known_hosts_section(ssh_dir)
    if host:
        rc, out = sc.ssh_g(host)
        lines += resolved_section(host, rc, out)

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
