---
name: review-architecture-plan
description: "Review and stress-test architecture plans, system-design proposals, technical plans, and ADRs for implementation readiness. Use when asked to evaluate or challenge a proposed architecture, compare a proposal with repository contracts or implementation, or assess trust boundaries, data models, APIs, lifecycle behavior, reliability, security, privacy, scale, or rollout sequencing—even when the user does not explicitly name this skill. Do not use for ordinary code-diff review, proofreading, implementation-only requests, or generating a plan from scratch without a review request."
---

# Review an Architecture Plan

Read [the review method](references/review-method.md) and
[the report template](references/report-template.md) completely before performing the review.

## Keep the review within bounds

- Begin read-only. Do not modify the reviewed repository unless the user separately asks for implementation.
- Never commit, push, deploy, provision infrastructure, or spend model credits as part of a review.
- Treat a code-diff review, proofreading request, implementation-only task, or request to create a plan from
  scratch as a different task. Do not expand it into an architecture review without a review request.
- Follow repository instructions and access constraints. Do not bypass unavailable evidence.
- Verify externally changing claims with current primary or official sources when browsing is available.
  Label the claim `Unverified` when current verification is unavailable.

## Perform the review

1. Read the complete proposal and identify its stated scope, goals, constraints, exclusions, and decisions.
2. Inspect relevant repository instructions, ADRs, schemas, interfaces, APIs, data models, implementations,
   publication or deployment workflows, tests, operational documentation, and configuration boundaries.
3. Maintain an evidence ledger that separates implemented behavior, proposed behavior, assumptions,
   unresolved decisions, and externally changing facts. Never present one category as another.
4. Compare the proposal with canonical repository contracts. Call out competing sources of truth and exact
   conflicts using `path:line` evidence.
5. Apply every relevant dimension in the review method. Mark a dimension not applicable or unverified rather
   than silently skipping it.
6. Prioritize findings by consequence. Reserve blockers for issues that must be resolved before safe
   implementation; do not promote wording or style preferences into architectural blockers.
7. Convert ambiguous lifecycle, safety, and reliability promises into enforceable invariants with acceptance
   evidence. Identify the decision owner when the repository does not settle a material choice.
8. Recommend the smallest end-to-end vertical slice that tests the riskiest assumptions and can be reversed.
9. Produce the report with the exact top-level structure and finding fields in the report template.

Record inspected files, commands, external sources, and verification gaps. End with one concrete next action.
