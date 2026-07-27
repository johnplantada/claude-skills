# Setup workflow — declare profiles, then make every surface follow

Goal: each directory tree gets one identity, applied automatically, with **git, ssh, signing, and
gh in agreement**. Work in this order — the map first, then one surface at a time, then proof.

## 0. Audit before changing anything

```bash
scripts/profile_audit.py
```
`profiles (none…)` is the greenfield case this workflow handles. If profiles already exist, you are
in [upgrade.md](upgrade.md) (adding one) or [repair.md](repair.md) (fixing one).

---

## 1. Establish the profile map — the one step worth a subagent

Everything else in this skill is deterministic, but *this* step is not: it means reading a sprawling
`~/.ssh/config`, the layout of the user's code directories, any existing `includeIf` rules, and
`gh auth status`, then inferring **which trees are which identity**. That's judgment over unbounded,
unparseable input whose answer is a four-row table — the one shape where a subagent pays for itself.

Spawn **one** subagent with read-only tools:

> Inspect this machine and propose an identity profile map. Read `~/.ssh/config` (all `Host` blocks
> and their `IdentityFile`s), `git config --global --get-regexp '^includeif\.'`, `gh auth status`,
> and the directory layout two levels under the user's code roots (`~/`, `~/code`, `~/codebase`,
> `~/work`, `~/projects` — whichever exist). For each identity you can infer, report: a short name,
> the directory tree that should map to it, the email if discoverable, the ssh key that appears
> intended for it, and an existing `Host` alias if there is one. Also list repos whose `origin`
> disagrees with the tree they sit in. Return a table plus a one-line rationale per row. Propose
> only — change nothing, and do not read any private key file.

Then **confirm the table with the user before writing anything.** The subagent proposes; the user
decides; the deterministic steps below execute. Do not let it perform step 2 onward — those are
`git config` and file edits that must be reproducible, not re-derived.

*If the machine is simple* (one obvious work tree, one personal), skip the subagent and just ask.
A context prime is not worth saving one question.

---

## 2. git — one `includeIf` per tree

The neutral/personal identity stays in `~/.gitconfig`; each tree pulls in its own file. Full
mechanics and the trailing-slash rule: **`git-setup`'s [identity.md](../../git-setup/reference/identity.md)**
— don't duplicate it here.

```ini
# ~/.gitconfig
[user]
    name  = <name>
    email = <personal@example.com>

[includeIf "gitdir:~/work/"]
    path = ~/.config/git/work.gitconfig
```

```bash
mkdir -p ~/.config/git
cat > ~/.config/git/work.gitconfig <<'EOF'
[user]
    email = you@work.example
    signingkey = ~/.ssh/id_ed25519_work.pub
EOF
```

Back up `~/.gitconfig` first. The **trailing slash** on the gitdir pattern is required.

## 3. ssh — one `Host` alias per profile

A per-tree key only takes effect if remotes address an alias that pins it:

```sshconfig
Host github-work
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_work
    IdentitiesOnly yes
```

`IdentitiesOnly yes` matters: without it ssh offers every agent key and the server accepts the
first that works — usually the wrong one. Key **creation** belongs to `ssh-config`'s keys workflow;
this step only wires an existing key to an alias.

## 4. signing — pair each identity in `allowed_signers`

Each profile signs with its own key, so each needs its own pairing line, or its commits sign and
show **Unverified**:

```bash
printf '%s %s\n' "you@work.example" "$(cat ~/.ssh/id_ed25519_work.pub)" >> ~/.config/git/allowed_signers
```

Confirm `gpg.ssh.allowedSignersFile` points at that file (`git-setup` owns that setting).

## 5. Point existing remotes at the alias

An https remote — or an ssh remote using the bare hostname — bypasses per-alias key selection:

```bash
git -C <repo> remote set-url origin git@github-work:<owner>/<repo>.git
```

Do this for the repos the map flagged in step 1. Confirm each with the user; changing a remote is
easy to reverse but not something to batch silently.

## 6. Prove it

```bash
scripts/profile_audit.py          # every profile, every surface — expect no 🔴
```
Then follow [verification.md](verification.md) for the per-profile proof (a signed test commit that
actually verifies, and the optional network probe). A profile is not set up until the audit is
clean *and* a commit under it verifies.

## 7. Track it

`~/.gitconfig`, `~/.config/git/*.gitconfig`, `~/.config/git/allowed_signers`, and `~/.ssh/config`
are all dotfiles — version them via the **dotfiles** skill so the profile map survives the next
machine. They contain emails and **public** keys only; private keys stay untracked.
