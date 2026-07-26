---
name: Neovim Config
description: Set up, repair, upgrade, and optimize a Neovim configuration. Use for GREENFIELD setup of a new config tailored to what the user wants, for REPAIRing a broken config (startup errors, failed plugins, LSP/treesitter issues), for UPGRADEing plugins and tooling safely, or for OPTIMIZing an existing working config (startup time, lazy-loading, deprecations, redundancy). lazy.nvim-first; every change is verified by driving headless Neovim.
argument-hint: [setup|repair|upgrade|optimize]
allowed-tools: Bash(nvim --headless *), Bash(nvim --version), Bash(ls *), Bash(tail *), Bash(cp *), Bash(git -C * *), Bash(*nvim-config/scripts/*)
---

# Neovim config toolkit

A generalized toolkit for managing **any** user's Neovim configuration through four workflows.
Works against the real environment on disk — **never assume the setup**; discover it first.

## 1. Route to a workflow

The user may pass an argument (`setup` | `repair` | `upgrade` | `optimize`) or describe the goal
in their own words. Match intent to a workflow, then follow that file:

| The user wants to… | Workflow |
|---|---|
| Create a config (none yet, or a fresh tailored one) | [reference/setup.md](reference/setup.md) |
| Fix something broken (errors, a plugin/LSP/treesitter failing) | [reference/repair.md](reference/repair.md) |
| Update plugins/tooling and stay current | [reference/upgrade.md](reference/upgrade.md) |
| Review a working config and make it better | [reference/optimize.md](reference/optimize.md) |

If intent is ambiguous, run **Environment discovery** below, then confirm which workflow.

## 2. The scripts (prefer these over ad-hoc bash)

Stable, tested helpers live in [`scripts/`](scripts/README.md) — **call them instead of
re-composing bash/Lua each session.** Run by absolute path from this skill's directory. They
resolve `stdpath` internally, so never hardcode `~/.config/nvim`.

| Need | Script |
|---|---|
| Environment discovery (**run first**) | `scripts/nvim_env.py` |
| A plugin's version, pins, tags, drift; locate a symbol across installed/newest-tag/core | `scripts/plugin_info.py <plugin> [symbol]` |
| Runtime verification: `startup` · `open <ext>` · `ts <ext>` · `lsp <ext>` · `deprecations` · `api <vim.path>` | `scripts/nvim_check.py <check> …` |
| Run arbitrary Lua headlessly, correctly (one-off checks) | `scripts/nvim_lua.py '<lua>'` |

Full contract + a worked example: [scripts/README.md](scripts/README.md). Reach for `nvim_lua.py`
for novel checks and the `.md` snippets below for what the scripts run under the hood.

## 3. Environment discovery (always run first)

`scripts/nvim_env.py` prints all of this as `key<TAB>value` lines. What each fact means:

- **Config dir** — honor `stdpath('config')` (`$XDG_CONFIG_HOME/nvim`, `~/.config/nvim`, or
  `~/AppData/Local/nvim`). Never hardcode `~/.config/nvim`.
- **Plugin manager** — lazy.nvim if there's a `lazy-lock.json` in the config dir or a `lazy/`
  dir under `stdpath('data')`. Also recognize packer, vim-plug, mini.deps, rocks.nvim. This
  toolkit **fully drives lazy.nvim**; for other managers, detect and advise, don't automate.
- **Structure** — single `init.lua` vs a modular `lua/` tree. **Read the real plugin specs**
  to learn the user's conventions before editing.
- **Data/state** — plugins & treesitter parsers live under `stdpath('data')`; logs
  (`lsp.log`, `conform.log`) under `stdpath('state')`.

## 4. Core principles (every workflow)

1. **Verify with headless Neovim.** Never declare a change done from reading code — config bugs
   (wrong API, load order, deprecations) only surface at runtime. Drive nvim and inspect the
   result: `scripts/nvim_check.py` for the common checks, `scripts/nvim_lua.py` for novel ones;
   snippets in [reference/verification.md](reference/verification.md). Do a **before/after**
   comparison for any fix or optimization.
2. **Check the version first.** Package managers auto-upgrade Neovim; a minor bump (e.g.
   0.11→0.12) is the single most common cause of sudden breakage.
3. **Back up before risky changes.** Copy `lazy-lock.json` before updates. If the config is a
   git repo, offer to commit first. If not, keep edits surgical and reversible, and say so.
4. **Don't assume inventory.** Read plugin specs from disk each session — they drift.
5. **Cross-reference known breakages:** [reference/known-issues.md](reference/known-issues.md)
   (Neovim-version bumps, treesitter master→main, mason-lspconfig v2, API deprecations, conform).

## 5. Settings

Read `~/.config/devenv/config.toml` before prompting for choices; if a `[nvim-config]` section
exists, use it as defaults (precedence: explicit answer this session > `config.toml` > ask). Had to
ask? Offer to save the answer back. Managed by the `devenv` skill. Keys honored:
- `plugin_manager` — expected manager (e.g. `lazy`). Most nvim state is discovered from disk, so
  this is the main knob; missing → detect it.

## 6. Safety

- Confirm before deleting or overwriting user config. On **setup over an existing config**, back
  it up (timestamped) first — never clobber silently.
- External CLIs must exist before use — verify, don't assume: `git`, a C compiler, `tree-sitter`
  (via `npm i -g tree-sitter-cli`), `node`/`npm`, `ripgrep`, and any formatters/LSP servers.
- Prefer the narrowest change that fixes the problem; don't break working LSP/completion chasing
  a cosmetic cleanup.
