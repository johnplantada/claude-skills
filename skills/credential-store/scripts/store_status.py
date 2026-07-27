#!/usr/bin/env python3
"""Which credential stores exist on this machine, and which to move secrets INTO. Read-only.
Part of the credential-store skill.

    store_status.py          # what's available, and the recommended destination

`credential_audit.py` finds credentials sitting in plaintext; this answers the question
that immediately follows — *move them where?* A finding with no destination is not
actionable, and picking a store the machine can't actually use wastes the user's time.

SECRETS: this reports store PRESENCE and account metadata only. It never enumerates,
reads, or unlocks a stored item — `security find-generic-password` and `op read` are
never called here. Writing a secret INTO a store is an out-of-band step the user runs;
the value must not pass through the model.
"""

from __future__ import annotations

import json
import sys

import _credential_common as cc

from lib.devenv_common import command_available, undetermined

# Preference order when several stores are usable. Keychain first: it is built in, needs
# no subscription, and shell references to it work with no daemon running.
_PREFERENCE = ("keychain", "1password", "pass", "chezmoi-encryption")

_HOW_TO_REFERENCE = {
    "keychain": 'export FOO_TOKEN="$(security find-generic-password -s FOO_TOKEN -w)"',
    "1password": 'export FOO_TOKEN="$(op read op://Personal/FOO/token)"',
    "pass": 'export FOO_TOKEN="$(pass show FOO/token)"',
    "chezmoi-encryption": "template the file and let `chezmoi apply` decrypt it",
}


# --- pure logic ----------------------------------------------------------------


def parse_op_accounts(json_text: str) -> list[str]:
    """Account identifiers from `op account list --format=json` (email, else url, else id).

    Returns [] on anything unparseable rather than raising — a store that can't be read is
    reported as undetermined by the caller, never as absent.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for entry in data:
        if isinstance(entry, dict):
            name = entry.get("email") or entry.get("url") or entry.get("account_uuid") or ""
            if name:
                out.append(str(name))
    return out


def recommend(available: dict[str, bool]) -> str:
    """The store to move secrets into: the first available in preference order, else ''."""
    return next((name for name in _PREFERENCE if available.get(name)), "")


def how_to_reference(store: str) -> str:
    """The shell line that turns a literal into a reference for `store` ('' if unknown)."""
    return _HOW_TO_REFERENCE.get(store, "")


def store_state(name: str, available: dict[str, bool], unusable: dict[str, str]) -> str:
    """`available` | `absent` | `unusable` for one store.

    `unusable` is a THIRD state, not a flavour of absent: an installed-but-locked 1Password
    is present on the machine and simply needs unlocking. Reporting it as `absent` sends
    the user to install a store they already own — and it contradicts the `undetermined`
    note printed right below it, which is how this first shipped.
    """
    if available.get(name):
        return "available"
    return "unusable" if name in unusable else "absent"


def format_stores(available: dict[str, bool], detail: dict[str, str],
                  unusable: dict[str, str] | None = None) -> list[str]:
    """Greppable `store.<name><TAB>available|unusable|absent` rows plus any detail line."""
    unusable = unusable or {}
    rows = []
    for name in _PREFERENCE:
        rows.append(f"store.{name}\t{store_state(name, available, unusable)}")
        if unusable.get(name):
            rows.append(f"store.{name}.reason\t{unusable[name]}")
        if detail.get(name):
            rows.append(f"store.{name}.detail\t{detail[name]}")
    return rows


# --- collection (IO) -----------------------------------------------------------


def collect() -> tuple[dict[str, bool], dict[str, str], dict[str, str]]:
    """(available, detail, unusable) across every supported store. All probes read-only."""
    available: dict[str, bool] = {}
    detail: dict[str, str] = {}
    unusable: dict[str, str] = {}

    available["keychain"] = cc.keychain_available()

    op_installed, op_raw = cc.op_accounts()
    accounts = parse_op_accounts(op_raw) if op_installed else []
    available["1password"] = bool(accounts)
    if op_installed and not accounts:
        # Installed but no account resolved — almost always locked or signed out. A third
        # state, not "absent": the store is here and needs unlocking, not installing.
        unusable["1password"] = "op is installed but listed no account (locked, or not signed in)"
    elif accounts:
        detail["1password"] = f"accounts={', '.join(accounts)}"

    available["pass"] = command_available("pass")

    encryption = cc.chezmoi_encryption()
    available["chezmoi-encryption"] = bool(encryption)
    if encryption:
        detail["chezmoi-encryption"] = f"backend={encryption}"

    return available, detail, unusable


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "-h" in args or "--help" in args:
        print(__doc__.strip())
        return 0

    available, detail, unusable = collect()
    lines = format_stores(available, detail, unusable)

    choice = recommend(available)
    if choice:
        lines.append(f"recommended\t{choice}")
        lines.append(f"reference_form\t{how_to_reference(choice)}")
    elif unusable:
        # Nothing is usable RIGHT NOW, but a store exists — unlocking beats installing.
        lines.append(undetermined("recommended",
                                  f"no store is usable yet; unlock {', '.join(sorted(unusable))} first"))
    else:
        lines.append(undetermined("recommended", "no usable credential store found on this machine"))

    print("\n".join(lines))
    return 0 if choice else 1


if __name__ == "__main__":
    sys.exit(main())
