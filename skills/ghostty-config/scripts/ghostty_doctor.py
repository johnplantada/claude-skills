#!/usr/bin/env python3
"""Health check for a Ghostty config. Read-only — changes nothing. Part of the
ghostty-config skill.

Usage:
    ghostty_doctor.py [config-file]

  - runs `ghostty +validate-config` (parse + semantic errors, with messages)
  - reports which file Ghostty actually loads. On macOS the Application Support
    config is ALWAYS read and, when both exist, OVERRIDES ~/.config/ghostty/config
    (which macOS does NOT read by default). So an un-included XDG file is silently
    ignored — a classic "I edited ~/.config but nothing changed" trap.
  - flags that split-brain: XDG config present with real content but NOT pulled in
    from the Library file via a `config-file =` include.

Greppable output (stable order):
    validate       ok | FAIL
    error<TAB>msg              one per validation error (only on FAIL)
    loads<TAB>/path            macOS Application Support config (always read)
    include<TAB>/path          XDG config pulled in via config-file (good)
    split_brain<TAB>/path      XDG config present but ignored (edit has no effect)
    in_sync        yes | no    final verdict (exit 0 if validate ok AND no split_brain)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import _ghostty_common as gc


def find_include_lines(lib_text: str) -> list[str]:
    """The `config-file = …` lines from the Library config (leading space allowed)."""
    out: list[str] = []
    for line in lib_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("config-file") and "=" in stripped:
            # ensure the key really is `config-file`, not e.g. `config-file-foo`
            key = stripped.split("=", 1)[0].strip()
            if key == "config-file":
                out.append(line)
    return out


def includes_xdg(lib_text: str, xdg_path: Path | str) -> bool:
    """True if a `config-file` include in the Library config references the XDG config.

    The path is matched as a FIXED STRING (substring), never a regex: a path is full
    of regex metacharacters (`.` in `.config`, etc.), so a regex match would spuriously
    hit a *different* file like `…/xconfig/ghostty/config` and wrongly report the XDG
    file as included, hiding a real split-brain.
    """
    targets = [
        str(xdg_path),
        "~/.config/ghostty/config",
        "$HOME/.config/ghostty/config",
    ]
    for line in find_include_lines(lib_text):
        if any(target in line for target in targets):
            return True
    return False


def build_report(
    validate_ok: bool,
    validate_output: str,
    lib_text: str,
    lib_has_content: bool,
    xdg_has_content: bool,
    lib_path: Path,
    xdg_path: Path,
    xdg_home_set: bool,
) -> tuple[list[str], bool]:
    """Assemble the greppable report lines and the in-sync verdict."""
    lines: list[str] = []
    drift = False

    if validate_ok:
        lines.append("validate\tok")
    else:
        lines.append("validate\tFAIL")
        lines += [f"error\t{ln}" for ln in validate_output.splitlines() if ln.strip()]

    if lib_has_content:
        lines.append(f"loads\t{lib_path}")
        if includes_xdg(lib_text, xdg_path):
            if xdg_has_content:
                lines.append(f"include\t{xdg_path}")
        elif xdg_has_content:
            lines.append(f"split_brain\t{xdg_path}")
            drift = True
    elif xdg_has_content:
        # No Library file: XDG only applies if XDG_CONFIG_HOME is exported (macOS quirk).
        lines.append(f"loads\t{xdg_path}")
        if not xdg_home_set:
            lines.append(f"split_brain\t{xdg_path}")
            drift = True

    in_sync = validate_ok and not drift
    lines.append("in_sync\tyes" if in_sync else "in_sync\tno")
    return lines, in_sync


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not gc.ghostty_available():
        print("ghostty-doctor: ghostty not on PATH", file=sys.stderr)
        return 3

    target = Path(args[0]) if args else None
    ok, output = gc.validate_config(target)
    lines, in_sync = build_report(
        ok,
        output,
        gc.read_text(gc.LIB),
        gc.has_content(gc.LIB),
        gc.has_content(gc.XDG),
        gc.LIB,
        gc.XDG,
        bool(os.environ.get("XDG_CONFIG_HOME")),
    )
    print("\n".join(lines))
    return 0 if in_sync else 1


if __name__ == "__main__":
    sys.exit(main())
