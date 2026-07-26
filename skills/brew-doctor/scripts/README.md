# brew-doctor scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the
same `brew leaves/list/outdated/tap/info` + launchd-grep + Brewfile-diff pipelines from
scratch each time. Fewer tokens, no re-derivation, no footguns (e.g. mis-reading a launchd
agent that only runs `brew update` as if it upgraded). These are the source of truth for the
mechanical commands; the reference `.md` files carry the judgment.

Run them by absolute path from the skill directory. They resolve state internally — the
Brewfile path and the fragile/pinned set come from `~/.config/devenv/config.toml`
(`[brew-doctor]`) when present, so you don't hardcode them.

| Script | Purpose | Example |
|---|---|---|
| `brew_find.py <term\|name>` | **Read-only** search + best-install advisor. A fuzzy `<term>` searches formula/cask names + descriptions; an exact `<name>` prints a dossier (desc, version, popularity, deprecation, arch bottle, versioned variants) **plus a best-install call** — flagging runtime→`mise`, fragile→pin, self-updating cask, cask-vs-formula. Runs only `brew search/info/desc/list`. | `brew_find.py json` · `brew_find.py neovim` |
| `brew_audit.py [section]` | **Read-only** health & risk report: env, inventory (leaves/casks/taps), pins vs. config, **auto-upgrade mechanism detection with mode** (`brew upgrade`=hazard vs `brew update`=safe), outdated, orphans, self-updating casks, `brew doctor`. Section = `env`\|`inventory`\|`pins`\|`autoupdate`\|`cruft`. **Run first.** | `brew_audit.py` · `brew_audit.py autoupdate` |
| `brewfile_status.py [--file PATH]` | **Read-only** Brewfile drift: `bundle check` gaps + two-way membership diff (`only_in_brewfile` = would install, `only_installed` = would prune). Path from `--file` > config > `~/Brewfile`. | `brewfile_status.py` |
| `upgrade_plan.py` | **Read-only, PLAN-ONLY.** Snapshots versions, classifies each outdated formula (already-pinned→gated, fragile/major→pin-first, else safe), and **prints the gated command sequence** — never runs `brew update/upgrade/pin/cleanup`. | `upgrade_plan.py` |

All four are **read-only inspectors** — safe to re-run. `upgrade_plan.py` *plans* mutations
but never performs them, and `brew_find.py` only searches/inspects; you review the printed
commands and run them yourself after confirming.

## Worked example — the audit-to-gated-upgrade path in three calls

```
brew_audit.py autoupdate    # autoupdate_tap=domt4/autoupdate; launchd mode=update-only (safe)
                            #   → a mechanism exists but only runs `brew update` — not the hazard
upgrade_plan.py             # neovim 0.11→0.12 flagged fragile+UNPINNED → plan proposes `brew pin neovim` first
brewfile_status.py          # bundle_check GAPS: ollama needs update; only_installed=0 → Brewfile is honest
```
`brew_audit.py` decides whether the auto-updater is actually dangerous (mode, not mere
presence). `upgrade_plan.py` gates the fragile bump behind a pin before proposing the upgrade.
Run the printed `brew pin …` / `brew upgrade …`, then re-run `brew_audit.py` to confirm the pin
took and nothing surprising moved.

## Conventions for adding scripts

- Python 3.9+, **stdlib only**; start with `from __future__ import annotations`, a `#!/usr/bin/env python3`
  shebang, and `chmod +x`. Keep pure parsing/analysis/formatting in module functions and isolate the
  `brew`/launchd/cron subprocess + filesystem calls in `_brew_common.py` so the logic stays testable.
- End with `def main(argv=None) -> int` guarded by `if __name__ == "__main__": sys.exit(main())`.
- Return the zero-match-is-valid cases as empty output rather than raising; never crash on an absent file/tap.
- Print `key<TAB>value` or `label: value` lines; keep output greppable and order stable.
- A module docstring doubling as `--help`.
- Read-only inspectors resolve state internally; don't hardcode paths that vary (Brewfile, config).
- **State-mutating helpers stay plan-only**: `upgrade_plan.py` prints `brew upgrade/pin/cleanup`
  commands but never runs them — rollback in Homebrew is hard, so mutations are always the
  reviewer's explicit call.
- Tests live in `tests/brew_doctor/` and call the pure functions directly (no mocking, no `brew`).
