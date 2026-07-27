"""Tests for the nvim-config `nvim_lua` script — pure arg parsing + command building.

These are the footgun-free contract: the temp-file/`+luafile` mechanics live in `run`,
but what flag maps to what is verified here without launching Neovim.
"""

import nvim_lua as nl
import pytest

# --- parse_lua_args ------------------------------------------------------------

def test_parse_inline_snippet_defaults():
    got = nl.parse_lua_args(["print(1+1)"])
    assert got == nl.LuaArgs(clean=False, wait="0", mode="inline", src="print(1+1)", help=False)


def test_parse_clean_flag():
    got = nl.parse_lua_args(["--clean", "print(1)"])
    assert got.clean is True
    assert got.mode == "inline"
    assert got.src == "print(1)"


def test_parse_wait_flag():
    got = nl.parse_lua_args(["--wait", "500", "print(1)"])
    assert got.wait == "500"
    assert got.src == "print(1)"


def test_parse_file_mode():
    got = nl.parse_lua_args(["-f", "check.lua"])
    assert got.mode == "file"
    assert got.src == "check.lua"


def test_parse_stdin_mode():
    got = nl.parse_lua_args(["-"])
    assert got.mode == "stdin"
    assert got.src is None


def test_parse_help_flag():
    assert nl.parse_lua_args(["-h"]).help is True
    assert nl.parse_lua_args(["--help"]).help is True


def test_parse_last_positional_wins():
    # The bash while-loop lets a later bare arg overwrite an earlier inline snippet.
    assert nl.parse_lua_args(["a", "b"]).src == "b"


def test_parse_wait_missing_value_raises():
    with pytest.raises(ValueError, match="--wait needs a number"):
        nl.parse_lua_args(["--wait"])


def test_parse_file_missing_value_raises():
    with pytest.raises(ValueError, match="-f needs a path"):
        nl.parse_lua_args(["-f"])


# --- build_nvim_cmd ------------------------------------------------------------

def test_build_cmd_plain():
    assert nl.build_nvim_cmd(False, 0, "/tmp/x.lua") == [
        "nvim", "--headless", "+lua vim.wait(0)", "+luafile /tmp/x.lua", "+qa"
    ]


def test_build_cmd_clean_inserts_flag_before_lua():
    assert nl.build_nvim_cmd(True, 600, "/tmp/x.lua") == [
        "nvim", "--headless", "--clean", "+lua vim.wait(600)", "+luafile /tmp/x.lua", "+qa"
    ]


def test_parse_wait_non_numeric_value_raises():
    # The value lands inside `+lua vim.wait(N)` — digits only, so an argument can't
    # smuggle Lua into the headless run.
    with pytest.raises(ValueError, match="--wait needs a number"):
        nl.parse_lua_args(["--wait", "0); os.exit(1"])


# --- nvim absent: the documented rc 3, not a traceback -------------------------


def test_nvim_missing_is_true_when_nvim_is_not_on_path(monkeypatch, tmp_path):
    # PATH is controlled, not mocked — the real shutil.which decides.
    monkeypatch.setenv("PATH", str(tmp_path))
    assert nl.nvim_missing() is True


def test_nvim_missing_is_false_when_a_nvim_executable_resolves(monkeypatch, tmp_path):
    fake = tmp_path / "nvim"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert nl.nvim_missing() is False


def test_main_returns_3_instead_of_crashing_when_nvim_is_absent(monkeypatch, tmp_path, capsys):
    # Regression: `run()` shells out to nvim directly, so a machine without Neovim died
    # with an unhandled FileNotFoundError. CI on a bare macOS runner is exactly that
    # machine, and the smoke suite's contract calls for rc 3.
    monkeypatch.setenv("PATH", str(tmp_path))
    assert nl.main(["print('x')"]) == 3
    assert "not on PATH" in capsys.readouterr().err


def test_help_still_works_without_nvim(monkeypatch, tmp_path):
    # --help documents the tool; needing nvim installed to read it would be absurd.
    monkeypatch.setenv("PATH", str(tmp_path))
    assert nl.main(["--help"]) == 0
