---
name: Runtime Versions
description: Find, set up, repair, upgrade, and optimize your language runtimes (node, python, go, ruby…) with ONE tool — mise — instead of a pile of nvm/asdf/pyenv/homebrew-node managers that fight over PATH. Use to FIND which runtime/version/scope to install (search mise's versions, LTS vs latest, global vs per-project), SET UP mise (greenfield, or migrate off the sprawl: capture versions, activate, neutralize old managers), REPAIR a broken resolution (`node` differs per shell, an old shim wins, mise not activated), UPGRADE versions day-to-day (`mise use`, bump, prune, honor `.tool-versions`/`.nvmrc`), or OPTIMIZE a working setup (residual sprawl, leftover shim dirs, global versions lagging intent). Every change is verified in a clean environment, in both shells, before old managers are removed.
argument-hint: [find|setup|repair|upgrade|optimize]
allowed-tools: Bash(*runtime-versions/scripts/*), Bash(mise doctor), Bash(mise ls*), Bash(mise ls-remote*), Bash(mise registry*), Bash(mise which *), Bash(mise current*), Bash(mise settings*), Bash(command -v *), Bash(type *), Bash(which -a *), Bash(env -i *), Bash(zsh -l *), Bash(zsh -i *), Bash(zsh -c *), Bash(fish -l *), Bash(fish -c *), Bash(cat *), Bash(ls *), Bash(brew list *), Bash(brew leaves), Bash(git -C * *)
---

# Runtime versions

Manage language runtimes with **one** manager — [mise](https://mise.jdx.dev) — and end the
**nvm/asdf/pyenv/rbenv/fnm/homebrew-node sprawl** where every tool has its own shims, its own PATH
entry, and its own opinion about which `node` you get. mise is a single fast shim layer that reads
the `.tool-versions`/`.nvmrc`/`mise.toml` files the others left behind, so migration is additive.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Choose which runtime / version / scope to install (before installing) | [reference/find.md](reference/find.md) |
| Stand up mise — greenfield, or migrate off nvm/asdf/pyenv/… safely | [reference/setup.md](reference/setup.md) |
| Fix a broken resolution — `node` differs per shell, an old shim wins, mise not active | [reference/repair.md](reference/repair.md) |
| Set / install / bump versions day-to-day, global or per-project | [reference/upgrade.md](reference/upgrade.md) |
| Review a working setup — residual sprawl, leftover dirs, global lags intent | [reference/optimize.md](reference/optimize.md) |

## The scripts (prefer these over ad-hoc bash)

Stable, tested, **read-only** helpers live in [`scripts/`](scripts/README.md) — **call them instead
of re-composing the `command -v` / `which -a` / `mise which` / `env -i` blocks each session.** Run by
absolute path from this skill's directory. They handle a missing manager/shell/mise gracefully.

| Need | Script |
|---|---|
| **Choose what to install** (find): is a tool mise-managed, recent versions + `@lts`, current owner, brew/legacy flag | `scripts/runtime_find.py [tool …]` |
| Sprawl hunt: which managers are present, their rc hooks + versions, brew runtimes, shim dirs (**run first** for setup/repair/optimize) | `scripts/detect_managers.py` |
| Who resolves a runtime (current shell): `command -v`, real path, owning manager, mise's opinion, dupes | `scripts/tool_resolve.py [tool …]` |
| The real per-shell test — clean-env (`env -i`) login resolution in zsh/fish + mise-shims count | `scripts/shell_resolve.py [zsh\|fish\|both] [tool …]` |
| mise health + inventory: activated? shims dir, problems, `current`, `ls` | `scripts/mise_status.py` |

Full contract + a worked example: [scripts/README.md](scripts/README.md). The inline `bash` snippets in
this file and the reference `.md`s show what the scripts run **under the hood** — reach for them for
novel one-off checks, not to re-type the routine diagnostics.

## Discovery (always run first)

**Run `scripts/detect_managers.py`** (which managers, rc hooks, brew runtimes, shim dirs), then
`scripts/tool_resolve.py` (what each tool resolves to now) and, for the per-shell truth,
`scripts/shell_resolve.py both`. Under the hood, that is:

```bash
mise --version 2>/dev/null || echo "mise NOT installed"
command -v mise nvm asdf pyenv rbenv fnm                  # which managers are present
brew list --formula 2>/dev/null | grep -E '^(node|python|ruby|go)(@|$)'  # homebrew runtimes
mise which node python go 2>/dev/null                     # what mise would resolve (if active)
command -v node python go                                 # what THIS shell actually resolves
```
- Multiple managers present, or a runtime installed via **both** brew and a manager, is the sprawl
  this skill fixes — different shells silently get different versions. Review it in
  [optimize.md](reference/optimize.md); an active per-shell divergence is [repair.md](reference/repair.md).
- **Shells activate these managers**, so the truth is per-shell. Always check zsh **and** fish
  (`scripts/shell_resolve.py both`).

## Core principles

1. **mise-first, additive migration.** mise reads existing `.tool-versions`/`.nvmrc`, so adopting it
   doesn't break projects. Set up mise, verify it, *then* neutralize the old managers.
2. **Verify in a CLEAN environment.** A shell spawned inside your current session inherits a polluted
   PATH. Prove resolution with `scripts/shell_resolve.py both` (clean `env -i` in each shell) — see
   [verification.md](reference/verification.md).
3. **Don't remove old managers until mise is verified** working in both zsh and fish. Back up shell
   config first; shell edits are owned by the `shell-sync` skill (below), not reimplemented here.
4. **Don't assume state.** Re-run discovery each time — which manager wins depends on shim PATH order.

## Cross-skill coordination (reference, don't reimplement)

- **shell-sync** — mise activation adds shims to PATH; the **canonical** shell owns the `mise activate`
  line and the **mirror** is regenerated. Route all shell-config edits through it.
- **dotfiles** — track `~/.config/mise/config.toml` via chezmoi so global versions are reproducible.
- **brew-doctor** — install mise via `brew`; uninstall `nvm`/`asdf`/`node@x` after migration verifies.
- **nvim-config** — LSP servers run on the mise-managed runtime; a version change can move them.

## Settings

Read `~/.config/devenv/config.toml` before prompting; if a `[runtime-versions]` section exists, use it
as defaults (precedence: explicit answer this session > `config.toml` > ask). Had to ask? Offer to save
the answer back. Managed by the `devenv` skill. Keys honored:
- `manager` — the version manager to standardize on (e.g. `"mise"`).
- `tools` — map of global runtime versions, e.g. `node = "lts"`, `python = "3.13"`, `go = "latest"`.

## Safety

- Switching managers **changes which runtime a project resolves** — verify per-project
  `.tool-versions`/`.nvmrc` are still honored under mise before trusting the switch.
- **Back up shell config** (`~/.zshrc`, `~/.config/fish/config.fish`) before neutralizing a manager.
- **Do not remove nvm/asdf/pyenv/`node@x` until mise is verified** in a clean env in BOTH shells — a
  half-migrated PATH silently falls back to the old manager (or to no runtime at all).
- Confirm before editing shell config, `mise use -g` (changes global default), or any uninstall.
