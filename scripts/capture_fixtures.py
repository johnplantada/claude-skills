#!/usr/bin/env python3
"""Capture REAL tool output into tests/fixtures/ — the antidote to imagined test data.

Every parser bug this repo has shipped came from the same place: unit tests fed the
parsers strings a human *invented*, and reality printed something else. `brew outdated`
uses `!=` for casks but `<` for formulae; lazy.nvim wraps its progress rows in ANSI and
embeds each plugin's commit subject; `mise doctor` answers differently depending on
which shell asked. Hand-written fixtures encode the same wrong assumption as the code,
so the tests go green and the bug ships.

This script records what the tools ACTUALLY print on a real machine, so parser tests
run against ground truth. Re-run it after a tool upgrade to refresh the corpus, and
diff the result: a changed fixture IS the format-drift warning.

    capture_fixtures.py              # capture everything available on this machine
    capture_fixtures.py brew mise    # only these groups

Captures are read-only commands only. Output goes to tests/fixtures/<group>/<case>.txt
with a header noting the command and the tool version. Anything a tool can't produce
here (not installed, nothing outdated) is skipped and reported — an absent fixture is
honest; a fabricated one is the bug we're fixing.

SECRETS & PRIVACY: only commands whose output is metadata by construction are captured —
nothing here reads key material, .netrc, credentials, or `env`. Beyond secrets, a fixture
is committed to git FOREVER and this repo is public, so captures are redacted (home paths,
username, internal hostnames, emails) and length-capped. A fixture only needs to show the
tool's FORMAT; it is not an environment dump. New cases must hold that line.
"""

from __future__ import annotations

import getpass
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

# Default cap: enough lines to show every format variant, few enough that a capture can't
# become a personal-data dump. Per-case overrides live in CASES.
DEFAULT_MAX_LINES = 40

# Per-case overrides: enough to cover every format variant the parser must handle.
MAX_LINES = {
    "macos/defaults_read_dock": 20,      # only the dict/array SHAPE matters
    "ghostty/show_config": 60,           # many key kinds (theme, font-family, keybind, palette)
    "mise/doctor": 60,                   # activation + shims + problems sections
    "chezmoi/doctor": 50,                # ok/info/warning/error row variants
    "ghostty/list_fonts_head": 20,
    "chezmoi/managed_files": 15,
}


def redact(text: str) -> str:
    """Strip machine-identifying detail while preserving the tool's output SHAPE.

    Parsers care about separators, column layout, and key names — never about whose
    home directory or which internal host appears in a value. Redacting keeps the
    fixture useful as ground truth without publishing the machine it came from.
    """
    home = str(Path.home())
    user = getpass.getuser()
    text = text.replace(home, "/Users/USER")
    text = re.sub(rf"\b{re.escape(user)}\b", "USER", text)
    # emails, and internal/LAN hostnames (anything not a well-known public domain)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "USER@example.com", text)
    text = re.sub(r"\b[\w-]+\.(?:lan|local|internal|home|corp)\b", "host.example", text)
    return text

# group -> [(case name, argv)]. Read-only commands, metadata output only.
CASES: dict[str, list[tuple[str, list[str]]]] = {
    "brew": [
        ("outdated_verbose", ["brew", "outdated", "--verbose"]),
        ("outdated_verbose_formula", ["brew", "outdated", "--verbose", "--formula"]),
        ("outdated_cask", ["brew", "outdated", "--cask"]),
        ("list_pinned", ["brew", "list", "--pinned"]),
        ("autoremove_dry_run", ["brew", "autoremove", "--dry-run"]),
        ("tap", ["brew", "tap"]),
    ],
    "mise": [
        ("doctor", ["mise", "doctor"]),
        ("ls", ["mise", "ls"]),
        ("current", ["mise", "current"]),
    ],
    "chezmoi": [
        ("status", ["chezmoi", "status"]),
        ("doctor", ["chezmoi", "doctor"]),
        ("managed_files", ["chezmoi", "managed", "--include=files"]),
    ],
    "git": [
        ("config_global_list", ["git", "config", "--global", "--list"]),
        ("version", ["git", "--version"]),
    ],
    "ghostty": [
        ("show_config", ["ghostty", "+show-config"]),
        ("list_fonts_head", ["ghostty", "+list-fonts"]),
    ],
    "nvim": [
        ("version", ["nvim", "--version"]),
    ],
    "macos": [
        ("defaults_read_dock", ["defaults", "read", "com.apple.dock"]),
        ("defaults_domains", ["defaults", "domains"]),
    ],
}


def capture(group: str, case: str, argv: list[str], max_lines: int = DEFAULT_MAX_LINES) -> str:
    """Run argv, redact + cap its output, and write it; return a one-line status."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"skip  {group}/{case}: {type(exc).__name__}"
    body = proc.stdout + proc.stderr
    if not body.strip():
        return f"skip  {group}/{case}: no output (nothing to capture on this machine)"

    lines = redact(body).splitlines()
    truncated = len(lines) > max_lines
    kept = lines[:max_lines]

    out_dir = FIXTURES / group
    out_dir.mkdir(parents=True, exist_ok=True)
    header = [
        f"# captured from: {' '.join(argv)}",
        f"# exit: {proc.returncode}",
        "# redacted (home path, username, emails, internal hostnames) — format sample, not an env dump",
    ]
    if truncated:
        header.append(f"# truncated to {max_lines} of {len(lines)} lines")
    (out_dir / f"{case}.txt").write_text("\n".join(header + kept) + "\n")
    count = f"{len(kept)}/{len(lines)}" if truncated else str(len(kept))
    return f"ok    {group}/{case} ({count} lines, exit {proc.returncode})"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    groups = args or sorted(CASES)
    unknown = [g for g in groups if g not in CASES]
    if unknown:
        print(f"unknown group(s): {unknown}; known: {sorted(CASES)}", file=sys.stderr)
        return 2
    for group in groups:
        for case, cmd in CASES[group]:
            print(capture(group, case, cmd, MAX_LINES.get(f"{group}/{case}", DEFAULT_MAX_LINES)))
    print(f"\nfixtures at {FIXTURES}")
    print("review the diff before committing — a CHANGED fixture is a format-drift warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
