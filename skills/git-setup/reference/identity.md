# Identity workflow — work vs personal via conditional includes

Goal: the right `user.email` (and signing key) automatically, based on which directory a repo lives
in — no per-repo `git config` and no accidental commits under the wrong identity. Confirm before
altering global identity/email.

## The shape

`~/.gitconfig` keeps a **neutral or personal** identity, then pulls in a per-directory file with
`includeIf "gitdir:…"`. The include wins for repos under that path.

```ini
# ~/.gitconfig  (personal is the default)
[user]
    name  = Bobby Babada
    email = you@personal.example

[includeIf "gitdir:~/work/"]
    path = ~/.config/git/work.gitconfig

[includeIf "gitdir:~/personal/"]
    path = ~/.config/git/personal.gitconfig
```
- The **trailing slash** matters: `gitdir:~/work/` matches repos anywhere under `~/work/`.
- Includes are evaluated **top to bottom**; a later match overrides an earlier value.

## Each identity file sets its own email + signing key

```bash
mkdir -p ~/.config/git

cat > ~/.config/git/work.gitconfig <<'EOF'
[user]
    email = you@work.example
    signingkey = ~/.ssh/id_ed25519_work.pub
EOF

cat > ~/.config/git/personal.gitconfig <<'EOF'
[user]
    email = you@personal.example
    signingkey = ~/.ssh/id_ed25519.pub
EOF
```
If each identity signs with a different SSH key, add **both** email→pubkey lines to
`~/.config/git/allowed_signers` (coordinate with **ssh-config**) so commits under either identity
verify locally:
```bash
printf '%s %s\n' "you@work.example" "$(cat ~/.ssh/id_ed25519_work.pub)" >> ~/.config/git/allowed_signers
printf '%s %s\n' "you@personal.example"   "$(cat ~/.ssh/id_ed25519.pub)"      >> ~/.config/git/allowed_signers
```

## Verify the right identity resolves per directory

> **Run [`scripts/git_identity.py <path>`](../scripts/git_identity.py)** for each tree — it
> evaluates the effective config from inside that path (so `includeIf gitdir:` is applied exactly
> as git sees it), prints the resolved email + signing key, and **names the file each came from**.
>
> ```bash
> scripts/git_identity.py ~/work/some-repo      # -> user.email you@work.example, user.email_from …/work.gitconfig
> scripts/git_identity.py ~/personal/some-repo  # -> user.email you@personal.example
> ```

Under the hood it evaluates the config **from inside** a repo in each tree:

```bash
git -C ~/work/some-repo    config user.email     # -> you@work.example
git -C ~/personal/some-repo config user.email    # -> you@personal.example
git -C ~/work/some-repo config --show-origin user.email   # which file supplied it
```
`git config --show-origin` names the include file that won — the definitive check that the
`includeIf` matched (`git_identity.py` reports it as `user.email_from`). See
[verification.md](verification.md) for the full identity-resolution proof and a signed test commit
under each identity.

## Track it

Version `~/.gitconfig` and both `~/.config/git/*.gitconfig` files via the **dotfiles** skill. These
hold emails and **public** key paths only — safe to track. Private keys stay in `~/.ssh`, untracked.
