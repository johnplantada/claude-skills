"""macOS smoke — actually EXECUTE every read-only entry point against the real OS.

The unit suite (tests/) feeds the pure parsers canned strings, so the subprocess
wrappers and real-tool output formats are never exercised there. This layer runs each
read-only script end to end and asserts it exits in its documented range without a
Python traceback — catching wrapper rot and tool-output format drift the unit tests
structurally cannot.

Deliberately OUTSIDE pyproject's testpaths: plain `pytest` stays fast and hermetic.
Run explicitly (CI macos job, or locally on a Mac):

    python3 -m pytest tests_smoke -q

Scripts probe whatever is installed; a missing underlying tool is a DOCUMENTED exit
path (e.g. rc 3 "not on PATH"), so every allowed-rc set below includes those. Only
read-only entry points run — nothing here mutates (defaults_apply runs WITHOUT --yes,
which its contract defines as dry-run: back up + preview only).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="smoke targets macOS")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

_FIXTURE_MACOS_SH = """\
#!/bin/bash
# smoke fixture — one benign declared default
defaults write com.apple.dock tilesize -int 48
"""

# (relative script path, args, allowed return codes). Args using {tmp} get a fresh
# empty dir; {macos_sh} gets the fixture script above.
CASES = [
    # hook
    ("scripts/chezmoi_drift_check.py", [], {0}),
    # git-setup (read-only + the self-contained signing selftest)
    ("skills/git-setup/scripts/git_audit.py", [], {0}),
    ("skills/git-setup/scripts/git_identity.py", [], {0}),
    ("skills/git-setup/scripts/verify_signing.py", ["--self-test"], {0, 1}),
    # dotfiles (chezmoi may or may not be installed)
    ("skills/dotfiles/scripts/chezmoi_status.py", [], {0}),
    ("skills/dotfiles/scripts/dotfiles_inventory.py", [], {0, 1}),
    ("skills/dotfiles/scripts/secret_scan.py", ["{tmp}"], {0}),
    # runtime-versions
    ("skills/runtime-versions/scripts/tool_resolve.py", ["node"], {0}),
    ("skills/runtime-versions/scripts/detect_managers.py", [], {0}),
    ("skills/runtime-versions/scripts/mise_status.py", [], {0}),
    ("skills/runtime-versions/scripts/shell_resolve.py", ["zsh", "node"], {0}),
    # shell-sync
    ("skills/shell-sync/scripts/dump_env.py", ["zsh", "path"], {0}),
    ("skills/shell-sync/scripts/path_doctor.py", ["zsh"], {0}),
    ("skills/shell-sync/scripts/mirror_plan.py", [], {0, 3}),
    ("skills/shell-sync/scripts/mirror_drift.py", [], {0, 1, 3}),
    # macos-defaults (read-only reads + the dry-run apply against a fixture)
    ("skills/macos-defaults/scripts/defaults_read.py", ["dock"], {0}),
    ("skills/macos-defaults/scripts/drift_audit.py", ["{macos_sh}"], {0, 1}),
    ("skills/macos-defaults/scripts/defaults_apply.py", ["{macos_sh}"], {0}),
    # ghostty (rc 3 when ghostty absent — the documented exit)
    ("skills/ghostty-config/scripts/ghostty_doctor.py", [], {0, 1, 3}),
    ("skills/ghostty-config/scripts/config_audit.py", [], {0, 1, 3}),
    ("skills/ghostty-config/scripts/font_check.py", [], {0, 1, 3}),
    ("skills/ghostty-config/scripts/show_effective.py", [], {0, 3}),
    # nvim (scripts degrade cleanly when nvim is absent)
    ("skills/nvim-config/scripts/nvim_env.py", [], {0}),
    ("skills/nvim-config/scripts/nvim_lua.py", ["print('smoke')"], {0}),
    # ssh-config (empty temp ssh-dir: exercises the stat/keygen/agent wrappers safely)
    ("skills/ssh-config/scripts/ssh_config_audit.py", [], {0}),
    ("skills/ssh-config/scripts/key_audit.py", ["{tmp}"], {0}),
    ("skills/ssh-config/scripts/agent_status.py", ["{tmp}"], {0}),
    # brew (env/pins are the fast read-only sections; rc 3 when brew absent)
    ("skills/brew-doctor/scripts/brew_audit.py", ["env"], {0, 3}),
    ("skills/brew-doctor/scripts/brew_audit.py", ["pins"], {0, 3}),
    # terminal-theme
    ("skills/terminal-theme/scripts/theme_status.py", [], {0, 1}),
    ("skills/terminal-theme/scripts/theme_list.py", ["nord"], {0, 3}),
    ("skills/terminal-theme/scripts/theme_swatch.py", [], {0}),
    # identity-profiles (rc 1 = a 🔴 gap on this machine, a documented outcome).
    # --probe-remote is deliberately NOT smoked: it makes an outbound authenticated
    # connection, which a test suite must never do on the user's behalf.
    ("skills/identity-profiles/scripts/profile_audit.py", [], {0, 1}),
    ("skills/identity-profiles/scripts/profile_resolve.py", [], {0}),
    # credential-store (rc 1 = a 🔴 finding / no usable store — both documented outcomes)
    ("skills/credential-store/scripts/credential_audit.py", [], {0, 1}),
    ("skills/credential-store/scripts/credential_audit.py", ["--all-assignments"], {0, 1}),
    ("skills/credential-store/scripts/store_status.py", [], {0, 1}),
]


def _materialize(arg: str, tmp_path: Path) -> str:
    if arg == "{tmp}":
        d = tmp_path / "empty"
        d.mkdir(exist_ok=True)
        return str(d)
    if arg == "{macos_sh}":
        f = tmp_path / "macos.sh"
        f.write_text(_FIXTURE_MACOS_SH)
        return str(f)
    return arg


@pytest.mark.parametrize(
    ("script", "args", "allowed"),
    CASES,
    ids=[f"{Path(s).parent.parent.name}:{Path(s).name}:{' '.join(a) or '(bare)'}" for s, a, _ in CASES],
)
def test_entry_point_runs_clean(script: str, args: list[str], allowed: set[int], tmp_path: Path):
    argv = [sys.executable, str(ROOT / script)] + [_materialize(a, tmp_path) for a in args]
    proc = subprocess.run(
        argv, capture_output=True, text=True, timeout=120,
        stdin=subprocess.DEVNULL, cwd=str(ROOT),
    )
    assert "Traceback" not in proc.stderr, f"{script} crashed:\n{proc.stderr}"
    assert proc.returncode in allowed, (
        f"{script} exited {proc.returncode} (allowed {sorted(allowed)})\n"
        f"stdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"
    )

    # SHAPE, not just "didn't crash". Every bug this suite failed to catch produced
    # perfectly well-formed exit-0 output that was missing or misreporting a key. An
    # exit code alone would sail through a parser that silently stopped emitting facts
    # after an upstream tool changed its format.
    expected = EXPECTED_KEYS.get(script)
    if expected and proc.returncode == 0:
        missing = [k for k in expected if k not in proc.stdout]
        assert not missing, (
            f"{script} exited 0 but its report is missing {missing} — a parser can go "
            f"silent without failing.\nstdout:\n{proc.stdout[-2000:]}"
        )


# Keys each script must emit in a successful run. Deliberately a few load-bearing keys
# per script, not the whole surface: enough that a parser going quiet is caught, few
# enough that legitimate output changes don't cause churn.
EXPECTED_KEYS: dict[str, list[str]] = {
    "skills/git-setup/scripts/git_audit.py": ["git_version", "identity.name", "gap"],
    "skills/git-setup/scripts/git_identity.py": ["query_path", "user.email", "in_repo"],
    "skills/dotfiles/scripts/chezmoi_status.py": ["chezmoi_installed"],
    "skills/runtime-versions/scripts/tool_resolve.py": ["context", "node_owner"],
    "skills/runtime-versions/scripts/detect_managers.py": ["mise_present", "brew_runtimes"],
    "skills/runtime-versions/scripts/mise_status.py": ["mise_installed"],
    "skills/shell-sync/scripts/path_doctor.py": ["entry"],
    "skills/macos-defaults/scripts/defaults_read.py": ["com.apple.dock"],
    "skills/nvim-config/scripts/nvim_env.py": ["nvim_version", "plugin_manager", "config_dir"],
    "skills/ssh-config/scripts/ssh_config_audit.py": ["== permissions ==", "known_hosts"],
    "skills/ssh-config/scripts/agent_status.py": ["== agent =="],
    "skills/terminal-theme/scripts/theme_status.py": ["ghostty", "coordinated"],
    "skills/identity-profiles/scripts/profile_resolve.py": ["query_path", "user.email", "key_match"],
    # Both keys appear whether or not this machine declares any profile: the empty case
    # prints `profiles (none…)` + `gaps undetermined`, the populated one `profile …` +
    # `-- gaps --`. So a machine with no profiles still proves the report isn't silent.
    "skills/identity-profiles/scripts/profile_audit.py": ["profile", "gaps"],
    "skills/credential-store/scripts/credential_audit.py": ["scanned", "summary", "finding"],
    "skills/credential-store/scripts/store_status.py": ["store.keychain", "recommended"],
}
