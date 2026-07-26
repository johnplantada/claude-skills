# zsh ↔ fish translation reference

How each construct maps between the shells. Used by the **sync** workflow to emit the mirror's
managed file. Translate the **resolved value**, not the source syntax.

## PATH

| zsh | fish |
|---|---|
| `export PATH="/a:/b:$PATH"` | `set -gx PATH /a /b $PATH` |
| (whole list) | `set -gx PATH /a /b /c …` (space-separated, canonical order) |
| append one dir | `fish_add_path --append /a` (idempotent) |
| prepend one dir | `fish_add_path /a` (idempotent, moves to front) |

For a mirror file, prefer one explicit `set -gx PATH <ordered entries>` block — predictable and
idempotent — over many `fish_add_path` calls. fish also has universal `fish_user_paths` (in
`fish_variables`); don't fight it, just let the managed `set -gx PATH` define the full list.

## Environment variables

| zsh | fish |
|---|---|
| `export NAME="value"` | `set -gx NAME 'value'` |
| `export NAME="$OTHER/x"` | `set -gx NAME "$OTHER/x"` (fish expands `$var` in double quotes) |
| `unset NAME` | `set -e NAME` |
| colon-list var (e.g. `MANPATH`) | `set -gx MANPATH /a /b` (fish lists are space-separated arrays) |

Skip shell-managed vars (PWD, SHLVL, PS1/PROMPT, TERM*, ZSH*, etc.) — mirror only user-set ones.

## Aliases

| zsh | fish |
|---|---|
| `alias gs='git status'` | `alias gs 'git status'` (or `abbr -a gs 'git status'`) |
| alias with args needing `$@` | fish `alias` wraps into a function; simple cases work. Complex → write a fish function instead. |

`abbr` (fish abbreviations) expand inline as you type — good for interactive shortcuts; `alias`
is a thin function. Simple command aliases translate cleanly; anything using zsh globbing,
`$1`/`$@` gymnastics, or zsh-only syntax should be **flagged for manual porting**, not auto-emitted.

## Functions

zsh and fish function bodies are **not** compatible (different syntax for args, conditionals,
loops, `$1` vs `$argv`). Do **not** blindly translate.

| zsh | fish |
|---|---|
| `foo() { ... }` / `function foo { ... }` | `function foo … end` in `~/.config/fish/functions/foo.fish` |
| `$1 $2 $@` | `$argv[1] $argv[2] $argv` |
| `if [ ... ]; then … fi` | `if test …; …; end` |

Policy: only auto-emit **trivial one-liners** that are obviously portable. For anything else, list
the function names and their zsh source so the user can port them by hand.

## Prompt (starship)

[starship](https://starship.rs) is a **cross-shell** prompt: one shell-agnostic config
(`~/.config/starship.toml`) plus a per-shell **init line**. shell-sync mirrors only the init line —
the `.toml` needs no translation and is a shared dotfile (track it via the `dotfiles` skill).

| zsh | fish |
|---|---|
| `eval "$(starship init zsh)"` | `starship init fish \| source` |

`mirror_plan.py` emits the fish init line into the managed block when `starship` is on PATH. Put it
in `conf.d/00-shell-sync.fish` (or `config.fish`); the single `starship.toml` then gives both shells
the **same** prompt. A hand-written zsh prompt (`PROMPT`/`PS1`) is **not** portable — port it by hand
or adopt starship for true cross-shell parity.

## fish gotchas

- fish has no `export`; use `set -gx` (global exported) / `set -x` (local exported).
- fish arrays are space-separated; there is no `:`-joined PATH string to append to.
- Universal variables (`set -U`) persist in `fish_variables` across sessions — prefer `set -gx`
  in a generated file so state is reproducible from config, not hidden universal state.
- conf.d/ files load **before** `config.fish`; put PATH there so it isn't overridden later.
