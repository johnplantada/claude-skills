#!/usr/bin/env python3
"""Read-only Homebrew health & risk inspector. Part of the brew-doctor skill.

Collapses the whole audit inventory + hazard sweep into one call. READ-ONLY: runs
only `brew leaves/list/outdated/tap/info/autoremove --dry-run/doctor` and reads
launchd/cron; it never installs, pins, upgrades, or removes anything. Prints
greppable `key<TAB>value` / `label: value` lines in a stable order.

Usage:
    brew_audit.py                 # all sections (env, inventory, pins, autoupdate, cruft)
    brew_audit.py autoupdate      # just the silent-auto-upgrade sweep (the top hazard)
    brew_audit.py inventory       # leaves/formulae/casks/taps counts + lists
    brew_audit.py pins            # what's pinned vs. what config expects pinned
    brew_audit.py cruft           # outdated, orphans, self-updating casks, brew doctor

The autoupdate section resolves each launchd agent's program and greps it to tell
`brew upgrade` (the real hazard) apart from `brew update` (metadata, safe).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import _brew_common as bc

NEWLINE = "\n"
SECTIONS = ("all", "env", "inventory", "pins", "autoupdate", "cruft")


# --- pure helpers ------------------------------------------------------------

def count_nonempty(text: str) -> int:
    """Number of non-empty lines — the `grep -c .` count."""
    return sum(1 for line in text.splitlines() if line)


def join_trailing(lines: list[str], default: str) -> str:
    """Join lines the way `tr '\\n' ' '` does — each item plus a trailing space —
    or `default` when there are no lines."""
    if not lines:
        return default
    return "".join(f"{line} " for line in lines)


def agent_matches(basename: str) -> bool:
    """True when a LaunchAgent filename looks brew-related (the old case glob:
    `*brew*` / `*autoupdate*` / `*Homebrew*`, case-sensitive)."""
    return "brew" in basename or "autoupdate" in basename or "Homebrew" in basename


def mode_of_script(content: str, readable: bool, target: str) -> str:
    """Classify an auto-updater wrapper by which `brew` subcommand it runs."""
    if not readable:
        return f"unknown (target unreadable: {target})"
    up = re.compile(r"brew\s+([^&|;]*\s)?upgrade")
    ud = re.compile(r"brew\s+([^&|;]*\s)?update")
    lines = content.splitlines()
    if any(up.search(line) for line in lines):
        return "UPGRADE (bumps packages unattended — the hazard)"
    if any(ud.search(line) for line in lines):
        return "update-only (metadata + notify — safe)"
    return "not an auto-updater (runs a service/binary, not 'brew update'/'upgrade')"


def orphan_kept_lines(text: str) -> list[str]:
    """`brew autoremove --dry-run` lines minus the `would remove` / `==>` headers
    (the old `grep -vi 'would remove\\|^==>'`)."""
    kept: list[str] = []
    for line in text.splitlines():
        if "would remove" in line.lower():
            continue
        if line.startswith("==>"):
            continue
        kept.append(line)
    return kept


def orphan_tokens(kept: list[str]) -> list[str]:
    """Space/newline-split the kept orphan lines into individual package tokens."""
    return [tok for tok in re.split(r"[ \n]+", "\n".join(kept)) if tok]


# --- section emitters (I/O via _brew_common) ---------------------------------

def _emit_env(out: list[str]) -> None:
    version = bc.brew("--version").splitlines()
    out.append(f"brew_version\t{version[0] if version else ''}")
    out.append(f"brew_prefix\t{bc.brew('--prefix').strip()}")


def _emit_inventory(out: list[str]) -> None:
    out.append(f"leaves_count\t{count_nonempty(bc.brew('leaves'))}")
    out.append(f"formulae_total\t{count_nonempty(bc.brew('list', '--formula'))}")
    out.append(f"casks_count\t{count_nonempty(bc.brew('list', '--cask'))}")
    taps = bc.brew("tap").splitlines()
    out.append(f"taps\t{join_trailing(taps, '(none)')}")


def _emit_pins(out: list[str]) -> None:
    pinned = bc.brew("list", "--pinned").splitlines()
    out.append(f"pinned\t{join_trailing(pinned, '(none — nothing is gated!)')}")
    expect = bc.config_str("brew-doctor", "pinned")
    if expect:
        out.append(f"pinned_expected(config)\t{expect}")


def _emit_autoupdate(out: list[str]) -> None:
    tap_au = "\n".join(ln for ln in bc.brew("tap").splitlines() if "autoupdate" in ln.lower())
    out.append(f"autoupdate_tap\t{tap_au or '(not tapped)'}")
    status = bc.brew("autoupdate", "status", merge=True).splitlines()
    out.append(f"autoupdate_status\t{status[0] if status else '(no output)'}")
    expect_mode = bc.config_str("brew-doctor", "autoupdate_mode")
    if expect_mode:
        out.append(f"autoupdate_expected(config)\t{expect_mode}")

    found = False
    agents_dir = bc.launch_agents_dir()
    if agents_dir.is_dir():
        for plist in sorted(agents_dir.glob("*.plist")):
            if not agent_matches(plist.name):
                continue
            found = True
            prog = bc.plist_program(plist)
            out.append(f"launchd_agent\t{plist.name}")
            out.append(f"  program\t{prog or '(none)'}")
            if prog:
                readable = os.access(prog, os.R_OK)
                out.append(f"  mode\t{mode_of_script(bc.read_text(Path(prog)), readable, prog)}")
    if not found:
        out.append("launchd_agent\t(none matching brew/autoupdate)")

    out.append(f"cron_brew\t{bc.crontab_brew_lines() or '(none)'}")


def _emit_cruft(out: list[str]) -> None:
    # `--formula` keeps casks out of the FORMULA count — a bare `brew outdated` lists
    # both, so every outdated cask was counted twice (once here, once as a cask below).
    outdated = bc.brew("outdated", "--verbose", "--formula")
    out.append(f"outdated_count\t{count_nonempty(outdated)}")
    for line in outdated.splitlines():
        if line:
            out.append(f"  outdated: {line}")

    outdated_cask = bc.brew("outdated", "--cask")
    out.append(f"outdated_cask_count\t{count_nonempty(outdated_cask)}")
    for line in outdated_cask.splitlines():
        if line:
            out.append(f"  outdated_cask: {line}")

    kept = orphan_kept_lines(bc.brew("autoremove", "--dry-run"))
    out.append(f"orphans_count\t{count_nonempty(NEWLINE.join(kept))}")
    for tok in orphan_tokens(kept):
        out.append(f"  orphan: {tok}")

    for cask in bc.brew("list", "--cask").split():
        if "auto_updates true" in bc.brew("info", "--cask", cask):
            out.append(f"self_updating_cask\t{cask}")

    doctor = bc.brew("doctor", merge=True).splitlines()
    out.append(f"brew_doctor\t{doctor[0] if doctor else ''}")


def build_report(section: str) -> list[str]:
    """Assemble the report lines for the requested section (or all of them)."""
    out: list[str] = []
    want = lambda name: section == "all" or section == name  # noqa: E731
    if want("env"):
        _emit_env(out)
    if want("inventory"):
        _emit_inventory(out)
    if want("pins"):
        _emit_pins(out)
    if want("autoupdate"):
        _emit_autoupdate(out)
    if want("cruft"):
        _emit_cruft(out)
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    section = args[0] if args else "all"
    if section not in SECTIONS:
        # A typo'd section must not print an empty report that reads as "healthy".
        print(f"brew-audit: unknown section '{section}' (use: {' '.join(SECTIONS)})", file=sys.stderr)
        return 2
    if not bc.brew_available():
        print("brew-audit: brew not on PATH", file=sys.stderr)
        return 3
    print("\n".join(build_report(section)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
