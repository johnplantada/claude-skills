# Set up workflow — coordinate one theme across all four surfaces

Goal: make Ghostty, fish, zsh, and starship share **one** theme via the inherit model — convert any
hardcoded hex in starship/fish to ANSI names so they follow Ghostty's `theme`, then that theme is the
single knob. Prove it with `scripts/theme_status.py`.

> Want exact brand hex everywhere instead of inheritance? That's the **matched** model —
> [upgrade.md](upgrade.md). A surface that clashes after setup → [repair.md](repair.md).

## 1. Audit the starting point

```bash
scripts/theme_status.py
```
Each surface reads `inherits` (ANSI → follows the terminal) or `hardcoded (<n> hex)` (pinned, clashes).
The Ghostty line is your **knob** (`theme <name>`). Typical greenfield: Ghostty on some theme, starship
on a hardcoded preset (e.g. gruvbox hex), fish with a stray hardcoded color or two, zsh inheriting.

## 2. Pick the knob (the Ghostty theme)

Inherit mode: **any** Ghostty theme works — everything follows it.
```bash
scripts/theme_list.py              # cross-tool families; or `ghostty +list-themes`
```
Set it via the **ghostty-config** skill (`theme = <name>` in `~/.config/ghostty/config`), or keep the
current one. This is the only theme decision you'll make.

## 3. Convert starship → ANSI (`~/.config/starship.toml`)

Replace the `[palettes.*]` hex with ANSI **names** and point `palette =` at it. Names resolve to the
terminal's slots, so the prompt follows Ghostty:

```toml
palette = 'terminal'
[palettes.terminal]
color_fg0    = 'white'          # bright foreground / segment text
color_bg1    = 'black'          # darkest segment bg
color_bg3    = 'bright-black'   # muted segment bg
color_blue   = 'blue'
color_aqua   = 'cyan'
color_green  = 'green'
color_orange = 'red'            # ANSI 1 is the terminal's orange/red
color_purple = 'purple'
color_red    = 'bright-red'
color_yellow = 'yellow'
```
Also convert any inline `fg:#rrggbb` / `bg:#rrggbb` in `format = …` lines to a palette entry or ANSI
name. Verify **zero** hex remain and it still renders:
```bash
grep -nE '#[0-9a-fA-F]{6}' ~/.config/starship.toml || echo "no hex — inherits"
starship prompt --status=0 | cat -v | head -2      # should show \033[3Xm / [4Xm ANSI codes, not 38;2;R;G;B
```
Starship ANSI names: `black red green yellow blue purple cyan white` + `bright-*`, or slot numbers `0`–`255`.

## 4. Point fish at ANSI (`config.fish` overrides)

fish 4.3+ already stores its theme as **ANSI color names** in `conf.d/fish_frozen_theme.fish`
(auto-migrated from universal vars), so fish usually **inherits** the terminal out of the box. Confirm,
then fix only the exceptions:

```bash
fish -l -i -c 'for v in (set -n | grep fish_color); echo $v" = "$$v; end'   # any hex? any too-faded value?
```
- Values should be ANSI names (`blue`, `brblack`, …; fish names are `normal black red green yellow blue
  magenta cyan white` + `br*`). A **hex** value won't inherit — convert it to a name.
- **Overrides go in `config.fish`**, which loads *after* every `conf.d` file (this is fish's own
  guidance — see the header of `fish_frozen_theme.fish`). The 16-ANSI palette has no readable mid-gray,
  so pin the ghost/suggestion text to a fixed dim gray there (the one deliberate non-inherit):
  ```fish
  # ~/.config/fish/config.fish
  set -g fish_color_autosuggestion 8a8a8a   # ANSI 8 (brblack) blends into dark themes
  ```
- **No frozen theme** (older fish / clean install)? Put the full ANSI color set in `config.fish`
  directly, or in a `conf.d` file whose name sorts **after** any theme file.

## 5. zsh

No syntax highlighter → zsh already renders with the terminal ANSI palette; nothing to do. If
`zsh-syntax-highlighting` is installed, set `ZSH_HIGHLIGHT_STYLES[...]` to ANSI slot numbers
(`fg=4`, not `fg=#458588`) so it inherits too — see [repair.md](repair.md).

## 6. Verify + track

```bash
scripts/theme_status.py      # expect every surface "inherits" + "coordinated yes"
scripts/theme_swatch.py      # (in Ghostty) the shared palette
```
Reload Ghostty (`cmd+shift+,`) and open a **new shell**. Track the configs via `dotfiles`:
```bash
chezmoi add ~/.config/starship.toml ~/.config/fish/config.fish ~/.config/fish/conf.d/fish_frozen_theme.fish
```
Save `model`/`source`/`theme` to `[terminal-theme]` in `~/.config/devenv/config.toml`.

## Report

The knob (Ghostty theme), what was converted from hex→ANSI on each surface, the `theme_status.py`
proof (`coordinated yes`), and that switching themes is now a one-line Ghostty edit.
