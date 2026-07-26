# ghostty-config — make your Ghostty terminal reproducible

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that **sets up, repairs, upgrades,
and optimizes** your [Ghostty](https://ghostty.org) terminal configuration as a **declarative,
version-controlled file**: a clean commented config (font + Nerd Font, theme, default shell, padding,
keybinds) you can reproduce on any machine, fix when it won't load, and audit for cruft. Every change
is proven with `ghostty +validate-config` and `ghostty +show-config` — an edit is never trusted blindly.

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Stand up a clean, commented config the robust macOS way — real config in `~/.config/ghostty/config`, pulled in via a `config-file` include so the Library file can't silently override it. Font (with Nerd-Font glyphs), theme, default shell, padding, keybinds. |
| **repair** | Fix a config that won't load or a setting that won't take — split-brain between the Library and `~/.config` files, invalid/deprecated keys, a font rendering as tofu, a wrong theme name, reload-vs-restart confusion. |
| **upgrade** | Adopt new options after a Ghostty version bump, reconcile deprecated keys, refresh theme/font, and re-validate. |
| **optimize** | Tighten a working config — drop `key = value` lines that equal Ghostty's default, remove duplicate/unknown keys, and prove every font resolves with glyph coverage. |

## Why it's different

Most "Ghostty dotfile" gists are a config you paste once and hope for — and on macOS half of them
silently don't apply because Ghostty reads the *Library* path, not `~/.config`. This skill treats the
terminal config like code:

- **Verification-first.** After every edit it validates (`+validate-config`) and confirms the value
  is actually in effect (`+show-config`). Ghostty live-reloads with `cmd+shift+,` — no restart to prove it.
- **Knows the macOS trap.** On macOS the Application Support config always wins over `~/.config`;
  the skill sets up a `config-file` include so your dotfiles-tracked config is the real source, and
  `ghostty_doctor.py` flags the split-brain when it isn't.
- **Fonts that render.** `font_check.py` proves each `font-family` resolves *and* advertises
  Nerd-Font glyphs, so prompt icons don't become empty boxes.
- **Reproducible.** The config is a dotfile — track `~/.config/ghostty/config` via the `dotfiles`
  skill (chezmoi), and `devenv` wires it into bootstrap + the health sweep.

## Requirements

- **Claude Code**, **Ghostty** installed (`ghostty +version`), on **macOS** (the config-location
  handling is macOS-specific).

## Install

Part of the [devenv](../../) plugin / [claude-skills](../../) gallery — installed with the plugin, or
symlink just this skill:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/skills/ghostty-config ~/.claude/skills/ghostty-config
```

## Usage

```
/ghostty-config setup       # stand up a clean config (macOS-robust config-file include)
/ghostty-config repair      # config won't load / setting won't take
/ghostty-config upgrade     # adopt new options after a Ghostty update
/ghostty-config optimize    # drop redundant defaults, kill dup/unknown keys, prove the font
```

Or describe it — "set up my Ghostty config", "my terminal font shows boxes", "why isn't my
~/.config/ghostty change working", "clean up my ghostty config" — and it routes to the right workflow.

```
ghostty-config/
├── SKILL.md                  # router + discovery + verification-first principles + the macOS trap
├── scripts/                  # the stable toolbox — read-only; the mutation is a file edit
│   ├── ghostty_doctor.py     # +validate-config + split-brain detection; which file loads
│   ├── show_effective.py     # +show-config: resolved config / confirm a change is in effect
│   ├── font_check.py         # every font-family resolves + has Nerd-Font glyphs (no tofu)
│   ├── config_audit.py       # dup / redundant-default / unknown-key audit
│   └── README.md             # toolbox table + worked example + the macOS config-loading gotcha
├── reference/
│   ├── setup.md              # clean config via ~/.config + Library config-file include; track in dotfiles
│   ├── repair.md             # split-brain, invalid/deprecated key, tofu font, wrong theme, reload-vs-restart
│   ├── upgrade.md            # adopt new options + reconcile deprecations after a version bump
│   ├── optimize.md           # drop redundant defaults, dedupe, prove font glyph coverage
│   └── verification.md       # validate + show-config + live-reload — the golden rule
└── README.md                 # (LICENSE lives at the gallery root)
```

## License

[MIT](../../LICENSE).
