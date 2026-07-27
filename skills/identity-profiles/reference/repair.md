# Repair workflow — a surface disagrees with the tree

Start from the symptom. Every path below begins with the same two commands, because the fix depends
on **which** surface drifted, and guessing costs more than measuring:

```bash
scripts/profile_audit.py                 # all profiles — the gap report names the check that failed
scripts/profile_resolve.py <the-repo>    # one repo — every surface side by side
```

## Symptom → cause → fix

### "I committed under the wrong email"

`profile_resolve.py <repo>` → `user.email` is the other identity.

- **`in_repo no`** — the path isn't a git repo, so `includeIf "gitdir:"` never applied. Not a bug;
  re-run inside the repo.
- **Right tree, wrong email** — the `includeIf` didn't match. Almost always the **trailing slash**
  (`gitdir:~/work` vs `gitdir:~/work/`) or a symlinked path (git matches the *resolved* path; a repo
  reached through a symlinked `~/work` won't match). Confirm which file supplied the value with
  **`git-setup`'s `git_identity.py <repo>`** — it names the winning include file.
- **The repo sits outside every declared tree** — either move it, or add a tree
  ([upgrade.md](upgrade.md)). Do **not** fix it with a per-repo `git config user.email`; that is the
  drift this skill removes.

To fix commits already made, see `git-setup` — rewriting history is its territory, not this skill's.

### "My push authenticated as the other account"

`profile_audit.py` → `key_match mismatch`.

The tree signs with one key but its remote's alias offers another. Two causes:

- **The remote doesn't use the alias.** `remote_alias (not an ssh remote)` or the bare hostname →
  `git -C <repo> remote set-url origin git@<alias>:<owner>/<repo>.git`.
- **The alias points at the wrong key**, or ssh is offering extras. Fix the `Host` block's
  `IdentityFile` and add `IdentitiesOnly yes` — without it ssh offers every agent key and the server
  takes the first that works. Re-check with `ssh -G <alias> | grep identityfile`.

Confirm the real answer with the network probe, which reports the account rather than the intent:

```bash
scripts/profile_resolve.py <repo> --probe-remote     # -> ssh.authenticates_as <account>
```

### "Commits are signed but show Unverified"

`profile_audit.py` → `allowed_signers missing` (or `no-file`).

The second identity's email is not paired with **that identity's** key. One line fixes it:

```bash
printf '%s %s\n' "<that-tree's-email>" "$(cat <that-tree's-signingkey>)" >> ~/.config/git/allowed_signers
```

`no-file` means `gpg.ssh.allowedSignersFile` is unset or empty — that's `git-setup`'s setup
workflow; come back here once it's set. Prove the fix with a real signed commit
([verification.md](verification.md)), not by re-reading the file.

### "gh is doing things as the wrong account"

`profile_resolve.py` → `gh.accounts` lists both, but gh has one *active* account globally and does
not follow directories. Switch it explicitly (`gh auth switch`) when crossing profiles. This skill
reports the account; it does not manage gh's auth state.

### "The audit says undetermined"

Not a pass — a check that could not run:

- `probe_repo undetermined` — no repo under that tree, so nothing about the profile could be
  resolved. Clone one, or drop the stale `includeIf` rule.
- `ssh.identityfile undetermined` — `ssh -G <alias>` failed; the alias probably doesn't exist in
  `~/.ssh/config`. That's the finding.
- `gh.accounts undetermined` — `gh` isn't installed; ignore unless the user wants the gh surface.

## After any fix

Re-run `scripts/profile_audit.py` and confirm the specific gap is gone and no new one appeared.
Then do the [verification.md](verification.md) proof for the profile you touched — editing config is
the start of a repair, not the end of it.
