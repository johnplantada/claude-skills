# Set up workflow — capture your prefs into a declarative script

Goal: stand up the declarative artifact — a commented, idempotent `macos.sh` of `defaults write`
lines that **reflects the current machine**. Read each value first, then write the line — the script
is a mirror of reality, not a guess.

> **New machine** with a tracked `macos.sh` already? You don't capture — you *apply* it to reach your
> baseline: [upgrade.md](upgrade.md). This path is for creating (or extending) the script from a
> machine's live prefs. A declared setting that won't take → [repair.md](repair.md).

## 1. Confirm scope

Confirm the target script path (default `~/.config/devenv/macos.sh`, or `[macos-defaults].script`
from settings) and which areas to capture. Offer a curated, popular set and let the user trim:

| Area | Domain(s) |
|---|---|
| Dock | `com.apple.dock` |
| Finder | `com.apple.finder`, `NSGlobalDomain` |
| Keyboard / key-repeat | `NSGlobalDomain` |
| Trackpad (tap-to-click) | `com.apple.driver.AppleBluetoothMultitouch.trackpad`, `com.apple.AppleMultitouchTrackpad` |
| Screenshots (format + location) | `com.apple.screencapture` |
| Global UI | `NSGlobalDomain` |

## 2. Read current values first

For every setting you plan to declare, read what's actually set so the script matches the machine.
Use the inspector — one call dumps the curated set (or the groups you name) in a stable, greppable
`domain key = value` form, with `(not set)` for keys at their OS default:

```bash
scripts/defaults_read.py                       # whole curated set
scripts/defaults_read.py dock finder screenshots   # just those groups
scripts/defaults_read.py com.apple.dock autohide   # one ad-hoc domain + key
```
`(not set)` means the OS default is in effect — decide with the user whether to pin it explicitly or
leave it out.

<details><summary>Under the hood — the raw reads the inspector wraps</summary>

```bash
defaults read com.apple.dock autohide 2>/dev/null
defaults read com.apple.finder AppleShowAllExtensions 2>/dev/null
defaults read NSGlobalDomain KeyRepeat 2>/dev/null
defaults read com.apple.screencapture location 2>/dev/null
```
A missing key exits non-zero and prints `does not exist` to stderr; the inspector captures that and
reports `(not set)` instead of aborting.
</details>

## 3. Write the script — grouped, commented, idempotent

Each line is a `defaults write`; re-running is a no-op. Group by area with comments. A curated,
sensible starting set:

```bash
#!/usr/bin/env bash
# ~/.config/devenv/macos.sh — declarative macOS defaults. Idempotent: safe to re-run.
# Apply with the macos-defaults skill (restarts affected apps + verifies). Track via chezmoi.
set -euo pipefail

# --- Dock ---
defaults write com.apple.dock autohide -bool true            # auto-hide the Dock
defaults write com.apple.dock tilesize -int 48               # icon size
defaults write com.apple.dock show-recents -bool false       # no recent apps

# --- Finder ---
defaults write com.apple.finder AppleShowAllExtensions -bool true    # show all file extensions
defaults write com.apple.finder AppleShowAllFiles -bool true         # show hidden files
defaults write com.apple.finder ShowPathbar -bool true               # path bar
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"  # list view

# --- Keyboard / key-repeat (fast) ---
defaults write NSGlobalDomain KeyRepeat -int 2               # repeat rate (lower = faster)
defaults write NSGlobalDomain InitialKeyRepeat -int 15       # delay until repeat
defaults write NSGlobalDomain ApplePressAndHoldEnabled -bool false   # key repeat over accents

# --- Trackpad: tap-to-click ---
defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking -bool true
defaults write com.apple.AppleMultitouchTrackpad Clicking -bool true

# --- Screenshots ---
defaults write com.apple.screencapture type -string "png"           # format
defaults write com.apple.screencapture location -string "$HOME/Desktop/Screenshots"  # location
defaults write com.apple.screencapture disable-shadow -bool true     # no window shadow
```
Match value types to what `scripts/defaults_read.py` reported (`-bool`, `-int`, `-string`, `-float`).
Note in a comment any line that needs logout/restart (see [upgrade.md](upgrade.md)). Once written,
`scripts/drift_audit.py <script>` should read every line `MATCH` against the machine you captured from.

## 4. Track it

The script is a dotfile — offer to version it via the `dotfiles` skill:
```bash
chezmoi add ~/.config/devenv/macos.sh
```
And offer to save the path back to `[macos-defaults].script` in `config.toml` if it wasn't already there.

## Report

Which areas/keys were captured, any keys left at OS default (not pinned), any `sudo`-only settings
skipped, and the script path. Then point the user at [upgrade.md](upgrade.md) to run it.
