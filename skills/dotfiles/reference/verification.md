# Verification — prove the dotfiles state is consistent

chezmoi's own commands are the verification tools — use them, don't eyeball the source tree.
`scripts/chezmoi_status.py` rolls the in-sync + health checks below into one greppable report;
`scripts/secret_scan.py` covers the no-secret-leaked check. Inline commands are the under-the-hood
detail.

## In sync? (source == home)

`scripts/chezmoi_status.py` prints `status_drift	0` and `diff_pending	0` when source and home
agree. Non-zero means drift — reconcile (`chezmoi re-add` to keep home changes, `chezmoi apply` to
keep source) before calling anything done.

<details><summary>Under the hood</summary>

```bash
chezmoi status     # EMPTY output = source and home agree (no drift)
chezmoi diff       # EMPTY = apply would change nothing
```
</details>

## Apply is idempotent

```bash
chezmoi apply
chezmoi apply      # second run must be a no-op; chezmoi_status.py keeps drift/diff at 0
```

## Health

`scripts/chezmoi_status.py` prints a `doctor ... warning=N error=N` summary and lists any
warning/error rows as `doctor_issue` lines. Address each (e.g. missing `age`, unreachable password
manager, template that can't render on this host). `info` rows are optional-tool noise and are
intentionally not surfaced.

<details><summary>Under the hood</summary>

```bash
chezmoi doctor     # flags missing tools, bad config, encryption/template problems
```
</details>

## Templates resolved correctly on THIS machine

For any `.tmpl` file, confirm the rendered result is what you expect here:
```bash
chezmoi cat ~/.gitconfig          # shows the RENDERED output apply would write
```
Check per-machine values (hostname, os) and that secret references resolved (not left as literal
`{{ ... }}`, and not printing a real secret to a log you keep).

## No secret leaked (see secrets.md)

Run `scripts/secret_scan.py` — exit 0 (`clean`) is the green light; exit 1 lists each offending
path + reason (never the value) to reconcile first. Confirm the remote is your **private** repo via
`scripts/chezmoi_status.py`'s `source_remote` line.

<details><summary>Under the hood</summary>

```bash
git -C "$(chezmoi source-path)" grep -InE '(api[_-]?key|secret|token|BEGIN [A-Z ]*PRIVATE KEY|ghp_|AKIA[0-9A-Z]{16})' \
  && echo "REVIEW ABOVE" || echo "no obvious plaintext secrets in source"
git -C "$(chezmoi source-path)" remote -v   # confirm the remote is your PRIVATE repo
```
</details>

## After a new-machine bootstrap

`chezmoi status` empty, `chezmoi doctor` clean, encrypted files decrypted (the `age`/`gpg` key was
present), and templated secrets resolved (the password manager was reachable). If apply failed on
a file, it's almost always a missing key or unreachable secret source — not a chezmoi bug.
