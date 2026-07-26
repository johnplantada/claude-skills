# shell-sync scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the
`env -i … zsh -l -i -c '…'`, `awk seen[$0]++`, and `comm`/`command -v` blocks from scratch each
time. Fewer tokens, no re-derivation, no footguns (the classic one: running `zsh -l -i` from
*inside* another session inherits the parent's `$PATH` and pollutes the audit — every script here
wipes the environment with `env -i` so you read the TRUE login state). These are the source of
truth for the mechanical commands; the reference `.md` files carry the judgment.

Run them by absolute path from the skill directory. All are **read-only inspectors** — including
`mirror_plan.py`, which only prints a proposed file to stdout. **No script ever writes a config
file**; repairs and mirrors are emitted as plans for you to review and apply.

| Script | Purpose | Example |
|---|---|---|
| `dump_env.py <zsh\|fish> [path\|exports\|aliases\|functions\|all]` | Resolve one shell's real environment in a clean login+interactive shell. Single section = raw lines (composable); `all` = tag-prefixed overview. **The primitive under the other three.** | `dump_env.py zsh path` |
| `path_doctor.py [zsh\|fish] [--plan]` | Audit a shell's PATH: `dup` (duplicates in order), `dead` (nonexistent dirs), `missing_tool_dir` (installed but not on PATH). `--plan` emits a deduped/dead-stripped PATH to stdout. | `path_doctor.py zsh` |
| `shell_diff.py [tool …]` | zsh-vs-fish divergence: PATH set diff (`only_in_zsh`/`only_in_fish`, each tagged `benign (…)` or `review`), startup cleanliness, and tool reachability in both. Reports and skips if fish is absent. | `shell_diff.py node go` |
| `mirror_plan.py [canonical] [mirror]` | Emit the proposed fish `conf.d/00-shell-sync.fish` body (PATH + user exports + simple aliases + the starship prompt init line if starship is on PATH) to **stdout** — a plan, never written. Filters out tool-injected vars (`MISE_*`, `HOMEBREW_*`), dead/transient PATH dirs, zsh default aliases, and a starship init already in `config.fish`. Only zsh→fish is auto-generated. | `mirror_plan.py > /tmp/plan.fish` |
| `mirror_drift.py [mirror-file]` | Is the **installed** mirror still current vs the canonical? Compares it against a fresh `mirror_plan.py` and reports `drift_env_*` / `drift_path_*` / `stale_mtime`; prints `in_sync yes\|no` (exit 0 = in sync, 1 = drift). | `mirror_drift.py` |

## Worked example — audit PATH, then prove the shells agree

```
path_doctor.py zsh          # dead  /pkg/env/global/bin ; dead /usr/ucb  → path_helper transients
shell_diff.py node go       # only_in_zsh /usr/ucb  benign (dead/system path_helper)
                            # only_in_fish /opt/homebrew/opt/mise/bin  benign (brew vendor activation: mise)
                            # tool node  zsh=/opt/homebrew/bin/node  fish=/opt/homebrew/bin/node
mirror_drift.py             # in_sync  yes   → installed mirror is current
```
Only a `review` row from `shell_diff.py` is a real divergence; `benign (…)` rows are system/vendor
noise. `in_sync yes` + tools resolving to the **same** path in both = the shells agree. If a change
to zsh made the mirror stale, `mirror_drift.py` prints the `drift_*` lines — then
`mirror_plan.py > /tmp/plan.fish`, review, and install it as the mirror's managed file.

## Conventions for adding scripts

- Python 3.9+, **stdlib only** (no pip deps); `#!/usr/bin/env python3`, `from __future__ import annotations`,
  type hints, and a `def main(argv=None) -> int:` guarded by `if __name__ == "__main__": sys.exit(main())`.
- **Separate pure logic from IO.** Parsing / analysis / formatting are plain module functions (that's what
  the tests in `tests/shell_sync/` call directly — no mocking); the subprocess/filesystem wrappers live in
  `_shell_common.py`.
- Read another shell's real env by invoking it as a **clean login+interactive** shell
  (`_shell_common.run_login` — the Python equivalent of `env -i HOME="$HOME" TERM=xterm <bin> -l -i -c '…'`);
  resolve the binary with `resolve_bin` (stdlib `shutil.which`) *before* wiping the env. If the shell isn't
  installed, report to stderr and skip (exit 3) — never abort. A non-zero shell exit is swallowed (the shell
  may error on one rc line yet still print usable state).
- Print `key<TAB>value` / `label<TAB>value` lines; keep output greppable and order stable.
- **Never mutate** shell config here. State-changing helpers emit a **plan to stdout**; the human applies it.
- A module docstring doubling as `--help` / usage.
