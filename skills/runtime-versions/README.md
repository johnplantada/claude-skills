# runtime-versions — one runtime manager (mise), not five

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that helps you **find, set up,
repair, upgrade, and optimize** your language runtimes (node, python, go, ruby…) with a single
tool — [mise](https://mise.jdx.dev) — replacing the nvm/asdf/pyenv/rbenv/fnm/homebrew-node sprawl
where every manager has its own shims, its own PATH entry, and its own idea of which `node` you get.
Every change is verified in a clean environment, in both shells, before the old managers are removed.

## What it does

| Workflow | Use it to… |
|---|---|
| **find** | Choose *what* to install: is a tool mise-managed, its recent versions + `@lts`, what resolves now and who owns it, and a flag if brew/an old manager already provides it — before you install. |
| **setup** | Stand up mise — greenfield, or migrate off the sprawl: install mise, capture the versions your old managers provide, recreate them, activate it (via `shell-sync`), then neutralize and uninstall nvm/asdf/pyenv/`node@x`. |
| **repair** | Fix a broken resolution — `node` differs between zsh and fish, an old shim wins over mise, mise isn't activated, or a version won't resolve. |
| **upgrade** | Day-to-day: global vs per-project versions (`mise use`), install/list/bump/prune, honoring existing `.nvmrc`/`.tool-versions` without rewriting them. |
| **optimize** | Review a working setup — residual manager sprawl, leftover shim dirs still on PATH, a runtime installed via both brew and mise, and global versions that lag your intent. |

## Why it's different

Runtime managers fight over PATH silently. Two of them installed, or a runtime installed via **both**
Homebrew and nvm, means whichever shim sits earliest on PATH wins — and since shells initialize
managers in *their own* config, zsh and fish can hand you **different** versions of the same runtime.
This skill:

- **Standardizes on mise** — one fast shim layer that already reads `.tool-versions`/`.nvmrc`, so
  migration is additive and no project breaks.
- **Verifies in a clean environment** — it proves resolution with `env -i` in both zsh and fish, not
  from reading config (a nested shell inherits a polluted PATH and lies).
- **Won't remove the old managers until mise is proven** working in both shells, with shell config
  backed up first.
- **Coordinates, doesn't reimplement** — shell activation is owned by `shell-sync`, install/uninstall
  by `brew-doctor`, config tracking by `dotfiles`, editor tooling by `nvim-config`.

## Requirements

- **Claude Code**, plus **Homebrew** (to install mise). macOS or Linux, zsh and/or fish.

## Install

Part of the [claude-skills](../) gallery:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/runtime-versions ~/.claude/skills/runtime-versions
```

## Usage

```
/runtime-versions find        # choose which runtime/version/scope to install
/runtime-versions setup       # stand up mise / move off nvm/asdf/pyenv, verified
/runtime-versions repair      # fix node-differs-per-shell, an old shim winning
/runtime-versions upgrade     # set/install/bump versions, global or per-project
/runtime-versions optimize    # review a working setup: residual sprawl, stale globals
```

Or describe it — "my node is different in fish than in zsh", "get me off nvm and pyenv", "pin this
project to node 22", "which python should I install" — and it routes to the right workflow.

```
runtime-versions/
├── SKILL.md                 # router + discovery + mise-first principles + settings
├── scripts/                 # stable, tested, read-only diagnostics (call these)
│   ├── runtime_find.py      # find: is a tool mise-managed, versions + @lts, owner, brew/legacy flag
│   ├── detect_managers.py   # sprawl hunt: managers, rc hooks, versions, brew runtimes, shim dirs
│   ├── tool_resolve.py      # who resolves a runtime: command -v, real path, owner, mise's opinion
│   ├── shell_resolve.py     # clean-env (env -i) per-shell resolution — the node-differs test
│   ├── mise_status.py       # mise health + inventory (doctor / current / ls)
│   └── README.md            # toolbox table + worked example + conventions
├── reference/
│   ├── find.md              # choose which runtime/version/scope before installing
│   ├── setup.md             # install mise -> capture old versions -> activate -> neutralize old
│   ├── repair.md            # node-differs-per-shell, old shim wins, mise not active, won't resolve
│   ├── upgrade.md           # global vs per-project, install/list/bump/prune, honor .nvmrc
│   ├── optimize.md          # residual sprawl + leftover dirs + global lags intent, prioritized
│   └── verification.md      # mise doctor + clean-env resolution in BOTH shells
└── README.md                # (LICENSE lives at the gallery root)
```

## License

[MIT](../../LICENSE).
