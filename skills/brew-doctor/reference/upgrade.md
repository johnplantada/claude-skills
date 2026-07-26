# Upgrade workflow — gated, verified, reversible-as-possible

> **Start with [`scripts/upgrade_plan.py`](../scripts/README.md)** — it does steps 1–3 in one
> read-only call: snapshots versions to a temp file, classifies each outdated formula
> (already-pinned → auto-skipped; fragile/major-bump → **pin first**; else safe), and **prints
> the gated `brew pin`/`brew upgrade` sequence without running it**. Review its plan, then run the
> printed commands (steps 4–7). The inline commands below are what it plans and what you execute.

Goal: get current without getting broken. Homebrew rollback is limited, so gate the fragile things
and verify immediately.

## 1. Snapshot first

```bash
brew list --versions > /tmp/brew_versions.before     # so you know what to reinstall if needed
brew list --pinned                                   # current gates
```

## 2. Update metadata & review (no upgrades yet)

```bash
brew update                          # refresh formula/cask definitions (does NOT upgrade anything)
brew outdated --verbose              # what WOULD upgrade, current -> new versions
brew outdated --cask
```
Scan the list for **fragile / major-version** bumps — editors (neovim), language servers,
databases, runtimes. Those are the ones that break configs.

## 3. Gate the fragile ones

```bash
brew pin neovim                      # example: don't let this bump unattended
brew pin <other version-sensitive formulae>
```
Confirm the pin list with the user. Pinned formulae are skipped by `brew upgrade`. (Pinning is
formula-only; for a fragile cask, just omit it from the cask upgrade in the next step.)

## 4. Upgrade — selectively, not blind

```bash
# safe bulk: pinned formulae are automatically skipped
brew upgrade                         # upgrades everything not pinned
# or, more conservative — upgrade named formulae only:
brew upgrade <formula> <formula>
brew upgrade --cask <cask>           # casks individually; skip self-updating ones
```
Prefer named upgrades when something important is due for a major bump you're not ready to verify.

## 5. Verify immediately (the point of gating)

Right after upgrading, confirm nothing broke — see [verification.md](verification.md):
```bash
brew doctor
diff <(brew list --versions) /tmp/brew_versions.before   # what actually changed
```
For an editor/toolchain that upgraded, **drive it** (e.g. chain into the `nvim-config` skill's
headless verification, re-check `node`/`python` via the `shell-sync` reachability check). Catch
breakage now, while you remember what changed.

## 6. If something broke

Something broke on upgrade → **[repair.md](repair.md)** ("Recover from a broken upgrade"): pin +
reinstall a versioned formula, roll back via a tap commit, or fix forward through the tool's own
repair skill and pin it so it can't recur unattended.

## 7. Clean up

```bash
brew autoremove --dry-run && brew autoremove    # drop now-unused deps (confirm)
brew cleanup                                     # remove old downloaded versions/caches
```

## Report

What upgraded (the versions diff), what was pinned/gated, what broke and how it was resolved, and
whether an auto-upgrade mechanism still needs taming ([optimize.md](optimize.md)).
