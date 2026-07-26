"""Tests for the shell-sync `dump_env` script — pure parsing/tagging, no shell needed."""

import dump_env as de


# --- section_command -----------------------------------------------------------

def test_section_command_path_differs_per_shell():
    assert de.section_command("zsh", "path") == 'printf "%s\\n" $path'
    assert de.section_command("fish", "path") == "for p in $PATH; echo $p; end"


def test_section_command_shared_and_functions():
    assert de.section_command("zsh", "exports") == "env"
    assert de.section_command("fish", "aliases") == "alias"
    assert de.section_command("zsh", "functions") == "print -l ${(k)functions}"
    assert de.section_command("fish", "functions") == "functions -n"


# --- parse_functions -----------------------------------------------------------

def test_parse_functions_fish_is_comma_separated_sorted_unique():
    assert de.parse_functions("fish", "foo, bar, baz, bar\n") == ["bar", "baz", "foo"]


def test_parse_functions_zsh_is_line_per_name_sorted_unique():
    assert de.parse_functions("zsh", "b\na\na\n") == ["a", "b"]


# --- tag_all -------------------------------------------------------------------

def test_tag_all_prefixes_each_section():
    out = de.tag_all(["/a"], ["FOO=1"], ["gs='git status'"], ["myfn"])
    assert out == [
        "path\t/a",
        "export\tFOO=1",
        "alias\tgs='git status'",
        "function\tmyfn",
    ]
