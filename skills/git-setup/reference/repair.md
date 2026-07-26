# Repair workflow — signing won't verify, wrong identity, cred re-prompts

Goal: fix a git setup that's configured but misbehaving — commits that sign yet show **unverified**,
HTTPS that re-prompts for a password, or the **wrong email** landing on commits in a repo. Diagnose
with the read-only scripts, fix the narrowest cause, then **prove** it with a signed test commit.

> **Diagnose:** `scripts/git_audit.py | grep '^gap'` (ranked gaps + fix commands),
> `scripts/verify_signing.py` (prove your **real** config yields status `G`, not `N`/`U`),
> `scripts/git_identity.py <path>` (which email + key resolve in a tree, and the file each came
> from). Prove the fix — [verification.md](verification.md).

## 1. Symptom → cause

| Symptom | Likely cause | Check |
|---|---|---|
| commits show **Unverified** on GitHub / local `No signature` (`N`) | `commit.gpgsign` off, or the commit wasn't signed | `git_audit.py` · `verify_signing.py` |
| local `show-signature` says **`No principal matched`** (`U`) | `allowedSignersFile` missing the `<email> <pubkey>` line | `verify_signing.py` |
| signing "on" but nothing verifies | `user.signingkey` points at a **private** key (needs the `.pub`), or `gpg.format` wrong | `git_audit.py` |
| **wrong email** on commits in a repo | an `includeIf` didn't match (trailing slash / path), or only a global email is set | `git_identity.py <repo>` |
| HTTPS push **re-prompts** every time | `credential.helper` unset (macOS: `osxkeychain`) | `git_audit.py` |

## 2. Fix the cause (confirm — these are mutating)

- **Signed but `No principal matched` (`U`)** — the classic half-configured trap. Add the identity's
  line to the allowed-signers file, then set the pointer:
  ```bash
  printf '%s %s\n' "$(git config --global user.email)" "$(cat ~/.ssh/id_ed25519.pub)" \
    >> ~/.config/git/allowed_signers
  git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
  ```
- **`No signature` (`N`)** — turn signing on and confirm the format/key point at the **public** key:
  `git config --global gpg.format ssh` · `user.signingkey ~/.ssh/id_ed25519.pub` · `commit.gpgsign true`.
- **Private key where a `.pub` is required** — repoint `user.signingkey` at the `.pub`. The private
  key never appears in config, is never tracked, and is never read into this session.
- **Wrong identity** — `git_identity.py <repo>` names the file that won. Fix the `includeIf` glob (a
  **trailing slash** is required: `gitdir:~/work/`) in `~/.gitconfig`, or add the missing per-tree
  file ([identity.md](identity.md)). Re-check that the origin is the expected `*.gitconfig`.
- **Cred re-prompts (macOS)** — `git config --global credential.helper osxkeychain`.

## 3. Prove the fix

```bash
scripts/verify_signing.py                    # real config now: result ✅ GOOD signature, status G
scripts/git_identity.py ~/work/<repo>        # resolves to the expected email, from the right file
```
A signed commit that still won't verify isn't fixed — chase the `%G?` status (`U` = allowed-signers
gap, `N` = not signed) until it reads `G`. Full proof in [verification.md](verification.md).
