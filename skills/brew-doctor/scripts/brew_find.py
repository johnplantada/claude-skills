#!/usr/bin/env python3
"""Read-only search + info + "best install" advisor. Part of the brew-doctor skill.

Given a NEED or a NAME, helps decide WHAT to install and HOW for your machine —
BEFORE setup.md installs it.

    brew_find.py <term>     # fuzzy: search formula + cask NAMES and DESCRIPTIONS
    brew_find.py <name>     # exact: a dossier on one formula/cask + a best-install call

The dossier layers brew-doctor JUDGMENT on top of `brew info`:
  - runtime (node/python/ruby/go…) -> prefer `mise` (runtime-versions skill), NOT brew
  - fragile (editors/LSPs/DBs, or [brew-doctor].pinned) -> pin on install
  - self-updating cask, no native arm64 bottle, versioned formulae available, cask-vs-formula
Read-only: runs only `brew search/info/desc/list` — never install/pin/upgrade/tap.
"""

from __future__ import annotations

import platform
import sys

import _brew_common as bc

# Runtimes belong to mise, not brew. Fragile = version-sensitive config breakers.
RUNTIME_SET = (
    "node nodejs python python3 ruby go golang rust deno bun php perl elixir erlang "
    "openjdk java kotlin scala dotnet"
).split()
FRAGILE_BUILTIN = (
    "neovim vim postgresql mongodb mysql redis lua-language-server gopls pyright "
    "rust-analyzer terraform"
).split()

USAGE = """brew_find.py — read-only search + info + "best install" advisor. Never mutates.

Given a NEED or a NAME, helps decide WHAT to install and HOW for your machine —
BEFORE setup.md installs it.
  brew_find.py <term>     # fuzzy: search formula + cask NAMES and DESCRIPTIONS
  brew_find.py <name>     # exact: a dossier on one formula/cask + a best-install call

The dossier layers brew-doctor JUDGMENT on top of `brew info`:
  - runtime (node/python/ruby/go…) -> prefer `mise` (runtime-versions skill), NOT brew
  - fragile (editors/LSPs/DBs, or [brew-doctor].pinned) -> pin on install
  - self-updating cask, no native arm64 bottle, versioned formulae available, cask-vs-formula"""


# --- pure helpers ------------------------------------------------------------

def lc(text: str) -> str:
    return text.lower()


def in_set(tokens: list[str], name: str) -> bool:
    """True when `name` equals any token (case-insensitive) — the old `in_set`."""
    target = lc(name)
    return any(lc(tok) == target for tok in tokens)


def sub_set(tokens: list[str], name: str) -> bool:
    """True when `name` contains any token as a substring (ci) — the old `sub_set`."""
    target = lc(name)
    return any(lc(tok) in target for tok in tokens)


def fragile_set(config_pinned: str) -> list[str]:
    """Built-in fragile keywords + runtimes + the config's pinned formulae."""
    return FRAGILE_BUILTIN + RUNTIME_SET + config_pinned.split()


def stem_of(arg: str) -> str:
    """`arg` without a trailing `@version` (the old `${ARG%@*}`)."""
    return arg.rsplit("@", 1)[0]


def build_search(term: str, name_matches: str, desc_matches: str) -> list[str]:
    """The fuzzy-search report lines for a term with no exact formula/cask."""
    out = [f"mode\tsearch\tterm={term}", "== name matches (brew search) =="]
    out.extend(name_matches.splitlines())
    out.append("")
    out.append("== description matches (brew search --desc) ==")
    out.extend(f"  {line}" for line in desc_matches.splitlines())
    out.append("")
    out.append("next: brew_find.py <name>   # dossier + best-install call on any candidate above")
    return out


def build_best_install(
    arg: str,
    stem: str,
    kind: str,
    is_runtime: bool,
    cask_auto_updates: bool,
    arch: str,
    has_arm64_bottle: bool,
    variants: str,
    arg_is_fragile: bool,
) -> list[str]:
    """The "best install for your situation" judgment block."""
    out = ["== best install for your situation =="]
    if is_runtime:
        out.append("⚠ runtime: prefer mise, NOT brew — brew auto-bumps runtimes and breaks configs.")
        out.append(
            f"  → runtime-versions skill:  mise use -g {stem}@<version>   "
            f"(per-project: mise use {stem}@<version>)"
        )

    if kind == "cask":
        if cask_auto_updates:
            out.append(
                "note: cask self-updates (auto_updates) — brew won't manage its version; "
                "that drift is expected."
            )
        out.append(f"install: brew install --cask {arg}")
        out.append(
            f"  (a sudo installer can't run headless — run it yourself: ! brew install --cask {arg})"
        )
    elif is_runtime:
        out.append(
            f"(brew has {stem}, but installing a runtime via brew is not recommended — use mise above.)"
        )
    else:
        if arch == "arm64" and not has_arm64_bottle:
            out.append(
                "note: no native arm64 bottle detected — may build from source (slow) or run via Rosetta."
            )
        if variants.replace(" ", ""):
            out.append(f"versioned formulae: {variants} (pin to a major to avoid surprise bumps)")
        if arg_is_fragile:
            out.append("⚠ fragile: version-sensitive — pin on install so it can't bump unattended:")
            out.append(f"  install: brew install {arg} && brew pin {arg}")
        else:
            out.append(f"install: brew install {arg}")
    return out


def _grep_lines(text: str, pattern: str, *, ignorecase: bool = False):
    import re

    flags = re.IGNORECASE if ignorecase else 0
    return [ln for ln in text.splitlines() if re.search(pattern, ln, flags)]


def build_dossier(
    arg: str,
    kind: str,
    desc: str,
    info: str,
    versions: str | None,
    also_cask: bool,
    best_install: list[str],
) -> list[str]:
    """The exact-name dossier: header, desc/info/status, install state, popularity,
    homepage, cask note, then the best-install block."""
    out = [f"mode\tdossier\tname={arg}\tkind={kind}"]
    out.extend(f"desc: {line}" for line in desc.splitlines())
    info_lines = info.splitlines()
    out.append(f"info: {info_lines[0] if info_lines else ''}")
    out.extend(f"status: {line}" for line in _grep_lines(info, r"deprecated|disabled!", ignorecase=True))

    if versions is not None:
        out.append(f"installed: {versions}")
    else:
        out.append("installed: no")

    pop = _grep_lines(info, r"install:.*day|install \(30", ignorecase=True)
    if pop:
        out.append(f"popularity: {pop[0]}")
    home = _grep_lines(info, r"https?://[^ ]+")
    if home:
        import re

        m = re.search(r"https?://[^ ]+", home[0])
        if m:
            out.append(f"home: {m.group(0)}")

    if kind == "formula" and also_cask:
        out.append("note: also ships as a cask — formula = CLI, cask = app; pick by how you'll use it.")

    out.extend(best_install)
    out.append("")
    out.append("after installing: refresh the Brewfile (setup.md) and re-check gates/pins (optimize.md).")
    return out


# --- main (I/O via _brew_common) ---------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    arg = args[0] if args else ""
    if not arg:
        print(USAGE)
        return 2
    if not bc.brew_available():
        print("brew-find: brew not on PATH", file=sys.stderr)
        return 3

    if bc.brew_ok("info", "--formula", arg):
        kind = "formula"
    elif bc.brew_ok("info", "--cask", arg):
        kind = "cask"
    else:
        kind = ""

    if not kind:
        name_matches = bc.brew("search", arg)
        desc_matches = bc.brew("search", "--desc", arg)
        print("\n".join(build_search(arg, name_matches, desc_matches)))
        return 0

    stem = stem_of(arg)
    info = bc.brew("info", f"--{kind}", arg)
    desc = bc.brew("desc", arg)
    versions = bc.brew("list", "--versions", arg).strip() if bc.brew_ok("list", "--versions", arg) else None
    also_cask = kind == "formula" and bc.brew_ok("info", "--cask", arg)

    is_runtime = in_set(RUNTIME_SET, stem)
    fragile = fragile_set(bc.config_array("brew-doctor", "pinned"))
    arg_is_fragile = sub_set(fragile, arg)
    cask_auto_updates = kind == "cask" and "auto_updates" in info.lower()
    arch = platform.machine() or "unknown"
    has_arm64_bottle = '"arm64' in bc.brew("info", "--json=v2", arg)
    variants_raw = bc.brew("search", "--formula", f"/^{stem}@/")
    variants = " ".join(variants_raw.split()) + (" " if variants_raw.split() else "")

    best_install = build_best_install(
        arg, stem, kind, is_runtime, cask_auto_updates, arch, has_arm64_bottle, variants, arg_is_fragile
    )
    print("\n".join(build_dossier(arg, kind, desc, info, versions, also_cask, best_install)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
