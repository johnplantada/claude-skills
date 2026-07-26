#!/usr/bin/env python3
"""runtime_find.py — read-only "which runtime / version / scope" advisor. Never mutates.

Given a TOOL, helps decide what to install and how — BEFORE setup/upgrade installs it.
    runtime_find.py <tool> [tool …]   # default: node python go ruby

Per tool: is it mise-managed? recent installable versions (+ @lts where it applies); what
resolves NOW and who owns it (mise/homebrew/legacy/system); and a flag if brew or an old
manager already provides it (→ consolidate via setup.md — install runtimes via mise, not brew).
Read-only: runs only `mise registry/ls-remote`, `command -v`, `brew list`. Never installs.
"""

from __future__ import annotations

import re
import sys

import _runtime_common as rc

# Languages mise exposes an @lts alias for.
LTS_LANGS = {"node"}
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def owner_of(path: str) -> str:
    """Classify what a `command -v` result belongs to: mise/legacy/homebrew/system/(none)."""
    if not path:
        return "(none)"
    if "mise" in path or "/shims/" in path:
        return "mise"
    if any(m in path for m in ("/.nvm/", "/.pyenv/", "/.rbenv/", "/.asdf/", "fnm")):
        return "legacy"
    if path.startswith("/opt/homebrew/") or path.startswith("/usr/local/"):
        return "homebrew"
    return "system"


def recent_versions(ls_remote_output: str) -> str:
    """Last 5 plain `X.Y.Z` versions from `mise ls-remote`, space-joined (trailing space).

    Empty when nothing matches, so the caller can fall back to a hint. Mirrors
    `grep -E '^[0-9]+\\.[0-9]+\\.[0-9]+$' | tail -5 | tr '\\n' ' '`.
    """
    versions = [l for l in ls_remote_output.splitlines() if _SEMVER_RE.match(l)]
    return "".join(v + " " for v in versions[-5:])


def is_lts_lang(tool: str) -> bool:
    """True for languages mise offers an `@lts` alias for."""
    return tool in LTS_LANGS


def brew_has(tool: str) -> bool:
    """Is a matching runtime installed via Homebrew? (`brew list --formula` scan)."""
    if not rc.have("brew"):
        return False
    formula = rc.run(["brew", "list", "--formula"]).stdout
    pat = re.compile(rf"^{re.escape(tool)}(@|$)")
    return any(pat.match(l) for l in formula.splitlines())


def tool_lines(tool: str, have_mise: bool) -> list[str]:
    """Every output line for one tool (header, mise info, resolution, recommendations)."""
    lines = [f"== {tool} =="]

    if have_mise:
        if rc.run(["mise", "ls-remote", tool]).returncode == 0:
            lines.append("mise_managed\tyes")
            rec = recent_versions(rc.run(["mise", "ls-remote", tool]).stdout)
            lines.append("recent_versions\t" + (rec or f"(see: mise ls-remote '{tool}')"))
            if is_lts_lang(tool):
                lines.append(f"lts_alias\t{tool}@lts (recommended default)")
        else:
            lines.append(f"mise_managed\tunknown — check: mise registry | grep {tool}")

    cur = rc.command_v(tool)
    lines.append(f"resolves_now\t{cur or '(not found)'}\towner={owner_of(cur)}")

    if brew_has(tool):
        lines.append("⚠ also provided by Homebrew — don't stack sources. Install runtimes via mise, not brew")
        lines.append("  (brew auto-bumps and breaks pins); consolidate via setup.md.")

    if is_lts_lang(tool):
        lines.append(f"recommend: {tool}@lts globally (mise use -g {tool}@lts), or pin a major per project.")
    else:
        lines.append(
            "recommend: pin a major globally (mise use -g "
            f"{tool}@<major>) — patches yes, surprise majors no; @latest only for throwaway/CI."
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    tools = args or ["node", "python", "go", "ruby"]
    have_mise = rc.have("mise")
    if not have_mise:
        print("mise: NOT installed — stand it up first (setup.md); showing current resolution only.")

    for tool in tools:
        for line in tool_lines(tool, have_mise):
            print(line)

    print()
    print("decide version+scope in find.md; install via upgrade.md (mise owns runtimes) or setup.md (stand mise up).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
