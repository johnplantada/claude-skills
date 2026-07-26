"""Tests for the ssh-config `ssh_config_audit` script. Pure functions -> no mocking,
no `ssh -G` needed."""

import ssh_config_audit as sca

# --- host_aliases: redacts values, reports aliases only ------------------------

def test_host_aliases_lists_aliases_with_trailing_space():
    text = "Host github.com\n  User git\nHost server *.internal\n"
    assert sca.host_aliases(text) == "github.com server *.internal "


def test_host_aliases_none():
    assert sca.host_aliases("  User git\n") == ""


def test_host_aliases_case_insensitive_match():
    # grep -i matches any case; sed only strips Host/host prefix.
    assert sca.host_aliases("host foo\n") == "foo "


# --- include_dirs --------------------------------------------------------------

def test_include_dirs():
    assert sca.include_dirs("Include config.d/*\n") == "config.d/* "


def test_include_dirs_none():
    assert sca.include_dirs("Host x\n") == ""


# --- option_count: hardening presence ------------------------------------------

def test_option_count_counts_matching_lines():
    text = "IdentityFile ~/.ssh/a\nHost b\nIdentityFile ~/.ssh/b\n"
    assert sca.option_count(text, "IdentityFile") == 2


def test_option_count_case_insensitive_and_word_boundary():
    # 'identitiesonly' must not be counted as 'IdentitiesOnly'? it IS the same key.
    assert sca.option_count("identitiesonly yes\n", "IdentitiesOnly") == 1
    # 'IdentityFile' should not match 'IdentityAgent'
    assert sca.option_count("IdentityAgent foo\n", "IdentityFile") == 0


def test_option_count_absent():
    assert sca.option_count("Host x\n", "UseKeychain") == 0


# --- weak_settings: dangerous config flagged -----------------------------------

def test_weak_settings_flags_stricthostkeychecking_no():
    text = "Host x\nStrictHostKeyChecking no\n"
    ws = sca.weak_settings(text)
    assert "StrictHostKeyChecking no" in ws
    assert ws.endswith(";")
    assert ws.startswith("2:")  # lineno prefix preserved


def test_weak_settings_multiple_joined_by_semicolon():
    text = "CheckHostIP no\nPasswordAuthentication yes\n"
    ws = sca.weak_settings(text)
    assert ws.count(";") == 2


def test_weak_settings_none():
    assert sca.weak_settings("Host x\nStrictHostKeyChecking yes\n") == ""


# --- filter_resolved: only the auth-deciding ssh -G keys ------------------------

def test_filter_resolved_keeps_auth_keys_only():
    out = (
        "hostname github.com\n"
        "user git\n"
        "port 22\n"
        "identityfile ~/.ssh/id_ed25519\n"
        "identitiesonly yes\n"
        "compression no\n"          # not an auth-deciding key -> dropped
        "loglevel INFO\n"
    )
    kept = sca.filter_resolved(out)
    assert kept == [
        "hostname github.com",
        "user git",
        "port 22",
        "identityfile ~/.ssh/id_ed25519",
        "identitiesonly yes",
    ]


def test_filter_resolved_does_not_confuse_similar_keys():
    # 'identityagent' must not be surfaced; 'user' is exact-token only.
    out = "identityagent none\nusekeychain yes\n"
    assert sca.filter_resolved(out) == ["usekeychain yes"]


# --- config_section: MISSING vs present ----------------------------------------

def test_config_section_missing(tmp_path):
    lines = sca.config_section(tmp_path / "config")
    assert lines[0] == ""
    assert lines[1] == "== config file =="
    assert "state: MISSING — no ~/.ssh/config yet (see setup.md)" in lines


def test_config_section_present_reports_opts(tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text(
        "Host github.com\n  IdentitiesOnly yes\n  IdentityFile ~/.ssh/id_ed25519\n"
    )
    lines = sca.config_section(cfg)
    assert "state: present" in lines
    assert "host_blocks: github.com " in lines
    assert "opt_IdentitiesOnly: set (1 block(s))" in lines
    assert "opt_UseKeychain: ABSENT" in lines
    assert "weak_settings: (none found)" in lines
    assert "include: (none — monolithic config)" in lines


# --- known_hosts_section -------------------------------------------------------

def test_known_hosts_present_counts_entries(tmp_path, monkeypatch):
    kh = tmp_path / "known_hosts"
    kh.write_text("github.com ssh-ed25519 AAAA\ngitlab.com ssh-rsa BBBB\n")
    monkeypatch.setattr(sca.sc, "SSH_DIR", tmp_path)
    lines = sca.known_hosts_section(tmp_path)
    assert "known_hosts: present (2 entries)" in lines


def test_known_hosts_absent(tmp_path):
    lines = sca.known_hosts_section(tmp_path)
    assert "known_hosts: ABSENT (every host will be TOFU-prompted)" in lines


# --- resolved_section: pipefail semantics --------------------------------------

def test_resolved_section_prints_matches():
    lines = sca.resolved_section("github.com", 0, "hostname github.com\nuser git\n")
    assert "resolved: hostname github.com" in lines
    assert "resolved: user git" in lines
    assert not any("failed" in l for l in lines)


def test_resolved_section_failure_when_rc_nonzero():
    lines = sca.resolved_section("nope", 255, "")
    assert "resolved: (ssh -G failed for nope)" in lines


def test_resolved_section_failure_when_no_matches():
    # ssh succeeded but nothing auth-deciding matched -> grep rc1 under pipefail.
    lines = sca.resolved_section("h", 0, "compression no\n")
    assert "resolved: (ssh -G failed for h)" in lines
