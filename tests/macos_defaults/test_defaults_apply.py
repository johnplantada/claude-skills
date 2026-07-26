"""Tests for the macos-defaults `defaults_apply` script — the MUTATING helper.

The parsing is pure; the --yes gate (dry-run-by-default) is verified by injecting the
`_macos_common` CLI wrappers and asserting the script is only executed with --yes."""

import defaults_apply as ap


# --- find_sensitive_lines ------------------------------------------------------

def test_find_sensitive_lines_flags_sudo_and_security_terms():
    text = (
        "defaults write com.apple.dock autohide -bool true\n"
        "sudo defaults write /Library/Preferences/foo bar -bool true\n"
        "defaults write com.apple.security something -int 1\n"
        "spctl --master-disable\n"
    )
    got = ap.find_sensitive_lines(text)
    linenos = [n for n, _ in got]
    assert linenos == [2, 3, 4]  # 1-based, the harmless line 1 excluded


def test_find_sensitive_lines_none_when_clean():
    assert ap.find_sensitive_lines("defaults write com.apple.dock autohide -bool true\n") == []


# --- extract_write_domains -----------------------------------------------------

def test_extract_write_domains_unique_first_seen_order():
    text = (
        "defaults write com.apple.dock autohide -bool true\n"
        "defaults write com.apple.finder ShowPathbar -bool true\n"
        "defaults write com.apple.dock tilesize -int 48\n"      # dup domain, dropped
        "killall Dock\n"                                          # not a write
    )
    assert ap.extract_write_domains(text) == ["com.apple.dock", "com.apple.finder"]


# --- the --yes gate: dry run by default ----------------------------------------

class _Spy:
    def __init__(self):
        self.ran = []
        self.killed = []

    def run_bash(self, path):
        self.ran.append(path)
        return 0

    def killall(self, names):
        self.killed.append(names)


def _wire(monkeypatch, spy):
    # no `defaults write` lines -> extract_write_domains == [] -> no domain backups/IO
    monkeypatch.setattr(ap.mc, "run_bash", spy.run_bash)
    monkeypatch.setattr(ap.mc, "killall", spy.killall)


def test_dry_run_does_not_execute_the_script(monkeypatch, tmp_path, capsys):
    script = tmp_path / "macos.sh"
    script.write_text("echo hi\n")
    spy = _Spy()
    _wire(monkeypatch, spy)

    rc = ap.main([str(script)])           # no --yes

    assert rc == 0
    assert spy.ran == []                    # never applied
    assert spy.killed == []
    assert "dry run (no --yes)" in capsys.readouterr().out


def test_yes_applies_and_restarts(monkeypatch, tmp_path, capsys):
    script = tmp_path / "macos.sh"
    script.write_text("echo hi\n")
    spy = _Spy()
    _wire(monkeypatch, spy)

    rc = ap.main([str(script), "--yes"])

    assert rc == 0
    assert spy.ran == [script]              # applied exactly once
    assert spy.killed == [["Dock", "Finder", "SystemUIServer"]]
    out = capsys.readouterr().out
    assert "== applying: bash" in out
    assert "== restarting affected apps ==" in out


def test_missing_script_argument_exits_2(capsys):
    assert ap.main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_nonexistent_script_exits_2(tmp_path, capsys):
    assert ap.main([str(tmp_path / "nope.sh")]) == 2
    assert "not a file" in capsys.readouterr().err
