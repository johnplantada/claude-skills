# git-setup — set up, repair, upgrade, and optimize your global git, and prove it works

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that **sets up, repairs, upgrades,
and optimizes** your **global** git configuration: commit signing, a readable pager, sane defaults,
aliases, a global gitignore, and work-vs-personal identities. Its golden rule is
**verification-first** — it makes a test commit and confirms the signature actually verifies, the
identity resolves, and delta renders, rather than just writing config and hoping.

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Apply recommended settings, set up **SSH commit signing** (with an `allowedSignersFile` that actually verifies), install/enable **delta**, add aliases and a global gitignore, and (for work+personal) per-directory identities via `includeIf`. |
| **repair** | Fix a broken setup — commits signed but showing **unverified**, the **wrong identity** resolving in a repo, or HTTPS re-prompting for a password. |
| **upgrade** | Adopt newer git defaults (`push.autoSetupRemote`, `zdiff3`, `rebase.updateRefs`…) as git ships them, and refresh git/delta. |
| **optimize** | Review `git config --global --list --show-origin` — signing, pager, aliases, sane defaults, global gitignore, credential helper — and get a **prioritized gap report** (🔴/🟡/🟢). |

Work-vs-personal identities (`includeIf` conditional includes) live in
[`reference/identity.md`](reference/identity.md), a supporting reference used by **setup** and **repair**.

## Why it's different

Most "set up git" guides stop at writing config — which is exactly where the classic trap lives: a
commit that's **signed but doesn't verify** because the `allowedSignersFile` was never set. This
skill treats setting config as the *start*, not the finish:

- **Proves signing verifies** — makes a real test commit and reads `git log --show-signature`,
  catching the signed-but-unverifiable gap.
- **Proves identity resolves** — evaluates config from inside a work repo (`git -C ~/work/… config
  user.email`) so the `includeIf` is confirmed, not assumed.
- **Read-only by default** — its pre-approved tools are read-only; every mutating `git config`
  change is proposed, and it backs up `~/.gitconfig` first.
- **Coordinates, doesn't duplicate** — SSH signing reuses your key (`ssh-config`), and configs are
  tracked via `dotfiles`/chezmoi (public key + allowed signers only — **never** the private key).

## Requirements

- **Claude Code**, plus **git**. macOS or Linux (SSH signing + osxkeychain preferred on macOS).
- **delta** (`git-delta`, via Homebrew) for the pager workflow — installed on demand.

## Install

Part of the [claude-skills](../) gallery:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/git-setup ~/.claude/skills/git-setup
```

## Usage

```
/git-setup setup        # settings + SSH signing + delta + gitignore (+ identities), then verify
/git-setup repair       # signed-but-unverified, wrong identity, HTTPS re-prompts
/git-setup upgrade      # adopt newer git defaults + refresh git/delta
/git-setup optimize     # global config health + prioritized gap report
```

Or describe it — "why aren't my commits verified", "set up ssh commit signing", "separate my work
and personal git email", "make git diffs readable" — and it routes to the right workflow.

```
git-setup/
├── SKILL.md                 # router + discovery + verification-first principles
├── reference/
│   ├── setup.md             # settings + SSH signing + delta + aliases + gitignore
│   ├── repair.md            # signed-but-unverified, wrong identity, cred re-prompts
│   ├── upgrade.md           # adopt newer git defaults + refresh tooling
│   ├── optimize.md          # global config review -> prioritized gap report
│   ├── identity.md          # work vs personal via includeIf (supporting reference)
│   └── verification.md      # test commit -> show-signature; identity resolution; delta renders
└── README.md                # (LICENSE lives at the gallery root)
```

## License

[MIT](../LICENSE).
