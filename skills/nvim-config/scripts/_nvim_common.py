"""Shared subprocess/IO helpers for the nvim-config skill scripts. Stdlib only.

Every call that shells out to `nvim` or `git`, and every filesystem read, lives here
so the callers' logic stays as pure, directly-testable functions. A path/CLI change is
then a one-file edit. Named `_nvim_common` (unique) to avoid colliding with other
skills' `_common` helpers on the shared pytest sys.path.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.devenv_common import command_available, read_text  # noqa: E402


def nvim_available() -> bool:
    """True if `nvim` is on PATH."""
    return command_available("nvim")


def nvim_version_line() -> str:
    """First line of `nvim --version` (e.g. `NVIM v0.11.2`)."""
    try:
        proc = subprocess.run(["nvim", "--version"], capture_output=True, text=True)
    except OSError:
        return ""
    lines = proc.stdout.splitlines()
    return lines[0] if lines else ""


def nvim_write(lua: str, *, clean: bool = False) -> str:
    """Run `nvim --headless "+lua <lua>" +qa` and return its stdout verbatim.

    `lua` is expected to `io.write(...)` the value of interest (no trailing newline).
    """
    cmd = ["nvim", "--headless"]
    if clean:
        cmd.append("--clean")
    cmd += [f"+lua {lua}", "+qa"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except OSError:
        return ""
    return proc.stdout


def stdpath(name: str) -> str:
    """`vim.fn.stdpath('<name>')` — the resolved config/data/state directory."""
    return nvim_write(f"io.write(vim.fn.stdpath('{name}'))")


def clean_type(expr: str) -> str:
    """`type(<expr>)` evaluated in a clean (no-user-config) Neovim; '?' on failure.

    Used to tell whether a `vim.*` API still exists in core (a `nil` type means the
    symbol was removed and any caller of it breaks).
    """
    lua = (
        f"local ok,t=pcall(function() return type({expr}) end); "
        "io.write(ok and t or 'nil/error')"
    )
    out = nvim_write(lua, clean=True).strip()
    return out or "?"


def run_lazy_sync() -> str:
    """`nvim --headless +Lazy! sync +qa`, combined stdout+stderr."""
    try:
        proc = subprocess.run(
            ["nvim", "--headless", "+Lazy! sync", "+qa"], capture_output=True, text=True
        )
    except OSError:
        return ""
    return proc.stdout + proc.stderr


def run_checkhealth_deprecated() -> str:
    """Run `checkhealth vim.deprecated` and print its WARNING/ERROR buffer lines."""
    lua = (
        "for _,l in ipairs(vim.api.nvim_buf_get_lines(0,0,-1,false)) do "
        "if l:match('WARNING') or l:match('ERROR') then print(l) end end"
    )
    try:
        proc = subprocess.run(
            ["nvim", "--headless", "+checkhealth vim.deprecated", f"+lua {lua}", "+qa"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    return proc.stdout + proc.stderr


def make_scratch(ext: str, content: str) -> str:
    """Create a temp scratch file `<tmp>.<ext>` with `content`; return its path.

    Scratch files land in the system temp dir, never the user's project.
    """
    fd, base = tempfile.mkstemp(prefix="nvimchk.")
    os.close(fd)
    path = f"{base}.{ext}"
    os.rename(base, path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def remove(path: str) -> None:
    """Delete a scratch file, ignoring a missing file."""
    try:
        os.unlink(path)
    except OSError:
        pass


def walk_files(root: str) -> list[tuple[str, str]]:
    """(path, text) for every file under `root`, recursively (like `grep -r`)."""
    out: list[tuple[str, str]] = []
    for dirpath, _dirs, filenames in os.walk(root):
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            out.append((path, read_text(path)))
    return out


def read_spec_files(config: str) -> list[tuple[str, str]]:
    """(path, text) for `init.lua` then everything under `lua/` — the plugin specs.

    Mirrors `grep -rn ... "$CONFIG"/init.lua "$CONFIG"/lua`: init.lua first, then the
    modular tree.
    """
    files: list[tuple[str, str]] = []
    init = os.path.join(config, "init.lua")
    if os.path.isfile(init):
        files.append((init, read_text(init)))
    luadir = os.path.join(config, "lua")
    for dirpath, _dirs, filenames in os.walk(luadir):
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            files.append((path, read_text(path)))
    return files


def count_lua_files_containing(directory: str, symbol: str) -> int:
    """Count `*.lua` files under `directory` that mention `symbol` (`grep -rl`)."""
    count = 0
    for dirpath, _dirs, filenames in os.walk(directory):
        for name in filenames:
            if name.endswith(".lua") and symbol in read_text(os.path.join(dirpath, name)):
                count += 1
    return count


# --- git -----------------------------------------------------------------------

def git_is_repo(path: str) -> bool:
    """True if `path` is inside a git work tree."""
    try:
        proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def git_short_head(path: str) -> str | None:
    """Short HEAD commit for `path`, or None (e.g. a repo with no commits yet)."""
    try:
        proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    head = proc.stdout.strip()
    return head if proc.returncode == 0 and head else None


def git_fetch_tags(directory: str) -> None:
    """`git fetch --tags --quiet` (best-effort; errors ignored)."""
    try:
        subprocess.run(
            ["git", "-C", directory, "fetch", "--tags", "--quiet"], capture_output=True
        )
    except OSError:
        pass


def git_log1(directory: str) -> str:
    """Latest commit as `%h %ci %s`, or '?' when unavailable."""
    try:
        proc = subprocess.run(
            ["git", "-C", directory, "log", "-1", "--format=%h %ci %s"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return "?"
    out = proc.stdout.strip()
    return out if proc.returncode == 0 and out else "?"


def git_describe(directory: str) -> str:
    """`git describe --tags`, or '(untagged)' when it has no reachable tag."""
    try:
        proc = subprocess.run(
            ["git", "-C", directory, "describe", "--tags"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return "(untagged)"
    out = proc.stdout.strip()
    return out if proc.returncode == 0 and out else "(untagged)"


def git_tags(directory: str) -> list[str]:
    """All tags, newest-created first (`git tag --sort=-creatordate`)."""
    try:
        proc = subprocess.run(
            ["git", "-C", directory, "tag", "--sort=-creatordate"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    return [t for t in proc.stdout.splitlines() if t.strip()]


def git_grep_count(directory: str, symbol: str, ref: str) -> int:
    """Count `*.lua` files at `ref` mentioning `symbol` (`git grep -l ... -- '*.lua'`)."""
    try:
        proc = subprocess.run(
            ["git", "-C", directory, "grep", "-l", symbol, ref, "--", "*.lua"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return 0
    if proc.returncode != 0:
        return 0
    return len([line for line in proc.stdout.splitlines() if line.strip()])
