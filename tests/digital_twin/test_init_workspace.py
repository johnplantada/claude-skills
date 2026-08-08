"""Deterministic workspace-initialization safety tests."""

import json
import os
import stat
from pathlib import Path

import init_workspace as iw
from _bundle_common import EMPTY_FILES, TEMPLATE_FILES, WORKSPACE_DIRECTORIES


def test_initializes_exact_private_skeleton_outside_git(tmp_path: Path):
    destination = tmp_path / "private-twin"
    assert iw.main([str(destination)]) == 0

    expected = set(WORKSPACE_DIRECTORIES) | set(TEMPLATE_FILES) | set(EMPTY_FILES)
    actual = {str(path.relative_to(destination)) for path in destination.rglob("*")}
    assert actual == expected
    for relative in TEMPLATE_FILES:
        assert isinstance(json.loads((destination / relative).read_text()), dict)

    if os.name != "nt":
        assert stat.S_IMODE(destination.stat().st_mode) == 0o700
        assert all(stat.S_IMODE((destination / item).stat().st_mode) == 0o700 for item in WORKSPACE_DIRECTORIES)
        assert all(
            stat.S_IMODE((destination / item).stat().st_mode) == 0o600 for item in (*TEMPLATE_FILES, *EMPTY_FILES)
        )


def test_pristine_second_invocation_is_noop(tmp_path: Path):
    destination = tmp_path / "private-twin"
    assert iw.main([str(destination)]) == 0
    mtimes = {str(path.relative_to(destination)): path.stat().st_mtime_ns for path in destination.rglob("*")}
    assert iw.main([str(destination)]) == 0
    assert mtimes == {str(path.relative_to(destination)): path.stat().st_mtime_ns for path in destination.rglob("*")}


def test_refuses_nonempty_destination_without_mutation(tmp_path: Path):
    destination = tmp_path / "occupied"
    destination.mkdir()
    marker = destination / "owner-file.txt"
    marker.write_text("synthetic owner marker")

    assert iw.main([str(destination)]) == 2
    assert marker.read_text() == "synthetic owner marker"
    assert list(destination.iterdir()) == [marker]


def test_refuses_partial_initializer_state(tmp_path: Path):
    destination = tmp_path / "partial"
    (destination / "sources").mkdir(parents=True)
    assert iw.main([str(destination)]) == 2
    assert sorted(str(path.relative_to(destination)) for path in destination.rglob("*")) == ["sources"]


def test_refuses_git_worktree_by_marker_and_allows_explicit_override(tmp_path: Path):
    repository = tmp_path / "repo"
    (repository / ".git").mkdir(parents=True)
    destination = repository / "private-twin"

    assert iw.main([str(destination)]) == 2
    assert not destination.exists()
    assert iw.main([str(destination), "--allow-git-worktree"]) == 0
    assert (destination / "sources" / "source-manifest.json").is_file()


def test_refuses_git_worktree_file_marker(tmp_path: Path):
    repository = tmp_path / "linked-worktree"
    repository.mkdir()
    (repository / ".git").write_text("gitdir: /synthetic/not-read")
    destination = repository / "private-twin"
    assert iw.main([str(destination)]) == 2
    assert not destination.exists()


def test_refuses_final_component_symlink(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "workspace-link"
    link.symlink_to(target, target_is_directory=True)
    assert iw.main([str(link)]) == 2
    assert list(target.iterdir()) == []
