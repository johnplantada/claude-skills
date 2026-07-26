# Verification — prove the git setup actually works, don't just set it

Setting config is not the finish line. Prove a commit **verifies**, an alias **runs**, and the right
identity **resolves**. Do this in a throwaway repo so nothing pollutes real work.

> **Signing → run [`scripts/verify_signing.py`](../scripts/verify_signing.py)** — it makes the test
> commit in a `mktemp -d` repo it owns and removes on exit, then reports the `%G?` status + the
> `Good signature` line. `--self-test` proves the whole sign→verify pipeline with an ephemeral key
> (no real key touched) *before* you adopt signing; no flag reflects your **real** global config.
> **Identity → run [`scripts/git_identity.py <path>`](../scripts/git_identity.py)** (see below).
>
> ```bash
> scripts/verify_signing.py --self-test    # ✅ GOOD signature — the machinery works on this machine
> scripts/verify_signing.py                # after configuring: proves your real global setup yields G, not N
> ```

The sections below are the under-the-hood reference for the manual throwaway-repo dance:

```bash
TMP=$(mktemp -d) && git -C "$TMP" init -q && cd "$TMP"
```

## Signing actually verifies (the real test)

A signed commit that doesn't verify locally is the #1 half-configured trap. `verify_signing.py` does
this for you; by hand it's — make a commit and check the signature:

```bash
git -C "$TMP" commit --allow-empty -m "signing test" -q
git -C "$TMP" log --show-signature -1
```
- Look for **`Good "git" signature for <email>`** (SSH) or `Good signature from …` (GPG) —
  `verify_signing.py` reports `result ✅ GOOD signature` (status code `G`).
- **`No signature`** (`N`) → `commit.gpgsign` isn't on, or the commit wasn't signed.
- **`No principal matched`** / unknown key (`U`) → the `allowedSignersFile` is missing the
  `<email> <pubkey>` line for this identity ([setup.md](setup.md) §4). Fix it and re-check —
  this is what makes the difference between "signed" and "verified".

## The config values are what you think — and come from where you think

```bash
git config --get commit.gpgsign            # true
git config --get gpg.format                # ssh
git config --get user.signingkey           # ~/.ssh/id_ed25519.pub  (a .pub, not a private key)
git config --list --show-origin | grep -E 'signingkey|gpgsign|allowedSigners|pager|user\.email'
```
`--show-origin` proves *which file* supplied each value — essential once conditional includes are in
play.

## Identity resolves per directory (if using includes)

**Run [`scripts/git_identity.py <path>`](../scripts/git_identity.py)** for each tree — it resolves
the email + signing key and names the file each came from (`user.email_from`). Under the hood it
evaluates config from inside a repo in each tree — see [identity.md](identity.md):

```bash
git -C ~/work/<any-repo>     config user.email          # -> work email
git -C ~/personal/<any-repo> config user.email          # -> personal email
git -C ~/work/<any-repo>     config --show-origin user.email   # names the include file that won
```
Confirm each resolves to the expected email; the origin should be the matching
`~/.config/git/*.gitconfig`.

## Delta actually renders

```bash
echo "a" > f && git -C "$TMP" add f && git -C "$TMP" commit -qm one
printf 'a\nb\n' > f && git -C "$TMP" -c core.pager=delta diff        # colored, line-numbered output
command -v delta && delta --version
```
You should see delta's styled diff, not plain `+/-` lines.

## Aliases run

```bash
git config --get-regexp '^alias\.'         # they're defined
git -C "$TMP" lg -1                          # the graph-log alias actually executes
git -C "$TMP" st                             # status alias
```

## Clean up

```bash
cd - >/dev/null && rm -rf "$TMP"
```

Report what verified: a **Good signature** on a real commit, delta rendering, each alias running,
and every identity resolving to the right email from the right file. If anything failed, it's a
config gap to fix — not a "probably fine."
