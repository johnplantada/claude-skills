#!/usr/bin/env python3
"""One call that answers "what version is this lazy plugin, what pins it, and is there
a fix upstream?" — collapsing the ~5 ad-hoc git+grep calls a repair or upgrade
otherwise needs. With a `symbol`, also locate a function/API across the installed tree,
the newest tag, and (for `vim.*`) Neovim core.

Usage:
    plugin_info.py telescope.nvim                     # version + pins + tags
    plugin_info.py telescope.nvim ft_to_lang          # + where the symbol lives
    plugin_info.py telescope.nvim ft_to_lang --fetch  # refresh tags/commits first

--fetch does network (git fetch --tags); omit to stay offline/fast (shows only what
lazy has already fetched locally).
"""

from __future__ import annotations

import os
import re
import sys

import _nvim_common as gc


def parse_plugin_args(argv: list[str]) -> tuple[str, str | None, bool]:
    """Return (plugin, symbol, fetch). First bare arg is the plugin, second the symbol.

    Raises ValueError when no plugin name is given.
    """
    plugin: str | None = None
    symbol: str | None = None
    fetch = False
    for arg in argv:
        if arg == "--fetch":
            fetch = True
        elif plugin is None:
            plugin = arg
        elif symbol is None:
            symbol = arg
    if plugin is None:
        raise ValueError("plugin required")
    return plugin, symbol, fetch


def find_lockfile_pin(lock_text: str, plugin: str) -> str:
    """The `lazy-lock.json` line(s) pinning `plugin`, or '' when absent."""
    pattern = re.compile('"' + re.escape(plugin) + '"')
    hits = [line for line in lock_text.splitlines() if pattern.search(line)]
    return "\n".join(hits)


def spec_pin_lines(files: list[tuple[str, str]], plugin: str) -> list[str]:
    """`file:lineno:line` context around the plugin's spec that names a pin.

    Mirrors `grep -rn -A6 "$PLUGIN" ... | grep -iE '<plugin>"|(tag|version|commit|
    branch|pin) *=' | head -8`: gather each match plus the 6 following lines, then keep
    only those that actually declare a pin, capped at eight.
    """
    name = re.compile(re.escape(plugin))
    keep = re.compile(
        re.escape(plugin) + r'"|[^a-z](tag|version|commit|branch|pin) *=', re.IGNORECASE
    )
    context: list[str] = []
    for path, text in files:
        lines = text.splitlines()
        wanted: set[int] = set()
        for i, line in enumerate(lines):
            if name.search(line):
                wanted.update(range(i, min(i + 7, len(lines))))
        for j in sorted(wanted):
            sep = ":" if name.search(lines[j]) else "-"
            context.append(f"{path}:{j + 1}{sep}{lines[j]}")
    return [line for line in context if keep.search(line)][:8]


def format_tags(tags: list[str]) -> str:
    """The newest five tags space-joined (trailing space, as `... | tr '\\n' ' '`)."""
    return "".join(tag + " " for tag in tags[:5])


def compute_drift(describe: str, newest: str | None) -> str | None:
    """The drift note when the installed describe differs from the newest tag, else None."""
    if newest and newest != describe:
        return f"installed={describe}  newest_tag={newest}"
    return None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        plugin, symbol, fetch = parse_plugin_args(args)
    except ValueError:
        print("usage: plugin_info.py <plugin-dir-name> [symbol] [--fetch]", file=sys.stderr)
        return 2

    config = gc.stdpath("config")
    data = gc.stdpath("data")
    directory = os.path.join(data, "lazy", plugin)
    if not os.path.isdir(directory):
        print(f"not installed: {directory}", file=sys.stderr)
        return 1

    if fetch:
        gc.git_fetch_tags(directory)

    out: list[str] = [f"== {plugin} =="]
    out.append(f"installed_commit:   {gc.git_log1(directory)}")
    describe = gc.git_describe(directory)
    out.append(f"installed_describe: {describe}")

    lock = os.path.join(config, "lazy-lock.json")
    if os.path.isfile(lock):
        pin = find_lockfile_pin(gc.read_text(lock), plugin)
        out.append(f"lockfile_pin:       {pin or '(absent from lazy-lock.json)'}")

    out.append("spec_pin:")
    spec = spec_pin_lines(gc.read_spec_files(config), plugin)
    if spec:
        out += [f"  {line}" for line in spec]
    else:
        out.append("  (no explicit pin found — floats on branch HEAD)")

    tags = gc.git_tags(directory)
    tags_str = format_tags(tags)
    out.append(f"newest_tags:        {tags_str or '(none)'}")
    newest = tags[0] if tags else None
    drift = compute_drift(describe, newest)
    if drift:
        out.append(f"drift:              {drift}")

    if symbol:
        out.append(f"== symbol: {symbol} ==")
        out.append(f"in_installed_tree:  {gc.count_lua_files_containing(directory, symbol)} file(s)")
        if newest:
            out.append(f"in_newest_tag:      {gc.git_grep_count(directory, symbol, newest)} file(s) @ {newest}")
        if symbol.startswith("vim."):
            out.append(
                f"in_nvim_core:       type({symbol}) = {gc.clean_type(symbol)}"
                "   (nil = removed/absent → callers break)"
            )

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
