"""Tests for the credential-store `credential_audit` script.

Pure functions -> no mocking, no filesystem. The literal-vs-reference classification is
the whole skill, so it carries the most cases; and one test pins the safety property the
skill is built around — a finding can never carry a secret's value.

The "secrets" below are invented strings that match no real credential format in use.
"""

import credential_audit as ca

# --- parse_assignment ----------------------------------------------------------


def test_parse_assignment_export_form():
    assert ca.parse_assignment("export API_TOKEN=abc") == ("API_TOKEN", "abc")


def test_parse_assignment_bare_form():
    assert ca.parse_assignment("API_TOKEN=abc") == ("API_TOKEN", "abc")


def test_parse_assignment_indented():
    assert ca.parse_assignment("   export API_TOKEN=abc") == ("API_TOKEN", "abc")


def test_parse_assignment_fish_form():
    assert ca.parse_assignment("set -gx API_TOKEN abc") == ("API_TOKEN", "abc")


def test_parse_assignment_fish_without_flags():
    assert ca.parse_assignment("set API_TOKEN abc") == ("API_TOKEN", "abc")


def test_parse_assignment_ignores_comments():
    assert ca.parse_assignment("# export API_TOKEN=abc") is None
    assert ca.parse_assignment("   # API_TOKEN=abc") is None


def test_parse_assignment_ignores_non_assignments():
    assert ca.parse_assignment("echo hello") is None
    assert ca.parse_assignment("") is None


def test_parse_assignment_keeps_the_whole_rhs_including_spaces():
    var, rhs = ca.parse_assignment('export API_TOKEN="$(op read op://a/b/c)"')
    assert var == "API_TOKEN"
    assert rhs == '"$(op read op://a/b/c)"'


# --- is_credential_name --------------------------------------------------------


def test_is_credential_name_matches_common_shapes():
    for name in ("GITHUB_TOKEN", "OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY",
                 "DB_PASSWORD", "MY_CREDENTIAL", "NPM_AUTH"):
        assert ca.is_credential_name(name), name


def test_is_credential_name_is_case_insensitive():
    assert ca.is_credential_name("github_token")


def test_is_credential_name_rejects_pointers_not_secrets():
    # These name a LOCATION of a credential, not the credential — flagging them is noise.
    for name in ("SSH_KEY_PATH", "TOKEN_FILE", "SECRET_DIR", "AUTH_URL", "API_KEY_NAME"):
        assert not ca.is_credential_name(name), name


def test_is_credential_name_rejects_ordinary_variables():
    for name in ("EDITOR", "PATH", "LANG", "KEYBOARD_LAYOUT_ID"):
        assert not ca.is_credential_name(name), name


# --- classify_rhs --------------------------------------------------------------


def test_classify_rhs_literal_unquoted():
    assert ca.classify_rhs("zzqq-not-a-real-token") == "literal"


def test_classify_rhs_literal_double_quoted():
    assert ca.classify_rhs('"zzqq-not-a-real-token"') == "literal"


def test_classify_rhs_literal_single_quoted():
    assert ca.classify_rhs("'zzqq-not-a-real-token'") == "literal"


def test_classify_rhs_command_substitution_is_a_reference():
    assert ca.classify_rhs('"$(op read op://Personal/GitHub/token)"') == "reference"


def test_classify_rhs_keychain_lookup_is_a_reference():
    assert ca.classify_rhs('"$(security find-generic-password -s GH -w)"') == "reference"


def test_classify_rhs_backticks_are_a_reference():
    assert ca.classify_rhs("`pass show gh/token`") == "reference"


def test_classify_rhs_variable_indirection_is_a_reference():
    assert ca.classify_rhs("$OTHER_TOKEN") == "reference"
    assert ca.classify_rhs("${OTHER_TOKEN}") == "reference"


def test_classify_rhs_chezmoi_template_is_a_reference():
    assert ca.classify_rhs('"{{ onepasswordRead "op://a/b/c" }}"') == "reference"


def test_classify_rhs_reading_a_plaintext_file_is_its_own_category():
    # Better than inlining, but the secret is still readable on disk.
    assert ca.classify_rhs('"$(cat ~/.mytoken)"') == "file-reference"
    assert ca.classify_rhs('"$(< ~/.mytoken)"') == "file-reference"


def test_classify_rhs_path_is_not_a_secret():
    assert ca.classify_rhs("~/.ssh/id_ed25519") == "path"
    assert ca.classify_rhs('"/etc/ssl/cert.pem"') == "path"


def test_classify_rhs_empty():
    assert ca.classify_rhs("") == "empty"
    assert ca.classify_rhs('""') == "empty"
    assert ca.classify_rhs("   ") == "empty"


# --- scan_assignments ----------------------------------------------------------


def test_scan_assignments_reports_line_numbers_and_classification():
    lines = [
        "# my shell rc",
        "export EDITOR=nvim",
        "export GITHUB_TOKEN=zzqq-not-a-real-token",
        'export OPENAI_API_KEY="$(op read op://Personal/OpenAI/key)"',
    ]
    assert ca.scan_assignments(lines) == [
        (3, "GITHUB_TOKEN", "literal"),
        (4, "OPENAI_API_KEY", "reference"),
    ]


def test_scan_assignments_skips_non_credential_variables():
    assert ca.scan_assignments(["export EDITOR=nvim", "export PATH=/usr/bin"]) == []


def test_scan_assignments_never_returns_the_value():
    # THE core safety property, pinned structurally: a finding is (line, name, kind).
    # If a future refactor threaded the RHS through, this fails loudly.
    secret = "zzqq-invented-secret-value-9f3a"
    findings = ca.scan_assignments([f"export API_TOKEN={secret}"])
    assert findings == [(1, "API_TOKEN", "literal")]
    assert secret not in repr(findings)


def test_formatted_output_never_contains_the_value():
    # The end-to-end version of the property: value in, value NOT in the printed report.
    secret = "zzqq-invented-secret-value-9f3a"
    scanned = ca.scan_assignments([f"export API_TOKEN={secret}"])
    rendered = "\n".join(ca.format_findings(ca.shell_findings("/home/u/.zshrc", scanned)))
    assert secret not in rendered
    assert "API_TOKEN" in rendered and "/home/u/.zshrc:1" in rendered


# --- inventory_rows (the redacted review view) ---------------------------------


def test_inventory_rows_lists_every_assignment_with_its_flag():
    lines = ["export EDITOR=nvim", "export STRIPE_SK=zzqq-invented"]
    rows = ca.inventory_rows("/home/u/.zshrc", lines)
    assert rows == [
        "assignment\t/home/u/.zshrc:1\tEDITOR\tliteral\tflagged=no",
        "assignment\t/home/u/.zshrc:2\tSTRIPE_SK\tliteral\tflagged=no",
    ]


def test_inventory_rows_marks_heuristic_hits():
    rows = ca.inventory_rows("/rc", ["export GITHUB_TOKEN=zzqq"])
    assert rows[0].endswith("flagged=yes")


def test_inventory_rows_never_contains_a_value():
    # This view is what a REVIEWER (or subagent) reads, so it must be value-free by
    # construction — that is the whole reason the review is safe to delegate.
    secret = "zzqq-invented-secret-value-9f3a"
    rows = ca.inventory_rows("/rc", [f"export STRIPE_SK={secret}"])
    assert secret not in "\n".join(rows)


def test_inventory_rows_skips_non_assignments():
    assert ca.inventory_rows("/rc", ["# comment", "echo hi", ""]) == []


# --- severity ------------------------------------------------------------------


def test_severity_of_each_classification():
    assert ca.severity_of("literal") == ca.RED
    assert ca.severity_of("file-reference") == ca.YELLOW
    assert ca.severity_of("reference") == ca.GREEN


def test_severity_of_non_findings_is_empty():
    assert ca.severity_of("path") == ""
    assert ca.severity_of("empty") == ""


def test_location_severity_grades_by_readability():
    assert ca.location_severity("0600") == ca.YELLOW   # plaintext, but owner-only
    assert ca.location_severity("0644") == ca.RED      # world-readable
    assert ca.location_severity("0640") == ca.RED      # group-readable


def test_location_severity_unknown_mode_is_not_a_pass():
    assert ca.location_severity("???") == ca.YELLOW


# --- shell_findings / format_findings ------------------------------------------


def test_shell_findings_drops_non_findings():
    scanned = [(1, "SSH_KEY", "path"), (2, "EMPTY_TOKEN", "empty")]
    assert ca.shell_findings("/home/u/.zshrc", scanned) == []


def test_format_findings_sorts_red_then_yellow_then_green():
    findings = [
        (ca.GREEN, "shell", "a", "ok"),
        (ca.YELLOW, "file", "b", "meh"),
        (ca.RED, "shell", "c", "bad"),
    ]
    rendered = ca.format_findings(findings)
    assert rendered[0].startswith(f"finding\t{ca.RED}")
    assert rendered[1].startswith(f"finding\t{ca.YELLOW}")
    assert rendered[2].startswith(f"finding\t{ca.GREEN}")


def test_format_findings_empty_states_what_was_looked_for():
    assert "none" in ca.format_findings([])[0]
