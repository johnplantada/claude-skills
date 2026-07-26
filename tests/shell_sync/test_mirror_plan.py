"""Tests for the shell-sync `mirror_plan` script.

The PINNED finding: fish value emission must escape single quotes and backslashes so
a value like ``O'Brien`` or one with a literal backslash produces a VALID fish
``set -gx`` line — never a broken/half-quoted one. That bug can't come back.
"""

import mirror_plan as mp


# --- fish_quote: the pinned escaping finding -----------------------------------

def test_fish_quote_escapes_a_single_quote():
    # O'Brien -> 'O\'Brien'  (a valid fish single-quoted literal)
    assert mp.fish_quote("O'Brien") == "'O\\'Brien'"


def test_fish_quote_escapes_a_backslash():
    # a\b -> 'a\\b'  (backslash doubled first, so the quote-escape can't be broken)
    assert mp.fish_quote("a\\b") == "'a\\\\b'"


def test_fish_quote_leaves_a_plain_value_untouched():
    assert mp.fish_quote("git status") == "'git status'"


def test_env_line_for_a_quote_value_is_a_valid_fish_set():
    assert mp.env_lines(["NAME=O'Brien"]) == ["set -gx NAME 'O\\'Brien'"]


def test_alias_line_for_a_quote_value_is_escaped_too():
    assert mp.alias_lines(["x=don't"]) == ["alias x 'don\\'t'"]


# --- env_lines: the denylist ---------------------------------------------------

def test_env_lines_drops_shell_managed_vars_keeps_user_vars():
    lines = mp.env_lines(["PWD=/x", "HOMEBREW_PREFIX=/opt", "FOO=bar"])
    assert lines == ["set -gx FOO 'bar'"]


def test_env_lines_skips_blank_lines():
    assert mp.env_lines(["", "FOO=bar"]) == ["set -gx FOO 'bar'"]


# --- alias_lines ---------------------------------------------------------------

def test_alias_lines_translates_a_simple_alias():
    assert mp.alias_lines(["gs='git status'"]) == ["alias gs 'git status'"]


def test_alias_lines_flags_expansion_as_todo():
    assert mp.alias_lines(["ll='ls $HOME'"]) == [
        "# TODO port alias (uses shell expansion): ll=ls $HOME"
    ]


def test_alias_lines_drops_zsh_default_aliases():
    assert mp.alias_lines(["run-help='man'", "which-command='whence'"]) == []


# --- starship_block ------------------------------------------------------------

def test_starship_block_emits_init_when_present_and_not_in_config():
    assert mp.starship_block(True, False)[-1] == "starship init fish | source"


def test_starship_block_does_not_duplicate_an_existing_init():
    assert mp.starship_block(True, True) == [
        "# starship already initialized in config.fish — not duplicated here."
    ]


def test_starship_block_notes_when_starship_absent():
    block = mp.starship_block(False, False)
    assert block[0].startswith("# no starship on PATH")


def test_config_has_starship_init_ignores_commented_lines():
    assert mp.config_has_starship_init("starship init fish | source") is True
    assert mp.config_has_starship_init("# starship init fish | source") is False


# --- build_plan: end-to-end shape ----------------------------------------------

def test_build_plan_has_markers_path_and_footer():
    lines = mp.build_plan(
        "2026-07-26", ["/a", "/b"], ["FOO=bar"], ["gs='git status'"], True, False
    )
    assert lines[0] == "# >>> shell-sync (AUTO-GENERATED) >>>"
    assert "set -gx PATH /a /b" in lines
    assert "set -gx FOO 'bar'" in lines
    assert "alias gs 'git status'" in lines
    assert "# --- functions ---" in lines
    assert lines[-1] == "# <<< shell-sync (AUTO-GENERATED) <<<"
    assert any("2026-07-26" in l for l in lines)
