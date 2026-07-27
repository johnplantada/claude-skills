---
name: Credential Store
description: Get every credential OFF this machine's disk and into one store — so shell rc files, git, gh, and tool configs REFERENCE a secret at use time instead of embedding it. Use to SET UP a store and migrate literal tokens into it, REPAIR a reference that stopped resolving (locked store, empty variable, non-interactive shell), UPGRADE by rotating a credential or moving to a better store, or OPTIMIZE by auditing every surface for plaintext. A secret's VALUE never enters the model's context — detection reports names, paths, and classifications only, and every operation needing real plaintext runs out of band.
argument-hint: [setup|repair|upgrade|optimize]
allowed-tools: Bash(*credential-store/scripts/*), Bash(git config --global --get credential.helper), Bash(gh auth status), Bash(security list-keychains), Bash(op account list*), Bash(command -v *), Bash(ls -la *), Bash(stat *)
---

# Credential store

One store holds every secret; **everything else references it**. A shell rc line reads
`export GITHUB_TOKEN="$(security find-generic-password -s GITHUB_TOKEN -w)"` — not the token. The
credential lives in exactly one place, rotating it is a one-line change, and nothing readable on
disk is worth stealing.

The golden rule is **verification-first**: prove a migration by resolving the value in a fresh
login shell *and* confirming the plaintext is gone — never by editing the rc file and assuming.

## The hard control — a secret's value never enters this session

> **Never read, print, `cat`, `grep -o`, or echo a credential's value.** This holds *after* a
> finding too: never open a flagged file to "confirm what tripped it" — the `path + name +
> classification` row is the complete evidence, and one confirmation read defeats the entire
> pipeline. The scripts are built so this is structural, not careful: `scan_assignments` classifies
> a value and **discards** it, so a finding physically cannot carry one.
>
> Operations that need real plaintext — writing a secret into the store, unlocking a manager,
> copying a token — **run out of band**: the user runs them (e.g. via the `!` prefix), or the value
> is piped between tools without passing through a report. For files that are secret by *location*,
> the plugin's `PreToolUse` guard (`scripts/secret_read_guard.py`) enforces this mechanically —
> treat a denial as the contract working.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Pick a store and migrate literal credentials into it | [reference/setup.md](reference/setup.md) |
| Fix a reference that stopped resolving (empty var, locked store, non-interactive shell) | [reference/repair.md](reference/repair.md) |
| Rotate a credential, or move to a different store | [reference/upgrade.md](reference/upgrade.md) |
| Audit every surface for plaintext, with a prioritized report | [reference/optimize.md](reference/optimize.md) |
| Prove a migrated secret resolves and the plaintext is gone | [reference/verification.md](reference/verification.md) |

**No workflow named?** (a bare `/credential-store`) — **triage first:** run `scripts/credential_audit.py`:
- any 🔴 → **setup** if no store exists yet, else **repair**/migrate.
- only 🟡 → offer **optimize**.
- no findings → report it and **stop**.

## The four surfaces

| Surface | Where a credential hides | Reference form |
|---|---|---|
| **shell** | `export FOO_TOKEN=…` in a zsh/fish rc — also exported into every process you launch | `$(security find-generic-password -s FOO -w)` / `$(op read …)` |
| **files** | `~/.aws/credentials`, `~/.netrc`, `~/.npmrc`, `~/.git-credentials` — plaintext by location | a store-backed `credential_process`, or delete + reference |
| **git** | `credential.helper=store` writes `~/.git-credentials` in cleartext | `credential.helper=osxkeychain` |
| **gh** | a token in `~/.config/gh/hosts.yml` instead of the keyring | `gh auth login` with keyring storage |

## The scripts (call these, don't re-derive them)

Read-only inspectors in [`scripts/`](scripts/README.md). The *mutation* — writing a secret into a
store and editing the rc line — is done by the user, out of band.

| Need | Script |
|---|---|
| Sweep every surface for plaintext (**run first**) | `scripts/credential_audit.py` |
| Just the shell rc sweep, fast | `scripts/credential_audit.py --shell-only` |
| A **redacted** inventory of every assignment, for reviewing what the name heuristic missed | `scripts/credential_audit.py --all-assignments` |
| Which stores exist here, and the reference form for the recommended one | `scripts/store_status.py` |

## Core principles

1. **Literal vs. reference is the whole question.** Not "is there a secret" (that's `dotfiles`'
   pre-commit tripwire) but "is this value *on disk*, or fetched at use time." `credential_audit.py`
   classifies every credential-shaped assignment into exactly that.
2. **A finding names, never quotes.** Variable names, file paths, line numbers, and modes are
   metadata and are reported — they're what makes a finding actionable. Values are not.
3. **A store you can't use is not a store.** Never recommend a destination `store_status.py` reports
   as absent; a migration into a store the machine can't reach just breaks the shell.
4. **Migrate one credential at a time, verifying each.** A batch migration that half-works leaves a
   shell that can't authenticate and no clear culprit.
5. **Deleting the plaintext is part of the migration.** A secret copied into a store but left in the
   rc file is strictly worse than before — now it's in two places.

## Settings

Read `~/.config/devenv/config.toml`; if a `[credential-store]` section exists, use it as defaults
(precedence: explicit > config > ask). Managed by the `devenv` skill. Keys honored:
- `store` — the destination store (`keychain`, `1password`, `pass`, `chezmoi-encryption`).
- `allow_file_reference` — `true` to accept `$(cat …)` as adequate (default `false`).

## Boundaries with the other skills

- **dotfiles** owns secrets in the chezmoi **source tree** — the pre-commit question, plus `age`
  encryption and password-manager templating ([secrets.md](../dotfiles/reference/secrets.md)). This
  skill owns the **live machine**: what's in the rc files and config files you actually use. When a
  file needs to be both tracked and secret, migrate it here, then track it there.
- **ssh-config** owns private keys, passphrases, and the agent. A private key is not migrated into a
  credential store — it stays in `~/.ssh` with correct modes.
- **git-setup** owns `credential.helper` as a git setting; this skill flags it when the chosen
  helper stores cleartext.
- **shell-sync** owns the rc files' structure and zsh↔fish parity; this skill only changes the
  right-hand side of a credential assignment, and a migrated line must be mirrored to both shells.

## Safety

- **Back up** any rc file before editing it (timestamped copy).
- **Never delete a plaintext credential until the reference is proven to resolve.** Order:
  store it → switch the line → verify in a new login shell → *then* remove the original.
- **A rotation invalidates the old value everywhere.** Enumerate what consumes it before rotating.
- Never run a store CLI in a way that prints a secret (`op read` into a report, `security … -w`
  captured for display, `gh auth token`). Their output goes into the environment, not into a message.
