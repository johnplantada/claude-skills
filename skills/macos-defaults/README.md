# macos-defaults — make your Mac's system settings reproducible

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that **sets up, repairs, upgrades,
and optimizes** macOS system preferences as **idempotent `defaults` code**: capture the settings you
care about into a declarative, commented `macos.sh`, apply it on any machine, fix settings that won't
stick, and audit for drift. Every setting is proven by re-reading it — a `defaults write` is never
trusted blindly.

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Read current prefs (Dock, Finder, keyboard/trackpad, screenshots, key-repeat, show-all-extensions, hidden files, tap-to-click) and write them as an idempotent, grouped `defaults write` script. |
| **repair** | Fix a setting that won't stick — wrong domain/key/type, needs a `killall`/logout, a `sudo` domain, or a value the OS rewrites. |
| **upgrade** | Apply the script to converge a machine (new machine, after edits), `killall` the affected apps, flag what needs logout/restart, and reconcile after a macOS update. |
| **optimize** | Compare live `defaults read` values against the declared script, list the drift — system-changed vs script-ahead — prioritized, and tighten the declaration. |

## Why it's different

Most "macOS setup" gists are a pile of `defaults write` lines you paste once and hope for. This skill
treats prefs like code:

- **Verification-first.** After every write it re-reads the value and confirms it matches — writes
  no-op, coerce types, or hit the wrong domain, so the read is the proof.
- **Reflects reality.** `setup` reads current values before declaring them, so the script mirrors
  the machine instead of a guessed default.
- **Idempotent + drift-aware.** The script is safe to re-run, and `optimize` tells you exactly where
  the live machine diverged from what's declared.
- **Reproducible.** The `macos.sh` is a dotfile — track it via the `dotfiles` skill (chezmoi), and
  `devenv bootstrap` runs it as the OS-settings step.

Security/privacy settings (FileVault, Gatekeeper, firewall, TCC) are never touched without explicit
confirmation, and `sudo`-only domains are confirmed before writing.

## Requirements

- **Claude Code**, on **macOS** (uses the `defaults` system).

## Install

Part of the [claude-skills](../) gallery:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/macos-defaults ~/.claude/skills/macos-defaults
```

## Usage

```
/macos-defaults setup       # snapshot current prefs into macos.sh
/macos-defaults repair      # fix a setting that won't stick
/macos-defaults upgrade     # apply the script + restart apps; reconcile after an OS update
/macos-defaults optimize    # find drift vs the declared script, and tighten it
```

Or describe it — "save my Mac settings to a script", "set up this Mac's defaults", "did my Finder
prefs drift" — and it routes to the right workflow.

```
macos-defaults/
├── SKILL.md                 # router + discovery + verification-first principles
├── scripts/                 # the stable toolbox — call these instead of re-composing bash
│   ├── defaults-read.sh     # read prefs as greppable `domain key = value` (read-only)
│   ├── drift-audit.sh       # parse a macos.sh + re-read live -> MATCH/DRIFT/MISSING (read-only)
│   ├── defaults-apply.sh    # back up -> run script -> killall apps (mutating, gated behind --yes)
│   └── README.md            # toolbox table + worked example + conventions
├── reference/
│   ├── setup.md             # read live values -> grouped, idempotent defaults script
│   ├── repair.md            # a setting that won't stick: wrong key/type, restart/sudo, OS-rewritten
│   ├── upgrade.md           # apply -> killall affected apps -> flag reboot-needed; OS-update reconcile
│   ├── optimize.md          # live vs declared drift, classified + prioritized + tighten
│   └── verification.md      # re-read every key + idempotency + find domain/key
└── README.md                # (LICENSE lives at the gallery root)
```

## License

[MIT](../../LICENSE).
