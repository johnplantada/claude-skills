"""Tests for the shared primitives in lib/devenv_common.py."""

from lib import devenv_common as c


def test_read_text_returns_contents(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello\n")
    assert c.read_text(p) == "hello\n"


def test_read_text_accepts_str_and_path(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("x")
    assert c.read_text(str(p)) == "x"
    assert c.read_text(p) == "x"


def test_read_text_missing_file_returns_empty(tmp_path):
    assert c.read_text(tmp_path / "nope") == ""


def test_read_text_decodes_binary_leniently(tmp_path):
    p = tmp_path / "bin"
    p.write_bytes(b"ok\xff\xfebytes")
    # never raises; degrades to a searchable string
    assert "ok" in c.read_text(p)


def test_command_available_true_for_a_real_binary():
    assert c.command_available("python3") is True


def test_command_available_false_for_missing():
    assert c.command_available("definitely-not-a-real-binary-xyz") is False


def test_command_path_returns_path_or_empty():
    assert c.command_path("python3").endswith("python3")
    assert c.command_path("definitely-not-a-real-binary-xyz") == ""


def test_run_captures_output_and_never_raises():
    proc = c.run(["printf", "hi"])
    assert proc.returncode == 0
    assert proc.stdout == "hi"
    # a non-zero exit is returned, not raised
    assert c.run(["false"]).returncode != 0


def test_run_rc_returns_code_and_output():
    assert c.run_rc(["printf", "hi"]) == (0, "hi")
    rc, _out = c.run_rc(["false"])
    assert rc != 0


def test_run_rc_merge_folds_stderr():
    _rc, out = c.run_rc(["sh", "-c", "echo err >&2"], merge=True)
    assert "err" in out
    # without merge, stderr is dropped
    assert c.run_rc(["sh", "-c", "echo err >&2"])[1] == ""


def test_run_rc_unlaunchable_returns_1_empty():
    assert c.run_rc(["definitely-not-a-real-binary-xyz"]) == (1, "")


def test_run_out_returns_stdout_or_empty():
    assert c.run_out(["printf", "hi"]) == "hi"
    assert c.run_out(["definitely-not-a-real-binary-xyz"]) == ""


# --- output conventions: unparsed / provenance / undetermined -------------------

def test_unparsed_line_surfaces_the_raw_line():
    """A parser that can't read an in-scope line must SAY so. The alternative — returning
    a blank field — is how a cask's missing version became a confident 'major-bump'."""
    row = c.unparsed_line("elgato (1.8.1) != 1.9", "unrecognized format")
    assert row.startswith("unparsed\t")
    assert "elgato (1.8.1) != 1.9" in row
    assert "unrecognized format" in row


def test_fact_tags_provenance_only_when_given():
    assert c.fact("mise_activated", "yes") == "mise_activated\tyes"
    assert c.fact("mise_activated", "yes", src="login-shell") == (
        "mise_activated\tyes\tsrc=login-shell"
    )


def test_undetermined_is_distinct_from_a_clean_result():
    """'couldn't check' must not read as 'checked, all good' — they imply opposite actions."""
    row = c.undetermined("mise_activated", "no zsh to ask")
    assert "undetermined" in row
    assert "no zsh to ask" in row
    assert row != c.fact("mise_activated", "yes")
