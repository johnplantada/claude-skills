---
name: Identity Profiles
description: Coordinate WHO YOU ARE per directory tree — git identity, ssh key, commit signing, and gh account — so the right one applies automatically and no surface disagrees. Use to SET UP work-vs-personal (or client) profiles across all four surfaces at once, REPAIR a mismatch (commits under the wrong email, pushes authenticating as the other account, signed-but-Unverified for the second identity), UPGRADE by adding a profile or rotating a key across every surface, or OPTIMIZE by auditing each declared tree for a surface that drifted. Verified by resolving every surface from inside a repo in the tree and proving they name the same person.
argument-hint: [setup|repair|upgrade|optimize]
allowed-tools: Bash(*identity-profiles/scripts/*), Bash(git config --get *), Bash(git config --global --get-regexp *), Bash(git config --list *), Bash(git -C * *), Bash(ssh -G *), Bash(ssh -o BatchMode=yes *), Bash(gh auth status), Bash(cat *), Bash(ls *)
---

# Identity profiles

Keep **git, ssh, commit signing, and gh** naming the same person in any given directory — one
identity per tree, applied automatically. The model is **derive, don't repeat**: a tree
(`~/work/`) is the single declaration, and every other surface is configured *once* to follow it.
**Move a repo into the tree → it gets the whole identity.**

The golden rule is **verification-first**: prove coordination by resolving every surface from
inside a real repo in that tree and confirming they agree — never by reading the config files and
assuming they compose.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Set up work-vs-personal (or per-client) profiles across all four surfaces | [reference/setup.md](reference/setup.md) |
| Fix a mismatch — wrong email committed, wrong account pushed, signed-but-Unverified | [reference/repair.md](reference/repair.md) |
| Add a profile, or rotate a key across every surface at once | [reference/upgrade.md](reference/upgrade.md) |
| Audit every declared tree for a surface that drifted | [reference/optimize.md](reference/optimize.md) |
| Prove the surfaces agree | [reference/verification.md](reference/verification.md) |

**No workflow named?** (a bare `/identity-profiles`) — **triage first:** run `scripts/profile_audit.py`:
- `profiles (none…)` → **setup** (nothing is declared yet).
- any 🔴 gap → **repair**.
- only 🟡 gaps → offer **optimize**.
- no gaps → report it and **stop**.

## The four surfaces, and who owns each

| Surface | Declares identity via | Owned by |
|---|---|---|
| **git** | `includeIf "gitdir:<tree>"` → a per-profile `.gitconfig` (email, name) | `git-setup` owns the mechanism; this skill owns which tree maps to which |
| **signing** | `user.signingkey` + a pairing line in `allowed_signers` | `git-setup` owns signing setup; this skill owns per-profile pairing |
| **ssh** | a `Host <alias>` block with its own `IdentityFile`; remotes use the alias | `ssh-config` owns keys and hygiene; this skill owns alias↔tree mapping |
| **gh** | the active `gh auth` account | this skill only reads it — `gh` account switching is the user's |

## The scripts (call these, don't re-derive them)

Read-only inspectors in [`scripts/`](scripts/README.md). The *mutation* is editing gitconfig
includes and `~/.ssh/config`; these are the audit and proof around it.

| Need | Script |
|---|---|
| Sweep every declared profile for cross-surface disagreement (**run first**) | `scripts/profile_audit.py` |
| Who am I in ONE directory, across git + ssh + gh at once | `scripts/profile_resolve.py [path]` |
| …and ask the host which account the key really authenticates as | `scripts/profile_resolve.py <path> --probe-remote` |

## Core principles

1. **The tree is the declaration.** One `includeIf "gitdir:"` rule per profile; everything else
   derives from it. Never set identity per-repo — that's the state this skill exists to remove.
2. **A profile is only real if every surface agrees.** The right email with the wrong key is not a
   working profile; it is a push that authenticates as someone else. `profile_audit.py` checks the
   join, which is the one thing neither `git-setup` nor `ssh-config` can see alone.
3. **Distinct keys need distinct pairings.** A second identity with its own signing key needs its
   own `allowed_signers` line, or its commits sign and show **Unverified**. This is the single most
   common failure and it is silent.
4. **ssh aliases, not hostnames.** Per-tree key selection only works when remotes point at a
   `Host` alias (`git@github-work:…`); an https remote bypasses key selection entirely.
5. **Prove it from inside the tree.** `includeIf "gitdir:"` only applies inside a real repo, so a
   check run anywhere else is measuring the wrong thing. Both scripts probe from a repo in the tree
   and say `undetermined` when they can't find one.

## Settings

Read `~/.config/devenv/config.toml`; if an `[identity-profiles]` section exists, use it as defaults
(precedence: explicit > config > ask). Managed by the `devenv` skill. Keys honored:
- `default` — the profile that applies outside any declared tree (e.g. `personal`).
- `probe_remote` — `true` to include the network probe in verification (default `false`).

The declarations themselves live in git's own config, not here: `git config --global --get-regexp
'^includeif\.'` is the source of truth, which is why `profile_audit.py` discovers profiles instead
of being told about them.

## Boundaries with the other skills

- **git-setup** owns global git config, signing setup, and `git_identity.py` (which include file
  won, for the git surface alone). This skill owns the *cross-surface* join. For a git-only
  question, use `git-setup` directly.
- **ssh-config** owns key generation, permissions, passphrases, and the agent. This skill never
  creates or inspects a private key — it only compares the **paths** ssh reports.
- **dotfiles** tracks the resulting files (`~/.gitconfig`, `~/.config/git/*.gitconfig`,
  `~/.ssh/config`) so profiles are reproducible on the next machine.

## Safety

- **Back up** `~/.gitconfig` and `~/.ssh/config` (timestamped copy) before editing either.
- **Confirm before changing a global identity.** Changing `user.email` globally silently
  re-attributes every future commit outside a declared tree.
- **Never write a private key path into a tracked file** beyond `~/.ssh/config`, and never move key
  material between machines through this skill — that's `ssh-config`'s keys workflow, out of band.
- `--probe-remote` makes a **network call** to a git host. It is opt-in, never part of the default
  audit, and it authenticates as you — don't run it against a host the user hasn't already used.
