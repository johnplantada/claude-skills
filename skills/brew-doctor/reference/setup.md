# Set up workflow — a safe, reproducible Homebrew baseline

Goal: stand up Homebrew (or bring a new machine up to your declarative baseline) with the safety
rails in place from day one — a tracked Brewfile as the source of truth, fragile formulae pinned,
and the auto-updater tamed. Greenfield and new-machine restore both land here.

> Tightening an existing, working install (not standing one up)? → [optimize.md](optimize.md).
> Fixing a *broken* install? → [repair.md](repair.md).

## 1. Ensure Homebrew exists

```bash
brew --version        # already installed? skip to step 2
```
If absent, Homebrew's installer is an interactive, `sudo`-gated network script — it **can't** run
headlessly. Hand it to the user:
```
! /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Then have them add the shell hook (`eval "$(/opt/homebrew/bin/brew shellenv)"`) — or let the
`shell-sync` skill place it — and re-run `brew --version` to confirm it's on PATH.

## 2. Restore from a Brewfile (new machine) — or capture one (first time)

**New machine, Brewfile already tracked** → install everything it declares:
```bash
brew bundle --file=~/Brewfile          # taps, brews, casks, mas apps
```
Pairs with the `dotfiles` bootstrap: apply dotfiles first (that brings the Brewfile), then
`brew bundle`.

**First time, no Brewfile yet** → capture what's installed into the declarative record:
```bash
brew bundle dump --file=~/Brewfile     # taps, brews, casks, mas apps (with description comments)
# --force to overwrite an existing one (confirm first)
```
Recent Homebrew writes a description comment per entry by default (the old `--describe` switch is
deprecated — omit it). Review the file — it lists **all** leaves + casks + taps; prune anything you
don't want reproduced on a new machine.

## 3. Track it (ideally via chezmoi / the dotfiles skill)

A Brewfile belongs in version control next to the rest of your dotfiles:
```bash
chezmoi add ~/Brewfile         # if the dotfiles skill/chezmoi is set up
```
Otherwise commit it wherever you keep dotfiles. The Brewfile records formulae but **not pin state** —
note pinned formulae in a comment (pins are set next, and reviewed in [optimize.md](optimize.md)).

## 4. Set the initial safety gates

Establish the gates now, so the first unattended `brew upgrade` can't break a tool:
```bash
brew pin neovim                # pin version-sensitive tools: editors, LSPs, databases, runtimes
```
Confirm the pin list — seed it from `[brew-doctor].pinned` in `config.toml` when set. Then tame the
auto-updater to **update-only** (never an unattended `upgrade`); the mechanism, how to detect it,
and how to classify its mode are detailed in [optimize.md](optimize.md). Casks with a `sudo`
installer can't run headlessly — hand those to the user (`! brew install --cask <name>`).

## 5. Verify

```bash
brew bundle check --file=~/Brewfile     # "dependencies are satisfied" = Brewfile == reality
brew list --pinned                      # the fragile set you intended IS pinned
brew doctor                             # "Your system is ready to brew"
```
Brewfile committed, gates in place, `brew doctor` clean — see [verification.md](verification.md).
