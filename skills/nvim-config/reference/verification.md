# Headless Neovim verification snippets

**Prefer [`scripts/nvim_check.py`](../scripts/README.md)** — it wraps the common checks below as
named subcommands (`startup`, `open`, `ts`, `lsp`, `deprecations`, `api`), and
`scripts/nvim_lua.py` runs arbitrary Lua headlessly without the `-c 'lua <<EOF'` heredoc footgun.
The snippets here are what those scripts run under the hood — reach for them when composing a
**novel** check the scripts don't cover, or to understand/extend a script.

Tested patterns for verifying config changes without an interactive session. All are safe to run
repeatedly. Write throwaway test files to a scratch dir, not the user's project. Substitute the
real language/server/parser names for the placeholders.

## Resolve the important paths first

```bash
CFG=$(nvim --headless "+lua io.write(vim.fn.stdpath('config'))" +qa 2>&1)
DATA=$(nvim --headless "+lua io.write(vim.fn.stdpath('data'))" +qa 2>&1)
STATE=$(nvim --headless "+lua io.write(vim.fn.stdpath('state'))" +qa 2>&1)
# logs: $STATE/lsp.log, $STATE/conform.log   |   parsers/plugins: $DATA/...
```

## Config loads with no error

```bash
nvim --headless "+Lazy! sync" +qa 2>&1 | grep -iE 'error|fail' | grep -viE 'receiving|resolving|counting'
# Healthy = no "Failed to run `config` for <plugin>" lines.
# One transient failure DURING a branch-changing sync can be ignored — re-run clean.
```

## No errors / deprecations on opening real files

```bash
printf 'def f(x):\n    return x\n' > /tmp/t.py       # use a file of the relevant filetype
nvim --headless "+edit /tmp/t.py" "+lua vim.wait(600)" "+messages" +qa 2>&1 \
  | grep -iE 'deprecat|will be removed|E5108|stack traceback|attempt to' | head
# No output = clean.
```

## Treesitter highlighting actually activates

```bash
nvim --headless "+edit /tmp/t.py" "+lua vim.wait(400)" \
  "+lua local b=vim.api.nvim_get_current_buf(); print('ts-highlight=', vim.treesitter.highlighter.active[b]~=nil)" \
  +qa 2>&1 | grep ts-highlight
```

Install parsers to completion on the **main** branch (needs `tree-sitter` CLI):

```bash
nvim --headless "+lua require('nvim-treesitter').install({'python','lua'}):wait(300000)" +qa 2>&1 \
  | grep -iE 'error|compil' | head
```

## An LSP client attaches (with intended settings)

LSP attach is async — wait 2–3s before checking.

```bash
nvim --headless "+edit /tmp/t.py" "+lua vim.wait(3000)" \
  "+lua for _,c in ipairs(vim.lsp.get_clients()) do print(c.name,'| completionProvider:', c.server_capabilities.completionProvider~=nil) end" \
  +qa 2>&1 | grep -iE 'completionProvider|<server-name>'
```

Confirm a specific per-server setting applied:

```bash
nvim --headless "+edit <a-file>" "+lua vim.wait(2500)" \
  "+lua local c=vim.lsp.get_clients({name='<server>'})[1]; print(c and vim.inspect(c.config.settings))" +qa 2>&1
```

List enabled clients (catch an unwanted one, e.g. a formatter launched as LSP):

```bash
nvim --headless "+edit /tmp/t.lua" "+lua vim.wait(2000)" \
  "+lua local n={} for _,c in ipairs(vim.lsp.get_clients()) do n[#n+1]=c.name end print('clients:', table.concat(n,', '))" +qa
```

## Formatter verification (conform.nvim)

Drive **format-on-save** or use `async = true` — do **NOT** call `require('conform').format({...})`
synchronously in `--headless` (it can hang; guard any headless format test with a background
`sleep N; kill -9`).

```bash
printf 'local   x=1\n' > /tmp/t.lua
( nvim --headless "+edit /tmp/t.lua" "+lua vim.wait(200)" "+write" "+lua vim.wait(6000)" +qa ) &
P=$!; ( sleep 20; kill -9 $P 2>/dev/null ) & wait $P 2>/dev/null
cat /tmp/t.lua        # should be reformatted
# Availability + errors:  require('conform').list_formatters(0)  |  $STATE/conform.log
```

## Deprecation audit

```bash
nvim --headless "+checkhealth vim.deprecated" \
  "+lua for _,l in ipairs(vim.api.nvim_buf_get_lines(0,0,-1,false)) do if l:match('WARNING') or l:match('ERROR') then print(l) end end" \
  +qa 2>&1 | grep -iE 'warning|error'
# Static grep of the user's config:
grep -rnE 'vim\.loop|vim\.highlight\.on_yank|tbl_islist|sign_define|goto_prev|goto_next|require\("lspconfig"\)|neodev' "$CFG"
```

## Startup load count (optimization before/after)

```bash
nvim --headless "+lua vim.wait(200)" \
  "+lua local s=require('lazy').stats(); print(string.format('loaded at startup: %d / %d', s.loaded, s.count))" +qa
# Plugins NOT loaded at startup:
nvim --headless "+lua vim.wait(200)" \
  "+lua local d={} for n,p in pairs(require('lazy.core.config').plugins) do if not p._.loaded then d[#d+1]=n end end table.sort(d) print('deferred: '..table.concat(d,', '))" +qa
```

Note: `require('lazy').stats().startuptime` reads `0.0` under `--headless` — use the **load
count** as the meaningful metric. `plugin._.loaded` is a **table** when loaded (truthy), not the
boolean `true` — test truthiness/`~= nil`, not `== true`.
