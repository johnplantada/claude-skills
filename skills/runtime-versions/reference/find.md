# Find workflow — choose which runtime, which version, which scope

Goal: turn a need ("I need node for this project", "which python should I use?") into the right
install decision — the step *before* setup/upgrade actually installs it. Read-only: recommends,
never installs.

> **Run [`scripts/runtime_find.py`](../scripts/README.md) `<tool>`** — it checks whether mise can
> manage the tool, lists recent installable versions (+ the `@lts` alias where it applies), shows
> what currently resolves and who owns it, and flags a runtime that brew or an old manager is
> already providing (→ consolidate via setup.md). The commands below are what it runs.

## 1. Is it mise-managed, and what versions exist?

```bash
mise registry | grep -i <tool>       # is this tool known to mise? (and the backend it uses)
mise ls-remote <tool>                # every installable version — newest at the bottom
mise ls-remote node | grep -i lts    # LTS lines, for languages that ship an LTS (node)
```

## 2. Choose the version

| You want… | Spec | When |
|---|---|---|
| Stability (apps, daily use) | `<tool>@lts` (node) or a pinned major `node@22` | most cases — patches without a surprise major |
| Newest features | `<tool>@latest` | tooling/CI where you track head |
| Match a project | whatever its `.nvmrc`/`.tool-versions` pins | honor it as-is — don't rewrite |

A **pinned major** (`node@22`, `python@3.13`) is the safe default: you get patch updates, never a
surprise major bump. Reserve `@latest` for throwaway/CI.

## 3. Choose the scope

| Scope | Spec | Use for |
|---|---|---|
| Global default | `mise use -g <tool>@<v>` → `~/.config/mise/config.toml` | your machine-wide default |
| This project | `mise use <tool>@<v>` (in the dir) → `./mise.toml` | pin a repo to a version |
| Portable | `mise use --asdf <tool>@<v>` → `./.tool-versions` | asdf/other-tool interop |

Resolution walks **up** from the current dir; the nearest file wins, falling back to global.

## 4. Sanity-check before installing

- **Already provided by brew or an old manager?** `runtime_find.py` flags it — don't stack a second
  source. Install runtimes through **mise**, not brew (brew auto-bumps and breaks pins); consolidate
  via [setup.md](setup.md).
- **Honor an existing project file** rather than adding a competing one.

## 5. Install

Once decided, hand to **[upgrade.md](upgrade.md)** (`mise use …` + `mise install`) if mise already
owns your runtimes, or **[setup.md](setup.md)** if you still need to stand mise up. Then confirm it
resolves — [verification.md](verification.md).
