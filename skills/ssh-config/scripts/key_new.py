#!/usr/bin/env python3
"""key_new.py <name> <comment> — generate a new ed25519 key, load it into the agent +
keychain, and show its PUBLIC half ready to register. MUTATING.

  name     filename under ~/.ssh (e.g. id_ed25519_myserver). Refuses to overwrite.
  comment  the -C label (email or user@host). A LABEL, not a secret.

STATE-CHANGING — this creates a key file, edits the agent, and writes to the login keychain.
ssh-keygen PROMPTS for a passphrase interactively; ALWAYS set one (a passphrase-less private
key is a single-file compromise). This script never passes -N '' and never disables the prompt.

After it runs, register the PUBLIC key (printed at the end) with the remote — e.g.
  gh ssh-key add ~/.ssh/<name>.pub --title "<host>"
Never paste the private half (the file without .pub) anywhere. See reference/keys.md.

SECRETS: only ever displays ~/.ssh/<name>.pub (public). The private key is generated on disk
with 600 perms by ssh-keygen and is never printed, cat'd, or copied by this script.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import _ssh_common as sc


def public_key_report(key: str, name: str, pub_text: str) -> list[str]:
    """The trailing 'register it' block, shown after the key is generated. `pub_text` is
    the PUBLIC key file's contents — the only key material this script ever surfaces."""
    return [
        "",
        "== public key (safe to register) ==",
        pub_text.rstrip("\n"),
        "",
        f'register it, e.g.:  gh ssh-key add {key}.pub --title "{name}"',
        f"add a Host block pointing IdentityFile at {key} (see setup.md), then verify with:",
        "  ssh_config_audit.py <host>   &&   ssh -T <host>",
    ]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2 or not args[0] or not args[1]:
        print("usage: key_new.py <name> <comment>", file=sys.stderr)
        return 1
    name, comment = args[0], args[1]
    key = sc.SSH_DIR / name

    if key.exists():
        print(f"refusing to overwrite existing key: {key}", file=sys.stderr)
        return 1

    sc.SSH_DIR.mkdir(parents=True, exist_ok=True)
    sc.SSH_DIR.chmod(0o700)

    # Interactive passphrase prompt (no -N) — the user MUST enter a passphrase.
    proc = subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-C", comment, "-f", str(key)]
    )
    if proc.returncode != 0:
        return proc.returncode
    key.chmod(0o600)
    Path(f"{key}.pub").chmod(0o644)

    # Load into agent + store the passphrase in the login keychain (older macOS: -K).
    if subprocess.run(
        ["ssh-add", "--apple-use-keychain", str(key)],
        stderr=subprocess.DEVNULL,
    ).returncode != 0:
        subprocess.run(["ssh-add", "-K", str(key)])
    subprocess.run(["ssh-add", "-l"])

    # Only the PUBLIC half is read and shown — never the private key.
    pub_text = sc.read_text(f"{key}.pub")
    print("\n".join(public_key_report(str(key), name, pub_text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
