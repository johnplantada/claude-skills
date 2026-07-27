#!/usr/bin/env python3
"""Stable runtime verification harness — named shortcuts for the checks a repair,
upgrade, or optimize runs every time. For one-off checks, use nvim_lua.py directly.
All checks are read-only and safe to re-run; scratch files go to a temp dir, never
the user's project.

Checks:
    startup                 load config; print error/deprecation lines (none = clean)
    open <ext>              open scratch .<ext>; report errors + ts-highlight active
    ts <ext>                is treesitter highlighting active for that filetype?
    lsp <ext> [server]      open scratch .<ext>, wait, list attached LSP clients
    deprecations            checkhealth vim.deprecated + static grep of config
    api <vim.path>          type of a core API (nil = removed) — e.g. vim.treesitter.language.get_lang
"""

from __future__ import annotations

import re
import sys

import _nvim_common as gc
import nvim_lua

USAGE = """nvim_check.py <check> [args] — stable runtime verification harness.
Named shortcuts for the checks a repair/upgrade/optimize runs every time.
For one-off checks, use nvim_lua.py directly. All checks are read-only and
safe to re-run; scratch files go to a temp dir, never the user's project.

  startup                 load config; print error/deprecation lines (none = clean)
  open <ext>              open scratch .<ext>; report errors + ts-highlight active
  ts <ext>                is treesitter highlighting active for that filetype?
  lsp <ext> [server]      open scratch .<ext>, wait, list attached LSP clients
  deprecations            checkhealth vim.deprecated + static grep of config
  api <vim.path>          type of a core API (nil = removed) — e.g. vim.treesitter.language.get_lang"""

# Startup noise filter: keep real error/deprecation lines, drop lazy.nvim's progress
# chatter. The subtle case is a plugin's own GIT COMMIT SUBJECT — lazy prints
# `[cmp-nvim-lsp] checkout | HEAD is now at cbc7b02 Call client methods without
# generating deprecation warnings…`, and a subject that merely *mentions* a
# deprecation is indistinguishable from a real one by keyword alone. Excluding the
# progress format itself is what separates "a plugin fixed a deprecation" (noise)
# from "your config hit one" (the finding) — otherwise every sync reports phantom
# problems and the check stops meaning anything.
_STARTUP_INCLUDE = re.compile(r"error|fail|deprecat|attempt to|E5108", re.IGNORECASE)
_STARTUP_EXCLUDE = re.compile(
    r"receiving|resolving|counting|compressing"
    r"|HEAD is now at"          # git checkout line: the rest is a commit subject
    r"|\|\s*(checkout|clone|updated|installed|pulling|fetching)\b",  # lazy progress rows
    re.IGNORECASE,
)

_WARN_ERR = re.compile(r"warning|error", re.IGNORECASE)

# A filetype extension becomes part of a scratch filename that is then interpolated
# into a Lua `vim.cmd('edit …')` string — keep it to plain extension characters.
_EXT_RE = re.compile(r"[A-Za-z0-9_.-]+")

# Deprecated API call-sites a static scan of the config should surface.
_DEPRECATION = re.compile(
    r'vim\.loop|vim\.highlight\.on_yank|tbl_islist|sign_define|goto_prev|goto_next'
    r'|require\("lspconfig"\)|neodev'
)


def filter_startup(output: str) -> list[str]:
    """Lines from a `Lazy! sync` run that name a real error/deprecation (progress
    chatter like `receiving objects` removed). Empty list == a clean startup."""
    return [
        line
        for line in output.splitlines()
        if _STARTUP_INCLUDE.search(line) and not _STARTUP_EXCLUDE.search(line)
    ]


def filter_warn_err(output: str) -> list[str]:
    """checkhealth lines that mention WARNING or ERROR (case-insensitive)."""
    return [line for line in output.splitlines() if _WARN_ERR.search(line)]


def static_deprecation_grep(files: list[tuple[str, str]]) -> list[str]:
    """`file:lineno:line` for every config line hitting a deprecated call-site pattern."""
    out: list[str] = []
    for path, text in files:
        for i, line in enumerate(text.splitlines(), 1):
            if _DEPRECATION.search(line):
                out.append(f"{path}:{i}:{line}")
    return out


def build_open_lua(path: str) -> str:
    """Snippet: open the scratch buffer, echo any error/deprecation messages, and
    report whether treesitter highlighting attached."""
    return (
        f"vim.cmd('edit {path}')\n"
        "vim.wait(400)\n"
        "local b = vim.api.nvim_get_current_buf()\n"
        "for _,l in ipairs(vim.fn.split(vim.fn.execute('messages'), '\\n')) do\n"
        "  if l:match('[Ee]rror') or l:match('deprecat') or l:match('attempt to') then print('MSG: '..l) end\n"
        "end\n"
        "print('ts_highlight_active=' .. tostring(vim.treesitter.highlighter.active[b] ~= nil))\n"
    )


def build_ts_lua(path: str) -> str:
    """Snippet: open the scratch buffer and report treesitter-highlight state only."""
    return (
        f"vim.cmd('edit {path}'); vim.wait(400)\n"
        "local b = vim.api.nvim_get_current_buf()\n"
        "print('ts_highlight_active=' .. tostring(vim.treesitter.highlighter.active[b] ~= nil))\n"
    )


def build_lsp_lua(path: str) -> str:
    """Snippet: open the scratch buffer, wait, and list attached LSP clients."""
    return (
        f"vim.cmd('edit {path}'); vim.wait(3000)\n"
        "local names = {}\n"
        "for _,c in ipairs(vim.lsp.get_clients()) do\n"
        "  names[#names+1] = c.name .. (c.server_capabilities.completionProvider and ' (completion)' or '')\n"
        "end\n"
        "print('lsp_clients: ' .. (#names > 0 and table.concat(names, ', ') or '(none attached)'))\n"
    )


def build_api_lua(expr: str) -> str:
    """Snippet: print `<expr> = <type>` (or `nil/error`) for a core-API existence check."""
    return (
        f"local ok,t=pcall(function() return type({expr}) end); "
        f"print('{expr} = ' .. (ok and t or 'nil/error'))"
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    check = args[0] if args else ""
    rest = args[1:]

    # Every check below drives nvim (directly or via nvim_lua.run), so a machine without
    # it gets the documented rc 3 rather than an unhandled FileNotFoundError. The usage
    # text still prints without nvim, so `nvim_check.py` with no args stays helpful.
    if check and nvim_lua.nvim_missing():
        print("nvim_check: nvim not on PATH", file=sys.stderr)
        return 3

    if check == "startup":
        lines = filter_startup(gc.run_lazy_sync())
        print("\n".join(lines) if lines else "clean: no error/deprecation lines")
        return 0

    if check in ("open", "ts", "lsp") and rest and not _EXT_RE.fullmatch(rest[0]):
        print(f"invalid extension: {rest[0]!r} (letters/digits/._- only)", file=sys.stderr)
        return 1

    if check == "open":
        if not rest:
            print("open needs a filetype extension, e.g. lua", file=sys.stderr)
            return 1
        path = gc.make_scratch(rest[0], "local x = 1\nprint(x)\n")
        try:
            print(nvim_lua.run(build_open_lua(path), wait=600))
        finally:
            gc.remove(path)
        return 0

    if check == "ts":
        if not rest:
            print("ts needs a filetype extension", file=sys.stderr)
            return 1
        path = gc.make_scratch(rest[0], "local x=1\n")
        try:
            print(nvim_lua.run(build_ts_lua(path)))
        finally:
            gc.remove(path)
        return 0

    if check == "lsp":
        if not rest:
            print("lsp needs a filetype extension", file=sys.stderr)
            return 1
        path = gc.make_scratch(rest[0], "local x=1\n")
        try:
            print(nvim_lua.run(build_lsp_lua(path), wait=3000))
        finally:
            gc.remove(path)
        return 0

    if check == "deprecations":
        config = gc.stdpath("config")
        print("-- checkhealth vim.deprecated --")
        warn = filter_warn_err(gc.run_checkhealth_deprecated())
        print("\n".join(warn) if warn else "  (none)")
        print("-- static grep of config --")
        grep = static_deprecation_grep(gc.walk_files(config))
        print("\n".join(grep) if grep else "  (none)")
        return 0

    if check == "api":
        if not rest:
            print("api needs an expression, e.g. vim.treesitter.language.get_lang", file=sys.stderr)
            return 1
        print(nvim_lua.run(build_api_lua(rest[0]), clean=True))
        return 0

    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
