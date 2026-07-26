"""Tests for the ssh-config `key_new` script. MUTATING at runtime (generates keys), so
only its pure pieces and its gating are exercised — never the key-generation IO."""

import key_new as kn


# --- public_key_report: the register hint, references the .py entrypoints -------

def test_public_key_report_shows_pub_and_register_hint():
    lines = kn.public_key_report(
        "/home/me/.ssh/id_ed25519", "id_ed25519", "ssh-ed25519 AAAA me@host\n"
    )
    assert "== public key (safe to register) ==" in lines
    assert "ssh-ed25519 AAAA me@host" in lines
    assert 'register it, e.g.:  gh ssh-key add /home/me/.ssh/id_ed25519.pub --title "id_ed25519"' in lines
    # invocation examples point at the .py entrypoint, not the old .sh
    assert any("ssh-config-audit.py <host>" in l for l in lines)
    assert not any(".sh" in l for l in lines)


# --- gating: missing args and overwrite refusal -------------------------------

def test_main_requires_two_args(capsys):
    assert kn.main([]) == 1
    assert kn.main(["only-one"]) == 1
    err = capsys.readouterr().err
    assert "usage:" in err


def test_main_refuses_to_overwrite_existing_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kn.sc, "SSH_DIR", tmp_path)
    existing = tmp_path / "id_ed25519"
    existing.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n")
    rc = kn.main(["id_ed25519", "me@host"])
    assert rc == 1
    assert "refusing to overwrite existing key" in capsys.readouterr().err


# --- SECRETS: an existing private key is never read into output ---------------

def test_overwrite_refusal_does_not_read_key_body(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kn.sc, "SSH_DIR", tmp_path)
    (tmp_path / "id_ed25519").write_text(
        "-----BEGIN OPENSSH PRIVATE KEY-----\nSECRETBYTES\n"
    )
    kn.main(["id_ed25519", "me@host"])
    captured = capsys.readouterr()
    assert "SECRETBYTES" not in captured.out
    assert "SECRETBYTES" not in captured.err
