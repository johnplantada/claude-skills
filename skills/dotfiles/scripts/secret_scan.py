#!/usr/bin/env python3
"""Flag plaintext secrets in the chezmoi source tree, SAFELY. Part of the dotfiles skill.

  secret_scan.py            # scan the chezmoi source tree (chezmoi source-path)
  secret_scan.py <path>     # scan an explicit dir/file (e.g. a file about to be added)

SAFETY CONTRACT: this NEVER prints matched values or file contents — only a file
path plus the reason it was flagged (pattern *name* or *location*, never the text
that matched). Run it before any first-add and before every first commit. The #1
dotfiles hazard is a secret in git.

Output: one `<path>\treason=<why>` line per finding (sorted, de-duped) on stdout.
Exit: 0 = clean, 1 = findings to review, 2 = usage error. `.git/` is skipped.
"""

from __future__ import annotations

import os
import re
import sys

import _dotfiles_common as dc

# --- Content patterns: high-signal credential shapes. (name, extended-regex).
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
_CONTENT_RES: list[tuple[str, "re.Pattern[str]"]] = [
    (name, re.compile(regex)) for name, regex in CONTENT_PATTERNS
]


def scan_text_for_names(text: str) -> list[str]:
    """Names of every content pattern that matches `text`, in pattern order. Returns
    only the names — never the matched substring (the safety contract)."""
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


def scan(target: str) -> list[str]:
    """Sorted, de-duplicated finding lines (`<path>\treason=...`) for `target`."""
    findings: set[str] = set()
    for path in dc.iter_files(target):
        base = path.rsplit("/", 1)[-1]

        # Content: read the file (binary skipped, like `grep -I`); emit pattern names only.
        text = dc.read_text_skip_binary(path)
        if text is not None:
            for name in scan_text_for_names(text):
                findings.add(f"{path}\treason=content:{name}")

        # Location: filename/path shape only — no read. `encrypted_*` is exempt.
        if not base.startswith("encrypted_"):
            reason = location_reason(path)
            if reason is not None:
                findings.add(f"{path}\treason={reason}")

    return sorted(findings)


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

    findings = scan(target)
    if findings:
        print("\n".join(findings))
        print(
            f"findings\t{len(findings)}\t— REVIEW each: encrypt (chezmoi add --encrypt), "
            f"template, or .chezmoiignore",
            file=sys.stderr,
        )
        return 1
    print(f"clean\tno plaintext-secret indicators in {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
