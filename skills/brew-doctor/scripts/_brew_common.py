"""Shared helpers for the brew-doctor skill scripts. Stdlib only.

Single source of truth for the `brew` CLI wrappers, the launchd/cron/plist reads,
and the `~/.config/devenv/config.toml` `[brew-doctor]` reader. The subprocess and
filesystem calls live here so the callers' parsing/classification/formatting stays
as pure, directly-testable functions.

The config reader is a section-aware TOML-ish scraper (no TOML library, matching the
old awk one line-for-line): `config_str` strips quotes; `config_array` keeps only
`[A-Za-z0-9@._ \t-]` and squeezes whitespace — both operate on already-read text via
the pure `parse_config_str` / `parse_config_array` functions.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_available, read_text
from lib.devenv_common import run_rc as run

CONFIG_TOML = Path(
    os.environ.get("DEVENV_CONFIG") or (Path.home() / ".config" / "devenv" / "config.toml")
)


# --- brew availability + generic runner --------------------------------------

def brew_available() -> bool:
    return command_available("brew")


def brew(*args: str, merge: bool = False) -> str:
    """Run `brew <args>` and return its output (stderr per `merge`)."""
    return run(["brew", *args], merge=merge)[1]


def brew_ok(*args: str) -> bool:
    """Run `brew <args>` discarding output; True on a zero exit."""
    return run(["brew", *args])[0] == 0


# --- filesystem reads (launchd / cron / plist / files) -----------------------

# read_text (lenient decode for launchd `Program` binaries) comes from lib.devenv_common.


def launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def crontab_brew_lines() -> str:
    """`crontab -l | grep -i brew` — the brew-mentioning crontab lines (may be '')."""
    out = run(["crontab", "-l"])[1]
    return "\n".join(ln for ln in out.splitlines() if "brew" in ln.lower())


def plist_program(path: Path) -> str:
    """First executable target of a launchd plist: :Program, else :ProgramArguments:0.

    Uses PlistBuddy when present (handles binary plists), else a text grep fallback.
    """
    buddy = Path("/usr/libexec/PlistBuddy")
    if buddy.is_file() and os.access(buddy, os.X_OK):
        for key in (":Program", ":ProgramArguments:0"):
            rc, out = run([str(buddy), "-c", f"Print {key}", str(path)])
            if rc == 0 and out.strip():
                return out.strip()
        return ""
    return parse_plist_program(read_text(path))


# --- pure config parsing (no I/O) --------------------------------------------

def parse_config_str(text: str, section: str, key: str) -> str:
    """Value of `key` under `[section]`, quotes stripped; '' if absent.

    Mirrors the old `cfg_str` awk: strip everything up to the first `=` (and the
    spaces after it), drop a trailing ` # comment`, then remove all double quotes.
    """
    return _config_value(text, section, key, strip_quotes=True)


def parse_config_array(text: str, section: str, key: str) -> str:
    """Value of a TOML array `key` under `[section]` as space-separated tokens.

    Mirrors the old `cfg_array` awk: keep only `[A-Za-z0-9@._ \t-]` (dropping the
    brackets, quotes and commas) then squeeze runs of whitespace to a single space.
    """
    value = _config_value(text, section, key, strip_quotes=False)
    value = re.sub(r"[^A-Za-z0-9@._ \t-]", "", value)
    return re.sub(r"[ \t]+", " ", value)


def _config_value(text: str, section: str, key: str, *, strip_quotes: bool) -> str:
    sec_re = re.compile(r"^\s*\[" + re.escape(section) + r"\]")
    key_re = re.compile(r"^\s*" + re.escape(key) + r"\s*=")
    in_section = False
    for line in text.splitlines():
        if re.match(r"^\s*\[", line):
            in_section = bool(sec_re.search(line))
            continue
        if in_section and key_re.search(line):
            value = re.sub(r"^[^=]*=\s*", "", line)
            value = re.sub(r"\s*#.*$", "", value)
            if strip_quotes:
                value = value.replace('"', "")
            return value
    return ""


def parse_plist_program(text: str) -> str:
    """Text-grep fallback for `plist_program`: the first <string> after a
    Program / ProgramArguments key. '' if none found."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"<key>Program(Arguments)?</key>", line, re.IGNORECASE):
            for follow in lines[i + 1 :]:
                m = re.search(r"<string>(.*)</string>", follow)
                if m:
                    return m.group(1)
            break
    return ""


# --- config convenience wrappers (read + parse) ------------------------------

def config_str(section: str, key: str) -> str:
    if not os.access(CONFIG_TOML, os.R_OK):
        return ""
    return parse_config_str(read_text(CONFIG_TOML), section, key)


def config_array(section: str, key: str) -> str:
    if not os.access(CONFIG_TOML, os.R_OK):
        return ""
    return parse_config_array(read_text(CONFIG_TOML), section, key)
