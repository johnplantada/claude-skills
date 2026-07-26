#!/usr/bin/env python3
"""PROVE a commit signature verifies, end to end. Part of the git-setup skill.

Makes a test commit in a throwaway `mkdtemp` repo and reports whether git says the
signature is GOOD. The temp repo is the ONLY thing it writes — it is removed on exit
and NEVER touches any real repo or your global config.

    verify_signing.py              # inherit your GLOBAL config → reflects real state
                                   #   (unsigned commit here means global signing is off)
    verify_signing.py --self-test  # generate an EPHEMERAL ssh key in the temp repo and
                                   #   prove the whole sign→verify pipeline works, regardless
                                   #   of your global setup. Touches no real key.
    verify_signing.py --key ~/.ssh/id_ed25519.pub [--email you@x.com] [--signers <file>]
                                   #   prove a SPECIFIC key signs+verifies before you adopt it
                                   #   globally (needs its private key reachable / in ssh-agent).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import _git_common as gc

# --- pure argument parsing -----------------------------------------------------

def parse_args(argv: list[str]) -> dict:
    """Parse CLI args into {help|mode,key,email,signers}; raise ValueError on misuse."""
    mode, key, email, signers = "inherit", "", "", ""
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test":
            mode = "selftest"
            i += 1
        elif arg == "--key":
            if i + 1 >= len(argv):
                raise ValueError("--key needs a .pub path")
            mode, key = "key", argv[i + 1]
            i += 2
        elif arg == "--email":
            if i + 1 >= len(argv):
                raise ValueError("--email needs an address")
            email = argv[i + 1]
            i += 2
        elif arg == "--signers":
            if i + 1 >= len(argv):
                raise ValueError("--signers needs a path")
            signers = argv[i + 1]
            i += 2
        elif arg in ("-h", "--help"):
            return {"help": True}
        else:
            raise ValueError(f"unknown arg: {arg}")
    return {"help": False, "mode": mode, "key": key, "email": email, "signers": signers}


# --- pure output interpretation ------------------------------------------------

def collapse_ws(text: str) -> str:
    """`tr '\\n' ' ' | sed 's/  */ /g'`: newlines to spaces, runs of spaces squeezed."""
    return re.sub(r" +", " ", text.replace("\n", " "))


def grep_lines(text: str, pattern: str) -> str:
    """Lines matching `pattern` (case-insensitive), each with a trailing newline —
    mirroring `grep -iE` output (which is why its downstream `tr` yields a trailing space)."""
    return "".join(ln + "\n" for ln in text.splitlines() if re.search(pattern, ln, re.IGNORECASE))


def extract_good_signer(show: str, verify: str) -> str:
    """First `Good …signature` line across SHOW+VERIFY, leading whitespace stripped."""
    for line in (show + verify).splitlines():
        if re.search(r"Good .*signature", line, re.IGNORECASE):
            return re.sub(r"^\s*", "", line)
    return ""


def interpret_status(mode: str, sig: str, show: str, verify: str) -> list[str]:
    """The `result`/`verify_line`/`detail` lines for a given `%G?` status code."""
    if sig == "G":
        signer = extract_good_signer(show, verify)
        return [
            f"verify_line\t{signer or 'Good signature'}",
            "result\t✅\tGOOD signature — signing verifies end to end",
        ]
    if sig == "N":
        if mode == "inherit":
            return ["result\t🟡\tcommit is UNSIGNED — global signing is off (this is the real current state)"]
        return ["result\t❌\tcommit is UNSIGNED despite signing config — check gpg.format/user.signingkey"]
    if sig == "U":
        return [
            "result\t🟡\tsigned but validity UNKNOWN — email not in allowedSignersFile (add '<email> <pubkey>')",
            f"detail\t{collapse_ws(verify)}",
        ]
    return [
        f"result\t❌\tsignature status={sig} — could not verify",
        f"detail\t{collapse_ws(grep_lines(show, r'signature|principal|error'))}",
    ]


# --- IO: run the throwaway-repo signing test -----------------------------------

def _git(tmp: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", tmp, *args], capture_output=True, text=True)


def _run_verify(tmp: str, mode: str, key: str, email: str, signers: str) -> int:
    _git(tmp, "init", "-q")

    # Author identity: --email, else the resolved global email, else a placeholder.
    if not email:
        email = gc.config_get("user.email") or "verify-signing@example.invalid"
    _git(tmp, "config", "user.email", email)
    _git(tmp, "config", "user.name", gc.config_get("user.name") or "verify-signing")

    out = [f"mode\t{mode}", f"temp_repo\t{tmp}", f"commit_email\t{email}"]

    if mode == "selftest":
        # Ephemeral, passphrase-less key generated INSIDE the temp repo — proves the
        # sign+verify machinery without touching any real key/agent.
        keygen = subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "verify-signing-selftest",
             "-f", f"{tmp}/sign_key"],
            capture_output=True, text=True,
        )
        key = f"{tmp}/sign_key.pub"
        if keygen.returncode != 0 or not Path(key).is_file():
            out.append("result\t❌\tssh-keygen failed — cannot generate the self-test key")
            out.append(f"detail\t{collapse_ws((keygen.stdout + keygen.stderr).strip())}")
            print("\n".join(out))
            return 1
        pub = Path(key).read_text().strip()
        signers = f"{tmp}/allowed_signers"
        Path(signers).write_text(f"{email} {pub}\n")
        _git(tmp, "config", "gpg.format", "ssh")
        _git(tmp, "config", "user.signingkey", key)
        _git(tmp, "config", "commit.gpgsign", "true")
        _git(tmp, "config", "gpg.ssh.allowedSignersFile", signers)
        out.append(f"signing_key\t{key}")
    elif mode == "key":
        _git(tmp, "config", "gpg.format", "ssh")
        _git(tmp, "config", "user.signingkey", key)
        _git(tmp, "config", "commit.gpgsign", "true")
        if not signers:
            # Build a one-line allowed_signers on the fly so verification can succeed.
            signers = f"{tmp}/allowed_signers"
            pub = Path(key).read_text().strip()
            Path(signers).write_text(f"{email} {pub}\n")
        _git(tmp, "config", "gpg.ssh.allowedSignersFile", signers)
        out.append(f"signing_key\t{key}")
        out.append(f"allowed_signers\t{signers}")
    else:  # inherit — reflect the real global state; report what git will actually do.
        out.append(f"global_gpgsign\t{gc.config_get('commit.gpgsign') or 'false'}")
        out.append(f"global_format\t{gc.config_get('gpg.format') or '(unset)'}")
        out.append(f"global_signingkey\t{gc.config_get('user.signingkey') or '(unset)'}")
        out.append(f"global_allowedSigners\t{gc.config_get('gpg.ssh.allowedSignersFile') or '(unset)'}")

    # Make the test commit. If signing needs a passphrase and no agent is loaded this
    # can fail — capture that instead of aborting.
    commit = _git(tmp, "commit", "--allow-empty", "-m", "signing test", "-q")
    if commit.returncode == 0:
        short = _git(tmp, "rev-parse", "--short", "HEAD").stdout.strip()
        out.append(f"commit\tcreated ({short})")
    else:
        commit_err = (commit.stdout + commit.stderr).strip()
        out.append("commit\tFAILED")
        out.append(f"commit_error\t{commit_err}")
        out.append("result\t❌\tcould not create the commit — see commit_error above")
        print("\n".join(out))
        return 1

    # Is this commit actually signed?  %G? : G good / B bad / U good-unknown / N none / E error
    sig = _git(tmp, "log", "-1", "--format=%G?").stdout.strip() or "?"
    out.append(f"sig_status_code\t{sig}")

    # Capture like bash `$(… 2>&1)` — combined streams, trailing newlines stripped.
    def _capture(p: subprocess.CompletedProcess[str]) -> str:
        return (p.stdout + p.stderr).rstrip("\n")

    show = _capture(_git(tmp, "log", "--show-signature", "-1"))
    verify = _capture(_git(tmp, "verify-commit", "HEAD"))
    out += interpret_status(mode, sig, show, verify)

    print("\n".join(out))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        parsed = parse_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if parsed["help"]:
        print(__doc__)
        return 0
    if parsed["mode"] == "key" and not Path(parsed["key"]).is_file():
        print(f"--key: no such file: {parsed['key']}", file=sys.stderr)
        return 2

    tmp = tempfile.mkdtemp(prefix="verifysign.")
    try:
        return _run_verify(tmp, parsed["mode"], parsed["key"], parsed["email"], parsed["signers"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
