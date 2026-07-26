#!/usr/bin/env python3
"""Print the terminal's ANSI palette (slots 0-15) as swatches. Read-only.

Lets you eyeball the colors that starship / fish / zsh all inherit. Touches no config.
Render it INSIDE Ghostty to see the active theme's real colors (in a plain pipe you'll
just see the escape codes). Part of the terminal-theme skill.
"""

from __future__ import annotations

import sys

ESC = "\033"


def render_swatch() -> str:
    """The full swatch output, escape codes and all, exactly as printed."""
    bg_normal = "".join(f"{ESC}[4{i}m   {ESC}[0m" for i in range(8))
    bg_bright = "".join(f"{ESC}[10{i}m   {ESC}[0m" for i in range(8))
    fg_normal = "".join(f"{ESC}[3{i}mAa{ESC}[0m " for i in range(8))
    fg_bright = "".join(f"{ESC}[9{i}mAa{ESC}[0m " for i in range(8))
    return (
        "\nTerminal ANSI palette — what every surface inherits (render in Ghostty):\n\n"
        "  bg blocks  normal 0-7 : " + bg_normal +
        "\n  bg blocks  bright 8-15: " + bg_bright +
        "\n\n  fg text    normal     : " + fg_normal +
        "\n  fg text    bright     : " + fg_bright +
        "\n\n"
        "  0 black  1 red  2 green  3 yellow  4 blue  5 magenta  6 cyan  7 white   (8-15 = bright)\n\n"
    )


def main(argv: list[str] | None = None) -> int:
    sys.stdout.write(render_swatch())
    return 0


if __name__ == "__main__":
    sys.exit(main())
