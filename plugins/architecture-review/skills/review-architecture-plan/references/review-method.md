# Architecture Review Method

Use this rubric to test implementation readiness. Apply it proportionally to the proposal, but account for
every dimension by reviewing it, marking it not applicable, or naming the missing evidence.

## Contents

1. [Establish scope and authority](#1-establish-scope-and-authority)
2. [Build the evidence ledger](#2-build-the-evidence-ledger)
3. [Test requirements and contracts](#3-test-requirements-and-contracts)
4. [Test trust, provenance, and privacy](#4-test-trust-provenance-and-privacy)
5. [Test lifecycle and failure behavior](#5-test-lifecycle-and-failure-behavior)
6. [Test boundaries and operating fitness](#6-test-boundaries-and-operating-fitness)
7. [Test delivery and reversibility](#7-test-delivery-and-reversibility)
8. [Prioritize findings](#8-prioritize-findings)
9. [Write invariants and decisions](#9-write-invariants-and-decisions)
10. [Choose the vertical slice](#10-choose-the-vertical-slice)
11. [Verify external claims](#11-verify-external-claims)
12. [Check review completeness](#12-check-review-completeness)

## 1. Establish scope and authority

- Read repository-level and directory-level instructions before interpreting local evidence.
- Read the whole proposal, including appendices, diagrams, linked ADRs, and declared non-goals.
- Identify the system boundary, actors, protected assets, dependencies, environments, and change surface.
- Record which documents claim authority over schemas, interfaces, lifecycle rules, release processes, and
  operational behavior. Treat duplicate authorities as a risk until precedence is explicit.
- Inspect read-only evidence from architecture documents, schemas, interfaces, APIs, data models, existing
  implementations, tests, operations documentation, configuration, and publication or deployment workflows.
- Bound the review explicitly when relevant evidence is missing, inaccessible, generated, or outside scope.

Do not infer that a plan is implemented because it uses present tense. Do not infer that current code is the
intended contract when a canonical schema or ADR says otherwise.

## 2. Build the evidence ledger

Classify every material claim before judging it:

| Class | Meaning | Required treatment |
|---|---|---|
| Implemented | Observable in current repository behavior or contract | Cite the exact file and line; note test coverage |
| Proposed | Introduced by the plan and not yet implemented | Cite the proposal; assess compatibility and completeness |
| Assumption | Relied on without adequate evidence | State how to validate or retire it |
| Unresolved decision | Multiple viable choices remain | Name the owner, deadline, and downstream contracts affected |
| External fact | Depends on changing behavior outside the repository | Verify currently or label `Unverified` |

Prefer primary evidence over summaries. When evidence conflicts, cite both sides, identify the canonical source
if one exists, and make reconciliation a required decision. Use `relative/path:line` references so another
reviewer can reproduce each important finding.

## 3. Test requirements and contracts

### Functional and non-functional requirements

- Trace each stated user or system outcome through inputs, state transitions, outputs, and failure outcomes.
- Expose missing latency, availability, throughput, capacity, durability, recovery, consistency, security,
  privacy, accessibility, compliance, data residency, and cost targets that influence the design.
- Demand measurable ranges and workload shapes instead of words such as “fast,” “scalable,” or “reliable.”
- Distinguish a genuinely deferred requirement from an unstated one that invalidates a design choice.

### Canonical contracts and sources of truth

- Identify the canonical schema, interface, API, state machine, configuration, and release artifact.
- Detect duplicate writers, projections treated as authorities, caches without invalidation rules, and plan text
  that silently replaces an existing contract.
- Compare field names, types, nullability, identifiers, uniqueness, versioning, enum values, defaults, migration
  paths, compatibility windows, and publication semantics.
- Flag exact conflicts between the proposal and repository contracts. Do not accept “the implementation will
  be updated” without identifying ordering, compatibility, data migration, and rollback behavior.

### Alternatives and trade-offs

- Require explicit alternatives for consequential choices, including retaining the current design.
- Compare choices against the same requirements and operating assumptions.
- Preserve a decision when the evidence supports it; do not invent alternatives merely to fill a section.

## 4. Test trust, provenance, and privacy

### Trust and authorization boundaries

- Map callers, services, operators, tenants, external processors, and credentials across each trust boundary.
- Specify authentication, authorization subject, resource scope, tenant isolation, privilege changes, and the
  enforcement point for every sensitive action.
- Check that internal network location, possession of an identifier, or a UI restriction is not treated as
  authorization.

### Provenance and evidence integrity

- Track where data, decisions, transformations, and generated results originate.
- Require immutable or tamper-evident evidence where auditability matters.
- Distinguish observed facts from derived values and model-generated claims. Preserve version, timestamp,
  input, and policy provenance needed to reproduce a result.
- Check whether retries, edits, reprocessing, and imports can overwrite or detach evidence.

### Privacy and information lifecycle

- Inventory collected data, sensitive fields, purpose, legal or policy basis, recipients, and transformations.
- Trace retention, revocation, deletion, erasure, backup expiry, cache invalidation, derived artifacts, logs,
  indexes, replicas, analytics, and external processors.
- Define whether deletion is synchronous, asynchronous, or best effort; name completion evidence and maximum
  latency. Separate access revocation from physical erasure.
- Minimize data sent across trust boundaries. Require redaction or tokenization before external processing when
  the external party does not need the original.

## 5. Test lifecycle and failure behavior

- Model creation, update, publication, suspension, revocation, deletion, restoration, migration, and terminal
  states. Make illegal transitions explicit.
- Trace partial failure at every multi-step boundary. Identify the authoritative state after each failure.
- Define timeouts, retry eligibility, backoff, idempotency scope, deduplication window, poison-message handling,
  dead-letter behavior, replay, and operator recovery.
- State ordering and consistency requirements. Distinguish transactional atomicity from eventual convergence.
- Check concurrent writers, stale reads, lost updates, split-brain ownership, and compensating action failure.
- Require crash-safe behavior around irreversible external effects. Do not rely on exactly-once delivery without
  an enforceable protocol and evidence.

## 6. Test boundaries and operating fitness

### Storage and data-model fitness

- Check access patterns, cardinality, growth, indexing, constraints, partitioning, retention, migrations, and
  repairability against the chosen store.
- Preserve stable identifiers and lineage across projections, reprocessing, and schema versions.
- Prefer database-enforced constraints for invariants that must hold across writers.

### API and service boundaries

- Check cohesion, ownership, synchronous coupling, error contracts, pagination, versioning, compatibility,
  rate limits, cancellation, and backpressure.
- Reject service boundaries that only mirror organizational charts or create distributed transactions without
  a compensating design.

### Observability and sensitive logging

- Define metrics, structured events, traces, audit records, correlation identifiers, alerts, and operator
  actions for each critical state transition and failure mode.
- Prohibit secrets, credentials, raw sensitive payloads, and unnecessary personal data in logs or traces.
- Specify redaction, access controls, sampling, retention, and deletion behavior for telemetry.
- Ensure the system can prove an invariant without exposing the protected data itself.

### Operating limits

- Quantify workload volume, burstiness, payload size, fan-out, concurrency, hot keys, storage growth, geographic
  distribution, cost envelope, and latency budget.
- Identify behavior at limits: reject, queue, degrade, shed load, or fall back. Require capacity alarms and
  safe defaults.

## 7. Test delivery and reversibility

### Testing and release gates

- Require contract, migration, authorization, failure-injection, load, privacy-lifecycle, recovery, and
  observability tests where relevant.
- Define objective promotion gates, owners, evidence location, rollback triggers, and post-release checks.
- Separate “test exists” from “test protects the contract under production-like conditions.”

### Implementation phases

- Order phases by risk retired, not by component convenience.
- Keep schema and API changes backward compatible through the stated rollout window.
- Use shadowing, dual reads, controlled writes, backfills, and feature flags only with reconciliation and removal
  plans. Avoid dual writes without a declared authority and repair mechanism.
- Make destructive migrations, external effects, and irreversible data disclosures the last gated step.

## 8. Prioritize findings

Assign priority from consequence and required timing:

- `P0` — Prevents safe operation or creates an immediate catastrophic security, privacy, integrity, or loss risk.
- `P1` — Must be resolved before implementation or rollout because the plan is contradictory, unsafe, or not
  testable enough to make the readiness decision.
- `P2` — Important non-blocking improvement that reduces operational, maintenance, or future-change risk.

Place only `P0` and `P1` findings under **Blocking findings**. Place `P2` findings under **Important
improvements**. Do not inflate naming, prose, formatting, technology taste, or an equivalent alternative into
a blocker unless it creates a concrete consequence under stated requirements.

For every finding, cite evidence, explain the consequence as a plausible failure, and state the minimum
resolution needed. Merge symptoms that share one root decision. Keep unrelated risks separate.

## 9. Write invariants and decisions

Turn each ambiguous safety or lifecycle promise into a rule with:

1. **Scope and trigger** — identify the entity, actor, and event.
2. **Invariant** — state what must always or never be true in observable terms.
3. **Enforcement point** — name the schema constraint, transaction, authorization policy, service boundary, or
   workflow gate that makes the rule hold.
4. **Acceptance evidence** — specify a deterministic test, metric, audit record, or reconciliation query.
5. **Failure response** — define behavior when enforcement or verification fails.

List unresolved choices separately with an owner, decision deadline, alternatives, trade-offs, and affected
contracts. Do not disguise an open decision as an invariant.

## 10. Choose the vertical slice

- Identify the assumption with the highest combination of consequence and uncertainty.
- Select the thinnest real path through input, authorization, canonical state, processing, output, telemetry,
  and failure recovery that can test that assumption.
- Use production-shaped interfaces and representative data without requiring full scale or broad rollout.
- Define entry criteria, measurable pass/fail gates, cleanup, and rollback before starting.
- Prefer one end-to-end slice over completing several disconnected component layers.
- Stop expansion after the slice yields the evidence needed for the next architecture decision.

## 11. Verify external claims

- Browse only when allowed and when a claim depends on current external behavior, limits, pricing, retention,
  security guarantees, regulations, standards, or product capabilities.
- Prefer the current primary source: official documentation, specification, source repository, regulator, or
  first-party policy.
- Record the source and access date. State any inference that combines the source with repository evidence.
- Mark the claim `Unverified` when browsing is unavailable, access is blocked, or no authoritative current
  source supports it. Turn consequential unverified claims into a validation gate.

## 12. Check review completeness

Before issuing the verdict, confirm that the review:

- separates implemented, proposed, assumed, unresolved, and external claims;
- cites exact local evidence for important findings;
- identifies conflicts and competing sources of truth;
- covers applicable functional, non-functional, trust, data, lifecycle, failure, privacy, observability,
  operating-limit, testing, and rollout concerns;
- distinguishes blockers from improvements by consequence;
- states enforceable invariants and decision owners;
- recommends a risk-ordered, reversible vertical slice;
- lists inspected files, commands, sources, and verification gaps; and
- has not modified the reviewed repository or performed delivery actions.
