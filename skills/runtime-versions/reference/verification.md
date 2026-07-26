# Verification — prove mise owns your runtimes, in BOTH shells, from a clean env

The golden rule: **never declare a migration done from reading config.** Config says what *should*
happen; a shim on PATH decides what *does*. Prove resolution by observing real behavior, before and
after — and do it in a **clean environment**, because a shell launched inside your current session
inherits the outer PATH and will falsely show mise winning.

> **Use the scripts** ([scripts/README.md](../scripts/README.md)): `mise_status.py` for health,
> `shell_resolve.py both` for the clean-env per-shell test (it already does `env -i` correctly,
> including resolving a Homebrew shell's absolute path). The `bash` below is what they run under the hood.

## Health

**`scripts/mise_status.py`** — installed? activated (per `mise doctor`)? shims dir, problem count,
`mise current`, `mise ls`, all greppable; says so and exits 0 if mise is absent. Under the hood:

```bash
mise doctor                          # activation status, shims dir, problems ("mise is active")
mise ls                              # installed tools; each intended runtime marked Active
mise current                         # versions in effect here + the file each came from
```
`mise doctor` should report activation on and no PATH problems. If it says mise is **not** activated,
the shell init (owned by `shell-sync`) is the fix — not a mise reinstall.

## The real test — clean-env resolution in BOTH shells

**`scripts/shell_resolve.py both`** does exactly this: a nested shell inherits PATH and pollutes the
check, so it launches each shell from an **empty** environment (`env -i`), keeping only `HOME`/`TERM`,
so runtimes resolve exactly as a fresh login would. Under the hood:

```bash
# zsh, clean login+interactive:
env -i HOME="$HOME" TERM=xterm /bin/zsh -l -i -c '
  for t in node python go; do printf "%-7s %s  %s\n" "$t" "$(command -v $t)" "$($t --version 2>/dev/null)"; done'

# fish, clean login:
env -i HOME="$HOME" TERM=xterm /usr/bin/env fish -l -c '
  for t in node python go; printf "%-7s %s  %s\n" $t (command -v $t) ($t --version 2>/dev/null); end'
```
Pass criteria — in **both** shells:
- every `command -v` points into the **mise shims dir** (e.g. `~/.local/share/mise/shims/node`) — NOT
  `~/.nvm`, `~/.pyenv/shims`, `/opt/homebrew/bin/node`, or an fnm/asdf path.
- the reported versions **match intent** (the settings `tools` map / what you set with `mise use`).
- zsh and fish agree — same path, same version. Divergence = a `shell-sync` fix, not done.

## Per-project files still honored

Migration must not break project pins. In a project that declares a version:

```bash
cd <project-with-.nvmrc-or-.tool-versions>
mise current                         # shows the project version, sourced from that file
command -v node && node --version    # resolves to the pinned version via a mise shim
```

## Activation is idempotent

Re-sourcing shell init (or opening nested shells) must not stack duplicate shim entries on PATH.
`shell_resolve.py` already prints `<shell>:mise_shims_on_path` (**expect 1**) for each shell. Raw form:

```bash
env -i HOME="$HOME" TERM=xterm /bin/zsh -l -i -c \
  'echo "$PATH" | tr ":" "\n" | grep -c "mise.*shims"'   # expect 1, not 2+
```
More than one mise-shims entry means activation runs twice — fix the shell init (via `shell-sync`)
rather than tolerating a duplicated PATH.

Only after all of the above passes in both shells is it safe to remove the old managers
([setup.md](setup.md)).
