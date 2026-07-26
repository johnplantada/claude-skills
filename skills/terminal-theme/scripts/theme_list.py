#!/usr/bin/env python3
"""List the Ghostty themes you can set as the ONE knob. Read-only.

    theme_list.py [filter]

In the inherit model any Ghostty theme works — starship/fish/zsh follow it
automatically — so this is just Ghostty's theme catalog. With no filter it highlights
the families with the broadest cross-tool ports (in case you later want the matched
model, or a native fish/starship theme to match exactly). Part of the terminal-theme skill.
"""

from __future__ import annotations

import re
import sys

import _theme_common as tc

# Theme families with Ghostty + fish + starship ports all in the wild.
_FAMILIES = re.compile(
    r"catppuccin|gruvbox|tokyo ?night|nord|rose.?pine|dracula|kanagawa|everforest",
    re.IGNORECASE,
)


def filter_themes(all_themes: str, needle: str) -> list[str]:
    """Lines of the theme catalog containing `needle` (case-insensitive substring)."""
    low = needle.lower()
    return [ln for ln in all_themes.splitlines() if low in ln.lower()]


def highlight_families(all_themes: str) -> list[str]:
    """Cross-tool-friendly theme lines, de-duplicated and sorted (grep -iE … | sort -u)."""
    matches = {ln for ln in all_themes.splitlines() if _FAMILIES.search(ln)}
    return sorted(matches)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not tc.command_exists("ghostty"):
        print("theme-list: ghostty not installed", file=sys.stderr)
        return 3

    themes = tc.ghostty_list_themes()

    if args and args[0]:
        matches = filter_themes(themes, args[0])
        if matches:
            print("\n".join(matches))
        else:
            print(f"(no theme matches '{args[0]}')")
        return 0

    print("# Cross-tool-friendly families (Ghostty + fish + starship ports all exist):")
    families = highlight_families(themes)
    if families:
        print("\n".join(families))
    print()
    print("# inherit model: ANY ghostty theme works — everything follows it.")
    print("# full list:  ghostty +list-themes    |    filter:  theme_list.py <name>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
