# Health workflow — whole-environment sweep

Goal: one prioritized report across every layer, by running each skill's **audit** (read-only) and
merging the results. Change nothing — propose fixes and hand each to its skill.

## Run each layer's audit (read-only)

Every layer skill now exposes its audit as a **read-only script** under `<skill>/scripts/` (they
resolve their own paths and print greppable output). Fastest sweep: run each skill's script by name.
Delegate for interpretation and fixes; don't re-implement the checks.

| Layer | Skill · read-only script | What it surfaces |
|---|---|---|
| Packages | **`brew-doctor`** · `scripts/brew_audit.py` | auto-updater mode, unpinned fragile formulae, `brew doctor`, outdated, orphans |
| Runtimes | **`runtime-versions`** · `scripts/detect_managers.py`, `scripts/shell_resolve.py` | which manager each tool resolves to per shell, nvm/asdf/pyenv sprawl, stale global versions |
| Dotfiles | **`dotfiles`** · `scripts/chezmoi_status.py`, `scripts/secret_scan.py` | `chezmoi status`/`doctor` drift, unmanaged configs, any secret in source (paths only) |
| Shells | **`shell-sync`** · `scripts/path_doctor.py`, `scripts/shell_diff.py` | PATH dupes/dead entries, installed-but-not-on-PATH, zsh↔fish divergence |
| Terminal | **`ghostty-config`** · `scripts/ghostty_doctor.py`, `scripts/font_check.py` | invalid/deprecated keys, macOS split-brain (`~/.config` edits ignored), font not resolving / tofu |
| Theme | **`terminal-theme`** · `scripts/theme_status.py` | a surface (starship/fish/zsh) on hardcoded hex that clashes with the Ghostty theme instead of inheriting it |
| Editor | **`nvim-config`** · `scripts/nvim_check.py startup`, `scripts/nvim_check.py deprecations` | startup errors, deprecated APIs, plugin breakage |
| Git | **`git-setup`** · `scripts/git_audit.py` | signing off/unverified, missing sane defaults, identity misresolution, gitignore gaps |
| SSH | **`ssh-config`** · `scripts/key-audit.py`, `scripts/ssh-config-audit.py` | key permissions/type, passphrase-less keys, agent identities, config hygiene |
| macOS prefs | **`macos-defaults`** · `scripts/drift_audit.py <macos.sh>` | live `defaults` values drifted from the declarative script |

Read `~/.config/devenv/config.toml` first so each audit uses the user's known settings (canonical
shell, pin list, the `macos-defaults` script path, etc.) instead of asking. Each script is the
skill's audit entrypoint — for anything ambiguous or for fixes, hand off to the skill itself.

## Merge into one report

Collect findings and present a single list, **sorted by severity across layers**, not per-skill:

- 🔴 broken / actively degrading (a red gate anywhere)
- 🟡 deprecated-but-works / drift / unpinned-fragile / missing-tool
- 🟢 cleanup / cosmetic

Each finding: **layer · what · where · the skill + workflow that fixes it**. Note cross-layer
interactions (e.g. a shell PATH change that would affect which `node` nvim's LSP uses).

## Offer fixes — via the owning skill

Group proposed fixes by skill so the user can approve a layer at a time. Apply only what's approved,
and let each skill run its own verification. Don't batch-apply across layers silently.

## Report

Top line: a one-glance status per layer
(`brew ✓ · runtimes ✓ · dotfiles ✓ · shells ⚠ · terminal ✓ · theme ✓ · nvim ✓ · git ✓ · ssh ✓ · macos ✓`), then the
prioritized findings, then the recommended next action.
