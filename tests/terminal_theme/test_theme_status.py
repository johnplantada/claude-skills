"""Tests for the terminal-theme `theme_status` script.

Pure functions -> no mocking, no fish/zsh/ghostty needed. Every pinned review finding
is anchored here so the bug can't come back:
  * fish hex detection must NOT false-alarm on fish's stock defaults,
  * fish must count hex by OCCURRENCE, consistently with the starship/zsh checks,
  * `fish_color_autosuggestion` (a fixed dim gray) is an intentional exemption,
  * zsh/fish colors must be resolved from a LIVE shell, not by reading files.
"""

import inspect

import _theme_common as tc
import theme_status as ts


# --- extract_ghostty_theme -----------------------------------------------------

def test_extract_ghostty_theme_reads_the_first_theme_line():
    out = "font-size = 13\ntheme = Doom Peacock\nbold-is-bright = true\n"
    assert ts.extract_ghostty_theme(out) == "Doom Peacock"


def test_extract_ghostty_theme_none_when_no_theme_set():
    assert ts.extract_ghostty_theme("font-size = 13\npalette = 0=#000000\n") is None


def test_extract_ghostty_theme_none_when_theme_value_is_empty():
    assert ts.extract_ghostty_theme("theme = \n") is None


# --- count_starship_hex / count_zsh_hex ----------------------------------------

def test_count_starship_hex_counts_each_occurrence():
    toml = "color_fg = '#d65d0e'\ncolor_bg = '#282828'\ncolor_ok = 'blue'\n"
    assert ts.count_starship_hex(toml) == 2


def test_count_starship_hex_zero_for_ansi_names_only():
    assert ts.count_starship_hex("color_fg = 'white'\ncolor_bg = 'bright-black'\n") == 0


def test_count_zsh_hex_counts_occurrences():
    styles = "ZSH_HIGHLIGHT_STYLES[command]='fg=#458588'\nZSH_HIGHLIGHT_STYLES[alias]='fg=#b8bb26'\n"
    assert ts.count_zsh_hex(styles) == 2


# --- count_fish_hex: the pinned findings ---------------------------------------

# A faithful snapshot of a stock fish color dump (fresh HOME, `fish -l -i -c …`).
# Everything is ANSI names + modifiers (`--background=`, `--theme=default`, `-r`, `--bold`).
FISH_STOCK_DUMP = (
    "fish_color_autosuggestion = brblack fish_color_autosuggestion = --theme=default\n"
    "fish_color_cancel = -r fish_color_cancel = --theme=default\n"
    "fish_color_command = --reset fish_color_command = --theme=default\n"
    "fish_color_comment = red fish_color_comment = --theme=default\n"
    "fish_color_cwd = green fish_color_cwd = --theme=default\n"
    "fish_color_end = green fish_color_end = --theme=default\n"
    "fish_color_error = brred fish_color_error = --theme=default\n"
    "fish_color_escape = brcyan fish_color_escape = --theme=default\n"
    "fish_color_host_remote = yellow fish_color_host_remote = --theme=default\n"
    "fish_color_operator = brcyan fish_color_operator = --theme=default\n"
    "fish_color_param = cyan fish_color_param = --theme=default\n"
    "fish_color_quote = yellow fish_color_quote = --theme=default\n"
    "fish_color_search_match = white fish_color_search_match = --background=brblack "
    "fish_color_search_match = --bold\n"
    "fish_color_selection = white fish_color_selection = --background=brblack\n"
    "fish_color_valid_path = --underline\n"
    "fish_pager_color_progress = brwhite fish_pager_color_progress = --background=cyan\n"
    "fish_pager_color_selected_background = -r\n"
)


def test_count_fish_hex_does_not_false_alarm_on_stock_defaults():
    # Pinned finding: fish's stock ANSI-name theme must read as fully inheriting.
    assert ts.count_fish_hex(FISH_STOCK_DUMP) == 0


def test_count_fish_hex_detects_real_bare_hex():
    # fish stores hex bare (no `#`); 6- and 3-digit forms both pin the color.
    dump = "fish_color_command = 005fd7\nfish_color_param = 00afff\nfish_color_x = f00\n"
    assert ts.count_fish_hex(dump) == 3


def test_count_fish_hex_exempts_autosuggestion_gray():
    # Pinned finding: a fixed dim gray for the ghost text is intentional, not drift.
    dump = "fish_color_autosuggestion = 8a8a8a\nfish_color_command = blue\n"
    assert ts.count_fish_hex(dump) == 0


def test_count_fish_hex_counts_by_occurrence_not_by_line():
    # Pinned finding: two hardcoded colors on one line must count as TWO, the same
    # occurrence-based accounting the starship/zsh checks use (old bash counted lines -> 1).
    one_line = "fish_color_foo = 005fd7 fish_color_foo = af00af\n"
    assert ts.count_fish_hex(one_line) == 2
    assert ts.count_starship_hex("#005fd7 #af00af") == ts.count_fish_hex(one_line)


def test_count_fish_hex_six_digit_counts_once_not_as_two_triples():
    assert ts.count_fish_hex("fish_color_command = 8a8a8a\n") == 1


# --- per-surface formatters ----------------------------------------------------

def test_format_ghostty_line_variants():
    assert ts.format_ghostty_line(False, "") == "ghostty\t(ghostty not installed)"
    assert ts.format_ghostty_line(True, "theme = Nord\n") == "ghostty\ttheme Nord"
    assert ts.format_ghostty_line(True, "font-size = 13\n") == "ghostty\tpalette-only (no theme= set)"


def test_format_starship_line_variants():
    assert ts.format_starship_line(False, "") == ("starship\t(no starship.toml)", False)
    assert ts.format_starship_line(True, "color = 'blue'\n") == ("starship\tinherits", False)
    assert ts.format_starship_line(True, "color = '#d65d0e'\n") == ("starship\thardcoded (1 hex)", True)


def test_format_fish_line_variants():
    assert ts.format_fish_line(False, False, "") == ("fish\t(fish not installed)", False)
    # A resolution failure must count as bad, never silently read as "inherits".
    assert ts.format_fish_line(True, False, "") == ("fish\t(could not resolve colors)", True)
    assert ts.format_fish_line(True, True, FISH_STOCK_DUMP) == ("fish\tinherits", False)
    assert ts.format_fish_line(True, True, "fish_color_command = 005fd7\n") == (
        "fish\thardcoded (1 hex)",
        True,
    )


def test_format_zsh_line_variants():
    assert ts.format_zsh_line(False, "") == ("zsh\tinherits (no highlighter)", False)
    assert ts.format_zsh_line(True, "") == ("zsh\tinherits (no highlighter)", False)
    assert ts.format_zsh_line(True, "ZSH_HIGHLIGHT_STYLES[command]='fg=blue'\n") == (
        "zsh\tinherits",
        False,
    )
    assert ts.format_zsh_line(True, "ZSH_HIGHLIGHT_STYLES[command]='fg=#458588'\n") == (
        "zsh\thardcoded (1 hex)",
        True,
    )


# --- build_report: end-to-end assembly + verdict -------------------------------

def test_build_report_all_inherit_is_coordinated():
    lines, coordinated = ts.build_report(
        ghostty_installed=True,
        ghostty_config="theme = Doom Peacock\n",
        starship_exists=True,
        starship_text="color = 'blue'\n",
        fish_installed=True,
        fish_ok=True,
        fish_dump=FISH_STOCK_DUMP,
        zsh_installed=True,
        zsh_styles="",
    )
    assert coordinated is True
    assert lines == [
        "ghostty\ttheme Doom Peacock",
        "starship\tinherits",
        "fish\tinherits",
        "zsh\tinherits (no highlighter)",
        "coordinated\tyes",
    ]


def test_build_report_any_hardcoded_surface_breaks_coordination():
    lines, coordinated = ts.build_report(
        ghostty_installed=True,
        ghostty_config="theme = Nord\n",
        starship_exists=True,
        starship_text="color = '#d65d0e'\n",
        fish_installed=True,
        fish_ok=True,
        fish_dump=FISH_STOCK_DUMP,
        zsh_installed=True,
        zsh_styles="",
    )
    assert coordinated is False
    assert "starship\thardcoded (1 hex)" in lines
    assert lines[-1] == "coordinated\tno"


# --- live-shell resolution is pinned in the helper -----------------------------

def test_fish_dump_is_resolved_in_a_live_login_interactive_shell():
    # Pinned finding: fish colors must be resolved by a real shell, not read from files.
    src = inspect.getsource(tc.fish_color_dump)
    assert '"fish"' in src and '"-l"' in src and '"-i"' in src


def test_zsh_styles_resolved_from_a_live_interactive_shell():
    # Pinned finding: ZSH_HIGHLIGHT_STYLES must come from a live shell (sourced fragments
    # count), not from parsing ~/.zshrc.
    src = inspect.getsource(tc.zsh_highlight_styles)
    assert '"zsh"' in src and '"-i"' in src and "ZSH_HIGHLIGHT_STYLES" in src
