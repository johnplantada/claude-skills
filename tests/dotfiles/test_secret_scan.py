"""Tests for the dotfiles `secret_scan` script.

The pinned safety invariant is here: detection emits pattern NAMES, PATHS, and
match-LOCATIONS only — a matched secret value must NEVER appear in the output. Pure
functions -> no chezmoi, no subprocess.
"""

import secret_scan as ss

# --- scan_text_for_names: content detection ------------------------------------

def test_detects_private_key_block():
    text = "-----BEGIN OPENSSH PRIVATE KEY-----\n"
    assert ss.scan_text_for_names(text) == ["private-key-block"]


def test_detects_aws_access_key_id():
    assert ss.scan_text_for_names("id = AKIAIOSFODNN7EXAMPLE") == ["aws-access-key-id"]


def test_detects_github_token():
    assert ss.scan_text_for_names("ghp_0123456789abcdefABCD") == ["github-token"]


def test_detects_slack_token():
    assert ss.scan_text_for_names("xoxb-1234567890-abcdef") == ["slack-token"]


def test_detects_generic_assignment():
    assert ss.scan_text_for_names('api_key = "hunter2"') == ["generic-assignment"]
    assert ss.scan_text_for_names("password: swordfish") == ["generic-assignment"]


def test_clean_text_yields_no_names():
    # No credential keyword before the `=`, so the generic-assignment rule stays quiet.
    assert ss.scan_text_for_names("editor = nvim\n") == []
    assert ss.scan_text_for_names("plain prose with no markers") == []


# --- THE SAFETY INVARIANT: a secret value never appears in output --------------

def test_scan_text_returns_only_names_never_the_matched_value():
    secret = "ghp_SUPERSECRETtoken123456"
    names = ss.scan_text_for_names(f"token = {secret}")
    joined = "\t".join(names)
    assert secret not in joined
    assert "SUPERSECRET" not in joined


def test_scan_over_a_tree_never_emits_secret_values(tmp_path):
    secret = "AKIAIOSFODNN7EXAMPLE"
    f = tmp_path / "dot_aws" / "credentials"
    f.parent.mkdir()
    f.write_text(f"aws_access_key_id = {secret}\naws_secret_access_key = topsecretvalue\n")

    findings = ss.scan(str(tmp_path))
    blob = "\n".join(findings)
    # Findings reference the path and the reason, never the credential text itself.
    assert findings, "expected the planted credential file to be flagged"
    assert secret not in blob
    assert "topsecretvalue" not in blob
    assert all(line.split("\t")[1].startswith("reason=") for line in findings)
    assert str(f) in blob


# --- location_reason: secret-by-location ---------------------------------------

def test_location_flags_ssh_source_encoding():
    r = ss.location_reason("/src/private_dot_ssh/id_rsa")
    assert r == "location:secret-by-location (encrypt or template instead)"


def test_location_flags_raw_dot_ssh_path():
    assert ss.location_reason("/home/me/.ssh/config") is not None


def test_location_encrypted_basename_is_exempt():
    assert ss.location_reason("/src/private_dot_ssh/encrypted_id_rsa.age") is None


def test_location_does_not_trip_on_env_infix():
    # `uv.env.fish` must NOT match the `.env` dotenv rule (anchored to a segment start).
    assert ss.location_reason("/src/dot_config/fish/uv.env.fish") is None


def test_location_flags_dotenv_file():
    assert ss.location_reason("/src/dot_config/app/.env") is not None
    assert ss.location_reason("/src/dot_config/app/.env.local") is not None


def test_location_flags_credentials_file():
    assert ss.location_reason("/src/dot_config/gh/credentials") is not None


# --- scan(): finding format, sort + de-dup -------------------------------------

def test_scan_produces_sorted_unique_reason_lines(tmp_path):
    (tmp_path / "dot_netrc").write_text("machine example login me password x\n")
    findings = ss.scan(str(tmp_path))
    assert findings == sorted(findings)
    assert len(findings) == len(set(findings))
    for line in findings:
        _path, reason = line.split("\t", 1)
        assert reason.startswith("reason=")


def test_scan_skips_git_dir(tmp_path):
    gitfile = tmp_path / ".git" / "config"
    gitfile.parent.mkdir()
    gitfile.write_text("password = leaked\n")
    assert ss.scan(str(tmp_path)) == []


def test_scan_of_clean_tree_is_empty(tmp_path):
    (tmp_path / "dot_hushlogin").write_text("")
    (tmp_path / "notes.txt").write_text("nothing sensitive here\n")
    assert ss.scan(str(tmp_path)) == []
