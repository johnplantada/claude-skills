"""Tests for the terminal-theme `theme_list` script. Pure functions -> no ghostty needed."""

import theme_list as tl


CATALOG = (
    "Adventure Time (resources)\n"
    "Catppuccin Mocha (resources)\n"
    "Gruvbox Dark (resources)\n"
    "Gruvbox Light (resources)\n"
    "Nord (resources)\n"
    "Rose Pine (resources)\n"
    "Solarized Dark (resources)\n"
    "Tokyo Night (resources)\n"
)


# --- filter_themes -------------------------------------------------------------

def test_filter_themes_is_case_insensitive_substring():
    assert tl.filter_themes(CATALOG, "gruvbox") == [
        "Gruvbox Dark (resources)",
        "Gruvbox Light (resources)",
    ]


def test_filter_themes_no_match_returns_empty():
    assert tl.filter_themes(CATALOG, "zzznope") == []


# --- highlight_families --------------------------------------------------------

def test_highlight_families_picks_cross_tool_families_sorted_unique():
    fams = tl.highlight_families(CATALOG)
    assert fams == [
        "Catppuccin Mocha (resources)",
        "Gruvbox Dark (resources)",
        "Gruvbox Light (resources)",
        "Nord (resources)",
        "Rose Pine (resources)",
        "Tokyo Night (resources)",
    ]
    # Not a cross-tool family highlight — must be excluded.
    assert "Solarized Dark (resources)" not in fams
    assert "Adventure Time (resources)" not in fams


def test_highlight_families_matches_rose_pine_and_tokyonight_spelling_variants():
    catalog = "RosePine Moon (resources)\nTokyonight Storm (resources)\n"
    fams = tl.highlight_families(catalog)
    assert "RosePine Moon (resources)" in fams
    assert "Tokyonight Storm (resources)" in fams
