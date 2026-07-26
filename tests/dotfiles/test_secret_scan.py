"""Tests for the dotfiles `secret_scan` tripwire.

The pinned safety invariant is here: detection emits pattern/rule NAMES, PATHS, and
match-LOCATIONS only — a matched secret value must NEVER appear in the output, whether
the engine is the built-in patterns or gitleaks. Pure functions -> no chezmoi, no gitleaks.

Note: the "token" fixtures are split across `+` so the contiguous credential string never
appears literally in source (keeps GitHub push-protection from tripping on the tests); the
runtime value is identical, so detection is exercised for real.
"""

import json

import pytest
import secret_scan as ss


@pytest.fixture(autouse=True)
def _force_builtin_engine(monkeypatch):
    # Keep scan()/content_findings deterministic regardless of whether gitleaks happens to
    # be installed on the test host; the gitleaks path has its own tests below.
    monkeypatch.setattr(ss, "gitleaks_available", lambda: False)


# --- scan_text_for_names: built-in content detection ---------------------------

def test_detects_private_key_block():
    text = "-----BEGIN OPENSSH " + "PRIVATE KEY-----\n"
    assert ss.scan_text_for_names(text) == ["private-key-block"]


def test_detects_aws_access_key_id():
    # AWS's official documentation example key (allowlisted by scanners).
    assert ss.scan_text_for_names("id = AKIAIOSFODNN7EXAMPLE") == ["aws-access-key-id"]


def test_detects_github_token():
    assert ss.scan_text_for_names("ghp_" + "0123456789abcdefABCD") == ["github-token"]


def test_detects_slack_token():
    assert ss.scan_text_for_names("xoxb-" + "1234567890-abcdef") == ["slack-token"]


def test_detects_generic_assignment():
    assert ss.scan_text_for_names('api_key = "hunter2"') == ["generic-assignment"]
    assert ss.scan_text_for_names("password: swordfish") == ["generic-assignment"]


def test_clean_text_yields_no_names():
    assert ss.scan_text_for_names("editor = nvim\n") == []
    assert ss.scan_text_for_names("plain prose with no markers") == []


# --- THE SAFETY INVARIANT: a secret value never appears in output --------------

def test_scan_text_returns_only_names_never_the_matched_value():
    secret = "ghp_" + "SUPERSECRETtoken123456"
    names = ss.scan_text_for_names(f"token = {secret}")
    joined = "\t".join(names)
    assert secret not in joined
    assert "SUPERSECRET" not in joined


def test_scan_over_a_tree_never_emits_secret_values(tmp_path):
    secret = "AKIAIOSFODNN7EXAMPLE"
    f = tmp_path / "dot_aws" / "credentials"
    f.parent.mkdir()
    f.write_text(f"aws_access_key_id = {secret}\naws_secret_access_key = topsecretvalue\n")

    findings, _engine = ss.scan(str(tmp_path))
    blob = "\n".join(findings)
    assert findings, "expected the planted credential file to be flagged"
    assert secret not in blob
    assert "topsecretvalue" not in blob
    assert all(line.split("\t")[1].startswith("reason=") for line in findings)
    assert str(f) in blob


# --- gitleaks engine: pure JSON parsing, metadata-only -------------------------

def test_parse_gitleaks_report_extracts_only_file_and_rule():
    leaked = "ghp_" + "REALLEAKEDSECRETvalue00000"
    report = json.dumps([
        {"File": "dot_env", "RuleID": "generic-api-key",
         "Secret": leaked, "Match": f"key={leaked}", "StartLine": 3},
    ])
    out = ss.parse_gitleaks_report(report)
    assert out == {"dot_env\treason=gitleaks:generic-api-key"}
    blob = "\n".join(out)
    assert "REALLEAKEDSECRET" not in blob  # Secret/Match fields are never read
    assert "key=" not in blob


def test_parse_gitleaks_report_tolerates_empty_and_garbage():
    assert ss.parse_gitleaks_report("[]") == set()
    assert ss.parse_gitleaks_report("") == set()
    assert ss.parse_gitleaks_report("not json at all") == set()
    assert ss.parse_gitleaks_report(json.dumps({"not": "a list"})) == set()


def test_content_findings_prefers_gitleaks_when_present(monkeypatch):
    monkeypatch.setattr(ss, "gitleaks_available", lambda: True)
    monkeypatch.setattr(ss, "gitleaks_findings", lambda target: {"f\treason=gitleaks:x"})
    assert ss.content_findings("/anything") == ({"f\treason=gitleaks:x"}, "gitleaks")


def test_content_findings_falls_back_when_gitleaks_errors(monkeypatch, tmp_path):
    # gitleaks present but produced no report (a run error) -> use the built-in patterns,
    # never silently report "clean" — and the reported ENGINE must be the fallback, not
    # gitleaks (the summary line must not claim an engine that didn't run).
    (tmp_path / "leak").write_text("token = ghp_" + "0123456789abcdefABCD\n")
    monkeypatch.setattr(ss, "gitleaks_available", lambda: True)
    monkeypatch.setattr(ss, "gitleaks_findings", lambda target: None)
    found, engine = ss.content_findings(str(tmp_path))
    assert any("github-token" in line for line in found)
    assert engine == "built-in patterns"


# --- location_reason: secret-by-location ---------------------------------------

def test_location_flags_ssh_source_encoding():
    r = ss.location_reason("/src/private_dot_ssh/id_rsa")
    assert r == "location:secret-by-location (encrypt or template instead)"


def test_location_flags_raw_dot_ssh_path():
    assert ss.location_reason("/home/me/.ssh/config") is not None


def test_location_encrypted_basename_is_exempt():
    assert ss.location_reason("/src/private_dot_ssh/encrypted_id_rsa.age") is None


def test_location_does_not_trip_on_env_infix():
    assert ss.location_reason("/src/dot_config/fish/uv.env.fish") is None


def test_location_flags_dotenv_file():
    assert ss.location_reason("/src/dot_config/app/.env") is not None
    assert ss.location_reason("/src/dot_config/app/.env.local") is not None


def test_location_flags_credentials_file():
    assert ss.location_reason("/src/dot_config/gh/credentials") is not None


# --- scan(): finding format, sort + de-dup -------------------------------------

def test_scan_produces_sorted_unique_reason_lines(tmp_path):
    (tmp_path / "dot_netrc").write_text("machine example login me password x\n")
    findings, _engine = ss.scan(str(tmp_path))
    assert findings == sorted(findings)
    assert len(findings) == len(set(findings))
    for line in findings:
        _path, reason = line.split("\t", 1)
        assert reason.startswith("reason=")


def test_scan_skips_git_dir(tmp_path):
    gitfile = tmp_path / ".git" / "config"
    gitfile.parent.mkdir()
    gitfile.write_text("password = leaked\n")
    assert ss.scan(str(tmp_path))[0] == []


def test_scan_of_clean_tree_is_empty(tmp_path):
    (tmp_path / "dot_hushlogin").write_text("")
    (tmp_path / "notes.txt").write_text("nothing sensitive here\n")
    assert ss.scan(str(tmp_path))[0] == []


def test_parse_gitleaks_report_anchors_relative_paths_to_base():
    # Both engines must emit the same path shape: the built-in scanner walks real
    # paths, so a relative gitleaks File is joined onto the scanned target dir.
    report = json.dumps([{"File": "dot_env", "RuleID": "r"}])
    assert ss.parse_gitleaks_report(report, base="/src") == {"/src/dot_env\treason=gitleaks:r"}
    absolute = json.dumps([{"File": "/abs/dot_env", "RuleID": "r"}])
    assert ss.parse_gitleaks_report(absolute, base="/src") == {"/abs/dot_env\treason=gitleaks:r"}
