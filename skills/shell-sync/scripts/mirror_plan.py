#!/usr/bin/env python3
"""Emit the PROPOSED managed mirror file to STDOUT — a plan you review, then save
yourself. NEVER writes any config file. Part of the shell-sync skill.

Only the documented common case is auto-generated: canonical=zsh -> mirror=fish
(defaults). It reads zsh's resolved PATH + user-set exports + simple aliases and
prints a ``~/.config/fish/conf.d/00-shell-sync.fish`` body between AUTO-GENERATED
markers. Functions and non-trivial aliases are NOT translated — they are listed
as TODO comments for manual porting (see reference/translation.md).

Usage:
    mirror_plan.py [canonical] [mirror]

    mirror_plan.py                       # zsh -> fish plan to stdout
    mirror_plan.py > /tmp/plan.fish      # capture, review, then install by hand
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import sys
from pathlib import Path

import _shell_common as sc
import dump_env

# Vars we must NOT mirror — only user-set vars should cross to fish. Three classes:
#   1. shell/session/system (PWD, TERM, SSH_*, __CF*, …)
#   2. tool-injected by the canonical shell's rc (HOMEBREW_* from `brew shellenv`,
#      MISE_*/__MISE_* from `mise activate zsh`, STARSHIP_* from `starship init zsh`).
#      These are zsh-activation STATE — mirroring `MISE_SHELL=zsh` or `STARSHIP_SHELL=zsh`
#      into fish is actively wrong; fish's own init sets its correct values (and
#      STARSHIP_SESSION_KEY is a per-session random key that must never be pinned).
#   3. path-like vars fish rebuilds on its own (PATH handled below; MANPATH/INFOPATH).
DENY = (
    r"^(PWD|OLDPWD|SHLVL|_|TERM|TERM_PROGRAM|TERM_SESSION_ID|PS1|PROMPT|SHELL|LOGNAME|USER"
    r"|HOME|TMPDIR|PATH|FPATH|MANPATH|INFOPATH|LANG|LC_[A-Z]+|DISPLAY|COLORTERM|SSH_[A-Z]+"
    r"|ITERM.*|__CF.*|XPC_.*|SECURITYSESSIONID|COMMAND_MODE|Apple_PubSub_Socket_Render"
    r"|fish_greeting|HOMEBREW_[A-Z]+|MISE_[A-Z0-9_]+|__MISE[A-Z0-9_]*|STARSHIP_[A-Z_]+)="
)
DENY_RE = re.compile(DENY)

# zsh predefines default aliases (run-help, which-command) that are shell builtins,
# not user config — skip them so they don't leak into the mirror.
ALIAS_DENY_RE = re.compile(r"run-help|which-command")


# --- pure logic ----------------------------------------------------------------

def fish_quote(value: str) -> str:
    """Render VALUE as a fish single-quoted literal — a VALID ``set -gx``/``alias`` value.

    Inside fish single quotes only two characters are special: the backslash and the
    single quote itself, each escaped with a backslash. Escaping backslash first (then
    the quote) is required so a value like ``O'Brien`` or one containing a literal
    backslash produces a well-formed line instead of a broken/half-quoted one.
    """
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def strip_wrapping_quotes(val: str) -> str:
    """Strip one layer of surrounding single- then double-quotes (as zsh prints them)."""
    val = val.removeprefix("'")
    val = val.removesuffix("'")
    val = val.removeprefix('"')
    val = val.removesuffix('"')
    return val


def env_lines(export_lines: list[str]) -> list[str]:
    """User-set exports (denylist applied) as fish ``set -gx NAME 'value'`` lines."""
    out: list[str] = []
    for line in export_lines:
        if not line or DENY_RE.search(line):
            continue
        name, _, val = line.partition("=")
        out.append(f"set -gx {name} {fish_quote(val)}")
    return out


def alias_lines(alias_raw: list[str]) -> list[str]:
    """Simple aliases as fish ``alias name 'value'``; ones using shell expansion
    (``$``/backtick/brace) are emitted as ``# TODO port`` comments instead."""
    out: list[str] = []
    for line in alias_raw:
        if not line:
            continue
        name, _, val = line.partition("=")
        if ALIAS_DENY_RE.fullmatch(name):
            continue
        val = strip_wrapping_quotes(val)
        if any(ch in val for ch in ("$", "`", "{")):
            out.append(f"# TODO port alias (uses shell expansion): {name}={val}")
        else:
            out.append(f"alias {name} {fish_quote(val)}")
    return out


def config_has_starship_init(text: str) -> bool:
    """True if an (uncommented) ``starship init fish`` line is already in config.fish."""
    pat = re.compile(r"^[^#]*starship init fish")
    return any(pat.search(line) for line in text.splitlines())


def starship_block(has_starship: bool, config_has_init: bool) -> list[str]:
    """The `# --- prompt ---` body: mirror starship's per-shell init, or explain why not."""
    if not has_starship:
        return [
            "# no starship on PATH — prompt not mirrored. shell-sync mirrors starship's per-shell init",
            "# line only; a hand-written zsh prompt (PROMPT/PS1) must be ported to fish by hand.",
        ]
    if config_has_init:
        return ["# starship already initialized in config.fish — not duplicated here."]
    return [
        "# starship: cross-shell prompt. Config is the single shell-agnostic ~/.config/starship.toml",
        "# (track it via the dotfiles skill); only the per-shell init line is mirrored here.",
        "starship init fish | source",
    ]


def build_plan(
    date: str,
    path_entries: list[str],
    export_lines: list[str],
    alias_raw: list[str],
    has_starship: bool,
    config_has_init: bool,
) -> list[str]:
    """Assemble the full managed-file body between the AUTO-GENERATED markers."""
    lines: list[str] = [
        "# >>> shell-sync (AUTO-GENERATED) >>>",
        "# Mirrors zsh -> fish. Do NOT edit; edit your zsh config and re-generate with mirror_plan.py.",
        f"# Generated {date}. Review before installing to ~/.config/fish/conf.d/00-shell-sync.fish.",
        "",
        "# PATH — resolved zsh login PATH: deduped, dead/transient (system) entries dropped.",
        f"set -gx PATH {' '.join(path_entries)}",
        "",
        "# --- env ---",
    ]
    lines += env_lines(export_lines)
    lines += ["", "# --- aliases ---"]
    lines += alias_lines(alias_raw)
    lines += ["", "# --- prompt ---"]
    lines += starship_block(has_starship, config_has_init)
    lines += ["", "# --- functions ---"]
    lines += [
        "# NOT auto-translated (zsh and fish bodies are incompatible). Port any user",
        "# functions by hand into ~/.config/fish/functions/<name>.fish — see reference/translation.md.",
        "# <<< shell-sync (AUTO-GENERATED) <<<",
    ]
    return lines


# --- IO ------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    canon = args[0] if args else "zsh"
    mirror = args[1] if len(args) > 1 else "fish"
    if canon != "zsh" or mirror != "fish":
        print(
            f"mirror-plan: only zsh->fish is auto-generated; do {canon}->{mirror} by hand "
            "(see reference/translation.md)",
            file=sys.stderr,
        )
        return 2

    binary = sc.resolve_bin("zsh")
    if not binary:
        print("mirror-plan: zsh not installed — skipping", file=sys.stderr)
        return 3

    path_entries = sc.dedupe_existing(dump_env.resolve_section("zsh", "path", binary))
    exports = dump_env.resolve_section("zsh", "exports", binary)
    aliases = dump_env.resolve_section("zsh", "aliases", binary)

    has_starship = shutil.which("starship") is not None
    config_fish = Path(os.environ.get("HOME", "")) / ".config" / "fish" / "config.fish"
    config_has_init = config_has_starship_init(sc.read_text(config_fish))

    date = datetime.date.today().strftime("%Y-%m-%d")
    print("\n".join(build_plan(date, path_entries, exports, aliases, has_starship, config_has_init)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
