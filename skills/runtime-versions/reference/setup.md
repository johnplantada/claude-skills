# Set up workflow — make mise your one runtime manager

Goal: get **mise** owning your runtimes — whether that's **greenfield** (no manager yet: install
mise, activate it, install what you need) or **migrating** off an nvm/asdf/pyenv/rbenv/fnm/
homebrew-node sprawl without breaking a single project. mise reads existing `.tool-versions`/
`.nvmrc`, so migration is additive: set up mise, verify it, *then* neutralize the old managers.
**Never remove an old manager before mise is verified.**

> Greenfield (nothing installed yet)? Do steps 1, 3, 4, 5 — skip capture/neutralize (2, 6).
> Deciding *which* versions to install? → [find.md](find.md). Broken resolution to fix? →
> [repair.md](repair.md).

> **Use the scripts** ([scripts/README.md](../scripts/README.md)): `detect_managers.py` for step 2's
> capture (present managers + their global versions), `shell_resolve.py both` + `mise_status.py` for
> the step-5 gate. The `bash` blocks are what they run under the hood.

## 1. Install mise (via Homebrew)

```bash
brew install mise                    # chain into the brew-doctor skill for a clean install
mise --version
```

## 2. Detect existing managers & capture their versions

Inventory what's installed and, crucially, the **versions each currently provides** — you'll recreate
these in mise. **`scripts/detect_managers.py`** does this: per present manager it prints its rc hook
and best-effort global version (`nvm_default`, `pyenv_global`, `asdf_current`, …), plus brew runtimes.
Under the hood:

```bash
command -v nvm asdf pyenv rbenv fnm                       # shim-based managers
brew list --formula | grep -E '^(node|python|ruby|go)(@|$)'   # homebrew runtimes (e.g. node@20)
# global/installed versions per manager (run only those that exist):
nvm ls 2>/dev/null;   nvm version default 2>/dev/null     # node
asdf current 2>/dev/null; asdf list 2>/dev/null           # all asdf tools
pyenv versions 2>/dev/null; pyenv global 2>/dev/null      # python
rbenv versions 2>/dev/null; rbenv global 2>/dev/null      # ruby
fnm list 2>/dev/null                                      # node (fnm)
```
Record the **global** version for each tool — that becomes `mise use -g`. Note any `.nvmrc` /
`.tool-versions` in active project dirs; mise honors them as-is (no rewrite needed).

## 3. Recreate versions in mise

```bash
mise use -g node@lts                 # or the exact captured version, e.g. node@20
mise use -g python@3.13
mise use -g go@latest ruby@3.3       # one tool@version per captured runtime
mise install                         # download everything declared globally
mise ls                              # confirm each tool is present and Active
```
`mise use -g` writes `~/.config/mise/config.toml` (track it via the **dotfiles** skill). Honor the
`[runtime-versions] tools` map from settings as the default version set.

## 4. Activate mise in the shell (via shell-sync)

mise works through a shim/activation line that must be added to the **canonical** shell; the mirror
is regenerated. **Do not hand-edit both shells** — route this through the `shell-sync` skill so PATH
stays consistent. The activation lines it should own:

| Shell | Line |
|---|---|
| zsh (`~/.zshrc`) | `eval "$(mise activate zsh)"` |
| fish (`~/.config/fish/config.fish`) | `mise activate fish \| source` |

Activation must come **after** (and eventually instead of) the old managers' init lines on PATH.

## 5. VERIFY before removing anything

Confirm every runtime resolves to a mise shim in **both** zsh and fish — run
**`scripts/shell_resolve.py both`** (clean-env per-shell) and **`scripts/mise_status.py`** (activation
+ inventory); full criteria in [verification.md](verification.md). Do not proceed until it passes.
This is the gate.

## 6. Neutralize the old managers (only now)

Back up shell config first (`cp ~/.zshrc ~/.zshrc.bak`, likewise `config.fish`). Then, via
**shell-sync**, remove/comment the old managers' init from the canonical shell and regenerate the
mirror:

| Manager | Init to remove from shell config |
|---|---|
| nvm | `export NVM_DIR=…` + the `nvm.sh` / bash_completion source lines |
| pyenv | `eval "$(pyenv init -)"` (and `pyenv virtualenv-init`) |
| rbenv | `eval "$(rbenv init -)"` |
| asdf | the `asdf.sh` source line (`. $(brew --prefix asdf)/libexec/asdf.sh`) |
| fnm | `eval "$(fnm env …)"` |

Re-verify in a clean env (step 5) after removing each. Once green in both shells, uninstall the
managers via the **brew-doctor** skill:

```bash
brew uninstall nvm asdf pyenv rbenv fnm 2>/dev/null       # confirm each first
brew uninstall node@20 python@3.11 2>/dev/null            # homebrew runtimes mise now owns
# non-brew nvm: rm -rf ~/.nvm  (confirm)
```
Leftover `~/.tool-versions`, `.nvmrc`, `~/.pyenv`, `~/.rbenv` shim dirs on PATH are the usual cause of
"it still uses the old node" — hunt them in [repair.md](repair.md).

## Report

What was migrated (tool → version), the activation now owned by the canonical shell, the clean-env
verification result for both shells, and which old managers were removed vs. still pending.
