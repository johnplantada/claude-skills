"""Tests for the ghostty-config `ghostty_doctor` script.

Pure functions -> no `ghostty` needed. The known review findings are pinned as tests.
"""

import ghostty_doctor as doctor
from pathlib import Path


# --- find_include_lines --------------------------------------------------------

def test_find_include_lines_picks_config_file_only():
    text = "config-file = ~/.config/ghostty/config\nfont-size = 14\n  config-file = /x\n"
    assert doctor.find_include_lines(text) == [
        "config-file = ~/.config/ghostty/config",
        "  config-file = /x",
    ]


def test_find_include_lines_ignores_lookalike_keys():
    # `config-file-foo` is not `config-file`.
    assert doctor.find_include_lines("config-file-foo = bar\n") == []


# --- includes_xdg: the FIXED-STRING (not regex) finding ------------------------

def test_includes_xdg_matches_fixed_string_not_regex():
    # PINNED FINDING (a): the include check must be a FIXED-STRING match. As a regex,
    # the `.` in `.config` would match any char and spuriously hit `…/xconfig/…`,
    # wrongly reporting the XDG file as included and hiding a real split-brain.
    xdg = "/home/user/.config/ghostty/config"
    lib_text = "config-file = /home/user/xconfig/ghostty/config\n"
    assert doctor.includes_xdg(lib_text, xdg) is False


def test_includes_xdg_true_on_exact_path():
    xdg = "/home/user/.config/ghostty/config"
    assert doctor.includes_xdg(f"config-file = {xdg}\n", xdg) is True


def test_includes_xdg_true_on_tilde_literal():
    assert doctor.includes_xdg(
        "config-file = ~/.config/ghostty/config\n", "/some/other/path"
    ) is True


# --- build_report --------------------------------------------------------------

def test_report_include_layout_is_in_sync():
    lib_text = "config-file = ~/.config/ghostty/config\n"
    lines, in_sync = doctor.build_report(
        validate_ok=True, validate_output="", lib_text=lib_text,
        lib_has_content=True, xdg_has_content=True,
        lib_path=Path("/lib"), xdg_path=Path("/xdg"), xdg_home_set=False,
    )
    assert in_sync is True
    assert "validate\tok" in lines
    assert "loads\t/lib" in lines
    assert "include\t/xdg" in lines
    assert lines[-1] == "in_sync\tyes"


def test_report_split_brain_when_xdg_not_included():
    lines, in_sync = doctor.build_report(
        validate_ok=True, validate_output="", lib_text="font-size = 14\n",
        lib_has_content=True, xdg_has_content=True,
        lib_path=Path("/lib"), xdg_path=Path("/xdg"), xdg_home_set=False,
    )
    assert in_sync is False
    assert "split_brain\t/xdg" in lines
    assert lines[-1] == "in_sync\tno"


def test_report_validation_failure_emits_errors_and_not_in_sync():
    lines, in_sync = doctor.build_report(
        validate_ok=False, validate_output="bad-key: unknown field\n", lib_text="",
        lib_has_content=False, xdg_has_content=False,
        lib_path=Path("/lib"), xdg_path=Path("/xdg"), xdg_home_set=True,
    )
    assert in_sync is False
    assert "validate\tFAIL" in lines
    assert "error\tbad-key: unknown field" in lines


def test_report_xdg_only_needs_xdg_config_home():
    # No Library file, XDG present but XDG_CONFIG_HOME unset -> ignored -> split-brain.
    lines, in_sync = doctor.build_report(
        validate_ok=True, validate_output="", lib_text="",
        lib_has_content=False, xdg_has_content=True,
        lib_path=Path("/lib"), xdg_path=Path("/xdg"), xdg_home_set=False,
    )
    assert in_sync is False
    assert "loads\t/xdg" in lines
    assert "split_brain\t/xdg" in lines


def test_report_xdg_only_in_sync_when_config_home_set():
    lines, in_sync = doctor.build_report(
        validate_ok=True, validate_output="", lib_text="",
        lib_has_content=False, xdg_has_content=True,
        lib_path=Path("/lib"), xdg_path=Path("/xdg"), xdg_home_set=True,
    )
    assert in_sync is True
    assert "loads\t/xdg" in lines
    assert lines[-1] == "in_sync\tyes"
