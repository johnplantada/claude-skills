# Upgrade workflow — update plugins & tooling safely

Goal: bring everything current **without leaving the user broken**. Updates frequently introduce
breakage, so the verification step is mandatory — an upgrade isn't done until it's verified.

## 1. Pre-flight backup (always)

```bash
cp <config>/lazy-lock.json <config>/lazy-lock.json.bak.$(nvim --headless '+lua io.write(os.date("%Y%m%d-%H%M%S"))' +qa 2>&1)
```
- If the config is a git repo, offer to commit the current state first (clean rollback point).
- Record current versions (`nvim --version`, key plugin commits) for the before/after report.

## 2. Update

Run the manager and tooling updates (lazy.nvim):

```bash
nvim --headless "+Lazy! update" +qa 2>&1 | tail -20      # update plugins to latest allowed
nvim --headless "+TSUpdate" +qa 2>&1 | tail -5            # treesitter parsers
nvim --headless "+MasonUpdate" +qa 2>&1 | tail -5         # mason registry/servers (if present)
```
- **Neovim itself:** a new Neovim version usually comes from the OS package manager
  (`brew upgrade neovim`, etc.). **Mention** it and its risk, but don't run an OS-level upgrade
  without explicit consent — it's the biggest breakage source.
- Diff the lockfile to see exactly what moved: `git -C <config> diff lazy-lock.json` (or compare
  to the `.bak` copy).

## 3. Verify — the whole point

Run the full suite from [verification.md](verification.md). Updates commonly break things:
- config still loads with no error;
- real files of each language open with no errors/**new deprecations**;
- LSP clients still attach; treesitter still highlights;
- `:checkhealth vim.deprecated` — did an update newly deprecate an API the config uses?

If anything broke, treat it as a **repair** ([repair.md](repair.md)) and cross-reference
[known-issues.md](known-issues.md) (major-version bumps are the usual culprit).

## 4. Rollback if needed

```vim
:Lazy restore        " restore plugins to the lockfile commits
```
To go back to the pre-upgrade state, restore the `.bak` lockfile first, then `:Lazy restore`.
Re-verify after rolling back.

## 5. Report

- **What updated** (lockfile diff summary: plugins bumped, any major-version jumps).
- **What broke and was fixed**, with evidence.
- **Newly deprecated** APIs to address now or soon.
- Whether a Neovim/OS-level upgrade is still pending and its risk.
