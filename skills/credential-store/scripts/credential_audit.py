#!/usr/bin/env python3
"""Find every credential sitting in plaintext on this machine. Read-only.
Part of the credential-store skill.

    credential_audit.py                   # shell startup files + known credential files + git/gh
    credential_audit.py --shell-only      # just the shell rc sweep (fast)
    credential_audit.py --all-assignments # + a redacted inventory of EVERY assignment,
                                          #   for reviewing what the name heuristic missed

The question is not "is there a secret here" — `dotfiles`' secret_scan.py already answers
that for the chezmoi SOURCE tree, before a commit. This asks the LIVE machine a different
question: for each credential the environment provides, is it a **literal** baked into a
config file, or a **reference** resolved from a store at use time?

That classification is the whole skill. A literal is a credential readable by anything
that can read the file — and, in a shell rc, it is also in the environment of every
process you launch. A reference (`$(op read …)`, `$(security find-generic-password …)`)
leaves nothing on disk.

SECRETS: no finding carries a value. `scan_assignments` classifies the right-hand side
and DISCARDS it, so a finding is (line number, variable name, classification) and cannot
carry a secret even if a formatter tried to print one. Variable names and paths are
metadata and are reported, because a finding you can't act on is useless.

Exit 0 when there are no 🔴 findings, 1 when there are.
"""

from __future__ import annotations

import os
import re
import sys

import _credential_common as cc

RED, YELLOW, GREEN = "🔴", "🟡", "🟢"

# Names that denote a credential. Deliberately broad — a false positive costs one glance,
# a false negative leaves a token on disk.
_CRED_NAME_RE = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|API_?KEY|ACCESS_?KEY|PRIVATE_?KEY|AUTH)", re.IGNORECASE
)
# Suffixes that make a credential-ish name a pointer instead: FOO_KEY_PATH is a path.
_NOT_SECRET_SUFFIXES = ("_PATH", "_FILE", "_DIR", "_URL", "_ENABLED", "_METHOD", "_NAME", "_ID")

_POSIX_ASSIGN_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_FISH_ASSIGN_RE = re.compile(r"^\s*set\s+(?:-[A-Za-z]+\s+)*([A-Za-z_][A-Za-z0-9_]*)\s+(.+)$")
# A command substitution that just reads a file is still plaintext-on-disk, one step away.
_FILE_READ_RE = re.compile(r"\$\(\s*(?:cat|<)\s|\$\(\s*head\s")


# --- pure logic: classification ------------------------------------------------


def parse_assignment(line: str) -> tuple[str, str] | None:
    """`(variable, right_hand_side)` for an assignment line, or None.

    Handles POSIX (`export FOO=…`, `FOO=…`) and fish (`set -gx FOO …`). Comment lines are
    not assignments. The RHS is returned so the caller can CLASSIFY it — never so it can
    be reported.
    """
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    for pattern in (_POSIX_ASSIGN_RE, _FISH_ASSIGN_RE):
        match = pattern.match(line)
        if match:
            return match.group(1), match.group(2).strip()
    return None


def is_credential_name(var: str) -> bool:
    """Does this variable name denote a credential (rather than a pointer to one)?"""
    upper = var.upper()
    if upper.endswith(_NOT_SECRET_SUFFIXES):
        return False
    return bool(_CRED_NAME_RE.search(upper))


def classify_rhs(rhs: str) -> str:
    """How a value is supplied: reference | file-reference | literal | path | empty.

    `reference` is the goal state — the value is fetched from a store at use time and is
    not on disk. `file-reference` reads a plaintext file, which is better than inlining
    but still leaves the secret readable. `literal` is the finding this skill exists for.
    """
    value = rhs.strip()
    if value[:1] in ("'", '"') and value[-1:] == value[:1] and len(value) >= 2:
        value = value[1:-1]
    value = value.strip()
    if not value:
        return "empty"
    if value.startswith(("/", "~", "./")):
        return "path"
    if _FILE_READ_RE.search(value):
        return "file-reference"
    if "$(" in value or "`" in value or value.startswith("$") or "${" in value:
        return "reference"
    if "{{" in value and "}}" in value:
        return "reference"
    return "literal"


def scan_assignments(lines: list[str]) -> list[tuple[int, str, str]]:
    """`(line_number, variable, classification)` for credential-named assignments.

    The RHS is classified and then dropped — it is deliberately absent from the return
    value, so no caller can print a secret even by mistake. This is the skill's core
    safety property, and it is structural rather than a matter of care.
    """
    findings = []
    for number, line in enumerate(lines, start=1):
        parsed = parse_assignment(line)
        if not parsed:
            continue
        var, rhs = parsed
        if not is_credential_name(var):
            continue
        findings.append((number, var, classify_rhs(rhs)))
    return findings


def severity_of(classification: str) -> str:
    """Severity for a shell-rc finding. `path`/`empty` are not findings at all."""
    return {
        "literal": RED,
        "file-reference": YELLOW,
        "reference": GREEN,
    }.get(classification, "")


def location_severity(mode: str) -> str:
    """A credential file is 🔴 if others can read it, 🟡 if it's plaintext but locked down."""
    if mode == "???" or len(mode) < 3:
        return YELLOW
    return RED if mode[-2:] != "00" else YELLOW


# --- pure logic: formatting ----------------------------------------------------


def format_findings(findings: list[tuple[str, str, str, str]]) -> list[str]:
    """The finding section, sorted 🔴 → 🟡 → 🟢, stable within a severity."""
    if not findings:
        return ["finding\t(none — no credential-shaped assignment or known credential file found)"]
    order = {RED: 0, YELLOW: 1, GREEN: 2}
    ranked = sorted(findings, key=lambda f: order.get(f[0], 9))
    return [f"finding\t{sev}\t{surface}\t{where}\t{why}" for sev, surface, where, why in ranked]


def shell_findings(path: str, scanned: list[tuple[int, str, str]]) -> list[tuple[str, str, str, str]]:
    """Turn one file's classified assignments into report findings."""
    out = []
    for number, var, classification in scanned:
        severity = severity_of(classification)
        if not severity:
            continue
        why = {
            "literal": f"{var} is a literal in a shell rc — plaintext on disk, and exported "
                       "into every process you launch",
            "file-reference": f"{var} is read from a plaintext file at shell start — better "
                              "than inlining, still readable",
            "reference": f"{var} resolves from a store at shell start",
        }[classification]
        out.append((severity, "shell", f"{path}:{number}", why))
    return out


# --- collection (IO) -----------------------------------------------------------


def inventory_rows(path: str, lines: list[str]) -> list[str]:
    """A REDACTED inventory of every assignment in a file — names and shapes, no values.

    `--all-assignments` exists so a reviewer (human or subagent) can catch credentials the
    name heuristic missed — `STRIPE_SK`, `SLACK_WEBHOOK`, a bare `DSN` — which need world
    knowledge a regex doesn't have. Emitting classification instead of value is what makes
    that review safe to delegate: the reader sees `literal`, never the literal.
    """
    rows = []
    for number, line in enumerate(lines, start=1):
        parsed = parse_assignment(line)
        if not parsed:
            continue
        var, rhs = parsed
        flagged = "yes" if is_credential_name(var) else "no"
        rows.append(f"assignment\t{path}:{number}\t{var}\t{classify_rhs(rhs)}\tflagged={flagged}")
    return rows


def sweep_shell(*, inventory: bool = False) -> tuple[list[str], list[tuple[str, str, str, str]], list[str]]:
    """Scan every shell startup file. Returns (files_scanned, findings, inventory_rows).

    Each file is read exactly ONCE and both outputs derive from those lines. The earlier
    version re-read every file to build the inventory, which doubled IO on precisely the
    files that hold credentials — the last place to open twice for no reason.
    """
    files = cc.existing_shell_rc_files()
    findings: list[tuple[str, str, str, str]] = []
    rows: list[str] = []
    for path in files:
        lines = cc.read_lines(path)
        findings += shell_findings(path, scan_assignments(lines))
        if inventory:
            rows += inventory_rows(path, lines)
    return files, findings, rows


def sweep_files() -> list[tuple[str, str, str, str]]:
    """Known credential-bearing files present on this machine. Never opens the by-location set."""
    findings = []
    for raw, holds in cc.SECRET_BY_LOCATION:
        path = cc.expand(raw)
        if os.path.isfile(path):
            mode = cc.file_mode(path)
            findings.append((location_severity(mode), "file", f"{path} (mode={mode})",
                             f"plaintext {holds} — move to a store and delete the file"))
    for raw, pattern, holds in cc.CONDITIONAL_SECRET_FILES:
        path = cc.expand(raw)
        if os.path.isfile(path) and cc.matches_marker(path, pattern):
            mode = cc.file_mode(path)
            findings.append((location_severity(mode), "file", f"{path} (mode={mode})",
                             f"contains {holds}"))
    return findings


def sweep_helpers() -> tuple[list[str], list[tuple[str, str, str, str]]]:
    """git + gh credential storage. Returns (fact_rows, findings)."""
    facts, findings = [], []

    helper = cc.git_credential_helper()
    facts.append(f"git.credential_helper\t{helper or '(unset)'}")
    if helper == "store":
        findings.append((RED, "git", "credential.helper=store",
                         "git writes HTTPS credentials to ~/.git-credentials in cleartext — use osxkeychain"))
    elif not helper:
        findings.append((YELLOW, "git", "credential.helper=(unset)",
                         "no helper, so HTTPS pushes re-prompt or fall back to a cleartext file"))

    gh_installed, gh_raw = cc.gh_auth_raw()
    if not gh_installed:
        facts.append("gh.storage\t(gh not installed)")
    elif "keyring" in gh_raw:
        facts.append("gh.storage\tkeyring")
    elif "Logged in" in gh_raw:
        facts.append("gh.storage\tfile")
        findings.append((YELLOW, "gh", "~/.config/gh/hosts.yml",
                         "gh stores its token in a file rather than the keyring — `gh auth login` again to move it"))
    else:
        facts.append("gh.storage\t(not logged in)")
    return facts, findings


# --- entrypoint ----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "-h" in args or "--help" in args:
        print(__doc__.strip())
        return 0
    shell_only = "--shell-only" in args

    files, findings, inventory = sweep_shell(inventory="--all-assignments" in args)
    lines = [f"scanned\tshell_rc_files={len(files)}"]
    lines += [f"scanned.file\t{p}" for p in files]
    lines += inventory

    if not shell_only:
        facts, helper_findings = sweep_helpers()
        lines += facts
        findings += sweep_files() + helper_findings

    reds = sum(1 for f in findings if f[0] == RED)
    lines.append(f"summary\tfindings={len(findings)}\tred={reds}\tscope={'shell' if shell_only else 'full'}")
    print("\n".join(lines + format_findings(findings)))
    return 1 if reds else 0


if __name__ == "__main__":
    sys.exit(main())
