# devenv — a Claude Code plugin

[![tests](https://github.com/johnplantada/claude-skills/actions/workflows/test.yml/badge.svg)](https://github.com/johnplantada/claude-skills/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)

A gallery of [Claude Code](https://claude.com/claude-code) **Agent Skills** that set up, repair,
upgrade, and optimize a dev environment — Homebrew, language runtimes, dotfiles, shells, the terminal,
Neovim, git, and ssh — packaged as **one plugin** so the whole thing installs and versions as a unit.

Every skill is **verification-first**: it proves a change by observing real behavior (validating a
config, re-reading a value, resolving both shells), never by trusting that an edit did what it meant.

## Architecture

Three tiers. A capstone holds the whole-machine coordination knowledge; **goal skills** each own one
outcome that no single layer can deliver alone; layer skills each own exactly one concern and are the
only things that mutate it. A shared library and settings store keep them consistent.
*One brain, many hands.*

```mermaid
graph TD
    you([You: one request]) --> cc[Claude Code agent]
    cc -->|routes by skill description| G
    cc -->|routes by skill description| L
    cc -->|whole-machine goals| cap
    cap[["devenv · capstone<br/>bootstrap + health runbooks"]] -. sequences .-> L

    subgraph G["goal skills — one outcome, spanning layers"]
        th[terminal-theme]
        idp[identity-profiles]
        cs[credential-store]
    end

    subgraph L["layer skills — one per environment concern"]
        brew[brew-doctor]
        rt[runtime-versions]
        dot[dotfiles]
        shell[shell-sync]
        gh[ghostty-config]
        nv[nvim-config]
        git[git-setup]
        ssh[ssh-config]
        mac[macos-defaults]
    end

    G -. coordinates, never mutates .-> L
    L -->|read| cfg[("~/.config/devenv/config.toml<br/>shared settings")]
    L -->|import| lib["lib/devenv_common.py<br/>shared primitives"]
    cc -. Stop hook .-> hook{{"chezmoi dotfiles-drift reminder"}}
    cc -. PreToolUse .-> guard{{"secret-read guard:<br/>denies reading private keys,<br/>.netrc, credentials"}}
```

**What makes a goal skill** (rather than another layer): it names a user-visible outcome, no single
layer can deliver it, it has a *source-of-truth model* the other surfaces derive from, it can detect
the specific drift that breaks that model, and it declares its boundaries with the layers it spans.
`terminal-theme` inherits from the Ghostty theme; `identity-profiles` derives from the directory
tree; `credential-store` resolves from one store. Anything missing the model or the detector is a
runbook, and belongs in `devenv`.

## Skills

| Skill | What it does |
|---|---|
| [**brew-doctor**](skills/brew-doctor/) | Find, set up, repair, upgrade, and optimize Homebrew safely — search + choose the best install, a reproducible Brewfile, gated upgrades, and taming of silent auto-upgrades so a background `brew upgrade` never breaks your tools. |
| [**runtime-versions**](skills/runtime-versions/) | Manage language runtimes with one tool — mise — instead of nvm/asdf/pyenv fighting over PATH; migrate off the sprawl and fix per-shell `node`-differs bugs. |
| [**dotfiles**](skills/dotfiles/) | Version-control your configs with chezmoi, sync across machines, bootstrap a new machine, and keep secrets out of git (metadata-only handling is the required workflow). |
| [**shell-sync**](skills/shell-sync/) | Keep zsh ↔ fish consistent (mirror one canonical shell's env/PATH/aliases/prompt into the other) and keep PATH healthy — verified by resolving both shells and comparing. |
| [**ghostty-config**](skills/ghostty-config/) | Manage your Ghostty config as a version-controlled file — the macOS-robust way (real config in `~/.config`, pulled in via a `config-file` include so it isn't silently overridden), proven with `ghostty +validate-config`. |
| [**terminal-theme**](skills/terminal-theme/) | Coordinate one theme across Ghostty, fish, zsh, and starship so they never clash — the "inherit" model makes them follow Ghostty's ANSI palette, so one edit re-themes the whole terminal. |
| [**nvim-config**](skills/nvim-config/) | Set up, repair, upgrade, and optimize a Neovim config — lazy.nvim-first, every change verified by driving headless Neovim. |
| [**git-setup**](skills/git-setup/) | Configure global git — signing, pager, defaults, and work-vs-personal identities — verified so commits actually verify and identities resolve. |
| [**identity-profiles**](skills/identity-profiles/) | Coordinate *who you are* per directory tree across git, ssh, signing, and gh — catching the two silent failures no single layer can see: right email + wrong key, and signed-but-Unverified for the second identity. |
| [**credential-store**](skills/credential-store/) | Get credentials off disk and into one store, so configs *reference* a secret instead of embedding it — classifying every assignment literal vs. reference, using metadata-only helpers to keep values out of model output. |
| [**ssh-config**](skills/ssh-config/) | Clean up `~/.ssh/config` + key hygiene and generate/rotate ed25519 keys — using metadata-only key audits and keeping private-key values out of model output. |
| [**macos-defaults**](skills/macos-defaults/) | Capture a Mac's preferences into idempotent `defaults` code, apply on any machine, and audit for drift — each setting proven by re-reading it. |
| [**devenv**](skills/devenv/) 🧭 | **Capstone.** The shared settings store the others read, plus ordered cross-skill runbooks — bootstrap a machine end-to-end and run a whole-environment health sweep. Delegates down; never duplicates a layer's logic. |

## Anatomy of a skill

Each skill is small always-on routing that hands off to detailed workflows and tested Python helpers.

```mermaid
graph LR
    req([task]) --> md["SKILL.md<br/>router + principles"]
    md --> ref["reference/*.md<br/>setup · repair · upgrade · optimize"]
    ref --> py["scripts/*.py<br/>typed helpers"]
    py -->|pure logic| test["./check · unit + fixtures · CI"]
    py -->|subprocess + IO| lib["lib/devenv_common.py"]
    ref ==>|verification-first| proof{{"prove it by observing<br/>real behavior, not reading code"}}
```

## Design principles

- **Verification-first** — prove a change by observing real behavior, not by reading code.
- **Progressive disclosure** — a small always-on `SKILL.md` routes to `reference/` workflows loaded
  only when needed, so context stays cheap.
- **Tested Python, not inline bash** — mechanical work lives in each skill's `scripts/*.py` as typed,
  stdlib-only helpers with **pure logic separated from subprocess/IO**, so it's directly unit-tested.
- **One brain** — coordination knowledge (ordering, the settings contract) lives only in `devenv`;
  the layer skills never fork it.
- **Keep secrets out of context** — metadata-only helpers and skill instructions are the required
  workflow. The plugin's `PreToolUse` guard denies recognized secret-by-location paths for `Read`,
  explicit-file `Grep`, and supported direct Bash readers. It is deliberately narrow and fails open
  on unexpected input; it does not cover arbitrary shell/Python reads, directory-wide searches, or
  secrets embedded in ordinary files. This is defense in depth, not a guarantee of containment.
- **Reports say how they know** — a fact that depends on which environment was asked carries
  `src=login-shell` or `src=this-process`; a line a parser couldn't read is emitted as `unparsed`
  rather than silently dropped; a check that couldn't run says `undetermined` instead of looking
  clean. All three exist because the alternative shipped confident, wrong findings.

## Testing & CI

One entry point, `./check`. The tiers cost very different amounts, so they're opt-in by flag
rather than all-or-nothing:

```bash
./check              # lint + unit tests — free, ~1s. Run this before every commit.
./check --smoke      # + every read-only entry point, on this machine — free, ~1 min, macOS
./check --evals      # + LLM skill evals — SPENDS TOKENS, several minutes
./check --all        # everything
./check --capture    # refresh tests/fixtures/ from this machine's real tool output
```

Why four tiers, when most repos have one — each catches something the others structurally cannot:

| Tier | Proves |
|---|---|
| **unit** ([`tests/`](tests/)) | pure logic, plus docs↔scripts consistency (a renamed script breaks the build) |
| **fixtures** ([`tests/fixtures/`](tests/fixtures/)) | parsers handle what tools *actually* print — recorded output, not invented strings |
| **smoke** ([`tests_smoke/`](tests_smoke/)) | entry points really run against real tools, and still emit their key facts |
| **evals** ([`tests_eval/`](tests_eval/)) | direct skill-following behavior via explicit `SKILL.md` prompts, graded by deterministic transcript checks; does not verify installed-plugin routing or hooks |

Pure functions are tested directly — no mocking — and every past bug is pinned as a regression
test. [GitHub Actions](.github/workflows/test.yml) runs lint + unit on every push, and smoke on
macOS (both CI jobs currently use Python 3.12). Helpers declare Python 3.9+; the optional
settings-validation examples require Python 3.11+ for stdlib `tomllib`. The declared minimum
has not been verified by a CI matrix. An explicitly selected eval tier with zero executed tests
fails instead of reporting a pass. Eval receipts record revision/dirty state, platform, Python,
CLI version, outcomes and skipped counts in `tests_eval/results/`; preserve the matching diff
when the revision is dirty. See [installed-plugin acceptance](docs/plugin-acceptance.md).

## Install

### As a plugin (recommended)

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills

# Load it for a session (great for local dev — picks up repo edits live):
claude --plugin-dir ~/codebase/claude-skills

# …or add the bundled marketplace and install it persistently:
/plugin marketplace add ~/codebase/claude-skills
/plugin install devenv
```

Installed, skills are namespaced by the plugin (`/devenv:ghostty-config`, `/devenv:shell-sync`, …) —
or just describe your task and the matching skill auto-activates — and the Stop hook is active.
Validate the structure with `claude plugin validate ~/codebase/claude-skills`.

### A single skill

Prefer one skill without the plugin? Symlink its directory — the command name comes from the
directory name (`/ghostty-config`):

```bash
ln -s ~/codebase/claude-skills/skills/ghostty-config ~/.claude/skills/ghostty-config
```

**A symlink-only install activates neither plugin hook:** the `Stop` drift reminder nor the
`PreToolUse` secret-read guard. Use the plugin install when you need those protections.

## The hooks

The plugin ships a **`PreToolUse` secret-read guard** and a **`Stop` drift reminder**.
The guard's scope and limitations are described above; its implementation is
[`scripts/secret_read_guard.py`](scripts/secret_read_guard.py).

The **`Stop` hook** ([`hooks/hooks.json`](hooks/hooks.json) →
[`scripts/chezmoi_drift_check.py`](scripts/chezmoi_drift_check.py)): when Claude finishes a response,
if a chezmoi-managed dotfile has drifted (a skill just edited a config), it prints a one-line reminder
to sync. It is **non-blocking** and never writes, commits, or pushes — you decide when. Silent when in sync.

## Repository layout

```
├── check                  ONE entry point for every tier (./check --help)
├── requirements-dev.txt   pytest + ruff, pinned exactly (CI installs from here)
├── .claude-plugin/        plugin.json + marketplace.json
├── skills/<name>/         SKILL.md · reference/*.md · scripts/*.py
├── lib/devenv_common.py   shared Python primitives + output conventions
├── scripts/               plugin hooks (drift reminder, secret-read guard) + fixture capture
├── tests/                 unit suite (mirrors skills/) + fixtures/ of real tool output
├── tests_smoke/           entry points run against real tools (macOS)
├── tests_eval/            LLM skill evals, opt-in (spends tokens)
└── .github/workflows/     CI (runs ./check)
```

## Contributing

Issues and PRs welcome. New skills go in `skills/<name>/` and follow the principles above; changes to
existing skills should include the test that proves them (`pytest` must stay green).

## License

[MIT](LICENSE).
