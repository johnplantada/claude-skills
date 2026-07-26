#!/usr/bin/env python3
"""Run Lua in headless Neovim, correctly. The primitive under all verification.

Use this instead of hand-writing `nvim --headless -c 'lua ...'`, which has two
recurring footguns this wrapper removes:
  1. `-c 'lua <<EOF ... EOF'` heredocs do NOT execute — silently no-op.
  2. Quoting multi-line Lua inside +lua "..." mangles it.
The snippet goes to a temp `.lua` file and runs via `+luafile` (always correct).

Usage:
    nvim_lua.py 'print(1+1)'              # inline snippet (loads user config)
    nvim_lua.py -f check.lua             # from a file
    printf 'print(1)\\n' | nvim_lua.py -  # from stdin
Options:
    --clean     load WITHOUT user config (nvim --clean) — for core API checks
    --wait N    vim.wait(N) before running the snippet (default 0); use for async LSP

Output is the snippet's stdout/stderr, verbatim. `print()` and `io.write()` both work.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import NamedTuple


class LuaArgs(NamedTuple):
    """Parsed nvim_lua invocation."""

    clean: bool
    wait: str
    mode: str  # "inline" | "file" | "stdin"
    src: str | None
    help: bool


def parse_lua_args(argv: list[str]) -> LuaArgs:
    """Parse the CLI into a `LuaArgs`. Later positionals win (last inline snippet).

    Raises ValueError with the exact bash message when `--wait`/`-f` lack an argument.
    """
    clean = False
    wait = "0"
    mode = "inline"
    src: str | None = None
    want_help = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--clean":
            clean = True
            i += 1
        elif arg == "--wait":
            if i + 1 >= len(argv):
                raise ValueError("--wait needs a number")
            wait = argv[i + 1]
            i += 2
        elif arg == "-f":
            if i + 1 >= len(argv):
                raise ValueError("-f needs a path")
            mode = "file"
            src = argv[i + 1]
            i += 2
        elif arg == "-":
            mode = "stdin"
            i += 1
        elif arg in ("-h", "--help"):
            want_help = True
            i += 1
        else:
            mode = "inline"
            src = arg
            i += 1
    return LuaArgs(clean, wait, mode, src, want_help)


def build_nvim_cmd(clean: bool, wait: str | int, tmp: str) -> list[str]:
    """The headless argv: pre-wait, then run the temp `.lua` via `+luafile`."""
    cmd = ["nvim", "--headless"]
    if clean:
        cmd.append("--clean")
    cmd += [f"+lua vim.wait({wait})", f"+luafile {tmp}", "+qa"]
    return cmd


def run(snippet: str, *, clean: bool = False, wait: str | int = 0) -> str:
    """Run `snippet` in headless Neovim; return combined stdout+stderr, verbatim.

    Trailing newlines are normalized to none here (the caller's `print` adds exactly
    one) so output stays line-oriented and greppable across back-to-back checks.
    """
    fd, tmp = tempfile.mkstemp(suffix=".lua")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(snippet)
        proc = subprocess.run(build_nvim_cmd(clean, wait, tmp), capture_output=True, text=True)
        return (proc.stdout + proc.stderr).rstrip("\n")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        parsed = parse_lua_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if parsed.help:
        print(__doc__.strip())
        return 0

    if parsed.mode == "file":
        with open(parsed.src, encoding="utf-8") as fh:
            snippet = fh.read()
    elif parsed.mode == "stdin":
        snippet = sys.stdin.read()
    else:  # inline: printf '%s\n' "$SRC"
        snippet = (parsed.src or "") + "\n"

    print(run(snippet, clean=parsed.clean, wait=parsed.wait))
    return 0


if __name__ == "__main__":
    sys.exit(main())
