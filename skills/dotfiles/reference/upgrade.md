# Upgrade workflow — change configs & sync across machines

Goal: keep dotfiles current — change a managed config without creating drift between the source and
`$HOME`, and propagate changes to/from other machines. Day-to-day maintenance plus cross-machine
sync live here.

> First-time init or a new-machine bootstrap is [setup.md](setup.md); a secret-bearing file is
> [secrets.md](secrets.md); a broken apply or an unreconcilable conflict is [repair.md](repair.md).

> `scripts/dotfiles_inventory.py` shows every managed file with its live drift code, and
> `scripts/chezmoi_status.py` gives the `status_drift` / `diff_pending` counts. The inline chezmoi
> commands below are what they run under the hood — use them for the actual edit/apply actions.

## Add a new file to management

```bash
chezmoi add <path>                 # plaintext config
chezmoi add --template <path>      # if it has per-machine values -> .tmpl
chezmoi add --encrypt <path>       # secret-bearing -> see secrets.md
chezmoi git -- add -A && chezmoi git -- commit -m "Add <thing>"
```

## Edit a managed file — pick ONE flow, consistently

**Preferred (source-first):**
```bash
chezmoi edit --apply <target>      # edits the SOURCE copy, then applies to $HOME
```
**Alternative (home-first):** edit the live file in `$HOME`, then capture it back:
```bash
chezmoi re-add                     # update source from changed managed home files
# or, for one file: chezmoi re-add <path>
```
Mixing the two without capturing produces drift. If unsure which side changed, run
`chezmoi diff` / `chezmoi status` first and reconcile before editing more.

## Apply source to home

```bash
chezmoi diff                       # ALWAYS preview first — this overwrites home files
chezmoi apply                      # write source -> $HOME (idempotent)
chezmoi apply <target>             # just one file
```

## Reconcile drift

`scripts/dotfiles_inventory.py` tags each managed file with its status code (`--` = in sync):
- `M` in the first column → the **source** differs from home (apply would change home).
- Changes made directly in `$HOME` → `chezmoi re-add` to pull them into source, or
  `chezmoi apply` to discard them in favor of source. Decide with the user which side wins.

## Commit & push

```bash
chezmoi git -- add -A
chezmoi git -- commit -m "<what changed>"
chezmoi git -- push
```

## Pull remote changes onto this machine (sync)

```bash
chezmoi git -- fetch
chezmoi git -- log --oneline HEAD..@{u}    # what's incoming
chezmoi diff                                # what apply would change locally (preview!)
chezmoi update                              # = git pull (in source) + chezmoi apply
```
`chezmoi update` overwrites home files with incoming source — **always `chezmoi diff` first** so
local edits that would be lost are visible. Local edits worth keeping? `chezmoi re-add` and commit
them before updating.

## Handle sync conflicts

The source is a normal git repo — conflicts are git conflicts:
```bash
chezmoi git -- status
chezmoi cd            # drop into the source repo to resolve, then exit
```
Resolve, commit, then `chezmoi apply`. Never resolve by hand-editing `$HOME` files (that just
creates fresh drift). A conflict you can't cleanly resolve, or an apply that then fails, is
[repair.md](repair.md).

## Verify

After any edit: `scripts/chezmoi_status.py` shows `status_drift	0` and `diff_pending	0`
(source == home), and a re-`apply` keeps both at 0 — see [verification.md](verification.md).
