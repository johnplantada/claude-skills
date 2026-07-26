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

Run `scripts/secret_scan.py` — it scans the chezmoi source tree (pass a path to scan a file or dir
about to be added) and prints one `<path>	reason=…` line per finding, **never the secret value or
file contents** (it uses `grep -l`, filenames only). Exit 0 = clean, exit 1 = findings to
reconcile. It flags two ways: high-signal credential shapes in file *content*
(`content:github-token`, `content:aws-access-key-id`, …) and files that are secret-by-*location*
(`.ssh/`, `.aws/`, `.netrc`, `gh/hosts.yml`, `*credentials*`, `.env` — chezmoi's `dot_`/`private_`
encodings included) that are stored as plaintext rather than `encrypted_*.age` or a template.

<details><summary>Under the hood — the raw patterns the scanner greps</summary>

```bash
# obvious high-signal patterns in files about to be added / in the source
grep -rInE '(api[_-]?key|secret|token|password|passwd|BEGIN [A-Z ]*PRIVATE KEY|ghp_|xox[bap]-|AKIA[0-9A-Z]{16})' \
  "$(chezmoi source-path)" 2>/dev/null
```
Also treat these as secret-by-location and do NOT add as-is: `~/.ssh/*`, `~/.aws/credentials`,
`~/.config/gh/hosts.yml`, `~/.netrc`, `~/.config/*/credentials*`, `.env` files, keychains.
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
