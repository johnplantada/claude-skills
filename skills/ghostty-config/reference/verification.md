# Verification — the golden rule

An edit to a Ghostty config is not "done" until you've proven two things: it **parses** and it's
**actually in effect**. A change can be syntactically fine yet silently overridden (the macOS Library
file wins) or apply only to new windows. Prove it; don't assume.

## The two checks

```bash
ghostty +validate-config          # 1. does the whole loaded config parse + resolve? (exit 0)
ghostty +show-config              # 2. is the key set to what you meant? (the resolved value)
```
`scripts/ghostty_doctor.py` wraps (1) plus the macOS split-brain check; `scripts/show_effective.py
<key>` wraps (2). A change is verified when the doctor is `validate ok / in_sync yes` **and**
`show_effective.py <key>` prints your intended value.

## Live-reload, not restart

Ghostty re-reads its config on **`cmd+shift+,`** (the `reload_config` keybind) — no relaunch needed.
So the verify loop is: edit → `cmd+shift+,` → observe. If nothing changed, it's almost always one of:

1. **Not reloaded** — hit `cmd+shift+,` (or fully quit and reopen).
2. **Split-brain** — you edited `~/.config/ghostty/config` but Ghostty reads the Library file.
   `scripts/ghostty_doctor.py` prints `split_brain` — fix with the `config-file` include ([setup.md](setup.md) §4).
3. **New-window-only option** — some settings apply only to windows/tabs created *after* the reload:
   - `command` (the shell) — the current window keeps its running shell; open a new window.
   - window-creation options (initial size/position, some titlebar settings).
   Say "open a new window to see it" rather than claiming the running window changed.

## Effective vs declared

- **Declared** = the lines in your file. **Effective** = what Ghostty resolved after loading every
  file (`+show-config`). `optimize` uses the gap: a declared line whose value equals the default
  (`+show-config --default`) is redundant — dropping it leaves the *effective* config identical.
- After an optimize pass, the proof is: fewer declared lines, **byte-identical `+show-config`**, still
  `validate ok`.

## Fonts are a special case

`+validate-config` does **not** fail on a missing `font-family` — Ghostty silently falls back. So
font verification is its own step:

```bash
scripts/font_check.py             # resolved / MISSING, and nerd-font / maybe-tofu
```
"It validated" is not "the font renders." Prove the family resolves and has glyph coverage, then
eyeball a glyph-heavy prompt (a starship powerline line) in a reloaded window.

## Quick reference

| Question | Command |
|---|---|
| Does it parse? | `ghostty +validate-config` / `scripts/ghostty_doctor.py` |
| Is this key in effect? | `scripts/show_effective.py <key>` |
| Which file does Ghostty load? | `scripts/ghostty_doctor.py` (`loads` / `include` / `split_brain`) |
| Does my font resolve + have glyphs? | `scripts/font_check.py` |
| Any cruft / dead keys? | `scripts/config_audit.py` |
| How do I apply a change? | `cmd+shift+,` (reload); new window for `command` |
