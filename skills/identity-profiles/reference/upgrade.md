# Upgrade workflow — add a profile, or rotate a key across every surface

Both operations here fail the same way: a change lands on one surface and not the others, and the
gap stays silent until a push goes out as the wrong person. Each is a **checklist across all four
surfaces in one pass**, then the audit.

## Add a profile (a new client, a second job, an OSS identity)

Adding one touches four surfaces in lockstep. Skipping any leaves a half-profile that looks fine
until it isn't.

1. **The tree** — create it and decide the path (`~/clients/acme/`). One tree, one identity.
2. **git** — an `includeIf "gitdir:<tree>/"` rule in `~/.gitconfig` plus its
   `~/.config/git/<name>.gitconfig` (email, and `signingkey` if it signs with its own key).
3. **ssh** — a `Host <alias>` block with the profile's `IdentityFile` and `IdentitiesOnly yes`.
   Need a new key? That's `ssh-config`'s keys workflow — generate it there, then wire it here.
4. **signing** — a pairing line in `allowed_signers` for this email + this key.
5. **remotes** — new clones must use the alias: `git clone git@<alias>:<owner>/<repo>.git`.

Then:
```bash
scripts/profile_audit.py --tree ~/clients/acme/    # audits it even before the rule is picked up
```
`--tree` is for exactly this moment — checking a tree git doesn't declare yet. Once the `includeIf`
rule is in place, plain `profile_audit.py` discovers it and the flag is no longer needed.

## Rotate a key for an existing profile

The order matters: **add the new key everywhere before removing the old one**, so no window exists
where the profile can't authenticate.

1. Generate and register the new key (`ssh-config` keys workflow — including adding the **public**
   key to the git host).
2. **ssh** — point the profile's `Host` alias at the new `IdentityFile`.
3. **git** — update `signingkey` in that profile's gitconfig.
4. **signing** — add the new pairing line to `allowed_signers`. **Keep the old line**: it's what
   lets already-signed commits keep verifying. Removing it retroactively invalidates history.
5. Verify. First the static sweep:
   ```bash
   scripts/profile_audit.py
   ```
   then confirm the host actually accepts the new key as the right account:
   ```bash
   scripts/profile_resolve.py <repo-in-that-tree> --probe-remote
   ```
6. Only now retire the old key (revoke it at the host, remove from the agent).

## Move a tree

Changing a tree's path means updating the `includeIf` condition **and** re-checking that repos
still resolve. `includeIf "gitdir:"` matches the *resolved* path, so relocating a tree behind a
symlink silently stops matching:

```bash
scripts/profile_audit.py            # the moved profile should still resolve its email
```
If it reports `probe_repo undetermined`, the rule now points at nothing.

## Adopt a stricter default

Once profiles are working, tighten the fallback so an undeclared repo fails loudly instead of
committing under a default identity:

```bash
git config --global user.useConfigOnly true
```
This makes git refuse to commit when no identity is explicitly configured for the repo, converting
the silent-wrong-email failure into an error at commit time. Confirm with the user before setting
it — it will reject commits in any repo outside a declared tree until that tree is declared too.
