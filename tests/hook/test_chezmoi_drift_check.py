"""Tests for the devenv Stop-hook `chezmoi_drift_check` script.

Pure function -> no mocking, no `chezmoi` needed. The key behaviour pinned here
is that a chezmoi-managed path containing a SPACE survives into the reminder
intact (the reason the bash version sliced from column 4 rather than word-split).
"""

import chezmoi_drift_check as dc


# --- build_reminder: the in-sync case -----------------------------------------

def test_build_reminder_returns_none_when_in_sync():
    assert dc.build_reminder("") is None


def test_build_reminder_ignores_blank_lines():
    assert dc.build_reminder("\n   \n\n") is None


# --- build_reminder: drift ----------------------------------------------------

def test_build_reminder_reports_a_single_changed_file():
    msg = dc.build_reminder("MM .zshrc\n")
    assert msg is not None
    assert "1 chezmoi-managed file(s) changed (.zshrc)" in msg
    assert msg.startswith("⚠ dotfiles drift:")
    assert "Run /dotfiles or 'chezmoi re-add' + commit to sync." in msg


def test_build_reminder_counts_and_joins_multiple_files():
    msg = dc.build_reminder("MM .zshrc\n A .config/ghostty/config\n")
    assert msg is not None
    assert "2 chezmoi-managed file(s) changed (.zshrc, .config/ghostty/config)" in msg


def test_build_reminder_preserves_a_path_containing_a_space():
    # A managed path with a space must survive intact — the status format is
    # "XY <path>" so the path is everything from column 4 onward, not word 2.
    msg = dc.build_reminder("MM .config/My App/settings.json\n")
    assert msg is not None
    assert ".config/My App/settings.json" in msg
    assert "1 chezmoi-managed file(s) changed" in msg


def test_build_reminder_preserves_spaces_across_multiple_files():
    status = "MM .config/My App/settings.json\n A Library/Two Words/x.cfg\n"
    msg = dc.build_reminder(status)
    assert msg is not None
    assert "(.config/My App/settings.json, Library/Two Words/x.cfg)" in msg
