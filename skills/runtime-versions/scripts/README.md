# runtime-versions scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the
`command -v` / `which -a` / `mise which` / `env -i` blocks from scratch each time. Fewer tokens, no
re-derivation, no footguns (e.g. `env -i` wiping PATH so a Homebrew `fish` can't be found, or a
missing tool leaking the previous tool's version into a fish substitution). These are the source of
truth for the mechanical diagnostics; the reference `.md` files carry the judgment.

Run them by absolute path from the skill directory. **All five are READ-ONLY inspectors** — they
observe, never mutate. Safe to re-run. State changes (`mise use`, activating mise, editing shell rc,
uninstalls) stay in the docs and are routed to `shell-sync` / `brew-doctor`, never scripted here.

| Script | Purpose | Example |
|---|---|---|
| `runtime_find.py [tool …]` | **Choose what to install** (the `find` path): per tool — is it mise-managed? recent installable versions + the `@lts` alias where it applies; what resolves now and its owner (mise/homebrew/legacy/system); and a ⚠ flag if brew or an old manager already provides it (→ consolidate via `setup.md`). Runs only `mise registry/ls-remote`, `command -v`, `brew list`. | `runtime_find.py node` |
| `detect_managers.py` | Sprawl hunt: mise + each legacy manager (nvm/asdf/pyenv/rbenv/fnm) — present? home dir? which rc file inits it? global version it provides (migration capture)? Plus brew-installed runtimes and legacy shim dirs on PATH. **Run first.** | `detect_managers.py` |
| `tool_resolve.py [tool …]` | "Who resolves this runtime?" Per tool (default node/python/go/ruby): `command -v`, real path (symlinks followed), owning manager, mise's opinion, every copy on PATH. Queries the **current non-interactive shell**. | `tool_resolve.py node python` |
| `shell_resolve.py [zsh\|fish\|both] [tool …]` | The **real** per-shell test: resolution in a FRESH login shell from a clean `env -i` (the `node`-differs-per-shell bug), plus the mise-shims-on-PATH count (idempotency). Explicit about which shell + clean-login context. | `shell_resolve.py both` |
| `mise_status.py` | mise health + inventory: installed? activated (per `mise doctor`)? shims dir, problem count, `mise current`, `mise ls`. Says so and exits 0 if mise is absent. | `mise_status.py` |

## Worked example — the whole audit in three calls

```
detect_managers.py          # nvm_present=yes (rc-hook ~/.zshrc); mise_present=no; brew_runtimes=node go python@…
tool_resolve.py node        # node_owner=homebrew, node_mise_says=(mise not installed) — brew owns node, not a manager
shell_resolve.py both       # zsh and fish BOTH resolve /opt/homebrew/bin/node, 0 mise shims — consistent, pre-migration
```
Reading: nvm is wired into `~/.zshrc` but `node` actually comes from Homebrew, and zsh/fish agree — so
there's no per-shell divergence yet, but three managers (nvm, brew, and intended mise) overlap. The fix
is `setup.md`: install mise, capture versions, activate via `shell-sync`, then neutralize nvm/brew-node.
Re-run `shell_resolve.py` after activation — every `command -v` should land in the mise shims dir with
exactly `1` shims entry, in **both** shells, before removing anything.

## Why `shell_resolve.py`, not a nested shell

A shell spawned inside your session inherits the outer PATH and **falsely shows mise winning**. The
script launches each shell from an empty environment (`env -i`, keeping only `HOME`/`TERM`) so it
resolves exactly as a new login would. It resolves the shell binary's absolute path *before* clearing
the env — otherwise `env -i fish` can't find a Homebrew fish (env's fallback path is only
`/usr/bin:/bin`). The login rc rebuilds PATH from scratch, so the test stays clean.

## Conventions for adding scripts

- Python 3.9+, **stdlib only** — `#!/usr/bin/env python3`, `from __future__ import annotations`, type
  hints + docstrings, and an executable bit. End with `if __name__ == "__main__": sys.exit(main())`.
- **Separate pure logic from I/O.** Parsing / classifying / formatting live in plain module functions
  (directly unit-tested in `tests/runtime_versions/`, no mocking); the subprocess / PATH / filesystem
  probes live in `_runtime_common.py` (`have`, `run`, `command_v`, `which_all`, `realpath`,
  `login_shell_resolve`, …). A `main(argv=None) -> int` wires them together.
- Print `key<TAB>value` or `label: value` lines; keep output greppable and order stable. Where the old
  bash piped through `tr '\n' ' '`, the port keeps the same trailing space so callers see identical text.
- State **which shell/context** was queried — resolution differs between the script's own
  non-interactive shell and a clean login (`tool_resolve.py` vs `shell_resolve.py`).
- The module docstring doubles as help; `-h`/`--help` prints it and exits 0.
- Handle a manager/shell/mise that **isn't installed** gracefully — report and exit 0, don't error.
