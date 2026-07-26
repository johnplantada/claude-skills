# Repair workflow — the config won't load, or a setting won't take

Something is actually wrong: an edit has no effect, Ghostty falls back to defaults, the font is tofu,
or a theme/keybind errors. Diagnose with the doctor, fix the one cause, and re-verify. (Tightening a
config that already works → [optimize.md](optimize.md).)

## 1. Triage

```bash
scripts/ghostty_doctor.py          # validate + which file loads + split-brain
```
Route by what it prints:

| Symptom | Likely cause | Go to |
|---|---|---|
| `split_brain /…/.config/ghostty/config` | You edit `~/.config` but Ghostty reads the Library file | §2 |
| `validate FAIL` + `error … unknown field` | Typo or a **deprecated/renamed** key | §3 |
| `validate FAIL` + `theme … not found` | Theme name doesn't match `+list-themes` | §4 |
| Prompt icons are empty boxes (tofu) | `font-family` missing or lacks Nerd-Font glyphs | §5 |
| Edited, but the open window looks unchanged | Not reloaded, or the key applies to new windows only | §6 |

## 2. Split-brain — `~/.config` edits ignored

On macOS the Library file wins and `~/.config/ghostty/config` isn't read unless it's included. Make
the Library file a one-line include (back it up first):

```bash
LIB=~/Library/Application\ Support/com.mitchellh.ghostty/config
cp "$LIB" "$LIB.bak.$(date +%Y%m%d-%H%M%S)"
printf '# Managed by ghostty-config: real config in ~/.config/ghostty/config\nconfig-file = ~/.config/ghostty/config\n' > "$LIB"
scripts/ghostty_doctor.py          # expect: include <xdg>, in_sync yes
```
If instead you *want* the Library file to be the source, remove `~/.config/ghostty/config` (or fold
its lines into the Library file) so only one has real content.

## 3. Unknown / deprecated key

```bash
scripts/config_audit.py ~/.config/ghostty/config     # lists each `error  <key>: unknown field`
```
Confirm the current name/spelling against the docs for your installed version
(`ghostty +show-config --default --docs | grep -iA3 '<topic>'`). Ghostty renames options across
releases — a key valid last year may be gone. Fix or remove the line, then re-validate. Bump-related
reconciliation across a version change is [upgrade.md](upgrade.md).

## 4. Wrong theme name

```bash
ghostty +list-themes | grep -i <partial>   # exact names, case-sensitive; light:X,dark:Y for both modes
```
Set the exact name, then `scripts/ghostty_doctor.py` should be `validate ok`.

## 5. Tofu font (icons render as boxes)

```bash
scripts/font_check.py                 # MISSING = not installed; maybe-tofu = resolves but no glyphs
ghostty +list-fonts | grep -i <name>  # confirm the exact family name Ghostty sees
```
- `MISSING` → the family isn't installed (or the name is wrong). Install a Nerd Font
  (`brew install --cask font-<name>-nerd-font`) and use the exact name from `+list-fonts`.
- `maybe-tofu` → the face resolves but isn't a Nerd Font, so prompt/powerline glyphs have no
  coverage. Switch `font-family` to the **Nerd Font** build (the name contains `Nerd Font`).
Re-run `scripts/font_check.py` → every line `resolved` / `nerd-font`.

## 6. Reloaded? New-window-only?

Ghostty **live-reloads** with `cmd+shift+,` (keybind `reload_config`) — an edit isn't visible until
you reload (or open a new window). Some options — notably `command` (the shell), and window-creation
settings — apply only to **newly created** windows/tabs; the current one keeps its old value. Open a
new window to confirm, and say so rather than claiming the running window changed. See
[verification.md](verification.md).

## Verify

```bash
scripts/ghostty_doctor.py            # validate ok, in_sync yes
scripts/show_effective.py <key>      # the fixed key now shows the intended value
```

## Report

The one root cause, the fix applied (with the backup path), and the doctor/show-config evidence that
it's resolved.
