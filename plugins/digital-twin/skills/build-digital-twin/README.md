# build-digital-twin

This Claude Code skill guides a consenting owner from selected career documents and a focused
follow-up interview to a private, evidence-backed professional context bundle. It keeps facts
atomic, distinguishes self-report from corroboration, surfaces conflicts, requires exact owner
approval, and propagates source deletion to dependent claims and publication candidates.

## Start

Ask Claude:

> Review and organize my resume and project documents first, then interview me to fill the gaps.

The default path is:

1. Define purpose, audience, privacy, authority, and retention boundaries.
2. Inventory and review only the documents the owner selects.
3. Organize documentary candidates, conflicts, and coverage gaps.
4. Complete a gap-driven voice-or-text interview.
5. Approve exact records and compile a portable private bundle.
6. Validate privacy, provenance, evidence ceilings, lifecycle state, and publication eligibility.

## Safety guarantees

- No model-generated claim is approved by default.
- Private source content is not read until model-processing disclosure and explicit consent.
- Sources are explicit; the skill does not enumerate broad accounts or folders.
- Secret/privacy findings identify a category and field path, never the suspected value.
- Voice is transcript capture only; the skill stores no audio and performs no voice cloning.
- The result represents the owner but cannot impersonate or act for them.

## Deterministic helpers

Run from this skill directory:

Initialize with `python3 scripts/init_workspace.py /private/path/my-twin`.

Validate with `python3 scripts/validate_bundle.py /private/path/my-twin --format json`.

Both helpers use only the Python standard library. `init_workspace.py` refuses non-empty or git
worktree destinations by default. `validate_bundle.py` never prints matched secret values.

Part of the [Digital Twin Builder](../../README.md) plugin.
