"""Tests for the runtime-versions `tool_resolve` script — pure classify/format logic."""

import tool_resolve as tr


# --- classify: manager attribution, first-match-wins ---------------------------

def test_classify_mise():
    assert tr.classify("/Users/x/.local/share/mise/installs/node/20/bin/node") == "mise"
    assert tr.classify("/Users/x/.local/share/mise/shims/node") == "mise"


def test_classify_legacy_managers():
    assert tr.classify("/Users/x/.nvm/versions/node/v20/bin/node") == "nvm"
    assert tr.classify("/Users/x/.pyenv/shims/python") == "pyenv"
    assert tr.classify("/Users/x/.rbenv/shims/ruby") == "rbenv"
    assert tr.classify("/Users/x/.asdf/shims/node") == "asdf"


def test_classify_fnm_variants():
    assert tr.classify("/Users/x/.fnm/node-versions/v20/bin/node") == "fnm"
    assert tr.classify("/tmp/fnm_multishells/123/bin/node") == "fnm"
    assert tr.classify("/Users/x/Library/Caches/fnm_something/node") == "fnm"


def test_classify_homebrew():
    assert tr.classify("/opt/homebrew/bin/node") == "homebrew"
    assert tr.classify("/usr/local/Cellar/node/20/bin/node") == "homebrew"
    assert tr.classify("/usr/local/opt/node/bin/node") == "homebrew"


def test_classify_system():
    assert tr.classify("/usr/bin/python3") == "system"
    assert tr.classify("/bin/sh") == "system"


def test_classify_other():
    assert tr.classify("/some/weird/path/node") == "other"


# --- format_on_path ------------------------------------------------------------

def test_format_on_path_lists_entries_with_trailing_space():
    entries = ["/opt/homebrew/bin/node", "/usr/local/bin/node"]
    assert tr.format_on_path(entries) == (
        "2 entr(y/ies): /opt/homebrew/bin/node /usr/local/bin/node "
    )


def test_format_on_path_none_when_empty():
    assert tr.format_on_path([]) == "0 entr(y/ies): (none)"
