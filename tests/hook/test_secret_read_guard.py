"""Tests for the PreToolUse secret-read guard — the MECHANICAL layer of the contract.

The pinned findings: (1) a private key / credentials file is denied for every covered
ingestion route (Read, Grep target, Bash readers, `chezmoi cat`), in raw AND chezmoi
source encodings; (2) the ssh files the ssh-config skill must legitimately touch
(config, known_hosts, *.pub, allowed_signers) stay readable — a guard that breaks the
setup workflow gets disabled, which is worse than narrow scope.
"""

import secret_read_guard as g

# --- is_secret_path: the classification core ------------------------------------

def test_ssh_private_keys_are_secret_paths():
    assert g.is_secret_path("/Users/me/.ssh/id_ed25519")
    assert g.is_secret_path("/Users/me/.ssh/id_rsa")
    assert g.is_secret_path("/Users/me/.ssh/work_key")  # unknown name in .ssh = key


def test_chezmoi_source_encodings_are_covered():
    assert g.is_secret_path("/src/private_dot_ssh/id_ed25519")
    assert g.is_secret_path("/src/dot_ssh/id_rsa")
    assert g.is_secret_path("/src/private_dot_netrc")


def test_ssh_safe_files_are_not_secret_paths():
    assert not g.is_secret_path("/Users/me/.ssh/config")
    assert not g.is_secret_path("/Users/me/.ssh/id_ed25519.pub")
    assert not g.is_secret_path("/Users/me/.ssh/known_hosts")
    assert not g.is_secret_path("/Users/me/.ssh/known_hosts.old")
    assert not g.is_secret_path("/Users/me/.ssh/authorized_keys")
    assert not g.is_secret_path("/Users/me/.ssh/allowed_signers")


def test_non_ssh_secret_locations():
    assert g.is_secret_path("/Users/me/.netrc")
    assert g.is_secret_path("/Users/me/.aws/credentials")
    assert g.is_secret_path("/Users/me/.config/gh/hosts.yml")
    assert g.is_secret_path("/etc/certs/server.pem")


def test_ordinary_files_are_allowed():
    assert not g.is_secret_path("/Users/me/.zshrc")
    assert not g.is_secret_path("/Users/me/project/README.md")
    assert not g.is_secret_path("/Users/me/.config/starship.toml")
    # contains a secret only by CONTENT — path classification must not guess
    assert not g.is_secret_path("/Users/me/dot_config/env.sh")


def test_lookalike_dirs_do_not_trip_the_ssh_rule():
    assert not g.is_secret_path("/Users/me/mossh/id_ed25519")
    assert not g.is_secret_path("/Users/me/.sshx/id_rsa")


# --- evaluate: per-tool routing --------------------------------------------------

def test_read_of_private_key_is_denied():
    assert g.evaluate("Read", {"file_path": "/Users/me/.ssh/id_ed25519"}) is not None


def test_read_of_pub_and_config_is_allowed():
    assert g.evaluate("Read", {"file_path": "/Users/me/.ssh/id_ed25519.pub"}) is None
    assert g.evaluate("Read", {"file_path": "/Users/me/.ssh/config"}) is None


def test_grep_targeting_a_secret_file_is_denied():
    assert g.evaluate("Grep", {"path": "/Users/me/.netrc", "pattern": "token"}) is not None
    assert g.evaluate("Grep", {"path": "/Users/me/project", "pattern": "token"}) is None


def test_bash_readers_on_secret_paths_are_denied():
    assert g.evaluate("Bash", {"command": "cat ~/.ssh/id_rsa"}) is not None
    assert g.evaluate("Bash", {"command": "grep -n token /Users/me/.aws/credentials"}) is not None
    assert g.evaluate("Bash", {"command": "chezmoi cat ~/.netrc"}) is not None


def test_bash_non_readers_and_clean_paths_are_allowed():
    assert g.evaluate("Bash", {"command": "cat README.md"}) is None
    assert g.evaluate("Bash", {"command": "ls -la ~/.ssh"}) is None  # listing != reading
    assert g.evaluate("Bash", {"command": "chmod 600 ~/.ssh/id_ed25519"}) is None
    assert g.evaluate("Bash", {"command": "ssh-keygen -lf ~/.ssh/id_ed25519.pub"}) is None


def test_unknown_tools_and_garbage_input_are_allowed():
    assert g.evaluate("Edit", {"file_path": "/Users/me/.ssh/id_rsa"}) is None
    assert g.evaluate("Bash", {}) is None
    assert g.evaluate("Bash", {"command": "cat 'unterminated"}) is None
