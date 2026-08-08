# architecture-review — a Claude Code plugin

Review and stress-test architecture plans, system-design proposals, and ADRs before implementation.
The plugin grounds findings in the proposal and repository, distinguishes blockers from improvements,
turns vague promises into enforceable invariants, and recommends a risk-ordered vertical slice.

The [`review-architecture-plan`](skills/review-architecture-plan/SKILL.md) skill starts read-only. A
review never edits the reviewed repository, commits, pushes, deploys, provisions infrastructure, or
runs paid model evaluations. Implementation remains a separate, explicitly requested task.

## Install

Add this repository as a marketplace, then install the independent plugin:

```text
/plugin marketplace add johnplantada/claude-skills
/plugin install architecture-review@devenv-marketplace
```

For local development, point Claude Code at the plugin directory:

```bash
claude --plugin-dir ./plugins/architecture-review
```

## Use

Ask naturally, for example:

- “Review this architecture plan and tell me whether it is ready to implement.”
- “Stress-test this ADR against the repository's current schemas and deployment workflow.”
- “Evaluate the trust boundaries, deletion semantics, failure modes, and rollout gates in this proposal.”

The skill does not replace ordinary code-diff review, proofreading, implementation work, or
open-ended plan generation.

## Validate

```bash
claude plugin validate plugins/architecture-review
./check
```

The evaluation cases are fixtures for optional live-model testing. The default `./check` is
deterministic and does not spend model credits.
