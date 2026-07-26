"""Tests for the dotfiles `dotfiles_inventory` script — pure functions only."""

import pytest

import dotfiles_inventory as di


# --- status_code: the status<->managed correlation -----------------------------

def test_status_code_matches_exact_target_and_returns_two_char_code():
    status = "MM dot_zshrc\n M dot_gitconfig\n"
    assert di.status_code(status, "dot_zshrc") == "MM"
    assert di.status_code(status, "dot_gitconfig") == " M"


def test_status_code_returns_none_for_in_sync_target():
    assert di.status_code("MM dot_zshrc\n", "dot_vimrc") is None


def test_status_code_does_not_match_on_a_substring_path():
    # The stripped path must equal the target exactly, not merely contain it.
    status = "MM dot_config/nvim/init.lua\n"
    assert di.status_code(status, "init.lua") is None
    assert di.status_code(status, "dot_config/nvim/init.lua") == "MM"


# --- managed_rows --------------------------------------------------------------

def test_managed_rows_tags_each_target_with_code_or_placeholder():
    managed = "dot_zshrc\ndot_vimrc\n"
    status = "MM dot_zshrc\n"
    assert di.managed_rows(managed, status) == [
        "MM\tdot_zshrc",
        "--\tdot_vimrc",
    ]


def test_managed_rows_skips_blank_lines():
    assert di.managed_rows("a\n\nb\n", "") == ["--\ta", "--\tb"]


# --- parse_args ----------------------------------------------------------------

def test_parse_args_defaults():
    assert di.parse_args([]) == (False, False)


def test_parse_args_flags():
    assert di.parse_args(["--dirs", "--unmanaged"]) == (True, True)


def test_parse_args_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        di.parse_args(["--help"])
    assert exc.value.code == 0


def test_parse_args_unknown_flag_exits_two(capsys):
    with pytest.raises(SystemExit) as exc:
        di.parse_args(["--bogus"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unknown arg: --bogus" in err
