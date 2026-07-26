# nvim-config scripts — the stable toolbox

Tested, parameterized Python helpers so a session **calls a script** instead of re-composing
bash/Lua from scratch each time. Fewer tokens, no re-derivation, no footguns (e.g. the
`nvim -c 'lua <<EOF'` heredoc that silently no-ops). These are the source of truth for the
mechanical commands; the reference `.md` files carry the judgment.

Run them by absolute path from the skill directory (`python3 scripts/<name>.py …`, or directly —
they are executable). All are read-only inspectors except where noted, safe to re-run, and resolve
`stdpath` internally (never hardcode `~/.config/nvim`). Every `nvim`/`git`/IO call lives in
`_nvim_common.py`; each script keeps its parsing/formatting as pure functions the tests exercise.

| Script | Purpose | Example |
|---|---|---|
| `nvim_env.py` | Environment discovery — version, config/data/state dirs, plugin manager, structure, git status. **Run first.** | `nvim_env.py` |
| `plugin_info.py <plugin> [symbol] [--fetch]` | A lazy plugin's installed version, lockfile + spec pins, newest tags, drift. With `symbol`: locate it across installed tree / newest tag / Neovim core. | `plugin_info.py telescope.nvim ft_to_lang` |
| `nvim_check.py <check> …` | Runtime verification shortcuts: `startup`, `open <ext>`, `ts <ext>`, `lsp <ext> [server]`, `deprecations`, `api <vim.path>`. | `nvim_check.py api vim.treesitter.language.get_lang` |
| `nvim_lua.py <snippet\|-f file\|->` | Run Lua in headless Neovim **correctly** (temp file + `+luafile`). The primitive under `nvim_check.py`; use directly for one-off checks. `--clean` = no user config, `--wait N` = pre-wait for async LSP. | `nvim_lua.py 'print(vim.version())'` |

## Worked example — the whole telescope/0.12 diagnosis in two calls

```
plugin_info.py telescope.nvim ft_to_lang   # installed_describe=0.1.8, in_installed_tree=1 file, in_nvim_core=nil
nvim_check.py api vim.treesitter.language.get_lang   # = function  → the replacement API exists
```
`ft_to_lang` present in the plugin but `nil` in core = the crash; `get_lang` present in core = the fix
target. Bump the pin, re-run `plugin_info.py` (0 files) + `nvim_check.py open lua` to confirm.

## Conventions for adding scripts

- Python 3.9+, stdlib only. Start with `from __future__ import annotations`; shebang `#!/usr/bin/env python3`; `chmod +x`.
- Keep parsing/analysis/formatting as pure functions; isolate `nvim`/`git`/IO in `_nvim_common.py`. End with `def main(argv=None) -> int` under `if __name__ == "__main__": sys.exit(main())`.
- Print `key<TAB>value` or `label: value` lines; keep output greppable and order stable.
- A module docstring doubling as `--help`. Add tests under `tests/nvim_config/` that call the pure functions directly (no mocking).
