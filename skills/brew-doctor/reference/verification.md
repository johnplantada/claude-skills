# Verification — prove brew is healthy and upgrades didn't break anything

> **[`scripts/brew_audit.py`](../scripts/README.md)** re-runs the health/pins/autoupdate checks
> below in one call (`brew_audit.py pins`, `brew_audit.py autoupdate`, or the full report);
> `scripts/brewfile_status.py` confirms the Brewfile is honest. The inline commands are the
> under-the-hood detail and the per-tool drive-it checks the scripts don't cover.

## Health

```bash
brew doctor                                  # "Your system is ready to brew" or a list to address
brew missing                                 # formulae with missing dependencies
```

## Gates are in place

```bash
brew list --pinned                           # fragile formulae you intended to pin ARE pinned
brew autoupdate status 2>/dev/null           # auto-upgrade is off, or update-only (not upgrading)
```
If the goal was "stop silent upgrades," confirm the mechanism is actually tamed — not just that
you meant to.

## What actually changed (after an upgrade)

```bash
diff <(brew list --versions) /tmp/brew_versions.before    # exact version deltas
```
Nothing surprising should have moved — especially nothing you pinned.

## Brewfile is honest

```bash
brew bundle check --file=~/Brewfile          # "dependencies are satisfied" = Brewfile == reality
```

## Affected tools still work (the real test)

A green `brew doctor` doesn't mean your tools work — an upgraded tool can break at runtime. For
anything version-sensitive that upgraded, exercise it:
- **editor** (neovim upgraded) → drive it headless / chain into the `nvim-config` skill's verify.
- **runtimes** (node/python/go) → `command -v` + a version check in each shell (the `shell-sync`
  reachability check).
- **CLIs/servers** → run the tool's own `--version` / a smoke command.

Catch breakage here, immediately after the upgrade, while the cause is known.
