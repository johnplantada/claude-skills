"""Tests for the macos-defaults `defaults_read` script. Pure functions -> no mocking,
no `defaults` CLI needed."""

import defaults_read as dr


# --- parse_curated / select_targets --------------------------------------------

def test_parse_curated_yields_group_domain_key_triples():
    triples = dr.parse_curated()
    assert ("dock", "com.apple.dock", "autohide") in triples
    assert ("finder", "NSGlobalDomain", "AppleShowAllExtensions") in triples
    # every triple has exactly three fields, no blank lines leaked in
    assert all(len(t) == 3 and all(t) for t in triples)


def test_select_targets_no_groups_returns_everything():
    assert dr.select_targets([]) == dr.parse_curated()


def test_select_targets_filters_to_named_groups():
    got = dr.select_targets(["screenshots"])
    assert got and all(g == "screenshots" for g, _, _ in got)
    assert ("screenshots", "com.apple.screencapture", "type") in got


def test_select_targets_unknown_group_yields_nothing():
    assert dr.select_targets(["nope"]) == []


# --- looks_like_domain ---------------------------------------------------------

def test_looks_like_domain_dotted_and_nsglobaldomain():
    assert dr.looks_like_domain("com.apple.dock") is True
    assert dr.looks_like_domain("NSGlobalDomain") is True


def test_looks_like_domain_rejects_bare_group_name():
    assert dr.looks_like_domain("dock") is False
    assert dr.looks_like_domain("finder") is False


# --- collapse_value / format_reading -------------------------------------------

def test_collapse_value_flattens_multiline_and_squeezes_spaces():
    assert dr.collapse_value("(\n  a,\n  b\n)") == "( a, b )"


def test_format_reading_not_set_when_value_is_none():
    assert dr.format_reading("com.apple.dock", "autohide", None) == (
        "com.apple.dock autohide = (not set)"
    )


def test_format_reading_renders_value():
    assert dr.format_reading("com.apple.dock", "tilesize", "48") == (
        "com.apple.dock tilesize = 48"
    )


# --- parse_domains_output ------------------------------------------------------

def test_parse_domains_output_splits_sorts_and_trims():
    raw = "com.apple.finder, com.apple.dock, NSGlobalDomain\n"
    assert dr.parse_domains_output(raw) == [
        "NSGlobalDomain",
        "com.apple.dock",
        "com.apple.finder",
    ]
