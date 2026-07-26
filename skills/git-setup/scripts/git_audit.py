#!/usr/bin/env python3
"""Audit the GLOBAL git config and emit a prioritized gap report. Read-only.
Part of the git-setup skill.

No arguments. Everything is READ-ONLY (git config --global --get/--list, reading
files). Changes nothing. Prints greppable `key<TAB>value` facts (stable order),
then a `gap` section sorted 🔴 → 🟡 → 🟢, each with the exact fix command.

    git_audit.py                 # full report
    git_audit.py | grep '^gap'   # just the prioritized gaps
    git_audit.py | grep 🔴       # just the critical ones
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import _git_common as gc

# The 7 keys shown in the `default.*` facts block.
DEFAULT_FACT_KEYS = [
    "init.defaultBranch", "pull.rebase", "push.autoSetupRemote", "push.default",
    "fetch.prune", "rebase.autostash", "core.excludesfile",
]

# The 6 keys the gap report recommends when unset (key -> recommended value).
# core.excludesfile is handled separately by the global-gitignore check.
SANE_DEFAULTS = [
    ("init.defaultBranch", "main"),
    ("pull.rebase", "true"),
    ("push.autoSetupRemote", "true"),
    ("push.default", "simple"),
    ("fetch.prune", "true"),
    ("rebase.autostash", "true"),
]

SEVERITY_EMOJI = {"R": "🔴", "Y": "🟡", "G": "🟢"}


# --- pure helpers --------------------------------------------------------------

def _tr_join(values: list[str]) -> str:
    """Mimic `awk '{print $N}' | tr '\\n' ' '`: values space-joined, trailing space."""
    return "".join(v + " " for v in values)


def includes_from(lines: list[str]) -> str:
    """Second whitespace field of each `include.*` get-regexp line, tr-joined."""
    fields = [parts[1] for ln in lines if len(parts := ln.split()) >= 2]
    return _tr_join(fields)


def includeif_keys_from(lines: list[str]) -> str:
    """First whitespace field (the key) of each `includeif.*` line, tr-joined."""
    fields = [parts[0] for ln in lines if (parts := ln.split())]
    return _tr_join(fields)


def first_email_origin(show_origin: str) -> str:
    """Origin file of the first line mentioning `user.email=` (awk -F'\\t' $1, sed file:)."""
    for line in show_origin.splitlines():
        if re.search(r"user\.email=", line):
            origin = line.split("\t")[0]
            return origin[len("file:"):] if origin.startswith("file:") else origin
    return ""


# --- pure gap evaluation -------------------------------------------------------

def signing_gaps(gpgsign: str, fmt: str, signkey: str, signers: str) -> list[tuple[str, str, str]]:
    """Signing findings, in the bash script's add order."""
    out: list[tuple[str, str, str]] = []
    if gpgsign != "true":
        out.append((
            "Y",
            "no commit signing (commits show unverified on GitHub)",
            "see reference/configure.md §4 — set up SSH signing",
        ))
        return out
    if fmt == "ssh" and not signers:
        out.append((
            "R",
            "signed but WON'T VERIFY locally — commit.gpgsign=true, gpg.ssh.allowedSignersFile unset",
            "git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers  (+ add <email> <pubkey> line)",
        ))
    if fmt == "ssh" and signkey:
        if signkey.endswith(".pub"):
            pass
        elif signkey.startswith("/") or signkey.startswith("~"):
            out.append((
                "R",
                "user.signingkey looks like a PRIVATE key path (ssh format expects a .pub)",
                f"git config --global user.signingkey {signkey}.pub",
            ))
    return out


def pager_gap(pager: str, delta: str) -> list[tuple[str, str, str]]:
    """Delta pager finding."""
    if pager != "delta" or not delta:
        return [("G", "no delta pager (plain diffs)",
                 "brew install git-delta && git config --global core.pager delta")]
    return []


def default_gaps(defaults: dict[str, str]) -> list[tuple[str, str, str]]:
    """One G finding per unset sane-default key, in declared order."""
    out: list[tuple[str, str, str]] = []
    for key, recommended in SANE_DEFAULTS:
        if not defaults.get(key):
            out.append((
                "G",
                f"default {key} unset (recommend: {recommended})",
                f"git config --global {key} {recommended}",
            ))
    return out


def gitignore_gap(excludes: str, xdg_ignore_exists: bool) -> list[tuple[str, str, str]]:
    """Global-gitignore finding when neither core.excludesfile nor the XDG default exists."""
    if not excludes and not xdg_ignore_exists:
        return [(
            "Y",
            "no global gitignore (.DS_Store, .env, editor swap files get committed per-repo)",
            "git config --global core.excludesfile ~/.gitignore_global  (see reference/configure.md §2)",
        )]
    return []


def credential_gap(platform: str, cred: str) -> list[tuple[str, str, str]]:
    """macOS credential-helper finding."""
    if platform == "Darwin" and not cred:
        return [(
            "Y",
            "no credential helper on macOS (HTTPS pushes re-prompt every time)",
            "git config --global credential.helper osxkeychain",
        )]
    return []


def alias_gap(alias_count: int) -> list[tuple[str, str, str]]:
    """No-aliases finding."""
    if alias_count == 0:
        return [("G", "no aliases defined",
                 "see reference/configure.md §6 for st/co/br/lg/last/unstage")]
    return []


def identity_gap(email: str, includeif: str) -> list[tuple[str, str, str]]:
    """Single-global-identity finding (email set but no per-directory includeIf)."""
    if email and not includeif:
        return [(
            "G",
            "single global identity, no per-directory includeIf (fine unless you mix work+personal repos)",
            "see reference/identity.md for conditional includes",
        )]
    return []


def evaluate_gaps(facts: dict) -> list[tuple[str, str, str]]:
    """All findings as (severity, message, fix), in the bash script's add order."""
    findings: list[tuple[str, str, str]] = []
    findings += signing_gaps(facts["gpgsign"], facts["format"], facts["signkey"], facts["signers"])
    findings += pager_gap(facts["pager"], facts["delta"])
    findings += default_gaps(facts["defaults"])
    findings += gitignore_gap(facts["excludes"], facts["xdg_ignore_exists"])
    findings += credential_gap(facts["platform"], facts["cred"])
    findings += alias_gap(facts["alias_count"])
    findings += identity_gap(facts["email"], facts["includeif"])
    return findings


# --- pure formatting -----------------------------------------------------------

def format_facts(facts: dict) -> list[str]:
    """The greppable `key<TAB>value` facts block, in stable order."""
    lines = [
        f"git_version\t{facts['git_version']}",
        f"platform\t{facts['platform']}",
        f"gitconfig\t{facts['gitconfig']}",
        f"includes\t{facts['includes'] or '(none)'}",
        f"signing.gpgsign\t{facts['gpgsign'] or 'false'}",
        f"signing.format\t{facts['format'] or '(unset)'}",
        f"signing.key\t{facts['signkey'] or '(unset)'}",
        f"signing.allowedSigners\t{facts['signers'] or '(unset)'}",
        f"pager\t{facts['pager'] or '(unset, plain less)'}",
        f"delta_installed\t{facts['delta'] or 'no'}",
    ]
    for key in DEFAULT_FACT_KEYS:
        lines.append(f"default.{key}\t{facts['defaults'].get(key) or '(unset)'}")
    lines.append(f"global_gitignore\t{facts['global_gitignore']}")
    lines.append(f"credential.helper\t{facts['cred'] or '(unset)'}")
    lines.append(f"identity.name\t{facts['name'] or '(unset)'}")
    lines.append(f"identity.email\t{facts['email'] or '(unset)'}")
    lines.append(f"identity.email_from\t{facts['email_origin'] or '(unset)'}")
    lines.append(f"identity.includeif\t{facts['includeif'] or '(none)'}")
    return lines


def format_gaps(findings: list[tuple[str, str, str]]) -> list[str]:
    """The gap report: header, then gap/fix lines sorted R → Y → G, then a verdict."""
    lines = ["-- gaps (🔴 fix now / 🟡 should fix / 🟢 nice to have) --"]
    for severity in ("R", "Y", "G"):
        for sev, msg, fix in findings:
            if sev != severity:
                continue
            lines.append(f"gap\t{SEVERITY_EMOJI[severity]}\t{msg}")
            if fix:
                lines.append(f"fix\t  {fix}")
    if not findings:
        lines.append("gap\t✅\tnone — global git config is in good shape")
    return lines


# --- IO: collect the raw facts -------------------------------------------------

def collect_facts() -> dict:
    """Gather every fact the report needs (all read-only git/uname/PATH probes)."""
    home = Path.home()
    main = str(home / ".gitconfig")
    gitconfig = main if Path(main).is_file() else "(none)"

    excludes = gc.getg("core.excludesfile")
    xdg_ignore = Path(os.environ.get("XDG_CONFIG_HOME") or (home / ".config")) / "git" / "ignore"
    xdg_ignore_exists = xdg_ignore.is_file()
    if excludes:
        global_gitignore = f"{excludes} (core.excludesfile)"
    elif xdg_ignore_exists:
        global_gitignore = f"{xdg_ignore} (XDG default, active)"
    else:
        global_gitignore = "(none)"

    return {
        "git_version": gc.git_version(),
        "platform": gc.uname_s(),
        "gitconfig": gitconfig,
        "includes": includes_from(gc.get_regexp_global(r"^include\.")),
        "gpgsign": gc.getg("commit.gpgsign"),
        "format": gc.getg("gpg.format"),
        "signkey": gc.getg("user.signingkey"),
        "signers": gc.getg("gpg.ssh.allowedSignersFile"),
        "pager": gc.getg("core.pager"),
        "delta": gc.command_v("delta"),
        "defaults": {k: gc.getg(k) for k in DEFAULT_FACT_KEYS},
        "excludes": excludes,
        "xdg_ignore_exists": xdg_ignore_exists,
        "global_gitignore": global_gitignore,
        "cred": gc.getg("credential.helper"),
        "name": gc.config_get("user.name"),
        "email": gc.config_get("user.email"),
        "email_origin": first_email_origin(gc.config_list_show_origin()),
        "includeif": includeif_keys_from(gc.get_regexp_global(r"^includeif\.")),
        "alias_count": len(gc.get_regexp_global(r"^alias\.")),
    }


def main(argv: list[str] | None = None) -> int:
    facts = collect_facts()
    lines = format_facts(facts)
    lines += format_gaps(evaluate_gaps(facts))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
