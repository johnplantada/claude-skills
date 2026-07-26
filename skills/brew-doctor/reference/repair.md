# Repair workflow — fix a broken Homebrew

Goal: get a broken or misbehaving Homebrew back to healthy — `brew doctor` warnings, broken
links/permissions, missing dependencies, a bad tap, or a tool an upgrade just broke. Diagnose
first, change the narrowest thing, then prove it with `brew doctor` **and by driving the tool**.

> **Run [`scripts/brew_audit.py`](../scripts/README.md) first** (or `brew_audit.py cruft`) — it
> reports `brew doctor`, orphans, and inventory as greppable lines. Fix the cause, not just the
> symptom: many "broke by itself" cases are an unattended `brew upgrade`, so after repairing, tame
> the mechanism ([optimize.md](optimize.md)) — a repair that leaves the trigger armed will bite again.

## 1. Diagnose

```bash
brew doctor            # config problems, broken symlinks, unlinked kegs, permission issues
brew missing           # formulae with missing dependencies
brew config            # prefix, versions, PATH — sanity of the install itself
```
Read the actual messages — `brew doctor` names the exact fix (relink, remove, chown) most of the
time. Don't run remediations blind.

## 2. Common repairs

```bash
brew link --overwrite <formula>                  # "not linked" / conflicting symlinks (doctor names them)
brew reinstall <formula>                          # a formula whose files are corrupt or half-removed
brew install <dep>                                # satisfy what `brew missing` reports
brew untap <bad/tap>                              # a tap that 404s or fails to update (confirm first)
sudo chown -R "$(whoami)" "$(brew --prefix)"/*    # prefix permission errors (doctor flags these)
```
Each is a proposal — confirm before running anything mutating. Prefer the narrowest fix `brew
doctor` points to over a broad reinstall.

## 3. Recover from a broken upgrade

An upgrade bumped a tool across a major version and broke its config (the classic: **neovim
0.11→0.12** breaking treesitter). Homebrew rollback is limited — options, best first:

- **Pin + reinstall a versioned formula** if one exists: `brew install <formula>@<major>` (e.g.
  `node@18`), then repoint/relink.
- **Reinstall the prior version** from a specific tap commit (advanced): check out the old formula
  in `$(brew --repository)/Library/Taps/…` and `brew reinstall`.
- If neither is feasible, **fix forward** via the tool's own repair skill (the usual outcome —
  e.g. chain into `nvim-config` repair), then **pin** it so it can't recur unattended.

## 4. Stop it recurring

If the breakage came from an unattended upgrade, the fix isn't done until the trigger is disarmed:
detect the auto-updater and its mode, then reconfigure it to update-only or pin the fragile set —
see [optimize.md](optimize.md).

## 5. Verify

```bash
brew doctor            # back to "ready to brew" (or only known-benign warnings)
brew missing           # empty
```
A green `brew doctor` isn't proof the tool runs — **drive the tool that was broken** (headless
nvim, a runtime `--version` in each shell, a CLI smoke command). See [verification.md](verification.md).
