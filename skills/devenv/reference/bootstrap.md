# Bootstrap workflow — set up a new machine end-to-end

Goal: take a fresh machine to a working dev environment by running the gallery's skills **in the
right order with the right gates**. This runbook only sequences and hands off — each step's real
work (and verification) belongs to the named skill.

Confirm scope with the user first (this touches every layer). Read `[*]` from
`~/.config/devenv/config.toml` so steps don't stop to ask.

## Order (each arrow is a gate — don't proceed until the prior step verifies)

1. **Prerequisites** — Xcode Command Line Tools (`xcode-select --install`), then install Homebrew.
   Verify: `brew --version` and `git --version` (git ships with the CLT).

2. **Bootstrap the dotfiles tool** — `brew install chezmoi`. (You need it before you can pull
   configs.) Verify: `chezmoi --version`.

3. **SSH keys** → delegate to **`ssh-config`** (keys). Generate an `ed25519` key (algorithm from
   `[ssh-config].key_type`), add it to the agent + keychain, and **register the PUBLIC key with
   GitHub**. This must come *before* the dotfiles pull: a private dotfiles repo over SSH can't
   authenticate without it, and git commit signing (step 6) reuses this key.
   ⚠️ Gate: if you can't register a key yet, clone the dotfiles repo over **HTTPS** instead and
   circle back. Verify: `ssh -T git@github.com` authenticates.

4. **Dotfiles** → delegate to **`dotfiles`** (setup → new-machine bootstrap).
   `chezmoi init --apply <repo>` pulls shell/editor/git configs **and the Brewfile**.
   ⚠️ Gate: **secrets prerequisites first** — the `age`/`gpg` key or password-manager must be
   present, or encrypted/templated files fail to apply. Verify: `chezmoi status` empty.

5. **Packages** → delegate to **`brew-doctor`** (setup). `brew bundle --file="$brewfile"` installs
   everything the (now-present) Brewfile declares (incl. `mise`, `tree-sitter`, formatters, LSPs).
   Then apply intent from settings: pin the `[brew-doctor].pinned` formulae and confirm
   `autoupdate_mode`. Verify: `brew bundle check`.

6. **Git identity & signing** → delegate to **`git-setup`** (setup). Harden the global
   config that dotfiles brought, set signing (`[git-setup].signing` — SSH signing reuses the step-3
   key) and any work/personal `identities`. Verify: a signed test commit shows `Good "git" signature`
   and the right identity resolves per directory.

7. **Runtimes** → delegate to **`runtime-versions`** (setup/upgrade). Activate `mise` and install
   the global `[runtime-versions].tools` (e.g. `node = "lts"`, `python`). Verify: `mise doctor` clean
   and `mise which node`/`python` resolve to mise shims.

8. **Shells** → delegate to **`shell-sync`** (setup). With `[shell-sync].canonical` known, regenerate
   the mirror shell's managed include from the canonical config (now including brew + mise
   activation). Set the login shell if desired. Verify: both shells resolve the same PATH and start
   clean.

9. **Editor** → delegate to **`nvim-config`** (setup/repair as needed). Install treesitter parsers
   (needs the `tree-sitter` CLI — step 5) and LSP servers (mason, needing node/python from step 7),
   then verify headlessly. Verify: files highlight, LSP attaches, no deprecations.

10. **macOS defaults** → delegate to **`macos-defaults`** (upgrade). Apply the declarative
    `[macos-defaults].script`, then restart affected apps (Dock, Finder). Verify: each written key
    reads back the expected value.

11. **Terminal** → delegate to **`ghostty-config`** (setup/upgrade). `chezmoi apply` the tracked
    `~/.config/ghostty/config`, then write the macOS Library `config-file` include so it's
    authoritative, and install any Nerd Font it references (`brew install --cask font-…-nerd-font`).
    Depends on the shell (step 8, for `command = <shell> --login`) and the font cask (step 5).
    Verify: `ghostty +validate-config` passes, `ghostty_doctor.py` is `in_sync yes`, `font_check.py`
    shows the font `resolved`.

12. **Final sweep** → run [health.md](health.md) to confirm every layer is green.

## Notes

- Steps 3→4 order matters: SSH auth must work before a private dotfiles repo will clone.
- Steps 4→5 order matters: chezmoi brings the Brewfile, then `brew bundle` installs from it.
- Steps 5→7→8→9 order matters: brew installs `mise`/`tree-sitter`, mise installs the runtimes,
  shell-sync mirrors the resulting activation, and nvim's LSP needs those runtimes on PATH.
- If a step fails, stop and hand to that skill's **repair** path — don't push past a red gate.
- Everything here is idempotent by virtue of the underlying skills; re-running resumes safely.

## Report

A short per-layer checklist (✓/✗ with the verifying evidence) and anything that still needs the
user (a login-shell change, a secret key to transfer, a GUI installer to click through).
