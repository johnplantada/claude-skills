"""Tests for the runtime-versions `runtime_find` script — pure advisor logic."""

import runtime_find as rf

# --- owner_of ------------------------------------------------------------------

def test_owner_of_none_for_empty():
    assert rf.owner_of("") == "(none)"


def test_owner_of_mise_shim():
    assert rf.owner_of("/Users/x/.local/share/mise/shims/node") == "mise"


def test_owner_of_legacy_managers():
    assert rf.owner_of("/Users/x/.nvm/versions/node/v20/bin/node") == "legacy"
    assert rf.owner_of("/Users/x/.pyenv/versions/3.13/bin/python") == "legacy"
    assert rf.owner_of("/Users/x/Library/Caches/fnm_multishells/1/bin/node") == "legacy"


def test_owner_of_shims_dir_reads_as_mise():
    # runtime_find's owner_of matches `*/shims/*` before the legacy dirs (bash order),
    # so any shims path — even a legacy one — is attributed to mise here.
    assert rf.owner_of("/Users/x/.pyenv/shims/python") == "mise"


def test_owner_of_homebrew():
    assert rf.owner_of("/opt/homebrew/bin/node") == "homebrew"
    assert rf.owner_of("/usr/local/bin/python") == "homebrew"


def test_owner_of_system():
    assert rf.owner_of("/usr/bin/python3") == "system"


# --- recent_versions -----------------------------------------------------------

def test_recent_versions_keeps_last_five_semver_only():
    out = "18.0.0\n18.1.0\n19.0.0\n20.0.0\n20.1.0\n20.2.0\nlts/iron\n"
    # Only plain X.Y.Z lines; last 5 of the six semvers, trailing space kept.
    assert rf.recent_versions(out) == "18.1.0 19.0.0 20.0.0 20.1.0 20.2.0 "


def test_recent_versions_empty_when_no_semver():
    assert rf.recent_versions("system\nlts/iron\n") == ""


# --- is_lts_lang ---------------------------------------------------------------

def test_is_lts_lang_true_for_node():
    assert rf.is_lts_lang("node") is True


def test_is_lts_lang_false_for_others():
    assert rf.is_lts_lang("python") is False
    assert rf.is_lts_lang("go") is False
