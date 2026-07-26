# terminal-theme scripts — the stable toolbox

Tested, read-only helpers so a session **calls a script** instead of re-deriving the "is every
surface using ANSI or is something hardcoded?" checks each time. Ghostty's config, `starship.toml`,
and fish `conf.d` are the mutable source; these scripts are the **audit + verification** around edits.

| Script | Purpose | Read-only? |
|---|---|---|
| `theme_status.py` | Audit coordination across Ghostty (the knob), starship, fish, zsh. Each surface is `inherits` (ANSI names/slots → follows the terminal) or `hardcoded (<n> hex)` (pinned, will clash). Exit 0 = `coordinated yes`. | yes |
| `theme_swatch.py` | Print the terminal's ANSI palette (slots 0–15, fg + bg) as swatches. Render it **inside Ghostty** to eyeball the active theme's real colors — the exact colors starship/fish/zsh inherit. | yes |
| `theme_list.py [filter]` | List Ghostty themes (the one knob in inherit mode). No filter → highlights families with the broadest cross-tool ports (Catppuccin, Gruvbox, Nord…). | yes |

## Worked example — the coordination loop

```
theme_status.py                 # expect every surface "inherits" + "coordinated yes"
theme_swatch.py                 # (in Ghostty) the 16 colors everything shares
theme_list.py gruvbox           # options for the knob, if switching
```
`starship  hardcoded (10 hex)` means the prompt palette is pinned to specific hex and won't follow the
terminal — convert those `[palettes.*]` entries to ANSI names (see `../reference/repair.md`). After a
change, open a **new shell** (fish/zsh read colors at startup) and reload Ghostty (`cmd+shift+,`).

## Why "inherit" (ANSI names) coordinates for free

An ANSI color name (`red`, `blue`, `bright-black`, or slot `0`–`15`) is not a fixed color — it's a
*reference* to whatever the terminal's active theme paints that slot. So if starship's palette,
fish's `fish_color_*`, and zsh's highlight styles all use ANSI names, they render with **Ghostty's**
theme, and switching the Ghostty `theme` re-themes all of them. A `#rrggbb` breaks that — it's a fixed
color the terminal theme can't touch. The scripts hunt for exactly those `#hex` escapes.

## Conventions for adding scripts

- Python 3.9+, **stdlib only**, `#!/usr/bin/env python3`, `from __future__ import annotations`, executable.
- Keep **pure logic** (parsing / hex-counting / formatting) in plain module functions and isolate every
  subprocess/file call in `_theme_common.py` — that split is what the `tests/terminal_theme` suite drives
  directly (no mocking, no fish/zsh/ghostty needed).
- Detect fish colors by resolving them in a real login shell (`fish -l -i -c`), not by reading files —
  universal vars, `conf.d`, and `config.fish` all contribute and only the shell resolves the winner.
  Likewise resolve `ZSH_HIGHLIGHT_STYLES` from a live `zsh -i` (sourced fragments count).
- Count hardcoded hex by **occurrence** on every surface (starship/fish/zsh alike); exempt
  `fish_color_autosuggestion` (its fixed dim gray is intentional).
- Print greppable `surface<TAB>state` lines; keep order stable. Read-only only.
