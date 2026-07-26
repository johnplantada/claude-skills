# Upgrade workflow — adopt newer git defaults and refresh tooling

Goal: keep a working setup current. git ships better defaults over time and old configs miss them;
this path checks your git version, adopts the newly-recommended settings you don't have yet, refreshes
the tooling (git, delta), and re-proves signing still verifies. Every `git config` is mutating —
propose each, confirm, back up `~/.gitconfig` first.

> Run [`scripts/git_audit.py`](../scripts/git_audit.py) first — it reports what's set vs. missing.
> This path adds the settings that became recommended *after* your config was written. A brand-new
> config is [setup.md](setup.md); a broken one is [repair.md](repair.md).

## 1. Check the version

```bash
git --version                        # newer git = more/better defaults available
command -v delta && delta --version  # pager tooling current?
```
Upgrade the binaries via the **brew-doctor** skill (`brew upgrade git git-delta`) — gated, so a git
bump doesn't surprise you. Then adopt the config below.

## 2. Adopt settings that became recommended (only those unset)

Each landed in a recent git; safe, high-value, and easy to miss on an older config. Set only the ones
`git_audit.py` shows unset:

| Setting | Value | Since | Why |
|---|---|---|---|
| `push.autoSetupRemote` | `true` | 2.37 | `git push` on a new branch just works — no `--set-upstream` |
| `merge.conflictStyle` | `zdiff3` | 2.35 | conflict markers show the common ancestor — far easier merges |
| `rebase.updateRefs` | `true` | 2.38 | rebasing a stack restacks the intermediate branches too |
| `fetch.prune` / `fetch.pruneTags` | `true` | — | drop deleted remote branches/tags automatically |
| `rerere.enabled` | `true` | — | remembers conflict resolutions and replays them |
| `init.defaultBranch` | `main` | 2.28 | avoids the legacy `master` default |
| `column.ui` | `auto` | — | columnar `git branch`/`status` output |

```bash
git config --global push.autoSetupRemote true
git config --global merge.conflictStyle zdiff3
git config --global rebase.updateRefs true
git config --global rerere.enabled true
# …only for keys git_audit.py reports unset — don't clobber a deliberate choice.
```

## 3. Migrate deprecated / superseded config

- A pinned `push.default` other than `simple` (the modern default) — drop it unless intentional.
- An old `[color] ui = always` (breaks piping) → `auto`.
- A GPG signing setup you've since replaced with SSH — remove the stale `gpg.format openpgp` /
  `user.signingkey <KEYID>` so it doesn't shadow the SSH key.

## 4. Re-prove nothing broke

```bash
scripts/verify_signing.py            # signing still yields status G after the changes
scripts/git_audit.py | grep '^gap'   # the newly-adopted gaps are gone
```
See [verification.md](verification.md). Then re-track `~/.gitconfig` via the **dotfiles** skill so the
refreshed config is reproducible.
