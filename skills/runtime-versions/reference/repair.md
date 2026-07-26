# Repair workflow — fix a broken runtime resolution

Goal: your runtimes don't resolve the way they should — `node` differs between zsh and fish, an old
manager's shim still wins over mise, mise isn't activated, or a version won't resolve at all.
Diagnose in a **clean env** (a nested shell lies), fix the narrowest cause, then re-verify in both
shells.

> **Diagnose with the scripts** ([scripts/README.md](../scripts/README.md)): `detect_managers.py`
> (who's present + rc hooks + leftover shim dirs), `tool_resolve.py <tool>` (what wins now + owner),
> `shell_resolve.py both` (the clean-env per-shell truth), `mise_status.py` (is mise even
> activated?). The golden rule: **never diagnose from reading config** — a shim on PATH decides what
> runs. See [verification.md](verification.md).

## 1. Symptom → cause

| Symptom | Likely cause | Check |
|---|---|---|
| `node` differs in zsh vs fish | only one shell activates mise; managers differ per shell | `shell_resolve.py both` |
| right version installed, wrong one runs | an old shim dir (`~/.nvm`, `~/.pyenv/shims`) precedes mise on PATH | `tool_resolve.py <tool>` |
| `mise` works but shims don't resolve | mise not activated in this shell | `mise_status.py` (`mise doctor`) |
| `command not found` / no version | version not installed, or config not honored | `mise current` · `mise ls` |
| "still uses old node" after migrating | leftover manager rc hook or shim dir not removed | `detect_managers.py` |

## 2. Fix: activation missing, or per-shell divergence

The canonical shell must own the `mise activate` line and the mirror is regenerated — **route this
through the `shell-sync` skill**, don't hand-patch one shell (that's how the two drift). Confirm the
activation line is present and lands **after** any surviving legacy manager init:

| Shell | Line |
|---|---|
| zsh | `eval "$(mise activate zsh)"` |
| fish | `mise activate fish \| source` |

Then re-run `shell_resolve.py both` — both shells must resolve into the mise shims dir.

## 3. Fix: an old shim wins over mise

mise's shims must precede every legacy shim dir on PATH. If `detect_managers.py` shows a
`~/.pyenv/shims` / `~/.nvm` entry ahead of mise, remove that manager's init from the canonical shell
(via `shell-sync`) and drop the leftover shim dir. Uninstall the dead manager via `brew-doctor` once
resolution is green. (This is the tail of a migration — [setup.md](setup.md).)

## 4. Fix: a version won't resolve

```bash
mise current                         # what mise thinks applies here, and from which file
mise install                         # install everything the in-scope config pins
mise use -g <tool>@<version>         # (confirm) set a global default if none is set
```
An existing `.nvmrc`/`.tool-versions` is honored as-is — if it pins a version you haven't installed,
`mise install` fixes it. Don't rewrite the project's file.

## 5. Verify

Re-run **`shell_resolve.py both`** and **`mise_status.py`**: every `command -v` lands in the mise
shims dir, versions match intent, zsh and fish agree, and `mise doctor` reports activation on with no
PATH problems. Full criteria in [verification.md](verification.md). Not green in both shells = not fixed.
