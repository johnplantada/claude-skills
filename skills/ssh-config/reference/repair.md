# Repair workflow — SSH auth is failing

Goal: fix auth that's broken — a key "not offered", the agent empty, the wrong `Host` matching, or
"Too many authentication failures". Diagnose from the **effective config** and the **verbose
handshake** (fingerprints only), fix the narrowest cause, and prove auth works. **Never read a
private key** to debug — permissions, fingerprints, and `ssh -vT` tell the whole story.

> **Diagnose with the read-only scripts** (metadata only, never key bytes):
> `scripts/ssh_config_audit.py <host>` (resolved `ssh -G`), `scripts/key_audit.py` (perms / type /
> passphrase), `scripts/agent_status.py` (loaded identities). Prove the fix — [verification.md](verification.md).

## 1. Symptom → cause

| Symptom | Likely cause | Check |
|---|---|---|
| `Permission denied (publickey)` / key "not offered" | **loose perms** → ssh silently ignores the key/config | `key_audit.py` (700/600/644) |
| agent has no identities | key not loaded, or agent not running | `agent_status.py` · `ssh-add -l` |
| `Too many authentication failures` | agent offers **every** key; server cuts you off | `ssh -G <host>` → `identitiesonly`? |
| wrong user / host / key used | an earlier `Host *` / `Match` / `Include` overrides | `ssh -G <host>` (effective config) |
| `Host key verification failed` | `known_hosts` mismatch (host rotated — or MITM) | the host's `known_hosts` entry |

## 2. Fix the cause (confirm — some are mutating)

- **Loose perms** (the #1 "key not offered" cause): `chmod 700 ~/.ssh; chmod 600 ~/.ssh/config
  ~/.ssh/id_*; chmod 644 ~/.ssh/*.pub`. ssh refuses world/group-readable keys and configs.
- **Agent empty**: `ssh-add --apple-use-keychain ~/.ssh/id_ed25519` ([keys.md](keys.md)); add
  `AddKeysToAgent yes` so it auto-loads next time.
- **Too many failures**: set `IdentitiesOnly yes` on the `Host` and name its `IdentityFile`, so only
  that key is offered ([upgrade.md](upgrade.md) / [setup.md](setup.md)).
- **Wrong resolution**: `ssh -G <host>` shows what actually wins (first match per option). Fix the
  `Host` glob / block ordering so the intended block matches.
- **`known_hosts` mismatch**: if the host key legitimately rotated, `ssh-keygen -R <host>` then
  reconnect to re-pin. If it changed **unexpectedly, stop** — verify the host key fingerprint out of
  band before trusting it (a mismatch can be a machine-in-the-middle).

## 3. Prove it (fingerprints only, never the key)

```bash
scripts/ssh_config_audit.py <host>              # identityfile is the key you intend; identitiesonly yes
ssh -vT git@github.com 2>&1 | grep -iE 'offering|authentication succeeded|identity file'
ssh -o BatchMode=yes <host> true                # green = KEY auth worked (not a password fallback)
```
A green `BatchMode` result is the proof. No step here `cat`s a private key — see
[verification.md](verification.md).
