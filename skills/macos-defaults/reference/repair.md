# Repair workflow — a declared setting won't take

Goal: you applied `macos.sh` but a setting didn't stick — `drift_audit.py` still shows `DRIFT`/
`MISSING` for it, or the value reads back correct yet the UI doesn't reflect it. Diagnose why the
write didn't land (or didn't show), fix the line, re-apply, and prove it by re-reading.

> **Diagnose with the read-only scripts:** `scripts/drift_audit.py <macos.sh>` names the exact
> key that diverged; `scripts/defaults_read.py --find <term>` / `--domains` locate the *correct*
> domain/key when a spelling is wrong. Nothing here writes until you re-apply via
> [upgrade.md](upgrade.md). Verify by re-reading — [verification.md](verification.md).

## 1. Symptom → cause

| Symptom | Likely cause | Check |
|---|---|---|
| `MISSING` / reads `(not set)` after apply | wrong **domain** or **key** (typo, or renamed in this macOS) | `defaults_read.py --find <term>` · `--domains` |
| `DRIFT` — live value isn't what you wrote | wrong **type** (`-int` where the key is `-bool`/`-string`); OS coerced it | re-read the key; compare type |
| reads back correct, but UI unchanged | owning app hasn't reloaded, or needs logout/reboot | did you `killall`? is it a login-only key? |
| write appears ignored | a **system domain** (`/Library`, login window) needs `sudo` | is the domain user-level? |
| value reverts on every login | the OS **rewrites** this key at launch (not idempotent) | re-read after a logout |

## 2. Fix the cause

- **Wrong domain/key** — find the real one (`defaults_read.py --find "tap to click"`), or diff
  `defaults read` before/after toggling it in System Settings ([verification.md](verification.md)
  has the before/after recipe). Correct the line in `macos.sh`.
- **Wrong type** — match the type `defaults_read.py <domain> <key>` reports (`-bool`/`-int`/
  `-string`/`-float`). A `-string "1"` is not a `-bool` `1`.
- **Not reloaded** — `killall Dock Finder SystemUIServer` (or the specific app). Key-repeat and some
  trackpad settings read correct immediately but only **behave** after logout/reboot — say so, don't
  claim success.
- **Needs sudo** — a system-wide domain requires `sudo defaults write`. **Confirm with the user
  first** (Safety in [SKILL.md](../SKILL.md)); never run `sudo` writes silently. Some are
  security/privacy (FileVault, Gatekeeper, TCC) — don't touch without explicit go-ahead.
- **OS rewrites it** — if a key won't stay, it may not be user-controllable via `defaults`; drop the
  line rather than shipping a script that always drifts, and note why in a comment.

## 3. Re-apply & verify

Re-apply the corrected script ([upgrade.md](upgrade.md)), restart the affected app, then prove it:

```bash
scripts/drift_audit.py ~/.config/devenv/macos.sh     # the fixed key now reads MATCH, exit 0
```
Not `MATCH` after a correct re-apply + restart? The key isn't `defaults`-controllable on this macOS —
remove it or track it another way. A green read is not proof the UI updated — confirm the behavior
for login-only settings.
