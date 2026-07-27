# Repair workflow — a reference stopped resolving

The failure mode of a store-backed setup is the opposite of a leak: the variable is **empty**, and
whatever needed it fails somewhere unrelated with a confusing error. Diagnose without ever printing
the value.

## The one diagnostic that's always safe

```bash
zsh -l -i -c 'echo "${GITHUB_TOKEN:+set}${GITHUB_TOKEN:-EMPTY}"'
```

Prints `set` or `EMPTY` — never the value. Use this shape for every check below. **Never** `echo
$TOKEN` to "see what's wrong"; emptiness is the whole diagnosis.

## Symptom → cause → fix

### The variable is empty in a new shell

Work outward from the store:

1. **Is the store reachable?**
   ```bash
   scripts/store_status.py
   ```
   `store.1password unusable` means the CLI is installed but **locked** or signed out (the
   `store.X.reason` row says which); `absent` means it isn't installed at all. The distinction
   matters — a locked store needs unlocking, not installing. Either way it returns nothing and
   exits non-zero, so the shell exports an empty string. Unlock it (out of band) and retry.
2. **Is the item name right?** The reference names an item in the store; a typo yields empty, not an
   error. Verify the item exists **without reading it** — `security find-generic-password -s NAME`
   *without* `-w` prints metadata and exits 0 when found.
3. **Is the line actually reached?** The assignment may sit in an rc file that a non-interactive or
   non-login shell never sources (`~/.zshrc` isn't read by a non-interactive shell). Confirm which
   file it's in with `scripts/credential_audit.py --shell-only`, then let **shell-sync** place it in
   the right file for the shells that need it.

### It works interactively but not in scripts, cron, or an editor's terminal

The reference lives in an interactive-only rc file. A store lookup in `~/.zshrc` doesn't exist for a
`cron` job or a GUI-launched app. Options, in order of preference:

- Have the consumer read from the store directly rather than from the environment.
- Move the assignment to a file the non-interactive shell sources (`~/.zshenv`) — but note it then
  runs a store lookup on **every** shell start, including fast scripted ones.
- For a GUI app, use the store's own integration rather than the environment.

Say which of these you chose and why; they trade correctness against startup cost differently.

### Every shell start became slow

Each store lookup is a process spawn, sometimes a network call. Ten credentials in `~/.zshenv` means
ten spawns per shell. Fix by making the lookup **lazy** — a function that fetches on first use
instead of an eager `export`:

```bash
github_token() { security find-generic-password -s GITHUB_TOKEN -w 2>/dev/null; }
```
Consumers call `$(github_token)`. Startup cost drops to zero and the value still never lands on
disk. `shell-sync`'s startup measurement can confirm the improvement.

### The audit still reports a credential I migrated

Two common causes, both real:

- **The plaintext was copied, not moved** — the store now has it *and* the rc line still assigns a
  literal. That's worse than before. Delete the original line.
- **A second copy exists on another surface** — the same token in `~/.npmrc` or `~/.aws/credentials`.
  The audit reports the surface and path; migrate that one too.

### The audit flags something that isn't a credential

`AUTH_METHOD=oauth` or `TOKEN_NAME=ci` are configuration, not secrets. The name heuristic is
deliberately broad (a false positive costs a glance; a false negative leaves a token on disk). Confirm
it's benign and move on — do **not** rename the variable to dodge the check, which just blinds the
next audit.

## After any fix

```bash
scripts/credential_audit.py
```
Confirm the specific finding is gone and none appeared. Then re-prove resolution in a fresh login
shell ([verification.md](verification.md)) — editing an rc file is the start of a repair, not the end.
