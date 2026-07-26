# Recorded fixtures — real output the machine can no longer reproduce

`capture_fixtures.py` records live tool output, but some formats only appear in states a
healthy machine isn't in: `brew outdated` prints nothing once everything is upgraded, and
a `Lazy! sync` log only shows plugin-update rows when plugins actually update.

Those are exactly the states where today's bugs lived. Each file here was observed
**verbatim** in a real run (provenance in the file header), then preserved so the parser
tests keep covering the format after the machine moved on.

Rules:

- **Verbatim only.** These are recordings, not inventions. If you can't cite where a line
  came from, it belongs in a hand-written unit test, clearly labelled as hypothetical —
  not here. The whole point of this directory is that its content is ground truth.
- **Same redaction as captures** (home path, username, emails, internal hostnames).
- When a tool version bumps and you can reproduce the state again, prefer re-capturing
  over keeping a stale recording.
