# Verification — prove the shells agree

After any sync or PATH change, resolve the environment in **both** shells and compare. Never
declare done from reading the generated file.

> **`scripts/shell_diff.py` is the verifier** — PATH set diff, startup cleanliness, and tool
> reachability in one clean-environment call. It reports and skips gracefully if fish is absent.
> The bash below is what it runs — reference, not what you retype.

## Diff both shells in one call

```bash
scripts/shell_diff.py node cargo go rustc python3    # add any tools you care about
```
Output (greppable): `only_in_zsh<TAB>/dir` / `only_in_fish<TAB>/dir` (PATH set diff),
`startup<TAB><shell><TAB>clean|issues|absent`, and `tool<TAB><name><TAB>zsh=…<TAB>fish=…`.

- **PATH set diff.** For a canonical→mirror sync, expect **`only_in_fish` empty** (the mirror has
  everything canonical does). `only_in_zsh` is normally non-empty — macOS `path_helper` gives zsh a
  few transient dirs fish never runs; that's expected.
- **Startup.** Each shell must start with no error/parse lines. `absent` = fish not installed.
- **Tool reachability.** Flag tools that resolve in one shell but not the other, or resolve to
  **different paths** (e.g. `node` via nvm in zsh vs asdf in fish) — exactly the divergence sync
  should eliminate. `-` = not found; `?` = fish absent.

Need a single value? `scripts/dump_env.py zsh exports | grep CLAUDE_CODE_SETTINGS_FILE` (and the
same for `fish`) checks one env var in each shell.

<details><summary>Under the hood (what shell_diff.py runs)</summary>

```bash
# PATH, one entry per line, sorted for set-comparison
zsh  -l -i -c 'printf "%s\n" $path'          | sort -u > /tmp/z_path
fish -l    -c 'for p in $PATH; echo $p; end' | sort -u > /tmp/f_path
comm -23 /tmp/z_path /tmp/f_path   # only in zsh
comm -13 /tmp/z_path /tmp/f_path   # only in fish  (empty = mirror in sync)

# startup must be clean
zsh  -l -i -c 'exit' 2>&1 | grep -iE 'error|not found|parse|command not found'
fish -l    -c 'exit' 2>&1 | grep -iE 'error|unknown|expected|missing'

# tool reachability in each shell
for t in node cargo go rustc python3; do
  echo "$t zsh=$(zsh -l -i -c "command -v $t")  fish=$(fish -l -c "command -v $t")"
done
```
Every command runs under `env -i HOME="$HOME" TERM=xterm <bin> …` (see Notes) so the parent
session can't pollute the result.
</details>

## Notes

- **Audit in a CLEAN environment.** Running `zsh -l -i` from inside another shell **inherits the
  parent's `$PATH`**, so the resolved PATH is polluted with entries your login config never added
  (e.g. a sandbox's asdf/go dirs). Wipe the environment to get the TRUE login PATH:
  ```bash
  env -i HOME="$HOME" TERM=xterm /bin/zsh          -l -i -c 'printf "%s\n" $path'
  env -i HOME="$HOME" TERM=xterm /opt/homebrew/bin/fish -l    -c 'for p in $PATH; echo $p; end'
  ```
  Call the shell by full path (a wiped env has no PATH to find it). Use this form for every
  PATH/env comparison — otherwise you'll "fix" phantom entries.
- **Expect the mirror to lack a few system-managed dirs.** zsh login gets transient entries from
  macOS `path_helper` (cryptex `/var/run/...`, `/usr/ucb`, `/pkg/env/global/bin`) that fish does
  not run. "Only in zsh = those" is normal; what matters is **"only in fish" is empty**.
- Use `-l` (login) so `.zprofile` / `path_helper` apply; `-i` (interactive) so `.zshrc` / fish
  interactive config load. If a prompt hangs headlessly, drop `-i` or set `PS1=`/`fish_greeting=`.
- Always back up config files before edits; keep a `git diff` or timestamped `.bak` as the record.
