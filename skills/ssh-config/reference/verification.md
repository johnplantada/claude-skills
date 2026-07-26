# Verification — prove the config resolves and auth actually works

Editing `~/.ssh/config` is not proof. A change is done only when the effective config resolves as
intended **and** authentication succeeds. **Never print a private key to verify it** — use
fingerprints and effective-config output.

> **Fast path:** `scripts/ssh-config-audit.py <host>` prints the resolved `ssh -G` settings, and
> `scripts/agent-status.py` shows the loaded identities — both read-only, fingerprints only. The
> blocks below are the under-the-hood reference.

## The config resolves (effective, not just the file)

`ssh -G` prints the *fully resolved* config for a host — every `Host`/`Match`/`Include` applied, so
you see what ssh will actually use (not what you think the file says). `scripts/ssh-config-audit.py
<host>` runs this and extracts the key settings; under the hood:

```bash
ssh -G github.com | grep -E '^(hostname|user|port|identityfile|identitiesonly|addkeystoagent) '
```
Confirm `identityfile` points at the key you intend and `identitiesonly yes` is present. If the file
looks right but `ssh -G` disagrees, an earlier `Host *`/`Match` block or an `Include` is overriding
it — first match wins per option.

## Auth actually works

```bash
ssh -T git@github.com                 # GitHub: "Hi <user>! You've successfully authenticated…" (exit 1 is normal — no shell)
ssh -o BatchMode=yes <host> true      # any host: non-interactive; fails fast instead of hanging on a password prompt
```
`BatchMode=yes` disables password/keyboard-interactive prompts, so a green result means **key**
auth genuinely worked (not a fallback password). Do this on the new key/config **before** removing
the old one.

## Permissions are correct (ssh refuses loose perms)

ssh silently ignores a key or config that's too open — a "key not offered" bug is often just perms.

```bash
stat -f '%A %N' ~/.ssh ~/.ssh/config ~/.ssh/id_* ~/.ssh/*.pub 2>/dev/null
# Expect: 700 ~/.ssh | 600 config | 600 private keys | 644 *.pub
# One-shot fix:
chmod 700 ~/.ssh; chmod 600 ~/.ssh/config ~/.ssh/id_*; chmod 644 ~/.ssh/*.pub
```
Confirm with a verbose dry run that the intended key is offered (fingerprints only, never the key):
```bash
ssh -vT git@github.com 2>&1 | grep -iE 'offering|authentication succeeded|identity file'
```

## The agent holds the expected identities

`scripts/agent-status.py` lists them and cross-references on-disk `*.pub` for you. Under the hood:

```bash
ssh-add -l         # lists loaded keys by fingerprint/type — never the key body
```
Cross-check against the `identityfile` from `ssh -G`. Missing? `ssh-add --apple-use-keychain
~/.ssh/id_ed25519` ([keys.md](keys.md)).

## Nothing secret leaked (the standing check)

- No command in this session ever `cat`'d a private key or pasted its contents.
- If tracking config via dotfiles: `git -C "$(chezmoi source-path)" ls-files | grep -E 'id_[^.]*$'`
  returns **nothing** — a private key in git means rotate now ([keys.md](keys.md) step 5).
