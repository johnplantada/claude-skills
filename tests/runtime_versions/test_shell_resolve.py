"""Tests for the runtime-versions `shell_resolve` script — pure arg parsing."""

import shell_resolve as sr


def test_parse_args_defaults_to_both_and_default_tools():
    assert sr.parse_args([]) == ("both", ["node", "python", "go"])


def test_parse_args_shell_selector_only():
    assert sr.parse_args(["zsh"]) == ("zsh", ["node", "python", "go"])


def test_parse_args_shell_and_tools():
    assert sr.parse_args(["fish", "ruby", "node"]) == ("fish", ["ruby", "node"])


def test_parse_args_tools_without_shell_keep_default_shell():
    # A leading non-shell token is a tool, not a shell selector.
    assert sr.parse_args(["ruby"]) == ("both", ["ruby"])


def test_parse_args_both_explicit():
    assert sr.parse_args(["both", "go"]) == ("both", ["go"])


def test_parse_args_rejects_a_tool_name_with_shell_metacharacters():
    # Tool names are interpolated into the login-shell scripts — a name carrying shell
    # syntax must be rejected up front, never quoted-and-hoped.
    import pytest

    with pytest.raises(ValueError, match="invalid tool name"):
        sr.parse_args(["zsh", "node; rm -rf /"])


def test_parse_args_accepts_versioned_and_dotted_tool_names():
    assert sr.parse_args(["python3.12", "node@22"]) == ("both", ["python3.12", "node@22"])
