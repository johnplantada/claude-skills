# Setup workflow — pick a store, migrate literals into it, delete the plaintext

Goal: every credential lives in one store, and every config **references** it. Work one credential
at a time; a half-finished batch leaves a shell that can't authenticate.

## 0. Audit, and pick the destination

```bash
scripts/credential_audit.py
scripts/store_status.py
```

The first ranks what's exposed; the second says where it can go and prints the exact
`reference_form` for the recommended store. **Never migrate into a store reported `absent`** — the
reference will resolve to an empty string and the failure surfaces later, somewhere unrelated.

If every store is absent, install one first (`keychain` needs nothing on macOS; `op` and `pass` come
from `brew-doctor`).

---

## 1. Review what the heuristic missed — the one step worth a subagent

`credential_audit.py` flags credential-*shaped* names (`*_TOKEN`, `*_API_KEY`, `*_SECRET`). It
cannot know that `STRIPE_SK` is a Stripe secret key, that `SLACK_WEBHOOK` is a credential, or that a
bare `DSN` embeds a password. That judgment needs world knowledge over a messy inventory — the one
shape where a subagent pays for itself.

**It is safe to delegate only because the input is redacted.** Generate the value-free view:

```bash
scripts/credential_audit.py --all-assignments --shell-only
```

Every row is `path:line`, variable name, classification (`literal`/`reference`/`path`/`empty`), and
whether the heuristic flagged it. **No values.** Hand *that output* to the subagent — never the rc
files themselves:

> Below is a redacted inventory of every variable assignment in this machine's shell startup files:
> `path:line`, variable name, how the value is supplied, and whether a name heuristic flagged it as
> a credential. No values are included and you must not read the source files. Identify rows that
> are almost certainly credentials but were NOT flagged (`flagged=no`) — service-specific key names,
> webhook URLs, connection strings that embed a password, license keys. For each, give the row, what
> service it belongs to, and your confidence. Report only; change nothing.

Add its hits to the migration list, confirm the list with the user, then continue below.

*Skip the subagent* when the inventory is short enough to read at a glance — a dozen assignments
doesn't need a context prime.

---

## 2. Migrate one credential — the four steps, in this order

For each credential, in order. **Do not reorder**: the plaintext is the fallback until the reference
is proven.

**a. Put the value in the store — out of band.** The user runs this; the value must not pass
through a message or a report. For keychain:

```bash
security add-generic-password -a "$USER" -s GITHUB_TOKEN -w
```
Run with no `-w` argument, it prompts for the value interactively — which is the point: it never
appears in a command line, in shell history, or in this session.

**b. Switch the rc line to a reference.** Back up the file first.

```bash
export GITHUB_TOKEN="$(security find-generic-password -s GITHUB_TOKEN -w 2>/dev/null)"
```

**c. Verify in a NEW login shell** — see [verification.md](verification.md). The check is that the
variable is non-empty, not what it contains.

**d. Only now remove the plaintext.** Delete the old line (it's already gone if you edited in place)
and confirm the audit no longer reports it.

Repeat per credential. Re-run `scripts/credential_audit.py` between migrations so a regression is
attributed to the line that caused it.

## 3. Mirror to the other shell

A migrated line must exist in **both** zsh and fish, or the credential silently vanishes in one of
them. fish syntax differs:

```fish
set -gx GITHUB_TOKEN (security find-generic-password -s GITHUB_TOKEN -w 2>/dev/null)
```
Propagating rc changes across shells is **shell-sync**'s job — hand off rather than hand-editing
both, so the two don't drift.

## 4. Fix the non-shell surfaces

- **git** — `git config --global credential.helper osxkeychain` (replaces `store`, which writes
  cleartext). Owned by `git-setup`.
- **gh** — re-run `gh auth login` and choose keyring storage when the audit reports `gh.storage file`.
- **`~/.aws/credentials`** — replace the static keys with a `credential_process` entry that fetches
  from the store, or switch to SSO; then delete the file.
- **`~/.npmrc` / `~/.pypirc`** — replace the inline token with `${NPM_TOKEN}`, which npm expands from
  the environment your rc now populates from the store.

## 5. Track the result

The rc files are dotfiles — version them via **dotfiles**. This is now safe *because* they contain
references, not values, which is the property that makes the whole config committable. Re-run
`dotfiles`' `secret_scan.py` before the first commit to confirm.
