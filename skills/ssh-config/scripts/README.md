# ssh-config scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the
`stat` / `ssh-keygen -lf` / `ssh-keygen -y` / `ssh -G` / `ssh-add -l` incantations from scratch
each time. Fewer tokens, no re-derivation, and — critically — the secrets discipline is baked in
so it can't be forgotten mid-audit. These scripts are the source of truth for the mechanical
commands; the reference `.md` files carry the judgment.

Run them by absolute path from the skill's `scripts/` directory.

| Script | Purpose | Example |
|---|---|---|
| `key_audit.py [ssh-dir]` | **Key-hygiene auditor.** Per private key: perms, type, bits, comment, fingerprint (from the `.pub`), passphrase-protected?, loaded-in-agent?, strength verdict. Read-only. | `key_audit.py` |
| `ssh_config_audit.py [host]` | **Config auditor + resolver.** Perms on `~/.ssh`/config/config.d, Host aliases, `Include`, hardening options present/absent, weak settings, `known_hosts`. With `[host]`: also `ssh -G` effective config. Read-only. | `ssh_config_audit.py github.com` |
| `agent_status.py [ssh-dir]` | **Agent/keychain inspector.** `ssh-add -l` identities (fingerprints) cross-referenced against on-disk `*.pub`: which are loaded, which orphaned. Read-only. | `agent_status.py` |
| `key_new.py <name> <comment>` | **MUTATING.** Generate an ed25519 key (interactive passphrase — always set one), load it into agent + macOS keychain, print the PUBLIC half ready to register. Refuses to overwrite. | `key_new.py id_ed25519_server "me@host"` |

The first three are **read-only inspectors** — safe to re-run any time. `key_new.py` **changes
state** (creates a key, edits the agent + keychain); run it deliberately.

## The secrets rule these scripts enforce

A private key is a secret. **No script ever prints, cats, or echoes private-key bytes.**

- Type / bits / fingerprint / comment come from the **public** `*.pub` (`ssh-keygen -lf`).
- Passphrase protection is inferred from the **exit code** of `ssh-keygen -y -P '' -f <key>` with
  all output redirected to `/dev/null` — pass/fail is observed, the (public) output discarded.
- Private keys are discovered via `grep -ql 'PRIVATE KEY'` (matches the header line, prints nothing).
- `ssh_config_audit.py` never dumps the config verbatim (it can hold private HostName/User) — it
  reports Host *aliases* and which options are *set*, not their values. `ssh -G` output is shown
  only for a host you pass explicitly.
- File perms come from `stat`. Nothing writes a private key except `key_new.py` via `ssh-keygen`.

## Worked example — a full hygiene audit in three calls

```
ssh_config_audit.py github.com   # perms 700/600, Include present, IdentitiesOnly ABSENT; ssh -G resolves id_ed25519
key_audit.py                     # id_ed25519: ED25519, passphrase: protected, in_agent: no  → strong key, just not loaded
agent_status.py                  # agent EMPTY → key on disk but not-loaded  → `ssh-add --apple-use-keychain` to load
```
Verdict: strong ed25519 key, correctly permissioned and passphrase-protected, but not in the agent
and `IdentitiesOnly` is absent from the config — fix both via keys.md / setup.md.

## Conventions for adding scripts

- `#!/usr/bin/env python3`, **Python 3.9+, stdlib only** (no pip deps); start with
  `from __future__ import annotations`; type hints + module/function docstrings.
- **Separate pure logic from IO:** parsing / analysis / formatting are plain module functions
  (what the tests call, no mocking); the `stat` / `ssh-keygen` / `ssh-add` / `ssh -G` subprocess
  wrappers live in `_ssh_common.py`. End each script with `if __name__ == "__main__": sys.exit(main())`.
- Print `label: value` (or `key<TAB>value`) lines; keep output greppable and order stable.
- A leading module docstring doubling as `--help`.
- **Secrets first:** never emit private-key material; operate on metadata (`.pub`, `stat`, exit codes).
