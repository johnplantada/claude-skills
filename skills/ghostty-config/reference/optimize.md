# Optimize workflow — tighten a working config, prove it

The config works and nothing's broken — now make it **lean and provably correct**: drop lines that
just restate Ghostty's defaults, remove duplicate/unknown keys, and confirm every font resolves with
glyph coverage. Review and report; change nothing without confirmation. (Something actually *wrong* —
an edit ignored, a tofu font, a bad key → [repair.md](repair.md).)

> `scripts/config_audit.py` finds the cruft; `scripts/font_check.py` proves the fonts;
> `scripts/ghostty_doctor.py` proves it still loads clean. All read-only.

## 1. Audit for cruft

```bash
scripts/config_audit.py ~/.config/ghostty/config
```
- **`redundant  key = value`** — the value equals Ghostty's built-in default (`+show-config --default`).
  Removing it changes nothing and shrinks the config to *just your intent*. Drop it (with the user's ok).
- **`dup  key  N times`** — the key is set more than once; only the last wins, the earlier ones are
  dead lines. Collapse to one.
- **`error  key: unknown field`** — a typo or a key deprecated by your Ghostty version → this is
  really [repair.md](repair.md)/[upgrade.md](upgrade.md), but notice it here.

## 2. Prove the fonts

```bash
scripts/font_check.py
```
Tight setup: every `font-family*` line `resolved`, and the primary face `nerd-font` (so prompt icons
have glyphs). A `maybe-tofu` on your prompt font is worth switching to the Nerd-Font build even if it
"looks fine" — some glyphs will be missing. Ghostty auto-derives `-bold`/`-italic` from `font-family`,
so you usually only need the one line unless you want a different face per style.

## 3. Confirm the layout is single-source

```bash
scripts/ghostty_doctor.py          # expect: loads <lib>, include <xdg>, in_sync yes
```
`split_brain` here means two files carry real content — consolidate to `~/.config/ghostty/config` +
a one-line Library include (that's [repair.md](repair.md) §2). One authoritative file is the optimized
state.

## 4. Apply & re-verify

Make the edits (remove redundant/dup lines), then prove nothing regressed:
```bash
scripts/ghostty_doctor.py          # validate ok, in_sync yes
scripts/config_audit.py ~/.config/ghostty/config   # expect: clean
scripts/show_effective.py          # same effective values, fewer declared lines
```
The effective config (`+show-config`) should be unchanged — you removed lines that equalled the
default, so behavior is identical while the file is leaner. Live-reload (`cmd+shift+,`) to confirm.

## Report

The redundant/dup/unknown lines found (with the responsible line), the font proof, confirmation the
config is single-source, and the before/after: fewer declared keys, identical effective config, still
`validate ok`.
