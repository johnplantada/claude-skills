"""Tests for the ghostty-config `config_audit` script.

Every review finding against the old bash version is pinned here as a test, so the
bug can't come back. Pure functions -> no mocking, no `ghostty` needed.
"""

import config_audit as ca

# --- parse_pairs ---------------------------------------------------------------

def test_parse_pairs_skips_comments_and_blanks():
    text = "# a comment\nfont-size = 14\n\n  theme = Gruvbox Dark \n"
    assert ca.parse_pairs(text) == [("font-size", "14"), ("theme", "Gruvbox Dark")]


def test_parse_pairs_ignores_lines_without_equals():
    assert ca.parse_pairs("just-a-word\nfont-size = 14\n") == [("font-size", "14")]


# --- find_dups: the false-duplicate finding ------------------------------------

def test_find_dups_flags_a_real_single_value_duplicate():
    pairs = [("font-size", "14"), ("font-size", "14")]
    assert ca.find_dups(pairs) == {"font-size": 2}


def test_find_dups_excludes_ghostty_repeatable_keys():
    # Review finding: keybind / palette / font-family fallbacks legitimately repeat;
    # flagging them told users to delete valid config.
    pairs = [
        ("keybind", "cmd+1=goto_tab:1"), ("keybind", "cmd+2=goto_tab:2"),
        ("palette", "0=#000000"), ("palette", "1=#ff0000"),
        ("font-family", "JetBrains Mono"), ("font-family-bold", "JetBrains Mono Bold"),
    ]
    assert ca.find_dups(pairs) == {}


# --- find_redundant: the "delete your theme override" finding -------------------

def test_find_redundant_flags_a_default_value():
    pairs = [("font-size", "13")]
    assert ca.find_redundant(pairs, {"font-size": "13"}, has_theme=False) == [("font-size", "13")]


def test_find_redundant_skips_theme_colors_when_a_theme_is_active():
    # Review finding: `background` may equal the *built-in* default yet be OVERRIDING
    # an active theme. Never recommend deleting it.
    pairs = [("theme", "dracula"), ("background", "#282c34")]
    assert ca.find_redundant(pairs, {"background": "#282c34"}, has_theme=True) == []


def test_find_redundant_flags_color_keys_when_no_theme():
    pairs = [("background", "#282c34")]
    assert ca.find_redundant(pairs, {"background": "#282c34"}, has_theme=False) == [
        ("background", "#282c34")
    ]


# --- resolve_config: the "audited the include stub / wrong file" findings -------

def _point(monkeypatch, lib, xdg):
    monkeypatch.setattr(ca.gc, "LIB", lib)
    monkeypatch.setattr(ca.gc, "XDG", xdg)


def test_resolve_follows_include_stub_to_the_real_xdg_config(tmp_path, monkeypatch):
    # Round-2 finding: no-arg audit hit the one-line Library include and reported clean.
    lib = tmp_path / "lib"
    xdg = tmp_path / "xdg"
    lib.write_text("config-file = ~/.config/ghostty/config\n")
    xdg.write_text("font-size = 14\n")
    _point(monkeypatch, lib, xdg)
    assert ca.resolve_config(None) == xdg


def test_resolve_prefers_library_when_it_holds_real_settings(tmp_path, monkeypatch):
    # Round-3 finding: an all-in-Library layout is authoritative even if XDG has leftovers.
    lib = tmp_path / "lib"
    xdg = tmp_path / "xdg"
    lib.write_text("font-size = 14\ntheme = Nord\n")
    xdg.write_text("theme = Gruvbox Dark\n")
    _point(monkeypatch, lib, xdg)
    assert ca.resolve_config(None) == lib


def test_resolve_honours_an_explicit_path(tmp_path, monkeypatch):
    _point(monkeypatch, tmp_path / "lib", tmp_path / "xdg")
    assert ca.resolve_config("/some/explicit/config") == ca.Path("/some/explicit/config")


# --- audit(): end-to-end wiring, with the two ghostty calls stubbed ------------

def test_audit_reports_clean_and_counts_keys(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("font-size = 20\ntheme = Nord\n")
    monkeypatch.setattr(ca.gc, "validate_config", lambda c=None: (True, ""))
    lines, clean = ca.audit(cfg, defaults={"font-size": "13"})
    assert clean is True
    assert "validate\tok" in lines
    assert "keys\t2" in lines
    assert lines[-1] == "clean"


def test_audit_surfaces_validation_errors(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text("totally-not-a-key = 1\n")
    monkeypatch.setattr(ca.gc, "validate_config", lambda c=None: (False, "totally-not-a-key: unknown field"))
    lines, clean = ca.audit(cfg, defaults={})
    assert clean is False
    assert "validate\tFAIL" in lines
    assert "error\ttotally-not-a-key: unknown field" in lines
    assert lines[-1] == "cruft"
