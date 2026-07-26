# Upgrade workflow — apply the script to converge the machine (and keep it current)

Goal: bring the machine up to the declared `macos.sh` and make the changes visible — a **new
machine** reaching your baseline, a **re-apply** after you edited the script, or **reconciling after
a macOS update** (a new OS can add keys, change a default, or rename a setting). Re-running is a
no-op, so applying is safe to repeat.

> After a macOS update, also re-run [optimize.md](optimize.md) (drift audit) to catch OS-changed
> defaults, and [setup.md](setup.md) to capture any new setting worth pinning. A line that applies
> but won't take effect → [repair.md](repair.md).

**Fast path:** `scripts/defaults_apply.py <macos.sh>` does the whole flow — back up touched domains
→ warn on `sudo`/security lines → run the script → `killall` affected apps → flag reboot-needed. It
**dry-runs without `--yes`** (backs up + previews, writes nothing), so:

```bash
scripts/defaults_apply.py ~/.config/devenv/macos.sh          # dry run: back up + preview
scripts/defaults_apply.py ~/.config/devenv/macos.sh --yes    # apply + restart apps (confirm first)
scripts/drift_audit.py    ~/.config/devenv/macos.sh          # verify: expect all MATCH
```
`defaults write` is mutating and deliberately gated — confirm with the user before passing `--yes`.
The steps below are what that script automates (under the hood), in order.

## 1. Locate the script

```bash
cat ~/.config/devenv/macos.sh        # or the path from [macos-defaults].script
```
Read it first. Confirm it's the intended source of truth and scan for any `sudo` lines or
security-sensitive keys (see [SKILL.md](../SKILL.md) Safety) — confirm those with the user before running.

## 2. Back up current values (reversible)

Before writing, snapshot what the affected keys are now, so a change can be undone:

```bash
# for each domain the script touches:
defaults read com.apple.dock    > /tmp/macos.dock.before    2>/dev/null || true
defaults read com.apple.finder  > /tmp/macos.finder.before  2>/dev/null || true
```

## 3. Run the script

```bash
bash ~/.config/devenv/macos.sh
```
`defaults write` is mutating — confirm with the user before this step. Each line just sets a value;
running twice sets the same value twice (a no-op).

## 4. Restart affected apps

Most UI settings don't take effect until the owning app reloads its prefs:

```bash
killall Dock Finder SystemUIServer
```
- **Dock** — auto-hide, tile size, recents.
- **Finder** — extensions, hidden files, view style, path bar.
- **SystemUIServer** — menu bar / control center items.

`killall` on a running app just relaunches it; ignore `No matching processes` for apps not running.

## 5. Flag settings that need logout/restart

`killall` does **not** cover everything. These typically need a full logout or reboot — say so
explicitly rather than claiming success:
- Keyboard **key-repeat** rate (`KeyRepeat` / `InitialKeyRepeat`) — takes effect on next login.
- Trackpad **tap-to-click** on some macOS versions.
- Anything in `NSGlobalDomain` read by apps only at launch — restart the app, or log out.

## 6. Verify

Prove each setting took by re-reading it, and confirm a second run is a no-op:

```bash
scripts/drift_audit.py ~/.config/devenv/macos.sh     # every declared line should read MATCH
```
See [verification.md](verification.md) for the full re-read + idempotency check. Don't call `apply`
done until the values read back correct (auditor exits 0, no `DRIFT`/`MISSING`).

## Report

Which apps were restarted, which settings need logout/restart before they show, and the verification
result (all keys read back as intended). If this is the OS-settings step of `devenv bootstrap`,
report back to that runbook.
