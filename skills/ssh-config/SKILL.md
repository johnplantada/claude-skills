---
name: SSH Config
description: Set up, repair, upgrade, and optimize ~/.ssh/config and SSH KEY HYGIENE safely (macOS-aware), with a first-class KEYS path — treating private keys as secrets that must NEVER be exposed, committed, or read into the model's context. Use to SET UP a clean structured ~/.ssh/config (global defaults, per-Host blocks, Include, hardening), REPAIR failing auth (loose perms, agent empty, wrong Host match, too-many-failures, known_hosts mismatch), UPGRADE by hardening/modernizing the config and moving off weak key types, OPTIMIZE with a prioritized config + key-hygiene report, or manage KEYS (generate ed25519, add to agent + keychain, per-host identities, rotation, register the PUBLIC key with GitHub). Verified — config resolves and auth actually works.
argument-hint: [setup|repair|upgrade|optimize|keys]
allowed-tools: Bash(*ssh-config/scripts/*), Bash(ssh -G *), Bash(ssh -T *), Bash(ssh -o BatchMode=yes *), Bash(ssh-add -l), Bash(ssh-add -L), Bash(ssh-keygen -l *), Bash(ssh-keygen -lf *), Bash(cat ~/.ssh/config), Bash(cat ~/.ssh/config.d/*), Bash(ls -la *), Bash(stat *), Bash(git -C * *)
---

# SSH config & key hygiene

Manage `~/.ssh/config` and SSH **key hygiene** on macOS, with one non-negotiable rule: **a private
key is a secret** — never print it, never commit it, never expose it. This skill is
**verification-first**: prove the config resolves (`ssh -G`) and auth actually works (`ssh -T`)
rather than just editing the file and hoping.

## Route to a workflow

| The user wants to… | Workflow |
|---|---|
| Build a clean, structured `~/.ssh/config` | [reference/setup.md](reference/setup.md) |
| Fix failing auth — key not offered, agent empty, wrong Host match | [reference/repair.md](reference/repair.md) |
| Harden / modernize the config, move off weak key types | [reference/upgrade.md](reference/upgrade.md) |
| Review config + key hygiene, prioritized | [reference/optimize.md](reference/optimize.md) |
| Generate / add / rotate keys, register with GitHub | [reference/keys.md](reference/keys.md) |
| Prove config resolves and auth works | [reference/verification.md](reference/verification.md) |

**[reference/keys.md](reference/keys.md)** is a first-class path (key generation/rotation is a
distinct security flow), kept alongside the canonical four.

## The scripts (call these; don't re-derive them)

`scripts/` is the stable toolbox — see [scripts/README.md](scripts/README.md). Call a script by
name instead of re-deriving `stat` / `ssh-keygen` / `ssh -G` / `ssh-add` each session; the
**secrets discipline is baked in** (no script ever emits private-key bytes — metadata only).

| Script | Does | Read-only? |
|---|---|---|
| `scripts/ssh_config_audit.py [host]` | config perms + Host aliases + `Include` + hardening opts + weak settings + `known_hosts`; with `[host]`, the `ssh -G` effective config | ✅ |
| `scripts/key_audit.py [ssh-dir]` | per key: perms, type, bits, comment, fingerprint, passphrase?, in-agent?, strength verdict | ✅ |
| `scripts/agent_status.py [ssh-dir]` | `ssh-add -l` identities cross-referenced against on-disk `*.pub` | ✅ |
| `scripts/key_new.py <name> <comment>` | generate ed25519 + load into agent/keychain + print the PUBLIC key | ⚠️ mutates |

## Discovery (always run first)

```bash
scripts/ssh_config_audit.py    # perms, Host blocks, Include, hardening, known_hosts
scripts/key_audit.py           # key hygiene: types, perms, passphrases (metadata only)
scripts/agent_status.py        # loaded identities vs keys on disk
```
Under the hood these run the read-only primitives below (nothing here reads a private key):
```bash
ls -la ~/.ssh                                      # perms + inventory (dir should be 700)
ssh-add -l 2>/dev/null || echo "(agent empty / not running)"   # loaded identities
for k in ~/.ssh/*.pub; do ssh-keygen -lf "$k"; done 2>/dev/null # key types/sizes (PUBLIC only)
```
- **Never `cat` a private key.** Read type/size via `ssh-keygen -lf <key>.pub` and filenames only.
- `~/.ssh/config` may not exist yet → that's the `setup` path.

## Core principles

1. **Verify, don't assume.** `ssh -G <host>` shows the *effective* resolved config; `ssh -T
   git@github.com` confirms auth. Never call a change done without both. See
   [reference/verification.md](reference/verification.md).
2. **Private keys are secrets.** Only ever surface a key's *filename, type, and permissions* — never
   its contents. Public keys (`.pub`) are safe to show and share.
3. **Strict permissions or ssh refuses.** `700 ~/.ssh`, `600` private keys, `644` `.pub`. Loose
   perms make ssh silently ignore a key — fix perms before debugging auth.
4. **Don't break working auth.** Back up `~/.ssh/config` before edits; test the new config
   resolves and authenticates *before* removing an old Host or key.
5. **Prefer ed25519.** Small, fast, modern. Flag `rsa` < 3072 bits as weak.

## Cross-skill coherence

- **dotfiles** (chezmoi): track `~/.ssh/config` and `~/.ssh/config.d/*` and **PUBLIC** keys, but
  PRIVATE keys must be **excluded** (`.chezmoiignore`) or **encrypted** (chezmoi age) — never
  plaintext in git. See the `dotfiles` skill's secrets workflow; don't reimplement it here.
- **git-setup**: SSH commit signing / auth reuses these keys — keep the identity consistent.

## Settings

Read `~/.config/devenv/config.toml` before prompting; if a `[ssh-config]` section exists, use it as
defaults (precedence: explicit answer this session > `config.toml` > ask). Had to ask? Offer to save
the answer back. Managed by the `devenv` skill. Keys honored:
- `key_type` — preferred key algorithm for new keys (default `ed25519`).

## Safety

- **NEVER print, commit, expose, or read a private key into the model's context.** Only filenames,
  types, permissions, and fingerprints leave this skill; the scripts derive everything from the
  `.pub` and from exit codes (`grep -ql 'PRIVATE KEY'`, `ssh-keygen -y … >/dev/null`) — never the
  private bytes. Ops needing the key itself (generation, agent load) happen via the tooling, not by
  reading the material. Public keys (`.pub`) only.
- **Back up `~/.ssh/config` before any edit** (`cp ~/.ssh/config ~/.ssh/config.bak`).
- **Don't break working auth.** Test the new config resolves (`ssh -G`) and authenticates
  (`ssh -T`) before removing a Host or deleting a key.
- **Strict perms are mandatory** — ssh rejects world/group-readable keys and configs. Fix perms
  rather than working around them.
