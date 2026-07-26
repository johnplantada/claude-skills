# Optimize workflow — tighten PATH and prove the shells agree

Goal: the shells work and nothing's broken — now make the setup **lean and provably consistent**:
remove duplicate PATH entries, fix ordering/precedence, prune redundant managed state, and confirm
the mirror is a faithful copy of the canonical. Review and report; change nothing without
confirmation. (Something actually *wrong* — a dead entry, a tool not found, a divergence — is
[repair.md](repair.md).)

> **`scripts/path_doctor.py`** finds duplicates + ordering; **`scripts/shell_diff.py`** proves
> parity. Both run in a clean environment. The bash below is what they run — reference only.

## 1. Duplicates & ordering

```bash
scripts/path_doctor.py zsh          # `dup` lines + the ordered `entry` list
```
- **Duplicates** (`dup`) — the same dir listed more than once. Harmless to resolution (first wins)
  but a sign of piecemeal `export PATH=…` appends; note which config lines add the repeats and
  collapse them.
- **Order/precedence** — Homebrew and version-manager shims should generally precede `/usr/bin`;
  flag obvious inversions (a system dir shadowing a `brew`/mise tool). `path_doctor.py zsh --plan`
  prints a deduped, correctly-ordered PATH **to stdout** as a starting point (a plan — it writes
  nothing).

## 2. Prune redundant managed state

If the mirror's managed file carries entries the canonical no longer has (an old tool's PATH, a
retired alias), regenerating from the canonical drops them — this is really an [upgrade.md](upgrade.md)
re-sync. Optimize is where you *notice* the drift; upgrade is where you apply it.

## 3. Prove parity (the point)

```bash
scripts/shell_diff.py node cargo go rustc python3
```
A tight setup shows: **`only_in_fish` empty** (mirror has everything canonical does), `only_in_zsh`
holding only the expected macOS `path_helper` transients, every tool resolving to the **same path**
in both shells, the **same prompt** in both (starship inits in each, driven from one shared
`~/.config/starship.toml`), and both starting clean. That's the definition of "in sync" — see
[verification.md](verification.md).

## 4. Report

The dedupe/ordering changes proposed (with the responsible config line), any drift the mirror should
drop (→ upgrade), and the parity evidence proving both shells resolve identically.
