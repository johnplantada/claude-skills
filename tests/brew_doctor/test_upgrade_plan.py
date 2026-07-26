"""Tests for brew-doctor `upgrade_plan` pure helpers. No mocking, no `brew` needed."""

import upgrade_plan as up

# --- major / is_fragile -------------------------------------------------------

def test_major_strips_v_prefix_and_minor():
    assert up.major("0.11.0") == "0"
    assert up.major("v1.2.3") == "1"
    assert up.major("2023-01") == "2023"


def test_is_fragile_substring_case_insensitive():
    fragile = up.FRAGILE_BUILTIN
    assert up.is_fragile("NeoVim", fragile)
    assert up.is_fragile("postgresql@16", fragile)
    assert not up.is_fragile("ripgrep", fragile)


# --- parse_outdated_line ------------------------------------------------------

def test_parse_outdated_line_name_old_new():
    assert up.parse_outdated_line("neovim (0.11.0) < 0.12.0") == ("neovim", "0.11.0", "0.12.0")


def test_parse_outdated_line_takes_first_candidate_token():
    assert up.parse_outdated_line("foo (1.0) < 2.0 [pinned]") == ("foo", "1.0", "2.0")


# --- classify: the gating decision (the whole point) -------------------------

def test_pinned_formula_is_gated_and_auto_skipped():
    cat, line = up.classify("neovim", "0.11.0", "0.12.0", pinned=["neovim"], fragile=["neovim"])
    assert cat == "gated"
    assert "PINNED — auto-skipped by `brew upgrade` (gated ✅)" in line


def test_fragile_unpinned_must_pin_before_upgrade():
    cat, line = up.classify("neovim", "0.11.0", "0.12.0", pinned=[], fragile=["neovim"])
    assert cat == "to_pin"
    assert "fragile — UNPINNED: pin before upgrading" in line


def test_major_bump_flags_even_a_non_fragile_formula():
    cat, line = up.classify("somelib", "1.9.0", "2.0.0", pinned=[], fragile=[])
    assert cat == "to_pin"
    assert "major-bump — UNPINNED" in line


def test_major_bump_and_fragile_combine_flags():
    cat, line = up.classify("node", "18.0.0", "20.0.0", pinned=[], fragile=["node"])
    assert cat == "to_pin"
    assert "major-bump,fragile — UNPINNED" in line


def test_safe_formula_upgrades_directly():
    cat, line = up.classify("ripgrep", "14.0.0", "14.1.0", pinned=[], fragile=["neovim"])
    assert cat == "safe"
    assert line.endswith("safe to upgrade")


# --- build_commands: the printed (not executed) plan -------------------------

def test_build_commands_gates_pins_before_upgrades():
    lines = up.build_commands(
        to_pin=["neovim"], safe=["ripgrep"], has_out=True, has_cout=False, snap="/tmp/snap"
    )
    assert "brew pin neovim   # gate fragile/major bumps before upgrading" in lines
    assert "brew upgrade ripgrep   # upgrade the safe ones by name" in lines
    assert any("brew doctor && diff" in ln and "/tmp/snap" in ln for ln in lines)
    assert not any("--cask <cask>" in ln for ln in lines)


def test_build_commands_all_pinned_message():
    lines = up.build_commands(to_pin=[], safe=[], has_out=True, has_cout=True, snap="/tmp/s")
    assert "# all outdated formulae are already pinned — nothing to upgrade unattended" in lines
    assert any("--cask <cask>" in ln for ln in lines)


def test_build_commands_no_all_pinned_message_when_nothing_outdated():
    lines = up.build_commands(to_pin=[], safe=[], has_out=False, has_cout=False, snap="/tmp/s")
    assert not any("already pinned" in ln for ln in lines)


def test_parse_outdated_line_handles_the_cask_separator():
    """The pinned finding, caught by a live audit: casks print `!=` where formulae print
    `<`. Splitting on `< ` alone left `new` empty, and an empty new version compares
    unequal to any old major — manufacturing a phantom 'major-bump' that then advised
    `brew pin`, which does not work on casks."""
    line = "elgato-control-center (1.8.1,20582) != 1.9,20829"
    assert up.parse_outdated_line(line) == ("elgato-control-center", "1.8.1,20582", "1.9,20829")


def test_cask_style_bump_is_not_a_phantom_major_bump():
    name, old, new = up.parse_outdated_line("some-cask (1.8.1,20582) != 1.8.2,20829")
    category, _line = up.classify(name, old, new, pinned=[], fragile=[])
    assert category == "safe"
