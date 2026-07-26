# git-setup scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing the
same `git config --global --get` / throwaway-repo bash each time. Fewer tokens, no
re-derivation, no footguns (e.g. the signed-but-unverifiable trap). These are the source of
truth for the mechanical commands; the reference `.md` files carry the judgment.

Run them by absolute path from the skill directory. `git_audit.py` and `git_identity.py` are
**read-only inspectors** — safe to re-run, they change nothing. `verify_signing.py` writes
**only** inside a throwaway `mkdtemp` repo it removes on exit; it never touches a real repo
or your global config.

| Script | Purpose | Example |
|---|---|---|
| `git_audit.py` | Audit the GLOBAL config → greppable `key<TAB>value` facts + a gap report sorted 🔴 → 🟡 → 🟢, each with its fix command. **Run first.** | `git_audit.py` |
| `git_identity.py [path]` | Which `user.email` + signing key **resolves** in a directory (evaluates `includeIf` as git sees it), the file each value came from, and the global includeIf rules. Defaults to cwd. | `git_identity.py ~/work/some-repo` |
| `verify_signing.py [--self-test \| --key <pub>]` | PROVE a signature verifies: makes a test commit in a temp repo and reports `%G?` + the `Good signature` line. Default inherits your global config (reflects real state); `--self-test` proves the pipeline with an ephemeral key; `--key` tests a specific key before you adopt it. | `verify_signing.py --self-test` |

## Worked example — the whole audit → prove loop in two calls

```
git_audit.py | grep '^gap'          # e.g. 🟡 no commit signing / 🔴 signed but no allowedSignersFile
verify_signing.py --self-test       # result  ✅  GOOD signature — the sign→verify pipeline works here
```
First call ranks the gaps and hands you the exact `git config` fix. `--self-test` proves the
signing machinery on this machine end to end (ephemeral key, no real key touched) *before* you
commit to it globally; after configuring, `verify_signing.py` (no flag) proves your **real**
global setup now yields a `G` status instead of `N`. Per-directory identity? `git_identity.py
~/work/<repo>` names the winning include file — the definitive check that an `includeIf` matched.

## Conventions for adding scripts

- Python 3.9+, **stdlib only**. Start each file with `from __future__ import annotations`; add type
  hints and module/function docstrings.
- Separate **pure logic** (parsing / analysis / formatting) into plain functions from
  subprocess/IO — those pure functions are what the tests call, no mocking.
- Put the shared `git` / `uname` / PATH wrappers in **`_git_common.py`** (leading underscore = not a
  workflow entrypoint) — one place to edit when a CLI call changes. Operations unique to one script
  (a `mkdtemp` repo, `ssh-keygen`) stay inlined in that script.
- Print `key<TAB>value` or `label: value` lines; keep output greppable and order stable.
- Mutating helpers touch **only** a `mkdtemp` they own and clean up (`try/finally: shutil.rmtree`);
  never a real repo or global config.
- Executable: `#!/usr/bin/env python3` shebang, `chmod +x`, and end with
  `if __name__ == "__main__": sys.exit(main())`.
- Tests live in `tests/git_setup/` and exercise the pure functions directly.
