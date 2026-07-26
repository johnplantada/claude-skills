---
name: Shell Sync
description: Set up, repair, upgrade, and optimize the sync between your zsh and fish shells, and keep PATH healthy. Use to SET UP a canonical→mirror sync (regenerate one shell's PATH/env/aliases/functions and prompt from the other so both behave the same, including a shared starship prompt), REPAIR PATH and divergence (dead entries, installed-but-not-on-PATH tools, a tool or prompt resolving differently per shell, startup errors), UPGRADE the mirror after the canonical shell changes (re-propagate new aliases/vars/PATH/prompt), or OPTIMIZE a working setup (deduplicate, fix ordering/precedence, prove parity). Every change is verified by resolving the environment in both shells and comparing.
argument-hint: [setup|repair|upgrade|optimize]
allowed-tools: Bash(*shell-sync/scripts/*), Bash(zsh -l *), Bash(zsh -i *), Bash(zsh -f *), Bash(zsh -c *), Bash(fish -l *), Bash(fish -c *), Bash(command -v *), Bash(ls *), Bash(cp *), Bash(git -C * *)
---

# Shell sync

Keep **zsh** and **fish** consistent, and keep **PATH** healthy. Route to a workflow:

| The user wants to… | Workflow |
|---|---|
| Establish the sync — make both shells behave the same (env, PATH, aliases, functions) | [reference/setup.md](reference/setup.md) |
| Fix PATH or divergence — dead entries, a tool not found, a tool differing per shell | [reference/repair.md](reference/repair.md) |
| Re-sync the mirror after changing the canonical shell (new alias/var/PATH) | [reference/upgrade.md](reference/upgrade.md) |
| Tighten a working setup — dedupe, fix ordering/precedence, prove parity | [reference/optimize.md](reference/optimize.md) |

Sync model is **canonical → mirror**: one shell is the source of truth; the other is regenerated
to match. Default canonical = the login shell (`$SHELL`); confirm with the user.

**No workflow named?** (a bare `/shell-sync`) — don't guess one. **Triage first:** run Discovery,
then `scripts/shell_diff.py` and `scripts/mirror_drift.py`, classify the findings, and route:

- `mirror_drift.py` reports drift (`drift_*` / `stale_mtime`) → **upgrade** (re-sync the mirror).
- `shell_diff.py` shows a `review` divergence or a `startup … issues` → **repair**.
- No mirror file exists yet → **setup**.
- Everything `benign`/`in_sync yes`/startup clean → report parity and **stop** — there's nothing to do.

Ignore `benign (…)` divergences from `shell_diff.py` (system `path_helper` / brew vendor
activation) — they're expected noise, not work. Only a `review` row is a real divergence.

## The scripts (call these, don't re-compose bash)

The mechanical commands live in [`scripts/`](scripts/README.md) as tested, clean-environment helpers.
**Call them by name** — the inline bash below and in the reference docs is under-the-hood explanation,
not what you retype each session. All are read-only; none writes a config file (repairs/mirrors print
a plan to stdout for you to apply).

| Need | Script |
|---|---|
| Resolve a shell's real PATH / exports / aliases / functions | `scripts/dump_env.py <zsh\|fish> [section]` |
| Audit PATH — dupes, dead entries, installed-but-not-on-PATH (`--plan` = cleaned PATH) | `scripts/path_doctor.py [zsh\|fish] [--plan]` |
| Diff zsh vs fish — PATH set, startup cleanliness, tool reachability | `scripts/shell_diff.py [tool …]` |
| Emit the proposed fish mirror file (zsh→fish: PATH/env/aliases + starship prompt init) to stdout | `scripts/mirror_plan.py` |
| Check the installed mirror is still current vs the canonical (drift / staleness) | `scripts/mirror_drift.py [mirror-file]` |

## Discovery (always run first)

```bash
echo "login shell: $SHELL"; command -v zsh fish        # which shells exist
```
Locate config files (only those that exist):
- **zsh:** `~/.zshenv`, `~/.zprofile`, `~/.zshrc`, `~/.zlogin`
- **fish:** `~/.config/fish/config.fish`, `~/.config/fish/conf.d/*.fish`,
  `~/.config/fish/functions/`, `~/.config/fish/fish_variables` (universal vars incl. `fish_user_paths`)
- **macOS system PATH:** `/etc/paths`, `/etc/paths.d/*` (applied by `path_helper` in `/etc/zprofile`)
- **prompt:** `command -v starship` and `~/.config/starship.toml` — starship is cross-shell, so its
  single config is shared and only its per-shell init line is mirrored (see below).

Establish **canonical** (source of truth) and **mirror** (regenerated) — confirm direction before
writing anything.

## Core method: extract resolved values, don't parse script

Shell configs contain `eval`, `source`, and conditionals — do **not** statically translate them.
Instead **run the canonical shell and read the resolved state** with `scripts/dump_env.py`, then
emit it for the mirror:

```bash
scripts/dump_env.py zsh path        # resolved PATH entries, one per line
scripts/dump_env.py zsh exports     # exported env vars, NAME=value
scripts/dump_env.py zsh aliases     # aliases, name=value
scripts/dump_env.py zsh functions   # user function names
```
`dump_env.py` already runs the shell in a **clean environment** (`env -i … zsh -l -i -c …`) so a
shell launched inside another session can't pollute the result with the parent's PATH.

<details><summary>Under the hood (what dump_env.py runs)</summary>

```bash
zsh -l -i -c 'printf "%s\n" $path'   # resolved PATH entries (zsh $path array)
zsh -l -i -c 'env'                   # exported env vars, NAME=value
zsh -i -c 'alias'                    # aliases
zsh -i -c 'print -l ${(k)functions}' # user function names
```
</details>

For a mirror, drop system defaults/shell-internal vars (`mirror_plan.py` applies a denylist; or
compute a **delta vs a bare shell**, `env -i zsh -fc 'env'`). Translation rules (zsh↔fish for
PATH/env/alias/function/abbr): [reference/translation.md](reference/translation.md).

## Core principles

1. **Regenerate into the marked block; never hand-merge outside it.** The mirror's synced content
   lives in one **marked, auto-generated file** (e.g. fish `conf.d/00-shell-sync.fish`) the workflow
   overwrites idempotently — never splice into a file the user hand-edits. `mirror_plan.py` emits
   that block, but treat it as a **draft to review, not to install blindly**: its filters are
   good but not omniscient (a new tool that injects env like `mise`/`brew`, an alias it
   mis-classifies). When the generator's output would *regress* a good curated file, a **surgical
   edit inside the markers** — or a one-line diff-and-patch guided by `mirror_drift.py` — is the
   correct move, not a full overwrite. Order of preference: regenerate → marked-block edit → (never)
   hand-merge outside the markers.
2. **Verify in both shells.** After syncing, resolve PATH/env/aliases in *both* and diff them —
   see [reference/verification.md](reference/verification.md). This is the golden rule: prove it,
   don't assume.
3. **Back up before overwriting** any config file (timestamped copy).
4. **Be honest about limits.** Functions and complex aliases translate poorly across shells —
   auto-translate the simple ones, and **list** what needs manual review rather than emitting
   broken code.
5. **Fix the canonical first.** If PATH is messy, run the **repair** workflow on the canonical shell,
   then re-sync ([upgrade.md](reference/upgrade.md)) — don't propagate junk (`/path/to/pip`,
   duplicates) into the other shell.

## Settings

Read `~/.config/devenv/config.toml` before prompting; if a `[shell-sync]` section exists, use it as
defaults (precedence: explicit answer this session > `config.toml` > ask). Had to ask? Offer to save
the answer back. Managed by the `devenv` skill. Keys honored:
- `canonical` — source-of-truth shell (skips the "which is canonical?" prompt).
- `mirror` — the shell regenerated to match.
- `sync` — what to keep in sync: any of `path`, `env`, `aliases`, `functions`, `prompt` (the
  starship init line; the shared `starship.toml` is tracked by the `dotfiles` skill).

## Safety

- Confirm sync **direction** before writing. Overwriting the wrong shell's config loses work.
- `fish_add_path` and `set -gx PATH` change PATH ordering — regenerate the whole managed block so
  ordering is predictable, don't append piecemeal.
- Removing PATH entries can hide tools — show what would be removed and why, and confirm.
