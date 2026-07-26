# Set up workflow — a clean, reproducible Ghostty config

Goal: stand up a **commented, declarative config** that reflects what you want, in the location that
actually works on macOS. The source of truth is `~/.config/ghostty/config` (dotfiles-tracked); the
macOS Library file becomes a one-line pointer to it. Prove it with `ghostty +validate-config` and
`ghostty +show-config`.

> **New machine** with a config already tracked in dotfiles? You don't author — you `chezmoi apply`
> and wire the include: [upgrade.md](upgrade.md). A config that won't load → [repair.md](repair.md).

## 1. Discover what exists

```bash
ghostty +version
scripts/ghostty_doctor.py                    # valid? which file loads? split-brain?
ls -la ~/.config/ghostty/config \
  ~/Library/Application\ Support/com.mitchellh.ghostty/config 2>/dev/null
```
Three starting states:
- **Only the Library file** (Ghostty's auto-created default) → *migrate* its contents to `~/.config`
  (step 3), then add the include (step 4).
- **Only `~/.config/ghostty/config`** → likely *not being read* (macOS needs `XDG_CONFIG_HOME` or the
  include). Add the include (step 4).
- **Nothing** → author a fresh config in `~/.config` (step 2), then include it.

## 2. Author the config (`~/.config/ghostty/config`)

Group by area, comment each line. A sensible, popular starting set — trim with the user:

```ini
# ~/.config/ghostty/config — real Ghostty config (tracked in dotfiles). Reload: cmd+shift+,

# --- Font (install a Nerd Font so prompt/powerline glyphs render, not tofu) ---
font-family = JetBrainsMono Nerd Font
font-size = 14

# --- Theme (must match `ghostty +list-themes`; light/dark: `light:X,dark:Y`) ---
theme = Catppuccin Mocha

# --- Default shell (see the shell-sync skill for which shell is canonical) ---
command = /opt/homebrew/bin/fish --login

# --- Window ---
background-opacity = 0.95
window-padding-x = 8
window-padding-y = 8
macos-titlebar-style = tabs

# --- Keybinds (superset; reload_config is how you verify without a restart) ---
keybind = cmd+shift+comma=reload_config
```
Validate values as you pick them: `ghostty +list-themes`, `ghostty +list-fonts`, `ghostty +list-keybinds`.
Confirm the shell exists before writing `command`: `command -v fish`.

## 3. Migrating existing Library settings

If the real settings currently live in the Library file, move them into `~/.config/ghostty/config`
first (back up both):

```bash
LIB=~/Library/Application\ Support/com.mitchellh.ghostty/config
ts=$(date +%Y%m%d-%H%M%S); cp "$LIB" "$LIB.bak.$ts"
mkdir -p ~/.config/ghostty
# copy real settings across (or hand-move the non-comment lines), then verify below
```

## 4. Wire the macOS include (the crucial step)

Ghostty on macOS reads the Library file and it **overrides** `~/.config`. So make the Library file a
one-line include of your real config — that's what makes `~/.config/ghostty/config` authoritative:

```ini
# ~/Library/Application Support/com.mitchellh.ghostty/config
# Managed by ghostty-config: real config lives in ~/.config/ghostty/config (dotfiles).
config-file = ~/.config/ghostty/config
```
Nothing else belongs in the Library file. (Verified: a `font-size` set only in `~/.config` takes
effect through this include, and `+validate-config` stays clean.)

## 5. Verify (the point)

```bash
scripts/ghostty_doctor.py                    # expect: validate ok, include <xdg>, in_sync yes
scripts/show_effective.py font theme command # the values you set are actually in effect
scripts/font_check.py                        # font resolves + advertises nerd-font glyphs
```
Then **live-reload** an open window with `cmd+shift+,` (no restart). `command` applies to *new*
windows — open one to see the shell change. See [verification.md](verification.md).

## 6. Track it

`~/.config/ghostty/config` is a dotfile — offer to version it via the `dotfiles` skill:
```bash
chezmoi add ~/.config/ghostty/config
```
Note the Library include is machine-local (an absolute macOS path); dotfiles usually ignores it —
the `dotfiles` skill's `ignore` list is the place for that. Offer to save `config`, `theme`, `font`
to `[ghostty-config]` in `~/.config/devenv/config.toml`.

## Report

Where the real config lives, that the Library include makes it authoritative, the font/theme/shell
chosen, the validate + show-config evidence, and whether it's tracked in dotfiles.
