"""Tests for the ghostty-config `show_effective` script. Pure functions -> no `ghostty`."""

import show_effective as se


RAW = "font-family = Iosevka\nfont-size = 14\ntheme = Nord\ncursor-style = block\n"


# --- filter_lines --------------------------------------------------------------

def test_filter_lines_no_keys_returns_everything():
    assert se.filter_lines(RAW, []) == RAW.splitlines()


def test_filter_lines_or_matches_multiple_key_prefixes():
    assert se.filter_lines(RAW, ["font", "theme"]) == [
        "font-family = Iosevka",
        "font-size = 14",
        "theme = Nord",
    ]


def test_filter_lines_anchors_to_key_start():
    # `size` is inside `font-size` but not at the key start -> no match.
    assert se.filter_lines(RAW, ["size"]) == []


def test_filter_lines_tolerates_leading_whitespace():
    assert se.filter_lines("  theme = Nord\n", ["theme"]) == ["  theme = Nord"]


# --- main: the "don't abort on a non-zero +show-config" finding -----------------

def test_main_does_not_abort_when_show_config_failed(monkeypatch, capsys):
    # PINNED FINDING (b): a non-zero `ghostty +show-config` must NOT abort the script.
    # gc.show_config ignores the return code and returns whatever stdout it got (here
    # empty, as if the command failed); main must still exit 0.
    monkeypatch.setattr(se.gc, "ghostty_available", lambda: True)
    monkeypatch.setattr(se.gc, "show_config", lambda default=False: "")
    assert se.main(["font"]) == 0
    assert capsys.readouterr().out.strip() == "(no matching keys set)"


def test_main_prints_filtered_lines(monkeypatch, capsys):
    monkeypatch.setattr(se.gc, "ghostty_available", lambda: True)
    monkeypatch.setattr(se.gc, "show_config", lambda default=False: RAW)
    assert se.main(["theme"]) == 0
    assert capsys.readouterr().out.strip() == "theme = Nord"


def test_main_default_flag_passes_through(monkeypatch, capsys):
    seen = {}

    def fake_show(default=False):
        seen["default"] = default
        return RAW

    monkeypatch.setattr(se.gc, "ghostty_available", lambda: True)
    monkeypatch.setattr(se.gc, "show_config", fake_show)
    assert se.main(["--default", "cursor"]) == 0
    assert seen["default"] is True
    assert capsys.readouterr().out.strip() == "cursor-style = block"
