# Optimize workflow — review a working mise setup and tighten it

Goal: you're on mise and it works — now reduce residual risk and drift: leftover managers/shim dirs
still on PATH, a runtime installed via both brew and mise, and global versions that lag your intent.
Review and report; change nothing without confirmation. (An *active* conflict — `node` resolves
differently per shell, or an old shim beats mise — is broken, not merely untidy → [repair.md](repair.md).)

> **Use the scripts** ([scripts/README.md](../scripts/README.md)) — this whole review is three calls:
> `detect_managers.py` → `tool_resolve.py` → `shell_resolve.py both`. The `bash` blocks below are what
> they run under the hood; reach for them only for a novel one-off check.

## 1. Which managers are present & active

**`scripts/detect_managers.py`** — reports mise + each legacy manager (present? home dir? which rc
file inits it? global version it provides), brew-installed runtimes, and legacy shim dirs on PATH, as
greppable `key<TAB>value` lines. Under the hood:

```bash
command -v mise nvm asdf pyenv rbenv fnm                  # installed managers
brew list --formula | grep -E '^(node|python|ruby|go)(@|$)'   # runtimes ALSO installed via brew
ls -d ~/.nvm ~/.pyenv ~/.rbenv ~/.asdf 2>/dev/null        # leftover manager homes (shim dirs)
```
A runtime installed via **both** brew and a manager, or **two** managers for the same language, is
sprawl: whichever shim sits earliest on PATH silently wins.

## 2. What each tool actually resolves to

**`scripts/tool_resolve.py [tool …]`** (default node/python/go/ruby) — per tool: `command -v`, the
real path with symlinks followed, the **owning manager** (mise/nvm/pyenv/brew/system/…), mise's
opinion (`mise which`), and every copy on PATH. Under the hood:

```bash
for t in node python go ruby; do printf '%s -> ' "$t"; command -v "$t"; done
mise which node python go ruby 2>/dev/null               # where mise WOULD point (if active)
which -a node                                            # every node on PATH, in order — dupes = sprawl
```
`tool_resolve.py` queries **this** (non-interactive) shell. If an `_owner` is **not** `mise` while
mise is meant to own it, an old manager is winning.

## 3. Shim order on PATH (who wins)

`detect_managers.py` reports `legacy_shims_on_path` (numbered, first wins). Raw form:

```bash
echo "$PATH" | tr ':' '\n' | grep -nE 'mise|shims|\.nvm|\.pyenv|\.rbenv|asdf|fnm'
```
The **first** matching entry wins. mise's shims should precede every legacy shim dir. A `.pyenv/shims`
or `.nvm` entry ahead of mise is the smoking gun.

## 4. Per-shell divergence (the `node`-differs-per-shell bug)

Managers are initialized by shell config, so **zsh and fish can resolve different versions**.
**`scripts/shell_resolve.py both`** launches each shell from a CLEAN `env -i` login (a nested shell
inherits the outer PATH and hides the divergence — see [verification.md](verification.md)) and prints
`<shell>:<tool>  <path>  <version>` for each. Under the hood:

```bash
env -i HOME="$HOME" TERM=xterm /bin/zsh  -l -i -c 'echo "zsh:  $(command -v node) $(node -v 2>/dev/null)"'
env -i HOME="$HOME" TERM=xterm /usr/bin/env fish -l -c 'echo "fish: "(command -v node) (node -v 2>/dev/null)'
```
Different paths or versions between the two → the shells activate different managers. This is a
`shell-sync` problem: the canonical shell must own `mise activate` and the mirror is regenerated from
it. Reference that skill; don't hand-patch one shell.

## 5. Report — prioritized

- 🔴 **`node`/`python` resolves differently per shell**, or an old manager's shim wins over mise → an
  active conflict (broken). Hand to [repair.md](repair.md): fix the canonical activation via
  shell-sync, then re-verify.
- 🟡 Multiple managers installed, or a runtime installed via both brew and a manager, or legacy shim
  dirs (`~/.nvm`, `~/.pyenv`) still on PATH though unused → consolidate onto mise ([setup.md](setup.md)).
- 🟢 mise owns everything consistently, but a global version lags intent (settings `tools` map) →
  `mise use -g` to align ([upgrade.md](upgrade.md)).

Each finding with the exact command to fix.
