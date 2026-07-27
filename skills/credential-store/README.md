# credential-store — every secret in one store, everything else a reference

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that gets credentials **off your
disk** and into a single store, so shell rc files, git, gh, and tool configs *reference* a secret at
use time instead of embedding it. Its golden rule is **verification-first**: a migration is proven
by resolving the value in a fresh login shell *and* confirming the plaintext is gone — never by
editing a config and assuming.

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Pick a usable store, migrate literal credentials into it one at a time, and delete the plaintext — with the value never passing through the model. |
| **repair** | Fix a reference that stopped resolving: a locked store, a wrong item name, an rc file a non-interactive shell never sources, or a shell startup that got slow. |
| **upgrade** | Rotate a credential (enumerate consumers, update one store item, verify, *then* revoke), or move to a different store safely. |
| **optimize** | Audit every surface for plaintext with a **prioritized report** (🔴/🟡/🟢). |

## Why it's different

Most "don't commit secrets" tooling answers one question: *is a secret about to enter git?* That's a
pre-commit tripwire, and this repo already has one in [dotfiles](../dotfiles/reference/secrets.md).
This skill asks the question nobody owns — **on the machine you actually use, is each credential a
literal on disk, or a reference resolved at use time?**

That distinction is the entire skill, and it's the one a grep can't make:

```bash
export GITHUB_TOKEN=ghp_realTokenOnDisk          # 🔴 literal — readable by anything, and
                                                 #    exported into every process you launch
export GITHUB_TOKEN="$(security find-generic-password -s GITHUB_TOKEN -w)"   # 🟢 reference
```

Both are "a secret in your `.zshrc`" to a scanner. Only one is a problem. `credential_audit.py`
classifies every credential-shaped assignment into `literal` / `file-reference` / `reference` /
`path`, so the report distinguishes an exposure from a correct setup — and shows the correct ones,
so you can tell whether a finding is an outlier or the norm.

## The safety property, made structural

A credential's **value never enters the model's context** — and that's enforced by construction, not
by instruction:

- `scan_assignments()` classifies a value and **discards it**. A finding is `(line, variable name,
  classification)`; there is no field a secret could occupy. A test asserts an invented secret is
  absent from the rendered report, so the guarantee survives refactors.
- `matches_marker()` returns a bool, mirroring `grep -q` — enough to decide a finding, incapable of
  surfacing one.
- `--all-assignments` emits a **redacted inventory** (names + classifications, no values), which is
  what makes it safe to delegate the "which of these unusual names are credentials?" review to a
  subagent — it reads the inventory, never the files.
- No script calls a store CLI in a form that emits a secret. Writing a secret *into* a store runs
  out of band, by the user.

## Requirements

- **Claude Code**, plus **git**. macOS for the keychain path; `op` / `pass` / chezmoi `age` work
  anywhere. `gh` is optional.
- Scripts are **stdlib-only Python 3.9+** and read-only.

## Coordinates, doesn't duplicate

**dotfiles** owns secrets in the chezmoi source tree and the encryption/templating mechanics.
**ssh-config** owns private keys (which stay in `~/.ssh`, not a credential store). **git-setup** owns
`credential.helper` as a setting. **shell-sync** owns placing and mirroring rc lines across zsh and
fish. This skill owns only the literal→reference migration and the proof that it worked.

Part of the [devenv](../../README.md) plugin.
