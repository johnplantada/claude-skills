"""Tests for the nvim-config `nvim_check` script — pure filters + Lua builders.

The headless-Neovim runs are isolated in `_nvim_common`/`nvim_lua`; here we pin the
greppable output filters and the snippet builders that shape what those runs report.
"""

import nvim_check as nc

# --- filter_startup ------------------------------------------------------------

def test_filter_startup_keeps_error_and_deprecation_lines():
    out = "Error: bad thing\nall fine here\nfoo is deprecated\n"
    assert nc.filter_startup(out) == ["Error: bad thing", "foo is deprecated"]


def test_filter_startup_drops_git_progress_noise():
    # 'resolving deltas' contains no include word; 'error while resolving' would match
    # include but is excluded by the progress filter.
    out = "receiving objects: 50%\nerror while resolving deltas\nreal error line\n"
    assert nc.filter_startup(out) == ["real error line"]


def test_filter_startup_is_case_insensitive():
    assert nc.filter_startup("ATTEMPT TO index nil") == ["ATTEMPT TO index nil"]


def test_filter_startup_drops_plugin_commit_subjects():
    """The pinned finding, caught by a live health sweep: lazy.nvim prints each plugin's
    commit SUBJECT during sync, and a subject mentioning a deprecation/error is not a
    finding about YOUR config. Keyword matching alone reported these as problems every
    single run, which trains you to ignore the check."""
    out = (
        "\x1b[35m[cmp-nvim-lsp] \x1b[0m\x1b[36mcheckout\x1b[0m\x1b[90m | \x1b[0m"
        "HEAD is now at cbc7b02 Call client methods without generating deprecation "
        "warnings in nvim 0.11+ (#87)\n"
        "[telescope-fzf-native.nvim] checkout | HEAD is now at b25b749 "
        "fix: add shim for deprecated `vim.F.if_nil` (#159)\n"
    )
    assert nc.filter_startup(out) == []


def test_filter_startup_still_reports_a_real_deprecation_during_a_sync():
    # The exclusion must be surgical: a genuine runtime warning in the same output
    # still gets through.
    out = (
        "[plugin] checkout | HEAD is now at abc1234 fix deprecated api usage\n"
        "vim.tbl_islist is deprecated, use vim.islist\n"
    )
    assert nc.filter_startup(out) == ["vim.tbl_islist is deprecated, use vim.islist"]


def test_filter_startup_empty_when_clean():
    assert nc.filter_startup("Lazy sync finished\nall good\n") == []


# --- filter_warn_err -----------------------------------------------------------

def test_filter_warn_err_matches_either_word():
    out = "OK: nothing\nWARNING: vim.tbl_islist deprecated\nERROR: boom\n"
    assert nc.filter_warn_err(out) == [
        "WARNING: vim.tbl_islist deprecated",
        "ERROR: boom",
    ]


# --- static_deprecation_grep ---------------------------------------------------

def test_static_grep_flags_deprecated_call_sites():
    files = [
        ("init.lua", 'local a = vim.loop.now()\nlocal b = 1\nrequire("lspconfig")\n'),
    ]
    assert nc.static_deprecation_grep(files) == [
        "init.lua:1:local a = vim.loop.now()",
        'init.lua:3:require("lspconfig")',
    ]


def test_static_grep_empty_when_no_deprecations():
    assert nc.static_deprecation_grep([("init.lua", "local x = 1\nprint(x)\n")]) == []


# --- Lua snippet builders ------------------------------------------------------

def test_build_open_lua_embeds_path_and_reports_ts():
    lua = nc.build_open_lua("/tmp/s.lua")
    assert "vim.cmd('edit /tmp/s.lua')" in lua
    assert "ts_highlight_active=" in lua
    assert "MSG: " in lua


def test_build_ts_lua_is_minimal_ts_probe():
    lua = nc.build_ts_lua("/tmp/s.lua")
    assert "vim.cmd('edit /tmp/s.lua'); vim.wait(400)" in lua
    assert "ts_highlight_active=" in lua
    assert "MSG:" not in lua


def test_build_lsp_lua_lists_clients():
    lua = nc.build_lsp_lua("/tmp/s.lua")
    assert "vim.lsp.get_clients()" in lua
    assert "lsp_clients: " in lua
    assert "vim.wait(3000)" in lua


def test_build_api_lua_probes_type():
    lua = nc.build_api_lua("vim.treesitter.language.get_lang")
    assert "type(vim.treesitter.language.get_lang)" in lua
    assert "vim.treesitter.language.get_lang = " in lua
    assert "nil/error" in lua
