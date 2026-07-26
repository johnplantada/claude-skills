# Repair workflow — a surface clashes with the rest

One surface doesn't match: the prompt is a different palette than the terminal, fish highlighting
looks off, or switching the Ghostty theme changes everything *except* one thing. Cause is almost
always **hardcoded hex** that ignores the terminal, or a **later config overriding** the managed one.

## 1. Find the offender

```bash
scripts/theme_status.py          # which surface is `hardcoded (<n> hex)`?
```

| Surface flagged | Root cause | Fix |
|---|---|---|
| `starship hardcoded (n hex)` | `#rrggbb` in `[palettes.*]` or inline `fg:#…`/`bg:#…` | §2 |
| `fish hardcoded (n hex)` | a `fish_color_*` set to hex, often in `config.fish` | §3 |
| `zsh hardcoded (n hex …)` | `ZSH_HIGHLIGHT_STYLES[...]=fg=#…` | §4 |
| everything except one element follows the theme | a single inline hex in that element | §2/§3 |

## 2. starship

```bash
grep -nE '#[0-9a-fA-F]{6}' ~/.config/starship.toml
```
Convert each hit to an ANSI name (`black red green yellow blue purple cyan white` + `bright-*`, or a
slot number). Palette entries → names; inline `fg:#83a598` → `fg:color_fg0` (a palette entry) or a
name. Re-check:
```bash
grep -nE '#[0-9a-fA-F]{6}' ~/.config/starship.toml || echo "clean"
starship prompt --status=0 | cat -v | head -2      # ANSI codes (\033[3Xm), not truecolor 38;2;…
```

## 3. fish

fish colors have several sources that load in order — **conf.d/*** (incl. fish 4.3's
`fish_frozen_theme.fish`), then **`config.fish`** (loads last, wins). Resolve the actual winner in a
real shell:
```bash
fish -l -i -c 'for v in (set -n | grep fish_color); echo $v" = "$$v; end' | grep -iE '[0-9a-fA-F]{6}|\b[0-9a-fA-F]{3}\b'
```
- **Base theme** (`conf.d/fish_frozen_theme.fish`) — fish 4.3+ migrated colors here as ANSI names, so
  it usually inherits. A hex value in it → convert to an ANSI name.
- **A stray hex in `config.fish`** (e.g. `set -g fish_color_… 555`) overrides the theme — that's the
  usual culprit. Remove it, *unless* it's the intentional `fish_color_autosuggestion` gray (§ below).
- **Suggestion text too faded** (a common report): `fish_color_autosuggestion` is likely `brblack`
  (ANSI 8), which blends into dark themes. Override it in `config.fish` (loads last) with a readable
  fixed gray: `set -g fish_color_autosuggestion 8a8a8a`. This is the one expected non-inherit.
Re-check with the same `fish -l -i -c` dump.

## 4. zsh (only if a highlighter is installed)

```bash
grep -nE 'ZSH_HIGHLIGHT_STYLES|fg=#|bg=#' ~/.zshrc
```
Replace `fg=#458588` with an ANSI slot: `fg=blue` or `fg=4`. Without a highlighter, zsh already
inherits — nothing to repair.

## 5. Not hex, but still clashes?

- **Didn't reload.** Ghostty: `cmd+shift+,`. fish/zsh read colors at **startup** — open a new shell.
- **Two Ghostty configs (split-brain).** The theme you edited isn't the one loaded — run the
  `ghostty-config` skill's `ghostty_doctor.py`.
- **Truecolor off.** If ANSI names look wrong, confirm the terminal advertises a palette
  (`ghostty +show-config | grep -E '^palette'`).

## Verify

```bash
scripts/theme_status.py          # coordinated yes
scripts/theme_swatch.py          # (in Ghostty) all surfaces now match these 16 colors
```

## Report

The clashing surface, the hardcoded value(s) removed (and where they hid — `config.fish` overriding
`conf.d` is worth calling out), and the `coordinated yes` proof.
