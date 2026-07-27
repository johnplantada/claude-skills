# devenv — the dev-environment capstone

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that sits on top of the gallery's
per-layer skills (`nvim-config`, `shell-sync`, `dotfiles`, `brew-doctor`, `runtime-versions`,
`macos-defaults`, `git-setup`, `ssh-config`) and gives them two things they can't own individually:
**shared settings** and **ordered cross-skill runbooks**.

It **delegates** — it never re-implements a skill's logic.

## What it does

| Workflow | Use it to… |
|---|---|
| **settings** | View/edit/validate `~/.config/devenv/config.toml` — the config each skill reads for its defaults, so they stop re-asking (canonical shell, pin list, tracked paths…). |
| **bootstrap** | Set up a new machine end-to-end: Homebrew → chezmoi → SSH keys → dotfiles → `brew bundle` → git-setup → runtimes → shell-sync → nvim → macOS defaults — in the right order, with the right gates. |
| **health** | Run every skill's audit and merge into one prioritized, cross-layer report. |

## Why it's not a control plane

The skills already compose by cross-reference, and Claude chains them per request. What no single
skill can own is (a) **settings shared across skills** and (b) **the order + gates** of a multi-layer
flow like bootstrap. `devenv` owns exactly those, and nothing else:

- **Settings are defaults, not locks** — precedence is always: explicit answer this session >
  `config.toml` > ask. A skill that had to ask offers to save the answer back.
- **Runbooks delegate** — bootstrap/health invoke the individual skills; the real work and
  verification stay in them.
- **The settings file is a dotfile** — track it via `dotfiles` so your whole setup is reproducible.

## The settings file

```toml
# ~/.config/devenv/config.toml
[shell-sync]
canonical = "zsh"
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
signing = "ssh"
pager = "delta"
[ssh-config]
key_type = "ed25519"
```

## Install

Part of the [claude-skills](../) gallery:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/devenv ~/.claude/skills/devenv
```

## Usage

```
/devenv settings     # view / edit / validate shared settings
/devenv bootstrap     # new-machine, end-to-end
/devenv health        # whole-environment audit sweep
```

```
devenv/
├── SKILL.md                 # router + settings contract + delegate-don't-duplicate
├── reference/
│   ├── settings.md          # config.toml schema + view/edit/validate
│   ├── bootstrap.md         # ordered new-machine runbook (delegates)
│   └── health.md            # merged cross-layer audit
└── README.md                # (LICENSE lives at the gallery root)
```

## License

[MIT](../../LICENSE).
