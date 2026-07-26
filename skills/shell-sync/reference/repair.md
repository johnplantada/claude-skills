# Repair workflow — fix PATH and a broken / diverged mirror

Goal: fix what's actually broken — a tool that won't resolve, PATH with dead entries, a shell that
errors on startup, or the two shells resolving **different** versions of the same tool. Operate on
the **canonical** shell's config (the source of truth), then re-mirror.

> **Run `scripts/path_doctor.py` for the PATH audit** and **`scripts/shell_diff.py` for divergence**
> — both resolve in a clean environment. The per-check bash below is what they run — reference, not
> what you retype. Harmless-but-messy issues (duplicate entries, ordering) are the tidy-up pass →
> [optimize.md](optimize.md); this path is for things that are *wrong*.

## 1. Audit — one call, report findings (change nothing yet)

```bash
scripts/path_doctor.py zsh          # canonical (default). Use `fish` for the mirror.
scripts/shell_diff.py node go …     # does a tool resolve differently (or not) per shell?
```
`path_doctor.py` emits greppable lines — `dead<TAB>/dir`, `missing_tool_dir<TAB>/dir<TAB>N execs`,
`dup<TAB>/dir`, `entry<TAB>NN<TAB>/dir`. The **repair-class** findings:

- **Dead entries** (`dead`) — directories that don't exist (classic: leftover placeholders like
  `/path/to/pip`, removed toolchains). On macOS a few are `path_helper` cryptex transients —
  expected, not a bug.
- **Installed-but-not-on-PATH** (`missing_tool_dir`) — a tool's bin dir exists with executables but
  isn't on PATH, so the tool "isn't found." `path_doctor.py` checks the usual suspects present on
  the machine: `/opt/homebrew/{bin,sbin}`, `/usr/local/bin`, `~/.local/bin`, `~/.cargo/bin`,
  `~/go/bin`, `~/.asdf/shims`, `~/.rbenv/shims`, `~/.pyenv/shims`, `~/.fnm`.
- **Per-shell divergence** (`shell_diff.py`) — a tool that resolves to a **different path** in zsh vs
  fish (e.g. `node` via nvm in zsh vs asdf in fish), or resolves in one shell but not the other, or a
  shell that prints errors on startup. This is a stale/broken mirror or competing config.

<details><summary>Under the hood (what path_doctor.py runs)</summary>

```bash
env -i HOME="$HOME" TERM=xterm /bin/zsh -l -i -c 'printf "%s\n" $path'   # clean-env resolve
… | while read -r d; do [ -d "$d" ] || echo "MISSING: $d"; done          # dead entries
for d in /opt/homebrew/bin ~/.local/bin ~/.cargo/bin ~/go/bin ~/.asdf/shims; do
  [ -d "$d" ] && ! grep -qx "$d" <path> && echo "NOT ON PATH: $d"
done
```
Why clean-env: a shell launched inside another session inherits the parent's PATH and pollutes the
audit (see [verification.md](verification.md)).
</details>

## 2. Fix in the canonical config (confirm first)

Prioritized 🔴 → 🟡:

- 🔴 **Dead entries / a tool not reachable** — remove the dead/placeholder entries; add the missing
  tool dir (prefer the tool's own init if it has one, e.g. `. "$HOME/.cargo/env"`, else an explicit
  prepend) in the **config file and line** responsible. Confirm before removing anything that could
  hide a tool.
- 🔴 **Per-shell divergence** — a tool resolving differently per shell is a `shell-sync` problem at
  its core: the canonical shell must own the resolution and the mirror is regenerated from it. Fix
  the canonical, then re-mirror (step 3). For runtime managers specifically (nvm/asdf/pyenv vs mise),
  the fix lives in the `runtime-versions` skill — a single canonical activation.
- 🟡 **Shell startup errors** — resolve the erroring init line (a `source` of a file that no longer
  exists, a removed tool's `eval`), so both shells start clean.
- 🟡 **Prompt differs / missing in one shell** — starship's init line is in one shell but not the
  other (e.g. zsh has `eval "$(starship init zsh)"`, fish is missing `starship init fish | source`).
  Fix the canonical, re-mirror ([upgrade.md](upgrade.md)) — the managed block carries the init line.
  A hand-written `PROMPT`/`PS1` can't be auto-ported ([translation.md](translation.md)).

## 3. Verify + re-mirror

- `scripts/path_doctor.py zsh` again — no more `dead`/`missing_tool_dir`. `scripts/shell_diff.py
  <tool …>` — previously-missing tools now reachable, no divergence, both shells start clean (see
  [verification.md](verification.md)).
- If the shells are kept in sync, re-run [upgrade.md](upgrade.md) so the mirror picks up the fix.
