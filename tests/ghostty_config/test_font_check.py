"""Tests for the ghostty-config `font_check` script. Pure functions -> no `ghostty`."""

import font_check as fc


# --- parse_font_families -------------------------------------------------------

def test_parse_font_families_all_variants_and_quotes():
    text = (
        'font-family = "JetBrains Mono"\n'
        "font-family-bold = JetBrains Mono Bold\n"
        "  font-family-italic = Iosevka\n"
        "# font-family = Commented Out\n"
        "font-size = 14\n"
    )
    assert fc.parse_font_families(text) == [
        "JetBrains Mono",
        "JetBrains Mono Bold",
        "Iosevka",
    ]


def test_parse_font_families_skips_empty_values():
    assert fc.parse_font_families("font-family =\n") == []


# --- parse_installed_fonts -----------------------------------------------------

def test_parse_installed_fonts_keeps_only_family_headers():
    text = "JetBrains Mono\n    Regular\n    Bold\nIosevka Nerd Font\n\n"
    assert fc.parse_installed_fonts(text) == ["JetBrains Mono", "Iosevka Nerd Font"]


# --- check_fonts ---------------------------------------------------------------

def test_check_fonts_resolved_and_nerd_font():
    lines, miss = fc.check_fonts(["Iosevka Nerd Font"], ["Iosevka Nerd Font"])
    assert miss == 0
    assert lines == [
        "font-family\tIosevka Nerd Font\tresolved",
        "glyphs\tIosevka Nerd Font\tnerd-font",
    ]


def test_check_fonts_resolved_but_maybe_tofu():
    lines, miss = fc.check_fonts(["JetBrains Mono"], ["JetBrains Mono"])
    assert miss == 0
    assert "glyphs\tJetBrains Mono\tmaybe-tofu" in lines


def test_check_fonts_missing_counts_and_flags():
    lines, miss = fc.check_fonts(["No Such Font"], ["JetBrains Mono"])
    assert miss == 1
    assert lines == ["font-family\tNo Such Font\tMISSING"]


def test_check_fonts_requires_exact_match():
    # A substring is not a resolve — "Mono" must not match "JetBrains Mono".
    lines, miss = fc.check_fonts(["Mono"], ["JetBrains Mono"])
    assert miss == 1
    assert "font-family\tMono\tMISSING" in lines
