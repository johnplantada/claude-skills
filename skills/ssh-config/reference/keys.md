# Keys workflow — generate, load, rotate (macOS-aware)

Goal: modern **ed25519** keys, protected by a **passphrase** (stored in the macOS keychain so it's
entered once), loaded into the agent, and registered by their **PUBLIC** half. **NEVER print or
commit the private key.**

> **One-shot generate + load:** `scripts/key-new.py <name> <comment>` does steps 1-2 together —
> generates the ed25519 key (interactive passphrase prompt), loads it into the agent + keychain,
> and prints the PUBLIC key ready to register. It refuses to overwrite an existing key and never
> prints the private half. Steps 1-2 below are the under-the-hood reference (and the Linux path,
> where the keychain flag is dropped).

## 1. Generate an ed25519 key (with a passphrase)

```bash
scripts/key-new.py id_ed25519 "john@laptop-2026"    # generate + load + show the .pub
# — or by hand:
ssh-keygen -t ed25519 -C "john@laptop-2026" -f ~/.ssh/id_ed25519
# -C is a comment/label (email or user@host), NOT a secret. ssh-keygen prompts for a passphrase —
# ALWAYS set one. A passphrase-less private key is a single-file compromise.
```
- Per-host identity? Use a distinct filename: `-f ~/.ssh/id_ed25519_myserver`, then point that
  Host's `IdentityFile` at it ([setup.md](setup.md)).
- Result: `id_ed25519` (private, `600`) + `id_ed25519.pub` (public, `644`). Only the `.pub` ever
  leaves the machine.

## 2. Add to the agent + macOS keychain

```bash
ssh-add --apple-use-keychain ~/.ssh/id_ed25519   # stores the passphrase in the login keychain
ssh-add -l                                        # confirm it's loaded (fingerprint, not the key)
```
Pair with `AddKeysToAgent yes` + `UseKeychain yes` in `~/.ssh/config` so the passphrase is supplied
automatically from the keychain on future logins ([setup.md](setup.md)). On older macOS the
flag is `-K` instead of `--apple-use-keychain`.

## 3. Register the PUBLIC key with GitHub

```bash
# Preferred — GitHub CLI (public key only):
gh ssh-key add ~/.ssh/id_ed25519.pub --title "laptop-2026"
# For SSH commit signing instead of auth, add it as a signing key:
gh ssh-key add ~/.ssh/id_ed25519.pub --title "laptop-2026 (signing)" --type signing
```
Manual alternative: copy the public key and paste it at **GitHub → Settings → SSH and GPG keys**:
```bash
pbcopy < ~/.ssh/id_ed25519.pub    # copies the PUBLIC key to the clipboard (safe)
```
Never paste `id_ed25519` (no `.pub`) anywhere — that's the private key.

## 4. Verify the new key authenticates

```bash
ssh -T git@github.com     # "Hi <user>! You've successfully authenticated…"
```
See [verification.md](verification.md). Prove the new key works **before** removing the old one.

## 5. Rotation (replace a weak or exposed key safely)

1. Generate the new ed25519 key (step 1) with a **new filename** — don't overwrite the old one yet.
2. Register the new **public** key everywhere the old one is used (GitHub, servers'
   `~/.ssh/authorized_keys`).
3. Verify auth with the new key (step 4) on every target.
4. Only then remove the old key from remotes, delete it locally (`rm ~/.ssh/id_old*`), and drop it
   from the agent (`ssh-add -d ~/.ssh/id_old`).
- If a private key was ever **exposed** (committed, pasted, leaked): treat it as compromised —
  rotate immediately and revoke the old public key on every remote. A passphrase buys time, not
  immunity.

## 6. Cross-skill note

Track the **public** key + config via the `dotfiles` skill; keep the **private** key out of git
(`.chezmoiignore`) or chezmoi-**encrypted** (age) — never plaintext. The same key backs `git-setup`
SSH signing/auth; keep one identity per machine rather than scattering keys.
