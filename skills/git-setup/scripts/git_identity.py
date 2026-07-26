#!/usr/bin/env python3
"""Show which identity + signing key RESOLVES in a directory. Read-only.
Part of the git-setup skill.

    git_identity.py                  # identity that applies here (cwd)
    git_identity.py ~/work/some-repo # identity that applies in a work repo
    git_identity.py ~/personal/proj  # …in a personal repo

Evaluates the effective git config from inside <path> (default: cwd), so
`includeIf "gitdir:…"` conditional includes are applied exactly as git sees them.
Prints greppable `key<TAB>value`, names the file each value came from, and lists
the global includeIf rules.

NOTE: includeIf "gitdir:" only matches when <path> is (inside) a real git repo —
that's how git evaluates it. Non-repo paths resolve global + unconditional
includes only; the tool flags that so you don't misread the result.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import _git_common as gc


def origin_of(show_origin: str, key: str) -> str:
    """File that supplied `key` (awk -F'\\t' index($2,k)==1, tail -1, sed s/^file://).

    Scans `git config --list --show-origin` output (`origin<TAB>key=value` lines),
    keeps the LAST whose value field starts with `key=`, and strips the `file:` prefix.
    """
    prefix = f"{key}="
    result = ""
    for line in show_origin.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        origin, kv = parts
        if kv.startswith(prefix):
            result = origin
    return result[len("file:"):] if result.startswith("file:") else result


def format_rules(rules: list[str]) -> list[str]:
    """`rule<TAB>…` lines for the global includeIf rules, or the no-rules note."""
    if rules:
        return [f"rule\t{line}" for line in rules]
    return ["rule\t(none — every repo uses the global identity)"]


def format_identity(facts: dict) -> list[str]:
    """The greppable identity report lines (before the includeIf-rules section)."""
    return [
        f"query_path\t{facts['query_path']}",
        f"in_repo\t{facts['in_repo']}",
        f"repo_root\t{facts['repo_root']}",
        f"user.name\t{facts['name'] or '(unset)'}",
        f"user.email\t{facts['email'] or '(unset)'}",
        f"user.email_from\t{facts['email_from']}",
        f"signing.key\t{facts['signkey'] or '(unset)'}",
        f"signing.key_from\t{facts['signkey_from']}",
        f"signing.gpgsign\t{facts['gpgsign'] or '(unset)'}",
        f"signing.format\t{facts['format'] or '(unset)'}",
    ]


def collect_facts(directory: str) -> dict:
    """Resolve the effective config from inside `directory` (all read-only probes)."""
    if gc.is_inside_work_tree(directory):
        in_repo = "yes"
        toplevel = gc.show_toplevel(directory)
    else:
        in_repo = "no"
        toplevel = "(not a git repo — includeIf gitdir rules will NOT apply)"

    show_origin = gc.config_list_show_origin(directory)
    return {
        "query_path": directory,
        "in_repo": in_repo,
        "repo_root": toplevel,
        "name": gc.config_get("user.name", directory),
        "email": gc.config_get("user.email", directory),
        "email_from": origin_of(show_origin, "user.email"),
        "signkey": gc.config_get("user.signingkey", directory),
        "signkey_from": origin_of(show_origin, "user.signingkey"),
        "gpgsign": gc.config_get("commit.gpgsign", directory),
        "format": gc.config_get("gpg.format", directory),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    directory = args[0] if args else os.getcwd()
    if not Path(directory).is_dir():
        print(f"no such directory: {directory}", file=sys.stderr)
        return 2

    facts = collect_facts(directory)
    lines = format_identity(facts)
    lines.append("-- includeIf rules (global) --")
    lines += format_rules(gc.get_regexp_global(r"^includeif\."))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
