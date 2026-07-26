#!/usr/bin/env python3
"""Resolve one shell's REAL user environment and print it, greppable.

Runs the shell as a clean login+interactive shell (wiped env, full rc load) so
evals, sources, and macOS path_helper are all applied — then reads the resolved
state. Replaces the hand-composed ``env -i … zsh -l -i -c '…'`` blocks in the
reference docs. Read-only; safe to re-run. Part of the shell-sync skill.

Usage:
    dump_env.py <zsh|fish> [path|exports|aliases|functions|all]

    dump_env.py zsh                 # all sections, tag-prefixed overview
    dump_env.py zsh path            # one PATH dir per line (raw, pipeline-friendly)
    dump_env.py zsh exports         # NAME=value per exported var
    dump_env.py zsh aliases         # name=value per alias
    dump_env.py zsh functions       # one function name per line
    dump_env.py fish path           # same, from fish (if installed)

Single section  -> raw lines (composable: feed to path-doctor / diff).
`all` (default) -> each line prefixed  path<TAB> / export<TAB> / alias<TAB> / function<TAB>.
If the requested shell isn't installed: prints a note to stderr, exits 3.
"""

from __future__ import annotations

import re
import sys

import _shell_common as sc

SHELLS = ("zsh", "fish")
SECTIONS = ("path", "exports", "aliases", "functions", "all")

USAGE = __doc__ or ""


# --- pure logic: what to run, and how to parse what comes back -----------------

def section_command(shell: str, section: str) -> str:
    """The command string this shell runs to emit one section's raw lines."""
    if section == "path":
        return "for p in $PATH; echo $p; end" if shell == "fish" else 'printf "%s\\n" $path'
    if section == "exports":
        return "env"
    if section == "aliases":
        return "alias"
    if section == "functions":
        return "functions -n" if shell == "fish" else "print -l ${(k)functions}"
    raise ValueError(f"unknown section: {section}")


def parse_functions(shell: str, raw: str) -> list[str]:
    """Function names from the shell's raw output, sorted and de-duplicated.

    fish prints them comma-separated (``functions -n``); zsh one per line. Both are
    normalized to a sorted, unique list (the bash version's ``tr ',' '\\n' | sed |
    sort -u`` / ``sort -u``).
    """
    parts = re.split(r"[,\n]", raw) if shell == "fish" else raw.splitlines()
    return sorted({p.strip() for p in parts if p.strip()})


def tag_all(
    path_lines: list[str],
    export_lines: list[str],
    alias_lines: list[str],
    function_lines: list[str],
) -> list[str]:
    """The `all` overview: each section's lines prefixed with its tag."""
    out: list[str] = []
    out += [f"path\t{line}" for line in path_lines]
    out += [f"export\t{line}" for line in export_lines]
    out += [f"alias\t{line}" for line in alias_lines]
    out += [f"function\t{line}" for line in function_lines]
    return out


# --- IO: run the shell and hand its output to the pure parsers -----------------

def resolve_section(shell: str, section: str, binary: str) -> list[str]:
    """Run one section in the clean login shell and return its parsed lines."""
    raw = sc.run_login(binary, section_command(shell, section))
    if section == "functions":
        return parse_functions(shell, raw)
    return raw.splitlines()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    shell = args[0] if args else ""
    section = args[1] if len(args) > 1 else "all"

    if shell not in SHELLS:
        print(USAGE)
        return 2
    if section not in SECTIONS:
        print(USAGE)
        return 2

    binary = sc.resolve_bin(shell)
    if not binary:
        print(f"dump-env: {shell} not installed — skipping", file=sys.stderr)
        return 3

    if section == "all":
        lines = tag_all(
            resolve_section(shell, "path", binary),
            resolve_section(shell, "exports", binary),
            resolve_section(shell, "aliases", binary),
            resolve_section(shell, "functions", binary),
        )
    else:
        lines = resolve_section(shell, section, binary)

    if lines:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
