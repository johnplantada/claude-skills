# nvim-config — a Claude Code skill for managing Neovim configurations

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that sets up, repairs, upgrades,
and optimizes Neovim configurations — and **verifies every change by driving headless Neovim**,
so fixes are proven, not guessed.

lazy.nvim-first, works against whatever is actually on disk (XDG-aware), and grounded in a
catalog of the real breakages that hit modern Neovim 0.11/0.12 configs.

## What it does

Four workflows, routed by intent (pass an argument or just describe the goal):

| Workflow | Use it to… |
|---|---|
| **setup** | Stand up a new config tailored to an interview — choose **bespoke minimal**, **kickstart.nvim**, or **LazyVim**. |
| **repair** | Diagnose and fix a broken config (startup errors, failed plugins, LSP/treesitter issues) with a guided, confirm-as-you-go flow. |
| **upgrade** | Update plugins and tooling **safely** — backup, update, verify, and roll back if an update breaks something. |
| **optimize** | Review a working config as a whole, present a prioritized plan, then implement (startup time, lazy-loading, deprecations, redundancy). |

## Why it's different

- **Verification-first.** It never declares a change done from reading code. It opens real files
  in headless Neovim and checks that highlighting activates, LSP clients attach with the right
  capabilities, formatters run, and no deprecations fire — with **before/after** comparisons.
- **Knows the modern breakages.** treesitter `master`→`main`, mason-lspconfig v2 (`handlers`
  removed, `automatic_enable` launching formatters as LSPs), the 0.11/0.12 API deprecation table,
  conform's Python-formatter timeout — all catalogued with fixes.
- **Safe by default.** Backs up before risky changes, confirms before overwriting, and checks
  that external CLIs exist before relying on them.

## Requirements

- **Claude Code** (the skill runs inside it).
- **Neovim** — 0.10+ to manage; 0.11+ recommended for new setups.
- Standard tooling as needed: `git`, a C compiler, `node`/`npm`, `ripgrep`, and the
  `tree-sitter` CLI (`npm i -g tree-sitter-cli`) for treesitter parser builds.

## Install

This skill ships in the [claude-skills](../) gallery. Clone the gallery and symlink this skill
into your Claude Code **skills** directory so edits stay live:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/nvim-config ~/.claude/skills/nvim-config
```

Prefer a copy, or project-scoped? Copy this directory into `~/.claude/skills/` or a project's
`.claude/skills/`. The skill's command name comes from the directory, so keep the folder named
`nvim-config`.

Verify Claude Code sees it: it should appear in the skills list, invocable as `/nvim-config`.

## Usage

```
/nvim-config setup      # interview + build a new config
/nvim-config repair     # guided fix of a broken config
/nvim-config upgrade    # update plugins/tooling, then verify
/nvim-config optimize   # audit → plan → implement
```

Or just say what you want — "my nvim throws errors after an update", "make my startup faster",
"help me set up Neovim for Go" — and the skill auto-activates and routes to the right workflow.

## How it works

`SKILL.md` is a small router: it runs **environment discovery** (Neovim version, config dir via
`stdpath`, plugin manager, structure), then hands off to one of four workflow files under
`reference/`. Detailed procedures and the breakage catalog load only when needed (progressive
disclosure), keeping the always-on footprint small.

```
nvim-config/
├── SKILL.md                 # router + environment discovery + core principles
├── reference/
│   ├── setup.md             # greenfield setup (bespoke / kickstart / LazyVim)
│   ├── repair.md            # guided diagnose → fix
│   ├── upgrade.md           # backup → update → verify → rollback
│   ├── optimize.md          # audit → plan → implement
│   ├── verification.md      # headless-Neovim verification snippets
│   └── known-issues.md      # catalog of modern breakages + fixes
└── README.md                # (LICENSE lives at the gallery root)
```

## Contributing

Issues and PRs welcome — especially new entries for `reference/known-issues.md` as Neovim and the
plugin ecosystem move. Keep additions **verified** (include the headless check that proves it) and
concise.

## License

[MIT](../LICENSE).
