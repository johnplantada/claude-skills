---
name: macOS Defaults
description: Set up, repair, upgrade, and optimize a Mac's system preferences as reproducible, idempotent `defaults` code. Use to SET UP a declarative, commented `macos.sh` by capturing current prefs (Dock, Finder, keyboard/trackpad, screenshots), REPAIR a setting that won't take (wrong domain/key/type, needs a restart or sudo, OS-rewritten), UPGRADE by applying the script to converge a machine and reconciling after a macOS update, or OPTIMIZE by auditing live values against the script for drift and tightening the declaration. Every setting is proven by re-reading it — writes are never trusted blindly.
argument-hint: [setup|repair|upgrade|optimize]
allowed-tools: Bash(*macos-defaults/scripts/*), Bash(defaults read *), Bash(defaults find *), Bash(defaults domains), Bash(cat *), Bash(ls *), Bash(git -C * *)
---

# macOS defaults

Turn a Mac's system settings into **idempotent `defaults` code**, so a machine's preferences are
reproducible, reviewable, and drift is visible. The golden rule is **verification-first**: prove a
setting took by re-reading it — never trust that a `defaults write` did what you meant.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Snapshot current prefs into a declarative script | [reference/setup.md](reference/setup.md) |
| Fix a setting that won't stick (wrong key/type, needs restart/sudo) | [reference/repair.md](reference/repair.md) |
| Apply the script to a machine + restart apps; reconcile after an OS update | [reference/upgrade.md](reference/upgrade.md) |
| Find drift between live values and the script, and tighten it | [reference/optimize.md](reference/optimize.md) |
| Prove settings took (and stay idempotent) | [reference/verification.md](reference/verification.md) |

## The scripts (call these, don't re-compose bash)

The mechanical commands live in [`scripts/`](scripts/README.md) as tested helpers — call them by
name instead of hand-writing `defaults read` loops or a parse-and-compare each session:

| Script | Does | Read-only? |
|---|---|---|
| `scripts/defaults_read.py [groups… \| <domain> <key>]` | Read prefs as greppable `domain key = value`; no args = the curated set; `--find`/`--domains` for discovery; missing key → `(not set)`. | yes |
| `scripts/drift_audit.py <macos.sh> [--quiet]` | Parse a declared script's `defaults write` lines and re-read each live → `MATCH`/`DRIFT`/`MISSING` (type-aware: `-bool true` == `1`; `$HOME`/`~` expanded). | yes |
| `scripts/defaults_apply.py <macos.sh> [--yes]` | Back up → run the script → `killall` affected apps → flag reboot-needed. **Mutating**; dry-runs without `--yes` and confirms before writing. | no |

See [scripts/README.md](scripts/README.md) for the full toolbox, a worked example, and conventions.

## Discovery (always run first)

```bash
sw_vers                                                   # macOS version (some keys are version-specific)
ls ~/.config/devenv/macos.sh 2>/dev/null                  # is there already a declared script?
scripts/defaults_read.py                                  # sample live values across the curated set
scripts/defaults_read.py --find <term>                    # locate a setting's domain/key by keyword
```
- A **domain** is an app's pref bundle id (`com.apple.dock`, `com.apple.finder`, `NSGlobalDomain`
  for system-wide). A **key** is one setting inside it. `defaults read <domain> <key>` prints one value.
- Don't know a setting's domain/key? `scripts/defaults_read.py --find <term>`, or diff `defaults read`
  before/after toggling it in System Settings — see [reference/verification.md](reference/verification.md).

## Core principles

1. **Verify by re-reading.** After `defaults write`, `defaults read <domain> <key>` and confirm it
   equals the intended value. A silent write can no-op or coerce the type.
2. **Read reality before you declare it.** `setup` reads current values so the script reflects
   the machine, not a guess.
3. **Idempotent by construction.** The script is pure `defaults write` lines — re-running is a
   no-op. `optimize` confirms live == declared; a second `upgrade` (apply) changes nothing.
4. **Some settings need a restart.** `killall Dock Finder SystemUIServer` picks up most; a few
   need logout/reboot and won't reflect until then. Flag those explicitly.
5. **Track the script.** It's a dotfile — version it via the `dotfiles` skill (chezmoi) so prefs
   are reproducible across machines.

## Settings

Read `~/.config/devenv/config.toml` before prompting; if a `[macos-defaults]` section exists, use it
as defaults (precedence: explicit answer this session > `config.toml` > ask). Had to ask? Offer to
save the answer back. Managed by the `devenv` skill. Keys honored:
- `script` — path to the declarative defaults script (e.g. `~/.config/devenv/macos.sh`).

## Safety

- **Some domains need `sudo`** (system-wide `/Library` prefs, login window). Confirm first; never
  run `sudo defaults write` without the user's go-ahead.
- **Back up prior values** with `defaults read <domain> <key>` before writing, so a change is reversible.
- **Do NOT touch security/privacy settings** — FileVault, Gatekeeper, the firewall, TCC — without
  explicit confirmation. Never disable a security feature silently.
- Some settings require **logout or restart** to take effect; say so rather than claiming success.
- `defaults write` is **mutating** and is deliberately not pre-approved here — the skill reads
  freely but asks before it writes.
