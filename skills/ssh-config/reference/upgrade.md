# Upgrade workflow — harden and modernize ~/.ssh/config

Goal: bring a working setup up to current best practice — adopt the hardening options you're
missing, drop weak/deprecated settings, and move off weak key types. **Back up `~/.ssh/config`
first**; each change is mutating — propose, confirm, and verify auth still works. Only filenames,
types, and perms are ever surfaced — never a private key.

> Run [`scripts/ssh-config-audit.py`](../scripts/ssh-config-audit.py) first — it reports which
> hardening options are set vs absent and flags weak settings; `scripts/key-audit.py` flags weak key
> types. A brand-new config is [setup.md](setup.md); broken auth is [repair.md](repair.md); the
> actual key rotation is [keys.md](keys.md).

## 1. Adopt the hardening defaults (only those missing)

In the global `Host *` block (see the resolved audit for what's already set):

| Option | Value | Why |
|---|---|---|
| `AddKeysToAgent` | `yes` | auto-load the key into the agent on first use |
| `UseKeychain` | `yes` (macOS only) | passphrase from the login keychain — entered once |
| `IdentitiesOnly` | `yes` | offer only the named key — avoids "too many auth failures" |
| `HashKnownHosts` | `yes` | privacy: hashed host entries |
| `ServerAliveInterval` | `60` | keep long sessions alive |

On Linux, **drop `UseKeychain`** — ssh errors on the unknown option there.

## 2. Drop weak / deprecated settings

- `StrictHostKeyChecking no` (or `accept-new` applied globally) → remove; it defeats host-key
  verification. Re-pin hosts deliberately instead.
- Explicit weak `Ciphers` / `MACs` / `KexAlgorithms` overrides (arcfour, `hmac-md5`,
  `diffie-hellman-group1-sha1`) → remove the override and let modern OpenSSH defaults apply, or pin a
  known-good modern set.
- A legacy per-host RSA `IdentityFile` pointing at a weak key → rotate it (next step), then repoint.

## 3. Modernize key types

`key-audit.py` flags `rsa < 3072`, `dsa`, and old `ecdsa` as weak. Rotate each to **ed25519** via
[keys.md](keys.md) §5 — generate the new key, register its **public** half everywhere, verify auth on
every target, and only then retire the old one. Don't delete a key until its replacement authenticates.

## 4. Re-verify (nothing broke)

```bash
scripts/ssh-config-audit.py <host>       # perms right + the resolved effective config
ssh -T <host>                            # auth still works after the changes
```
See [verification.md](verification.md). Then track the hardened config (and `.pub` keys only) via the
`dotfiles` skill.
