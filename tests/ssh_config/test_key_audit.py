"""Tests for the ssh-config `key_audit` script. Pure functions -> no mocking, no
`ssh-keygen` needed. The secrets discipline (never reading private-key bytes) is
exercised via `is_private_key` header detection, not by feeding key material to output."""

import _ssh_common as sc
import key_audit as ka

# --- parse_keygen_line: the awk/sed field extraction ---------------------------

def test_parse_keygen_line_basic():
    bits, fp, ktype, comment = ka.parse_keygen_line(
        "256 SHA256:abc123 me@laptop (ED25519)"
    )
    assert bits == "256"
    assert fp == "SHA256:abc123"
    assert ktype == "ED25519"
    assert comment == "me@laptop"


def test_parse_keygen_line_multiword_comment():
    _, _, ktype, comment = ka.parse_keygen_line(
        "3072 SHA256:xyz work key 2026 (RSA)"
    )
    assert ktype == "RSA"
    assert comment == "work key 2026"


def test_parse_keygen_line_empty_comment():
    _bits, _fp, ktype, comment = ka.parse_keygen_line("256 SHA256:q  (ED25519)")
    assert comment == ""
    assert ktype == "ED25519"


# --- classify_strength: the weakness verdicts ----------------------------------

def test_strength_ed25519_preferred():
    assert ka.classify_strength("ED25519", "256") == "strength: ok (ed25519 — preferred)"


def test_strength_rsa_strong():
    assert ka.classify_strength("RSA", "4096") == (
        "strength: acceptable (rsa 4096 — consider ed25519)"
    )


def test_strength_rsa_weak_below_3072():
    assert ka.classify_strength("RSA", "2048") == (
        "strength: WEAK (rsa 2048 < 3072 — rotate; see keys.md)"
    )


def test_strength_rsa_non_numeric_bits_is_weak():
    # Mirrors bash `[ "$BITS" -ge 3072 ] 2>/dev/null` failing -> WEAK branch.
    assert ka.classify_strength("RSA", "??") == (
        "strength: WEAK (rsa ?? < 3072 — rotate; see keys.md)"
    )


def test_strength_dsa_and_ecdsa_and_unknown():
    assert ka.classify_strength("DSA", "1024") == "strength: WEAK (dsa — rotate; see keys.md)"
    assert ka.classify_strength("ECDSA", "256") == "strength: review (ecdsa — prefer ed25519)"
    assert ka.classify_strength("XMSS", "0") == "strength: unknown (XMSS)"


# --- dir_header ----------------------------------------------------------------

def test_dir_header_ok_perms():
    lines = ka.dir_header("/home/me/.ssh", "700")
    assert lines == ["== ssh dir ==", "path: /home/me/.ssh", "perms: 700 (ok)"]


def test_dir_header_bad_perms():
    lines = ka.dir_header("/home/me/.ssh", "755")
    assert lines[-1] == "perms: 755 (SHOULD be 700)"


# --- key_block: assembly with a public key present -----------------------------

def test_key_block_full_with_pub_loaded_and_protected():
    lines = ka.key_block(
        name="id_ed25519",
        path="/home/me/.ssh/id_ed25519",
        key_perms="600",
        pub_exists=True,
        pub_perms="644",
        keygen_line="256 SHA256:abc me@host (ED25519)",
        agent_fps=["SHA256:abc"],
        unprotected=False,
    )
    assert lines[0] == ""
    assert "== key: id_ed25519 ==" in lines
    assert "perms: 600 (ok)" in lines
    assert "pub_perms: 644 (ok)" in lines
    assert "type: ED25519" in lines
    assert "bits: 256" in lines
    assert "fingerprint: SHA256:abc" in lines
    assert "comment: me@host" in lines
    assert "strength: ok (ed25519 — preferred)" in lines
    assert "in_agent: yes" in lines
    assert "passphrase: protected" in lines


def test_key_block_loose_perms_and_unprotected():
    lines = ka.key_block(
        name="weak", path="/x/weak", key_perms="644", pub_exists=True,
        pub_perms="600", keygen_line="2048 SHA256:z c (RSA)",
        agent_fps=[], unprotected=True,
    )
    assert "perms: 644 (SHOULD be 600 — ssh ignores loose keys)" in lines
    assert "pub_perms: 600 (prefer 644)" in lines
    assert "in_agent: no" in lines
    assert "strength: WEAK (rsa 2048 < 3072 — rotate; see keys.md)" in lines
    assert "passphrase: NONE (unprotected — a stolen copy is instant compromise)" in lines


def test_key_block_missing_pub():
    lines = ka.key_block(
        name="nopub", path="/x/nopub", key_perms="600", pub_exists=False,
        pub_perms="", keygen_line="", agent_fps=[], unprotected=False,
    )
    assert any("pub: MISSING (/x/nopub.pub)" in l for l in lines)
    assert "passphrase: protected" in lines


def test_key_block_pub_present_but_unreadable():
    lines = ka.key_block(
        name="k", path="/x/k", key_perms="600", pub_exists=True,
        pub_perms="644", keygen_line="", agent_fps=[], unprotected=False,
    )
    assert "type: (could not read /x/k.pub)" in lines
    assert "comment: (none)" not in lines  # no metadata block emitted


def test_key_block_empty_comment_shows_none():
    lines = ka.key_block(
        name="k", path="/x/k", key_perms="600", pub_exists=True,
        pub_perms="644", keygen_line="256 SHA256:q  (ED25519)",
        agent_fps=[], unprotected=False,
    )
    assert "comment: (none)" in lines


# --- _is_candidate: the private-key discovery skip list ------------------------

def test_is_candidate_skips_non_keys():
    from pathlib import Path
    for skip in ("id_ed25519.pub", "known_hosts", "known_hosts.old", "config",
                 "config.bak", "id_rsa.bak", "authorized_keys"):
        assert ka._is_candidate(Path(f"/x/.ssh/{skip}")) is False
    for keep in ("id_ed25519", "id_rsa", "id_ed25519_server"):
        assert ka._is_candidate(Path(f"/x/.ssh/{keep}")) is True


# --- SECRETS: private-key bytes are detected, never surfaced -------------------

def test_is_private_key_detects_header_without_leaking(tmp_path):
    priv = tmp_path / "id_ed25519"
    priv.write_text("-----BEGIN OPENSSH " + "PRIVATE KEY-----\nSECRETBYTES\n"
                    + "-----END OPENSSH " + "PRIVATE KEY-----\n")
    pub = tmp_path / "id_ed25519.pub"
    pub.write_text("ssh-ed25519 AAAA me@host\n")
    assert sc.is_private_key(priv) is True
    assert sc.is_private_key(pub) is False
    # The report block for this key never contains the private bytes.
    lines = ka.key_block(
        name="id_ed25519", path=str(priv), key_perms="600", pub_exists=True,
        pub_perms="644", keygen_line="256 SHA256:x me@host (ED25519)",
        agent_fps=[], unprotected=False,
    )
    assert not any("SECRETBYTES" in l for l in lines)
