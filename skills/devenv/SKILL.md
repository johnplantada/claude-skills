---
name: Dev Environment
description: The capstone for the dev-environment skill gallery — a shared SETTINGS store the other skills read, plus ordered cross-skill RUNBOOKS. Use to view/edit settings that drive the layer skills (nvim-config, shell-sync, dotfiles, brew-doctor, runtime-versions, macos-defaults, git-setup, ssh-config) so they stop re-asking, to BOOTSTRAP a new machine end-to-end, or to run a whole-environment HEALTH sweep. Delegates to the individual skills — it never duplicates their logic.
argument-hint: [settings|bootstrap|health]
allowed-tools: Bash(cat *), Bash(ls *), Bash(python3 -c *), Bash(git -C * *)
---

# devenv — dev-environment capstone

The layer **on top of** the gallery's per-layer skills (`nvim-config`, `shell-sync`, `dotfiles`,
`brew-doctor`, `runtime-versions`, `macos-defaults`, `git-setup`, `ssh-config`). Two jobs, and only
two:

1. **Shared settings** — a single config file every skill reads for its defaults.
2. **Runbooks** — ordered, cross-skill flows (bootstrap, health) that *delegate* to the skills.

It **never re-implements** a skill's logic. If a task is single-layer (just nvim, just brew), use
that skill directly.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| See/change settings that drive the skills | [reference/settings.md](reference/settings.md) |
| Set up a new machine end-to-end | [reference/bootstrap.md](reference/bootstrap.md) |
| Check the whole environment's health | [reference/health.md](reference/health.md) |

## The settings store (the contract)

Location: **`${XDG_CONFIG_HOME:-$HOME/.config}/devenv/config.toml`** (referred to as
`~/.config/devenv/config.toml`). One file, a `[section]` per skill. Each skill reads **its own
section** for defaults; a missing file or key just means the skill asks as usual and offers to save
the answer. Full schema + validation: [reference/settings.md](reference/settings.md).

```toml
[shell-sync]
canonical = "zsh"          # source-of-truth shell; mirror = the other
sync = ["path", "env", "aliases"]
[brew-doctor]
pinned = ["neovim"]
brewfile = "~/Brewfile"
autoupdate_mode = "update-only"
[dotfiles]
manager = "chezmoi"
ignore = ["*.bak", ".config/fish/conf.d/00-shell-sync.fish"]
[nvim-config]
plugin_manager = "lazy"
[runtime-versions]
manager = "mise"
tools = { node = "lts", python = "3.13" }
[macos-defaults]
script = "~/.config/devenv/macos.sh"
[git-setup]
signing = "ssh"            # "ssh" | "gpg" | "none"
pager = "delta"
[ssh-config]
key_type = "ed25519"
```

The file is a plain dotfile — **track it via the `dotfiles` skill** so settings are reproducible.

## Core principles

1. **Delegate, don't duplicate.** Runbooks invoke the individual skills (via the Skill tool) in the
   right order with the right gates; the real work lives in those skills.
2. **Settings are defaults, not locks.** Precedence: an explicit answer this session > the value in
   `config.toml` > ask the user. Never override a fresh explicit instruction with a stored setting.
3. **Verify per layer.** Each delegated skill owns its own verification; the capstone's job is
   sequencing and merging results, not re-checking.
4. **Read reality too.** Settings describe intent; still confirm against the machine (the canonical
   shell exists, pinned formulae are installed, etc.).

## Safety

- Bootstrap and health touch every layer — confirm scope before a full run, and honor each skill's
  own safety gates (secrets, private keys, backups, private repos, gated upgrades).
- Editing `config.toml` changes how future skill runs behave — show the diff and validate it.
