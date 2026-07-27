"""Tests for the credential-store `store_status` script. Pure functions -> no mocking."""

import store_status as ss

# --- parse_op_accounts ---------------------------------------------------------


def test_parse_op_accounts_prefers_email():
    text = '[{"email": "you@example.com", "url": "my.1password.com", "account_uuid": "ABC"}]'
    assert ss.parse_op_accounts(text) == ["you@example.com"]


def test_parse_op_accounts_falls_back_to_url_then_uuid():
    assert ss.parse_op_accounts('[{"url": "my.1password.com"}]') == ["my.1password.com"]
    assert ss.parse_op_accounts('[{"account_uuid": "ABC"}]') == ["ABC"]


def test_parse_op_accounts_multiple():
    text = '[{"email": "a@x.com"}, {"email": "b@y.com"}]'
    assert ss.parse_op_accounts(text) == ["a@x.com", "b@y.com"]


def test_parse_op_accounts_bad_input_is_empty_not_an_exception():
    # A store that can't be read must degrade to "undetermined" upstream, never crash.
    assert ss.parse_op_accounts("") == []
    assert ss.parse_op_accounts("not json") == []
    assert ss.parse_op_accounts('{"email": "a@x.com"}') == []  # object, not a list
    assert ss.parse_op_accounts("[1, 2, 3]") == []


def test_parse_op_accounts_skips_entries_with_no_identifier():
    assert ss.parse_op_accounts('[{"shorthand": "x"}, {"email": "a@x.com"}]') == ["a@x.com"]


# --- recommend -----------------------------------------------------------------


def test_recommend_prefers_keychain_when_available():
    assert ss.recommend({"keychain": True, "1password": True, "pass": True}) == "keychain"


def test_recommend_falls_through_preference_order():
    assert ss.recommend({"keychain": False, "1password": True, "pass": True}) == "1password"
    assert ss.recommend({"keychain": False, "1password": False, "pass": True}) == "pass"


def test_recommend_returns_empty_when_nothing_is_available():
    assert ss.recommend({"keychain": False, "1password": False}) == ""
    assert ss.recommend({}) == ""


# --- how_to_reference ----------------------------------------------------------


def test_how_to_reference_gives_a_runnable_shell_line_per_store():
    assert "security find-generic-password" in ss.how_to_reference("keychain")
    assert "op read" in ss.how_to_reference("1password")
    assert "pass show" in ss.how_to_reference("pass")


def test_how_to_reference_unknown_store_is_empty():
    assert ss.how_to_reference("nonesuch") == ""


def test_every_preferred_store_has_a_reference_form():
    # A recommended store with no reference form leaves the user with no next step.
    assert all(ss.how_to_reference(name) for name in ss._PREFERENCE)


# --- format_stores -------------------------------------------------------------


def test_format_stores_reports_every_store_present_or_absent():
    rows = ss.format_stores({"keychain": True, "1password": False, "pass": False,
                             "chezmoi-encryption": False}, {})
    assert "store.keychain\tavailable" in rows
    assert "store.1password\tabsent" in rows


# --- store_state: unusable is a third state, not a flavour of absent -----------


def test_store_state_available():
    assert ss.store_state("keychain", {"keychain": True}, {}) == "available"


def test_store_state_absent_when_not_installed():
    assert ss.store_state("pass", {"pass": False}, {}) == "absent"


def test_store_state_installed_but_locked_is_unusable_not_absent():
    # Regression: a locked 1Password printed `absent` while the note below it said
    # "installed but locked" — the row contradicted the note, and "absent" sends the
    # user to install a store they already own.
    state = ss.store_state("1password", {"1password": False}, {"1password": "locked"})
    assert state == "unusable"


def test_format_stores_prints_the_reason_for_an_unusable_store():
    rows = ss.format_stores({"1password": False}, {}, {"1password": "op is locked"})
    assert "store.1password\tunusable" in rows
    assert "store.1password.reason\top is locked" in rows


def test_format_stores_never_calls_an_unusable_store_absent():
    rows = ss.format_stores({name: False for name in ss._PREFERENCE}, {}, {"1password": "locked"})
    assert not any(row == "store.1password\tabsent" for row in rows)


def test_format_stores_includes_detail_when_present():
    rows = ss.format_stores({"1password": True}, {"1password": "accounts=a@x.com"})
    assert "store.1password.detail\taccounts=a@x.com" in rows


def test_format_stores_order_is_stable():
    rows = ss.format_stores({name: True for name in ss._PREFERENCE}, {})
    names = [r.split("\t")[0] for r in rows]
    assert names == [f"store.{n}" for n in ss._PREFERENCE]
