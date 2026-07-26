# Optimize workflow — review the whole config, plan, then implement

Goal: make a **working** config faster, cleaner, and more modern — as a deliberate, reviewed
effort. Audit first, **present a plan, get approval, then implement incrementally**. Do not start
editing before the plan is agreed.

## 1. Audit (gather only — change nothing yet)

Collect a full picture using [verification.md](verification.md):

- **Startup** — `require('lazy').stats()` load count (`loaded/count`) and the list of plugins
  loaded eagerly at startup. `:Lazy profile` for per-plugin cost.
- **Eager vs lazy** — plugins with no `event`/`cmd`/`keys`/`ft` that aren't startup-critical
  (telescope→`cmd`, mason→`cmd`, tool-installers→`VeryLazy`, filetype tools→`ft` are classic wins).
- **Deprecations** — the grep + `:checkhealth vim.deprecated` (see known-issues.md table).
- **Redundancy / dead code** — duplicate autocmds, overlapping plugins (two fuzzy finders, two
  comment plugins), unreferenced files/modules, plugins installed but never configured/used.
- **Keymap conflicts** — same lhs bound twice; missing which-key group labels.
- **Health** — `:checkhealth` summary for warnings worth acting on.

## 2. Plan (present, then get approval)

Produce a **prioritized optimization plan** — each item with **impact**, **risk**, and the
concrete change. Order by value/risk. Example shape:

| # | Change | Impact | Risk |
|---|---|---|---|
| 1 | Lazy-load telescope (`cmd`) & mason (`cmd`) | fewer plugins at startup | low |
| 2 | Modernize deprecated APIs | future-proof (0.13/0.14) | low |
| 3 | Remove duplicate markdown autocmd / dead module | cleanliness | low |
| 4 | Drop overlapping plugin X (superseded by Y) | less to load/maintain | medium |

**Wait for the user to approve** (and let them defer/skip items). Keep behavior-preserving
changes separate from opinionated ones.

## 3. Implement incrementally

- One change (or one tight group) at a time.
- **Verify after each**: for startup work, capture the **before/after load count**; for API
  changes, confirm no new errors/deprecations; for LSP edits, confirm clients still attach with
  capabilities intact.
- If a change regresses anything, revert it and note why.

## 4. Report

- **Before/after metrics**: startup load count, deprecation count, plugin count.
- What changed (file:line), and what was intentionally left as optional.
- Any follow-ups surfaced (e.g. formatters installed but not wired to run → offer conform.nvim;
  linters not wired → offer nvim-lint).
