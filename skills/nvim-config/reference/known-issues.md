# Known breakages — modern lazy.nvim + Neovim 0.11 / 0.12

Catalog of recurring failure modes in current lazy.nvim configs, with the fix. When something
breaks after a Neovim or plugin update, check here first — the same causes recur across configs.
Symptom → cause → fix.

## Neovim minor-version bump breaks plugins (check this FIRST)

- **Symptom:** things that worked yesterday now error; often after a `brew upgrade` / package
  update.
- **Cause:** Neovim minor releases (0.11→0.12) remove deprecated APIs and change treesitter/LSP
  internals. Plugins pinned to old versions break.
- **Fix:** `nvim --version` first. If it jumped, expect treesitter/LSP/deprecation breakage below;
  update the affected plugins (and their branches) to versions that support the new Neovim.

## nvim-treesitter: `master` → `main` branch

- **Symptom:** `attempt to call method 'range' (a nil value)` / query-predicate errors, often on
  markdown, on Neovim 0.12.
- **Cause:** the `master` branch is frozen and supports Neovim ≤ 0.11 only.
- **Fix:** use `branch = "main"` and its rewritten API:
  - `require('nvim-treesitter').setup()` + `require('nvim-treesitter').install({ langs })`.
  - Highlighting is **not automatic** — a `FileType` autocmd calls `vim.treesitter.start(buf, lang)`
    when a parser exists (`vim.treesitter.get_parser(buf, lang, {error=false})`).
  - Parsers compile with the **`tree-sitter` CLI** (`npm i -g tree-sitter-cli`; the Homebrew
    `tree-sitter` formula is the library only). Installed parsers land under `stdpath('data')/site/parser/`.
  - `nvim-ts-autotag` is now a **standalone** plugin (`opts = {}`), not a treesitter module.
  - After switching branches, delete stale `<data>/lazy/nvim-treesitter/parser/*.so` — old
    master-built parsers shadow the new ones on the runtimepath.
  - Neovim 0.12 auto-starts treesitter for some bundled filetypes (e.g. markdown) via a core
    ftplugin; a plugin-level guard can't stop it — use `after/ftplugin/<ft>.lua` →
    `pcall(vim.treesitter.stop)` if another plugin should own that filetype.

## mason-lspconfig v1 → v2

- **Symptom A:** a formatter/tool (e.g. `stylua`) is launched as an LSP → `<tool> --lsp` error in
  `lsp.log`.
  - **Cause:** v2's `automatic_enable` (default on) enables every installed mason package that has
    a matching `lsp/<name>.lua` in nvim-lspconfig — including some formatters.
  - **Fix:** `require('mason-lspconfig').setup({ ensure_installed = servers, automatic_enable = false })`
    and explicit `vim.lsp.enable(servers)`.
- **Symptom B:** per-server settings/capabilities are silently ignored (e.g. `lua_ls` doesn't know
  the `vim` global; completion capabilities not advertised).
  - **Cause:** v2 **removed the `handlers` API**; old `handlers = {...}` blocks do nothing.
  - **Fix:** native config —
    ```lua
    vim.lsp.config("*", { capabilities = require("cmp_nvim_lsp").default_capabilities() })
    vim.lsp.config("<server>", { settings = { ... } })
    require("mason-lspconfig").setup({ ensure_installed = servers, automatic_enable = false })
    vim.lsp.enable(servers)
    ```

## API deprecations (0.11+, removed in 0.13–0.14)

| Deprecated | Replacement |
|---|---|
| `vim.loop.*` | `vim.uv.*` |
| `vim.highlight.on_yank` | `vim.hl.on_yank` |
| `vim.fn.sign_define("DiagnosticSign*")` | `vim.diagnostic.config({ signs = { text = { [severity] = icon } } })` |
| `vim.diagnostic.goto_prev/goto_next` | `vim.diagnostic.jump({ count = ±1, float = true })` |
| `vim.tbl_islist` | `vim.islist` (update the plugin that calls it, e.g. old Telescope tags) |
| `require("lspconfig")[server].setup{}` | `vim.lsp.config(server, {})` + `vim.lsp.enable(server)` |
| `folke/neodev.nvim` (archived) | `folke/lazydev.nvim` (`ft = "lua"`) |

## Formatting (conform.nvim)

- **Python formatters need a generous on-save timeout.** `isort`/`black` are Python CLIs with a
  slow cold start (~2–4s combined on the first save of a session) and they **share** the
  `timeout_ms` budget → 1s/3s time out; **5s works**. Warm saves are ~150ms; `timeout_ms` is only
  a ceiling. Rust (`stylua`) and Node (`prettier`) tools are fast.
- **Verify via format-on-save or `async = true`** — a synchronous `require('conform').format()` in
  `--headless` can hang (guard headless tests with a background `sleep N; kill -9`). Check
  availability with `require('conform').list_formatters(0)` and `stdpath('state')/conform.log`.

## Verification gotchas

- LSP attach is async — `vim.wait(2000–3000)` before checking `vim.lsp.get_clients()`.
- `lazy.core.config.plugins[name]._.loaded` is a **table** when loaded (truthy), not `true`.
- `require('lazy').stats().startuptime` is `0.0` under `--headless`; use the load count instead.
- A `Failed to run config` line can appear transiently during a branch-changing sync — re-run
  `+Lazy! sync` clean before treating it as real.
