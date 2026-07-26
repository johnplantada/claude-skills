# Upgrade workflow — manage & bump runtime versions day-to-day

Goal: set the right version in the right scope, install it, and keep things current — without
guessing. This is the day-to-day path: change a version, pin a project, bump to newer releases.
mise resolves versions from the nearest config upward, so **scope is everything**.

> Choosing *which* version/scope in the first place? → [find.md](find.md). A version that won't
> resolve because an old manager still wins? → [repair.md](repair.md).

## Scope model: global vs per-project

| Scope | Command | Writes | Use for |
|---|---|---|---|
| **Global** (default) | `mise use -g node@lts` | `~/.config/mise/config.toml` | your machine-wide default |
| **Project** | `mise use node@22` (in the project dir) | `./mise.toml` | a project's pinned version |
| **Project, portable** | `mise use --asdf node@22` | `./.tool-versions` | asdf/other-tool interop |

Resolution walks **up** from the current directory: the nearest `mise.toml`/`.tool-versions`/`.nvmrc`
wins, falling back to global. Check what applies here with **`scripts/mise_status.py`** (reports
`mise current` + `ls`) or **`scripts/tool_resolve.py <tool>`** (adds the owning manager and dupes);
raw form:

```bash
mise current                         # versions in effect for THIS directory + their source file
mise which node                      # absolute path of the resolved shim target
```

## Honor existing project files (don't rewrite them)

mise reads these natively — an existing repo needs no conversion:

```bash
cat .nvmrc .tool-versions mise.toml 2>/dev/null   # whatever the project already declares
mise install                         # install exactly what these files pin
```
Only add a `mise.toml` when a project has **no** version file; otherwise respect the one that's there.

## Install & list

```bash
mise ls-remote node                  # available versions to pick from
mise install node@22.5.0             # install a specific version (no scope change)
mise install                         # install everything declared by config in scope
mise ls                              # installed versions; Active marked; missing shown
```

## Set versions

```bash
mise use -g python@3.13              # change the global default (confirm — affects every project)
mise use node@lts                    # pin THIS project (writes ./mise.toml)
mise use node@22 python@3.13         # multiple tools at once
mise unuse node                      # drop a tool from the current-scope config
```

## Upgrade

```bash
mise outdated                        # tools with newer versions available
mise upgrade                         # bump to latest allowed by each version spec (confirm)
mise use -g node@lts && mise install # move the global LTS pin forward, then install
mise prune                           # remove installed versions no config references (confirm)
```
After changing a runtime that LSP servers or a project build depend on, re-verify
([verification.md](verification.md)) and, for editor tooling, chain into the `nvim-config` skill.

## Report

What changed and in which scope (global vs which project file), the resulting `mise current`, and any
config file written that should be tracked via the `dotfiles` skill.
