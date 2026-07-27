"""Tests for the identity-profiles `profile_resolve` script. Pure functions -> no mocking."""

import profile_resolve as pr

# --- parse_ssh_banner ----------------------------------------------------------


def test_parse_ssh_banner_github():
    text = "Hi octocat! You've successfully authenticated, but GitHub does not provide shell access."
    assert pr.parse_ssh_banner(text) == "octocat"


def test_parse_ssh_banner_github_deploy_key_names_the_repo():
    assert pr.parse_ssh_banner("Hi acme/widgets! You've successfully authenticated") == "acme/widgets"


def test_parse_ssh_banner_gitlab():
    assert pr.parse_ssh_banner("Welcome to GitLab, @octocat!") == "octocat"


def test_parse_ssh_banner_permission_denied_yields_nothing():
    assert pr.parse_ssh_banner("git@github.com: Permission denied (publickey).") == ""


def test_parse_ssh_banner_empty():
    assert pr.parse_ssh_banner("") == ""


# --- probe_outcome: a refused host is not a refused identity -------------------


def test_probe_outcome_ok_when_the_banner_names_an_account():
    assert pr.probe_outcome("Hi octocat! You've successfully authenticated") == ("octocat", "ok")


def test_probe_outcome_host_unknown_is_distinct_from_denied():
    # Strict host checking refusing an unseen host means the check COULDN'T RUN. Reporting
    # it the same as a rejected key would call a working profile broken.
    text = ("No ED25519 host key is known for github.com and you have requested strict "
            "checking.\nHost key verification failed.")
    assert pr.probe_outcome(text) == ("", "host-unknown")


def test_probe_outcome_denied_when_the_host_refused_the_key():
    assert pr.probe_outcome("git@github.com: Permission denied (publickey).") == ("", "denied")


def test_probe_outcome_unrecognized_for_an_unfamiliar_reply():
    assert pr.probe_outcome("some other server greeting") == ("", "unrecognized")


# --- parse_gh_accounts ---------------------------------------------------------


def test_parse_gh_accounts_single():
    text = "github.com\n  ✓ Logged in to github.com account octocat (keyring)\n"
    assert pr.parse_gh_accounts(text) == ["octocat"]


def test_parse_gh_accounts_multiple_preserves_order_and_dedupes():
    text = (
        "  ✓ Logged in to github.com account work-user (keyring)\n"
        "  - Active account: true\n"
        "  ✓ Logged in to github.com account personal-user (keyring)\n"
        "  ✓ Logged in to github.com account work-user (keyring)\n"
    )
    assert pr.parse_gh_accounts(text) == ["work-user", "personal-user"]


def test_parse_gh_accounts_logged_out():
    assert pr.parse_gh_accounts("You are not logged into any GitHub hosts.") == []


# --- format_resolution ---------------------------------------------------------


def _facts(**over):
    base = {
        "path": "/home/u/work/r", "in_repo": "yes", "email": "you@work.example",
        "signingkey": "/k.pub", "gpgsign": "true", "remote": "git@github-work:a/b.git",
        "alias": "github-work", "identityfiles": ["/k"], "key_match": "ok",
        "gh_installed": True, "gh_accounts": ["work-user"], "probed": False,
        "authenticates_as": "", "probe_status": "",
    }
    base.update(over)
    return base


def test_format_resolution_emits_greppable_rows():
    lines = pr.format_resolution(_facts())
    assert "user.email\tyou@work.example" in lines
    assert "key_match\tok" in lines
    assert "gh.accounts\twork-user" in lines


def test_format_resolution_marks_missing_gh_undetermined_not_absent():
    lines = pr.format_resolution(_facts(gh_installed=False, gh_accounts=[]))
    assert any(line.startswith("gh.accounts\tundetermined") for line in lines)


def test_format_resolution_omits_the_network_row_unless_probed():
    assert not any("authenticates_as" in line for line in pr.format_resolution(_facts()))


def test_format_resolution_includes_the_probe_result_when_probed():
    lines = pr.format_resolution(_facts(probed=True, authenticates_as="work-user", probe_status="ok"))
    assert "ssh.authenticates_as\twork-user" in lines


def test_format_resolution_reports_an_unknown_host_as_undetermined():
    # Not a failed identity — a check that couldn't run. It must never read as a pass
    # OR as a rejection.
    lines = pr.format_resolution(_facts(probed=True, probe_status="host-unknown"))
    row = next(line for line in lines if line.startswith("ssh.authenticates_as"))
    assert "undetermined" in row and "known_hosts" in row


def test_format_resolution_reports_a_denied_key_distinctly():
    lines = pr.format_resolution(_facts(probed=True, probe_status="denied"))
    row = next(line for line in lines if line.startswith("ssh.authenticates_as"))
    assert "permission denied" in row and "undetermined" not in row


def test_format_resolution_says_so_when_the_banner_was_not_recognized():
    lines = pr.format_resolution(_facts(probed=True, probe_status="unrecognized"))
    row = next(line for line in lines if line.startswith("ssh.authenticates_as"))
    assert "undetermined" in row and "named no account" in row


def test_format_resolution_unset_values_render_explicitly():
    lines = pr.format_resolution(_facts(email="", signingkey="", identityfiles=[]))
    assert "user.email\t(unset)" in lines
    assert "ssh.identityfile\t(none)" in lines
