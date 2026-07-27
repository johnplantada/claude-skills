# credential-store scripts — the stable toolbox

Tested, parameterized helpers so a session **calls a script** instead of re-composing greps over
shell rc files — and, more importantly, so detection happens in code that *structurally cannot*
emit a secret, rather than in a model that has been asked nicely not to.

Run them by absolute path from the skill directory. **Both are read-only inspectors** — they change
nothing, and neither ever reads, stores, or unlocks an item in a credential store.

| Script | Purpose | Example |
|---|---|---|
| `credential_audit.py [--shell-only] [--all-assignments]` | Sweep shell rc files, known credential files, and git/gh storage. Classifies each credential-shaped assignment as **literal** (on disk) or **reference** (fetched from a store) → findings sorted 🔴 → 🟡 → 🟢. Exit 1 if any 🔴. `--all-assignments` adds a redacted inventory of *every* assignment for review. **Run first.** | `credential_audit.py` |
| `store_status.py` | Which stores are usable here (keychain, 1Password, pass, chezmoi encryption), the recommended destination, and the exact shell `reference_form` for it. Exit 1 if no store is usable. | `store_status.py` |

## Worked example — audit → destination → migrate

```
credential_audit.py | grep '🔴'        # e.g. shell /Users/u/.zshrc:42  GITHUB_TOKEN literal
store_status.py                        # recommended keychain + the reference_form to paste
```
The first says what's exposed and where; the second says where it can go and how to write the line.
The migration itself — putting the value into the store — is **not** scripted here on purpose: it
must run out of band so the value never passes through a report. See
[../reference/setup.md](../reference/setup.md) §2.

## The safety property, and why it's structural

`scan_assignments()` classifies an assignment's right-hand side and then **discards it**. A finding
is `(line_number, variable_name, classification)` — there is no field a value could occupy. A test
pins it end to end: an invented secret goes into the scanner, and the formatted report is asserted
not to contain it. So the guarantee survives a future refactor that forgets the rule, which an
instruction in a doc would not.

The same reasoning shapes `matches_marker()` (returns a bool, mirroring `grep -q`) and
`--all-assignments` (names and classifications, so the review it enables is safe to delegate to a
subagent).

## Boundary with `dotfiles`' `secret_scan.py`

They answer different questions and neither is redundant:

- **`dotfiles/scripts/secret_scan.py`** — *is a secret about to be committed?* Scans the chezmoi
  **source tree**, delegating content detection to gitleaks when present. A pre-commit tripwire.
- **`credential_audit.py`** — *is a credential in plaintext on the machine I use, and does anything
  reference a store instead?* Scans the **live** rc and config files, and classifies literal vs.
  reference — which `secret_scan.py` does not do at all.

## Conventions for adding scripts

- Python 3.9+, **stdlib only**. Start each file with `from __future__ import annotations`; add type
  hints and module/function docstrings.
- Separate **pure logic** from subprocess and IO — those pure functions are what the tests call.
- Put the shared filesystem/CLI probes in **`_credential_common.py`** (leading underscore = not a
  workflow entrypoint).
- **No function may return, print, or log matched secret text.** Return a bool, a rule name, a
  classification, a path, a line number. If a new check needs the value to decide, it discards it
  before returning — and a test asserts the value is absent from the output.
- Never call a store CLI in a form that emits a secret (`op read`, `security … -w`, `gh auth token`).
  Presence and metadata only.
- Print `key<TAB>value` lines; keep output greppable and order stable. A check that couldn't run
  emits `undetermined` (`lib.devenv_common`), never a blank that reads as a pass.
- Executable: `#!/usr/bin/env python3` shebang, `chmod +x`, and end with
  `if __name__ == "__main__": sys.exit(main())`.
- Tests live in `tests/credential_store/` and exercise the pure functions directly.
