---
name: Ghostty Config
description: Set up, repair, upgrade, and optimize your Ghostty terminal configuration as a declarative, version-controlled file — proven by validating and re-reading it, never a blind write. Use to SET UP a clean commented config (font + Nerd Font, theme, default shell, padding, keybinds) on macOS the robust way (real config in ~/.config, pulled in via a config-file include so it isn't silently overridden), REPAIR a config that won't load or a setting that won't take (split-brain between the Library and ~/.config files, invalid/deprecated keys, a font rendering as tofu, a wrong theme name, reload-vs-restart), UPGRADE by adopting new options after a Ghostty version bump and reconciling deprecated keys, or OPTIMIZE a working config (drop redundant defaults, remove unknown/duplicate keys, prove the font resolves with glyph coverage). Every change is validated with `ghostty +validate-config` and confirmed in effect with `ghostty +show-config`.
argument-hint: [setup|repair|upgrade|optimize]
allowed-tools: Bash(*ghostty-config/scripts/*), Bash(ghostty +*), Bash(cat *), Bash(ls *), Bash(git -C * *)
---

# Ghostty config

Manage the [Ghostty](https://ghostty.org) terminal config as a **declarative, version-controlled
file**, so your terminal is reproducible and drift is visible. The golden rule is
**verification-first**: prove a setting took with `ghostty +validate-config` (it parses) and
`ghostty +show-config` (it's actually in effect) — never trust that an edit did what you meant.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Stand up a clean, commented config (font, theme, shell, keybinds) — the robust macOS way | [reference/setup.md](reference/setup.md) |
| Fix a config that won't load / a setting that won't take (split-brain, bad key, tofu font, wrong theme) | [reference/repair.md](reference/repair.md) |
| Adopt new options after a Ghostty update; reconcile deprecated keys | [reference/upgrade.md](reference/upgrade.md) |
| Tighten a working config — drop redundant defaults, kill dup/unknown keys, prove the font | [reference/optimize.md](reference/optimize.md) |
| Prove a change took (and understand live-reload) | [reference/verification.md](reference/verification.md) |

**No workflow named?** (a bare `/ghostty-config`) — **triage first:** run `scripts/ghostty_doctor.py`,
then route:
- `split_brain …` or `validate FAIL` → **repair**.
- No config file at all → **setup**.
- `in_sync yes` → run `scripts/config_audit.py` + `scripts/font_check.py`; any `cruft`/`issues` → **optimize**, else report clean and **stop**.

## The macOS config-location trap (read this first)

On macOS Ghostty **always** reads `~/Library/Application Support/com.mitchellh.ghostty/config` and
only consults `~/.config/ghostty/config` when `XDG_CONFIG_HOME` is exported — with the **Library file
winning**. So editing `~/.config/ghostty/config` alone often does *nothing*. The robust, dotfiles-
friendly layout this skill sets up: real config in **`~/.config/ghostty/config`** (chezmoi-tracked),
pulled in by a one-line Library file:

```
# ~/Library/Application Support/com.mitchellh.ghostty/config
config-file = ~/.config/ghostty/config
```
`scripts/ghostty_doctor.py` flags the split-brain when the XDG file exists but isn't included.

## The scripts (call these, don't re-compose bash)

The mechanical commands live in [`scripts/`](scripts/README.md) as tested, read-only helpers — call
them by name. Ghostty's config is a plain file, so the **mutation is a file edit** and these scripts
are the **verification** around it (none writes a config).

| Need | Script |
|---|---|
| Validate + detect the macOS split-brain; which file loads | `scripts/ghostty_doctor.py [config]` |
| See the resolved config / confirm a change is in effect | `scripts/show_effective.py [--default] [key…]` |
| Prove every `font-family` resolves + has Nerd-Font glyphs | `scripts/font_check.py [config]` |
| Audit for dup / redundant-default / unknown keys | `scripts/config_audit.py [config]` |

## Discovery (always run first)

```bash
ghostty +version                                   # config keys/deprecations are version-specific
scripts/ghostty_doctor.py                           # valid? which file loads? split-brain?
ls -la ~/.config/ghostty/config \
  ~/Library/Application\ Support/com.mitchellh.ghostty/config 2>/dev/null   # which files exist
```
Read `~/.config/devenv/config.toml` for a `[ghostty-config]` section before prompting.

## Core principles

1. **Validate, then confirm in effect.** After any edit: `ghostty +validate-config` must pass, and
   `ghostty +show-config` must show the intended value. A change that parses can still be overridden
   by the Library file (see the trap above).
2. **One authoritative file.** Keep real settings in `~/.config/ghostty/config`; the Library file is
   a one-line `config-file` include. Two files with real content = split-brain; the doctor flags it.
3. **Fonts must resolve *and* have glyphs.** A `font-family` Ghostty can't find falls back silently;
   a face without Nerd-Font glyphs renders prompt icons as tofu. `scripts/font_check.py` proves both.
4. **Live-reload, don't restart.** Ghostty reloads config with `cmd+shift+,` (keybind
   `reload_config`) — no relaunch needed to verify. A few options (e.g. `command`) apply only to
   *new* windows/surfaces; say so rather than claiming an open window changed.
5. **Track the config.** It's a dotfile — version `~/.config/ghostty/config` via the `dotfiles` skill
   (chezmoi) so your terminal is reproducible across machines.

## Settings

Read `~/.config/devenv/config.toml` before prompting; if a `[ghostty-config]` section exists, use it
as defaults (precedence: explicit answer this session > `config.toml` > ask). Had to ask? Offer to
save the answer back. Managed by the `devenv` skill. Keys honored:
- `config` — path to the real config file (default `~/.config/ghostty/config`).
- `theme` — preferred theme name (validated against `ghostty +list-themes`).
- `font` — preferred `font-family` (validated against `ghostty +list-fonts`).

## Boundaries with the other skills

- **shell-sync** decides *which* shell is canonical; this skill wires it into Ghostty via
  `command = <shell> --login`. Change the shell in shell-sync, reflect it here.
- **dotfiles** (chezmoi) tracks `~/.config/ghostty/config`. **runtime-versions / brew-doctor** own
  the tools; this skill only configures the terminal that launches them.

## Safety

- **Back up before overwriting** any config file (timestamped copy).
- **Don't silently move the source of truth.** Migrating from the Library file to `~/.config`
  changes what Ghostty reads — confirm direction, and leave the Library file as an explicit
  `config-file` pointer so the change is visible and reversible.
- **`command` sets the default shell.** Confirm the shell path exists (`command -v fish`) before
  writing it, or Ghostty opens to an error.
