"""Tests for brew-doctor `brew_audit` pure helpers. No mocking, no `brew` needed."""

import brew_audit as ba

# --- count_nonempty / join_trailing ------------------------------------------

def test_count_nonempty_counts_only_non_blank_lines():
    assert ba.count_nonempty("a\n\nb\n") == 2
    assert ba.count_nonempty("") == 0


def test_join_trailing_matches_tr_newline_space():
    assert ba.join_trailing(["a", "b"], "(none)") == "a b "
    assert ba.join_trailing([], "(none)") == "(none)"


# --- agent_matches: the launchd filename glob --------------------------------

def test_agent_matches_brew_autoupdate_homebrew():
    assert ba.agent_matches("com.user.brew-upgrade.plist")
    assert ba.agent_matches("io.autoupdate.plist")
    assert ba.agent_matches("Homebrew.agent.plist")
    assert not ba.agent_matches("com.apple.something.plist")


# --- mode_of_script: the core hazard classification --------------------------

def test_mode_flags_a_real_brew_upgrade_as_the_hazard():
    # Review-pinned: an agent that runs `brew upgrade` is the hazard, not `brew update`.
    script = "#!/bin/sh\nbrew update && brew upgrade\n"
    assert ba.mode_of_script(script, True, "/x") == "UPGRADE (bumps packages unattended — the hazard)"


def test_mode_update_only_is_safe():
    script = "#!/bin/sh\nbrew update\nterminal-notifier -message done\n"
    assert ba.mode_of_script(script, True, "/x") == "update-only (metadata + notify — safe)"


def test_mode_upgrade_wins_even_when_update_also_present():
    script = "brew update\nbrew upgrade\n"
    assert ba.mode_of_script(script, True, "/x").startswith("UPGRADE")


def test_mode_not_an_auto_updater():
    script = "#!/bin/sh\n/opt/homebrew/bin/some-daemon --serve\n"
    assert ba.mode_of_script(script, True, "/x").startswith("not an auto-updater")


def test_mode_unreadable_target():
    assert ba.mode_of_script("", False, "/opt/x") == "unknown (target unreadable: /opt/x)"


# --- orphan filtering ---------------------------------------------------------

def test_orphan_kept_lines_drops_headers():
    text = "==> Autoremoving 2 unneeded formulae:\nfoo bar\nWould remove: baz\n"
    kept = ba.orphan_kept_lines(text)
    assert kept == ["foo bar"]


def test_orphan_tokens_splits_on_whitespace():
    assert ba.orphan_tokens(["foo bar", "baz"]) == ["foo", "bar", "baz"]
    assert ba.orphan_tokens([]) == []
