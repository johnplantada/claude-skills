"""Tests for the dotfiles `chezmoi_status` script — pure functions only, no chezmoi/git."""

import chezmoi_status as cs


# --- count_nonblank_lines (grep -c .) ------------------------------------------

def test_count_nonblank_lines_ignores_empty_lines():
    assert cs.count_nonblank_lines("a\n\nb\n") == 2


def test_count_nonblank_lines_empty_text_is_zero():
    assert cs.count_nonblank_lines("") == 0


def test_count_nonblank_lines_counts_whitespace_only_line():
    # `grep -c .` counts a line containing a space (a space matches `.`).
    assert cs.count_nonblank_lines(" \nx\n") == 2


# --- count_diff_blocks (grep -cE '^diff ') -------------------------------------

def test_count_diff_blocks_counts_only_diff_headers():
    text = "diff a\n index 1\ndiff b\n+added\n"
    assert cs.count_diff_blocks(text) == 2


def test_count_diff_blocks_requires_leading_diff_space():
    assert cs.count_diff_blocks("mydiff x\ndiffx\n") == 0


# --- worktree_state ------------------------------------------------------------

def test_worktree_state_clean_on_empty_porcelain():
    assert cs.worktree_state("") == "clean"


def test_worktree_state_dirty_when_changes_present():
    assert cs.worktree_state(" M dot_zshrc\n") == "dirty (uncommitted changes in source)"


# --- parse_doctor --------------------------------------------------------------

def test_parse_doctor_counts_by_result_and_skips_header():
    text = (
        "RESULT    CHECK        MESSAGE\n"
        "ok        version      v2.71.1\n"
        "info      optional     not found\n"
        "warning   age-command  age not in PATH\n"
        "error     config       broken\n"
    )
    counts, issues = cs.parse_doctor(text)
    assert counts == {"ok": 1, "info": 1, "warning": 1, "error": 1}
    # Only warning/error rows surface, whitespace-normalized, prefixed with the tab key.
    assert issues == [
        "doctor_issue\twarning age-command age not in PATH",
        "doctor_issue\terror config broken",
    ]


def test_parse_doctor_normalizes_runs_of_whitespace_in_issue_rows():
    text = "RESULT CHECK MSG\nwarning   foo     multi   space   msg\n"
    _, issues = cs.parse_doctor(text)
    assert issues == ["doctor_issue\twarning foo multi space msg"]


def test_parse_doctor_empty_output_is_all_zero():
    counts, issues = cs.parse_doctor("")
    assert counts == {"ok": 0, "info": 0, "warning": 0, "error": 0}
    assert issues == []


# --- collect(): end-to-end wiring with the IO layer stubbed --------------------

def test_collect_reports_not_installed(monkeypatch):
    monkeypatch.setattr(cs.dc, "chezmoi_available", lambda: False)
    lines = cs.collect()
    assert lines == [
        "chezmoi_installed\tno",
        "hint\tinstall with: brew install chezmoi",
    ]


def test_collect_reports_uninitialized(monkeypatch):
    monkeypatch.setattr(cs.dc, "chezmoi_available", lambda: True)
    monkeypatch.setattr(cs.dc, "chezmoi_version", lambda: "chezmoi v2.71.1")
    monkeypatch.setattr(cs.dc, "chezmoi_source_path", lambda: "/tmp/src")
    monkeypatch.setattr(cs.dc, "is_git_repo", lambda s: False)
    lines = cs.collect()
    assert lines == [
        "chezmoi_installed\tyes",
        "chezmoi_version\tchezmoi v2.71.1",
        "source_dir\t/tmp/src",
        "initialized\tno",
        "hint\tnot initialized — this is an `init` job (see reference/init.md)",
    ]


def test_collect_full_initialized_report(monkeypatch, tmp_path):
    src = tmp_path / "src"
    (src / ".git").mkdir(parents=True)
    (src / ".chezmoiignore").write_text("README.md\n")
    (src / "dot_zshrc.tmpl").write_text("export X=1\n")

    monkeypatch.setattr(cs.dc, "chezmoi_available", lambda: True)
    monkeypatch.setattr(cs.dc, "chezmoi_version", lambda: "v2")
    monkeypatch.setattr(cs.dc, "chezmoi_source_path", lambda: str(src))
    monkeypatch.setattr(cs.dc, "git_porcelain", lambda s: " M dot_zshrc\n")
    monkeypatch.setattr(cs.dc, "git_head_short", lambda s: "abc1234")
    monkeypatch.setattr(cs.dc, "git_remote_url", lambda s: "git@example.com:me/dotfiles.git")
    monkeypatch.setattr(cs.dc, "chezmoi_managed", lambda inc: "a\nb\n" if inc == "files" else "d1\n")
    monkeypatch.setattr(cs.dc, "chezmoi_status", lambda: " M dot_zshrc\n")
    monkeypatch.setattr(cs.dc, "chezmoi_diff", lambda: "diff dot_zshrc\n+x\n")
    monkeypatch.setattr(cs.dc, "chezmoi_doctor", lambda: "RESULT CHECK MSG\nok v ok\n")

    lines = cs.collect()
    assert "initialized\tyes" in lines
    assert "source_worktree\tdirty (uncommitted changes in source)" in lines
    assert "source_head\tabc1234" in lines
    assert "source_remote\tgit@example.com:me/dotfiles.git" in lines
    assert "managed_files\t2" in lines
    assert "managed_dirs\t1" in lines
    assert "templates\t1" in lines
    assert "chezmoiignore\tpresent" in lines
    assert "status_drift\t1\t(0 = in sync)" in lines
    assert "diff_pending\t1\t(files apply would change)" in lines
    assert "doctor\tok=1 info=0 warning=0 error=0" in lines


def test_collect_uses_default_remote_string_when_no_remote(monkeypatch, tmp_path):
    src = tmp_path / "src"
    (src / ".git").mkdir(parents=True)
    monkeypatch.setattr(cs.dc, "chezmoi_available", lambda: True)
    monkeypatch.setattr(cs.dc, "chezmoi_version", lambda: "v2")
    monkeypatch.setattr(cs.dc, "chezmoi_source_path", lambda: str(src))
    monkeypatch.setattr(cs.dc, "git_porcelain", lambda s: "")
    monkeypatch.setattr(cs.dc, "git_head_short", lambda s: "no commits yet")
    monkeypatch.setattr(cs.dc, "git_remote_url", lambda s: "")
    monkeypatch.setattr(cs.dc, "chezmoi_managed", lambda inc: "")
    monkeypatch.setattr(cs.dc, "chezmoi_status", lambda: "")
    monkeypatch.setattr(cs.dc, "chezmoi_diff", lambda: "")
    monkeypatch.setattr(cs.dc, "chezmoi_doctor", lambda: "")
    lines = cs.collect()
    assert "source_remote\t(none — no remote; changes stay local)" in lines
    assert "source_worktree\tclean" in lines
    assert "status_drift\t0\t(0 = in sync)" in lines
