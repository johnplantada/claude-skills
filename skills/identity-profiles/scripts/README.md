# identity-profiles scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the
same `git config` / `ssh -G` / `gh auth status` pipeline and re-deriving how they join.
These are the source of truth for the mechanical checks; the reference `.md` files carry
the judgment.

Run them by absolute path from the skill directory. **Both are read-only inspectors** — safe
to re-run, they touch no file on this machine. `profile_resolve.py --probe-remote` additionally
makes an outbound `ssh -T` connection, which is why it is opt-in and never default; it still
writes nothing, because `StrictHostKeyChecking=yes` + `UpdateHostKeys=no` prevent the
`known_hosts` append that `accept-new` would have made.

| Script | Purpose | Example |
|---|---|---|
| `profile_audit.py [--tree <path>]` | Sweep **every** profile git declares via `includeIf`, resolve all four surfaces per tree, and report cross-surface disagreement → greppable facts + a gap report sorted 🔴 → 🟡. Exit 1 if any 🔴. `--tree` adds a tree git doesn't declare yet. **Run first.** | `profile_audit.py` |
| `profile_resolve.py [path] [--probe-remote]` | Who resolves in ONE directory across git + ssh + gh at once — email, signing key, the alias's key, the gh account. `--probe-remote` asks the host which account the key really authenticates as. Defaults to cwd. | `profile_resolve.py ~/work/api` |

## Worked example — the whole audit → prove loop in two calls

```
profile_audit.py | grep '^gap'                      # e.g. 🔴 work key_match / 🔴 work allowed_signers
profile_resolve.py ~/work/api --probe-remote        # ssh.authenticates_as  work-user
```
The first call ranks every profile's gaps and names the surface that drifted. The second answers
the question the static audit structurally cannot — which account the key *actually* authenticates
as, rather than which key ssh intends to offer. Per-profile signing proof is `git-setup`'s
`verify_signing.py`; this skill doesn't duplicate it.

## Why the cross-surface join lives here

`git-setup` can tell you which email resolves. `ssh-config` can tell you which keys are healthy.
Neither can tell you that **this tree's email is paired with this tree's key** in `allowed_signers`,
or that **this tree's remotes offer that same key** — those comparisons span both layers, and they
are the two failures that ship silently. `signers_pairing()` and `key_match()` are that join, and
they are pure functions so the tests decide them without git, ssh, or a network.

## Conventions for adding scripts

- Python 3.9+, **stdlib only**. Start each file with `from __future__ import annotations`; add type
  hints and module/function docstrings.
- Separate **pure logic** (parsing / analysis / formatting) from subprocess and IO — those pure
  functions are what the tests call, no mocking.
- Put the shared `git` / `ssh` / `gh` wrappers in **`_identity_common.py`** (leading underscore =
  not a workflow entrypoint) — one place to edit when a CLI call changes.
- Print `key<TAB>value` lines; keep output greppable and order stable. A check that could not run
  emits `undetermined` (`lib.devenv_common`), never a blank that reads as a pass.
- **Never open a private key.** Compare key *paths* as `ssh -G` reports them. Public halves
  (`*.pub`, `allowed_signers`) are fine to read; key hygiene belongs to `ssh-config`.
- Anything that touches the network must be behind an explicit opt-in flag and carry a timeout.
- Executable: `#!/usr/bin/env python3` shebang, `chmod +x`, and end with
  `if __name__ == "__main__": sys.exit(main())`.
- Tests live in `tests/identity_profiles/` and exercise the pure functions directly.
