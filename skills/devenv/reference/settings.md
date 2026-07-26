# Settings workflow — the shared config the skills read

One file, `~/.config/devenv/config.toml` (XDG-aware), with a `[section]` per skill. Each skill
reads **its own section** for defaults and skips the matching prompts; missing keys → ask + offer
to save. This workflow views, edits, and validates it.

## Schema (authoritative)

```toml
# ~/.config/devenv/config.toml — settings for the claude-skills gallery.

[shell-sync]
canonical = "zsh"          # source-of-truth shell (login shell is a good default)
mirror    = "fish"         # regenerated to match canonical
sync      = ["path", "env", "aliases"]   # add "functions" for best-effort function mirroring

[brew-doctor]
pinned          = ["neovim"]          # fragile formulae kept pinned (never auto-bumped)
brewfile        = "~/Brewfile"        # declarative package list
autoupdate_mode = "update-only"       # expected auto-updater mode; warn if it becomes "upgrade"

[dotfiles]
manager = "chezmoi"
repo    = "dotfiles"                   # remote repo name (keep it PRIVATE)
ignore  = ["*.bak", ".config/fish/fish_variables", ".config/fish/conf.d/00-shell-sync.fish"]

[nvim-config]
plugin_manager = "lazy"                # most nvim state is discovered; this is the main knob

[runtime-versions]
manager = "mise"                       # version manager to standardize on
tools   = { node = "lts", python = "3.13" }   # global runtime versions

[macos-defaults]
script = "~/.config/devenv/macos.sh"   # declarative `defaults write` script

[git-setup]
signing    = "ssh"                      # commit signing: "ssh" | "gpg" | "none"
pager      = "delta"                    # diff pager: "delta" | "less"
identities = { "~/work/" = "you@work.example" }   # dir -> email (conditional includes)

[ssh-config]
key_type = "ed25519"                   # preferred algorithm for new keys
```
Unknown sections/keys are ignored by skills — safe to extend as the gallery grows.

## View

```bash
cat ~/.config/devenv/config.toml 2>/dev/null || echo "no settings yet — skills will ask and offer to save"
```

## Edit / create

Create the dir + file if absent, then edit the relevant `[section]`. Keep values consistent with
reality (the canonical shell must exist, pinned formulae must be installed). After editing, always
**validate** (below), and offer to **track it** via the `dotfiles` skill:
`chezmoi add ~/.config/devenv/config.toml`.

## Validate

```bash
# 1. TOML parses
python3 -c 'import tomllib,sys; tomllib.load(open(sys.argv[1],"rb")); print("TOML OK")' ~/.config/devenv/config.toml
# 2. cross-check against reality (examples)
python3 - <<'PY'
import tomllib, shutil, subprocess, os
c = tomllib.load(open(os.path.expanduser("~/.config/devenv/config.toml"),"rb"))
sh = c.get("shell-sync",{}).get("canonical")
if sh and not shutil.which(sh): print(f"WARN: canonical shell '{sh}' not found")
for f in c.get("brew-doctor",{}).get("pinned",[]):
    r = subprocess.run(["brew","list","--formula",f],capture_output=True)
    if r.returncode: print(f"WARN: pinned '{f}' is not installed")
print("checked")
PY
```
Report mismatches (a setting that doesn't match the machine) rather than silently trusting the file.

## How skills consume it (for reference)

A skill reads `~/.config/devenv/config.toml`, and **if its `[section]` exists** uses those keys as
defaults, skipping the matching questions. Precedence is always: explicit answer this session >
`config.toml` > ask. A skill that had to ask (no stored value) offers to write the answer back into
its section here.
