# Set up workflow — configure settings, signing, delta, gitignore

Goal: stand up a hardened `~/.gitconfig` — recommended defaults, SSH commit signing, delta, a global
gitignore. **Back it up first**, propose each change, and finish by **proving it works**
([verification.md](verification.md)). Every `git config --global <key> <val>` is mutating — confirm
before running.

> Work + personal repos needing different emails/keys? Set up per-directory identities:
> [identity.md](identity.md). Keeping config current as git adds better defaults → [upgrade.md](upgrade.md).
> Signing configured but commits show unverified → [repair.md](repair.md).

## 0. Back up

```bash
cp ~/.gitconfig ~/.gitconfig.bak                 # restore point before any global edit
```

## 1. Sane defaults

```bash
git config --global init.defaultBranch main
git config --global pull.rebase true
git config --global push.autoSetupRemote true
git config --global push.default simple
git config --global fetch.prune true
git config --global rebase.autostash true
```

## 2. Global gitignore

```bash
cat > ~/.gitignore_global <<'EOF'
.DS_Store
*.swp
*.swo
.idea/
.vscode/
*.log
.env
.env.local
EOF
git config --global core.excludesfile ~/.gitignore_global
```

## 3. Credential helper (macOS)

```bash
[ "$(uname -s)" = Darwin ] && git config --global credential.helper osxkeychain
```

## 4. Commit signing — prefer SSH on macOS

SSH signing reuses your existing SSH key (coordinate with the **ssh-config** skill). **Confirm before
changing signing** — it changes whether commits show as "Verified" on GitHub.

```bash
# a) point git at your PUBLIC key (never the private key)
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true

# b) allowedSignersFile — REQUIRED for `git log --show-signature` to verify locally.
#    maps: <email> <space> <public key line>
mkdir -p ~/.config/git
printf '%s %s\n' "$(git config --global user.email)" "$(cat ~/.ssh/id_ed25519.pub)" \
  >> ~/.config/git/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
```
- Add the **public** key to GitHub as a **Signing key** (Settings → SSH and GPG keys) so GitHub
  shows commits as Verified. The private key stays in `~/.ssh` and is never tracked or shared.
- **GPG instead?** `git config --global gpg.format openpgp` + `user.signingkey <KEYID>` (from
  `gpg --list-secret-keys --keyid-format=long`). SSH is simpler on macOS; use GPG only if the user
  already has a GPG identity.

## 5. Delta as the pager (via Homebrew)

```bash
command -v delta || brew install git-delta       # install if missing (hand off if brew needs sudo)
git config --global core.pager delta
git config --global interactive.diffFilter 'delta --color-only'
git config --global delta.navigate true           # n/N to jump between files
git config --global merge.conflictStyle zdiff3     # better conflict markers
```

## 6. Helpful aliases

```bash
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.last 'log -1 HEAD --stat'
git config --global alias.unstage 'reset HEAD --'
git config --global alias.lg "log --graph --abbrev-commit --decorate --format=format:'%C(bold blue)%h%C(reset) %C(dim white)%an%C(reset) %C(green)(%ar)%C(reset)%C(auto)%d%C(reset) %s'"
```

## 7. Verify (do not skip)

Prove it, don't assume — **run [`scripts/verify_signing.py`](../scripts/verify_signing.py)** (no
flag) to confirm a real test commit now signs and verifies (`result ✅ GOOD signature`, status `G`,
not `N`). Then the rest of [verification.md](verification.md): `delta` rendering a diff, an alias
running, and `git config --list --show-origin` showing each value's source. Re-run
[`scripts/git_audit.py`](../scripts/git_audit.py) — the signing/pager/defaults gaps should be gone.

## Track it

Offer to version `~/.gitconfig`, `~/.gitignore_global`, and `~/.config/git/allowed_signers` via the
**dotfiles** skill (chezmoi). The **private** signing key is never tracked — public key + allowed
signers only.
