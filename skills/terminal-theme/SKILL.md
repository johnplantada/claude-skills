---
name: Terminal Theme
description: Coordinate one visual theme across your whole terminal — Ghostty, fish, zsh, and starship — so they never clash. Uses the "inherit" model by default — Ghostty's theme defines the 16 ANSI colors, and starship/fish/zsh are configured with ANSI color NAMES so they follow it automatically — change the Ghostty theme and the entire terminal re-themes with one edit. Use to SET UP coordinated theming (convert hardcoded hex in starship/fish to ANSI, pick the Ghostty theme as the source of truth), REPAIR a surface that clashes (a prompt or shell still on old hardcoded colors), UPGRADE by switching the theme (one Ghostty edit) or adopting the "matched" model for exact brand palettes, or OPTIMIZE by auditing every surface for hardcoded hex that breaks inheritance. Verified by auditing each surface and rendering ANSI swatches.
argument-hint: [setup|repair|upgrade|optimize]
allowed-tools: Bash(*terminal-theme/scripts/*), Bash(ghostty +*), Bash(fish -l -i -c *), Bash(starship *), Bash(grep *), Bash(cat *), Bash(ls *)
---

# Terminal theme

Keep **Ghostty, fish, zsh, and starship** visually consistent — one theme, no clashes. The default
approach is the **inherit model**: Ghostty's theme defines the 16 ANSI colors (slots 0–15 + fg/bg),
and the shells and prompt are configured with **ANSI color names** so they render with *whatever*
Ghostty theme is active. **Change the Ghostty theme → the whole terminal re-themes, one edit.**

The golden rule is **verification-first**: prove coordination by auditing every surface for hardcoded
hex (which won't follow the terminal) and rendering the ANSI palette everything shares.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Make the four surfaces share one theme (convert hardcoded colors → ANSI, set the Ghostty knob) | [reference/setup.md](reference/setup.md) |
| Fix a surface that clashes — a prompt/shell still on old hardcoded colors | [reference/repair.md](reference/repair.md) |
| Switch the theme (one Ghostty edit), or move to the "matched" model for exact brand palettes | [reference/upgrade.md](reference/upgrade.md) |
| Audit every surface for hex that breaks inheritance, and tighten it | [reference/optimize.md](reference/optimize.md) |
| Prove the surfaces agree (audit + swatches) | [reference/verification.md](reference/verification.md) |

**No workflow named?** (a bare `/terminal-theme`) — **triage first:** run `scripts/theme_status.py`:
- any `hardcoded (…)` surface → **repair** (or **setup** if none are converted yet).
- `coordinated yes` → report it and **stop** (offer `upgrade` to switch theme).

## The two models

- **Inherit (default, recommended).** starship/fish/zsh use ANSI color **names** → they resolve to
  Ghostty's palette. One source of truth (the Ghostty `theme`), impossible to drift, no per-theme
  data. Trade-off: colors are the terminal's 16 slots, not a specific brand's exact hex.
- **Matched (advanced).** Each surface gets a theme's **exact hex** (a native fish/starship theme +
  Ghostty theme of the same name). Brand-accurate, but every switch re-applies all surfaces and each
  theme needs its mapping. Covered in [upgrade.md](reference/upgrade.md).

## The scripts (call these, don't re-derive them)

Read-only helpers in [`scripts/`](scripts/README.md) — the *mutation* is editing config files
(starship.toml, fish `conf.d`), these are the **audit + verification** around it.

| Need | Script |
|---|---|
| Audit coordination across all four surfaces (hardcoded hex = won't inherit) | `scripts/theme_status.py` |
| Render the terminal's ANSI palette as swatches (what everything inherits) | `scripts/theme_swatch.py` |
| List Ghostty themes (the one knob); highlight cross-tool families | `scripts/theme_list.py [filter]` |

## Where each surface's theme lives

| Surface | Themed by | Inherit = use… |
|---|---|---|
| **Ghostty** | `theme = <name>` in `~/.config/ghostty/config` — **the knob** (defines ANSI 0–15 + fg/bg) | — (owns `ghostty-config`) |
| **starship** | palette in `~/.config/starship.toml` | ANSI names in `[palettes.*]` (no `#hex`) |
| **fish** | `fish_color_*` — fish 4.3+ stores them in `conf.d/fish_frozen_theme.fish` (ANSI names) | already inherits; per-color overrides go in `config.fish` (loads last, wins) |
| **zsh** | syntax-highlighter styles (`ZSH_HIGHLIGHT_STYLES`) *if installed*; else raw ANSI | ANSI slot numbers; no highlighter → already inherits |

## Core principles

1. **Ghostty is the source of truth.** In inherit mode, the only theme decision is the Ghostty
   `theme`. Everything else is configured *once* to follow it.
2. **Hardcoded hex is the enemy of coordination.** A `#rrggbb` in starship/fish/zsh pins that element
   regardless of the terminal theme → clash. `scripts/theme_status.py` flags it; convert to an ANSI name.
3. **Verify by audit + eyeball.** `theme_status.py` must show every surface `inherits`; then render
   `theme_swatch.py` and a glyph-heavy prompt in Ghostty to confirm they look like one theme.
4. **Live-reload.** Ghostty reloads with `cmd+shift+,`; open a **new shell** for fish/zsh color
   changes (colors are read at shell start). Say so rather than claiming an open shell changed.
5. **Track it.** `starship.toml`, `config.fish` (the fish color overrides), and fish's
   `conf.d/fish_frozen_theme.fish` are dotfiles — version them via the `dotfiles` skill so the
   coordinated theme is reproducible.

## Settings

Read `~/.config/devenv/config.toml`; if a `[terminal-theme]` section exists, use it as defaults
(precedence: explicit > config > ask). Managed by the `devenv` skill. Keys honored:
- `model` — `inherit` (default) or `matched`.
- `source` — the surface that is the source of truth (default `ghostty`).
- `theme` — the current theme name (the Ghostty `theme`, e.g. `Catppuccin Mocha`).

## Boundaries with the other skills

- **ghostty-config** owns the Ghostty `theme` line (the knob); this skill sets *which* theme and makes
  the others follow. **shell-sync** owns fish/zsh sync + the starship prompt init; this skill owns the
  *colors* in starship.toml and fish's theme (`config.fish` overrides). Change a shell's prompt structure in
  shell-sync; change its palette here.

## Safety

- **Back up** starship.toml / fish config before rewriting palettes (timestamped copy).
- **Converting to ANSI changes the exact colors** (brand hex → terminal slots). Confirm the user wants
  inherit over matched before rewriting a curated palette.
- fish loads `config.fish` **after** `conf.d/*` (incl. `fish_frozen_theme.fish`), so per-color
  overrides belong in `config.fish` (fish's own guidance) — that's where a readable
  `fish_color_autosuggestion` gray goes. A stray hardcoded color there still wins, so audit it.
- **Autosuggestion is the one deliberate non-inherit:** the 16-ANSI palette has no readable mid-gray,
  so a fixed dim gray (`8a8a8a`) is expected there — `theme_status.py` exempts it.
