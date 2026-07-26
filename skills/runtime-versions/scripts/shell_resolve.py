#!/usr/bin/env python3
"""shell_resolve.py [zsh|fish|both] [tool ...] — clean-env per-shell resolution.

THE real test: which binary/version each runtime resolves to in a FRESH login shell,
launched from an EMPTY environment (`env -i`, keeping only HOME/TERM) so it resolves
exactly as a new login would — NOT polluted by the current session's PATH (a nested
shell inherits it and falsely shows mise winning). This is the per-shell truth
tool_resolve.py cannot give. Collapses optimize.md §4 + verification.md ("the real
test" + idempotency count).

    shell_resolve.py              # both shells, tools: node python go
    shell_resolve.py zsh          # zsh only
    shell_resolve.py fish ruby node

Per shell, per tool prints:  <shell>:<tool>  <command -v>  <version>
Plus  <shell>:mise_shims_on_path  N  (expect exactly 1; 2+ = activation runs twice).
A shell not installed is reported and skipped. READ-ONLY (runs login rc as-is).
"""

from __future__ import annotations

import sys

import _runtime_common as rc


def parse_args(argv: list[str]) -> tuple[str, list[str]]:
    """(which-shells, tools). Leading zsh|fish|both selects the shell; rest are tools."""
    which = "both"
    args = list(argv)
    if args and args[0] in ("zsh", "fish", "both"):
        which = args[0]
        args = args[1:]
    tools = args or ["node", "python", "go"]
    return which, tools


_ZSH_SCRIPT = """
    for t in {tools}; do
      loc="$(command -v $t 2>/dev/null)"
      if [ -n "$loc" ]; then
        printf "zsh:%-7s %s  %s\\n" "$t" "$loc" "$("$loc" --version 2>/dev/null | head -1)"
      else
        printf "zsh:%-7s %s\\n" "$t" MISSING
      fi
    done
    printf "zsh:mise_shims_on_path  %s\\n" "$(echo $PATH | tr ":" "\\n" | grep -c "mise.*shims" || true)"
"""

_FISH_SCRIPT = """
    for t in {tools}
      set -l loc (command -v $t 2>/dev/null)
      if test -n "$loc"
        printf "fish:%-7s %s  %s\\n" $t $loc ($loc --version 2>/dev/null | head -1)
      else
        printf "fish:%-7s %s\\n" $t MISSING
      end
    end
    printf "fish:mise_shims_on_path  %s\\n" (echo $PATH | tr " " "\\n" | grep -c "mise.*shims")
"""


def _emit(proc, fallback: str) -> None:
    """Print the login shell's stdout, then a fallback line if it exited non-zero."""
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        print(fallback)


def run_zsh(tools: list[str]) -> None:
    """Resolve `tools` in a clean-env zsh login shell, or report zsh missing."""
    zbin = rc.command_v("zsh")
    if not zbin:
        print("zsh: (not installed)")
        return
    script = _ZSH_SCRIPT.format(tools=" ".join(tools))
    proc = rc.login_shell_resolve(zbin, ["-l", "-i"], script)
    _emit(proc, "zsh: (login shell exited non-zero — inspect ~/.zshrc)")


def run_fish(tools: list[str]) -> None:
    """Resolve `tools` in a clean-env fish login shell, or report fish missing."""
    fbin = rc.command_v("fish")
    if not fbin:
        print("fish: (not installed)")
        return
    script = _FISH_SCRIPT.format(tools=" ".join(tools))
    proc = rc.login_shell_resolve(fbin, ["-l"], script)
    _emit(proc, "fish: (login shell exited non-zero — inspect config.fish)")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    which, tools = parse_args(args)
    print("-- clean-env (env -i) login resolution; compare shells: same path+version = consistent --")
    if which == "zsh":
        run_zsh(tools)
    elif which == "fish":
        run_fish(tools)
    else:
        run_zsh(tools)
        run_fish(tools)
    return 0


if __name__ == "__main__":
    sys.exit(main())
