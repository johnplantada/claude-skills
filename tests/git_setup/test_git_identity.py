"""Tests for the git-setup `git_identity` script. Pure functions -> no mocking, no git."""

import git_identity as gi

# --- origin_of: the "which file supplied this value" logic ----------------------

def test_origin_of_strips_file_prefix():
    show = "file:/home/u/.gitconfig\tuser.email=a@x.com\n"
    assert gi.origin_of(show, "user.email") == "/home/u/.gitconfig"


def test_origin_of_takes_the_last_match():
    # An includeIf override wins: the later file is the effective source (tail -1).
    show = (
        "file:/home/u/.gitconfig\tuser.email=a@x.com\n"
        "file:/home/u/work.gitconfig\tuser.email=b@y.com\n"
    )
    assert gi.origin_of(show, "user.email") == "/home/u/work.gitconfig"


def test_origin_of_matches_only_the_exact_key_prefix():
    # user.emailfoo must not match a query for user.email.
    show = "file:/x\tuser.emailobfuscate=1\n"
    assert gi.origin_of(show, "user.email") == ""


def test_origin_of_preserves_non_file_origins():
    show = "command line:\tuser.email=a@x.com\n"
    assert gi.origin_of(show, "user.email") == "command line:"


def test_origin_of_absent_key_is_empty():
    assert gi.origin_of("file:/x\tuser.name=U\n", "user.signingkey") == ""


# --- format_rules --------------------------------------------------------------

def test_format_rules_prefixes_each_rule():
    rules = ["includeif.gitdir:~/work/.path ~/work.gitconfig",
             "includeif.gitdir:~/oss/.path ~/oss.gitconfig"]
    assert gi.format_rules(rules) == [
        "rule\tincludeif.gitdir:~/work/.path ~/work.gitconfig",
        "rule\tincludeif.gitdir:~/oss/.path ~/oss.gitconfig",
    ]


def test_format_rules_none_note_when_empty():
    assert gi.format_rules([]) == ["rule\t(none — every repo uses the global identity)"]


# --- format_identity -----------------------------------------------------------

def test_format_identity_placeholders_and_order():
    facts = {
        "query_path": "/repo", "in_repo": "yes", "repo_root": "/repo",
        "name": "U", "email": "", "email_from": "/repo/.git/config",
        "signkey": "", "signkey_from": "", "gpgsign": "", "format": "",
    }
    lines = gi.format_identity(facts)
    assert lines[0] == "query_path\t/repo"
    assert lines[1] == "in_repo\tyes"
    assert lines[2] == "repo_root\t/repo"
    assert "user.email\t(unset)" in lines
    assert "user.email_from\t/repo/.git/config" in lines
    assert "signing.key\t(unset)" in lines
    assert "signing.gpgsign\t(unset)" in lines
