# ssh-config — set up, repair, upgrade & optimize ~/.ssh/config and key hygiene, without ever leaking a key

A [Claude Code](https://claude.com/claude-code) **Agent Skill** that **sets up, repairs, upgrades,
and optimizes** your SSH setup: build a structured hardened `~/.ssh/config`, fix failing auth,
modernize hardening, audit key hygiene, and generate / rotate keys — all while treating the
**private key as a secret that never leaves the machine or enters the model's context**. Every change
is verified: the config actually resolves (`ssh -G`) and auth actually works (`ssh -T`).

## What it does

| Workflow | Use it to… |
|---|---|
| **setup** | Build a clean `~/.ssh/config`: global defaults, per-`Host` blocks, `Include ~/.ssh/config.d/*`, sensible hardening. Backs up first, fixes perms. |
| **repair** | Fix failing auth — loose perms (key not offered), an empty agent, the wrong `Host` matching, "too many authentication failures", or a `known_hosts` mismatch. |
| **upgrade** | Harden/modernize the config (`IdentitiesOnly`, `UseKeychain`, `HashKnownHosts`…), drop weak/deprecated settings, and move off weak key types. |
| **optimize** | Review Host blocks and key hygiene — **permissions**, key **types** (prefer ed25519), **passphrases**, loaded agent identities, `known_hosts` — prioritized 🔴/🟡/🟢. Never prints key contents. |
| **keys** | Generate ed25519 keys (passphrase in the keychain), add to the agent + macOS keychain, set per-host identities, rotate safely, and register the **PUBLIC** key with GitHub. |

## Why it's different

Most SSH advice edits the config and stops. This skill's discipline is elsewhere:

- **Secrets discipline first.** A private key is a secret — the skill only ever surfaces a key's
  *filename, type, and permissions*, **never its contents**. Its `allowed-tools` list is read-only
  and cannot read a private key. Public keys (`.pub`) only for anything that leaves the machine.
- **Verification-first.** A change isn't done until `ssh -G` shows the effective config resolving as
  intended **and** `ssh -T` / `BatchMode=yes` proves auth works — tested *before* an old key or Host
  is removed, so working access never breaks.
- **Perms are load-bearing.** ssh silently ignores a key/config with loose permissions; the skill
  treats `700/600/644` as mandatory, not cosmetic.
- **Plays with the gallery.** Config + public keys are tracked via `dotfiles` (chezmoi); private
  keys are `.chezmoiignore`d or age-encrypted — never plaintext in git. Keys back `git-setup`.

## Requirements

- **Claude Code**, plus **OpenSSH** (`ssh`, `ssh-keygen`, `ssh-add`). macOS-aware (`UseKeychain`,
  `--apple-use-keychain`); works on Linux minus the keychain bits. `gh` optional (GitHub key registration).

## Install

Part of the [claude-skills](../) gallery:

```bash
git clone https://github.com/johnplantada/claude-skills ~/codebase/claude-skills
ln -s ~/codebase/claude-skills/ssh-config ~/.claude/skills/ssh-config
```

## Usage

```
/ssh-config setup       # clean, structured, hardened ~/.ssh/config
/ssh-config repair      # fix failing auth: perms, agent, Host match, known_hosts
/ssh-config upgrade     # harden/modernize config, move off weak key types
/ssh-config optimize    # config + key-hygiene report, prioritized
/ssh-config keys        # generate / add / rotate keys, register with GitHub
```

Or describe it — "audit my ssh setup", "why won't my key work", "make a new ed25519 key for this
server", "clean up my ssh config" — and it routes to the right workflow.

```
ssh-config/
├── SKILL.md                 # router + discovery + secrets/verification principles
├── scripts/                 # the stable toolbox (metadata only — never key material)
│   ├── key_audit.py         # per-key perms/type/passphrase/agent + strength verdict
│   ├── ssh_config_audit.py  # config perms + Host blocks + Include + ssh -G resolve
│   ├── agent_status.py      # loaded identities vs on-disk *.pub
│   ├── key_new.py           # (mutating) generate ed25519 + load + show .pub
│   └── README.md            # toolbox table + secrets rule + conventions
├── reference/
│   ├── setup.md             # global defaults + per-Host + Include + hardening
│   ├── repair.md            # failing auth: perms, agent, Host match, known_hosts
│   ├── upgrade.md           # harden/modernize config + move off weak key types
│   ├── optimize.md          # perms + key types + passphrases + agent + config quality
│   ├── keys.md              # generate ed25519 + keychain + GitHub + rotation
│   └── verification.md      # ssh -G resolves + ssh -T auth + perms + agent
└── README.md                # (LICENSE lives at the gallery root)
```

## License

[MIT](../LICENSE).
