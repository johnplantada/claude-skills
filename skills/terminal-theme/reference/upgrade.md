# Upgrade workflow — switch the theme, or move to the matched model

Two jobs: **switch to a different theme** (trivial in inherit mode), and **adopt the matched model**
if you want exact brand colors instead of terminal inheritance.

## A. Switch the theme (inherit model — one edit)

Because starship/fish/zsh follow the terminal, the *only* change is the Ghostty `theme`:

```bash
scripts/theme_list.py <name>          # find the exact Ghostty theme name
```
Set it via the **ghostty-config** skill (`theme = <name>` in `~/.config/ghostty/config`), reload
Ghostty (`cmd+shift+,`), and open a new shell. Then confirm nothing regressed:
```bash
scripts/theme_status.py               # still coordinated yes (surfaces unchanged — they inherit)
scripts/theme_swatch.py               # the new palette; prompt + fish now wear it
```
Update `[terminal-theme].theme` in `~/.config/devenv/config.toml`. That's it — no starship/fish edits.

## B. Adopt the matched model (exact brand hex everywhere)

When you want *true* Catppuccin Mocha (not "the terminal's slots") across all surfaces. More work and
more moving parts, but brand-accurate. Per theme, apply the native port to each surface:

1. **Ghostty** — `theme = Catppuccin Mocha` (same as inherit).
2. **starship** — install the theme's palette hex. Some themes ship a starship preset
   (`starship preset tokyo-night -o ~/.config/starship.toml`); others (Catppuccin, Nord) publish a
   `[palettes.<name>]` hex block to paste and point `palette =` at.
3. **fish** — apply the native fish theme: `fish_config theme choose "Catppuccin Mocha"` then
   `fish_config theme save` (writes universal vars), or drop the `.theme` file in
   `~/.config/fish/themes/`. Note: this **reintroduces hex**, so `theme_status.py` will report
   `hardcoded` — that's expected in matched mode (set `[terminal-theme].model = matched`).
4. **zsh** — if a highlighter is installed, apply that theme's `ZSH_HIGHLIGHT_STYLES` hex.

Switching themes in matched mode means re-applying all four. Keep each theme's mapping in the repo so
it's repeatable. If this becomes tedious, that's the argument for the inherit model.

## C. Adopting a tool's new theme version

After a Ghostty update, a renamed/added theme may be available (`scripts/theme_list.py`). fish/starship
theme ports also get updated upstream — re-pull via the `dotfiles` skill if you track a native theme.

## Verify

```bash
scripts/theme_status.py      # inherit: coordinated yes  |  matched: expected `hardcoded` per surface
scripts/theme_swatch.py      # (in Ghostty) the active palette
```

## Report

The new theme, which model is in effect, the files touched (inherit: just Ghostty; matched: all four),
and the verification evidence. Offer to re-track changed configs via `dotfiles`.
