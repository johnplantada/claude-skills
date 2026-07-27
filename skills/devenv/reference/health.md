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
| Identity | **`identity-profiles`** · `scripts/profile_audit.py` | a declared tree whose surfaces disagree — right email but the alias offers the wrong ssh key, or an identity signing without an `allowed_signers` pairing (commits show Unverified) |
| Credentials | **`credential-store`** · `scripts/credential_audit.py`, `scripts/store_status.py` | a credential held as a literal on disk rather than referenced from a store — shell rc exports, `~/.aws/credentials`, `~/.netrc`, a cleartext git helper, a gh token in a file (findings name variables and paths, never values) |
| SSH | **`ssh-config`** · `scripts/key_audit.py`, `scripts/ssh_config_audit.py` | key permissions/type, passphrase-less keys, agent identities, config hygiene |
| macOS prefs | **`macos-defaults`** · `scripts/drift_audit.py <macos.sh>` | live `defaults` values drifted from the declarative script |

Read `~/.config/devenv/config.toml` first so each audit uses the user's known settings (canonical
shell, pin list, the `macos-defaults` script path, etc.) instead of asking. Each script is the
skill's audit entrypoint — for anything ambiguous or for fixes, hand off to the skill itself.

## Sanity-check a surprising finding BEFORE reporting it

An audit script's output is evidence, not a verdict. Two failure modes have produced
confidently wrong findings, and both are cheap to catch if you pause on surprise:

- **A fact measured in the wrong environment.** Shell activation, PATH order, and
  anything an rc file sets do not exist inside a non-interactive process. A script that
  reports `mise not activated` while `mise activate` is plainly in `~/.zshrc` is
  describing its own subprocess, not the machine. Facts tagged `src=this-process` are
  the ones to distrust; `src=login-shell` is the real answer. `undetermined` means the
  check could not run — never read it as a pass.
- **A parser meeting an unfamiliar format.** An `unparsed` row means the tool printed a
  variant the script does not know; findings computed nearby are suspect. Casks print
  `!=` where formulae print `<`; a plugin manager prints commit subjects that contain
  the words "error" and "deprecated".

So: when a finding contradicts what the config visibly says, **verify it a second way
before it reaches the user** — read the rc file, run the check inside
`zsh -l -i -c '…'`, or run the underlying tool by hand. A false positive costs the user
a real fix to a working system, which is worse than a missed finding: it spends their
trust and their time. Report what you verified, and say which findings you could not
confirm rather than upgrading a guess to a fact.

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
(`brew ✓ · runtimes ✓ · dotfiles ✓ · shells ⚠ · terminal ✓ · theme ✓ · nvim ✓ · git ✓ · identity ✓ · creds ✓ · ssh ✓ · macos ✓`), then the
prioritized findings, then the recommended next action.
