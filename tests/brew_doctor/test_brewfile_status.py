"""Tests for brew-doctor `brewfile_status` pure helpers. No mocking, no `brew` needed."""

import brewfile_status as bs


# --- resolve_brewfile: precedence + ~ expansion ------------------------------

def test_resolve_prefers_explicit_file():
    assert bs.resolve_brewfile("/a/Brewfile", "~/cfg/Brewfile", "/home/u") == "/a/Brewfile"


def test_resolve_falls_back_to_config_then_default():
    assert bs.resolve_brewfile("", "~/cfg/Brewfile", "/home/u") == "/home/u/cfg/Brewfile"
    assert bs.resolve_brewfile("", "", "/home/u") == "/home/u/Brewfile"


def test_resolve_expands_only_a_leading_tilde():
    assert bs.resolve_brewfile("~/dotfiles/Brewfile", "", "/home/u") == "/home/u/dotfiles/Brewfile"
    # a ~ mid-path is left alone
    assert bs.resolve_brewfile("/a/~b/Brewfile", "", "/home/u") == "/a/~b/Brewfile"


# --- entries: declarative lines only, comments stripped, sorted-unique -------

def test_entries_keeps_only_declarative_lines():
    text = (
        "# comment\n"
        'tap "homebrew/cask"\n'
        'brew "neovim"  # editor\n'
        'cask "docker"\n'
        "some_other_directive foo\n"
        'brew "neovim"\n'  # duplicate collapses
    )
    assert bs.entries(text) == ['brew "neovim"', 'cask "docker"', 'tap "homebrew/cask"']


# --- two-way diff -------------------------------------------------------------

def test_only_in_first_and_second_are_set_differences():
    a = ['brew "a"', 'brew "b"']
    b = ['brew "b"', 'brew "c"']
    assert bs.only_in_first(a, b) == ['brew "a"']
    assert bs.only_in_second(a, b) == ['brew "c"']


# --- bundle check gaps --------------------------------------------------------

def test_parse_check_gaps_picks_arrow_and_needs_lines():
    text = (
        "Using neovim\n"
        "neovim → needs update\n"
        "ollama needs to be installed\n"
        "All dependencies satisfied\n"
    )
    assert bs.parse_check_gaps(text) == ["neovim → needs update", "ollama needs to be installed"]
