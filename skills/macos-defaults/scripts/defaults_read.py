#!/usr/bin/env python3
"""Read the prefs you care about in a stable, greppable form. Part of the
macos-defaults skill. READ-ONLY: never writes. A missing key prints "(not set)"
instead of aborting.

Usage:
    defaults_read.py                       # dump the whole curated set (all groups)
    defaults_read.py dock finder           # only those groups (dock finder keyboard
                                           #   trackpad screenshots global)
    defaults_read.py com.apple.dock autohide   # ad-hoc: one domain + key
    defaults_read.py --find "tap to click"     # search all domains for a term
    defaults_read.py --domains                 # list every domain that has prefs

Output is one `domain key = value` line per setting (stable order). Booleans read
back as 1/0; "(not set)" means the OS default is in effect (key not written).
"""

from __future__ import annotations

import re
import sys

import _macos_common as mc

# Curated set — mirrors the setup.md popular table. One "group|domain|key" per line.
CURATED = """
dock|com.apple.dock|autohide
dock|com.apple.dock|tilesize
dock|com.apple.dock|show-recents
dock|com.apple.dock|mineffect
dock|com.apple.dock|orientation
finder|com.apple.finder|AppleShowAllExtensions
finder|com.apple.finder|AppleShowAllFiles
finder|com.apple.finder|ShowPathbar
finder|com.apple.finder|ShowStatusBar
finder|com.apple.finder|FXPreferredViewStyle
finder|com.apple.finder|_FXSortFoldersFirst
finder|NSGlobalDomain|AppleShowAllExtensions
keyboard|NSGlobalDomain|KeyRepeat
keyboard|NSGlobalDomain|InitialKeyRepeat
keyboard|NSGlobalDomain|ApplePressAndHoldEnabled
trackpad|com.apple.driver.AppleBluetoothMultitouch.trackpad|Clicking
trackpad|com.apple.AppleMultitouchTrackpad|Clicking
screenshots|com.apple.screencapture|type
screenshots|com.apple.screencapture|location
screenshots|com.apple.screencapture|disable-shadow
global|NSGlobalDomain|AppleInterfaceStyle
global|NSGlobalDomain|NSDocumentSaveNewDocumentsToCloud
"""


def parse_curated(text: str = CURATED) -> list[tuple[str, str, str]]:
    """Parse the CURATED block into (group, domain, key) triples, skipping blanks."""
    out: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        group, domain, key = line.split("|")
        out.append((group, domain, key))
    return out


def select_targets(
    groups: list[str], curated: list[tuple[str, str, str]] | None = None
) -> list[tuple[str, str, str]]:
    """The curated triples, optionally filtered to the named group(s). No groups → all."""
    triples = parse_curated() if curated is None else curated
    if not groups:
        return list(triples)
    return [t for t in triples if t[0] in groups]


def looks_like_domain(arg: str) -> bool:
    """True if the arg reads as a defaults domain: has a dot, or is NSGlobalDomain."""
    return "." in arg or arg == "NSGlobalDomain"


def collapse_value(raw: str) -> str:
    """Collapse embedded newlines to spaces and squeeze runs of spaces, so a multi-line
    array/dict value stays on one greppable line."""
    return re.sub(r" +", " ", raw.replace("\n", " "))


def format_reading(domain: str, key: str, value: str | None) -> str:
    """One `domain key = value` line, or `… = (not set)` when the key is absent."""
    if value is None:
        return f"{domain} {key} = (not set)"
    return f"{domain} {key} = {collapse_value(value)}"


def parse_domains_output(raw: str) -> list[str]:
    """Split `defaults domains` comma-separated output into a sorted list of domains."""
    names = [d.strip() for d in raw.split(",")]
    return sorted(n for n in names if n)


def read_one(domain: str, key: str) -> str:
    """Read one key via the CLI wrapper and format its line."""
    ok, value = mc.read_key(domain, key)
    return format_reading(domain, key, value if ok else None)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if args and args[0] == "--find":
        if len(args) < 2:
            print("defaults_read: --find needs a search term", file=sys.stderr)
            return 1
        sys.stdout.write(mc.find(args[1]))
        return 0
    if args and args[0] == "--domains":
        print("\n".join(parse_domains_output(mc.domains())))
        return 0

    # Ad-hoc: <domain> <key> when the first arg looks like a domain and a key follows.
    if len(args) >= 2 and looks_like_domain(args[0]):
        print(read_one(args[0], args[1]))
        return 0

    # Curated set, optionally filtered by group name(s).
    for _group, domain, key in select_targets(args):
        print(read_one(domain, key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
