# macos-defaults scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the
same `defaults read` / parse / compare bash each time. Fewer tokens, no re-derivation, no
footguns (e.g. a missing key aborting `set -e`, or `-bool true` failing to match a live `1`).
These are the source of truth for the mechanical commands; the reference `.md` files carry the
judgment.

Run them by absolute path from the skill directory. The two inspectors are **read-only**
(`defaults read` only) and safe to re-run; `defaults_apply.py` is **mutating** and refuses to
run without `--yes`.

| Script | Purpose | Example |
|---|---|---|
| `defaults_read.py [groups… \| <domain> <key>]` | Read prefs in a greppable `domain key = value` form. No args = the curated set (dock finder keyboard trackpad screenshots global); group names filter it; a `<domain> <key>` pair does an ad-hoc read. `--find <term>` / `--domains` for discovery. Missing key → `(not set)`. **Read-only.** | `defaults_read.py dock finder` |
| `drift_audit.py <macos.sh> [--quiet]` | Parse every `defaults write` line out of a declared script and re-read each target live, classifying `MATCH` / `DRIFT` / `MISSING`. Type-aware (`-bool true` == live `1`; `$HOME`/`~` expanded). `--quiet` = only drift/missing. Exit non-zero if anything diverged. **Read-only.** | `drift_audit.py ~/.config/devenv/macos.sh` |
| `defaults_apply.py <macos.sh> [--yes]` | Back up touched domains → run the script → `killall` affected apps → flag reboot-needed settings. **Mutating** — a dry run without `--yes`, and it warns on `sudo`/security lines first. | `defaults_apply.py ~/.config/devenv/macos.sh --yes` |

## Worked example — the whole capture → apply → audit loop

```
defaults_read.py dock finder screenshots     # see live values → write matching lines into macos.sh
defaults_apply.py ~/.config/devenv/macos.sh --yes   # apply + restart Dock/Finder/SystemUIServer
drift_audit.py   ~/.config/devenv/macos.sh    # prove it: expect every line MATCH, exit 0
```
Later, to check for hand-made drift in System Settings:
```
drift_audit.py ~/.config/devenv/macos.sh --quiet    # lists only DRIFT/MISSING; empty = in sync
```
`DRIFT com.apple.dock tilesize: live=64 expected=48` = someone changed it by hand; `MISSING …` =
the script was never applied on this machine. Re-apply, or re-capture if the new value is intended.

## Conventions for adding scripts

- `#!/usr/bin/env python3`, `from __future__ import annotations`, Python 3.9+, stdlib only. Executable
  (`chmod +x`) with a `def main(argv=None) -> int` guarded by `if __name__ == "__main__": sys.exit(main())`.
- **Separate pure logic from IO.** Parsing / classification / formatting go in plain module functions the
  tests call directly (no mocking); the `defaults` / `killall` / `bash` subprocess calls stay in `_macos_common.py`.
- `defaults read` of a missing key exits non-zero — the wrapper returns `(False, "")` for it so callers
  report "not set" rather than aborting; `defaults find` swallows a non-zero exit like `|| true`.
- Print `domain key = value` / `LABEL domain key …` lines; keep output greppable and order stable.
- Bool compares normalize `true/yes/1` → `1` and `false/no/0` → `0` so type spellings don't cause false drift.
- The module docstring doubles as `--help`.
- Read-only inspectors only. The one mutating helper (`defaults_apply.py`) guards writes behind `--yes`.
