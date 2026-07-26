#!/usr/bin/env python3
"""Apply a declared defaults script, then restart the affected apps. Part of the
macos-defaults skill. MUTATING: this runs `defaults write` (via the script) and
`killall`. It refuses to run without --yes so a stray invocation can't silently
change prefs.

Usage:
    defaults_apply.py ~/.config/devenv/macos.sh            # dry run: back up + preview only
    defaults_apply.py ~/.config/devenv/macos.sh --yes      # actually apply + restart apps

What it does (in order):
    1. Reads the script and WARNS on `sudo` / security-sensitive lines (won't proceed
       past those without the operator having seen them).
    2. Backs up every touched domain to a fresh private temp dir (mkdtemp), one
       <domain>.before file each — reversible, and a re-run can't clobber the
       previous run's backups.
    3. Without --yes: stops here (dry run). With --yes: runs `bash <script>`.
    4. `killall Dock Finder SystemUIServer` so UI settings reload (harmless if not running).
    5. Reminds which settings still need logout/reboot to take effect.

Verify the result with:  drift_audit.py <macos.sh>   (every line should read MATCH).
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

import _macos_common as mc

_SENSITIVE_RE = re.compile(
    r"sudo|FileVault|Gatekeeper|com\.apple\.(alf|security)|spctl|TCC"
)
_WRITE_DOMAIN_RE = re.compile(r"^\s*defaults\s+write\s+(\S+)\s+(\S+)")

REBOOT_NOTE = """== may need logout/reboot before they take effect ==
  - NSGlobalDomain KeyRepeat / InitialKeyRepeat (next login)
  - trackpad tap-to-click on some macOS versions
  - anything read by an app only at launch
Verify with: drift_audit.py <macos.sh>  (expect all MATCH)"""


def find_sensitive_lines(text: str) -> list[tuple[int, str]]:
    """1-based (lineno, line) for every sudo / security-sensitive line, in file order.
    Mirrors `grep -nE 'sudo|FileVault|Gatekeeper|com.apple.(alf|security)|spctl|TCC'`."""
    out: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _SENSITIVE_RE.search(line):
            out.append((i, line))
    return out


def extract_write_domains(text: str) -> list[str]:
    """Unique domains (third field) of every `defaults write` line, in first-seen order.
    Mirrors `grep '^…defaults write' | awk '{print $3}' | awk '!seen[$0]++'`."""
    seen: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        m = _WRITE_DOMAIN_RE.match(line)
        if not m:
            continue
        domain = m.group(1)
        if domain not in seen:
            seen.add(domain)
            out.append(domain)
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    script = args[0] if args else ""
    apply = len(args) >= 2 and args[1] == "--yes"

    if script in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if not script:
        print("usage: defaults_apply.py <macos.sh> [--yes]", file=sys.stderr)
        return 2
    path = Path(script)
    if not path.is_file():
        print(f"not a file: {script}", file=sys.stderr)
        return 2

    text = path.read_text()

    # 1. Flag sudo / security-sensitive lines for the operator to review.
    flags = find_sensitive_lines(text)
    if flags:
        print("== review: sudo / security-sensitive lines ==")
        for lineno, line in flags:
            print(f"{lineno}:{line}")
        print("-- confirm these are intended before applying --")

    # 2. Back up each domain the script writes to (unique, stable order). A fresh
    # mkdtemp per run: private (0700), never overwrites an earlier run's backups, and
    # a hostile domain token from the script text can't traverse outside it.
    backup_dir = Path(tempfile.mkdtemp(prefix="macos-defaults."))
    print(f"== backing up touched domains to {backup_dir} ==")
    for domain in extract_write_domains(text):
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", domain)
        out = backup_dir / f"{safe}.before"
        ok, contents = mc.read_domain(domain)
        if not ok:
            print(f"  ({domain} had no existing prefs)")
        out.write_text(contents)
        print(f"  {domain} -> {out}")

    # 3. Apply (guarded).
    if not apply:
        print("== dry run (no --yes): not applying. Re-run with --yes to write. ==")
        return 0
    print(f"== applying: bash {script} ==")
    mc.run_bash(path)

    # 4. Restart the apps that reload prefs only on relaunch.
    print("== restarting affected apps ==")
    mc.killall(["Dock", "Finder", "SystemUIServer"])

    # 5. Remind about settings that need logout/reboot.
    print(REBOOT_NOTE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
