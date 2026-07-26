# Optimize workflow — config & key-hygiene review

Goal: a prioritized picture of `~/.ssh/config` quality and key hygiene, and the exact fix for each
gap. Report; change nothing without confirmation. **NEVER print private key contents** — only
filenames, types, and perms. (Loose perms or a key not offered that *breaks* auth is
[repair.md](repair.md); applying the hardening is [upgrade.md](upgrade.md).)

> **Run the toolbox, don't re-compose bash.** Three read-only scripts cover this whole workflow
> and enforce the secrets rule (metadata only — never private-key bytes):
> ```bash
> scripts/key_audit.py            # §1-3: perms + types + passphrases, per key
> scripts/ssh_config_audit.py     # §1,5,6: config perms + Host blocks + Include + known_hosts
> scripts/agent_status.py         # §4: loaded identities vs on-disk keys
> ```
> The blocks below are the under-the-hood reference for what each script runs.

## 1. Permissions (ssh refuses loose perms — check first)

Covered by `scripts/key_audit.py` (per-key perms) and `scripts/ssh_config_audit.py` (dir + config).
Under the hood:

```bash
stat -f '%A %N' ~/.ssh ~/.ssh/config ~/.ssh/* 2>/dev/null   # macOS: octal perms per file
```
Expected — anything looser is 🔴 (ssh silently ignores the key/config):

| Path | Mode |
|---|---|
| `~/.ssh` (dir) | `700` |
| private keys (`id_*`, no `.pub`) | `600` |
| public keys (`*.pub`) | `644` |
| `~/.ssh/config` | `600` (644 tolerated) |

Fix: `chmod 700 ~/.ssh; chmod 600 ~/.ssh/id_*; chmod 644 ~/.ssh/*.pub`.

## 2. Key inventory & types (PUBLIC data only)

`scripts/key_audit.py` prints type/bits/fingerprint/comment + a strength verdict per key. Under the hood:

```bash
for k in ~/.ssh/*.pub; do ssh-keygen -lf "$k"; done   # bits, fingerprint, type — never the key body
```
- 🟢 **ed25519** — preferred (`256 SHA256:… (ED25519)`).
- 🟡 **rsa ≥ 3072** — acceptable; suggest migrating to ed25519.
- 🔴 **rsa < 3072**, **dsa**, **ecdsa** on old curves — weak; recommend rotation ([keys.md](keys.md)).

## 3. Passphrases (a stolen key with no passphrase = instant compromise)

`scripts/key_audit.py` reports `passphrase: NONE | protected` per key — from the exit code only,
never the key body. Under the hood:

```bash
# A key WITHOUT a passphrase decrypts with an empty one (exit 0) — no prompt, no key contents shown:
for k in ~/.ssh/id_*; do [ -f "$k.pub" ] && \
  ssh-keygen -y -P "" -f "$k" >/dev/null 2>&1 && echo "🔴 NO passphrase: $k" || echo "🟢 passphrase: $k"; done
```
Flag any 🔴 unprotected private key. On macOS the passphrase can live in the login keychain so it's
entered once — see [keys.md](keys.md).

## 4. Loaded agent identities

`scripts/agent_status.py` lists loaded identities and cross-references them against on-disk `*.pub`
(loaded / not-loaded / orphaned). Under the hood:

```bash
ssh-add -l 2>/dev/null || echo "(agent has no identities / not running)"
```
Compare against the keys on disk — identities loaded but no matching file (or vice-versa) is worth
noting. `AddKeysToAgent yes` (below) auto-loads on first use.

## 5. Config quality

`scripts/ssh_config_audit.py` reports Host aliases, `Include`, and which hardening options are
set/absent — without dumping the config verbatim (it can hold private HostName/User). Under the hood:

```bash
cat ~/.ssh/config 2>/dev/null
ls -la ~/.ssh/config.d 2>/dev/null                  # modular includes
```
Review each `Host` block and the global (`Host *`) defaults for:

| Look for | Why |
|---|---|
| `IdentityFile` per Host | explicit key beats agent guesswork |
| `IdentitiesOnly yes` | stops offering *every* agent key (avoids "too many auth failures" lockouts) |
| `AddKeysToAgent yes` | auto-loads the key into the agent on first use |
| `UseKeychain yes` (macOS) | pulls the passphrase from the login keychain |
| `Include ~/.ssh/config.d/*` | modular, per-context config |
| stale `Host` blocks | hosts/keys that no longer exist |

## 6. known_hosts

`scripts/ssh_config_audit.py` reports `known_hosts` presence + entry count. Under the hood:

```bash
wc -l ~/.ssh/known_hosts 2>/dev/null                # present? (absent = every host is TOFU-prompted)
ssh-keygen -F github.com >/dev/null && echo "github.com pinned"
```
Note if it's missing or if `StrictHostKeyChecking` is weakened anywhere.

## 7. Report

Prioritized:
- 🔴 loose perms / unprotected private key / weak key type / a private key tracked in git.
- 🟡 no `IdentitiesOnly`, no `UseKeychain` on macOS, rsa-3072, monolithic config (no `Include`).
- 🟢 cosmetic: stale Host blocks, missing comments, ed25519 migration opportunities.

Each with the exact fix command. Offer to proceed to [setup.md](setup.md) (clean up the
config) or [keys.md](keys.md) (rotate a weak/unprotected key). **Only filenames, types, and perms
appear in the report — never key contents.**
