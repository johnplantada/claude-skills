# brew-doctor — keep Homebrew healthy, and stop it from breaking your tools

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that helps you **find** the best
install for a need, then **set up, repair, upgrade, and optimize** Homebrew safely — a declarative
Brewfile, **gated** upgrades, and detection of silent auto-upgrade mechanisms so a background
`brew upgrade` never breaks a version-sensitive tool. Every change is verified before it's called done.

## What it does

| Workflow | Use it to… |
|---|---|
| **find** | Search formulae/casks for a need, read the dossier (popularity, deprecation, arch bottle), and **choose the best install for your machine** — formula vs cask, versioned + pinned, or a runtime → `mise` instead of brew. |
| **setup** | Install Homebrew, restore a machine from a declarative `Brewfile`, track it (ideally via the `dotfiles` skill), and set the initial safety gates (pins + a tamed auto-updater). |
| **repair** | Fix a broken brew — `brew doctor` errors, broken links/permissions, missing deps, a bad tap, or a tool a bad upgrade just broke. |
| **upgrade** | Snapshot → pin fragile formulae → upgrade selectively → **verify** → clean up. |
| **optimize** | Review a working setup and make it safer/leaner: **detect & tame silent auto-upgrade mechanisms**, pin unpinned fragile formulae, find orphans + `brew doctor` issues, and keep the Brewfile honest. |

## Why it exists

An unattended `brew upgrade` — from `brew autoupdate` in `--upgrade` mode, a launchd/cron timer, or
a dependency pulled up during an unrelated `brew install` — can bump a tool across a major version
and break its config (e.g. **neovim 0.11→0.12 breaking treesitter**). Note the skill **checks the
actual mode** of any auto-updater rather than assuming it upgrades (many run `brew update` +
notify, which is harmless). Homebrew rollback is hard, so it leans on **prevention**:

- **Gate fragile upgrades** — pin editors/LSPs/databases; tame or disable background auto-upgrade.
- **Verify after upgrading** — a green `brew doctor` isn't proof your tools run; the skill drives
  the affected tool (chaining into `nvim-config` / `shell-sync` verification).
- **Declarative Brewfile** — a reproducible, reviewable record that pairs with `dotfiles`.

## Requirements

- **Claude Code**, plus **Homebrew**. macOS or Linux.

## Install

Part of the [claude-skills](../) gallery:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/brew-doctor ~/.claude/skills/brew-doctor
```

## Usage

```
/brew-doctor find       # search + choose the best install for a need
/brew-doctor setup      # install / restore from Brewfile / set the gates
/brew-doctor repair     # fix doctor errors, broken links, a bad upgrade
/brew-doctor upgrade    # gated, verified upgrade
/brew-doctor optimize   # audit + harden a working setup
```

Or describe it — "did brew break my nvim again", "pin my fragile packages", "make a Brewfile",
"upgrade brew safely" — and it routes to the right workflow.

```
brew-doctor/
├── SKILL.md                 # router + discovery + gate-fragile-upgrades principle
├── scripts/                 # tested toolbox — call these over ad-hoc bash
│   ├── brew_find.py         # read-only search + info + best-install advisor
│   ├── brew_audit.py        # read-only health/risk report + auto-upgrade mode detection
│   ├── brewfile_status.py   # read-only Brewfile drift (check + two-way diff)
│   ├── upgrade_plan.py      # read-only, plan-only gated upgrade sequence
│   └── README.md            # toolbox table + worked example + conventions
├── reference/
│   ├── find.md              # search -> dossier -> best-install decision
│   ├── setup.md             # install / restore from Brewfile / track it / initial gates
│   ├── repair.md            # brew doctor, broken links, missing deps, bad-upgrade recovery
│   ├── upgrade.md           # snapshot -> pin -> selective upgrade -> verify -> cleanup
│   ├── optimize.md          # inventory + detect auto-upgrade + pins + prune cruft
│   └── verification.md      # brew doctor + versions diff + drive affected tools
└── README.md                # (LICENSE lives at the gallery root)
```

## License

[MIT](../../LICENSE).
