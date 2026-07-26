# Secrets workflow — never commit plaintext credentials

Dotfiles are the #1 place secrets leak into git. A managed config may hold API tokens, signing
keys, or session cookies. Handle these deliberately — never `chezmoi add` a secret-bearing file
as plaintext.

> **Hard control — a secret's plaintext is never read into this session.** Neither the skill nor its
> scripts print or ingest secret *values*: detection is `grep -l` (paths + reason only), verification
> is by exit code, ciphertext markers (`encrypted_*.age`), and unresolved `{{ ... }}` references —
> never by reading the value. Operations that need the real plaintext (creating an `age` key,
> unlocking a password manager, copying a private key to a new machine) run **out of band** — you run
> them yourself (e.g. via the `!` prefix); the value must not round-trip through the model.

## Detect (before every first-add and first-commit)

`scripts/secret_scan.py` is a **tripwire, not a comprehensive scanner** — a lightweight,
zero-dependency backstop so a skill never tracks an obvious plaintext secret, and (its whole reason
to exist) so a secret's *value* never enters this session. It prints one `<path>	reason=…` line
per finding — **never the secret value or file contents** — and exits 0 = clean, 1 = findings to
reconcile. Pass a path to scan a file/dir about to be added, or no arg to scan the source tree.

- **Content engine:** if **gitleaks** is installed it drives content detection — run with `--redact`,
  and the scanner reads only the *file* + *rule id* from its JSON, never a match/secret field.
  Otherwise a small built-in pattern set (github/slack/aws tokens, private-key blocks,
  `secret=`/`token=` assignments) is the fallback. Either way, findings are `<path>	reason=…` only.
- **Location engine (always built-in):** files that are secret-by-*location* — `.ssh/`, `.aws/`,
  `.netrc`, `gh/hosts.yml`, `*credentials*`, `.env`, chezmoi's `dot_`/`private_` encodings — stored
  as plaintext rather than `encrypted_*.age` or a template. gitleaks doesn't know chezmoi's source
  encoding, so this check stays local.

> **For real, repo-wide secret scanning, use a dedicated tool** —
> [gitleaks](https://github.com/gitleaks/gitleaks),
> [trufflehog](https://github.com/trufflesecurity/trufflehog) (adds live-secret verification), or
> [detect-secrets](https://github.com/Yelp/detect-secrets). This tripwire is a fast pre-add backstop
> with one property those aren't built for: **the value never reaches the model.**

<details><summary>Under the hood — the built-in fallback patterns (used only when gitleaks is absent)</summary>

High-signal content shapes, matched **by name only** (the matched text is never emitted):
`BEGIN [A-Z ]*PRIVATE KEY`, `AKIA[0-9A-Z]{16}`, `gh[pousr]_…`, `xox[bapr]-…`,
`(api[_-]?key|secret|token|password|passwd)[:=]`. Plus the secret-by-location paths above.
</details>

## Choose a strategy per secret

| Situation | Approach |
|---|---|
| A whole file is sensitive (private key, credentials) | **Encrypt it**: `chezmoi add --encrypt <file>` |
| A config is mostly public but has one secret value | **Template it**: pull the value from a password manager at apply time |
| A file should live on this machine only | **Ignore it**: add to `.chezmoiignore` (don't track at all) |

## Encryption (age — simplest)

```bash
# one-time: create a key and point chezmoi at it
age-keygen -o ~/.config/chezmoi/key.txt        # keep this key OUT of the repo
```
Add to `~/.config/chezmoi/chezmoi.toml`:
```toml
encryption = "age"
[age]
  identity = "~/.config/chezmoi/key.txt"
  recipient = "<age public key from keygen output>"
```
Then `chezmoi add --encrypt <file>` stores it as `encrypted_<name>.age` in the source — safe to
commit. `chezmoi apply` decrypts on this machine. The **private key never goes in the repo**;
transfer it to new machines out of band.

## Templating from a password manager

For a single secret inside an otherwise-public file, make it a `.tmpl` and reference the manager
(examples — use whichever the user has):
```
# 1Password
export GITHUB_TOKEN="{{ onepasswordRead "op://Personal/GitHub/token" }}"
# Bitwarden
export OPENAI_API_KEY="{{ (bitwardenFields "item" "OpenAI").api_key.value }}"
```
The secret is fetched at `chezmoi apply` time and never stored in git.

## `.chezmoiignore` for machine-local files

```
# in the source root — templated; supports per-host conditions
~/.config/some-tool/local-only.conf
{{ if ne .chezmoi.hostname "work-laptop" }}dot_config/work-only{{ end }}
```

## Verify no secret leaked

- `scripts/secret_scan.py` exits 0 (`clean`) against the source tree — nothing plaintext-sensitive.
- Encrypted files appear as `encrypted_*.age` (ciphertext), templated secrets appear as
  `{{ ... }}` references — never the raw value — in the committed source.
- The repo remote is **private** (`scripts/chezmoi_status.py` prints the `source_remote`).
