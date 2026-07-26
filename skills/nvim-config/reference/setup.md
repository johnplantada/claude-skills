# Setup workflow — create a tailored Neovim config

Goal: stand up a working config that matches what the user actually wants. Greenfield, or a
deliberate fresh start. lazy.nvim-based.

## 1. Guard existing config

Check `stdpath('config')`. **If a config already exists there:**
- Do NOT overwrite. Ask whether to (a) back it up and start fresh, or (b) switch to
  **repair**/**optimize** instead.
- If starting fresh, back up first: `mv <config> <config>.bak.<timestamp>` (or copy). Confirm
  the move with the user before doing it.

## 2. Check prerequisites

Report which are present/missing (don't silently assume):

| Tool | Needed for |
|---|---|
| Neovim ≥ 0.10 (0.11+ preferred) | everything; check `nvim --version` |
| `git` | plugin manager clones |
| C compiler (`cc`/`gcc`/`clang`) | treesitter, some plugins |
| `tree-sitter` CLI (`npm i -g tree-sitter-cli`) | nvim-treesitter `main` parser builds |
| `node` + `npm` | many LSP servers, prettier |
| `ripgrep` (`rg`) | telescope live-grep |
| a Nerd Font | icons (devicons, statusline) |

## 3. Interview the user

Ask (batch the questions):

1. **Base** — which foundation:
   - **Bespoke minimal** — the skill generates a small modular config with only what they pick.
   - **kickstart.nvim** — single well-commented `init.lua`; great for learning/hackable.
   - **LazyVim** — full distro with sane defaults + extras; least setup, most opinionated.
2. **Languages/filetypes** they work in → drives LSP servers, treesitter parsers, formatters.
3. **Features** they want: LSP + completion, formatting (conform.nvim), linting (nvim-lint),
   fuzzy finder (telescope), file explorer (nvim-tree/neo-tree), git signs, statusline,
   AI assistant (e.g. claudecode.nvim), which-key.
4. **Aesthetics** — colorscheme (tokyonight/catppuccin/gruvbox/…), transparency.
5. **Keys/level** — leader key (default `<space>`), and their experience level (affects how much
   is commented / how minimal).

## 4. Build, by chosen base

### Bespoke minimal
Generate a modular tree and write **modern, non-deprecated** code from the start (follow
[known-issues.md](known-issues.md) so it isn't born broken on 0.11/0.12):

```
init.lua                     -- leader, lazy.nvim bootstrap, require config.*, lazy.setup("plugins")
lua/config/options.lua       -- vim.opt
lua/config/keymaps.lua       -- global keymaps
lua/config/autocmds.lua      -- autocmds
lua/plugins/                 -- one file per concern (colorscheme, treesitter, lsp, cmp, …)
```
Key modern patterns to use:
- **lazy.nvim bootstrap** with `vim.uv.fs_stat` (not `vim.loop`).
- **nvim-treesitter `branch = "main"`**: `install{ langs }` + a `FileType` autocmd calling
  `vim.treesitter.start()`; nvim-ts-autotag as a standalone plugin.
- **LSP**: mason + mason-lspconfig **v2** (`automatic_enable = false` + explicit
  `vim.lsp.enable(servers)`); per-server config via `vim.lsp.config(name, {...})`; `lazydev.nvim`
  for editing Lua config.
- **Formatting**: conform.nvim with a generous `timeout_ms` (Python tools cold-start slowly).
- **Lazy-load** everything non-essential (`event`/`cmd`/`keys`/`ft`); keep only colorscheme,
  statusline, treesitter, file explorer eager.

### kickstart.nvim
`git clone https://github.com/nvim-lua/kickstart.nvim <config>`. Then customize the single
`init.lua` to the interview answers (servers, formatters, theme, extra plugins).

### LazyVim
Use the LazyVim starter: `git clone https://github.com/LazyVim/starter <config>` then remove its
`.git`. Enable language **extras** and add user plugins under `lua/plugins/` per the answers.

## 5. Install & verify

- Trigger install headless: `nvim --headless "+Lazy! sync" +qa` (then parser/LSP installs; for
  treesitter `main`, run `require('nvim-treesitter').install({...}):wait(...)`).
- Verify with [verification.md](verification.md): config loads clean, chosen LSPs attach,
  treesitter highlights the chosen filetypes, formatters run.
- Summarize what was installed, the key keymaps, and next steps (e.g. install a Nerd Font, add
  more languages later via the same workflow).
