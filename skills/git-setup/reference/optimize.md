# Optimize workflow — global git config health & gap report

Goal: review a working `~/.gitconfig` and tighten it — surface what's missing or risky and hand back
the exact fix for each. Report; change nothing without confirmation. Read everything from the real
config, with origins. (Signing that's on but **won't verify** is broken, not just a gap →
[repair.md](repair.md).)

> **Run [`scripts/git_audit.py`](../scripts/git_audit.py)** — it packages every check below into
> greppable `key<TAB>value` facts plus a gap report sorted 🔴 → 🟡 → 🟢, each with its fix command.
> The sections below are the under-the-hood reference for *reading* that report and judging severity.
>
> ```bash
> scripts/git_audit.py                 # full report
> scripts/git_audit.py | grep '^gap'   # just the prioritized gaps
> ```

```bash
git config --global --list --show-origin        # the source of truth for everything below
```

## 1. Commit signing (the highest-value gap)

```bash
git config --global --get commit.gpgsign             # true = sign every commit
git config --global --get gpg.format                 # "ssh" (preferred on macOS) or "openpgp"
git config --global --get user.signingkey            # ~/.ssh/id_ed25519.pub, or a GPG key id
git config --global --get gpg.ssh.allowedSignersFile # required for SSH signatures to *verify* locally
```
- No signing → 🟡 (commits show unverified on GitHub). Setting up SSH signing is the flagship fix
  ([setup.md](setup.md)).
- `commit.gpgsign=true` but `allowedSignersFile` unset → 🔴: commits are signed but **won't verify
  locally** (`git log --show-signature` says "No signature"/"unknown"). This is the classic
  half-configured trap — flag it loudly.

## 2. Pager

```bash
git config --global --get core.pager             # "delta" for readable diffs, else plain less
command -v delta                                 # installed?
```
`core.pager` unset or delta not installed → 🟢 recommend delta via Homebrew ([setup.md](setup.md)).

## 3. Sane defaults

```bash
for k in init.defaultBranch pull.rebase push.autoSetupRemote push.default \
         fetch.prune rebase.autostash core.excludesfile; do
  printf '%-24s %s\n' "$k" "$(git config --global --get "$k" || echo '(unset)')"
done
```
| Key | Recommended | Why |
|---|---|---|
| `init.defaultBranch` | `main` | avoids the `master` default |
| `pull.rebase` | `true` | linear history, no accidental merge commits on pull |
| `push.autoSetupRemote` | `true` | `git push` on a new branch just works |
| `push.default` | `simple` | push the current branch to its upstream, nothing else |
| `fetch.prune` | `true` | drop deleted remote-tracking branches automatically |
| `rebase.autostash` | `true` | auto-stash/pop around a rebase |
| `core.excludesfile` | `~/.gitignore_global` | global gitignore (below) |

Any unset → 🟡/🟢 depending on impact; list each with the exact `git config` to fix.

## 4. Aliases

```bash
git config --global --get-regexp '^alias\.'      # existing aliases (often empty)
```
Recommend a small, high-value set (see [setup.md](setup.md)): `st`, `co`, `br`, `lg` (a
graph log), `last`, `unstage`. 🟢.

## 5. Global gitignore

```bash
git config --global --get core.excludesfile      # points at the global ignore file?
cat "$(git config --global --get core.excludesfile 2>/dev/null)" 2>/dev/null
```
Unset → 🟡: `.DS_Store`, editor swap files, `.env`, etc. get committed per-repo. Recommend a global
ignore ([setup.md](setup.md)).

## 6. Credential helper (macOS)

```bash
git config --global --get credential.helper       # "osxkeychain" on macOS
```
Unset on Darwin → 🟡: HTTPS pushes re-prompt for a password every time. Recommend `osxkeychain`.

## 7. Identity

```bash
git config --global --get user.name
git config --global --get user.email
git config --global --get-regexp 'includeif'      # any per-directory identities set up?
```
One global email but the user has both work and personal repos → 🟡: propose conditional-include
identities ([identity.md](identity.md)).

## Report

Prioritized, each with the exact fix command:
- 🔴 **signing on but no `allowedSignersFile`** (signed yet unverifiable), or a private key path used
  where a `.pub` is required.
- 🟡 no signing at all / no credential helper on macOS / no global gitignore / mixed identities.
- 🟢 missing sane defaults, no aliases, no delta.

Offer to proceed with [setup.md](setup.md) (settings + signing + delta) and, if the user
has work+personal repos, [identity.md](identity.md). End by confirming with
[verification.md](verification.md).
