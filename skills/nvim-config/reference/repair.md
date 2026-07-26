# Repair workflow — guided fix of a broken config

Goal: find what broke and fix it, stepping through with the user and confirming at decision
points. Prefer the smallest change that resolves the issue.

## 1. Reproduce & capture (don't guess)

```bash
scripts/nvim_env.py                          # version (did Neovim jump a minor? top suspect) + paths
scripts/nvim_check.py open <ext>             # reproduce on the affected filetype; reads the real error
```
Then, as relevant:
- `scripts/nvim_check.py deprecations` — checkhealth vim.deprecated + a static grep of the config.
- The error names an API? `scripts/nvim_check.py api <vim.path>` — `nil` = removed by a version bump.
- The error names a plugin? `scripts/plugin_info.py <plugin> [symbol]` — installed version, pins, tags,
  and whether the symbol is gone from core / already fixed in a newer tag.
- LSP log: `stdpath('state')/lsp.log`. Formatter log: `stdpath('state')/conform.log` (paths from `nvim_env.py`).

## 2. Triage the failure

Classify the error, then cross-reference [known-issues.md](known-issues.md):

| Symptom | Likely cause |
|---|---|
| `attempt to call method 'range'…` / treesitter query errors | nvim-treesitter `master` on Neovim 0.12 → migrate to `main` |
| A formatter/tool launched as an LSP (`<tool> --lsp` in lsp.log) | mason-lspconfig v2 `automatic_enable` |
| Per-server LSP settings ignored | mason-lspconfig v2 removed `handlers` → use `vim.lsp.config`/`enable` |
| `… is deprecated` / `will be removed` | Neovim API deprecation (see the table) |
| `Failed to run config for <plugin>` | plugin error or major-version API break — read its error |
| `<cmd> not found` / server won't start | missing external CLI (compiler, node, server binary) |

## 3. Plugin-manager health (lazy.nvim)

```bash
scripts/nvim_check.py startup                # Lazy! sync + filter to real error/fail/deprecation lines
```
- Read `lazy-lock.json` to see pinned commits. A plugin failing to load often shows as
  `Failed to run config for …` — open that plugin's spec and its recent breaking changes.
- For non-lazy managers (packer/vim-plug): report findings and advise the equivalent, but don't
  drive them automatically.

## 4. Present findings, then fix (guided)

- Give a **prioritized list**: 🔴 broken → 🟡 deprecated-but-works → 🟢 cleanup, each with
  **root cause + proposed fix + file:line**.
- **Confirm before applying** anything destructive or version-changing (branch switches, deleting
  parsers, config rewrites). Explain what each change does and why.
- Apply fixes **one at a time**; **re-verify after each** (the specific error is gone AND nothing
  regressed). Never batch a pile of edits then hope.

## 5. If a recent update caused it → offer rollback

If breakage started after an update, offer to restore the previous plugin state:
```vim
:Lazy restore        " resets plugins to the commits in lazy-lock.json
```
Restore from a backed-up lockfile if the current one is already updated (see
[upgrade.md](upgrade.md) for the backup convention). Then re-verify.

## 6. Close out

Report: what was broken, the root cause, the fix applied, and verification evidence (before →
after). Note any 🟢 cleanups left as optional, and whether an external tool now needs installing.
