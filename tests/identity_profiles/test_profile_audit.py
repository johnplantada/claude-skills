"""Tests for the identity-profiles `profile_audit` script.

Pure functions only -> no mocking, no git, no ssh. Every cross-surface check this skill
exists for (allowed_signers pairing, ssh key match) is decided by a pure function, so the
interesting logic is all reachable from here.
"""

import os

import profile_audit as pa

# --- parse_includeif_rules -----------------------------------------------------


def test_parse_includeif_rules_reads_condition_and_path():
    lines = ["includeif.gitdir:~/work/.path /Users/u/.config/git/work.gitconfig"]
    assert pa.parse_includeif_rules(lines) == [("gitdir:~/work/", "/Users/u/.config/git/work.gitconfig")]


def test_parse_includeif_rules_splits_on_the_last_dot_path_not_the_first_dot():
    # The condition itself contains dots and colons; a naive split on '.' loses the tree.
    lines = ["includeif.gitdir:~/work/acme.corp/.path /Users/u/work.gitconfig"]
    assert pa.parse_includeif_rules(lines) == [("gitdir:~/work/acme.corp/", "/Users/u/work.gitconfig")]


def test_parse_includeif_rules_skips_keys_that_are_not_path():
    assert pa.parse_includeif_rules(["includeif.gitdir:~/work/.other value"]) == []


def test_parse_includeif_rules_skips_unrelated_and_valueless_lines():
    assert pa.parse_includeif_rules(["user.email a@b.c", "includeif.gitdir:~/w/.path"]) == []


def test_parse_includeif_rules_handles_a_space_in_the_tree():
    # Regression: splitting on the first space silently DROPPED this profile, so a
    # configured machine reported as having none. Real git output in
    # tests/fixtures/recorded/git_includeif_get_regexp.txt.
    line = "includeif.gitdir:~/my work/.path /Users/u/work.gitconfig"
    assert pa.parse_includeif_rules([line]) == [("gitdir:~/my work/", "/Users/u/work.gitconfig")]


def test_parse_includeif_rules_handles_a_space_in_the_include_path():
    line = "includeif.gitdir:~/work/.path /Users/u/My Configs/work.gitconfig"
    assert pa.parse_includeif_rules([line]) == [("gitdir:~/work/", "/Users/u/My Configs/work.gitconfig")]


def test_parse_includeif_rules_handles_spaces_on_both_sides():
    line = "includeif.gitdir:~/my work/.path /Users/u/My Configs/work.gitconfig"
    assert pa.parse_includeif_rules([line]) == [
        ("gitdir:~/my work/", "/Users/u/My Configs/work.gitconfig")
    ]


def test_parse_includeif_rules_tolerates_a_directory_literally_named_dot_path():
    # `.path ` (with the trailing space) is the separator, so `~/x.path/` is not one.
    line = "includeif.gitdir:~/x.path/.path /Users/u/w.gitconfig"
    assert pa.parse_includeif_rules([line]) == [("gitdir:~/x.path/", "/Users/u/w.gitconfig")]


def test_parse_includeif_rules_handles_multiple():
    lines = [
        "includeif.gitdir:~/work/.path /Users/u/work.gitconfig",
        "includeif.gitdir:~/personal/.path /Users/u/personal.gitconfig",
    ]
    assert len(pa.parse_includeif_rules(lines)) == 2


# --- tree_of -------------------------------------------------------------------


def test_tree_of_plain_gitdir():
    assert pa.tree_of("gitdir:~/work/") == "~/work/"


def test_tree_of_case_insensitive_form():
    assert pa.tree_of("gitdir/i:~/Work/") == "~/Work/"


def test_tree_of_strips_trailing_glob():
    assert pa.tree_of("gitdir:~/work/**") == "~/work/"


def test_tree_of_non_gitdir_conditions_are_not_profiles():
    assert pa.tree_of("onbranch:main") == ""
    assert pa.tree_of("hasconfig:remote.*.url:git@github.com:acme/**") == ""


# --- profile_name --------------------------------------------------------------


def test_profile_name_uses_the_trees_last_component():
    assert pa.profile_name("~/work/", "/Users/u/work.gitconfig") == "work"


def test_profile_name_falls_back_to_the_include_stem():
    assert pa.profile_name("/", "/Users/u/personal.gitconfig") == "personal"


def test_profile_name_never_returns_empty():
    assert pa.profile_name("", "") == "profile"


# --- alias_of_remote -----------------------------------------------------------


def test_alias_of_remote_scp_form():
    assert pa.alias_of_remote("git@github-work:acme/repo.git") == "github-work"


def test_alias_of_remote_ssh_url_form():
    assert pa.alias_of_remote("ssh://git@github-work/acme/repo.git") == "github-work"


def test_alias_of_remote_ssh_url_with_port():
    assert pa.alias_of_remote("ssh://git@github-work:2222/acme/repo.git") == "github-work"


def test_alias_of_remote_https_has_no_alias():
    # https bypasses per-alias key selection entirely — that's a finding, not a host.
    assert pa.alias_of_remote("https://github.com/acme/repo.git") == ""


def test_alias_of_remote_empty_and_local_paths():
    assert pa.alias_of_remote("") == ""
    assert pa.alias_of_remote("/srv/git/repo.git") == ""


# --- parse_ssh_identityfiles ---------------------------------------------------


def test_parse_ssh_identityfiles_expands_and_keeps_order():
    out = "hostname github.com\nidentityfile ~/.ssh/id_ed25519_work\nidentityfile ~/.ssh/id_rsa\n"
    assert pa.parse_ssh_identityfiles(out) == [
        os.path.expanduser("~/.ssh/id_ed25519_work"),
        os.path.expanduser("~/.ssh/id_rsa"),
    ]


def test_parse_ssh_identityfiles_ignores_other_keys():
    assert pa.parse_ssh_identityfiles("user git\nport 22\n") == []


def test_parse_ssh_identityfiles_tolerates_uppercase_key():
    assert pa.parse_ssh_identityfiles("IdentityFile /k") == ["/k"]


# --- key_material --------------------------------------------------------------


def test_key_material_drops_the_comment():
    # The comment differs between a .pub and allowed_signers; comparing it false-mismatches.
    assert pa.key_material("ssh-ed25519 AAAAC3Nz work@laptop\n") == "ssh-ed25519 AAAAC3Nz"


def test_key_material_of_unreadable_or_short_input():
    assert pa.key_material("") == ""
    assert pa.key_material("ssh-ed25519") == ""


# --- signers_pairing -----------------------------------------------------------

MATERIAL = "ssh-ed25519 AAAAC3Nz"


def test_signers_pairing_ok():
    text = f"you@work.example {MATERIAL} work@laptop\n"
    assert pa.signers_pairing(text, "you@work.example", MATERIAL) == "ok"


def test_signers_pairing_matches_one_of_several_principals():
    text = f"alt@x.com,you@work.example {MATERIAL}\n"
    assert pa.signers_pairing(text, "you@work.example", MATERIAL) == "ok"


def test_signers_pairing_missing_when_email_present_but_key_differs():
    # The classic second-identity trap: the file lists the personal key for the work email.
    text = "you@work.example ssh-ed25519 DIFFERENT\n"
    assert pa.signers_pairing(text, "you@work.example", MATERIAL) == "missing"


def test_signers_pairing_missing_when_key_present_but_email_differs():
    text = f"someone@else.example {MATERIAL}\n"
    assert pa.signers_pairing(text, "you@work.example", MATERIAL) == "missing"


def test_signers_pairing_does_not_match_a_substring_of_another_principal():
    text = f"notyou@work.example.org {MATERIAL}\n"
    assert pa.signers_pairing(text, "you@work.example", MATERIAL) == "missing"


def test_signers_pairing_skips_comments_and_blanks():
    text = f"# a comment\n\nyou@work.example {MATERIAL}\n"
    assert pa.signers_pairing(text, "you@work.example", MATERIAL) == "ok"


def test_signers_pairing_undetermined_states_are_distinct_from_missing():
    assert pa.signers_pairing("", "you@work.example", MATERIAL) == "no-file"
    assert pa.signers_pairing("x", "you@work.example", "") == "no-pubkey"
    assert pa.signers_pairing(f"a {MATERIAL}", "", MATERIAL) == "no-email"


# --- key_match -----------------------------------------------------------------


def test_key_match_ok_when_signing_pub_matches_the_offered_private_key():
    assert pa.key_match(["/home/u/.ssh/id_ed25519_work"], "/home/u/.ssh/id_ed25519_work.pub") == "ok"


def test_key_match_ok_among_several_offered_keys():
    files = ["/home/u/.ssh/id_rsa", "/home/u/.ssh/id_ed25519_work"]
    assert pa.key_match(files, "/home/u/.ssh/id_ed25519_work.pub") == "ok"


def test_key_match_mismatch_is_the_wrong_key_push():
    assert pa.key_match(["/home/u/.ssh/id_ed25519"], "/home/u/.ssh/id_ed25519_work.pub") == "mismatch"


def test_key_match_normalizes_redundant_path_segments():
    assert pa.key_match(["/home/u/.ssh/../.ssh/id_work"], "/home/u/.ssh/id_work.pub") == "ok"


def test_key_match_undetermined_states():
    assert pa.key_match([], "") == "no-signingkey"
    assert pa.key_match([], "/k.pub") == "no-identityfile"


def test_key_match_gpg_key_id_is_not_a_path():
    assert pa.key_match(["/home/u/.ssh/id"], "3AA5C34371567BD2") == "n/a-not-a-path"


def test_key_match_literal_ssh_key_is_not_a_path():
    # Regression: git's `key::` form embeds base64, which CONTAINS '/', so the naive
    # path test accepted it and reported a confident `mismatch` on a correct config.
    literal = "key::ssh-ed25519 AAAAC3NzaC1lZDI1/NTE5AAAAI+abc"
    assert pa.key_match(["/home/u/.ssh/id_ed25519"], literal) == "n/a-literal-key"


def test_key_match_bare_key_material_is_not_a_path():
    assert pa.key_match(["/home/u/.ssh/id"], "ssh-ed25519 AAAAC3Nz/abc") == "n/a-literal-key"


# --- is_true (git's boolean spellings) -----------------------------------------


def test_is_true_accepts_every_spelling_git_does():
    for value in ("true", "TRUE", "1", "yes", "on", " true "):
        assert pa.is_true(value), value


def test_is_true_rejects_the_false_spellings_and_unset():
    for value in ("false", "0", "no", "off", "", "   "):
        assert not pa.is_true(value), value


def test_signing_checks_fire_for_every_true_spelling():
    # Regression: `commit.gpgsign = 1` made signing_on False, which downgraded the
    # flagship 🔴 (signed but unpaired in allowed_signers) to a benign 🟡 "signing off".
    for value in ("true", "1", "yes", "on"):
        gaps = pa.gaps_for(_profile(gpgsign=value, signers="missing"))
        assert [(g[0], g[2]) for g in gaps] == [(pa.RED, "allowed_signers")], value


# --- gaps_for ------------------------------------------------------------------


def _profile(**over):
    base = {
        "name": "work", "tree": "~/work/", "include": "/w.gitconfig", "probe": "/home/u/work/r",
        "email": "you@work.example", "signingkey": "/k.pub", "gpgsign": "true", "format": "ssh",
        "signers_path": "/s", "signers": "ok", "remote": "git@github-work:a/b.git",
        "alias": "github-work", "identityfiles": ["/k"], "key_match": "ok",
    }
    base.update(over)
    return base


def test_gaps_for_clean_profile_reports_nothing():
    assert pa.gaps_for(_profile()) == []


def test_gaps_for_key_mismatch_is_red():
    gaps = pa.gaps_for(_profile(key_match="mismatch", identityfiles=["/other"]))
    assert [(g[0], g[2]) for g in gaps] == [(pa.RED, "key_match")]


def test_gaps_for_signed_but_unpaired_is_red():
    gaps = pa.gaps_for(_profile(signers="missing"))
    assert [(g[0], g[2]) for g in gaps] == [(pa.RED, "allowed_signers")]


def test_gaps_for_signing_on_with_no_signers_file_is_red():
    gaps = pa.gaps_for(_profile(signers="no-file"))
    assert [(g[0], g[2]) for g in gaps] == [(pa.RED, "allowed_signers")]


def test_gaps_for_unpaired_signers_is_not_reported_when_signing_is_off():
    # Nothing is signing, so an unpaired allowed_signers file breaks nothing yet.
    checks = [g[2] for g in pa.gaps_for(_profile(gpgsign="false", signers="missing"))]
    assert checks == ["commit.gpgsign"]


def test_gaps_for_missing_email_is_red():
    assert any(g[0] == pa.RED and g[2] == "user.email" for g in pa.gaps_for(_profile(email="")))


def test_gaps_for_https_remote_is_yellow():
    gaps = pa.gaps_for(_profile(alias="", remote="https://github.com/a/b.git", key_match="no-identityfile"))
    assert (pa.YELLOW, "remote_alias") in [(g[0], g[2]) for g in gaps]


def test_gaps_for_missing_probe_repo_is_a_single_yellow():
    gaps = pa.gaps_for(_profile(probe=""))
    assert [(g[0], g[2]) for g in gaps] == [(pa.YELLOW, "probe_repo")]


# --- format_gaps / format_profile ----------------------------------------------


def test_format_gaps_sorts_red_before_yellow():
    gaps = [(pa.YELLOW, "p", "a", "m1"), (pa.RED, "p", "b", "m2")]
    assert pa.format_gaps(gaps)[1].startswith(f"gap\t{pa.RED}")


def test_format_gaps_empty_says_so_explicitly():
    assert "none" in pa.format_gaps([])[1]


def test_format_profile_without_a_probe_repo_reports_undetermined_not_a_pass():
    lines = pa.format_profile(_profile(probe=""))
    assert any("undetermined" in line for line in lines)


def test_format_profile_rows_are_prefixed_with_the_profile_name():
    lines = pa.format_profile(_profile())
    assert "work.user.email\tyou@work.example" in lines
    assert "work.key_match\tok" in lines


# --- discover ------------------------------------------------------------------


def test_no_profiles_is_undetermined_not_a_clean_bill():
    # Regression: the empty-gap line ("every declared profile agrees") shipped for a
    # machine with ZERO profiles, so "nothing declared" read as "nothing wrong".
    lines = pa.format_no_profiles()
    assert any(line.startswith("gaps\tundetermined") for line in lines)
    assert not any("agrees across surfaces" in line for line in lines)


def test_discover_returns_profiles_and_notes_non_tree_conditions():
    rules = [("gitdir:~/work/", "/w"), ("onbranch:main", "/b")]
    profiles, notes = pa.discover(rules)
    assert profiles == [("work", "~/work/", "/w")]
    assert len(notes) == 1 and "not a gitdir condition" in notes[0]
