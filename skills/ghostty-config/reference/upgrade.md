# Upgrade workflow — adopt new options, reconcile after a Ghostty bump

Two jobs: **converge a machine** to your tracked config (e.g. a fresh install), and **reconcile** the
config after a Ghostty version bump — adopt useful new options, retire deprecated keys. Always
re-validate; a config that parsed on the old version can break on the new one.

## A. Converge a machine to your tracked config

New machine (or one that's drifted) with the config already in dotfiles:

```bash
ghostty +version
chezmoi apply ~/.config/ghostty/config        # bring the tracked config down (dotfiles skill)
```
Then wire the macOS include so it's authoritative (this part is machine-local, usually not tracked):
```bash
LIB=~/Library/Application\ Support/com.mitchellh.ghostty/config
[ -f "$LIB" ] && cp "$LIB" "$LIB.bak.$(date +%Y%m%d-%H%M%S)"
printf '# Managed by ghostty-config: real config in ~/.config/ghostty/config\nconfig-file = ~/.config/ghostty/config\n' > "$LIB"
scripts/ghostty_doctor.py                      # validate ok, include <xdg>, in_sync yes
scripts/font_check.py                          # fonts installed on THIS machine? (install if MISSING)
```
A `MISSING` font is the common new-machine gap — the config references a Nerd Font that isn't
installed here yet. Install it (`brew install --cask font-<name>-nerd-font`) and re-check.

## B. Reconcile after a version bump

```bash
ghostty +version                               # note the new version
scripts/config_audit.py ~/.config/ghostty/config    # any `error  <key>: unknown field` now?
```
- **Deprecated / renamed keys** surface as `unknown field`. Find the replacement in the current docs
  (`ghostty +show-config --default --docs | grep -iA4 '<topic>'`) and update the line. Remove options
  that were dropped entirely.
- **New options worth adopting** — skim what's new for your version and add only what you'll use
  (keep the config lean; [optimize.md](optimize.md) drops cruft). Validate each addition.

## C. Refresh font / theme (optional)

```bash
ghostty +list-themes | grep -i <partial>       # new/renamed themes
ghostty +list-fonts  | grep -i <partial>       # confirm a font family name before switching
```
Change one thing at a time and re-validate, so a regression is easy to attribute.

## Verify

```bash
scripts/ghostty_doctor.py                       # validate ok, in_sync yes
scripts/show_effective.py                        # the resolved config after the changes
```
Live-reload an open window (`cmd+shift+,`); open a new window for `command`/window-creation options.

## Track & report

Re-track if the config changed (`chezmoi add ~/.config/ghostty/config`). Report: the Ghostty version,
any keys retired/renamed, options adopted, font/theme changes, and the validate + show-config evidence.
