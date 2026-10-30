# Architecture Review Report Template

Use these top-level sections in this order. Keep them even when a section has no findings. Do not add another
top-level section unless the user explicitly requests a different report format.

# Verdict

State exactly one readiness verdict, followed by a brief rationale:

- **Ready** — implementation may proceed under the documented gates.
- **Ready with required changes** — the direction is sound, but named changes must be incorporated before the
  affected phase begins.
- **Not ready** — blocking contradictions, unsafe gaps, or unresolved foundational decisions prevent responsible
  implementation.

# What is strong

Identify specific decisions, constraints, evidence, or trade-offs worth preserving. Cite repository or proposal
evidence where available. Do not invent praise to balance the report.

# Blocking findings

Use one subsection per `P0` or `P1` finding. If none exist, write `None.`

## [P0|P1] Short consequence-oriented title

- **Priority:** `P0` or `P1` and why this timing is required.
- **Evidence:** Cite exact `relative/path:line` references and classify each claim as implemented, proposed,
  assumed, unresolved, or external.
- **Consequence:** Describe the plausible failure, affected asset or actor, and operating condition.
- **Required resolution:** State the minimum contract, decision, design change, or validation evidence needed.

# Important improvements

Use the same finding format with `P2` priority for non-blocking risks and maintainability concerns. If none exist,
write `None.` Do not include editorial preferences without a concrete consequence.

# Required invariants and decisions

For each invariant, state:

- **Trigger and scope:** Entity, actor, and event.
- **Invariant:** Observable rule that must always or never hold.
- **Enforcement:** Constraint, transaction, authorization policy, service, or release gate.
- **Acceptance evidence:** Deterministic test, metric, audit evidence, or reconciliation query.
- **Failure response:** Safe behavior when enforcement or verification fails.

For each unresolved decision, state the owner, deadline, alternatives, trade-offs, and affected contracts.

# Recommended rollout

Give a risk-ordered sequence. Start with the smallest end-to-end vertical slice that validates the riskiest
assumption. For each phase, state:

1. the risk or assumption being tested;
2. the minimum end-to-end scope;
3. entry criteria and measurable promotion gate;
4. observability and failure test;
5. rollback, cleanup, or reversibility boundary.

# Verification performed

- **Inspected files:** List files and relevant ranges.
- **Commands:** List read-only commands used.
- **External sources:** Link current primary or official sources and include access dates.
- **Not verified:** List missing, inaccessible, unstable, or out-of-scope evidence. Label consequential external
  claims `Unverified`.
- **Changes made:** State `None — review performed read-only.` unless the user separately requested implementation.

# Recommended next action

Give one concrete action that retires the most important remaining risk or decision. Name the expected owner and
the evidence that will show completion when known.
