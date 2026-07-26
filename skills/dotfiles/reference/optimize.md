# Optimize workflow — review and tighten the dotfiles source

Goal: the dotfiles work — now make the source cleaner and safer: configs worth adding that aren't
tracked yet, cruft that shouldn't be, plaintext that should be encrypted/templated, and per-machine
values that should be templated. Review and report; change nothing without confirmation.

> **Read-only inspectors:** `scripts/dotfiles_inventory.py --unmanaged` (managed + add-candidates),
> `scripts/secret_scan.py` (plaintext-secret hygiene — **paths + reason only, never values**),
> `scripts/chezmoi_status.py` (health). A genuinely *broken* state is [repair.md](repair.md).

## 1. Coverage — what's not tracked yet

```bash
scripts/dotfiles_inventory.py --unmanaged     # managed files + unmanaged add-candidates in $HOME
```
Config that lives only on this machine is a reproducibility gap — add the ones worth carrying
([upgrade.md](upgrade.md)), leave machine-local ones out via `.chezmoiignore`. Don't add blindly:
screen each with `secret_scan.py <path>` first.

## 2. Cruft — what shouldn't be tracked

Look for files that got swept in by a broad `chezmoi add <dir>`: caches, `*.bak`, auto-generated
state (`fish_variables`), another tool's regenerated files (e.g. `conf.d/00-shell-sync.fish`, owned
by the `shell-sync` skill). Move them to `.chezmoiignore` so they stop churning the repo.

## 3. Secret hygiene — plaintext that should be protected

```bash
scripts/secret_scan.py                         # exit 0 clean; exit 1 = paths + reason to fix
```
Any `content:*` or `location:*` finding is a plaintext secret or a secret-by-location file stored
raw — convert it to `encrypted_*.age` or a password-manager template ([secrets.md](secrets.md)).
This is the highest-priority tightening: a leaked secret in a (even private) repo is the top hazard.

## 4. Templating — per-machine values hardcoded

A managed file with a hostname, path, or OS-specific value baked in should be a `.tmpl`
(`{{ .chezmoi.hostname }}`, `{{ .chezmoi.os }}`) so it renders correctly on every machine instead of
carrying one host's value everywhere.

## 5. Report — prioritized

- 🔴 **plaintext secret / secret-by-location file** in source → encrypt or template now.
- 🟡 untracked config worth carrying; cruft that should be ignored; a public repo that should be
  private (`chezmoi_status.py` `source_remote`).
- 🟢 hardcoded per-machine values that would be cleaner as templates.

Each with the exact next step; converging is [upgrade.md](upgrade.md) / [secrets.md](secrets.md).
