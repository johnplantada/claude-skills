#!/usr/bin/env python3
"""Audit a Ghostty config for cruft — duplicate single-value keys and lines that
merely restate a default. Read-only. Part of the ghostty-config skill.

Usage:
    config_audit.py [config-file]

With no argument it audits the AUTHORITATIVE config (the file Ghostty actually loads
on macOS). Greppable output, one item per line:

    validate<TAB>ok | FAIL
    error<TAB><msg>              one per validation error (only on FAIL)
    dup<TAB><key><TAB><n> times  a single-value key set more than once
    redundant<TAB><key> = <val>  equals Ghostty's built-in default (safe to drop)
    keys<TAB><n>                 count of distinct keys set
    clean | cruft                final verdict (exit 0 if clean)
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import _ghostty_common as gc

# Ghostty keys that may legitimately appear many times — never "duplicates".
REPEATABLE = {
    "config-file", "keybind", "palette", "font-feature", "link", "env",
    "font-family", "font-family-bold", "font-family-italic", "font-family-bold-italic",
}

# Keys a `theme` sets. When a theme is active, "equals the built-in default" does NOT
# mean redundant — the line may be overriding the theme — so these are never flagged.
THEME_KEYS = {
    "background", "foreground", "cursor-color", "cursor-text",
    "selection-background", "selection-foreground", "palette",
}


def parse_pairs(text: str) -> list[tuple[str, str]]:
    """Extract `key = value` pairs, skipping blanks and comment lines."""
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        pairs.append((key.strip(), value.strip()))
    return pairs


def find_dups(pairs: list[tuple[str, str]]) -> dict[str, int]:
    """Single-value keys set more than once. Repeatable keys are excluded, so a normal
    config full of `keybind`/`palette`/`font-family` lines is not flagged."""
    counts = Counter(key for key, _ in pairs if key not in REPEATABLE)
    return {key: n for key, n in counts.items() if n > 1}


def find_redundant(
    pairs: list[tuple[str, str]], defaults: dict[str, str], has_theme: bool
) -> list[tuple[str, str]]:
    """Lines whose value equals Ghostty's built-in default (safe to remove).

    When a theme is active, color keys are skipped: their effective baseline is the
    theme, not the built-in default, so such a line may be *overriding* the theme and
    removing it would change the terminal's appearance.
    """
    out: list[tuple[str, str]] = []
    for key, value in pairs:
        if key in ("config-file", "theme"):
            continue
        if has_theme and key in THEME_KEYS:
            continue
        if defaults.get(key) == value:
            out.append((key, value))
    return out


def resolve_config(explicit: str | None) -> Path:
    """Pick the config to audit: an explicit path, else the AUTHORITATIVE file.

    On macOS the Library file is what Ghostty loads. It is authoritative when it holds
    real settings; when it is only a one-line `config-file` include, the real config is
    the XDG file. Prefer whichever actually carries settings.
    """
    if explicit:
        return Path(explicit)
    lib_pairs = parse_pairs(gc.read_text(gc.LIB))
    if any(key != "config-file" for key, _ in lib_pairs):
        return gc.LIB  # real settings live in the Library file (all-in-Library layout)
    if gc.has_content(gc.XDG):
        return gc.XDG  # include layout: the real config is in ~/.config
    if gc.has_content(gc.LIB):
        return gc.LIB
    raise FileNotFoundError(
        f"no config with settings found (looked in {gc.XDG} and the Library file)"
    )


def audit(config: Path, defaults: dict[str, str]) -> tuple[list[str], bool]:
    """Build the greppable report lines and the clean/cruft verdict."""
    lines: list[str] = []
    cruft = False

    ok, output = gc.validate_config(config)
    if ok:
        lines.append("validate\tok")
    else:
        lines.append("validate\tFAIL")
        cruft = True
        lines += [f"error\t{ln}" for ln in output.splitlines() if ln.strip()]

    pairs = parse_pairs(gc.read_text(config))
    has_theme = any(key == "theme" for key, _ in pairs)

    for key, count in sorted(find_dups(pairs).items()):
        lines.append(f"dup\t{key}\t{count} times")
        cruft = True
    for key, value in find_redundant(pairs, defaults, has_theme):
        lines.append(f"redundant\t{key} = {value}")
        cruft = True

    lines.append(f"keys\t{len({key for key, _ in pairs})}")
    lines.append("clean" if not cruft else "cruft")
    return lines, not cruft


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not gc.ghostty_available():
        print("config-audit: ghostty not on PATH", file=sys.stderr)
        return 3
    try:
        config = resolve_config(args[0] if args else None)
    except FileNotFoundError as exc:
        print(f"config-audit: {exc}", file=sys.stderr)
        return 3
    if not config.is_file():
        print(f"config-audit: no such file: {config}", file=sys.stderr)
        return 3

    lines, clean = audit(config, gc.show_config_defaults())
    print("\n".join(lines))
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
