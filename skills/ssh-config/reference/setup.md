# Set up workflow — a clean, structured ~/.ssh/config

Goal: stand up a readable, hardened `~/.ssh/config` with sane global defaults, per-`Host` blocks,
and `Include` for modularity. **Back up first**, then **verify it resolves**
([verification.md](verification.md)).

> Need a key first? Generate one in [keys.md](keys.md). Auth broken after? → [repair.md](repair.md).
> Tightening an existing config to current best practice → [upgrade.md](upgrade.md).

## 1. Back up (always, before any edit)

```bash
cp ~/.ssh/config ~/.ssh/config.bak 2>/dev/null && echo "backed up" || echo "(no existing config)"
```

## 2. Global defaults + per-Host blocks

Structure: a `Host *` defaults block at the **bottom** (last match wins for unset options, but
these are safe global defaults), specific `Host` blocks above it. Example:

```sshconfig
# ~/.ssh/config — managed by the ssh-config skill

Include ~/.ssh/config.d/*                # modular per-context config (see step 3)

Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes                   # offer ONLY this key for this host

Host myserver
    HostName 203.0.113.10
    User deploy
    Port 22
    IdentityFile ~/.ssh/id_ed25519_myserver
    IdentitiesOnly yes

# Global defaults — apply to every host unless overridden above.
Host *
    AddKeysToAgent yes                   # auto-load the key into ssh-agent on first use
    UseKeychain yes                      # macOS: read the passphrase from the login keychain
    IdentitiesOnly yes                   # never blast every agent key at a server
    ServerAliveInterval 60               # keep long sessions alive
    HashKnownHosts yes                   # privacy: hash host entries
```

- **`UseKeychain yes`** is macOS-only. On Linux, drop it (ssh errors on an unknown option there).
- **`IdentitiesOnly yes`** prevents the "Too many authentication failures" lockout when the agent
  holds several keys — the server only sees the `IdentityFile` you named.

## 3. Modularity with Include

Split per-context config into `~/.ssh/config.d/` so work/personal/client hosts stay separate and
each is easy to track (or ignore) in dotfiles:

```bash
mkdir -p ~/.ssh/config.d && chmod 700 ~/.ssh/config.d
# e.g. ~/.ssh/config.d/work.conf holds work Host blocks
```
Put `Include ~/.ssh/config.d/*` near the top of `~/.ssh/config` (Include is processed in place).

## 4. Fix permissions

```bash
chmod 700 ~/.ssh ~/.ssh/config.d 2>/dev/null
chmod 600 ~/.ssh/config ~/.ssh/config.d/* 2>/dev/null
chmod 600 ~/.ssh/id_* 2>/dev/null; chmod 644 ~/.ssh/*.pub 2>/dev/null
```
ssh **ignores** a config or key with loose perms — this is not optional.

## 5. Verify before you trust it

Run `scripts/ssh_config_audit.py <host>` to confirm perms are right and see the resolved effective
config, then `ssh -T` to prove auth. Under the hood the audit runs:

```bash
ssh -G github.com | grep -E '^(hostname|user|identityfile|identitiesonly) '   # resolved effective config
ssh -T git@github.com                                                          # auth actually works
```
If resolution looks wrong or auth breaks, restore: `cp ~/.ssh/config.bak ~/.ssh/config`. Only remove
a stale `Host` block once its replacement is proven ([verification.md](verification.md)).

## 6. Track it (dotfiles)

`~/.ssh/config` and `~/.ssh/config.d/*` are safe to version-control (no secrets). Hand to the
`dotfiles` skill: track the config + `.pub` keys, and **exclude/encrypt private keys** — never
commit `id_*` plaintext.
