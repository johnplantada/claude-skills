#!/usr/bin/env python3
"""Audit every identity profile on this machine for cross-surface agreement. Read-only.
Part of the identity-profiles skill.

    profile_audit.py                    # audit each tree git declares via includeIf
    profile_audit.py --tree ~/oss/      # also audit a tree that has no includeIf yet

A "profile" is a directory tree whose repos should all use one identity. Git declares
them in `includeIf "gitdir:…"` rules, so those rules ARE the machine's declaration and
this audit discovers them rather than asking. For each tree it resolves the identity git
applies there, then checks the surfaces that must agree with it:

  * `allowed_signers` pairs that tree's email with that tree's signing key
    (the signed-but-unverifiable trap, per identity),
  * the ssh host alias its remotes use resolves to the matching private key
    (the right-email-wrong-key push).

Neither the git nor the ssh layer can see that pairing alone — checking the join is this
script's entire reason to exist. Prints greppable `key<TAB>value` facts, then a gap
report sorted 🔴 → 🟡. Exit code is 0 when there are no 🔴 gaps, 1 when there are.
"""

from __future__ import annotations

import os
import sys

import _identity_common as ic

from lib.devenv_common import undetermined

RED, YELLOW = "🔴", "🟡"


# --- pure logic: parsing -------------------------------------------------------


def parse_includeif_rules(lines: list[str]) -> list[tuple[str, str]]:
    """`(condition, include_path)` pairs from `git config --get-regexp '^includeif\\.'`.

    Each line is `includeif.<condition>.path <file>`. Splitting on the first space is
    WRONG: both halves can contain spaces — a tree at `~/my work/` puts one in the key, and
    a path like `/Users/u/My Configs/work.gitconfig` puts one in the value. Splitting on
    the first space silently dropped such a profile, so the audit reported a configured
    machine as having none. `.path ` (with the trailing space) is the real separator, since
    the key always ends in `.path` and the value always follows one space.

    Lines with no `.path ` separator declare no include file to audit and are skipped.
    """
    rules = []
    for line in lines:
        key, sep, value = line.partition(".path ")
        if not sep or not value.strip() or not key.startswith("includeif."):
            continue
        rules.append((key[len("includeif.") :], value.strip()))
    return rules


def tree_of(condition: str) -> str:
    """The directory tree a `gitdir:` condition selects, or '' for other conditions.

    Handles the case-insensitive `gitdir/i:` form and strips a trailing `**` glob. Only
    `gitdir` conditions name a tree — `onbranch:` and `hasconfig:` select by something
    else entirely and are not profiles, so they resolve to ''.
    """
    for prefix in ("gitdir/i:", "gitdir:"):
        if condition.startswith(prefix):
            return condition[len(prefix) :].removesuffix("**")
    return ""


def profile_name(tree: str, include_path: str) -> str:
    """A short label for a profile: the tree's last component, else the include's stem."""
    name = os.path.basename(tree.rstrip("/"))
    if name and name not in (".", "~"):
        return name
    stem = os.path.basename(include_path).split(".")[0]
    return stem or "profile"


def alias_of_remote(url: str) -> str:
    """The ssh host (alias) a remote URL connects to, or '' if it isn't an ssh remote.

    Covers both ssh forms — `git@host:owner/repo` (scp-like) and `ssh://git@host/owner/repo`.
    An https remote has no alias to resolve, which is itself a finding: https bypasses the
    per-alias key selection this skill coordinates.
    """
    url = url.strip()
    if url.startswith("ssh://"):
        rest = url[len("ssh://") :]
        hostpart = rest.split("/", 1)[0]
        return hostpart.rpartition("@")[2].split(":", 1)[0]
    if "://" in url:
        return ""
    if "@" in url and ":" in url:
        return url.split(":", 1)[0].rpartition("@")[2]
    return ""


def parse_ssh_identityfiles(stdout: str) -> list[str]:
    """Expanded `identityfile` paths from `ssh -G <host>` output (keys are lowercased)."""
    files = []
    for line in stdout.splitlines():
        key, _, value = line.strip().partition(" ")
        if key.lower() == "identityfile" and value.strip():
            files.append(ic.expand(value.strip()))
    return files


def key_material(pub_text: str) -> str:
    """The `<keytype> <base64>` pair from a public key's first line ('' if unreadable).

    The comment field is deliberately dropped: it differs between a `.pub` file and the
    same key recorded in `allowed_signers`, so comparing it would produce false mismatches.
    """
    parts = pub_text.split()
    return " ".join(parts[:2]) if len(parts) >= 2 else ""


# --- pure logic: the cross-surface checks --------------------------------------


def signers_pairing(signers_text: str, email: str, material: str) -> str:
    """Is `email` paired with this exact key in allowed_signers? ok | missing | …

    Returns a status string rather than a bool so "couldn't check" stays distinct from
    "checked and absent" — `no-file` and `no-pubkey` are undetermined, not passes.
    """
    if not material:
        return "no-pubkey"
    if not signers_text.strip():
        return "no-file"
    if not email:
        return "no-email"
    for line in signers_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        principals = line.split(" ", 1)[0]
        if email in principals.split(",") and material in line:
            return "ok"
    return "missing"


def is_true(value: str) -> bool:
    """Git's boolean spellings, normalized. `1`, `yes`, `on`, `true` all mean enabled.

    `collect_profile` already asks git to normalize with `--type=bool`, but this stays
    defensive on purpose: `gaps_for` is a pure function the tests call directly, and it
    must not silently mean "off" for a value that git considers on. Getting this wrong
    disabled the skill's flagship check.
    """
    return value.strip().lower() in ("true", "1", "yes", "on")


def key_match(identityfiles: list[str], signingkey: str) -> str:
    """Does the ssh alias offer the same key the tree signs with? ok | mismatch | …

    Compares PATHS only — a signing key is named as its public half (`…_work.pub`) and
    `ssh -G` reports the private half (`…_work`), so the `.pub` suffix is stripped before
    comparing. No key file is opened here.

    Two non-path forms must NOT be treated as paths. A GPG key id is obvious. The subtler
    one is git's literal-key form (`user.signingkey = key::ssh-ed25519 AAAA…`): base64
    contains `/`, so a naive "does it look like a path" test accepted it and reported a
    confident `mismatch` against a config that was perfectly correct.
    """
    if not signingkey:
        return "no-signingkey"
    if signingkey.startswith("key::") or signingkey.startswith(("ssh-", "ecdsa-", "sk-ssh-", "sk-ecdsa-")):
        return "n/a-literal-key"  # the key itself, inline — there is no path to compare
    if "/" not in signingkey and not signingkey.startswith("~"):
        return "n/a-not-a-path"  # a GPG key id, not an ssh key
    if not identityfiles:
        return "no-identityfile"
    want = os.path.normpath(ic.expand(signingkey).removesuffix(".pub"))
    for candidate in identityfiles:
        if os.path.normpath(candidate.removesuffix(".pub")) == want:
            return "ok"
    return "mismatch"


# --- collection (IO) -----------------------------------------------------------


def collect_profile(name: str, tree: str, include_path: str) -> dict:
    """Resolve one profile across every surface. All probes are read-only."""
    profile = {"name": name, "tree": tree, "include": include_path, "probe": ic.find_repo_in(tree)}
    if not profile["probe"]:
        return profile

    probe = profile["probe"]
    profile["email"] = ic.config_get("user.email", probe)
    profile["signingkey"] = ic.config_get("user.signingkey", probe)
    profile["gpgsign"] = ic.config_get("commit.gpgsign", probe, as_bool=True)
    profile["format"] = ic.config_get("gpg.format", probe)

    signers_path = ic.config_get("gpg.ssh.allowedsignersfile", probe)
    profile["signers_path"] = signers_path
    profile["signers"] = signers_pairing(
        ic.read_allowed_signers(signers_path),
        profile["email"],
        key_material(ic.read_pub(profile["signingkey"])),
    )

    url = ic.remote_url(probe)
    profile["remote"] = url
    alias = alias_of_remote(url)
    profile["alias"] = alias
    if alias:
        rc, out = ic.ssh_g(alias)
        profile["identityfiles"] = parse_ssh_identityfiles(out) if rc == 0 else []
        profile["ssh_rc"] = rc
    else:
        profile["identityfiles"] = []
    profile["key_match"] = key_match(profile["identityfiles"], profile["signingkey"])
    return profile


# --- pure logic: formatting ----------------------------------------------------


def format_profile(p: dict) -> list[str]:
    """The greppable fact rows for one profile."""
    n = p["name"]
    head = f"profile\t{n}\ttree={p['tree']}\tinclude={p['include']}"
    if not p["probe"]:
        return [
            head,
            undetermined(
                f"{n}.probe_repo",
                f"no git repo found in {p['tree']} — includeIf gitdir only applies inside a repo, "
                "so nothing about this profile could be resolved",
            ),
        ]
    rows = [
        head,
        f"{n}.probe_repo\t{p['probe']}",
        f"{n}.user.email\t{p['email'] or '(unset)'}",
        f"{n}.user.signingkey\t{p['signingkey'] or '(unset)'}",
        f"{n}.commit.gpgsign\t{p['gpgsign'] or '(unset)'}",
        f"{n}.gpg.format\t{p['format'] or '(unset)'}",
        f"{n}.allowed_signers\t{p['signers']}\tfile={p['signers_path'] or '(unset)'}",
        f"{n}.remote\t{p['remote'] or '(no origin)'}",
        f"{n}.remote_alias\t{p['alias'] or '(not an ssh remote)'}",
    ]
    if p["alias"] and p.get("ssh_rc", 0) != 0:
        rows.append(undetermined(f"{n}.ssh.identityfile", f"ssh -G {p['alias']} failed (rc={p['ssh_rc']})"))
    else:
        rows.append(f"{n}.ssh.identityfile\t{', '.join(p['identityfiles']) or '(none)'}")
    rows.append(f"{n}.key_match\t{p['key_match']}")
    return rows


def gaps_for(p: dict) -> list[tuple[str, str, str, str]]:
    """`(severity, profile, check, message)` findings for one profile, worst first."""
    n = p["name"]
    if not p["probe"]:
        return [(YELLOW, n, "probe_repo",
                 f"no repo under {p['tree']} to verify the profile against — clone one, or drop the includeIf rule")]

    out = []
    if not p["email"]:
        out.append((RED, n, "user.email",
                    f"no email resolves in {p['tree']} — commits there will use the global identity"))
    if p["key_match"] == "mismatch":
        out.append((RED, n, "key_match",
                    f"alias '{p['alias']}' offers {', '.join(p['identityfiles'])} but this tree signs with "
                    f"{p['signingkey']} — pushes authenticate as the other identity"))
    signing_on = is_true(p["gpgsign"])
    if signing_on and p["signers"] == "missing":
        out.append((RED, n, "allowed_signers",
                    f"{p['email']} is not paired with {p['signingkey']} in {p['signers_path']} — "
                    "commits sign but show Unverified"))
    if signing_on and p["signers"] == "no-file":
        out.append((RED, n, "allowed_signers",
                    "commit signing is on but gpg.ssh.allowedSignersFile is unset/empty — "
                    "no commit can verify locally"))
    if signing_on and p["signers"] == "no-pubkey":
        out.append((YELLOW, n, "allowed_signers",
                    f"could not read the public half of {p['signingkey'] or '(unset)'}"))
    if not signing_on:
        out.append((YELLOW, n, "commit.gpgsign", f"commit signing is off in {p['tree']}"))
    if p["remote"] and not p["alias"]:
        out.append((YELLOW, n, "remote_alias",
                    "origin is https, so ssh key selection does not apply — this tree's identity can't be "
                    "enforced per-alias"))
    if p["key_match"] == "no-identityfile" and p["alias"]:
        out.append((YELLOW, n, "key_match", f"ssh -G {p['alias']} reported no identityfile to compare"))
    return out


def format_gaps(gaps: list[tuple[str, str, str, str]]) -> list[str]:
    """The gap section, sorted 🔴 before 🟡, stable within a severity."""
    if not gaps:
        return ["-- gaps --", "gap\t(none — every declared profile agrees across surfaces)"]
    order = {RED: 0, YELLOW: 1}
    ranked = sorted(gaps, key=lambda g: order.get(g[0], 9))
    return ["-- gaps --"] + [f"gap\t{sev}\t{name}\t{check}\t{msg}" for sev, name, check, msg in ranked]


def format_no_profiles() -> list[str]:
    """Rows for a machine with no declared profiles — explicitly NOT a clean bill.

    The empty-gap line ("every declared profile agrees") is true but reads as a pass when
    the real answer is that nothing was checked. `undetermined` keeps the two apart.
    """
    return [
        "profiles\t(none — no includeIf gitdir rules; every repo uses the global identity)",
        undetermined("gaps", "no profiles are declared, so no cross-surface check could run"),
    ]


def discover(rules: list[tuple[str, str]]) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Split includeIf rules into auditable `(name, tree, include)` profiles and notes."""
    profiles, notes = [], []
    for condition, include_path in rules:
        tree = tree_of(condition)
        if not tree:
            notes.append(f"skipped\tincludeif.{condition}\t"
                         "not a gitdir condition — selects by something other than a tree")
            continue
        profiles.append((profile_name(tree, include_path), tree, include_path))
    return profiles, notes


# --- entrypoint ----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    extra_trees = [args[i + 1] for i, a in enumerate(args) if a == "--tree" and i + 1 < len(args)]
    if "-h" in args or "--help" in args:
        print(__doc__.strip())
        return 0

    profiles, notes = discover(parse_includeif_rules(ic.global_includeif_rules()))
    for tree in extra_trees:
        if not any(t == tree for _, t, _ in profiles):
            profiles.append((profile_name(tree, ""), tree, "(--tree, not declared to git)"))

    lines = list(notes)
    if not profiles:
        print("\n".join(lines + format_no_profiles()))
        return 0

    all_gaps = []
    for name, tree, include_path in profiles:
        p = collect_profile(name, tree, include_path)
        lines += format_profile(p)
        all_gaps += gaps_for(p)

    lines.append(f"summary\tprofiles={len(profiles)}\tgaps={len(all_gaps)}")
    print("\n".join(lines + format_gaps(all_gaps)))
    return 1 if any(sev == RED for sev, *_ in all_gaps) else 0


if __name__ == "__main__":
    sys.exit(main())
