"""Tests for the runtime-versions `detect_managers` script.

Pure functions -> no mocking, no managers installed needed. The pinned review finding
(commit d34dabb: a commented-out rc hook must NOT count as an active hook) is locked in.
"""

import detect_managers as dm

# --- file_has_active_hook: the commented-out-hook finding ----------------------

def test_active_hook_matches_a_live_line():
    text = 'export NVM_DIR="$HOME/.nvm"\n[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"\n'
    assert dm.file_has_active_hook(text, r"NVM_DIR|nvm\.sh") is True


def test_active_hook_ignores_a_commented_out_line():
    # Pinned finding: a neutralized hook (leading #) is not an active hook.
    text = '# export NVM_DIR="$HOME/.nvm"\n#. "$NVM_DIR/nvm.sh"\n'
    assert dm.file_has_active_hook(text, r"NVM_DIR|nvm\.sh") is False


def test_active_hook_ignores_indented_comment():
    text = '   #   . "$NVM_DIR/nvm.sh"\n'
    assert dm.file_has_active_hook(text, r"nvm\.sh") is False


def test_active_hook_false_when_no_match():
    assert dm.file_has_active_hook("alias ll='ls -la'\n", r"pyenv init") is False


# --- hook_for: collect the matching rc files -----------------------------------

def test_hook_for_returns_space_joined_display_paths():
    contents = [
        ("~/.zshrc", 'eval "$(pyenv init -)"\n'),
        ("~/.bashrc", "# nothing here\n"),
        ("~/.profile", "export PYENV_ROOT=$HOME/.pyenv\n"),
    ]
    assert dm.hook_for(contents, r"pyenv init|PYENV_ROOT") == "~/.zshrc ~/.profile"


def test_hook_for_empty_when_nothing_matches():
    assert dm.hook_for([("~/.zshrc", "alias g=git\n")], r"nvm\.sh") == ""


# --- manager_lines: present/home/hook formatting -------------------------------

def test_manager_lines_absent():
    assert dm.manager_lines("pyenv", False, "/h/.pyenv", False, "") == ["pyenv_present\tno"]


def test_manager_lines_all_signals_in_order():
    lines = dm.manager_lines("nvm", True, "/h/.nvm", True, "~/.zshrc")
    assert lines == [
        "nvm_present\tyes (binary-on-path,home-dir,rc-hook)",
        "nvm_home\t/h/.nvm",
        "nvm_shell_hook\t~/.zshrc",
    ]


def test_manager_lines_hook_only():
    lines = dm.manager_lines("asdf", False, "/h/.asdf", False, "~/.zshrc")
    assert lines == [
        "asdf_present\tyes (rc-hook)",
        "asdf_shell_hook\t~/.zshrc",
    ]


# --- brew_runtimes -------------------------------------------------------------

def test_brew_runtimes_filters_and_joins_with_trailing_space():
    out = "git\nnode\npython@3.13\nripgrep\ngo\n"
    assert dm.brew_runtimes(out) == "node python@3.13 go "


def test_brew_runtimes_none_when_no_runtimes():
    assert dm.brew_runtimes("git\nripgrep\n") == "(none)"


def test_brew_runtimes_nodejs_lookalike_not_matched():
    # `nodeenv` must not match `^node(@|$)`.
    assert dm.brew_runtimes("nodeenv\n") == "(none)"


# --- legacy_shims_on_path ------------------------------------------------------

def test_legacy_shims_numbered_by_path_position():
    path = "/usr/bin:/home/u/.nvm/versions/node/bin:/opt/homebrew/bin:/home/u/.pyenv/shims"
    assert dm.legacy_shims_on_path(path) == (
        "2:/home/u/.nvm/versions/node/bin 4:/home/u/.pyenv/shims "
    )


def test_legacy_shims_none_when_clean():
    assert dm.legacy_shims_on_path("/usr/bin:/opt/homebrew/bin") == "(none)"
