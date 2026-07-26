"""Shared helpers for the terminal-theme skill scripts. Stdlib only.

Single source of truth for the surface CLIs (ghostty / fish / zsh) and the starship
config path, so a path/CLI change is a one-file edit. Every subprocess call and file
read lives here; the callers keep their parsing/analysis as pure, directly-testable
functions.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_available as command_exists
from lib.devenv_common import read_text

# The fish incantation that resolves every color var in a real login+interactive shell.
# Files alone lie: universal vars, conf.d, and config.fish all contribute and only the
# shell resolves the winner. Kept identical to the audited command.
_FISH_DUMP_CMD = (
    'for v in (set -n | grep -E "fish_color|fish_pager_color"); '
    'echo $v" = "$$v; end'
)


def starship_config_path() -> Path:
    """The starship config: $STARSHIP_CONFIG, else ~/.config/starship.toml."""
    override = os.environ.get("STARSHIP_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".config" / "starship.toml"


def ghostty_show_config() -> str:
    """Stdout of `ghostty +show-config` (the active, merged config)."""
    proc = subprocess.run(
        ["ghostty", "+show-config"], capture_output=True, text=True
    )
    return proc.stdout


def ghostty_list_themes() -> str:
    """Stdout of `ghostty +list-themes` (the theme catalog)."""
    proc = subprocess.run(
        ["ghostty", "+list-themes"], capture_output=True, text=True
    )
    return proc.stdout


def fish_color_dump() -> tuple[bool, str]:
    """Resolve fish's color vars in a real login+interactive shell.

    Returns (ok, dump). `ok` is False when fish exits non-zero — a resolution
    failure must NOT be read as "inherits".
    """
    proc = subprocess.run(
        ["fish", "-l", "-i", "-c", _FISH_DUMP_CMD],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, proc.stdout


def zsh_highlight_styles() -> str:
    """Dump ZSH_HIGHLIGHT_STYLES from a live interactive shell.

    Resolving it live (not by reading ~/.zshrc) picks up styles set in sourced
    fragments. Empty string when unset (no highlighter active).
    """
    proc = subprocess.run(
        ["zsh", "-i", "-c", "typeset -p ZSH_HIGHLIGHT_STYLES 2>/dev/null"],
        capture_output=True,
        text=True,
    )
    return proc.stdout
