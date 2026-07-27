# Verification — prove the surfaces name the same person

A profile is not working because the config files look right. It is working when the identity git
applies, the key ssh offers, and the account the host authenticates all resolve to **one person**,
measured from inside the tree. Three levels, cheapest first.

## Level 1 — the audit (always)

```bash
scripts/profile_audit.py
```

Expect: every profile's `key_match ok`, `allowed_signers ok`, an email, and no 🔴 gaps. Exit 0.

This is a **static** proof: it compares what each surface *intends*. It cannot tell you what a
server would actually accept — that's level 3.

Report each profile as a line: `work: email ✓ · signing ✓ · key ✓ · alias github-work`.

## Level 2 — a signed commit that actually verifies (per profile)

The static check confirms the pairing line exists; only a real commit confirms the whole
sign→verify pipeline works for **that** identity.

```bash
scripts/profile_resolve.py <a-repo-in-the-tree>     # confirm the right identity resolves here
```
Then make the test commit with **`git-setup`'s `verify_signing.py`**, which owns this proof and
runs it inside a throwaway repo it cleans up:

```bash
../git-setup/scripts/verify_signing.py --key <that-profile's-signingkey>
```
Expect a **GOOD signature**. A `%G?` of `N` (unsigned) or `U`/`E` means the profile's key is not
usable for verification yet — go to [repair.md](repair.md), don't paper over it.

Run this **once per profile**, not once per machine. Passing for the personal identity says nothing
about the work one; the second identity is exactly where this fails.

## Level 3 — the network probe (opt-in)

The only check that reports which account a key *actually* authenticates as, rather than which key
ssh intends to offer:

```bash
scripts/profile_resolve.py <repo> --probe-remote     # -> ssh.authenticates_as <account>
```

Confirm the reported account is the one that profile should be. Three other outcomes, and they mean
different things — don't collapse them:

| Row | Means | Do |
|---|---|---|
| `(permission denied — the host refused this key)` | the host was asked and rejected the key | a real finding — see [repair.md](repair.md) |
| `undetermined … host key not in known_hosts` | the host was never asked; strict checking refused an unseen host | connect to that host once yourself, then re-probe |
| `undetermined … named no account` | the host replied with something unfamiliar | undetermined, not a failure |

**It makes a real network call and authenticates as the user**, so it is opt-in and never part of
the default audit. Don't run it against a host the user hasn't already used, and skip it entirely on
a machine that's offline or behind a proxy that would hang the connection.

The probe is strictly **read-only**: `StrictHostKeyChecking=yes` plus `UpdateHostKeys=no` mean it
can never add a host key to `~/.ssh/known_hosts`. That's why an unseen host reports `undetermined`
rather than quietly succeeding — a tool whose job is verifying identity must not auto-trust a new one.

## What a clean result does and doesn't prove

| Proven | Not proven |
|---|---|
| The declared trees resolve the right email and signing key | Repos **outside** every declared tree — those use the global identity |
| Each identity's key is paired so its commits verify locally | That a **host** trusts the key — register the public key with the host (`ssh-config`) |
| The alias a remote uses offers the matching key | That every remote in the tree uses the alias — the audit samples one repo per tree |
| (level 3) The key authenticates as the expected account | That `gh` will act as that account — `gh` has one active account globally, not per-tree |

Say which of these you actually ran. "The audit is clean" and "I proved a work commit verifies" are
different claims, and only the second one covers the failure that brought the user here.
