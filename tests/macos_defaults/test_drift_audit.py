"""Tests for the macos-defaults `drift_audit` script. The parsing / normalization /
classification are pure; `audit()` takes an injected read_key so the whole flow is
testable without the `defaults` CLI."""

import drift_audit as da


# --- norm_bool -----------------------------------------------------------------

def test_norm_bool_maps_truthy_and_falsy_spellings():
    for t in ("true", "TRUE", "True", "yes", "YES", "Yes", "1"):
        assert da.norm_bool(t) == "1"
    for f in ("false", "FALSE", "False", "no", "NO", "No", "0"):
        assert da.norm_bool(f) == "0"


def test_norm_bool_passes_non_bool_through():
    assert da.norm_bool("Nlsv") == "Nlsv"


# --- expand_home ---------------------------------------------------------------

def test_expand_home_leading_tilde():
    assert da.expand_home("~/Desktop", "/Users/me") == "/Users/me/Desktop"
    assert da.expand_home("~", "/Users/me") == "/Users/me"


def test_expand_home_dollar_forms():
    assert da.expand_home("$HOME/Screens", "/Users/me") == "/Users/me/Screens"
    assert da.expand_home("${HOME}/Screens", "/Users/me") == "/Users/me/Screens"


def test_expand_home_leaves_bare_tilde_in_middle_alone():
    # only a leading ~ (or ~/...) is a home reference
    assert da.expand_home("a~b", "/Users/me") == "a~b"


# --- parse_write_line ----------------------------------------------------------

def test_parse_write_line_splits_type_and_value():
    assert da.parse_write_line(
        "defaults write com.apple.dock tilesize -int 48"
    ) == ("com.apple.dock", "tilesize", "-int", "48")


def test_parse_write_line_strips_trailing_comment():
    got = da.parse_write_line(
        "defaults write com.apple.dock autohide -bool true   # auto-hide the Dock"
    )
    assert got == ("com.apple.dock", "autohide", "-bool", "true")


def test_parse_write_line_strips_matching_quotes():
    assert da.parse_write_line(
        'defaults write com.apple.screencapture location -string "$HOME/Desktop"'
    ) == ("com.apple.screencapture", "location", "-string", "$HOME/Desktop")


def test_parse_write_line_handles_no_type_flag():
    assert da.parse_write_line(
        "defaults write com.apple.finder FXPreferredViewStyle Nlsv"
    ) == ("com.apple.finder", "FXPreferredViewStyle", "", "Nlsv")


def test_parse_write_line_ignores_comment_and_non_write_lines():
    assert da.parse_write_line("# defaults write com.apple.dock autohide -bool true") is None
    assert da.parse_write_line("set -euo pipefail") is None
    assert da.parse_write_line("killall Dock") is None


# --- collapse_live -------------------------------------------------------------

def test_collapse_live_flattens_and_strips_trailing():
    assert da.collapse_live("(\n  1,\n  2\n) ") == "( 1, 2 )"


# --- normalize_pair ------------------------------------------------------------

def test_normalize_pair_bool_declared_matches_live_one():
    # -bool true declared vs a live "1" both normalize to "1"
    assert da.normalize_pair("-bool", "true", "1", "/Users/me") == ("1", "1")


def test_normalize_pair_string_expands_home_on_declared_only():
    exp, cmp = da.normalize_pair("-string", "$HOME/Desktop", "/Users/me/Desktop", "/Users/me")
    assert exp == "/Users/me/Desktop" == cmp


# --- audit(): end-to-end with an injected read_key -----------------------------

def _reader(mapping):
    def read_key(domain, key):
        v = mapping.get((domain, key))
        return (v is not None, v or "")
    return read_key


def test_audit_classifies_match_drift_and_missing():
    script = (
        "#!/usr/bin/env bash\n"
        "defaults write com.apple.dock autohide -bool true\n"
        "defaults write com.apple.dock tilesize -int 48\n"
        "defaults write com.apple.finder ShowPathbar -bool true\n"
    )
    live = {
        ("com.apple.dock", "autohide"): "1",       # MATCH (bool true == 1)
        ("com.apple.dock", "tilesize"): "64",       # DRIFT (expected 48)
        # ShowPathbar absent -> MISSING
    }
    lines, n_match, n_drift, n_miss, n_decl = da.audit(
        script, _reader(live), home="/Users/me"
    )
    assert (n_match, n_drift, n_miss, n_decl) == (1, 1, 1, 3)
    assert "MATCH   com.apple.dock autohide = 1" in lines
    assert "DRIFT   com.apple.dock tilesize: live=64 expected=48" in lines
    assert "MISSING com.apple.finder ShowPathbar: not set, expected true" in lines
    assert lines[-1] == "summary: 1 match, 1 drift, 1 missing (3 declared)"


def test_audit_quiet_suppresses_match_lines_only():
    script = "defaults write com.apple.dock autohide -bool true\n"
    lines, *_ = da.audit(script, _reader({("com.apple.dock", "autohide"): "1"}),
                         home="/Users/me", quiet=True)
    assert not any(ln.startswith("MATCH") for ln in lines)
    assert lines[-1] == "summary: 1 match, 0 drift, 0 missing (1 declared)"


def test_audit_string_home_path_is_not_false_drift():
    script = 'defaults write com.apple.screencapture location -string "$HOME/Desktop"\n'
    live = {("com.apple.screencapture", "location"): "/Users/me/Desktop"}
    lines, n_match, n_drift, n_miss, _ = da.audit(script, _reader(live), home="/Users/me")
    assert (n_match, n_drift, n_miss) == (1, 0, 0)
