# Repair workflow — fix a broken chezmoi state

Goal: get chezmoi healthy again — `chezmoi apply` fails on a file, drift you can't reconcile, a
source git conflict, or an `apply` that overwrote a hand edit you wanted. Diagnose with chezmoi's
own tools (never by eyeballing the source), fix the cause, re-apply, and prove it's back in sync.

> **Diagnose with the read-only scripts:** `scripts/chezmoi_status.py` (drift counts + a `doctor`
> summary with `doctor_issue` rows), `scripts/dotfiles_inventory.py` (which files differ). Verify by
> re-reading state — [verification.md](verification.md). If a secret-bearing file is involved, its
> plaintext is **never** read into this session — check status/exit codes, not contents
> ([secrets.md](secrets.md)).

## 1. Symptom → cause

| Symptom | Likely cause | Check |
|---|---|---|
| `apply` fails on a `.tmpl` file | template can't render (missing var, bad syntax) | `chezmoi cat <target>` shows the render error |
| `apply` fails on an `encrypted_*` file | the `age`/`gpg` key isn't present on this machine | `chezmoi_status.py` `doctor_issue`; is the key at the configured path? |
| `apply` fails pulling a secret | password manager unreachable / not signed in | `doctor_issue` row; is the manager running? |
| persistent drift that won't clear | edits on both sides (source and `$HOME`) | `dotfiles_inventory.py` (`MM` rows) |
| a hand edit got overwritten by `apply` | source was authoritative; edit wasn't captured | recover from source git history |
| source won't push/pull | git conflict in the source repo | `chezmoi git -- status` |

## 2. Fix the cause

- **Template render error** — `chezmoi cat <target>` prints the failure. Fix the `.tmpl` (a missing
  `{{ .chezmoi.* }}` var, a data key that doesn't exist here), then re-apply just that file.
- **Missing decryption key** — the `age`/`gpg` identity must be transferred out of band to this
  machine and pointed at by `~/.config/chezmoi/chezmoi.toml`. The private key is never in the repo —
  copy it in securely, don't paste it through this session ([secrets.md](secrets.md)).
- **Unreachable password manager** — sign in / unlock it, then re-apply; the secret is fetched at
  apply time. Don't work around it by writing the value into the file.
- **Two-sided drift** — decide per file which side wins: `chezmoi re-add <path>` keeps the `$HOME`
  edit; `chezmoi apply <path>` keeps source. `dotfiles_inventory.py` names each drifting file.
- **Overwritten hand edit** — recover the prior source version from git: `chezmoi cd`, then
  `git log`/`git show` the file, restore it, `chezmoi apply`.
- **Source conflict** — `chezmoi cd`, resolve the git conflict, commit, exit, `chezmoi apply`. Never
  hand-edit `$HOME` to "fix" it (fresh drift).

## 3. Verify

```bash
scripts/chezmoi_status.py            # status_drift 0, diff_pending 0, doctor warning=0 error=0
chezmoi apply && chezmoi apply       # second run a no-op (idempotent)
```
Back to `0` drift and a clean `doctor`, with the previously-failing file now applying — see
[verification.md](verification.md). An apply that still fails is almost always a missing key or
unreachable secret source, not a chezmoi bug.
