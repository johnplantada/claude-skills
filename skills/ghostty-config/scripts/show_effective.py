#!/usr/bin/env python3
"""Print Ghostty's EFFECTIVE config — what it actually resolved after loading every
config file — via `ghostty +show-config`. Read-only. Part of the ghostty-config skill.

Usage:
    show_effective.py [--default] [key ...]

  (no args)        the keys you've explicitly set (compact; the "declared" view)
  key ...          only those keys (prefix match, e.g. `font` matches every font-*)
  --default        include Ghostty's built-in defaults too (the full surface)

Use it to answer "is my change actually in effect?" (verification) and to see the
declared-vs-default surface for the optimize workflow.

Examples:
    show_effective.py                 # everything you've set
    show_effective.py font theme      # just font/theme lines
    show_effective.py --default cursor  # every cursor-* option incl. defaults
"""

from __future__ import annotations

import sys

import _ghostty_common as gc


def filter_lines(raw: str, keys: list[str]) -> list[str]:
    """Lines whose key name starts with any of `keys` (anchored to the key, leading
    whitespace tolerated). With no keys, returns every line unchanged."""
    lines = raw.splitlines()
    if not keys:
        return lines
    return [line for line in lines if any(line.lstrip().startswith(k) for k in keys)]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not gc.ghostty_available():
        print("show-effective: ghostty not on PATH", file=sys.stderr)
        return 3

    default = False
    if args and args[0] == "--default":
        default = True
        args = args[1:]

    # NOTE: never abort on a non-zero `+show-config` exit — gc.show_config ignores the
    # return code and hands back whatever config was emitted on stdout.
    raw = gc.show_config(default=default)

    if not args:
        print(raw)
        return 0

    matched = filter_lines(raw, args)
    if not matched:
        print("(no matching keys set)")
        return 0
    print("\n".join(matched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
