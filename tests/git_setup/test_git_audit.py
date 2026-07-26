"""Tests for the git-setup `git_audit` script. Pure functions -> no mocking, no git."""

import git_audit as ga


# --- parsing helpers -----------------------------------------------------------

def test_includes_from_takes_second_field_with_trailing_space():
    lines = ["include.path /a/one.gitconfig", "include.path /b/two.gitconfig"]
    assert ga.includes_from(lines) == "/a/one.gitconfig /b/two.gitconfig "


def test_includes_from_empty_is_empty_string():
    assert ga.includes_from([]) == ""


def test_includeif_keys_from_takes_the_key_field():
    lines = ["includeif.gitdir:~/work/.path /w.gitconfig"]
    assert ga.includeif_keys_from(lines) == "includeif.gitdir:~/work/.path "


def test_first_email_origin_strips_file_prefix_and_takes_first():
    show = (
        "file:/home/u/.gitconfig\tuser.name=U\n"
        "file:/home/u/.gitconfig\tuser.email=a@x.com\n"
        "file:/home/u/work.gitconfig\tuser.email=b@y.com\n"
    )
    assert ga.first_email_origin(show) == "/home/u/.gitconfig"


def test_first_email_origin_none_when_absent():
    assert ga.first_email_origin("file:/x\tuser.name=U\n") == ""


# --- signing gaps: the two signing traps ---------------------------------------

def test_no_signing_is_a_yellow_gap():
    gaps = ga.signing_gaps(gpgsign="", fmt="", signkey="", signers="")
    assert gaps == [(
        "Y",
        "no commit signing (commits show unverified on GitHub)",
        "see reference/configure.md §4 — set up SSH signing",
    )]


def test_signed_but_no_allowed_signers_is_red():
    # The signed-but-won't-verify trap.
    gaps = ga.signing_gaps(gpgsign="true", fmt="ssh", signkey="~/.ssh/id.pub", signers="")
    assert gaps[0][0] == "R"
    assert "WON'T VERIFY" in gaps[0][1]


def test_private_key_path_as_signingkey_is_red():
    gaps = ga.signing_gaps(gpgsign="true", fmt="ssh", signkey="~/.ssh/id_ed25519",
                           signers="/some/allowed_signers")
    assert gaps == [(
        "R",
        "user.signingkey looks like a PRIVATE key path (ssh format expects a .pub)",
        "git config --global user.signingkey ~/.ssh/id_ed25519.pub",
    )]


def test_pub_signingkey_with_signers_is_no_gap():
    assert ga.signing_gaps(gpgsign="true", fmt="ssh", signkey="~/.ssh/id.pub",
                           signers="/allowed") == []


# --- the other gap categories --------------------------------------------------

def test_pager_gap_when_no_delta_binary():
    assert ga.pager_gap(pager="delta", delta="")[0][0] == "G"
    assert ga.pager_gap(pager="delta", delta="/usr/bin/delta") == []


def test_default_gaps_flags_only_unset_keys_in_order():
    defaults = {"init.defaultBranch": "main", "pull.rebase": "",
                "push.autoSetupRemote": "true", "push.default": "",
                "fetch.prune": "true", "rebase.autostash": "true"}
    gaps = ga.default_gaps(defaults)
    msgs = [m for _, m, _ in gaps]
    assert msgs == [
        "default pull.rebase unset (recommend: true)",
        "default push.default unset (recommend: simple)",
    ]


def test_gitignore_gap_only_when_both_absent():
    assert ga.gitignore_gap(excludes="", xdg_ignore_exists=False)[0][0] == "Y"
    assert ga.gitignore_gap(excludes="~/.gi", xdg_ignore_exists=False) == []
    assert ga.gitignore_gap(excludes="", xdg_ignore_exists=True) == []


def test_credential_gap_is_macos_only():
    assert ga.credential_gap("Darwin", "")[0][0] == "Y"
    assert ga.credential_gap("Darwin", "osxkeychain") == []
    assert ga.credential_gap("Linux", "") == []


def test_alias_gap_only_when_zero():
    assert ga.alias_gap(0)[0][0] == "G"
    assert ga.alias_gap(3) == []


def test_identity_gap_when_single_global_email():
    assert ga.identity_gap(email="me@x.com", includeif="")[0][0] == "G"
    assert ga.identity_gap(email="me@x.com", includeif="includeif.gitdir:~/w ") == []
    assert ga.identity_gap(email="", includeif="") == []


# --- formatting ----------------------------------------------------------------

def test_format_gaps_orders_red_yellow_green_with_fixes():
    findings = [
        ("G", "green msg", "green fix"),
        ("R", "red msg", "red fix"),
        ("Y", "yellow msg", ""),
    ]
    lines = ga.format_gaps(findings)
    assert lines[0] == "-- gaps (🔴 fix now / 🟡 should fix / 🟢 nice to have) --"
    assert lines[1:] == [
        "gap\t🔴\tred msg",
        "fix\t  red fix",
        "gap\t🟡\tyellow msg",
        "gap\t🟢\tgreen msg",
        "fix\t  green fix",
    ]


def test_format_gaps_reports_clean_when_empty():
    lines = ga.format_gaps([])
    assert lines[-1] == "gap\t✅\tnone — global git config is in good shape"


def test_format_facts_uses_placeholder_defaults():
    facts = {
        "git_version": "2.39.3", "platform": "Darwin", "gitconfig": "(none)",
        "includes": "", "gpgsign": "", "format": "", "signkey": "", "signers": "",
        "pager": "", "delta": "", "defaults": {}, "global_gitignore": "(none)",
        "cred": "", "name": "", "email": "", "email_origin": "", "includeif": "",
    }
    lines = ga.format_facts(facts)
    assert "signing.gpgsign\tfalse" in lines
    assert "signing.format\t(unset)" in lines
    assert "pager\t(unset, plain less)" in lines
    assert "delta_installed\tno" in lines
    assert "includes\t(none)" in lines
    assert "identity.includeif\t(none)" in lines
    assert "default.init.defaultBranch\t(unset)" in lines


def test_evaluate_gaps_end_to_end_order():
    facts = {
        "gpgsign": "", "format": "", "signkey": "", "signers": "",
        "pager": "", "delta": "",
        "defaults": {k: "" for k, _ in ga.SANE_DEFAULTS},
        "excludes": "", "xdg_ignore_exists": False,
        "platform": "Darwin", "cred": "",
        "alias_count": 0, "email": "me@x.com", "includeif": "",
    }
    findings = ga.evaluate_gaps(facts)
    severities = [s for s, _, _ in findings]
    # signing(Y), pager(G), 6 defaults(G), gitignore(Y), credential(Y), alias(G), identity(G)
    assert severities.count("R") == 0
    assert severities.count("Y") == 3
    assert severities.count("G") == 9
