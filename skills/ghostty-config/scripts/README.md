# ghostty-config scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the same
`ghostty +validate-config` / `+show-config` / parse-and-compare bash each time. Fewer tokens, no
re-derivation, no footguns (e.g. a failed validation tripping `set -e` before it can report the
error, or an un-included `~/.config` file silently ignored on macOS).

Run them by absolute path from the skill directory. **All four are read-only** — Ghostty's config
is a plain file, so the *mutation* is a file edit (via your editor / the Edit tool) and these scripts
are the **verification** around it. None writes a config.

| Script | Purpose | Read-only? |
|---|---|---|
| `ghostty_doctor.py [config]` | Health check: `+validate-config` (errors with messages) **and** split-brain detection — on macOS the Application Support config is always read and overrides `~/.config/ghostty/config`, so an un-included XDG file is silently ignored. Reports which file actually loads. Exit 0 = valid + no split-brain. | yes |
| `show_effective.py [--default] [key…]` | Ghostty's resolved config via `+show-config` — the keys you've set (or `--default` for the full surface), optionally filtered to `key…` substrings. The "is my change actually in effect?" check. | yes |
| `font_check.py [config]` | Every declared `font-family*` → resolved against `+list-fonts` (`MISSING` = silent fallback) and flagged `nerd-font` / `maybe-tofu` (a face lacking glyph coverage → empty boxes where prompt icons go). | yes |
| `config_audit.py [config]` | Tighten a config: `validate` (deprecated/unknown keys), `dup` (a *single-value* key set twice — Ghostty's repeatable keys like `keybind`/`palette`/`font-family` are excluded), `redundant` (`key = value` equal to Ghostty's default — safe to drop). Exit 0 = clean. | yes |

All four import **`_ghostty_common.py`** (leading underscore = not a workflow entrypoint) for the
macOS config paths (`LIB`/`XDG`), `has_content`, and the thin `validate_config` / `show_config` /
`list_fonts` subprocess wrappers — the subprocess/IO lives there so each script's parsing and
analysis stays as pure, directly-testable functions. One place to edit when Ghostty's path or CLI changes.

## Worked example — the whole verify loop

```
ghostty_doctor.py                 # valid? which file loads? split-brain? -> expect in_sync yes
show_effective.py font command    # confirm font-family / command resolved to what you meant
font_check.py                     # every font resolves; the prompt font advertises nerd-font glyphs
config_audit.py                   # no dup / redundant / unknown keys
```
After editing the config, re-run `ghostty_doctor.py` — Ghostty **live-reloads** with `cmd+shift+,`,
so no restart is needed to see the change. `split_brain /…/.config/ghostty/config` means "you edited
`~/.config` but Ghostty is reading the Library file" — pull it in with a `config-file =` include (see
[../reference/setup.md](../reference/setup.md)) or the edit has no effect.

## The macOS config-loading gotcha (why the split-brain check exists)

Ghostty on macOS reads `~/Library/Application Support/com.mitchellh.ghostty/config` **and** only
consults `$XDG_CONFIG_HOME/ghostty/config` when `XDG_CONFIG_HOME` is exported — with the Library file
loaded **last, so it wins**. So the robust, dotfiles-friendly layout is: real config in
`~/.config/ghostty/config` (chezmoi-tracked), and a one-line Library file that pulls it in:

```
# ~/Library/Application Support/com.mitchellh.ghostty/config
config-file = ~/.config/ghostty/config
```
Verified: with that include, a `font-size` set only in `~/.config/ghostty/config` takes effect and
`+validate-config` stays clean.

## Conventions for adding scripts

- `#!/usr/bin/env python3`, `from __future__ import annotations`, Python 3.9+, stdlib only. Executable
  (`chmod +x`) with a `def main(argv=None) -> int` guarded by `if __name__ == "__main__": sys.exit(main())`.
- **Separate pure logic from IO.** Parsing / analysis / formatting go in plain module functions the tests
  call directly (no mocking); the `ghostty` subprocess calls stay in `_ghostty_common.py`.
- **Never abort on a non-zero `ghostty` exit when there's still usable output** — e.g. `show_config` ignores
  the return code so `+show-config` failing doesn't lose the config it emitted, and validation errors are
  reported rather than raised.
- Print greppable `label<TAB>value` lines; keep output order stable.
- Read-only only. The mutation is a file edit; these scripts verify it.
