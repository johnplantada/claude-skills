"""Tests for the terminal-theme `theme_swatch` script. Pure string builder -> no IO."""

import theme_swatch as sw


def test_render_swatch_has_header_and_legend():
    out = sw.render_swatch()
    assert "Terminal ANSI palette" in out
    assert "render in Ghostty" in out
    assert "0 black  1 red  2 green  3 yellow  4 blue  5 magenta  6 cyan  7 white" in out


def test_render_swatch_emits_all_sixteen_slots_and_resets():
    out = sw.render_swatch()
    # 8 normal-bg + 8 bright-bg + 8 normal-fg + 8 bright-fg = 32 SGR resets.
    assert out.count("\033[0m") == 32
    # bg slots 40-47 and 100-107, fg slots 30-37 and 90-97 all present.
    for i in range(8):
        assert f"\033[4{i}m" in out
        assert f"\033[10{i}m" in out
        assert f"\033[3{i}m" in out
        assert f"\033[9{i}m" in out


def test_render_swatch_is_deterministic():
    assert sw.render_swatch() == sw.render_swatch()
