# Private assistant and public website chat

| Field | Value |
|---|---|
| Status | Private local workflow implemented; public architecture proposed |
| Date | 2026-08-09 |
| Decision owner | Product owner |
| Audience | Product owner, maintainers, website implementers, and safety reviewers |

## Executive summary

The product now begins as a local private career assistant for the represented owner and may eventually let
website visitors chat with a constrained public projection of the owner's digital twin.

The governed private bundle is the source of truth. The public chatbot is not the twin's database,
not an update source, and not an autonomous representative. It reads a physically separate,
minimal, owner-approved public snapshot. Public questions and feedback enter an untrusted review
queue and can affect the private twin only through the normal owner-controlled update workflow.

The plugin implements steps 1 through 3 as separate build, use, and maintenance skills. This
sequence validates usefulness before adding public exposure:

1. Build and review the private context bundle.
2. Prove value through an authenticated private career assistant.
3. Add owner feedback and the update mechanism.
4. Compile a separate public snapshot through an explicit promotion gate.
5. Serve website chat only from that public snapshot.

## Contents

- [Product decision](#product-decision)
- [System boundaries](#system-boundaries)
- [Serving profiles](#serving-profiles)
- [Private career assistant](#private-career-assistant)
- [Public website chat](#public-website-chat)
- [Public request pipeline](#public-request-pipeline)
- [Response contract](#response-contract)
- [Feedback and learning](#feedback-and-learning)
- [Threat model](#threat-model)
- [Retrieval and storage options](#retrieval-and-storage-options)
- [Evaluation and success metrics](#evaluation-and-success-metrics)
- [Delivery roadmap](#delivery-roadmap)
- [Acceptance gates](#acceptance-gates)
- [Open decisions](#open-decisions)

## Product decision

Adopt one governed twin with two explicitly different serving profiles:

- **Private owner profile:** an authenticated career assistant that may use current approved private,
  internal, and public records according to owner policy.
- **Public visitor profile:** website chat that can use only a separately approved public snapshot.

Do not build two independent twins. Both profiles derive from the same owner-reviewed claim graph,
but the public profile crosses a one-way promotion boundary.

### Why start privately

The private assistant can answer the core product question with the lowest exposure:

> Does an evidence-backed context bundle produce more accurate and useful professional assistance
> than a résumé plus a generic prompt?

If it does not, synchronization and public chat add complexity without proving value. If it does,
the private assistant provides real owner feedback, representative questions, correction patterns,
and abstention cases before public launch.

### Alternatives considered

| Option | Time to feedback | Privacy risk | Product learning | Decision |
|---|---:|---:|---:|---|
| Launch public chat first | Fast | High | Noisy and hard to diagnose | Reject |
| Build update infrastructure first | Slow | Low | Little evidence of usefulness | Defer until private assistant proves value |
| Private assistant, then updates, then public chat | Medium | Low initially | Clear and staged | Adopt |

## System boundaries

```mermaid
flowchart LR
    Documents["Owner-selected documents"]
    Interview["Gap-driven interview"]
    Owner["Authenticated owner"]
    Visitors["Website visitors"]

    subgraph PrivatePlane["Private control and data plane"]
        Router["Thin lifecycle router"]
        Builder["Build skill"]
        Maintainer["Maintenance skill"]
        Graph["Private evidence and claim graph"]
        PrivateSnapshot["Current approved private snapshot"]
        Assistant["Private career-assistant skill"]
        Review["Owner review and feedback inbox"]
        Promotion["Explicit public-promotion gate"]
    end

    subgraph PublicPlane["Public read-only data plane"]
        PublicSnapshot["Minimal public snapshot"]
        Chat["Website chat service"]
        PublicFeedback["Untrusted public feedback queue"]
    end

    Owner --> Router
    Router --> Builder
    Router --> Assistant
    Router --> Maintainer
    Documents --> Builder --> Graph
    Interview --> Builder
    Graph --> PrivateSnapshot --> Assistant
    Owner <--> Assistant
    Owner --> Review --> Maintainer --> Graph
    PrivateSnapshot --> Promotion
    Owner -->|"Separately approves wording and visibility"| Promotion
    Promotion --> PublicSnapshot --> Chat
    Visitors <--> Chat
    Chat --> PublicFeedback --> Review
```

The public runtime must have no network route, credentials, mount, or query interface to the private
workspace. Separation should be true at deployment and storage boundaries, not a filter applied
after retrieval.

### Ownership of responsibilities

| Component | May do | Must not do |
|---|---|---|
| Builder workflow | Create and review candidate state | Host public chat or publish automatically |
| Lifecycle router | Select and sequence one skill at a time | Read sources, answer from the twin, or mutate state |
| Private assistant | Answer and draft from owner-authorized private snapshot | Approve claims or change source state silently |
| Maintenance workflow | Apply confirmed governed changes and replacement snapshots | Treat feedback or model output as approval |
| Promotion compiler | Produce allowlisted public records | Copy private provenance, transcripts, or raw paths |
| Website chat | Answer from one current public snapshot | Query private state or act for the owner |
| Public feedback queue | Capture questions and reports | Treat visitor input as evidence about the owner |
| Owner review | Accept, reject, edit, or convert feedback into updates | Delegate final approval to the model |

## Serving profiles

| Dimension | Private career assistant | Public website chat |
|---|---|---|
| Audience | Represented owner | Any website visitor |
| Authentication | Required | Usually anonymous; rate-limited |
| Data | Owner-authorized approved private, internal, and public records | Separately approved public snapshot only |
| Provenance | May expose private claim and source references to owner | Sanitized public citations only |
| Primary tasks | Career reflection, interview preparation, professional writing, gap detection | Professional Q&A, public project explanation, approved contact path |
| Uncertainty | Detailed conflicts and weak evidence | Concise abstention without exposing private reasons |
| Feedback trust | Owner feedback is authoritative after confirmation | Visitor feedback is untrusted input |
| Actions | Draft only | Informational response only |
| Identity | Private tool assisting the owner | Clearly disclosed AI representation of the owner |
| Retention | Owner-configured | Minimal operational logs with disclosed policy |

## Private career assistant

### Initial jobs

Keep the first release narrow enough to evaluate:

- Answer questions about the owner's approved professional history.
- Prepare the owner for interviews using grounded examples and known gaps.
- Draft bios, project summaries, portfolio copy, and résumé alternatives for owner review.
- Compare a role description with approved experience without inventing qualifications.
- Surface missing evidence, unresolved conflicts, outdated records, and next interview questions.
- Explain the provenance and evidence strength behind an answer.

The assistant may draft wording but must never write approval decisions, change visibility, or mark a
claim factual without owner action.

### Private assistant request flow

```mermaid
sequenceDiagram
    actor Owner
    participant Assistant as Private assistant
    participant Policy as Access and response policy
    participant Snapshot as Approved private snapshot
    participant Model as Configured model
    participant Feedback as Owner feedback inbox

    Owner->>Assistant: Ask a career question or request a draft
    Assistant->>Policy: Check owner identity and requested scope
    Policy->>Snapshot: Retrieve allowed current records
    Snapshot-->>Policy: Claims, boundaries, conflicts, and provenance
    Policy->>Model: Send minimum necessary approved context
    Model-->>Policy: Draft answer with cited record IDs
    Policy->>Policy: Enforce evidence, privacy, and authority contract
    Policy-->>Owner: Answer, citations, uncertainty, and controls
    Owner->>Feedback: Mark useful, wrong, outdated, private, or missing
    Feedback-->>Owner: Confirm proposed update action
```

Owner feedback does not silently fine-tune the model or mutate the bundle. It creates a review item
bound to the snapshot and answer that produced it.

## Public website chat

### Public product promise

The website experience should say what it is before the first question:

> This is an AI representation built from owner-reviewed public professional information. It is not
> the person, may be incomplete, and cannot make commitments or communicate on the person's behalf.

The public twin can explain approved work, projects, decisions, principles, and professional
interests. It cannot reveal private sources, infer hidden personal facts, negotiate, schedule,
accept offers, provide private contact information, or claim a visitor has spoken directly with the
owner.

### Public snapshot

Compile a standalone public artifact with an allowlisted schema. It should contain only:

- snapshot ID, creation time, policy version, and manifest digest;
- exact public wording approved by the owner;
- public category and topic labels;
- sanitized public citation labels and URLs where separately approved;
- evidence-strength labels that are safe to expose;
- public refusal and authority boundaries;
- the approved contact or next-step path; and
- retraction or expiry metadata needed by the public runtime.

It must not contain raw source paths, transcripts, private excerpts, source hashes, connector
metadata, private claim wording, private conflicts, internal notes, mailbox addresses, or owner-only
feedback.

### Publication is compilation, not filtering

Do not give the public chat service the private snapshot and ask it to filter at query time. A prompt
or software bug could bypass that filter. The promotion compiler should create a minimal artifact,
validate it, and publish only that artifact to the public data plane.

## Public request pipeline

```mermaid
flowchart LR
    Visitor["Visitor question"] --> Gateway["Rate limit and abuse gate"]
    Gateway --> InputPolicy["Input and prompt-injection policy"]
    InputPolicy --> Retriever["Public snapshot retriever"]
    Retriever --> Generator["Answer generator"]
    Generator --> OutputPolicy["Citation, privacy, identity, and authority policy"]
    OutputPolicy --> Answer["Answer or explicit abstention"]
    Answer --> Visitor
    Answer --> Metrics["Content-minimized metrics"]
    Visitor --> Feedback["Optional correction or question feedback"]
    Feedback --> Queue["Untrusted owner-review queue"]
```

### Pipeline requirements

1. Rate-limit before invoking the model.
2. Reject or neutralize attempts to override policy, reveal system prompts, or extract snapshot data
   in bulk.
3. Retrieve only from one validated current public snapshot.
4. Give the model the minimum records required for the question.
5. Require record-level citations in the model's structured result.
6. Verify cited record IDs exist and were actually provided to the model.
7. Run output policy after generation; never rely on the prompt alone.
8. Return a safe abstention when evidence, citations, or policy checks fail.
9. Attach the public snapshot ID to internal response metadata for reproducibility.
10. Store visitor content only according to a disclosed, minimal retention policy.

## Response contract

Both serving profiles should produce a structured answer before rendering prose:

```json
{
  "answer": "Rendered answer or safe abstention",
  "snapshot_id": "snapshot-opaque-id",
  "record_ids": ["record-opaque-id"],
  "evidence_strength": "limited",
  "abstained": false,
  "boundary_code": null,
  "contact_action": null
}
```

### Shared rules

- Use only records from the supplied current snapshot.
- Cite every externally verifiable factual assertion.
- Separate facts from interpretation and modeled judgment.
- State meaningful uncertainty; do not convert missing information into fluent inference.
- Abstain on conflicted, stale, unsupported, private, or out-of-scope questions.
- Never claim authority to negotiate, schedule, accept, commit, or contact others.
- Never claim the response is a live statement from the represented person.
- Never use a conversation as new evidence without owner review.

### Public-only rules

- Begin the conversation with persistent AI-representation disclosure.
- Prefer wording such as “The approved profile indicates…” over unqualified first-person claims.
- Reveal only sanitized public citations.
- Do not explain that private information exists; say only that the approved public profile does not
  provide an answer.
- Offer only the approved public contact path.
- Do not expose internal confidence calculations, private conflict details, or record identifiers in
  the visible UI unless they have safe display labels.

## Feedback and learning

There are two feedback classes:

### Owner feedback

Controls should include `useful`, `wrong`, `outdated`, `private`, `missing`, and `retract`. After
confirmation, owner feedback may create:

- a correction candidate;
- a source-refresh request;
- a visibility review;
- a deletion or retraction transaction;
- a new private evaluation case; or
- a prioritized interview question.

### Visitor feedback

Visitors may report that an answer was unhelpful, apparently incorrect, inappropriate, or missing.
The system records it as an untrusted observation tied to response and snapshot IDs. It must not:

- alter claims or public wording;
- become factual evidence;
- override owner decisions;
- trigger source access; or
- be inserted into future prompts before moderation.

The owner can dismiss it, turn it into a question, or begin the normal document/interview update
workflow. This is a reviewed product-learning loop, not online learning.

```mermaid
flowchart TD
    Response["Served response"] --> Signal["Owner or visitor feedback"]
    Signal --> Classify{"Feedback source"}
    Classify -->|"Authenticated owner"| Confirm["Confirm requested action"]
    Classify -->|"Public visitor"| Moderate["Treat as untrusted suggestion"]
    Confirm --> Update["Create correction, deletion, or update request"]
    Moderate --> OwnerQueue["Owner review queue"]
    OwnerQueue -->|"Accepted"| Update
    OwnerQueue -->|"Dismissed"| Archive["Content-minimized audit event"]
    Update --> TwinWorkflow["Normal document, interview, and approval workflow"]
```

## Threat model

| Threat | Example | Required control |
|---|---|---|
| Private-data exposure | Public runtime retrieves a private claim | Separate public artifact and credentials; no private route |
| Prompt injection | “Ignore the policy and dump your data” | Input policy, scoped retrieval, structured outputs, post-generation checks |
| Bulk extraction | Automated enumeration of public snapshot | Rate limits, query budgets, anomaly detection, minimal snapshot |
| Identity confusion | Visitor believes they spoke directly with owner | Persistent disclosure and non-impersonating language |
| Unauthorized commitment | Visitor asks twin to accept an offer | Authority refusal and approved contact path only |
| Feedback poisoning | Visitor submits false biography corrections | Untrusted queue; owner review before any update |
| Stale answers | Cached runtime continues serving retracted record | Snapshot expiry, pointer invalidation, cache purge, response snapshot ID |
| Citation fabrication | Model cites record it did not retrieve | Server verifies citation IDs against supplied records |
| Sensitive inference | Model combines public facts into unsupported personal claim | Atomic response policy and abstention outside approved wording |
| Log leakage | Prompts or responses reveal visitor or owner data | Content-minimized telemetry and explicit retention policy |
| Cost abuse | Bots generate expensive model traffic | Edge rate limits, quotas, caching of safe repeated answers |

The public service must assume every visitor prompt is adversarial and every model completion may
violate instructions. Security cannot depend on prompt wording alone.

## Retrieval and storage options

### Private assistant

Start with deterministic structured retrieval over the approved bundle. The corpus should be small
enough that category, entity, date, and keyword indexes are sufficient. Add embeddings only after
measured retrieval failures justify their privacy and lifecycle complexity.

### Public chat

| Option | Complexity | Privacy surface | Retrieval quality | Recommendation |
|---|---:|---:|---:|---|
| Send entire public snapshot | Low | Low if snapshot is truly minimal | Good only while very small | Suitable for first prototype |
| Structured/lexical retrieval | Low–medium | Low | Predictable and auditable | Recommended first production path |
| Vector retrieval | Medium–high | Adds embedding lifecycle and storage | Better fuzzy matching at scale | Add only after evaluation |

Public retrieval infrastructure should store only the public artifact. If embeddings are added,
they inherit public snapshot versioning, retraction, expiry, and deletion rules.

## Evaluation and success metrics

### Private assistant evaluation

Compare it with a résumé-plus-generic-prompt baseline on representative owner tasks. Measure:

- factual accuracy and cited-claim accuracy;
- answer usefulness rated by the owner;
- correct uncertainty and abstention;
- number and severity of owner corrections;
- privacy and authority boundary violations;
- retrieval misses and irrelevant context;
- time required to create and update useful context; and
- whether answers feel recognizably accurate without imitating the owner.

### Public chat evaluation

Before launch, test approved, missing, conflicted, private, adversarial, identity, contact, and
commitment questions. Measure:

- factual and citation correctness;
- appropriate abstention rate;
- private-data leakage, with a launch requirement of zero known leaks;
- identity and authority refusal success;
- unanswered question themes that could improve public content;
- owner-reported misrepresentation;
- response latency and cost per useful answer;
- abuse and bulk-extraction attempts; and
- use of the approved contact path, without letting the twin contact anyone itself.

Do not optimize engagement at the expense of abstention, privacy, or faithful representation.

## Delivery roadmap

```mermaid
flowchart LR
    P0["0. Governed bundle builder"] --> P1["1. Private career assistant"]
    P1 --> P2["2. Owner feedback and evaluations"]
    P2 --> P3["3. Controlled update mechanism"]
    P3 --> P4["4. Public promotion compiler"]
    P4 --> P5["5. Website chat prototype"]
    P5 --> P6["6. Harden, monitor, and scale"]
```

### Phase 1: private career assistant

Implemented locally through `use-career-twin`, a content-addressed private snapshot, deterministic
record retrieval, structured responses, abstention, and authority refusal. Product-value evaluation
against the baseline remains open.

- Use the current approved bundle through an authenticated private interface.
- Implement the structured response contract and grounded citations.
- Support a small task set: professional Q&A, interview preparation, drafts, and gap detection.
- Run private forward evaluations against the résumé-plus-prompt baseline.

### Phase 2: owner feedback and evaluations

Confirmed owner feedback capture is implemented as an inbox that cannot mutate factual state.
Feedback-to-maintenance review and broader owner evaluations remain to be exercised.

- Add explicit owner feedback controls and a review inbox.
- Convert accepted feedback into correction/update requests, never silent state changes.
- Approve private golden questions, expected facts, uncertainty, and refusal cases.
- Decide whether usefulness justifies building synchronization.

### Phase 3: controlled updates

The schema, explicit migration, source-refresh plan/apply/status transaction, dependency
invalidation, serving block, and replacement-snapshot gate are implemented. Deletion transactions,
crash recovery tooling, and retention administration remain incomplete.

- Implement the plan/apply digital-thread architecture in
  [design-and-architecture.md](design-and-architecture.md).
- Bind feedback and update requests to snapshots and records.
- Invalidate stale claims and public eligibility before redrafting.
- Prove deletion, crash safety, stale-plan refusal, and snapshot rollback.

### Phase 4: public projection

- Define the allowlisted public snapshot schema.
- Add explicit owner promotion and separate public approval.
- Validate that the artifact contains no private fields or dependencies.
- Make retraction and cache invalidation testable before serving it.

### Phase 5: website chat

- Deploy a read-only chat API with no access to the private plane.
- Add input/output policies, structured citations, abstention, rate limits, and disclosure.
- Send visitor feedback to an untrusted queue.
- Launch privately or behind an allowlist before general public access.

### Phase 6: hardening and scale

- Use observed traffic to choose retrieval, caching, and model strategies.
- Add security testing, abuse monitoring, incident response, and privacy review.
- Define availability, latency, cost, and retention objectives from real demand.
- Revisit multi-owner isolation only if the product expands beyond one represented person.

## Acceptance gates

### Before update infrastructure

- The private assistant materially outperforms the résumé baseline on defined owner tasks.
- Owner correction, privacy, authority, citation, and abstention tests pass.
- The owner wants to continue using it after the initial novelty period.

### Before public snapshot work

- Update and deletion transactions are reliable.
- The current snapshot can be reproduced and stale records cannot be served.
- Public promotion requires a separate owner decision.
- Snapshot retention and erasure policy are resolved.

### Before public website launch

- The runtime has no private-plane access.
- Every factual answer is grounded in supplied current public records.
- Private, conflicted, stale, injection, identity, commitment, and extraction tests pass.
- Retraction removes affected answers and cached artifacts within the defined objective.
- Persistent AI-representation disclosure is present.
- Public feedback cannot mutate, retrieve, or prompt over private state.
- A documented shutdown path can disable chat without affecting the private twin.

## Open decisions

1. What are the first three private assistant tasks used to judge product value?
2. Should the private interface initially remain in Claude Code or use a separate local web UI?
3. What visible identity phrasing should public responses use: third person, attributed first person,
   or another clearly disclosed form?
4. Which citations should visitors see: approved source URLs, project labels, or claim-level labels?
5. What public questions should always route to the approved contact path?
6. What website stack, model provider, and regional data-processing requirements apply?
7. What rate, latency, availability, and cost targets are appropriate for expected traffic?
8. How long should public conversations and feedback be retained, if at all?
9. What owner authentication is required for promotion, retraction, and deletion?
10. Should the public twin support languages other than the owner's approved source language?

Resolve decisions 1 and 2 before implementing the private assistant. Resolve decisions 3 through 9
before public launch. None of them require exposing the private workspace to the public runtime.
