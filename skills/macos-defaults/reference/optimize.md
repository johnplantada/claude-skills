# Optimize workflow — audit drift and tighten the declaration

Goal: keep the machine and `macos.sh` honest — surface where they no longer match (the system was
changed by hand in System Settings, or the script declares a value the machine never got), and
tighten the declaration (pin settings worth capturing, prune lines for keys a newer macOS removed).
Read-only; nothing is written. (A declared setting that *won't take* is broken → [repair.md](repair.md).)

## 1. Run the auditor

```bash
scripts/drift_audit.py ~/.config/devenv/macos.sh            # or [macos-defaults].script
scripts/drift_audit.py ~/.config/devenv/macos.sh --quiet    # only DRIFT/MISSING lines
```
It parses every `defaults write <domain> <key> <type> <value>` line, re-reads each target live, and
classifies it — then prints a summary and exits non-zero if anything diverged:

```
MATCH   com.apple.dock autohide = 1
DRIFT   com.apple.dock tilesize: live=64 expected=48
MISSING com.apple.finder ShowPathbar: not set, expected 1
summary: 12 match, 1 drift, 1 missing (14 declared)
```
The compare is **type-aware**: `-bool true/yes/1` all match a live `1` (and `false/no/0` a live `0`),
and `$HOME`/`~` in a declared string path is expanded before comparing — so type spellings and home
paths don't show as false drift.

<details><summary>Under the hood — the raw per-key compare the auditor automates</summary>

```bash
# declared: defaults write com.apple.dock autohide -bool true
defaults read com.apple.dock autohide 2>/dev/null      # live -> 1 (true) means match
```
A quick sweep over one domain against a backup:

```bash
diff <(defaults read com.apple.dock 2>/dev/null) /tmp/macos.dock.before 2>/dev/null
```
Booleans read back as `0`/`1`; map `-bool true` → `1` when comparing.
</details>

## 2. Classify each difference

The auditor's label maps straight to a meaning and an action:

| Auditor label | Meaning | Action |
|---|---|---|
| `MATCH` | live == declared, in sync | none |
| `DRIFT` | live != declared — **system drifted** (changed by hand) | re-apply, or update the script if the new value is intended |
| `MISSING` | key present in script, not set live — script **never applied** here | run [upgrade.md](upgrade.md) |
| _(not listed)_ | a live key **absent from the script** — **undeclared** setting | add via [setup.md](setup.md), or leave it (the auditor only covers declared lines) |

The auditor covers every declared line; catching keys that are set live but *not* declared is
`scripts/defaults_read.py` territory (compare its dump against the script).

## 3. Prioritize

Lead with drift on settings that matter — security-adjacent keys, anything that changes behavior
(key-repeat, tap-to-click), then cosmetic. Distinguish clearly:
- **System changed vs script** → the machine drifted; decide re-apply vs re-capture.
- **Script changed vs system** → the declaration is ahead; `apply` to converge.

## Report

A table of drifted keys (domain/key, live value, declared value, classification), which direction
each drifted, and the recommended fix (re-apply, re-capture, or accept). Don't auto-write — optimize
only reports; converging is [upgrade.md](upgrade.md) or [setup.md](setup.md).
