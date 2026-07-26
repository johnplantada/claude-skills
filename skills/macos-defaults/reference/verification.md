# Verification — prove settings took, never trust the write

The golden rule: a `defaults write` is not done until `defaults read` confirms it. Writes can no-op,
coerce a type, or land in the wrong domain — so re-read every setting you changed.

## Each setting reads back as intended

The whole "did every declared line take?" check is one call — `scripts/drift_audit.py` re-reads each
`defaults write` target and reports `MATCH`/`DRIFT`/`MISSING` (type-aware, so `-bool true` matches a
live `1`):

```bash
scripts/drift_audit.py ~/.config/devenv/macos.sh    # all MATCH + exit 0 = every write took
```
Any `DRIFT`/`MISSING` line names the key that didn't take — check the domain/key spelling and value
type, then re-apply.

<details><summary>Under the hood — the raw per-key re-reads</summary>

```bash
# declared: defaults write com.apple.dock autohide -bool true
defaults read com.apple.dock autohide          # -> 1   (true)
defaults read com.apple.finder AppleShowAllExtensions   # -> 1
defaults read NSGlobalDomain KeyRepeat         # -> 2
defaults read com.apple.screencapture location # -> /Users/you/Desktop/Screenshots
```
`-bool true`/`false` read back as `1`/`0`. Or `scripts/defaults_read.py <domain> <key>` for one, with
`(not set)` when the key is absent.
</details>

## Idempotency — a second apply changes nothing

```bash
defaults read com.apple.dock > /tmp/dock.a
bash ~/.config/devenv/macos.sh
defaults read com.apple.dock > /tmp/dock.b
diff /tmp/dock.a /tmp/dock.b        # no output = idempotent (as it must be)
```
Any diff on a re-run means a line isn't idempotent (often a wrong type, or a value the OS rewrites).

## Restart-dependent settings

Some settings won't reflect in `defaults read` behavior until the owning app reloads or you log out:
- After `killall Dock Finder SystemUIServer`, the read value is correct **and** the UI shows it.
- Key-repeat and some trackpad settings read back correct immediately but only **behave** after
  logout/reboot. Note this — a correct read is not proof the UI has picked it up yet.

## Finding a setting's domain/key

When you don't know what to read/write:

```bash
scripts/defaults_read.py --find "tap to click"   # search all domains/keys/values for a term
scripts/defaults_read.py --domains               # list every domain that has prefs
```
(These wrap `defaults find` / `defaults domains`.)
Or **diff before/after toggling in System Settings** — the reliable way to find an obscure key:

```bash
defaults read > /tmp/defaults.before          # snapshot everything
# ...toggle the setting in System Settings...
defaults read > /tmp/defaults.after
diff /tmp/defaults.before /tmp/defaults.after # the changed lines name the domain + key
```

## Report

Every changed key read back as intended (or which didn't and why), that a re-apply was a no-op, and
which settings still need logout/restart before their effect is visible.
