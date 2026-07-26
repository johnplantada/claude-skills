#!/usr/bin/env python3
"""detect_managers.py — find the version-manager sprawl. No arguments. READ-ONLY.

One `key<TAB>value` line per signal, stable order. Collapses the manager-hunt from
optimize.md and setup.md (capture) into one call.

For mise and each legacy manager (nvm asdf pyenv rbenv fnm) reports:
    <m>_present     yes/no, with the signal (binary-on-path | home-dir | rc-hook)
    <m>_home        its shim/home dir if present
    <m>_shell_hook  which rc file initializes it (the line shells actually run)
    <m>_global      best-effort global version it currently provides (for migration capture)
Plus:
    brew_runtimes   node/python/ruby/go installed via Homebrew (double-owned = sprawl)
    legacy_shims_on_path   legacy shim dirs sitting on THIS PATH (first one wins)

`<m>_global` is best-effort: binary managers are queried directly; nvm is a shell
function, so it's sourced in a subshell. Absent managers are skipped cleanly.
"""

from __future__ import annotations

import os
import re
import sys

import _runtime_common as rc

# Runtimes that count as sprawl when Homebrew also owns them.
_BREW_RUNTIME_RE = re.compile(r"^(node|python|ruby|go)(@|$)")
# Legacy shim-dir markers to flag when they sit on PATH.
_SHIM_RE = re.compile(r"\.nvm|\.pyenv|\.rbenv|\.asdf|fnm")

# name -> (home dir, rc-hook regex). The pattern matches the line a shell runs to init it.
LEGACY_MANAGERS = [
    ("nvm", rc.HOME / ".nvm", r"NVM_DIR|nvm\.sh|nvm/nvm\.sh"),
    ("asdf", rc.HOME / ".asdf", r"asdf\.sh|asdf\.fish|libexec/asdf"),
    ("pyenv", rc.HOME / ".pyenv", r"pyenv init|PYENV_ROOT"),
    ("rbenv", rc.HOME / ".rbenv", r"rbenv init|RBENV_ROOT"),
    ("fnm", rc.HOME / ".fnm", r"fnm env|fnm --"),
]


def file_has_active_hook(text: str, pattern: str) -> bool:
    """True if any *non-commented* line of `text` matches `pattern`.

    A neutralized hook (leading `#`, optionally indented) is not an active hook — so a
    commented-out `nvm.sh` source line must NOT be reported as present.
    """
    regex = re.compile(pattern)
    for line in text.splitlines():
        if re.match(r"^[ \t]*#", line):
            continue
        if regex.search(line):
            return True
    return False


def hook_for(rc_contents: list[tuple[str, str]], pattern: str) -> str:
    """Space-joined display paths of the rc files whose active lines match `pattern`.

    `rc_contents` is (display_path, text) pairs; only the display path is emitted, so a
    caller passes already-tilde-collapsed names.
    """
    hits = [display for display, text in rc_contents if file_has_active_hook(text, pattern)]
    return " ".join(hits)


def manager_lines(name: str, has_binary: bool, home: str, home_exists: bool, hook: str) -> list[str]:
    """Build the present/home/shell_hook lines for one legacy manager."""
    present = "no"
    signals: list[str] = []
    if has_binary:
        present = "yes"
        signals.append("binary-on-path")
    if home_exists:
        present = "yes"
        signals.append("home-dir")
    if hook:
        present = "yes"
        signals.append("rc-hook")
    signal = ",".join(signals)
    lines = [f"{name}_present\t{present}" + (f" ({signal})" if signal else "")]
    if home_exists:
        lines.append(f"{name}_home\t{home}")
    if hook:
        lines.append(f"{name}_shell_hook\t{hook}")
    return lines


def brew_runtimes(formula_output: str) -> str:
    """Node/python/ruby/go lines from `brew list --formula`, space-joined; else (none).

    Mirrors `grep -E '^(node|python|ruby|go)(@|$)' | tr '\\n' ' '` (trailing space kept).
    """
    joined = "".join(l + " " for l in formula_output.splitlines() if _BREW_RUNTIME_RE.match(l))
    return joined or "(none)"


def legacy_shims_on_path(path: str) -> str:
    """Numbered legacy shim entries on `path` (first wins); else (none).

    Mirrors `echo $PATH | tr ':' '\\n' | grep -nE '...' | tr '\\n' ' '` — each hit is
    `N:entry` with N the 1-based PATH position, and a trailing space is kept.
    """
    hits = [f"{i}:{entry}" for i, entry in enumerate(path.split(":"), 1) if _SHIM_RE.search(entry)]
    joined = "".join(h + " " for h in hits)
    return joined or "(none)"


def _read_rc_contents() -> list[tuple[str, str]]:
    """(tilde-path, text) for each existing rc file."""
    out: list[tuple[str, str]] = []
    for f in rc.RC_FILES:
        if f.is_file():
            out.append((rc.tilde(str(f)), rc.read_text(f)))
    return out


def _tr(text: str, sep: str) -> str:
    """Mimic `tr '\\n' sep` — replace every newline (incl. the trailing one)."""
    return text.replace("\n", sep)


def collect() -> list[str]:
    """Assemble every report line, running the read-only manager probes."""
    lines: list[str] = []
    rc_contents = _read_rc_contents()

    # mise (the target)
    if rc.have("mise"):
        ver = (rc.run(["mise", "--version"]).stdout.splitlines() or [""])[0]
        lines.append(f"mise_present\tyes ({ver})")
    else:
        lines.append("mise_present\tno")

    # legacy managers
    for name, home, hookpat in LEGACY_MANAGERS:
        hook = hook_for(rc_contents, hookpat)
        lines += manager_lines(
            name, rc.have(name), str(home), home.is_dir(), hook
        )

    # best-effort global version each present manager provides (migration capture)
    if rc.have("pyenv"):
        lines.append("pyenv_global\t" + _tr(rc.run(["pyenv", "global"]).stdout, " "))
    if rc.have("rbenv"):
        lines.append("rbenv_global\t" + _tr(rc.run(["rbenv", "global"]).stdout, " "))
    if rc.have("asdf"):
        lines.append("asdf_current\t" + _tr(rc.run(["asdf", "current"]).stdout, ";"))
    if rc.have("fnm"):
        lines.append("fnm_default\t" + rc.run(["fnm", "current"]).stdout.rstrip("\n"))
    nvm_default = rc.nvm_default_version()
    if nvm_default is not None:
        lines.append(f"nvm_default\t{nvm_default}")

    # runtimes ALSO installed via Homebrew (double-owned = the sprawl)
    formula = rc.run(["brew", "list", "--formula"]).stdout if rc.have("brew") else ""
    lines.append("brew_runtimes\t" + brew_runtimes(formula))

    # legacy shim dirs actually on THIS PATH (earliest wins)
    lines.append("legacy_shims_on_path\t" + legacy_shims_on_path(os.environ.get("PATH", "")))

    return lines


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    print("\n".join(collect()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
