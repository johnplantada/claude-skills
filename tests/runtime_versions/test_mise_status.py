"""Tests for the runtime-versions `mise_status` script — pure `mise doctor` parsing."""

import mise_status as ms

# --- classify_activation: version-phrasing variants ----------------------------

def test_activation_yes_variants():
    assert ms.classify_activation("activated: yes") == "yes"
    assert ms.classify_activation("mise is active in this shell") == "yes"
    assert ms.classify_activation("shell is activated") == "yes"


def test_activation_no_variants():
    val = ms.classify_activation("activated: no")
    assert val.startswith("no (")
    assert ms.classify_activation("mise is not active").startswith("no (")


def test_activation_unknown_when_unclear():
    assert ms.classify_activation("some unrelated doctor output").startswith("unknown (")


# --- extract_shims_dir ---------------------------------------------------------

def test_extract_shims_dir_strips_leading_whitespace():
    doctor = "misc line\n    shims: /Users/x/.local/share/mise/shims\nmore\n"
    assert ms.extract_shims_dir(doctor, "/Users/x") == "shims: /Users/x/.local/share/mise/shims"


def test_extract_shims_dir_defaults_when_absent():
    assert ms.extract_shims_dir("no relevant line\n", "/Users/x") == (
        "/Users/x/.local/share/mise/shims (default)"
    )


def test_extract_shims_dir_takes_first_match():
    doctor = "shims first\nshims second\n"
    assert ms.extract_shims_dir(doctor, "/h") == "shims first"


# --- count_problems ------------------------------------------------------------

def test_count_problems_counts_matching_lines():
    doctor = "all good\n1 problem found\nWARNING: stale\nerror: bad\n"
    assert ms.count_problems(doctor) == 3


def test_count_problems_zero_when_clean():
    assert ms.count_problems("everything is fine\n") == 0


# --- prefixed ------------------------------------------------------------------

def test_prefixed_prepends_each_line():
    assert ms.prefixed("node 20\npython 3.13\n", "current: ") == [
        "current: node 20",
        "current: python 3.13",
    ]


def test_prefixed_empty_input_gives_no_lines():
    assert ms.prefixed("", "installed: ") == []


def test_login_doctor_reading_wins_over_the_in_process_one(monkeypatch, capsys):
    """The pinned finding, caught by a live audit: activation is set in an rc file, which
    this process never sources — so the in-process `mise doctor` says "not activated"
    even when the user's real shells are correctly activated. Reporting that sends them
    to fix a shell init that isn't broken. The login-shell reading must win."""
    monkeypatch.setattr(ms.rc, "have", lambda tool: True)
    monkeypatch.setattr(
        ms.rc, "run",
        lambda cmd: type("P", (), {"stdout": "activated: no\n", "stderr": "", "returncode": 1})(),
    )
    monkeypatch.setattr(ms, "login_doctor", lambda: "activated: yes\nshims: ~/.local/share/mise/shims\n")
    ms.main([])
    out = capsys.readouterr().out
    assert "mise_activated\tyes" in out
    assert "src=login-shell" in out  # provenance makes the wrong-environment class self-diagnosing


def test_falls_back_to_in_process_reading_when_no_login_shell(monkeypatch, capsys):
    monkeypatch.setattr(ms.rc, "have", lambda tool: True)
    monkeypatch.setattr(
        ms.rc, "run",
        lambda cmd: type("P", (), {"stdout": "activated: no\n", "stderr": "", "returncode": 1})(),
    )
    monkeypatch.setattr(ms, "login_doctor", lambda: "")
    ms.main([])
    out = capsys.readouterr().out
    # With no login shell to ask, the honest answer is "undetermined" — NOT "no", which
    # would read as a real finding and send the user to fix a working shell init.
    assert "mise_activated\tundetermined" in out
    assert "understate" in out
