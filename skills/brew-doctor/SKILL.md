---
name: Brew Doctor
description: Set up, repair, upgrade, and optimize Homebrew safely — so an auto-upgrade never silently breaks your tools. Use to FIND the best install for a need (search formulae/casks, compare, and choose formula vs cask vs a runtime manager), SET UP a reproducible brew (install, a declarative Brewfile, initial pins + a tamed auto-updater), REPAIR a broken one (`brew doctor` errors, broken links, missing deps, a bad upgrade), UPGRADE with gates (pin fragile formulae, upgrade selectively, verify), or OPTIMIZE a working one (detect & tame silent auto-upgrade, pin fragile formulae, prune orphans, keep the Brewfile honest). Every change is verified before it's called done.
argument-hint: [find|setup|repair|upgrade|optimize]
allowed-tools: Bash(brew leaves *), Bash(brew list *), Bash(brew outdated *), Bash(brew doctor), Bash(brew missing), Bash(brew config), Bash(brew search *), Bash(brew desc *), Bash(brew tap), Bash(brew deps *), Bash(brew uses *), Bash(brew info *), Bash(brew bundle check *), Bash(brew bundle list *), Bash(brew autoupdate status), Bash(brew autoremove --dry-run), Bash(ls *), Bash(git -C * *), Bash(*brew-doctor/scripts/*)
---

# Brew doctor

Keep Homebrew healthy and, above all, **prevent silent auto-upgrades from breaking your tools**.
Homebrew rollback is hard, so this skill leans on **prevention**: pin fragile formulae, gate
upgrades, and keep a declarative Brewfile as the source of truth.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Search for a tool / decide *what* to install and *how* (the best install for their situation) | [reference/find.md](reference/find.md) |
| Stand up Homebrew / restore a machine from a Brewfile / set the initial gates | [reference/setup.md](reference/setup.md) |
| Fix a broken brew — `doctor` errors, broken links, missing deps, a bad upgrade | [reference/repair.md](reference/repair.md) |
| Update packages without breaking things | [reference/upgrade.md](reference/upgrade.md) |
| Review a working setup and make it safer/leaner — audit, pin, prune (a.k.a. "audit") | [reference/optimize.md](reference/optimize.md) |

## The scripts (prefer these over ad-hoc bash)

Stable, tested helpers live in [`scripts/`](scripts/README.md) — **call them instead of
re-composing brew pipelines each session.** Run by absolute path from this skill's directory.
They resolve the Brewfile path and fragile/pinned set from `config.toml` internally.

| Need | Script |
|---|---|
| Search + info + **best-install advice** for a need or a name (formula vs cask vs mise, arch, pins) | `scripts/brew_find.py <term\|name>` |
| Health & risk report — inventory, pins, **auto-upgrade mode detection**, cruft (**run first** for setup/repair/upgrade/optimize) | `scripts/brew_audit.py [section]` |
| Brewfile drift — `bundle check` gaps + what would install / prune | `scripts/brewfile_status.py [--file PATH]` |
| Gated upgrade **plan** — classify outdated, pin fragile first, print (don't run) the commands | `scripts/upgrade_plan.py` |

All four are read-only; `upgrade_plan.py` *prints* the `brew pin/upgrade/cleanup` sequence but
never runs it, and `brew_find.py` only searches/inspects. Full contract + a worked example:
[scripts/README.md](scripts/README.md).

## Discovery (always run first)

`scripts/brew_audit.py` prints all of this as `key<TAB>value` lines (env, inventory, pins,
autoupdate mode, outdated, orphans, `brew doctor`). Under the hood it runs:

```bash
brew --version | head -1; brew --prefix
brew leaves | wc -l; brew list --cask | wc -l; brew tap        # inventory
brew list --pinned                                             # what's gated (empty = nothing!)
brew outdated                                                  # what would upgrade
brew autoupdate status 2>/dev/null                             # is a background auto-upgrade running?
ls ~/Library/LaunchAgents 2>/dev/null | grep -i brew           # launchd auto-upgrade agents
```
- **`brew leaves`** = top-level, explicitly-installed formulae → the basis of a minimal Brewfile.
- **Auto-upgrade mechanisms** (the `domt4/autoupdate` tap / `brew autoupdate`, or a launchd agent)
  are the #1 cause of "it broke by itself." `brew_audit.py` detects them **and classifies the
  mode** (`brew upgrade` = hazard vs `brew update` = safe) — see [reference/optimize.md](reference/optimize.md).

## Core principle: gate fragile upgrades

The hazard is a background `brew upgrade` bumping a tool whose config breaks on the new major
version (e.g. **neovim** 0.11→0.12 breaking treesitter). Defenses, in order:

1. **Pin fragile formulae** — `brew pin neovim` (and anything whose config is version-sensitive:
   editors, language servers, databases). `brew upgrade` skips pinned formulae.
2. **Tame auto-upgrade** — configure `brew autoupdate` to *update + notify*, NOT auto-`upgrade`;
   or remove it and upgrade deliberately. See [reference/optimize.md](reference/optimize.md).
3. **Upgrade selectively and verify** — never mass-`brew upgrade` blind; see
   [reference/upgrade.md](reference/upgrade.md).

## Core principles

1. **Verify after upgrading.** Homebrew rollback is limited, so catch breakage immediately: after
   an upgrade, confirm affected tools still work (for editors/toolchains, drive them — chain into
   the relevant skill's verify). See [reference/verification.md](reference/verification.md).
2. **Brewfile is the declarative record.** Track it (ideally via the `dotfiles`/chezmoi skill) so a
   machine is reproducible and drift is visible.
3. **Snapshot before upgrading.** Record current versions so you know what to reinstall if a
   versioned formula (`foo@x`) lets you downgrade.
4. **Don't assume inventory.** Read `brew leaves`/`brew list`/`brew outdated` each time.

## Settings

Read `~/.config/devenv/config.toml` before prompting; if a `[brew-doctor]` section exists, use it as
defaults (precedence: explicit answer this session > `config.toml` > ask). Had to ask? Offer to save
the answer back. Managed by the `devenv` skill. Keys honored:
- `pinned` — fragile formulae to keep pinned (never auto-bumped).
- `brewfile` — path to the declarative Brewfile.
- `autoupdate_mode` — the expected auto-updater mode; warn if it becomes `upgrade`.

## Safety

- **Rollback is hard in Homebrew.** Prevention > cure: pin fragile things, upgrade selectively.
- Confirm before `brew upgrade`, `brew bundle cleanup` (uninstalls), `brew autoremove`, or removing
  an auto-upgrade agent — show exactly what changes first.
- Some **casks run a `sudo` installer script** (driver/system apps) and need an interactive
  terminal for the admin password — they **cannot** be installed headlessly (`sudo: a terminal is
  required`). Hand these to the user (`! brew install --cask <name>`), then do the follow-up
  (removing an old cask, re-dumping the Brewfile) after they've completed it.
