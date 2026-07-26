#!/usr/bin/env python3
"""Audit live prefs against a declared defaults script. Part of the macos-defaults
skill. Parses every `defaults write <domain> <key> <type> <value>` line out of the
given script and re-reads each target live, classifying MATCH / DRIFT / MISSING.
READ-ONLY: only `defaults read` runs — nothing is written, no app is restarted.

Usage:
    drift_audit.py ~/.config/devenv/macos.sh
    drift_audit.py ~/.config/devenv/macos.sh --quiet   # only DRIFT/MISSING lines

Output (greppable, stable order = script order), then a summary line:
    MATCH   com.apple.dock autohide = 1
    DRIFT   com.apple.dock tilesize: live=64 expected=48
    MISSING com.apple.finder ShowPathbar: not set, expected 1
    summary: 12 match, 1 drift, 1 missing (14 declared)

Type-aware compare: -bool true/yes/1 all normalize to 1 (and false/no/0 to 0), so a
`-bool true` line matches a live `1`. $HOME / ${HOME} / a leading ~ in a declared
string value are expanded before comparing. Exit status is non-zero if any drift.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Callable

import _macos_common as mc

_WRITE_RE = re.compile(r"^\s*defaults\s+write\s+(\S+)\s+(\S+)\s+(.*)$")
_TYPE_RE = re.compile(r"^-[a-zA-Z]+\s*")


def norm_bool(token: str) -> str:
    """Map a defaults boolean spelling to 1/0; pass anything else through unchanged."""
    if token in ("true", "TRUE", "True", "yes", "YES", "Yes", "1"):
        return "1"
    if token in ("false", "FALSE", "False", "no", "NO", "No", "0"):
        return "0"
    return token


def expand_home(value: str, home: str) -> str:
    """Expand $HOME, ${HOME}, and a leading ~ (declared string paths usually reference
    $HOME; live reads come back fully expanded). Deliberately narrow — no general eval."""
    if value == "~" or value.startswith("~/"):
        value = home + value[1:]
    value = value.replace("${HOME}", home)
    value = value.replace("$HOME", home)
    return value


def strip_trailing_comment(line: str) -> str:
    """Drop a trailing ` # comment` (whitespace-preceded hash to end of line)."""
    return re.sub(r"\s#.*$", "", line)


def parse_write_line(line: str) -> tuple[str, str, str, str] | None:
    """Parse a `defaults write` line into (domain, key, type, value), or None if the
    line isn't a write. Splits an optional leading `-type` flag off the value and strips
    one layer of matching surrounding quotes."""
    if "defaults write " not in line:
        return None
    if line.startswith("#"):
        return None
    code = strip_trailing_comment(line)
    m = _WRITE_RE.match(code)
    if not m:
        return None
    domain, key, rest = m.group(1), m.group(2), m.group(3)

    type_ = ""
    if rest.startswith("-"):
        type_ = rest.split()[0]
        rest = _TYPE_RE.sub("", rest, count=1)

    value = rest.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return domain, key, type_, value


def collapse_live(raw: str) -> str:
    """Collapse a live read to one line: newlines→space, squeeze spaces, strip trailing."""
    s = re.sub(r" +", " ", raw.replace("\n", " "))
    return re.sub(r"\s+$", "", s)


def normalize_pair(type_: str, declared: str, live: str, home: str) -> tuple[str, str]:
    """Type-aware (expected, comparable-live) pair for the equality check."""
    if type_ == "-bool":
        return norm_bool(declared), norm_bool(live)
    if type_ in ("-string", ""):
        return expand_home(declared, home), live
    return declared, live


def audit(
    text: str,
    read_key: Callable[[str, str], tuple[bool, str]],
    home: str,
    quiet: bool = False,
) -> tuple[list[str], int, int, int, int]:
    """Build the report lines and the (match, drift, miss, declared) counts.

    `read_key(domain, key) -> (ok, raw_value)` is injected so the pure classification is
    testable without touching the `defaults` CLI.
    """
    lines: list[str] = []
    n_match = n_drift = n_miss = n_decl = n_unparsed = 0

    for line in text.splitlines():
        parsed = parse_write_line(line)
        if parsed is None:
            # A line that clearly INTENDS to be a `defaults write` but doesn't parse was
            # previously skipped in silence — so a declared setting simply went
            # unaudited while the summary still read "0 drift". Under-reporting drift is
            # the one thing this tool must never do, so say it out loud instead.
            if "defaults write " in line and not line.lstrip().startswith("#"):
                n_unparsed += 1
                lines.append(mc.unparsed_line(line, "not a parsable `defaults write` — NOT audited"))
            continue
        domain, key, type_, value = parsed
        n_decl += 1

        ok, raw = read_key(domain, key)
        if not ok:
            n_miss += 1
            lines.append(f"MISSING {domain} {key}: not set, expected {value}")
            continue
        live = collapse_live(raw)

        exp, cmp = normalize_pair(type_, value, live, home)
        if exp == cmp:
            n_match += 1
            if not quiet:
                lines.append(f"MATCH   {domain} {key} = {live}")
        else:
            n_drift += 1
            lines.append(f"DRIFT   {domain} {key}: live={live} expected={value}")

    summary = (
        f"summary: {n_match} match, {n_drift} drift, {n_miss} missing "
        f"({n_decl} declared)"
    )
    if n_unparsed:
        summary += f" — {n_unparsed} line(s) UNPARSED and not audited"
    lines.append(summary)
    return lines, n_match, n_drift, n_miss, n_decl


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    script = args[0] if args else ""
    quiet = len(args) >= 2 and args[1] == "--quiet"

    if script in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if not script:
        print("usage: drift_audit.py <macos.sh> [--quiet]", file=sys.stderr)
        return 2
    path = Path(script)
    if not path.is_file():
        print(f"not a file: {script}", file=sys.stderr)
        return 2

    home = os.environ.get("HOME", str(Path.home()))
    lines, _m, n_drift, n_miss, _d = audit(
        path.read_text(), mc.read_key, home, quiet=quiet
    )
    print("\n".join(lines))
    return 0 if (n_drift == 0 and n_miss == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
