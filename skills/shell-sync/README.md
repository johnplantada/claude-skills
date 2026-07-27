# shell-sync — keep zsh & fish in sync, and keep PATH healthy

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that **sets up, repairs, upgrades,
and optimizes** the sync between zsh and fish — mirroring one canonical shell's environment into the
other (so both behave the same) and keeping PATH healthy — **verified by resolving the environment in
both shells and comparing**.

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Establish the sync: mirror the canonical shell (default: your login shell) into the other — PATH, exported vars, aliases, simple functions, and the **starship prompt** — by regenerating one managed file. |
| **repair** | Fix what's broken: dead/placeholder PATH entries (`/path/to/pip` and friends), tools **installed but not on PATH**, or a tool resolving differently in zsh vs fish. |
| **upgrade** | Re-sync after you change the canonical shell — regenerate the mirror's managed file so a new alias/var/PATH entry propagates. |
| **optimize** | Tighten a working setup: deduplicate PATH, fix ordering/precedence, and prove both shells resolve identically. |

## Why it's different

- **Extracts resolved values, doesn't parse script.** Shell configs are full of `eval`, `source`,
  and conditionals. The skill *runs* the canonical shell to read the real resolved PATH / env /
  aliases, then emits them for the mirror — robust to however your config is written.
- **Regenerates one marked file.** The mirror's synced state lives in a single auto-generated,
  clearly-marked include (e.g. fish `conf.d/00-shell-sync.fish`) that re-runs idempotently — no
  fragile hand-merging into files you edit.
- **Honest about limits.** Functions and clever aliases translate poorly across shells; the skill
  auto-translates the simple cases and **lists** the rest for manual porting instead of emitting
  broken code.
- **Verified.** After changes it resolves PATH/env/aliases in *both* shells, diffs them, and
  confirms each shell still starts clean.

## Requirements

- **Claude Code**, plus **zsh** and **fish** installed.
- macOS or Linux (understands macOS `path_helper` / `/etc/paths.d`).

## Install

Part of the [claude-skills](../) gallery:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/shell-sync ~/.claude/skills/shell-sync
```

## Usage

```
/shell-sync setup      # establish canonical -> mirror sync
/shell-sync repair     # fix dead PATH entries, missing tools, per-shell divergence
/shell-sync upgrade    # re-sync the mirror after the canonical shell changes
/shell-sync optimize   # dedupe, fix ordering, prove parity
```

Or describe it — "my node is different in fish and zsh", "make sure my PATH has everything",
"keep my shells in sync" — and it routes to the right workflow.

```
shell-sync/
├── SKILL.md                 # router + discovery + core method
├── scripts/                 # the stable toolbox — call these, don't re-compose bash
│   ├── dump_env.py          # resolve a shell's PATH/exports/aliases/functions (clean env)
│   ├── path_doctor.py       # PATH audit: dupes, dead entries, installed-but-not-on-PATH
│   ├── shell_diff.py        # zsh vs fish: PATH set diff, startup, tool reachability
│   ├── mirror_plan.py       # emit proposed fish mirror (PATH/env/aliases + starship init) to stdout
│   └── README.md            # toolbox table + worked example + conventions
├── reference/
│   ├── setup.md             # establish the canonical -> mirror sync
│   ├── repair.md            # dead PATH entries, missing tools, per-shell divergence
│   ├── upgrade.md           # re-sync the mirror after the canonical changes
│   ├── optimize.md          # dedupe, ordering/precedence, prove parity
│   ├── translation.md       # zsh <-> fish construct mapping (supporting reference)
│   └── verification.md      # resolve both shells & compare
└── README.md                # (LICENSE lives at the gallery root)
```

## License

[MIT](../../LICENSE).
