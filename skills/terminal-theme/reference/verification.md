# Verification — the golden rule

Coordinated theming isn't "done" until you've proven two things: **no surface has hardcoded hex**
(everything references the terminal palette), and **switching the Ghostty theme moves every surface**.
Prove it; don't assume.

## The two checks

```bash
scripts/theme_status.py          # 1. every surface `inherits`, `coordinated yes` (exit 0)
scripts/theme_swatch.py          # 2. render the shared ANSI palette — in Ghostty
```
`theme_status.py` audits each config for hex that would break inheritance. `theme_swatch.py` shows the
16 colors everything is supposed to share — run it **inside Ghostty** to see the active theme's real
colors (in a plain pipe you'll see escape codes, which only proves the codes are emitted).

## The definitive proof: switch and watch

Inheritance is real only if changing the one knob re-themes everything:

1. Note the current theme, then set a **visibly different** Ghostty theme (e.g. `Gruvbox Dark` if
   you're on `Catppuccin Mocha`) via `ghostty-config`.
2. Reload Ghostty: **`cmd+shift+,`**. Open a **new shell** (fish/zsh read colors at startup — an open
   shell keeps its old colors).
3. The **prompt** (starship) and **fish** syntax colors should shift with the terminal. If one didn't,
   it still has hardcoded hex → [repair.md](repair.md).
4. Switch back.

## What "inherits" looks like under the hood

```bash
starship prompt --status=0 | cat -v | head -2
```
- **Inherits:** ANSI SGR codes — `\033[31m`, `\033[41;37m` (30–37 fg, 40–47 bg, 90–107 bright). The
  terminal maps these to its theme.
- **Hardcoded:** truecolor — `\033[38;2;214;93;14m` (literal R;G;B). The terminal can't re-theme it.

For fish, resolve in a real shell (files alone lie — universal vars + `conf.d` + `config.fish` all
contribute):
```bash
fish -l -i -c 'for v in (set -n | grep fish_color); echo -n "$v="; echo $$v; end'
```
Values should be names (`blue`, `brblack`) — no hex.

## Reload vs new shell

| Surface | How a change applies |
|---|---|
| Ghostty (the theme) | `cmd+shift+,` live-reload |
| starship (prompt) | next prompt render (immediate in a reloaded/new shell) |
| fish colors | **new shell** (read at startup) |
| zsh (if highlighter) | **new shell** |

## Quick reference

| Question | Command |
|---|---|
| Is every surface coordinated? | `scripts/theme_status.py` |
| What colors do they share? | `scripts/theme_swatch.py` (in Ghostty) |
| Does starship inherit? | `starship prompt --status=0 \| cat -v` (ANSI, not `38;2;…`) |
| Do fish colors inherit? | `fish -l -i -c '… fish_color …'` (names, no hex) |
| What themes can I set? | `scripts/theme_list.py [filter]` |
