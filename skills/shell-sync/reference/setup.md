# Set up workflow — establish the canonical → mirror sync

Goal: stand up the sync for the first time — make the **mirror** shell reproduce the **canonical**
shell's user environment (PATH, env vars, aliases, functions best-effort) from one regenerated,
clearly-marked file. Idempotent and verified.

Assumes canonical = zsh, mirror = fish (the common case). Reverse the commands if the user's
canonical is fish. **Confirm direction first** — overwriting the wrong shell loses work.

> **`scripts/mirror_plan.py` does steps 2 + 3** — it extracts canonical zsh state and prints the
> proposed fish managed file **to stdout** (a plan; it writes nothing). `scripts/dump_env.py` is the
> extractor underneath. Keeping the mirror current *after* setup (canonical changed later) →
> [upgrade.md](upgrade.md). PATH is messy going in → clean it first via [repair.md](repair.md).

## 1. Clean the canonical first

If PATH has junk (duplicates, dead entries), run [repair.md](repair.md) on the **canonical** shell
before mirroring — don't propagate garbage. Then proceed.

## 2 + 3. Generate the mirror's managed file (as a plan)

```bash
scripts/mirror_plan.py > /tmp/00-shell-sync.fish    # review before installing
```
It emits, between `# >>> shell-sync (AUTO-GENERATED) >>>` markers: one ordered `set -gx PATH …`
block (full resolved list, predictable), `set -gx NAME 'VALUE'` per **user-set** exported var (a
denylist drops shell-managed vars like `PWD`/`SHLVL`/`TERM*`/`SSH_*`), and `alias name 'value'` for
simple aliases (ones using `$`/backticks/braces are emitted as `# TODO port` comments). Functions
are **not** translated — it lists them for manual porting to `~/.config/fish/functions/`.

Review the plan, then install it as the mirror's **one** marked file —
`~/.config/fish/conf.d/00-shell-sync.fish` (the `00-` prefix loads it before other conf.d). Back up
any existing copy first. If the user's `config.fish` also sets PATH manually, tell them to remove
that block so this file owns PATH (conf.d loads before config.fish, so a manual `set -gx PATH` there
would override this). See [translation.md](translation.md) for the zsh↔fish mapping.

<details><summary>Under the hood (what mirror_plan.py / dump_env.py run)</summary>

```bash
zsh -l -i -c 'printf "%s\n" $path'   # PATH — fully resolved (evals, sources, path_helper applied)
zsh -l -i -c 'env'                   # exported env vars (NAME=value); denylist filters shell-managed
zsh -i -c 'alias'                    # aliases
zsh -i -c 'print -l ${(k)functions}' # user functions (listed, not translated)
```
For env, the alternative to the denylist is a **delta vs a bare shell** (`env -i zsh -fc 'env'` →
subtract). For PATH, mirror the full resolved list — it *is* the desired PATH.
</details>

## 3b. Prompt (starship)

If the canonical shell uses [starship](https://starship.rs), the mirror should show the **same**
prompt. `mirror_plan.py` already emits `starship init fish | source` into the managed block when
`starship` is on PATH — so the mirror inherits the prompt automatically. The prompt's *config* is a
single shell-agnostic `~/.config/starship.toml`, shared by both shells; it needs no translation —
track it via the `dotfiles` skill so it's reproducible. (No starship? A hand-written zsh
`PROMPT`/`PS1` isn't portable to fish — port it by hand, or adopt starship for parity.)

## 4. Verify (both shells must agree)

Run [verification.md](verification.md): resolved PATH sets match, synced env vars match, aliases
present in both, the **prompt matches** (same starship, or an intentionally-ported prompt), and
**each shell starts with no errors**. Report the diff as evidence.

## 5. Report

- What was mirrored (counts: N path entries, N env vars, N aliases).
- What was **not** auto-translated (functions/complex aliases) and where to finish them by hand.
- The one managed file that now owns the synced state, and that re-running after editing canonical is
  the [upgrade.md](upgrade.md) path.
