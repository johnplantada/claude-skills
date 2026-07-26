# dotfiles scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the
chezmoi discovery / status / secret-scan bash from scratch each time. Fewer tokens, no
re-derivation, no footguns (e.g. `chezmoi source-path` printing a path even when *not*
initialized, or a hand-written secret grep that prints the secret it found). These are the
source of truth for the mechanical commands; the reference `.md` files carry the judgment.

Run them by absolute path from the skill directory. All three are **read-only inspectors** —
safe to re-run, they never write to the source tree or `$HOME`. They resolve the source dir
via `chezmoi source-path` internally (never hardcode `~/.local/share/chezmoi`), and degrade
gracefully when chezmoi is absent or uninitialized.

| Script | Purpose | Example |
|---|---|---|
| `chezmoi_status.py` | Environment + health: installed? source dir, worktree clean/dirty, remote, config, managed file/dir counts, templates/encrypted, **drift** (`status`/`diff` counts), and a `doctor` summary with any warning/error rows. **Run first.** | `chezmoi_status.py` |
| `dotfiles_inventory.py [--dirs] [--unmanaged]` | Managed inventory in one view: summary counts, then each managed target tagged with its live drift code (`--` = in sync, `MM` = differs). `--unmanaged` also lists add-candidates in `$HOME`. | `dotfiles_inventory.py` |
| `secret_scan.py [path]` | Flags plaintext secrets in the source tree (or an explicit path) by **file path + reason only — never prints values or file contents**. Exit 1 = findings, 0 = clean. Run before every first-add and first-commit. | `secret_scan.py` |

## Worked example — is it initialized, does it drift, is it safe to commit?

```
chezmoi_status.py                    # initialized=yes, status_drift=2, doctor warning=0 → healthy but 2 files drift
dotfiles_inventory.py                # the two MM rows name exactly which files differ from $HOME
secret_scan.py                       # clean → safe to commit; exit 1 + path/reason rows → reconcile first
```
`status_drift=2` from the status script, the two `MM` rows from inventory pinpoint them
(reconcile with `chezmoi re-add` or `chezmoi apply`), and a `clean` from the scanner is the
green light to `chezmoi git -- commit`. A non-zero scanner exit lists each offending path with
a reason (`content:github-token`, `location:secret-by-location`) — encrypt, template, or ignore
it before committing.

## Conventions for adding scripts

- `#!/usr/bin/env python3`, `from __future__ import annotations`, Python 3.9+, stdlib only. Executable
  (`chmod +x`) with a `def main(argv=None) -> int` guarded by `if __name__ == "__main__": sys.exit(main())`.
- **Separate pure logic from IO.** Parsing / correlation / formatting go in plain module functions the
  tests call directly (no mocking); the `chezmoi` / `git` subprocess calls and filesystem walks stay in
  `_dotfiles_common.py`.
- A zero-match secret scan is the GOOD case (`clean`, exit 0); findings are exit 1, usage errors exit 2.
  Keep exit codes and the greppable `key<TAB>value` / `<code><TAB>path` output stable.
- **Never print secret values or file contents** — `secret_scan.py` emits only the file path plus a
  reason (a pattern *name* or a *location*), never the matched text. Any new inspector touching
  secret-bearing files must do the same.
- The module docstring doubles as `--help`.
