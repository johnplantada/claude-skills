---
name: Git Setup
description: Set up, repair, upgrade, and optimize your GLOBAL git config — prove commits actually verify, not just that config is set. Use to SET UP recommended settings + SSH commit signing + delta + a global gitignore (and work-vs-personal identities via conditional includes), REPAIR a broken setup (commits signed but unverified, wrong identity resolving, HTTPS re-prompts), UPGRADE by adopting newer git defaults and refreshing tooling, or OPTIMIZE with a prioritized gap report against the live config. Verification-first: a test commit is made to prove signatures verify and identities resolve.
argument-hint: [setup|repair|upgrade|optimize]
allowed-tools: Bash(*git-setup/scripts/*), Bash(git config --get *), Bash(git config --list *), Bash(git config --global --list *), Bash(git config --global --get *), Bash(git log *), Bash(git -C * *), Bash(cat *), Bash(ls *), Bash(command -v *), Bash(uname *)
---

# Git setup

Audit and harden the user's **global** git configuration, and — the golden rule — **prove it
works**: a signed commit that actually verifies, an alias that runs, the right identity resolving in
a work directory. Setting config is not the finish line; **verification is**.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Apply recommended settings, signing, delta, gitignore (+ work/personal identity) | [reference/setup.md](reference/setup.md) |
| Fix a broken setup — signed-but-unverified, wrong identity, cred re-prompts | [reference/repair.md](reference/repair.md) |
| Adopt newer git defaults + refresh tooling | [reference/upgrade.md](reference/upgrade.md) |
| See what's set and what's missing/risky (prioritized gap report) | [reference/optimize.md](reference/optimize.md) |
| Confirm signing verifies / identity resolves | [reference/verification.md](reference/verification.md) |

Supporting reference (not a standalone path): **[reference/identity.md](reference/identity.md)** —
work-vs-personal identities via `includeIf` conditional includes, pulled in by **setup** and
**repair**.

## The scripts (call these, don't re-derive them)

`scripts/` is the tested toolbox — call a script by name instead of re-deriving the same
`git config --global --get` probes or the throwaway-repo signing dance each session. Full table +
conventions in [scripts/README.md](scripts/README.md). All read-only except where noted.

| Script | Use it to… |
|---|---|
| `scripts/git_audit.py` | **Run first.** Whole global config as `key<TAB>value` facts + a gap report sorted 🔴 → 🟡 → 🟢, each with its fix command. |
| `scripts/git_identity.py [path]` | Which identity + signing key **resolves** in a directory (evaluates `includeIf` as git sees it) and the file each value came from. |
| `scripts/verify_signing.py [--self-test\|--key <pub>]` | **PROVE** a signature verifies — a test commit in a throwaway repo it owns and cleans up (never a real repo). `--self-test` proves the pipeline with an ephemeral key; no flag reflects your real global state. |

```bash
scripts/git_audit.py                 # discovery + gap report — always run first
scripts/git_audit.py | grep '^gap'   # just the prioritized gaps
```

Under the hood, discovery is these read-only commands (the script just packages them):

```bash
git --version
git config --global --list --show-origin       # the whole global config + where each value lives
uname -s                                        # Darwin -> prefer SSH signing + osxkeychain
git config --global --get commit.gpgsign        # signing on? (empty = off)
git config --global --get core.pager            # delta? (empty = plain)
ls ~/.gitconfig ~/.config/git/ 2>/dev/null      # main config + any conditional-include files
command -v delta                                # pager installed?
```
- **`--show-origin`** tells you *which* file a value comes from — the key to understanding
  conditional-include (per-directory) identities. Don't assume; read it each time.
- macOS (`Darwin`) → prefer **SSH commit signing** and the **osxkeychain** credential helper.

## Core principles

1. **Verify, don't assume.** Prove a signed commit verifies (`git log --show-signature`), an alias
   runs, and the right identity resolves per directory — see [reference/verification.md](reference/verification.md).
2. **Global scope, deliberate changes.** This skill hardens `~/.gitconfig`. **Back it up before
   edits**; confirm before changing signing, identity, or email.
3. **Signing affects "Verified" on GitHub.** Changing `gpg.format` / `user.signingkey` changes
   whether commits show as verified — treat it as a gated change, not a default.
4. **Read the real config each time.** `git config --global --list --show-origin`, not memory.

## Settings

Read `~/.config/devenv/config.toml` before prompting; if a `[git-setup]` section exists, use it as
defaults (precedence: explicit answer this session > `config.toml` > ask). Had to ask? Offer to save
the answer back. Managed by the `devenv` skill. Keys honored:
- `signing` — commit signing method: `"ssh"` (preferred on macOS), `"gpg"`, or `"none"`.
- `pager` — diff pager: `"delta"` or `"less"`.
- `identities` — map of directory → email, e.g. `{ "~/work/" = "you@work.example", "~/personal/" = "you@personal.example" }`, driving the per-directory conditional includes.

## Cross-skill coherence

- **ssh-config** — SSH commit signing reuses an SSH key; coordinate so `user.signingkey` points at
  the right `~/.ssh/*.pub` and the `allowedSignersFile` maps that email → public key.
- **dotfiles** — track `~/.gitconfig` and the `~/.config/git/*.gitconfig` identity files via chezmoi.
- **dotfiles (secrets)** — **NEVER** commit a private signing key. The SSH **public** key and the
  `allowedSigners` file are safe to track; the private key is not.

## Safety

- **Never commit private signing keys.** Public key + allowedSigners only.
- **Back up `~/.gitconfig`** before editing (`cp ~/.gitconfig ~/.gitconfig.bak`).
- Changing signing config affects whether commits show as **Verified** on GitHub — confirm first.
- Confirm before altering global **identity / email**; a wrong `user.email` misattributes commits.
- Writing config is **mutating** — this skill's pre-approved tools are read-only; each
  `git config --global <key> <val>` is proposed and run with the user's confirmation.
