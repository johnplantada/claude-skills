#!/usr/bin/env python3
"""Who am I in THIS directory — across git, ssh, and gh at once. Read-only.
Part of the identity-profiles skill.

    profile_resolve.py                       # the identity that applies in cwd
    profile_resolve.py ~/work/some-repo      # …in a specific repo
    profile_resolve.py ~/work/x --probe-remote   # + ask the host who this key authenticates as

`git-setup`'s `git_identity.py` answers the git half (which include file won). This answers
the question no single layer can: whether the identity git applies here, the key ssh would
push with, and the account gh is logged in as are the SAME person. Use it on one repo;
use `profile_audit.py` to sweep every declared profile.

`--probe-remote` makes a real network call (`ssh -T git@<alias>`) and is therefore opt-in:
it is the only way to learn which account a key actually authenticates as, rather than
which key ssh intends to offer.
"""

from __future__ import annotations

import os
import re
import sys

import _identity_common as ic
import profile_audit as pa

from lib.devenv_common import undetermined

# "Hi octocat!" (GitHub) · "Welcome to GitLab, @octocat!" (GitLab)
_BANNER_PATTERNS = (
    re.compile(r"\bHi ([A-Za-z0-9._/-]+)!"),
    re.compile(r"\bWelcome to GitLab, @([A-Za-z0-9._-]+)!"),
)
# "  - Active account: true" / "✓ Logged in to github.com account octocat (keyring)"
_GH_ACCOUNT_RE = re.compile(r"account\s+([A-Za-z0-9-]+)")


def parse_ssh_banner(text: str) -> str:
    """The account name a git host's ssh banner reports, or '' if none is recognizable.

    Both hosts answer a shell request by naming the authenticated user and then closing
    the connection with a NON-ZERO exit — so the banner, not the exit code, is the signal.
    """
    for pattern in _BANNER_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return ""


def probe_outcome(text: str) -> tuple[str, str]:
    """`(account, status)` from a probe's combined output.

    status is `ok` (a banner named the account), `host-unknown` (strict host checking
    refused an unseen host — a check that could not run, NOT a failed identity),
    `denied` (the host rejected the key), or `unrecognized`.

    Separating these matters: `host-unknown` and `denied` mean opposite things. The first
    says "I never asked the host"; the second says "I asked and the key was refused".
    Collapsing both to an empty account would report a working profile as broken.
    """
    account = parse_ssh_banner(text)
    if account:
        return account, "ok"
    lowered = text.lower()
    if "host key verification failed" in lowered or "no ed25519 host key is known" in lowered:
        return "", "host-unknown"
    if "permission denied" in lowered:
        return "", "denied"
    return "", "unrecognized"


def parse_gh_accounts(text: str) -> list[str]:
    """Account names from `gh auth status` output, in the order printed, deduplicated."""
    seen, accounts = set(), []
    for name in _GH_ACCOUNT_RE.findall(text):
        if name not in seen:
            seen.add(name)
            accounts.append(name)
    return accounts


def format_resolution(facts: dict) -> list[str]:
    """The greppable report rows for one directory."""
    rows = [
        f"query_path\t{facts['path']}",
        f"in_repo\t{facts['in_repo']}",
        f"user.email\t{facts['email'] or '(unset)'}",
        f"user.signingkey\t{facts['signingkey'] or '(unset)'}",
        f"commit.gpgsign\t{facts['gpgsign'] or '(unset)'}",
        f"remote\t{facts['remote'] or '(no origin)'}",
        f"remote_alias\t{facts['alias'] or '(not an ssh remote)'}",
        f"ssh.identityfile\t{', '.join(facts['identityfiles']) or '(none)'}",
        f"key_match\t{facts['key_match']}",
    ]
    if facts["gh_installed"]:
        rows.append(f"gh.accounts\t{', '.join(facts['gh_accounts']) or '(none logged in)'}")
    else:
        rows.append(undetermined("gh.accounts", "gh is not installed"))
    if facts["probed"]:
        status = facts["probe_status"]
        if status == "ok":
            rows.append(f"ssh.authenticates_as\t{facts['authenticates_as']}")
        elif status == "denied":
            rows.append("ssh.authenticates_as\t(permission denied — the host refused this key)")
        else:
            rows.append(undetermined("ssh.authenticates_as", {
                "host-unknown": "host key not in known_hosts and strict checking is on — "
                                "connect to this host once yourself, then re-probe",
            }.get(status, "the host's reply named no account")))
    return rows


def collect(path: str, *, probe_remote: bool) -> dict:
    """Resolve every surface for `path`. Read-only except the opt-in network probe."""
    in_repo = ic.is_git_repo(path)
    url = ic.remote_url(path) if in_repo else ""
    alias = pa.alias_of_remote(url)
    identityfiles = []
    if alias:
        rc, out = ic.ssh_g(alias)
        identityfiles = pa.parse_ssh_identityfiles(out) if rc == 0 else []

    signingkey = ic.config_get("user.signingkey", path)
    gh_installed, gh_raw = ic.gh_auth_status()
    facts = {
        "path": path,
        "in_repo": "yes" if in_repo else "no (includeIf gitdir rules will NOT apply)",
        "email": ic.config_get("user.email", path),
        "signingkey": signingkey,
        "gpgsign": ic.config_get("commit.gpgsign", path),
        "remote": url,
        "alias": alias,
        "identityfiles": identityfiles,
        "key_match": pa.key_match(identityfiles, signingkey),
        "gh_installed": gh_installed,
        "gh_accounts": parse_gh_accounts(gh_raw),
        "probed": False,
        "authenticates_as": "",
        "probe_status": "",
    }
    if probe_remote and alias:
        _, banner = ic.ssh_probe_identity(alias)
        facts["probed"] = True
        facts["authenticates_as"], facts["probe_status"] = probe_outcome(banner)
    return facts


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "-h" in args or "--help" in args:
        print(__doc__.strip())
        return 0
    probe_remote = "--probe-remote" in args
    positional = [a for a in args if not a.startswith("--")]
    path = ic.expand(positional[0]) if positional else os.getcwd()

    if not os.path.isdir(path):
        print(f"no such directory: {path}", file=sys.stderr)
        return 2

    print("\n".join(format_resolution(collect(path, probe_remote=probe_remote))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
