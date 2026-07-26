# Optimize workflow — tighten coordination, kill stray hex

Everything works — now make the theming **lean and provably coordinated**: no hardcoded hex hiding in
a config, no duplicate/overriding color declarations, and inheritance proven. Review and report;
change nothing without confirmation. (An actual clash → [repair.md](repair.md).)

## 1. Audit every surface

```bash
scripts/theme_status.py
```
The optimized state (inherit model) is **every surface `inherits` + `coordinated yes`**. Any
`hardcoded (<n> hex)` is the work.

## 2. Hunt stray hex

```bash
grep -nE '#[0-9a-fA-F]{6}' ~/.config/starship.toml
fish -l -i -c 'for v in (set -n | grep fish_color); echo -n "$v="; echo $$v; end' | grep -iE '[0-9a-fA-F]{6}|\b[0-9a-fA-F]{3}\b'
grep -nE 'fg=#|bg=#' ~/.zshrc 2>/dev/null
```
Convert each to an ANSI name/slot ([repair.md](repair.md) has the per-surface how-to). Even one stray
hex means "switch the Ghostty theme" won't fully re-theme — that element stays put.

## 3. De-duplicate declarations

- **fish:** the base theme is `conf.d/fish_frozen_theme.fish` (ANSI names); `config.fish` holds
  overrides (loads last, wins). Keep only intended overrides in `config.fish` (the readable
  `fish_color_autosuggestion` gray) — drop any stray leftover color lines there.
- **fish universal vars:** a past `fish_config theme` left universal `fish_color_*` in `fish_variables`
  (gitignored). The managed `set -g` shadows them, but they're dead weight — `set -eU` to clear, or
  leave them (harmless, just untracked).
- **starship:** an unused `[palettes.*]` block that `palette =` doesn't select — drop it.

## 4. Prove inheritance

```bash
scripts/theme_status.py          # coordinated yes
scripts/theme_swatch.py          # (in Ghostty) the 16 shared colors
```
The real proof: **temporarily** switch the Ghostty theme, reload (`cmd+shift+,`), open a new shell —
the prompt and fish should visibly change with it. Switch back. If something didn't move, it still has
hex (back to §2).

## Report

Any stray hex found (with file:line), duplicate/overriding color declarations collapsed, and the proof
that one Ghostty theme change re-themes every surface — the definition of coordinated.
