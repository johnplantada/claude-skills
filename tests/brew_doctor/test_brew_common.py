"""Tests for the brew-doctor shared `_brew_common` config/plist parsers.

Pure functions -> no mocking, no `brew` needed. The config reader must match the old
section-aware awk one line-for-line.
"""

import _brew_common as bc

CONFIG = """\
# a comment
[shell-sync]
canonical = "zsh"

[brew-doctor]
pinned          = ["neovim", "postgresql"]   # fragile formulae
brewfile        = "~/Brewfile"
autoupdate_mode = "update-only"  # notify only

[dotfiles]
manager = "chezmoi"
"""


# --- parse_config_str: quote-stripped scalar ---------------------------------

def test_config_str_reads_the_right_section_key():
    assert bc.parse_config_str(CONFIG, "brew-doctor", "brewfile") == "~/Brewfile"


def test_config_str_strips_quotes_and_trailing_comment():
    # `["neovim", "postgresql"]   # fragile formulae` -> quotes gone, comment gone.
    assert bc.parse_config_str(CONFIG, "brew-doctor", "pinned") == "[neovim, postgresql]"
    assert bc.parse_config_str(CONFIG, "brew-doctor", "autoupdate_mode") == "update-only"


def test_config_str_scoped_to_its_section():
    # `manager` exists under [dotfiles], not [brew-doctor].
    assert bc.parse_config_str(CONFIG, "brew-doctor", "manager") == ""
    assert bc.parse_config_str(CONFIG, "dotfiles", "manager") == "chezmoi"


def test_config_str_absent_key_is_empty():
    assert bc.parse_config_str(CONFIG, "brew-doctor", "nope") == ""


# --- parse_config_array: tokens, brackets/quotes/commas dropped --------------

def test_config_array_yields_space_separated_tokens():
    assert bc.parse_config_array(CONFIG, "brew-doctor", "pinned") == "neovim postgresql"


def test_config_array_absent_is_empty():
    assert bc.parse_config_array(CONFIG, "brew-doctor", "nope") == ""


# --- parse_plist_program: the grep fallback ----------------------------------

def test_parse_plist_program_finds_program_string():
    plist = (
        "<dict>\n<key>Program</key>\n"
        "<string>/opt/homebrew/bin/brew-autoupdate</string>\n</dict>"
    )
    assert bc.parse_plist_program(plist) == "/opt/homebrew/bin/brew-autoupdate"


def test_parse_plist_program_finds_first_program_argument():
    plist = (
        "<key>ProgramArguments</key>\n<array>\n"
        "<string>/bin/sh</string>\n<string>-c</string>\n</array>"
    )
    assert bc.parse_plist_program(plist) == "/bin/sh"


def test_parse_plist_program_none_found():
    assert bc.parse_plist_program("<dict><key>Label</key><string>x</string></dict>") == ""
