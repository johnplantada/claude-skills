#!/usr/bin/env python3
"""A plaintext-secret TRIPWIRE for the chezmoi source tree — safe by construction.

This is NOT a general secret scanner. It is a lightweight, zero-dependency guardrail
that runs *inside an agent* with one hard rule: a secret's VALUE never enters output or
the model's context — only a file path plus the reason it was flagged (a rule/pattern
NAME or a path shape). For real, repo-wide scanning use a dedicated tool:
gitleaks (https://github.com/gitleaks/gitleaks), trufflehog, or detect-secrets.

If **gitleaks** is installed it is used as the content engine (run with `--redact`, and
we read only the file + rule id from its JSON — never a match/secret field); otherwise a
small built-in pattern set is the fallback. Either way the output stays metadata-only.
Path-shape ("secret-by-location") detection is always the built-in check, since it knows
chezmoi's source encoding (`private_dot_ssh/`, `encrypted_*`) that gitleaks does not.

  secret_scan.py            # scan the chezmoi source tree (chezmoi source-path)
  secret_scan.py <path>     # scan an explicit dir/file (e.g. a file about to be added)

Output: one `<path>\treason=<why>` line per finding (sorted, de-duped) on stdout.
Exit: 0 = clean, 1 = findings to review, 2 = usage error. `.git/` is skipped.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile

import _dotfiles_common as dc

# --- Built-in content patterns (fallback when gitleaks is absent): high-signal shapes.
# Only the pattern NAME is ever emitted — the matched text stays out of output/context.
CONTENT_PATTERNS: list[tuple[str, str]] = [
    ("private-key-block", r"BEGIN [A-Z ]*PRIVATE KEY"),
    ("aws-access-key-id", r"AKIA[0-9A-Z]{16}"),
    ("github-token", r"gh[pousr]_[A-Za-z0-9]{16,}"),
    ("slack-token", r"xox[bapr]-[A-Za-z0-9-]{10,}"),
    ("generic-assignment", r"""(api[_-]?key|secret|token|password|passwd)["'\\ ]*[:=]"""),
]

# --- Location pattern: source files whose TARGET path is secret-by-location. Matches
# BOTH raw home paths (`.ssh/`) and chezmoi's source encoding (`dot_ssh/`,
# `private_dot_ssh/`). Each token is anchored to a path-segment start so, e.g.,
# `uv.env.fish` does NOT trip the `.env` (dotenv) rule.
LOCATION_REGEX = (
    r"(^|/)(private_|encrypted_)?(dot_|\.)ssh/"
    r"|(^|/)(dot_|\.)aws/"
    r"|(^|/)(private_|encrypted_)?(dot_|\.)netrc"
    r"|/gh/hosts\.yml"
    r"|(^|/)[^/]*credentials"
    r"|(^|/)(dot_|\.)env($|\.)"
)

_LOCATION_RE = re.compile(LOCATION_REGEX)
_CONTENT_RES: list[tuple[str, re.Pattern[str]]] = [
    (name, re.compile(regex)) for name, regex in CONTENT_PATTERNS
]


def scan_text_for_names(text: str) -> list[str]:
    """Names of every built-in content pattern that matches `text`, in pattern order.
    Returns only the names — never the matched substring (the safety contract)."""
    return [name for name, rx in _CONTENT_RES if rx.search(text)]


def location_reason(path: str) -> str | None:
    """The reason string if `path` is secret-by-location, else None. A source basename
    starting with `encrypted_` is the safe (ciphertext) form and is exempt."""
    base = path.rsplit("/", 1)[-1]
    if base.startswith("encrypted_"):
        return None
    if _LOCATION_RE.search(path):
        return "location:secret-by-location (encrypt or template instead)"
    return None


# --- Content engine: gitleaks when present, built-in patterns otherwise --------------

def gitleaks_available() -> bool:
    return dc.command_available("gitleaks")


def parse_gitleaks_report(report_json: str, base: str = "") -> set[str]:
    """Turn a gitleaks JSON report into `<file>\treason=gitleaks:<rule>` lines.

    A relative finding path is anchored to `base` (the scanned target dir) so both
    engines emit the same path shape — the built-in scanner walks real paths.

    SAFETY: reads ONLY the file path and rule id from each finding. The `Match`/`Secret`/
    line fields (redacted or not) are deliberately never touched, so no secret material
    can reach output or the model's context.
    """
    try:
        data = json.loads(report_json or "[]")
    except (ValueError, TypeError):
        return set()
    out: set[str] = set()
    for finding in data if isinstance(data, list) else []:
        if not isinstance(finding, dict):
            continue
        path = finding.get("File") or finding.get("file") or ""
        rule = finding.get("RuleID") or finding.get("rule") or "secret"
        if path:
            if base and not os.path.isabs(path):
                path = os.path.join(base, path)
            out.add(f"{path}\treason=gitleaks:{rule}")
    return out


def gitleaks_findings(target: str) -> set[str] | None:
    """Run gitleaks over `target` (REDACTED) and return metadata-only finding lines,
    or None if gitleaks produced no report (a run error — caller should fall back rather
    than trust a silent 'clean'). `--redact` keeps secrets out of gitleaks' own output."""
    with tempfile.TemporaryDirectory() as tmp:
        report = os.path.join(tmp, "gl.json")
        dc._run([
            "gitleaks", "detect", "--source", target, "--no-git", "--redact",
            "--report-format", "json", "--report-path", report,
            "--exit-code", "0", "--no-banner",
        ])
        text = dc.read_text_skip_binary(report)
        if text is None:
            return None
        base = target if os.path.isdir(target) else os.path.dirname(target)
        return parse_gitleaks_report(text, base)


def builtin_content_findings(target: str) -> set[str]:
    """Built-in fallback: pattern-match each file's content, emitting only rule names."""
    out: set[str] = set()
    for path in dc.iter_files(target):
        text = dc.read_text_skip_binary(path)
        if text is not None:
            for name in scan_text_for_names(text):
                out.add(f"{path}\treason=content:{name}")
    return out


def content_findings(target: str) -> tuple[set[str], str]:
    """Content-based findings plus the engine that ACTUALLY produced them: prefer
    gitleaks, fall back to the built-in patterns (also when gitleaks is present but
    errors — never trust a silent clean, and never label the fallback as gitleaks)."""
    if gitleaks_available():
        found = gitleaks_findings(target)
        if found is not None:
            return found, "gitleaks"
    return builtin_content_findings(target), "built-in patterns"


def scan(target: str) -> tuple[list[str], str]:
    """Sorted, de-duplicated finding lines (`<path>\treason=...`) for `target`, plus
    the content-engine name for the summary line."""
    findings, engine = content_findings(target)
    findings = set(findings)
    # Location shapes are chezmoi-source-encoding aware — always the built-in check
    # (location_reason itself exempts the encrypted_* ciphertext form).
    for path in dc.iter_files(target):
        reason = location_reason(path)
        if reason is not None:
            findings.add(f"{path}\treason={reason}")
    return sorted(findings), engine


def resolve_target(args: list[str]) -> str:
    """The path to scan: an explicit argument, else the chezmoi source tree. Raises
    SystemExit(2) with the bash script's messages on any resolution/usage failure."""
    if args:
        target = args[0]
    else:
        if not dc.chezmoi_available():
            print("chezmoi not installed and no path given", file=sys.stderr)
            raise SystemExit(2)
        target = dc.chezmoi_source_path()
        if not target:
            print("could not resolve chezmoi source-path", file=sys.stderr)
            raise SystemExit(2)
    if not os.path.exists(target):
        print(f"no such path: {target}", file=sys.stderr)
        raise SystemExit(2)
    return target


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    target = resolve_target(args)

    findings, engine = scan(target)
    if findings:
        print("\n".join(findings))
        print(
            f"findings\t{len(findings)}\t({engine}) — REVIEW each: encrypt "
            f"(chezmoi add --encrypt), template, or .chezmoiignore",
            file=sys.stderr,
        )
        return 1
    print(f"clean\tno plaintext-secret indicators in {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
