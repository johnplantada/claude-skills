"""Tests for the shell-sync `mirror_drift` script — pure normalization + diffing."""

import mirror_drift as md


# --- norm_env ------------------------------------------------------------------

def test_norm_env_excludes_path_and_expands_home_sorted():
    text = "set -gx FOO 'bar'\nset -gx PATH /a /b\nset -gx BAZ '$HOME/x'"
    assert md.norm_env(text, home="/Users/me") == ["BAZ=/Users/me/x", "FOO=bar"]


def test_norm_env_ignores_non_set_lines():
    assert md.norm_env("# a comment\nalias gs 'git status'", home="/h") == []


# --- norm_path -----------------------------------------------------------------

def test_norm_path_single_line():
    assert md.norm_path("set -gx PATH /b /a /a", home="/h") == ["/a", "/b"]


def test_norm_path_continuation_lines():
    text = "set -gx PATH /a \\\n/b"
    assert md.norm_path(text, home="/h") == ["/a", "/b"]


def test_norm_path_expands_home():
    assert md.norm_path("set -gx PATH $HOME/bin", home="/Users/me") == ["/Users/me/bin"]


# --- drift_lines ---------------------------------------------------------------

def test_drift_lines_reports_stale_and_missing():
    lines, drift = md.drift_lines(
        i_env=["A=1", "B=2"], f_env=["A=1", "C=3"],
        i_path=["/a"], f_path=["/b"],
    )
    assert drift is True
    assert lines == [
        "drift_env_stale\tB=2",
        "drift_env_missing\tC=3",
        "drift_path_stale\t/a",
        "drift_path_missing\t/b",
    ]


def test_drift_lines_clean_when_identical():
    lines, drift = md.drift_lines(["A=1"], ["A=1"], ["/a"], ["/a"])
    assert (lines, drift) == ([], False)
