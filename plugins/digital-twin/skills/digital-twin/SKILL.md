---
name: digital-twin
description: "Route ambiguous or multi-stage requests about a consenting owner's professional digital twin to the build, private-use, or maintenance workflow. Use when the owner asks generally to work with ‘my digital twin,’ is unsure which lifecycle operation applies, or combines creation, career assistance, correction, refresh, retraction, or deletion in one request. This is a thin orchestrator: it selects and sequences sibling skills but never reads owner sources, answers from the twin, or mutates bundle state itself."
---

# Route digital-twin work

Choose exactly one primary workflow at a time. Preserve the governed private bundle as the handoff
contract between workflows; do not merge their authority boundaries for convenience.

## Route the request

| Owner intent | Primary skill | Result |
|---|---|---|
| Create a new twin or deliberately rebuild one | [build-digital-twin](../build-digital-twin/SKILL.md) | Reviewed private bundle and compiled snapshot |
| Ask career questions, prepare, compare, or draft | [use-career-twin](../use-career-twin/SKILL.md) | Grounded answer or draft plus optional feedback |
| Refresh a source, correct facts, change visibility, retract, or delete | [maintain-digital-twin](../maintain-digital-twin/SKILL.md) | Owner-reviewed update and replacement snapshot |

When intent is unclear, ask one short routing question. Do not begin document processing merely
because the owner says “digital twin.”

## Sequence cross-workflow requests

1. Finish the current workflow at a safe checkpoint.
2. Name the proposed handoff and the state it will carry.
3. Obtain any confirmation required by the receiving workflow.
4. Read and follow the receiving sibling skill from its first applicable step.

Examples:

- “Use this new résumé, then prepare me for an interview” routes to maintenance first. Use the
  career twin only after a valid replacement private snapshot is current.
- “That answer is wrong” routes first to private-use feedback capture. Route to maintenance only
  after the owner confirms a factual correction or source refresh.
- “Build my twin and put it on my website” finishes the private build first. Public projection and
  website deployment are separate later work and never receive the private workspace.

## Enforce orchestration limits

- Never bypass consent, source selection, owner review, validation, or approval gates.
- Never let the private-use skill edit claims, decisions, visibility, evidence, or snapshots.
- Never let visitor input become evidence or an update request without owner review.
- Never treat a router decision as authorization to read a path or mutate a workspace.
- Never route public website traffic through these private skills.
- Stop after the receiving workflow reaches its own safe terminal state; do not chain unrelated
  actions automatically.
