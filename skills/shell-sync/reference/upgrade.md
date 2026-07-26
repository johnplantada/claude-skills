# Upgrade workflow — re-sync the mirror after the canonical shell changes

Goal: keep the two shells in sync **over time**. You changed the canonical shell — added an alias, a
new tool's PATH entry, an exported var — and the mirror needs to catch up. The sync file is
regenerated, never hand-edited, so this is a one-command refresh plus verification.

> Requires the sync to already exist ([setup.md](setup.md)). This path is the recurring maintenance;
> setup is the one-time stand-up.

## 1. Clean the canonical first (if PATH changed)

If the change touched PATH, run [repair.md](repair.md) on the **canonical** shell first — dedupe and
drop dead entries — so you don't propagate junk into the mirror.

## 2. Regenerate the managed file

```bash
scripts/mirror_plan.py > /tmp/00-shell-sync.fish            # re-extract canonical state as a plan
diff ~/.config/fish/conf.d/00-shell-sync.fish /tmp/00-shell-sync.fish   # what changed since last sync
```
Review the diff — it shows exactly which PATH entries / env vars / aliases (and the starship prompt
init line, if starship is on PATH) were added or removed. Back up the existing managed file, then
overwrite it with the new plan. Because it's a single marked,
auto-generated file, the overwrite is idempotent — no hand-merging.

## 3. Verify (both shells must agree)

Run [verification.md](verification.md) / `scripts/shell_diff.py <tools>`: `only_in_fish` empty
(mirror has everything canonical does), the new alias/var present in both, and each shell still
starts clean. If a newly-added tool now resolves differently per shell, that's a divergence →
[repair.md](repair.md).

## 4. Report

What propagated (added/removed path entries, env vars, aliases since the last sync), anything still
needing manual porting (functions/complex aliases), and the verified parity result.
