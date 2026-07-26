#!/usr/bin/env python3
"""tool_resolve.py [tool ...] — "who resolves this runtime?" the core diagnostic.

For each tool (default: node python go ruby) prints, as `key<TAB>value` lines, what
THIS script's shell actually resolves and which manager owns it:
    <t>_command_v   what `command -v <t>` returns here (a shim, a real binary, or absent)
    <t>_real_path   symlinks followed to the real file (mise/brew shims are symlinks)
    <t>_owner       classified: mise | nvm | pyenv | rbenv | asdf | fnm | homebrew | system | other
    <t>_mise_says   `mise which <t>` — where mise WOULD point (or that mise is absent)
    <t>_on_path     count of every <t> on PATH (2+ = dupes = sprawl) + the list
Collapses the per-tool `command -v` / `which -a` / `mise which` block from optimize.md.

CONTEXT: this queries the NON-INTERACTIVE shell this script runs in — it inherits the
caller's PATH, NOT a fresh login. Managers loaded only by interactive/login rc (e.g.
nvm, a shell function) may be INVISIBLE here. For the real per-shell answer from a clean
login, use shell_resolve.py. The first output line states the context.
"""

from __future__ import annotations

import fnmatch
import os
import sys

import _runtime_common as rc

# Ordered (glob, owner) — first match wins, exactly like the bash `case`.
_CLASSIFY = [
    ("*/mise/shims/*", "mise"),
    ("*/.local/share/mise/*", "mise"),
    ("*/mise/installs/*", "mise"),
    ("*/.nvm/*", "nvm"),
    ("*/.pyenv/*", "pyenv"),
    ("*/.rbenv/*", "rbenv"),
    ("*/.asdf/*", "asdf"),
    ("*/.fnm/*", "fnm"),
    ("*/fnm_multishells/*", "fnm"),
    ("*/Caches/fnm*", "fnm"),
    ("/opt/homebrew/*", "homebrew"),
    ("/usr/local/Cellar/*", "homebrew"),
    ("/usr/local/opt/*", "homebrew"),
    ("/usr/bin/*", "system"),
    ("/bin/*", "system"),
]


def classify(path: str) -> str:
    """Classify a resolved binary path to its owning manager (or 'other')."""
    for glob, owner in _CLASSIFY:
        if fnmatch.fnmatch(path, glob):
            return owner
    return "other"


def format_on_path(entries: list[str]) -> str:
    """The `<count> entr(y/ies): <list>` tail for `which -a` results ((none) if empty)."""
    joined = "".join(p + " " for p in entries)
    listout = joined or "(none)"
    return f"{len(entries)} entr(y/ies): {listout}"


def context_line() -> str:
    """The leading context line naming the shell this script runs in."""
    shell = os.environ.get("SHELL", "").rsplit("/", 1)[-1]
    return (
        f"context\tnon-interactive shell ({shell}), inherits caller PATH — "
        "see shell_resolve.py for clean per-shell truth"
    )


def tool_lines(tool: str, have_mise: bool) -> list[str]:
    """Every output line for one tool."""
    lines: list[str] = []
    cv = rc.command_v(tool)
    if not cv:
        lines.append(f"{tool}_command_v\t(not found on PATH)")
        lines.append(f"{tool}_owner\tnone")
    else:
        real = rc.realpath(cv)
        lines.append(f"{tool}_command_v\t{cv}")
        lines.append(f"{tool}_real_path\t{real}")
        lines.append(f"{tool}_owner\t{classify(real)}")

    if have_mise:
        mw = rc.run(["mise", "which", tool]).stdout.strip()
        lines.append(f"{tool}_mise_says\t{mw or f'(mise has no version for {tool} in this dir)'}")
    else:
        lines.append(f"{tool}_mise_says\t(mise not installed)")

    lines.append(f"{tool}_on_path\t{format_on_path(rc.which_all(tool))}")
    return lines


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    tools = args or ["node", "python", "go", "ruby"]
    have_mise = rc.have("mise")

    print(context_line())
    for tool in tools:
        for line in tool_lines(tool, have_mise):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
