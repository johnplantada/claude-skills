#!/usr/bin/env python3
"""Is the terminal theme coordinated across all four surfaces? Read-only.

In the "inherit" model each surface should use ANSI color NAMES/slots so it follows
Ghostty's active theme. Hardcoded hex = a surface that will NOT follow the terminal
(the source of theme drift). Ghostty is the one knob. Part of the terminal-theme skill.

Greppable output, one surface per line:

    ghostty<TAB>theme <name> | palette-only     the source of truth (the knob)
    starship<TAB>inherits | hardcoded (<n> hex)
    fish<TAB>inherits | hardcoded (<n> hex)
    zsh<TAB>inherits (no highlighter) | inherits | hardcoded (<n> hex)
    coordinated<TAB>yes | no                     (exit 0 if yes)
"""

from __future__ import annotations

import re
import sys

import _theme_common as tc

# starship/zsh store colors as `#rrggbb`. Count OCCURRENCES (not lines) so a single line
# with two hardcoded colors counts as two — the same accounting used for fish below.
_HEX6 = re.compile(r"#[0-9a-fA-F]{6}")

# fish stores colors bare (no `#`), as 6- or 3-digit hex. Word boundaries keep it from
# matching ANSI color NAMES and modifiers (`brblack`, `--background=cyan`, `--theme=default`,
# `-r`), so fish's stock defaults never false-alarm. The 6-hex alternative is tried first so
# `8a8a8a` counts once, not as two 3-hex hits.
_FISH_HEX = re.compile(r"#?[0-9a-fA-F]{6}\b|\b[0-9a-fA-F]{3}\b")


def extract_ghostty_theme(show_config_output: str) -> str | None:
    """The active theme name from `ghostty +show-config`, or None if only a palette.

    Mirrors `grep -E '^theme ' | head -1 | sed -E 's/^theme = //'`: the first line that
    begins with `theme `, with the `theme = ` prefix stripped. An empty value -> None.
    """
    for line in show_config_output.splitlines():
        if line.startswith("theme "):
            value = re.sub(r"^theme = ", "", line).strip()
            return value or None
    return None


def count_starship_hex(text: str) -> int:
    """Number of `#rrggbb` occurrences in a starship.toml (each is a color that pins)."""
    return len(_HEX6.findall(text))


def count_zsh_hex(text: str) -> int:
    """Number of `#rrggbb` occurrences in a ZSH_HIGHLIGHT_STYLES dump."""
    return len(_HEX6.findall(text))


def count_fish_hex(dump: str) -> int:
    """Hardcoded hex color values in a fish color dump, counted by OCCURRENCE.

    `fish_color_autosuggestion` is exempt: the 16-ANSI palette has no readable mid-gray
    for ghost/suggestion text, so a fixed dim gray there is intentional, not drift.
    """
    total = 0
    for line in dump.splitlines():
        if "fish_color_autosuggestion" in line:
            continue
        total += len(_FISH_HEX.findall(line))
    return total


def format_ghostty_line(installed: bool, show_config_output: str) -> str:
    """The `ghostty<TAB>…` report line."""
    if not installed:
        return "ghostty\t(ghostty not installed)"
    theme = extract_ghostty_theme(show_config_output)
    if theme:
        return f"ghostty\ttheme {theme}"
    return "ghostty\tpalette-only (no theme= set)"


def format_starship_line(config_exists: bool, config_text: str) -> tuple[str, bool]:
    """The `starship<TAB>…` report line and whether it counts as drift (bad)."""
    if not config_exists:
        return "starship\t(no starship.toml)", False
    n = count_starship_hex(config_text)
    if n == 0:
        return "starship\tinherits", False
    return f"starship\thardcoded ({n} hex)", True


def format_fish_line(installed: bool, resolved_ok: bool, dump: str) -> tuple[str, bool]:
    """The `fish<TAB>…` report line and whether it counts as drift (bad)."""
    if not installed:
        return "fish\t(fish not installed)", False
    if not resolved_ok:
        return "fish\t(could not resolve colors)", True
    n = count_fish_hex(dump)
    if n == 0:
        return "fish\tinherits", False
    return f"fish\thardcoded ({n} hex)", True


def format_zsh_line(installed: bool, styles: str) -> tuple[str, bool]:
    """The `zsh<TAB>…` report line and whether it counts as drift (bad).

    zsh is only themeable when a syntax highlighter populates ZSH_HIGHLIGHT_STYLES; with
    no styles (or no zsh) it already renders the terminal palette — inherits by default.
    """
    if not installed or not styles.strip():
        return "zsh\tinherits (no highlighter)", False
    n = count_zsh_hex(styles)
    if n == 0:
        return "zsh\tinherits", False
    return f"zsh\thardcoded ({n} hex)", True


def build_report(
    *,
    ghostty_installed: bool,
    ghostty_config: str,
    starship_exists: bool,
    starship_text: str,
    fish_installed: bool,
    fish_ok: bool,
    fish_dump: str,
    zsh_installed: bool,
    zsh_styles: str,
) -> tuple[list[str], bool]:
    """Assemble every surface line and the coordinated verdict from resolved inputs."""
    lines: list[str] = []
    bad = False

    lines.append(format_ghostty_line(ghostty_installed, ghostty_config))

    line, is_bad = format_starship_line(starship_exists, starship_text)
    lines.append(line)
    bad = bad or is_bad

    line, is_bad = format_fish_line(fish_installed, fish_ok, fish_dump)
    lines.append(line)
    bad = bad or is_bad

    line, is_bad = format_zsh_line(zsh_installed, zsh_styles)
    lines.append(line)
    bad = bad or is_bad

    lines.append("coordinated\tyes" if not bad else "coordinated\tno")
    return lines, not bad


def main(argv: list[str] | None = None) -> int:
    ghostty_installed = tc.command_exists("ghostty")
    ghostty_config = tc.ghostty_show_config() if ghostty_installed else ""

    starship_path = tc.starship_config_path()
    starship_exists = starship_path.is_file()
    starship_text = tc.read_text(starship_path) if starship_exists else ""

    fish_installed = tc.command_exists("fish")
    if fish_installed:
        fish_ok, fish_dump = tc.fish_color_dump()
    else:
        fish_ok, fish_dump = False, ""

    zsh_installed = tc.command_exists("zsh")
    zsh_styles = tc.zsh_highlight_styles() if zsh_installed else ""

    lines, coordinated = build_report(
        ghostty_installed=ghostty_installed,
        ghostty_config=ghostty_config,
        starship_exists=starship_exists,
        starship_text=starship_text,
        fish_installed=fish_installed,
        fish_ok=fish_ok,
        fish_dump=fish_dump,
        zsh_installed=zsh_installed,
        zsh_styles=zsh_styles,
    )
    print("\n".join(lines))
    return 0 if coordinated else 1


if __name__ == "__main__":
    sys.exit(main())
