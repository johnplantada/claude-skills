#!/usr/bin/env python3
"""Prove every font declared in a Ghostty config resolves to an installed face, and
warn when a face lacks Nerd-Font glyphs (the cause of "tofu" boxes where a
starship/powerline prompt's icons should be). Read-only. Part of the ghostty-config skill.

Usage:
    font_check.py [config-file]

  (no arg)      check the fonts in the EFFECTIVE config (`ghostty +show-config`)
  config-file   check the font-family* lines in a specific file instead

Greppable output:
    font-family<TAB>NAME<TAB>resolved | MISSING
    glyphs<TAB>NAME<TAB>nerd-font | maybe-tofu
    ok | issues        final line (exit 0 if every font resolved)

MISSING = Ghostty can't find that family and will silently fall back to a default
face. maybe-tofu = the family resolves but its name doesn't advertise Nerd-Font
glyph coverage, so prompt icons may render as empty boxes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import _ghostty_common as gc


def parse_font_families(text: str) -> list[str]:
    """Extract the values of `font-family` / `-bold` / `-italic` / `-bold-italic` lines.

    Leading whitespace is tolerated (config files may indent); comment lines are
    skipped. Surrounding double quotes are stripped from the value.
    """
    names: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("font-family") or "=" not in stripped:
            continue
        name = line.split("=", 1)[1].strip()
        if name.startswith('"'):
            name = name[1:]
        if name.endswith('"'):
            name = name[:-1]
        if name:
            names.append(name)
    return names


def parse_installed_fonts(text: str) -> list[str]:
    """Installed family names = the non-indented, non-empty lines of `+list-fonts`."""
    return [
        line for line in text.splitlines()
        if line and not line[0].isspace()
    ]


def check_fonts(declared: list[str], installed: list[str]) -> tuple[list[str], int]:
    """Build the report lines and count of MISSING fonts.

    A family resolves only on an exact match against an installed family name. A
    resolved family is flagged `nerd-font` when its name advertises Nerd-Font glyph
    coverage, else `maybe-tofu`.
    """
    installed_set = set(installed)
    lines: list[str] = []
    miss = 0
    for name in declared:
        if name in installed_set:
            lines.append(f"font-family\t{name}\tresolved")
            if "Nerd Font" in name:
                lines.append(f"glyphs\t{name}\tnerd-font")
            else:
                lines.append(f"glyphs\t{name}\tmaybe-tofu")
        else:
            lines.append(f"font-family\t{name}\tMISSING")
            miss += 1
    return lines, miss


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not gc.ghostty_available():
        print("font-check: ghostty not on PATH", file=sys.stderr)
        return 3

    if args:
        config = Path(args[0])
        if not config.is_file():
            print(f"font-check: no such file: {config}", file=sys.stderr)
            return 3
        declared_text = gc.read_text(config)
    else:
        declared_text = gc.show_config()

    declared = parse_font_families(declared_text)
    if not declared:
        print("font-family\t(none declared)\tresolved")
        print("ok")
        return 0

    installed = parse_installed_fonts(gc.list_fonts())
    lines, miss = check_fonts(declared, installed)
    lines.append("ok" if miss == 0 else "issues")
    print("\n".join(lines))
    return 0 if miss == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
