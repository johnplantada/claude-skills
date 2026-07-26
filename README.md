# devenv — a Claude Code plugin

A gallery of [Claude Code](https://claude.com/claude-code) **Agent Skills** for setting up, repairing,
upgrading, and optimizing a dev environment — packaged as a single **Claude Code plugin** so the
whole thing installs, versions, and updates as one unit. Every skill is **verification-first**: it
proves a change by observing real behavior, not by reading code.

Each skill lives in `skills/<name>/` with a `SKILL.md` (entry point) plus `reference/` and `scripts/`.
The plugin also ships a **hook** (see below) and a shared settings store the skills read
(`~/.config/devenv/config.toml`, managed by the `devenv` skill).

## Skills

| Skill | What it does |
|---|---|
| [**nvim-config**](skills/nvim-config/) | Set up, repair, upgrade, and optimize a Neovim configuration — lazy.nvim-first, every change verified by driving headless Neovim. |
| [**shell-sync**](skills/shell-sync/) | Set up, repair, upgrade, and optimize the zsh↔fish sync (mirror one canonical shell's env/PATH/aliases into the other) and keep PATH healthy — verified by resolving both shells and comparing. |
| [**dotfiles**](skills/dotfiles/) | Set up, repair, upgrade, and optimize configs with chezmoi — version-control one git-backed source, sync across machines, bootstrap a new machine, and keep secrets out of git (their plaintext never enters the model's context). |
| [**brew-doctor**](skills/brew-doctor/) | Find, set up, repair, upgrade, and optimize Homebrew safely — search + choose the best install for a need, a reproducible Brewfile, gated upgrades, and detection/taming of silent auto-upgrades so a background `brew upgrade` never breaks your tools. |
| [**runtime-versions**](skills/runtime-versions/) | Find, set up, repair, upgrade, and optimize language runtimes with one tool — mise — instead of nvm/asdf/pyenv/homebrew-node fighting over PATH; choose the right version, migrate off the sprawl, fix per-shell `node`-differs bugs, and keep versions current. |
| [**macos-defaults**](skills/macos-defaults/) | Set up, repair, upgrade, and optimize a Mac's system preferences as idempotent `defaults` code — capture prefs into a declarative script, apply on any machine, fix settings that won't stick, and audit for drift, each proven by re-reading it. |
| [**ghostty-config**](skills/ghostty-config/) | Set up, repair, upgrade, and optimize your Ghostty terminal config as a version-controlled file — font (with Nerd-Font glyphs), theme, default shell, keybinds — the macOS-robust way (real config in `~/.config`, pulled in via a `config-file` include so it isn't silently overridden), each change proven with `ghostty +validate-config` and `+show-config`. |
| [**terminal-theme**](skills/terminal-theme/) | Coordinate one visual theme across Ghostty, fish, zsh, and starship so they never clash — the "inherit" model makes the shells + prompt use ANSI color names that follow Ghostty's theme, so changing one line re-themes the whole terminal. Verified by auditing each surface for hardcoded hex and rendering the shared ANSI palette. |
| [**git-setup**](skills/git-setup/) | Set up, repair, upgrade, and optimize global git — signing, pager, defaults, aliases, and work-vs-personal identities — verified so commits actually verify and identities resolve. |
| [**ssh-config**](skills/ssh-config/) | Set up, repair, upgrade, and optimize `~/.ssh/config` + key hygiene, and generate/rotate ed25519 keys — treating private keys as secrets that never leave the machine or enter the model's context. |
| [**devenv**](skills/devenv/) | **Capstone.** A shared settings store the other skills read (`~/.config/devenv/config.toml`), plus ordered cross-skill runbooks — bootstrap a new machine end-to-end and run a whole-environment health sweep. Delegates to the skills above. |

The layer skills each manage one layer and stand alone. **`devenv`** sits on top: it holds the
settings they read and the runbooks that sequence them.

## The hook

The plugin ships one **`Stop` hook** ([`hooks/hooks.json`](hooks/hooks.json) →
[`scripts/chezmoi_drift_check.py`](scripts/chezmoi_drift_check.py)): when Claude finishes a response,
if any **chezmoi-managed dotfile has drifted** (e.g. a skill just edited a config in `~/.config`), it
prints a one-line reminder to sync. It is **non-blocking** and never writes, commits, or pushes —
you decide when to `/dotfiles` (or `chezmoi re-add` + commit). It stays silent when everything is in sync.

## Install

### As a plugin (recommended)

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills

# Load it for a session (great for local dev — picks up repo edits live):
claude --plugin-dir ~/codebase/claude-skills

# Or add the bundled marketplace and install it persistently:
/plugin marketplace add ~/codebase/claude-skills
/plugin install devenv
```

Installed as a plugin, skills are namespaced by the plugin: `/devenv:ghostty-config`,
`/devenv:shell-sync`, … (or just describe your task and the matching skill auto-activates), and the
hook is active. Validate the plugin structure with `claude plugin validate ~/codebase/claude-skills`.

### A single skill (un-namespaced)

Prefer one skill without the plugin? Symlink its directory into your skills folder — the command name
comes from the **directory name**, so keep it intact (`/ghostty-config`):

```bash
ln -s ~/codebase/claude-skills/skills/ghostty-config ~/.claude/skills/ghostty-config
```

Note: the `Stop` hook ships with the *plugin*, so a symlink-only install does not activate it.

## Conventions

Skills in this gallery aim to be:

- **Verification-first** — prove changes by observing real behavior, not by reading code.
- **Progressive-disclosure** — a small always-on `SKILL.md` that hands off to `reference/` files
  loaded only when needed.
- **Scripts, not inline bash** — mechanical commands live in each skill's `scripts/` as tested,
  read-only helpers the workflow calls by name.
- **Standing instructions, not one-time scripts** — every line earns its place in context.

## Contributing

Issues and PRs welcome. New skills go in `skills/<name>/` and should follow the conventions above;
improvements to existing skills should include the verification that proves them.

## License

[MIT](LICENSE) — applies to all skills in this repository.
