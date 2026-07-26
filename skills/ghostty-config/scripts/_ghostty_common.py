"""Shared helpers for the ghostty-config skill scripts. Stdlib only.

Single source of truth for the macOS config paths and the thin `ghostty` wrappers,
so a path/CLI change is a one-file edit. The subprocess calls live here; the callers'
logic stays as pure, directly-testable functions.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_available, read_text  # noqa: E402

# The two config locations on macOS. The Library file is always read and, when both
# exist, overrides the XDG file (which macOS only consults with XDG_CONFIG_HOME set).
LIB = Path.home() / "Library" / "Application Support" / "com.mitchellh.ghostty" / "config"
XDG = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "ghostty" / "config"


def ghostty_available() -> bool:
    return command_available("ghostty")


def has_content(path: Path) -> bool:
    """True if the file exists with at least one non-blank, non-comment line."""
    return any(
        s and not s.startswith("#")
        for s in (line.strip() for line in read_text(path).splitlines())
    )


def validate_config(config: Path | None = None) -> tuple[bool, str]:
    """Run `ghostty +validate-config`; return (ok, combined stdout+stderr)."""
    cmd = ["ghostty", "+validate-config"]
    if config is not None:
        cmd.append(f"--config-file={config}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def show_config(default: bool = False) -> str:
    """Return `ghostty +show-config` stdout (add `--default` for the full surface).

    The subprocess's exit code is deliberately ignored: `+show-config` can exit
    non-zero yet still emit usable config on stdout, and callers must keep going
    (never abort) rather than lose that output.
    """
    cmd = ["ghostty", "+show-config"]
    if default:
        cmd.append("--default")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout


def list_fonts() -> str:
    """Return `ghostty +list-fonts` stdout (family headers are the non-indented lines)."""
    proc = subprocess.run(["ghostty", "+list-fonts"], capture_output=True, text=True)
    return proc.stdout


def show_config_defaults() -> dict[str, str]:
    """Parse `ghostty +show-config --default` into {key: value} (first value wins)."""
    proc = subprocess.run(
        ["ghostty", "+show-config", "--default"], capture_output=True, text=True
    )
    defaults: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            defaults.setdefault(key.strip(), value.strip())
    return defaults
