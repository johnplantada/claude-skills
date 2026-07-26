"""Tests for the shell-sync `shell_diff` script — pure diff/classification logic."""

import shell_diff as sd


# --- only_in -------------------------------------------------------------------

def test_only_in_is_sorted_difference_without_blanks():
    assert sd.only_in({"/a", "/b", ""}, {"/b"}) == ["/a"]


# --- classify_zsh --------------------------------------------------------------

def test_classify_zsh_dead_dir_is_benign():
    assert sd.classify_zsh("/x", lambda d: False, set()) == "benign (dead/system path_helper)"


def test_classify_zsh_syspath_is_benign_path_helper():
    assert sd.classify_zsh("/etc/x", lambda d: True, {"/etc/x"}) == "benign (path_helper)"


def test_classify_zsh_live_non_syspath_is_review():
    assert sd.classify_zsh("/real", lambda d: True, set()) == "review"


# --- classify_fish -------------------------------------------------------------

def test_classify_fish_brew_keg_vendor_activation_is_benign():
    got = sd.classify_fish("/opt/homebrew/opt/mise/bin", lambda d: True, lambda keg: keg == "mise")
    assert got == "benign (brew vendor activation: mise)"


def test_classify_fish_live_non_vendor_is_review():
    assert sd.classify_fish("/some/dir", lambda d: True, lambda keg: False) == "review"


def test_classify_fish_dead_dir_is_benign():
    assert sd.classify_fish("/dead", lambda d: False, lambda keg: False) == "benign (dead)"


# --- startup_status ------------------------------------------------------------

def test_startup_status_zsh():
    assert sd.startup_status("zsh", "all good") == "clean"
    assert sd.startup_status("zsh", "zsh: parse error near }") == "issues"


def test_startup_status_fish():
    assert sd.startup_status("fish", "ok") == "clean"
    assert sd.startup_status("fish", "fish: Unknown command foo") == "issues"


# --- tool_line -----------------------------------------------------------------

def test_tool_line_format():
    assert sd.tool_line("node", "/p/node", "-") == "tool\tnode\tzsh=/p/node\tfish=-"
