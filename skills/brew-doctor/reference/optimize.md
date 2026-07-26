# Optimize workflow — review a healthy brew and make it safer & leaner

> **Run [`scripts/brew_audit.py`](../scripts/README.md) first** — it prints every fact below
> (inventory, pins, auto-upgrade mode, cruft, `brew doctor`) as greppable `key<TAB>value` lines.
> Scope with a section arg: `brew_audit.py autoupdate` · `inventory` · `pins` · `cruft`. The
> inline commands here are what it runs under the hood, for reference and one-off checks.

Goal: take a **working** Homebrew and reduce its risk and cruft — surface silent-upgrade
mechanisms, pin the fragile things, prune orphans, and keep the Brewfile honest. This is the
audit-and-harden path. Report; change nothing without confirmation. (Something actually *broken*
— `doctor` errors, missing deps, a bad upgrade? → [repair.md](repair.md).)

## 1. Inventory

```bash
brew leaves                      # top-level, explicitly installed (the Brewfile basis)
brew list --formula | wc -l      # total incl. dependencies
brew list --cask                 # GUI apps
brew tap                         # extra taps (each is extra trust + update surface)
```

## 2. 🔴 Detect silent auto-upgrade mechanisms (the top hazard)

`brew_audit.py autoupdate` does this whole sweep — it finds the tap/launchd agents/cron and, for
each agent, resolves the program it runs and **classifies the mode** (`brew upgrade` = hazard vs
`brew update` = safe). The commands below are what it runs under the hood.

An automatic `brew upgrade` is why tools "break by themselves." But **detecting a mechanism is not
the same as it upgrading** — you must determine its *mode*. Many setups run `brew update`
(metadata only, harmless) + a notification, NOT `brew upgrade`.

```bash
brew tap | grep -i autoupdate                            # the domt4/autoupdate tap
ls ~/Library/LaunchAgents 2>/dev/null | grep -i brew     # launchd agents that run brew on a timer
launchctl list 2>/dev/null | grep -i 'brew\|autoupdate'  # loaded?
crontab -l 2>/dev/null | grep -i brew                    # cron entries
```
**Then inspect what the agent actually runs** — the plist usually calls a wrapper script, so the
`--upgrade` decision is in the *script*, not the plist:
```bash
# read the Program / ProgramArguments target, then read THAT file:
cat ~/Library/LaunchAgents/com.github.domt4.homebrew-autoupdate.plist
cat "$HOME/Library/Application Support/com.github.domt4.homebrew-autoupdate/brew_autoupdate"
# does it run `brew upgrade` (dangerous) or just `brew update` (safe)?
```
- Runs **`brew upgrade`** → the real hazard. Recommend reconfiguring to update-only
  (`brew autoupdate delete`, then `brew autoupdate start` **without** `--upgrade`), or **pin
  fragile formulae** so critical tools are never bumped unattended.
- Runs **`brew update`** only → note it's **safe** and move on; don't misattribute past breakage to
  it. A tool that got bumped anyway was upgraded some other way (manual `brew upgrade`, or pulled
  up as a dependency) — pinning still helps.

## 3. Pins & fragile formulae

```bash
brew list --pinned               # what's gated (often empty — a risk)
```
Recommend pinning version-sensitive tools whose config breaks on major bumps: **editors**
(neovim/vim), **language servers**, **databases** (postgres/mongodb), and anything the user has
had break before. Pinning is a proposal — confirm before `brew pin`.

## 4. Cruft & health

```bash
brew outdated                    # pending upgrades (run `brew update` first for fresh data)
brew autoremove --dry-run        # unused dependencies that could be removed
brew doctor                      # config problems, broken symlinks, etc.
brew list --cask | while read c; do brew info --cask "$c" 2>/dev/null | grep -q 'auto_updates true' && echo "$c self-updates"; done
```
Casks with `auto_updates true` update themselves (brew won't manage their version) — note them so
their drift isn't mistaken for something to fix.

## 5. Report

Prioritized: 🔴 active auto-upgrade with nothing pinned → 🟡 fragile formulae unpinned / lots of
orphans / `brew doctor` warnings → 🟢 old versions to clean. Each with the exact command to fix.
Offer to proceed with pinning + taming auto-upgrade (the highest-value fixes), and to capture or
refresh the declarative Brewfile ([setup.md](setup.md)).
