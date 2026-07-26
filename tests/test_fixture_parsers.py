"""Run the parsers against REAL tool output — the fix for imagined test data.

Every parser bug this repo shipped had green unit tests, because those tests fed the
parser strings a human invented and the code made the same wrong assumption. These tests
read `tests/fixtures/` — output captured verbatim from real tools (see
`scripts/capture_fixtures.py`) — so a passing test means "handles what brew/mise/lazy
actually printed", not "handles what I imagined".

Two properties are asserted throughout:

  1. **No silent garbage.** A parser handed a real line must not return an empty/blank
     field that then flows into a comparison. That is exactly how the cask `!=` bug
     produced a confident, wrong "major-bump" verdict.
  2. **No crash on real input.** Fixtures include headers, ANSI codes, blank lines, and
     multi-line values; parsers must tolerate all of it.

Fixtures are optional by design: a machine without ghostty produces no ghostty fixture,
and those tests skip rather than fail. Absent ground truth is honest; fabricated ground
truth is the bug being fixed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(relative: str) -> str:
    """Fixture body with the `#` provenance header stripped, or skip if absent."""
    path = FIXTURES / relative
    if not path.is_file():
        pytest.skip(f"no fixture {relative} (tool absent or state unreproducible here)")
    lines = path.read_text().splitlines()
    return "\n".join(ln for ln in lines if not ln.startswith("#"))


# --- brew: the cask-separator bug, against the recorded real output -----------------

def test_outdated_parses_every_real_line_without_blank_fields():
    import upgrade_plan as up

    text = load("recorded/brew_outdated_verbose_with_cask.txt")
    rows = [up.parse_outdated_line(ln) for ln in text.splitlines() if ln.strip()]
    assert rows, "fixture had no parsable rows"
    for name, old, new in rows:
        assert name, "parser lost the package name"
        assert old, f"{name}: parser lost the OLD version"
        assert new, f"{name}: parser lost the NEW version — the blank that faked a major-bump"


def test_the_real_cask_line_is_not_classified_as_a_major_bump():
    import upgrade_plan as up

    text = load("recorded/brew_outdated_verbose_with_cask.txt")
    cask = next(ln for ln in text.splitlines() if ln.startswith("elgato-control-center"))
    name, old, new = up.parse_outdated_line(cask)
    category, line = up.classify(name, old, new, pinned=[], fragile=[])
    assert category == "safe", f"real cask line still misclassified: {line}"
    assert "pin" not in line, "advised `brew pin` on a cask, which does not work"


def test_pinned_list_parses():
    import upgrade_plan as up

    names = load("brew/list_pinned.txt").split()
    assert up.join_trailing(names, "(none)")


# --- nvim: the plugin-commit-subject false positive ---------------------------------

def test_real_lazy_sync_rows_are_not_reported_as_findings():
    import nvim_check as nc

    text = load("recorded/lazy_sync_plugin_updates.txt")
    assert nc.filter_startup(text) == [], (
        "plugin commit subjects reported as findings about the user's config"
    )


# --- mise: activation + shims, against real doctor output ---------------------------

def test_mise_doctor_activation_is_classified_not_unknown():
    import mise_status as ms

    doctor = load("mise/doctor.txt")
    verdict = ms.classify_activation(doctor)
    assert verdict.startswith(("yes", "no")), (
        f"real `mise doctor` output classified as {verdict!r} — the phrasing match is stale"
    )


def test_mise_shims_dir_extracted_from_real_output():
    import mise_status as ms

    assert ms.extract_shims_dir(load("mise/doctor.txt"), "/Users/USER")


# --- chezmoi: doctor row tallying ----------------------------------------------------

def test_chezmoi_doctor_rows_tally_from_real_output():
    import chezmoi_status as cs

    counts, _issues = cs.parse_doctor(load("chezmoi/doctor.txt"))
    assert sum(counts.values()) > 0, "no doctor rows recognized in real output"


def test_chezmoi_managed_lines_count():
    import chezmoi_status as cs

    assert cs.count_nonblank_lines(load("chezmoi/managed_files.txt")) > 0


# --- git: config --list parsing ------------------------------------------------------

def test_git_config_origin_scan_tolerates_real_list_output():
    import git_audit as ga

    # first_email_origin expects --show-origin lines; --list has no origin column, and it
    # must degrade to '' rather than raise on the real shape.
    assert ga.first_email_origin(load("git/config_global_list.txt")) == ""


# --- ghostty: config pairs + fonts ---------------------------------------------------

def test_ghostty_show_config_pairs_parse():
    import config_audit as ca

    pairs = ca.parse_pairs(load("ghostty/show_config.txt"))
    assert pairs, "no key=value pairs found in real +show-config output"
    assert all(k for k, _ in pairs), "a pair parsed with an empty key"


def test_ghostty_font_families_extracted_from_real_config():
    import font_check as fc

    text = load("ghostty/show_config.txt")
    # The fixture is a real config; if it declares fonts they must parse non-empty.
    for name in fc.parse_font_families(text):
        assert name.strip(), "font-family parsed to an empty value"


def test_ghostty_installed_font_families_parse():
    import font_check as fc

    assert fc.parse_installed_fonts(load("ghostty/list_fonts_head.txt"))


# --- macOS: defaults read, multi-line values -----------------------------------------

def test_defaults_read_collapses_multiline_values():
    import drift_audit as da

    collapsed = da.collapse_live(load("macos/defaults_read_dock.txt"))
    assert "\n" not in collapsed, "multi-line defaults value not collapsed to one line"
