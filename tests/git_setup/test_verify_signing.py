"""Tests for the git-setup `verify_signing` script. Pure functions -> no mocking, no git."""

import pytest
import verify_signing as vs

# --- parse_args ----------------------------------------------------------------

def test_parse_args_defaults_to_inherit():
    assert vs.parse_args([]) == {"help": False, "mode": "inherit", "key": "",
                                 "email": "", "signers": ""}


def test_parse_args_self_test():
    assert vs.parse_args(["--self-test"])["mode"] == "selftest"


def test_parse_args_key_with_email_and_signers():
    parsed = vs.parse_args(["--key", "/k.pub", "--email", "me@x.com", "--signers", "/s"])
    assert parsed == {"help": False, "mode": "key", "key": "/k.pub",
                      "email": "me@x.com", "signers": "/s"}


def test_parse_args_help():
    assert vs.parse_args(["--help"]) == {"help": True}
    assert vs.parse_args(["-h"]) == {"help": True}


def test_parse_args_missing_value_raises():
    with pytest.raises(ValueError):
        vs.parse_args(["--key"])


def test_parse_args_unknown_raises():
    with pytest.raises(ValueError, match="unknown arg: --bogus"):
        vs.parse_args(["--bogus"])


# --- collapse_ws / grep_lines --------------------------------------------------

def test_collapse_ws_squeezes_newlines_and_spaces():
    assert vs.collapse_ws("a\nb   c\n") == "a b c "


def test_grep_lines_case_insensitive_filter():
    # Each matching line keeps a trailing newline, mirroring grep's output.
    text = "Good signature\nirrelevant\nNo principal matched\nERROR here\n"
    assert vs.grep_lines(text, r"signature|principal|error") == (
        "Good signature\nNo principal matched\nERROR here\n"
    )


# --- extract_good_signer -------------------------------------------------------

def test_extract_good_signer_strips_leading_space():
    show = 'x\n  Good "git" signature for me@x.com\ny\n'
    assert vs.extract_good_signer(show, "") == 'Good "git" signature for me@x.com'


def test_extract_good_signer_none_returns_empty():
    assert vs.extract_good_signer("no match here\n", "") == ""


# --- interpret_status: the four %G? outcomes -----------------------------------

def test_interpret_good():
    lines = vs.interpret_status("selftest", "G",
                                'Good "git" signature for me@x.com\n', "")
    assert lines[0] == 'verify_line\tGood "git" signature for me@x.com'
    assert lines[1] == "result\t✅\tGOOD signature — signing verifies end to end"


def test_interpret_good_falls_back_to_generic_line():
    lines = vs.interpret_status("key", "G", "", "")
    assert lines[0] == "verify_line\tGood signature"


def test_interpret_unsigned_inherit_is_yellow_real_state():
    lines = vs.interpret_status("inherit", "N", "", "")
    assert lines == ["result\t🟡\tcommit is UNSIGNED — global signing is off (this is the real current state)"]


def test_interpret_unsigned_configured_is_red():
    lines = vs.interpret_status("selftest", "N", "", "")
    assert lines == ["result\t❌\tcommit is UNSIGNED despite signing config — check gpg.format/user.signingkey"]


def test_interpret_unknown_validity_is_yellow_with_detail():
    # verify is the $()-captured value (trailing newline stripped), so no trailing space.
    lines = vs.interpret_status("key", "U", "", "No principal matched")
    assert lines[0].startswith("result\t🟡\tsigned but validity UNKNOWN")
    assert lines[1] == "detail\tNo principal matched"


def test_interpret_other_status_is_red_with_filtered_detail():
    show = "some line\nbad signature check\nprincipal error\n"
    lines = vs.interpret_status("inherit", "B", show, "")
    assert lines[0] == "result\t❌\tsignature status=B — could not verify"
    assert lines[1] == "detail\tbad signature check principal error "
