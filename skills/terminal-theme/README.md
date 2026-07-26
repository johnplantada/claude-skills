# terminal-theme — one theme across your whole terminal

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that **coordinates one visual theme**
across **Ghostty, fish, zsh, and starship** so they never clash. It defaults to the **inherit model**:
Ghostty's theme defines the 16 ANSI colors, and the shells + prompt are configured with ANSI color
*names* so they follow it — change the Ghostty theme and the **entire terminal re-themes with one edit.**

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Convert hardcoded hex in starship/fish to ANSI names so they inherit, pick the Ghostty theme as the source of truth, verify all four surfaces agree, and track the configs. |
| **repair** | Fix a surface that clashes — a prompt or shell still on hardcoded colors, or a `config.fish` line overriding the managed theme file. |
| **upgrade** | Switch the theme (one Ghostty edit in inherit mode), or adopt the "matched" model for exact brand palettes everywhere. |
| **optimize** | Audit every surface for stray hex that breaks inheritance, collapse duplicate color declarations, and prove one theme change re-themes everything. |

## Why it's different

Most terminal theming is four independent configs you keep in sync by hand — and on a real setup they
drift (a gruvbox prompt on a Doom-Peacock terminal). This skill removes the coordination problem
instead of managing it:

- **One source of truth.** ANSI color *names* are references, not fixed colors — they resolve to
  whatever Ghostty's theme paints. So starship/fish/zsh render with the terminal, and switching the
  Ghostty `theme` re-themes all of them. No per-theme mappings, drift is impossible.
- **Verification-first.** `theme_status.py` audits each surface for hardcoded hex (the thing that
  breaks inheritance); the real proof is switching the Ghostty theme and watching the prompt + shell
  follow.
- **Honest about the trade-off.** Inherit uses the terminal's 16 slots; if you want a brand's *exact*
  hex everywhere, the **matched** model is documented too.

## Requirements

- **Claude Code**, **Ghostty**, and optionally **starship** / **fish**. Pairs with the
  `ghostty-config` and `shell-sync` skills.

## Install

Part of the [devenv](../../) plugin / [claude-skills](../../) gallery — installed with the plugin, or
symlink just this skill:

```bash
ln -s ~/codebase/claude-skills/skills/terminal-theme ~/.claude/skills/terminal-theme
```

## Usage

```
/terminal-theme setup       # coordinate all four surfaces (convert hex → ANSI, set the knob)
/terminal-theme repair      # a surface clashes with the rest
/terminal-theme upgrade     # switch the theme (one edit), or go "matched"
/terminal-theme optimize    # audit for stray hex, prove inheritance
```

Or describe it — "make my prompt match my terminal theme", "coordinate my terminal colors", "why is
my prompt a different color scheme than ghostty" — and it routes to the right workflow.

```
terminal-theme/
├── SKILL.md                  router + the inherit/matched models + where each surface's theme lives
├── scripts/                  read-only; the mutation is editing starship.toml / fish conf.d
│   ├── theme_status.py       audit coordination across all four surfaces (hardcoded hex = won't inherit)
│   ├── theme_swatch.py       render the terminal's ANSI palette everything shares
│   ├── theme_list.py         list Ghostty themes (the one knob); highlight cross-tool families
│   └── README.md
├── reference/
│   ├── setup.md              convert hex → ANSI across starship/fish; set the Ghostty knob; track
│   ├── repair.md             a surface clashes: find the hex; the config.fish-overrides-conf.d gotcha
│   ├── upgrade.md            switch theme (one edit) or adopt the matched model
│   ├── optimize.md           kill stray hex, collapse duplicates, prove one-knob re-theming
│   └── verification.md       audit + swatches + the switch-and-watch proof
└── README.md
```

## License

[MIT](../../LICENSE).
