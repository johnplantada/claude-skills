# Upgrade workflow — rotate a credential, or move to a different store

Both operations share one hazard: a credential has **consumers you've forgotten**, and the failure
shows up later somewhere unrelated. Enumerate first, switch second.

## Rotate a credential

1. **Enumerate consumers before touching anything.** The same secret is often on several surfaces:
   ```bash
   scripts/credential_audit.py --all-assignments
   ```
   Grep the redacted inventory for the variable name across every rc file, then check the non-shell
   surfaces (`~/.npmrc`, CI secrets, a `.env` in a project, the store item's own usages). Write the
   list down — this is the step people skip.
2. **Issue the new credential** at the provider. Don't revoke the old one yet.
3. **Update the store item — out of band.** The user runs it; the value never passes through this
   session:
   ```bash
   security add-generic-password -U -a "$USER" -s GITHUB_TOKEN -w
   ```
   `-U` updates an existing item. Because everything *references* the item, this single write is the
   entire rotation for every shell consumer — that's the payoff of the reference model.
4. **Verify** in a fresh login shell ([verification.md](verification.md)), then exercise one real
   consumer (a `git push`, an API call) to confirm the new value actually works.
5. **Now revoke the old credential** at the provider, and confirm nothing broke.

If a consumer holds its own copy (a CI secret, a `.env`), rotation is not one write — update each,
then revoke. That's the cost of every copy that isn't a reference, and worth naming to the user.

## Move to a different store

Migrating keychain → 1Password (or adopting `pass`) is a per-credential repeat of setup, with one
rule: **run both in parallel until the new one is proven.**

1. `scripts/store_status.py` — confirm the new store is `available`, not just installed.
2. For each credential: write it into the new store (out of band), change the rc line to the new
   `reference_form`, verify in a fresh shell.
3. Only after every credential verifies, remove the items from the old store.

Never delete from the old store first. A store that's locked, unreachable, or subscription-expired
silently yields empty — and if the old copy is already gone, the credential is gone.

## Tighten a `file-reference` into a real reference

A 🟡 `file-reference` (`$(cat ~/.mytoken)`) keeps the secret out of the rc file but leaves it
readable on disk. Upgrading is a plain migration:

1. Move the file's contents into the store — out of band, e.g. piping the file directly into the
   store's stdin so the value never appears in a report.
2. Switch the rc line to the store reference.
3. Verify, then **shred the file** (`rm -P` on macOS) rather than a plain `rm`.

## Adopt lazy resolution

Once several credentials are store-backed, eager `export` lines cost a process spawn each at every
shell start. Converting them to lazy functions (see [repair.md](repair.md)) is a pure win — same
security property, no startup cost. Worth proposing when the audit shows more than a handful of
store-backed exports; measure with `shell-sync` before and after so the claim is real.
