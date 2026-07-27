# identity-profiles — the right you, in the right directory, on every surface

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that coordinates **who you are** per
directory tree — git identity, ssh key, commit signing, and gh account — so the correct one applies
automatically and no surface disagrees with the others. Its golden rule is **verification-first**:
it resolves every surface from inside a real repo in the tree and confirms they name the same
person, rather than reading four config files and assuming they compose.

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Declare work-vs-personal (or per-client) profiles and wire all four surfaces at once — an `includeIf` tree, a per-profile ssh `Host` alias, an `allowed_signers` pairing, and remotes that use the alias. |
| **repair** | Fix a mismatch — commits under the wrong email, a push that authenticated as the other account, or the second identity signing but showing **Unverified**. |
| **upgrade** | Add a profile, or rotate a key across every surface in the order that never leaves a gap. |
| **optimize** | Audit every declared tree for a surface that drifted, with a **prioritized gap report** (🔴/🟡). |

## Why it's different

Most work-vs-personal guides stop at `includeIf` — which fixes the *email* and leaves the two
failures that actually bite:

- **Right email, wrong key.** The tree resolves your work identity, but the remote's ssh alias
  offers your personal key, so the push authenticates as the wrong account. Only comparing the
  tree's signing key against `ssh -G`'s `identityfile` catches this — a comparison that spans two
  layers, so neither layer's own audit performs it.
- **Signed but Unverified, for the second identity only.** Each identity signs with its own key and
  needs its own `allowed_signers` pairing. Personal commits verify, work commits don't, and nothing
  says why.

This skill treats those two joins as its entire reason to exist. `profile_audit.py` checks them
across every declared profile in one pass, and reports `undetermined` — never a reassuring blank —
when an input was missing.

It also **declares profiles where the machine already declares them**: git's own `includeIf
"gitdir:"` rules are the source of truth, so the audit discovers profiles instead of asking you to
restate them in a settings file that could drift.

## Requirements

- **Claude Code**, plus **git** and **ssh**. macOS or Linux. `gh` is optional (its surface is
  reported as `undetermined` when absent).
- Scripts are **stdlib-only Python 3.9+** and read-only. The one network call
  (`profile_resolve.py --probe-remote`) is opt-in and carries a timeout.

## Safety

- **Private keys are never opened.** Key *paths* are compared as `ssh -G` reports them; only public
  halves (`*.pub`, `allowed_signers`) are ever read. Key generation, permissions, passphrases, and
  the agent belong to the **ssh-config** skill.
- **Global identity changes are confirmed first** — changing `user.email` globally silently
  re-attributes every future commit outside a declared tree.
- `~/.gitconfig` and `~/.ssh/config` are backed up before editing.

## Coordinates, doesn't duplicate

**git-setup** owns global git config, signing setup, and the git-only "which include file won"
question (`git_identity.py`). **ssh-config** owns keys and `Host` block hygiene. **dotfiles** tracks
the resulting files so the profile map survives the next machine. This skill owns only the mapping
between a tree and an identity, and the proof that every surface follows it.

Part of the [devenv](../../README.md) plugin.
