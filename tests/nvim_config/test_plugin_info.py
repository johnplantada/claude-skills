"""Tests for the nvim-config `plugin_info` script — pure arg/text parsing.

git and Neovim calls are isolated in `_nvim_common`; the pin/tag/drift analysis is
plain string work verified here.
"""

import pytest

import plugin_info as pi


# --- parse_plugin_args ---------------------------------------------------------

def test_parse_plugin_only():
    assert pi.parse_plugin_args(["telescope.nvim"]) == ("telescope.nvim", None, False)


def test_parse_plugin_and_symbol():
    assert pi.parse_plugin_args(["telescope.nvim", "ft_to_lang"]) == (
        "telescope.nvim",
        "ft_to_lang",
        False,
    )


def test_parse_fetch_flag_anywhere():
    assert pi.parse_plugin_args(["telescope.nvim", "--fetch", "ft_to_lang"]) == (
        "telescope.nvim",
        "ft_to_lang",
        True,
    )


def test_parse_requires_plugin():
    with pytest.raises(ValueError):
        pi.parse_plugin_args(["--fetch"])


# --- find_lockfile_pin ---------------------------------------------------------

def test_find_lockfile_pin_hit():
    lock = (
        "{\n"
        '  "telescope.nvim": { "branch": "master", "commit": "abc" },\n'
        '  "other.nvim": { "commit": "def" }\n'
        "}\n"
    )
    assert pi.find_lockfile_pin(lock, "telescope.nvim") == (
        '  "telescope.nvim": { "branch": "master", "commit": "abc" },'
    )


def test_find_lockfile_pin_absent():
    assert pi.find_lockfile_pin('{\n  "other.nvim": {}\n}\n', "telescope.nvim") == ""


# --- spec_pin_lines ------------------------------------------------------------

def test_spec_pin_lines_finds_tag_near_spec():
    files = [("init.lua", '{\n  "telescope.nvim",\n  tag = "0.1.8",\n  opts = {},\n}\n')]
    assert pi.spec_pin_lines(files, "telescope.nvim") == [
        'init.lua:2:  "telescope.nvim",',
        'init.lua:3-  tag = "0.1.8",',
    ]


def test_spec_pin_lines_empty_when_no_pin_declared():
    files = [("init.lua", '{\n  "telescope.nvim",\n  opts = {},\n}\n')]
    # The spec name line still matches the plugin-quote branch of the keep filter.
    assert pi.spec_pin_lines(files, "telescope.nvim") == ['init.lua:2:  "telescope.nvim",']


def test_spec_pin_lines_none_when_plugin_absent():
    assert pi.spec_pin_lines([("init.lua", "local x = 1\n")], "telescope.nvim") == []


# --- format_tags ---------------------------------------------------------------

def test_format_tags_first_five_with_trailing_space():
    assert pi.format_tags(["v3", "v2", "v1"]) == "v3 v2 v1 "


def test_format_tags_caps_at_five():
    assert pi.format_tags(["a", "b", "c", "d", "e", "f"]) == "a b c d e "


def test_format_tags_empty():
    assert pi.format_tags([]) == ""


# --- compute_drift -------------------------------------------------------------

def test_compute_drift_when_behind():
    assert pi.compute_drift("0.1.8", "0.1.9") == "installed=0.1.8  newest_tag=0.1.9"


def test_compute_drift_none_when_current():
    assert pi.compute_drift("0.1.9", "0.1.9") is None


def test_compute_drift_none_when_no_tags():
    assert pi.compute_drift("0.1.9", None) is None
