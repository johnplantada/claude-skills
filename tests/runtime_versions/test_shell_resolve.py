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
