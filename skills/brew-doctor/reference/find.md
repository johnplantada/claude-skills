# Find workflow — search, compare, and choose the best install

Goal: turn a **need** ("I want a tool that does X") or a **name** into the right install decision
for *your* machine — the step *before* [setup.md](setup.md) installs it. Read-only: this
recommends, it never installs.

> **Run [`scripts/brew_find.py`](../scripts/README.md)** — `brew_find.py <term>` searches formulae
> + casks by name and description; `brew_find.py <name>` prints a dossier (desc, version,
> popularity, deprecation, arch bottle, versioned variants) **plus a best-install call** that
> layers the judgment below on top of `brew info`. The inline commands here are what it runs.

## 1. Search — what's out there

```bash
brew search <term>            # match formula/cask NAMES
brew search --desc <term>     # match DESCRIPTIONS — use this for "a tool that does X"
```
`--desc` casts the wider net when you know the *job* but not the *name*. Narrow to a candidate,
then get its dossier.

## 2. Dossier — is this the right one?

```bash
brew desc <name>              # one line: what it is
brew info <name>              # version, deps, caveats, analytics, deprecated/disabled, homepage
```
Read for: **popularity** (30/90/365-day install counts = how used/maintained it is),
**deprecated/disabled** (avoid — it's on the way out), **caveats** (post-install gotchas),
**license**. `brew info --json=v2 <name>` exposes bottle arches and structured fields.

## 3. Best install for YOUR situation (the decision)

Weigh, in order — `brew_find.py` flags each of these automatically:

1. **Is it a runtime?** (node/python/ruby/go/rust/deno/bun/php/java…) → install with **`mise`**,
   NOT brew. Brew auto-bumps runtimes and breaks configs — that's the whole brew-doctor hazard.
   Hand off to the **`runtime-versions`** skill: `mise use -g <tool>@<version>`.
2. **GUI or CLI?** GUI app → `--cask` (or **mas** for App-Store-only apps). CLI → formula. Some
   ship both — pick by how you'll actually use it.
3. **Core vs a tap.** A tapped formula is extra trust + update surface — prefer core unless the tap
   is the upstream project's own and well-maintained.
4. **arm64 native?** No native bottle → it builds from source (slow) or runs via Rosetta.
   `brew info --json=v2 <name>` shows which arches are bottled.
5. **Fragile / version-sensitive?** (editors, LSPs, databases) → install a **versioned formula**
   (`postgresql@16`, `node@20`) when offered, and **pin** it:
   `brew install <name> && brew pin <name>` — so it can't bump unattended.
6. **Self-updating cask?** `auto_updates true` → brew won't manage its version; that drift is
   expected, not a problem to fix.

## 4. Install, then fold back in

Once decided, install per the call `brew_find.py` printed. Then:
- refresh the declarative Brewfile ([setup.md](setup.md)),
- confirm the gates/pins took ([optimize.md](optimize.md)),
- and **verify it actually runs** — a `--version` or smoke command ([verification.md](verification.md)).
