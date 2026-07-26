# dotfiles — manage your configs with chezmoi

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that **sets up, repairs, upgrades,
and optimizes** your dotfiles with [chezmoi](https://chezmoi.io): version-control your configs in one
git-backed source, sync them across machines, bootstrap a fresh machine — and keep **secrets** out of
git (their plaintext never enters the model's context). Every change is verified with `chezmoi diff`
/ `status` / `doctor`.

Pairs naturally with the other gallery skills: `nvim-config` and `shell-sync` manage specific
configs; **dotfiles** version-controls and syncs them all.

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Initialize chezmoi and bring existing configs under a **private** repo — or bootstrap a fresh machine from an existing repo. |
| **repair** | Fix a broken state — `apply` failing (missing key, unreachable password manager, template error), drift that won't reconcile, a source conflict. |
| **upgrade** | Day-to-day add / edit / apply in one drift-free flow, and sync across machines (`chezmoi update` / push / pull). |
| **optimize** | Review & tighten the source — untracked configs worth carrying, cruft to ignore, plaintext that should be encrypted or templated. |
| **secrets** | Store credentials safely — encryption (age) or password-manager templates, never plaintext in git; a secret's value never enters the model's context. |

## Why it's different

- **Source is truth, verified by chezmoi.** It doesn't eyeball files — it uses `chezmoi status`
  (drift), `chezmoi diff` (what apply changes), and `chezmoi doctor` (health), and confirms
  `apply` is idempotent.
- **Secrets are a first-class concern.** It scans before committing and routes credentials through
  encryption or password-manager templates — the #1 way dotfiles leak.
- **Drift-aware.** It enforces a single editing flow (source-first `chezmoi edit --apply`, or
  home-first `chezmoi re-add`) so you don't end up with the source and your machine disagreeing.

## Requirements

- **Claude Code**, plus **chezmoi** (`brew install chezmoi`).
- `git` and (for pushing) `gh` or a configured remote.
- Optional: `age` (file encryption) and/or a password manager CLI (1Password, Bitwarden) for
  secret templates.

## Install

Part of the [claude-skills](../) gallery:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/dotfiles ~/.claude/skills/dotfiles
```

## Usage

```
/dotfiles setup      # first-time init, or bootstrap a new machine
/dotfiles repair     # apply fails, drift won't reconcile, source conflict
/dotfiles upgrade    # add / edit / apply, and sync across machines
/dotfiles optimize   # tighten the source: coverage, cruft, secret hygiene
/dotfiles secrets    # store a credential safely
```

Or describe it — "track my nvim + shell config", "set up my dotfiles on a new laptop", "how do I
keep this API key out of git" — and it routes to the right workflow.

```
dotfiles/
├── SKILL.md                 # router + discovery + core model + secrets safety
├── scripts/                 # the stable toolbox — call these over ad-hoc bash
│   ├── chezmoi_status.py    # environment + health + drift, one greppable report
│   ├── dotfiles_inventory.py# managed files tagged with per-file drift status
│   ├── secret_scan.py       # plaintext-secret scan — paths + reason, never values
│   └── README.md            # toolbox table + worked example + conventions
├── reference/
│   ├── setup.md             # initialize + add existing configs + private repo; new-machine bootstrap
│   ├── repair.md            # apply failures, unreconcilable drift, source conflicts
│   ├── upgrade.md           # add / edit / apply without drift, and sync across machines
│   ├── optimize.md          # tighten the source: coverage, cruft, secret hygiene
│   ├── secrets.md           # encryption + password-manager templates (value never read)
│   └── verification.md      # chezmoi status/diff/doctor + no-secret checks
└── README.md                # (LICENSE lives at the gallery root)
```

## License

[MIT](../LICENSE).
