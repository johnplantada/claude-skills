#!/usr/bin/env python3
"""Discover the real Neovim environment. Run FIRST, every session.

No arguments. Prints one `key<TAB>value` line per fact (greppable, stable order):

    nvim_version<TAB><first line of `nvim --version`>
    config_dir<TAB><stdpath('config')>
    data_dir<TAB><stdpath('data')>
    state_dir<TAB><stdpath('state')>
    plugin_manager<TAB>lazy | packer | vim-plug | mini.deps | unknown
    structure<TAB>modular (lua/ tree) | single init.lua
    config_git<TAB>repo @ <short-sha> | not a git repo
    lsp_log<TAB><state>/lsp.log
    conform_log<TAB><state>/conform.log

Replaces the hand-composed discovery block in SKILL.md §2.
"""

from __future__ import annotations

import os
import sys
from typing import Callable

import _nvim_common as gc


def detect_manager(config: str, data: str, exists: Callable[[str], bool]) -> str:
    """Identify the plugin manager from marker files/dirs. lazy wins ties.

    This toolkit fully drives lazy; the others are detect-and-advise. Order matches the
    original bash cascade so the verdict is unchanged.
    """
    join = os.path.join
    if exists(join(config, "lazy-lock.json")) or exists(join(data, "lazy")):
        return "lazy"
    if exists(join(data, "site", "pack", "packer")):
        return "packer"
    if exists(join(config, "autoload", "plug.vim")) or exists(join(data, "plugged")):
        return "vim-plug"
    if exists(join(data, "site", "pack", "deps")):
        return "mini.deps"
    return "unknown"


def detect_structure(config: str, isdir: Callable[[str], bool]) -> str:
    """`modular (lua/ tree)` if there's a `lua/` dir, else `single init.lua`."""
    return "modular (lua/ tree)" if isdir(os.path.join(config, "lua")) else "single init.lua"


def format_git_status(is_repo: bool, short_head: str | None) -> str:
    """The `config_git` value: repo + short sha, or a `no commits yet` / not-a-repo note."""
    if not is_repo:
        return "not a git repo"
    return f"repo @ {short_head or 'no commits yet'}"


def build_env_lines(
    version: str,
    config: str,
    data: str,
    state: str,
    manager: str,
    structure: str,
    git: str,
) -> list[str]:
    """Assemble the nine `key<TAB>value` lines in their stable order."""
    return [
        f"nvim_version\t{version}",
        f"config_dir\t{config}",
        f"data_dir\t{data}",
        f"state_dir\t{state}",
        f"plugin_manager\t{manager}",
        f"structure\t{structure}",
        f"config_git\t{git}",
        f"lsp_log\t{state}/lsp.log",
        f"conform_log\t{state}/conform.log",
    ]


def main(argv: list[str] | None = None) -> int:
    version = gc.nvim_version_line()
    config = gc.stdpath("config")
    data = gc.stdpath("data")
    state = gc.stdpath("state")

    manager = detect_manager(config, data, os.path.exists)
    structure = detect_structure(config, os.path.isdir)
    git = format_git_status(gc.git_is_repo(config), gc.git_short_head(config))

    print("\n".join(build_env_lines(version, config, data, state, manager, structure, git)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
