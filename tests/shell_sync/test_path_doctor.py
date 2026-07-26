"""Tests for the shell-sync `path_doctor` script — pure PATH-audit logic."""

import _shell_common as sc
import path_doctor as pd


def test_entry_lines_numbers_in_order_and_skips_blanks():
    assert pd.entry_lines(["/a", "", "/b", "/a"]) == [
        "entry\t01\t/a",
        "entry\t02\t/b",
        "entry\t03\t/a",
    ]


def test_dup_lines_flags_only_repeats_keeping_first():
    assert pd.dup_lines(["/a", "/b", "/a", "/a"]) == ["dup\t/a", "dup\t/a"]


def test_dead_lines_uses_injected_predicate():
    assert pd.dead_lines(["/a", "/x"], is_dir=lambda d: d == "/a") == ["dead\t/x"]


def test_missing_tool_dir_lines_skips_dirs_already_on_path():
    lines = pd.missing_tool_dir_lines(
        ["/a"],
        suspects=["/opt/x", "/a"],
        is_dir=lambda d: True,
        exec_count=lambda d: 3,
    )
    assert lines == ["missing_tool_dir\t/opt/x\t3 execs"]


def test_missing_tool_dir_lines_skips_absent_dirs():
    lines = pd.missing_tool_dir_lines(
        [], suspects=["/opt/x"], is_dir=lambda d: False, exec_count=lambda d: 0
    )
    assert lines == []


def test_plan_lines_fish_quotes_each_entry():
    assert pd.plan_lines("fish", ["/a", "/b"]) == [
        "-- repair plan (review, then apply by hand) --",
        "set -gx PATH '/a' '/b'",
    ]


def test_plan_lines_fish_keeps_a_spaced_dir_as_one_entry():
    body = pd.plan_lines("fish", ["/Applications/VS Code.app/bin"])[1]
    assert body == "set -gx PATH '/Applications/VS Code.app/bin'"


def test_plan_lines_zsh_is_colon_joined_export():
    assert pd.plan_lines("zsh", ["/a", "/b"])[1] == 'export PATH="/a:/b"'


def test_dedupe_existing_drops_blanks_dupes_and_dead():
    entries = ["/a", "/a", "", "/b", "/dead"]
    assert sc.dedupe_existing(entries, is_dir=lambda d: d != "/dead") == ["/a", "/b"]


def test_suspect_dirs_expands_home():
    dirs = pd.suspect_dirs("/Users/me")
    assert "/opt/homebrew/bin" in dirs
    assert "/Users/me/.cargo/bin" in dirs
