# Verification — prove it resolves, and prove the plaintext is gone

A migration has two halves and both must be checked. Proving the reference works while the original
line still sits in the rc file means the credential is now in **two** places — strictly worse than
before you started.

Every check below is designed to answer with `set`/`EMPTY` or a path, **never a value**.

## Level 1 — the reference resolves, in a fresh login shell

Interactive rc files aren't sourced by the process running the audit, so this must be measured in a
real login shell:

```bash
zsh -l -i -c 'echo "${GITHUB_TOKEN:+set}${GITHUB_TOKEN:-EMPTY}"'
```

Expect `set`. Then the same for the other shell, because a migrated line that wasn't mirrored is
invisible until the day you're in fish:

```bash
fish -l -i -c 'if set -q GITHUB_TOKEN; and test -n "$GITHUB_TOKEN"; echo set; else; echo EMPTY; end'
```

`EMPTY` in one shell and `set` in the other means the mirror is missing — that's **shell-sync**'s
fix, not a store problem.

## Level 2 — the plaintext is gone

```bash
scripts/credential_audit.py --shell-only
```

Expect the variable's row to have moved from 🔴 `literal` to 🟢 `reference`, and expect **no**
remaining row for it anywhere. If the old file surface still reports it, the migration copied rather
than moved.

For a migrated credential *file*, confirm the file is actually gone (`ls`), not merely unreferenced.
Use `rm -P` for a file that held a secret.

## Level 3 — a real consumer still works

Resolution proves the variable is populated; it does not prove the value is *correct*. One real
operation does — a `git push`, an `npm whoami`, an authenticated API call. Run the cheapest one the
credential is actually for, and read its exit status.

This matters most after a **rotation**, where the variable resolves perfectly to a value the
provider has already invalidated.

## What a clean result does and doesn't prove

| Proven | Not proven |
|---|---|
| The variable resolves in both login shells | That non-interactive shells, cron, or GUI apps see it — those don't source interactive rc files |
| No plaintext remains on the scanned surfaces | That no copy exists in a project `.env`, a CI secret, or an app's own config |
| (level 3) The value is currently valid | That it stays valid — a rotation elsewhere invalidates it silently |
| The store is reachable now | That it's reachable when locked, offline, or after a subscription lapses |

Say which levels you actually ran. "The audit is clean" and "I proved the token still pushes" are
different claims, and only the second one covers the failure that brings the user back.

## Never do, while verifying

- **Never print the value** to confirm it "looks right". `${VAR:+set}` is the complete check.
- **Never `cat` a flagged file** to see what tripped the scanner. The finding row is the evidence.
- **Never paste a credential into a command line** — it lands in shell history and in this session.
  Store CLIs prompt for the value interactively for exactly this reason; use that path.
