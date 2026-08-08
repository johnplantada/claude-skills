#!/usr/bin/env python3
"""Initialize an empty, private professional digital-twin workspace.

The destination is always explicit. The initializer copies no owner sources, refuses non-empty and
git-worktree destinations by default, and uses restrictive permissions where supported.

Exit codes: 0 = initialized/pristine no-op, 1 = filesystem failure, 2 = usage/safety refusal.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from _bundle_common import (
    WORKSPACE_DIRECTORIES,
    chmod_private,
    expected_file_text,
)


def destination_path(raw: str) -> Path:
    """Return an absolute owner-selected destination without requiring it to exist."""
    return Path(os.path.abspath(os.path.expanduser(raw)))


def nearest_existing_ancestor(path: Path) -> Path:
    """Find the nearest existing directory at or above path without enumerating siblings."""
    current = path if path.exists() and path.is_dir() else path.parent
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def git_worktree_root(path: Path) -> Path | None:
    """Return a containing git worktree root using marker ancestry and git when available."""
    resolved = path.resolve(strict=False)
    probe = resolved if resolved.exists() and resolved.is_dir() else resolved.parent
    for ancestor in (probe, *probe.parents):
        if (ancestor / ".git").exists():
            return ancestor

    existing = nearest_existing_ancestor(resolved)
    try:
        proc = subprocess.run(
            ["git", "-C", str(existing), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    output = proc.stdout.strip()
    return Path(output) if output else None


def pristine_workspace(path: Path) -> bool:
    """Whether an existing destination is the exact untouched generated skeleton."""
    if not path.is_dir():
        return False
    expected_files = expected_file_text()
    expected_paths = set(WORKSPACE_DIRECTORIES) | set(expected_files)
    actual_paths = {str(item.relative_to(path)) for item in path.rglob("*")}
    if actual_paths != expected_paths:
        return False
    return all((path / relative).read_text(encoding="utf-8") == text for relative, text in expected_files.items())


def destination_problem(path: Path) -> str | None:
    """Return a fixed safety-refusal reason, or None when initialization is safe."""
    if path.is_symlink():
        return "destination is a symbolic link"
    if path.exists() and not path.is_dir():
        return "destination exists and is not a directory"
    if not path.exists():
        return None
    if pristine_workspace(path):
        return None
    try:
        next(path.iterdir())
    except StopIteration:
        return None
    return "destination is non-empty or partially initialized"


def create_workspace(path: Path) -> None:
    """Create the documented skeleton after all safety checks have passed."""
    files = expected_file_text()
    old_umask = os.umask(0o077)
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        chmod_private(path, 0o700)
        for relative in WORKSPACE_DIRECTORIES:
            directory = path / relative
            directory.mkdir(mode=0o700, exist_ok=True)
            chmod_private(directory, 0o700)
        for relative, text in files.items():
            target = path / relative
            with target.open("x", encoding="utf-8") as handle:
                handle.write(text)
            chmod_private(target, 0o600)
    finally:
        os.umask(old_umask)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an empty private digital-twin workspace; never copies owner sources."
    )
    parser.add_argument("destination", help="explicit owner-selected workspace path")
    parser.add_argument(
        "--allow-git-worktree",
        action="store_true",
        help="allow the destination inside a git worktree after an informed owner override",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = destination_path(args.destination)

    problem = destination_problem(path)
    if problem:
        print(f"refused\t{problem}\t{path}", file=sys.stderr)
        return 2

    worktree = git_worktree_root(path)
    if worktree and not args.allow_git_worktree:
        print(
            f"refused\tdestination is inside a git worktree\t{path}\n"
            "choose a private path outside source repositories, or use --allow-git-worktree "
            "only after an informed owner decision",
            file=sys.stderr,
        )
        return 2
    if worktree:
        print(
            "warning\towner override permits sensitive generated material inside a git worktree",
            file=sys.stderr,
        )

    if path.exists() and pristine_workspace(path):
        print(f"ready\tpristine workspace already exists\t{path}")
        return 0

    try:
        create_workspace(path)
    except OSError as exc:
        print(f"error\tworkspace initialization failed\t{type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"initialized\tprivate empty workspace\t{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
