"""Tests for the nvim-config `nvim_env` script — pure detection + formatting only.

No `nvim`/`git` needed: the manager/structure detectors take an injected `exists`
predicate, and the line builders are string functions.
"""

import nvim_env as env

# --- detect_manager ------------------------------------------------------------

def _exists(paths):
    present = set(paths)
    return lambda p: p in present


def test_detect_manager_lazy_via_lockfile():
    exists = _exists({"/cfg/lazy-lock.json"})
    assert env.detect_manager("/cfg", "/data", exists) == "lazy"


def test_detect_manager_lazy_via_data_dir():
    exists = _exists({"/data/lazy"})
    assert env.detect_manager("/cfg", "/data", exists) == "lazy"


def test_detect_manager_packer():
    exists = _exists({"/data/site/pack/packer"})
    assert env.detect_manager("/cfg", "/data", exists) == "packer"


def test_detect_manager_vim_plug_via_autoload():
    exists = _exists({"/cfg/autoload/plug.vim"})
    assert env.detect_manager("/cfg", "/data", exists) == "vim-plug"


def test_detect_manager_vim_plug_via_plugged():
    exists = _exists({"/data/plugged"})
    assert env.detect_manager("/cfg", "/data", exists) == "vim-plug"


def test_detect_manager_mini_deps():
    exists = _exists({"/data/site/pack/deps"})
    assert env.detect_manager("/cfg", "/data", exists) == "mini.deps"


def test_detect_manager_unknown_when_no_markers():
    assert env.detect_manager("/cfg", "/data", lambda p: False) == "unknown"


def test_detect_manager_lazy_wins_over_packer():
    # lazy is checked first; an all-markers-present config still resolves to lazy.
    exists = _exists({"/data/lazy", "/data/site/pack/packer"})
    assert env.detect_manager("/cfg", "/data", exists) == "lazy"


# --- detect_structure ----------------------------------------------------------

def test_detect_structure_modular():
    assert env.detect_structure("/cfg", lambda p: p == "/cfg/lua") == "modular (lua/ tree)"


def test_detect_structure_single_init():
    assert env.detect_structure("/cfg", lambda p: False) == "single init.lua"


# --- format_git_status ---------------------------------------------------------

def test_format_git_status_repo_with_head():
    assert env.format_git_status(True, "abc1234") == "repo @ abc1234"


def test_format_git_status_repo_no_commits():
    assert env.format_git_status(True, None) == "repo @ no commits yet"


def test_format_git_status_not_a_repo():
    assert env.format_git_status(False, None) == "not a git repo"


# --- build_env_lines -----------------------------------------------------------

def test_build_env_lines_shape_and_order():
    lines = env.build_env_lines(
        "NVIM v0.11.2", "/cfg", "/data", "/state", "lazy", "modular (lua/ tree)", "repo @ abc"
    )
    assert lines == [
        "nvim_version\tNVIM v0.11.2",
        "config_dir\t/cfg",
        "data_dir\t/data",
        "state_dir\t/state",
        "plugin_manager\tlazy",
        "structure\tmodular (lua/ tree)",
        "config_git\trepo @ abc",
        "lsp_log\t/state/lsp.log",
        "conform_log\t/state/conform.log",
    ]
