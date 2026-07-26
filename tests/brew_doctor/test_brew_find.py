"""Tests for brew-doctor `brew_find` pure helpers. No mocking, no `brew` needed."""

import brew_find as bf

# --- set membership -----------------------------------------------------------

def test_in_set_is_exact_case_insensitive():
    assert bf.in_set(bf.RUNTIME_SET, "Node")
    assert bf.in_set(bf.RUNTIME_SET, "python")
    assert not bf.in_set(bf.RUNTIME_SET, "node-sass")  # exact only, not substring


def test_sub_set_is_substring_case_insensitive():
    fragile = bf.fragile_set("")
    assert bf.sub_set(fragile, "postgresql@16")  # contains 'postgresql'
    assert bf.sub_set(fragile, "NeoVim")
    assert not bf.sub_set(fragile, "ripgrep")


def test_fragile_set_includes_config_pinned():
    fragile = bf.fragile_set("mytool otherthing")
    assert "mytool" in fragile
    assert bf.sub_set(fragile, "mytool-cli")


# --- stem_of ------------------------------------------------------------------

def test_stem_strips_trailing_version():
    assert bf.stem_of("node@20") == "node"
    assert bf.stem_of("postgresql@16") == "postgresql"
    assert bf.stem_of("ripgrep") == "ripgrep"


# --- build_best_install: the judgment layer ----------------------------------

def test_runtime_is_steered_to_mise_not_brew():
    lines = bf.build_best_install(
        "node", "node", "formula", is_runtime=True, cask_auto_updates=False,
        arch="arm64", has_arm64_bottle=True, variants="", arg_is_fragile=True,
    )
    assert any("prefer mise, NOT brew" in ln for ln in lines)
    assert any("installing a runtime via brew is not recommended" in ln for ln in lines)
    assert not any(ln.startswith("install: brew install node") for ln in lines)


def test_fragile_formula_gets_pin_on_install():
    lines = bf.build_best_install(
        "neovim", "neovim", "formula", is_runtime=False, cask_auto_updates=False,
        arch="arm64", has_arm64_bottle=True, variants="", arg_is_fragile=True,
    )
    assert "  install: brew install neovim && brew pin neovim" in lines


def test_plain_formula_just_installs():
    lines = bf.build_best_install(
        "ripgrep", "ripgrep", "formula", is_runtime=False, cask_auto_updates=False,
        arch="arm64", has_arm64_bottle=True, variants="", arg_is_fragile=False,
    )
    assert "install: brew install ripgrep" in lines


def test_missing_arm64_bottle_is_noted_only_on_arm():
    on_arm = bf.build_best_install(
        "foo", "foo", "formula", is_runtime=False, cask_auto_updates=False,
        arch="arm64", has_arm64_bottle=False, variants="", arg_is_fragile=False,
    )
    on_intel = bf.build_best_install(
        "foo", "foo", "formula", is_runtime=False, cask_auto_updates=False,
        arch="x86_64", has_arm64_bottle=False, variants="", arg_is_fragile=False,
    )
    assert any("no native arm64 bottle" in ln for ln in on_arm)
    assert not any("no native arm64 bottle" in ln for ln in on_intel)


def test_self_updating_cask_note_and_headless_warning():
    lines = bf.build_best_install(
        "docker", "docker", "cask", is_runtime=False, cask_auto_updates=True,
        arch="arm64", has_arm64_bottle=True, variants="", arg_is_fragile=False,
    )
    assert any("cask self-updates (auto_updates)" in ln for ln in lines)
    assert "install: brew install --cask docker" in lines
    assert any("can't run headless" in ln for ln in lines)


def test_versioned_variants_listed_when_present():
    lines = bf.build_best_install(
        "python", "python", "formula", is_runtime=False, cask_auto_updates=False,
        arch="arm64", has_arm64_bottle=True, variants="python@3.11 python@3.12 ",
        arg_is_fragile=False,
    )
    assert any("versioned formulae: python@3.11 python@3.12" in ln for ln in lines)


# --- build_search -------------------------------------------------------------

def test_build_search_greppable_header_and_indented_desc():
    lines = bf.build_search("json", "jq\njo", "libjson: a json lib")
    assert lines[0] == "mode\tsearch\tterm=json"
    assert "jq" in lines
    assert "  libjson: a json lib" in lines
    assert lines[-1].startswith("next: brew_find.py <name>")


# --- build_dossier ------------------------------------------------------------

def test_dossier_header_and_installed_state():
    lines = bf.build_dossier(
        "neovim", "formula", "neovim: vim fork", "==> neovim: stable 0.11.0\ndeprecated",
        versions="neovim 0.11.0", also_cask=False, best_install=["== best install for your situation =="],
    )
    assert lines[0] == "mode\tdossier\tname=neovim\tkind=formula"
    assert "desc: neovim: vim fork" in lines
    assert "info: ==> neovim: stable 0.11.0" in lines
    assert "status: deprecated" in lines
    assert "installed: neovim 0.11.0" in lines


def test_dossier_reports_not_installed():
    lines = bf.build_dossier(
        "ripgrep", "formula", "", "ripgrep: search", versions=None, also_cask=False,
        best_install=[],
    )
    assert "installed: no" in lines
