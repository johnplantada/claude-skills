# Optimize workflow — audit every surface for plaintext

Read-only review producing a **prioritized report**. Change nothing without approval; hand each fix
to the workflow that owns it.

## Run the audit

```bash
scripts/credential_audit.py
scripts/store_status.py
```

Exit code is 0 when there are no 🔴 findings and 1 when there are, so it drops into a health sweep
unchanged. `store_status.py` exits 1 when **no** store is usable — a machine with exposures and
nowhere to put them is the worst case and should lead the report.

## Read the report honestly

Findings carry a surface, a location, and a classification — never a value. Three things are easy to
misread:

| Row | Means | Don't read it as |
|---|---|---|
| `finding 🟢 … reference` | the good state, listed so you can see coverage | a problem |
| `finding 🟡 … file-reference` | out of the rc file, still plaintext on disk | done |
| `store.X unusable` | the store is installed but **locked** or signed out — `store.X.reason` says which | absent |

A 🟢 row is deliberate: a report that lists only problems can't show that the *rest* of the machine
is already correct, and that context is what tells you whether one 🔴 is an outlier or the norm.

## Prioritize

Sort by severity **across surfaces**, not per file:

- 🔴 **readable secret** — a literal credential in a shell rc (also exported into every process you
  launch); a world- or group-readable credential file; `credential.helper=store`.
- 🟡 **plaintext but contained** — an owner-only credential file (`mode=0600`); a `file-reference`;
  a gh token in a file instead of the keyring; no credential helper set at all.
- 🟢 **already correct** — store-backed references.

Each finding: **surface · location · what · the workflow that fixes it**.

## Cleanups worth proposing

- **The same credential on two surfaces.** A token in both `~/.zshrc` and `~/.npmrc` means rotation
  is two edits and one will be missed. Collapse to a single store item plus references.
- **A credential file no consumer needs.** `~/.netrc` and `~/.git-credentials` often outlive whatever
  wrote them. Confirm nothing uses it, then delete — the cheapest 🔴 to clear.
- **Eager store lookups at shell start.** Several `export FOO="$(op read …)"` lines cost a process
  spawn each on every shell. Propose lazy functions ([upgrade.md](upgrade.md)); the security property
  is identical and the startup cost goes to zero.
- **Unflagged credentials.** Run `credential_audit.py --all-assignments` and review the redacted
  inventory for service-specific names the heuristic can't know (`STRIPE_SK`, `SLACK_WEBHOOK`, a DSN
  with an embedded password). [setup.md](setup.md) §1 covers delegating that review safely.
- **A store that isn't tracked.** `chezmoi-encryption` present but unused, or a keychain with items
  no rc file references — a store nothing points at provides no benefit.

## Hand off fixes

Group proposals by owning skill so the user can approve one surface at a time — this skill for
migrations, `git-setup` for `credential.helper`, `shell-sync` for placing and mirroring rc lines,
`dotfiles` for what gets committed. Apply only what's approved, then re-run the audit and let
[verification.md](verification.md) prove each migrated credential.

**Never** batch-migrate several credentials in one pass to make the report clean. Each migration
needs its own verification, and a batch that half-works leaves a shell that can't authenticate with
no clear culprit.
