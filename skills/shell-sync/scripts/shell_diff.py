#!/usr/bin/env python3
"""Diff zsh vs fish so you can prove they agree (or find where they diverge).

Compares the resolved PATH set, checks each shell starts clean, and resolves a
list of tools in both. Collapses the comm/``command -v``/startup-grep blocks in
verification.md. Read-only. If fish isn't installed it says so and does the
zsh-only checks it can. Part of the shell-sync skill.

Usage:
    shell_diff.py [tool ...]

    shell_diff.py                 # PATH set diff + startup + default tool list
    shell_diff.py node go deno    # also resolve these specific tools in both

Greppable output:
    only_in_zsh<TAB>/dir<TAB>benign …|review    PATH dir zsh has and fish lacks
    only_in_fish<TAB>/dir<TAB>benign …|review    PATH dir fish has and zsh lacks
    startup<TAB>zsh<TAB>clean|issues
    startup<TAB>fish<TAB>clean|issues|absent
    tool<TAB>node<TAB>zsh=/path|-<TAB>fish=/path|-|?   (- = not found, ? = fish absent)
"""

from __future__ import annotations

import os
import re
import sys
from typing import Callable

import _shell_common as sc
import dump_env

VENDORS = [
    "/opt/homebrew/share/fish/vendor_conf.d",
    "/usr/local/share/fish/vendor_conf.d",
]
DEFAULT_TOOLS = ["node", "cargo", "go", "rustc", "python3", "ruby"]

# Tool names are interpolated into `command -v <t>` run by a login shell — they must
# be plain command names, never shell syntax.
_TOOL_NAME_RE = re.compile(r"[A-Za-z0-9@._+-]+")

ZSH_STARTUP = re.compile(r"error|not found|parse error|bad pattern|command not found", re.IGNORECASE)
FISH_STARTUP = re.compile(r"error|unknown command|expected|missing", re.IGNORECASE)


# --- pure logic ----------------------------------------------------------------

def only_in(a: set[str], b: set[str]) -> list[str]:
    """Sorted, non-empty entries in set ``a`` that are not in set ``b``."""
    return sorted(x for x in (a - b) if x)


def classify_zsh(d: str, is_dir: Callable[[str], bool], syspaths: set[str]) -> str:
    """Classify a zsh-only PATH dir: system path_helper noise vs a real divergence."""
    if not is_dir(d):
        return "benign (dead/system path_helper)"
    if d in syspaths:
        return "benign (path_helper)"
    return "review"


def classify_fish(d: str, is_dir: Callable[[str], bool], vendor_has: Callable[[str], bool]) -> str:
    """Classify a fish-only PATH dir: a brew-vendor keg activation vs a real divergence."""
    m = re.match(r".*/opt/([^/]+)/bin$", d)
    if m:
        keg = m.group(1)
        if vendor_has(keg):
            return f"benign (brew vendor activation: {keg})"
    if not is_dir(d):
        return "benign (dead)"
    return "review"


def startup_status(shell: str, output: str) -> str:
    """`clean` or `issues` from a shell's captured startup output."""
    pat = ZSH_STARTUP if shell == "zsh" else FISH_STARTUP
    return "issues" if pat.search(output) else "clean"


def tool_line(tool: str, zpath: str, fpath: str) -> str:
    """Format one tool-reachability row."""
    return f"tool\t{tool}\tzsh={zpath}\tfish={fpath}"


# --- IO ------------------------------------------------------------------------

def _read_syspaths() -> set[str]:
    """The macOS path_helper source dirs: /etc/paths + /etc/paths.d/* (nonempty lines)."""
    out: set[str] = set()
    files = ["/etc/paths"]
    d = "/etc/paths.d"
    if os.path.isdir(d):
        files += [os.path.join(d, f) for f in sorted(os.listdir(d))]
    for f in files:
        for line in sc.read_text(f).splitlines():
            if line.strip():
                out.add(line)
    return out


def _vendor_has(keg: str) -> bool:
    """True if any fish vendor_conf.d activation file name matches ``keg`` (case-insensitive)."""
    pat = re.compile(keg, re.IGNORECASE)
    for v in VENDORS:
        try:
            entries = os.listdir(v)
        except OSError:
            continue
        if any(pat.search(name) for name in entries):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    for t in args:
        if not _TOOL_NAME_RE.fullmatch(t):
            print(f"shell-diff: invalid tool name: {t!r} (letters/digits/@._+- only)", file=sys.stderr)
            return 2

    zbin = sc.resolve_bin("zsh")
    if not zbin:
        print("shell-diff: zsh not installed", file=sys.stderr)
        return 3
    fbin = sc.resolve_bin("fish")

    zset = {l for l in dump_env.resolve_section("zsh", "path", zbin) if l}
    fset = {l for l in dump_env.resolve_section("fish", "path", fbin) if l} if fbin else set()

    syspaths = _read_syspaths()
    out: list[str] = []

    for d in only_in(zset, fset):
        out.append(f"only_in_zsh\t{d}\t{classify_zsh(d, os.path.isdir, syspaths)}")
    if fbin:
        for d in only_in(fset, zset):
            out.append(f"only_in_fish\t{d}\t{classify_fish(d, os.path.isdir, _vendor_has)}")

    out.append(f"startup\tzsh\t{startup_status('zsh', sc.run_login(zbin, 'exit', combine_stderr=True))}")
    if fbin:
        out.append(f"startup\tfish\t{startup_status('fish', sc.run_login(fbin, 'exit', combine_stderr=True))}")
    else:
        out.append("startup\tfish\tabsent")

    # Every fact here comes from a real login shell under a wiped environment, which is
    # what makes this tool's answers trustworthy where tool_resolve.py's are only
    # "what this process happens to see". Saying so in the output means a reader never
    # has to remember which script had which guarantee.
    out.append("source\tlogin-shell (env -i, rc fully loaded)\tsrc=login-shell")

    tools = args or DEFAULT_TOOLS
    for t in tools:
        zp = sc.run_login(zbin, f"command -v {t}").strip() or "-"
        fp = sc.run_login(fbin, f"command -v {t}").strip() or "-" if fbin else "?"
        out.append(tool_line(t, zp, fp))

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
