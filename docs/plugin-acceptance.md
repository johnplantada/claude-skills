# Installed-plugin acceptance

On released main `4970cef`, Claude Code 2.1.309 accepted an isolated local marketplace add
and `devenv@devenv-marketplace` install and listed version 0.2.0 as enabled. Strict validation
found unquoted hook paths; executing that command from a plugin folder with spaces failed
before the guard ran. Release 0.2.1 quotes those paths and gives caches a new version.

`tests/hook/test_packaged_commands.py` executes the actual registered shell commands from
a spaced fixture path: synthetic Read/Grep/Bash denials, readable public-key control,
fail-open malformed input, Stop drift adapter, absent chezmoi, and absent Python. It also
executes two helpers through single-skill symlinks with their tools missing. These are
package/adapter checks, not Claude dispatch or all-skill semantic checks.

The install-only CLI tests use an isolated `CLAUDE_CONFIG_DIR` and `--bare` to avoid
keychain reads and model requests. `--bare` skips hooks, so those tests do not prove
client-side hook dispatch. Normal-session namespaced routing, natural-language selection,
and hook events remain pending a consumer with an authorized model setup.

Direct `tests_eval` prompts read `SKILL.md`; they do not establish plugin installation,
automatic routing, namespacing, or hook activation. Unit and fixture passes must be
reported separately from machine smoke and paid agent evals. A receipt with zero
executed tests is `not_executed`, never behavioral proof. Skipped counts and unavailable
provenance fields must remain visible.

Before claiming an installed-plugin pass:

1. Use a disposable workspace and a clean, isolated Claude configuration/profile supported
   by the installed CLI. Record the exact CLI version, OS, Python, repo SHA and dirty diff,
   invocation, model, selected cases, executed/passed/failed/skipped counts, and receipt path.
   Confirm the CLI's isolation mechanism from its help before use; do not reuse personal
   credentials or configs. Paid evals require separate authorization.
2. Load the repo with `--plugin-dir` and verify the plugin is listed, a namespaced skill
   resolves, and a natural-language task selects the intended skill. Record actual tool
   events and final output. Include a single-skill symlink control: neither plugin hook
   should be claimed active for that installation.
3. Create only synthetic canaries in the disposable workspace: fake `home/.ssh/id_ed25519`,
   `.aws/credentials`, `.netrc`, and `gh/hosts.yml`, plus readable public-key/config controls.
   Never use the real home directory or real secrets. Confirm recognized `Read`, explicit
   `Grep`, and supported direct Bash reader attempts receive the guard's deny decision;
   verify canary contents are absent from the captured transcript. These checks prove
   only the tested paths and tool forms. Separately document the known fail-open and
   unsupported-read limitations; do not claim general containment.
4. Verify the Stop hook's reminder against a disposable chezmoi source/destination with a
   harmless synthetic drift. Confirm it is non-blocking and changes no files.
5. Preserve receipts and transcripts privately, review failures and skips, and have an
   independent reviewer inspect the evidence before promoting a verification claim.

Python compatibility: metadata currently declares 3.9+, but CI runs 3.12 only. The
settings reference uses stdlib `tomllib` and explicitly requires 3.11+ for those examples.
A future change should either validate the declared 3.9 minimum in a compatible tooling
matrix and provide a tested settings path, or propose a documented minimum-version change.
Neither a dependency install nor a requirement increase is part of this patch.
