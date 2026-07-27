# Optimize workflow — audit every declared tree for a surface that drifted

Read-only review of the whole profile map, producing a **prioritized gap report**. Change nothing
without approval; hand each fix to the workflow that owns it.

## Run the audit

```bash
scripts/profile_audit.py
```

One pass covers every declared profile. Exit code is 0 when there are no 🔴 gaps and 1 when there
are, so it drops into a health sweep unchanged.

## Read the report honestly

The fact rows come before the gap rows. Three statuses are **not** passes, and reading them as
passes is the failure mode this report is shaped to prevent:

| Status | Means | Don't read it as |
|---|---|---|
| `undetermined` | the check could not run at all | clean |
| `no-file` / `no-pubkey` / `no-identityfile` | an input was missing, so nothing was compared | configured |
| `n/a-not-a-path` | the signing key is a GPG id, so the ssh key comparison doesn't apply | mismatch |
| `n/a-literal-key` | the signing key is inline key material (git's `key::` form), so there is no path to compare | mismatch |

If a finding contradicts what the config visibly says, verify it a second way before reporting it —
`git_identity.py <repo>` for the git surface, `ssh -G <alias>` for ssh. A false positive costs the
user a real change to a working setup, which is worse than a missed finding.

## Prioritize

Present findings sorted by severity **across profiles**, not grouped per profile:

- 🔴 **actively wrong** — `key_match mismatch` (pushes go out as the other identity),
  `allowed_signers missing` while signing is on (commits show Unverified), no email resolving in a
  declared tree.
- 🟡 **works but unenforced** — signing off; an https origin (no per-alias key selection); a
  declared tree with no repo to verify against; `ssh -G` reporting no identityfile.

Each finding: **profile · surface · what · the workflow that fixes it**.

## Common cleanups worth proposing

- **A stale `includeIf` rule** — `probe_repo undetermined` on a tree that no longer exists. Drop the
  rule; a rule that matches nothing is a false sense of coverage.
- **https origins inside a declared tree.** They work, but the tree's key never applies, so the
  profile is advisory rather than enforced. Offer to switch them to the alias.
- **`IdentitiesOnly` missing** on a profile's `Host` block. Without it ssh offers every agent key
  and the server accepts the first that works — the alias stops being a guarantee. (Fix belongs to
  `ssh-config`; flag it here because only the cross-surface view shows why it matters.)
- **Two profiles sharing one key.** Legal, but it means the ssh surface can't distinguish them —
  `key_match` will pass for both and the alias enforces nothing. Worth naming explicitly.
- **A default identity that isn't neutral.** If `~/.gitconfig` carries the work email, every repo
  outside a declared tree silently commits as work. Consider `user.useConfigOnly true`
  ([upgrade.md](upgrade.md)).

## Hand off fixes

Group proposals by the skill that owns the fix so the user can approve one surface at a time —
`git-setup` for signing setup and history, `ssh-config` for keys and `Host` blocks, this skill for
the tree↔alias mapping. Apply only what's approved, then re-run the audit and let
[verification.md](verification.md) prove the profile you touched.
