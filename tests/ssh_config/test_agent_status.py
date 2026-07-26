"""Tests for the ssh-config `agent_status` script. Pure functions -> no mocking, no
`ssh-add` / `ssh-keygen` needed."""

import agent_status as ag


# --- agent_fingerprints --------------------------------------------------------

def test_agent_fingerprints_takes_second_field_of_each_line():
    out = "256 SHA256:aaa foo@host (ED25519)\n256 SHA256:bbb bar (ED25519)"
    assert ag.agent_fingerprints(out) == ["SHA256:aaa", "SHA256:bbb"]


def test_agent_fingerprints_skips_blank_lines():
    assert ag.agent_fingerprints("\n\n256 SHA256:x c (ED25519)\n\n") == ["SHA256:x"]


def test_agent_fingerprints_empty_input():
    assert ag.agent_fingerprints("") == []


# --- pub_fingerprint -----------------------------------------------------------

def test_pub_fingerprint_second_field():
    assert ag.pub_fingerprint("256 SHA256:zzz me@host (ED25519)") == "SHA256:zzz"


def test_pub_fingerprint_unreadable_is_empty():
    assert ag.pub_fingerprint("") == ""


# --- agent_section: the three states -------------------------------------------

def test_agent_section_running_with_identities_lists_loaded():
    lines = ag.agent_section(True, 0, "256 SHA256:aaa foo (ED25519)")
    assert lines[0] == "== agent =="
    assert lines[1] == "state: running with identities"
    assert lines[2] == "loaded: 256 SHA256:aaa foo (ED25519)"


def test_agent_section_empty_agent():
    lines = ag.agent_section(False, 1, "")
    assert lines[1] == "state: running but EMPTY (no identities loaded)"


def test_agent_section_no_agent():
    lines = ag.agent_section(False, 2, "")
    assert lines[1] == "state: no agent reachable (SSH_AUTH_SOCK unset or agent down)"


# --- disk_section: LOADED vs not-loaded, and the no-pub case -------------------

def test_disk_section_marks_loaded_and_not_loaded():
    entries = [("id_ed25519.pub", "SHA256:aaa"), ("other.pub", "SHA256:ccc")]
    lines = ag.disk_section("/home/me/.ssh", entries, ["SHA256:aaa"])
    assert "id_ed25519.pub: LOADED  (SHA256:aaa)" in lines
    assert "other.pub: not-loaded  (SHA256:ccc)" in lines


def test_disk_section_unreadable_pub():
    lines = ag.disk_section("/home/me/.ssh", [("bad.pub", "")], [])
    assert "bad.pub: not-loaded  (unreadable)" in lines


def test_disk_section_no_pubs():
    lines = ag.disk_section("/home/me/.ssh", [], ["SHA256:aaa"])
    assert lines[-1] == "(no *.pub keys in /home/me/.ssh)"


# --- orphan_section: loaded identity with no matching *.pub --------------------

def test_orphan_section_flags_agent_only_fingerprint():
    disk_fps = ["SHA256:aaa"]
    agent_fps = ["SHA256:aaa", "SHA256:orphaned"]
    lines = ag.orphan_section(disk_fps, agent_fps)
    assert lines[0] == ""
    assert lines[1] == "== loaded identities with no *.pub on disk =="
    assert "orphan: SHA256:orphaned" in lines
    assert "orphan: SHA256:aaa" not in lines


def test_orphan_section_empty_agent_emits_nothing():
    assert ag.orphan_section(["SHA256:aaa"], []) == []


def test_orphan_section_all_accounted_for_prints_only_header():
    lines = ag.orphan_section(["SHA256:aaa"], ["SHA256:aaa"])
    assert lines == ["", "== loaded identities with no *.pub on disk =="]


# --- build_report: end-to-end wiring, no IO -----------------------------------

def test_build_report_full_wiring():
    entries = [("k.pub", "SHA256:aaa"), ("orphanless.pub", "SHA256:bbb")]
    lines = ag.build_report(True, 0, "256 SHA256:aaa c (ED25519)", "/x/.ssh", entries)
    assert lines[0] == "== agent =="
    assert "k.pub: LOADED  (SHA256:aaa)" in lines
    assert "orphanless.pub: not-loaded  (SHA256:bbb)" in lines
    # orphan section present because the agent holds an identity
    assert "== loaded identities with no *.pub on disk ==" in lines
