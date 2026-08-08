# Evidence and candidate model

Evidence attaches to atomic claims, never to a project or document as a whole. Keep the source
occurrence separate from its content hash: identical bytes from two origins are still one piece of
independent content.

## Contents

- [Source roles](#source-roles)
- [Evidence ceilings](#evidence-ceilings)
- [Candidate shape](#candidate-shape)
- [Evidence edges](#evidence-edges)
- [Metrics and attribution](#metrics-and-attribution)
- [Approval digest](#approval-digest)

## Source roles

- `discovery`: finds a topic or source; provides no factual support.
- `self_report`: records an owner statement; supports only self-reported status by itself.
- `corroboration`: independently supports a factual claim.
- `authoritative`: a record with appropriate authority for the fact it supports.
- `style_only`: informs voice or form; never proves a fact.

Never infer independence from the number of links. Repeated resumes, copied biographies, circular
summaries, and multiple statements from the same underlying account do not multiply support.

For each source occurrence, retain its opaque source/occurrence IDs, content hash, any
`derived_from_source_ids`, an `independence_group`, and `independence_review_state`. Only
`owner_confirmed` independence can contribute to moderate or strong support. Reject circular source
derivation graphs.

## Evidence ceilings

Calculate the maximum defensible strength from active, consented evidence. The owner may downgrade
but never upgrade beyond the ceiling.

| Ceiling | Minimum defensible support |
|---|---|
| `self_reported` | At least one eligible `self_report` edge. |
| `limited` | One eligible non-style factual source. |
| `moderate` | Two owner-confirmed independent non-self-report sources with distinct content hashes. |
| `strong` | The moderate rule, including an `authoritative` source with bounded provenance. |

An edge is ineligible when its source is deleted, retracted, consent-withdrawn, not processing-
consented, or missing. `discovery` and `style_only` edges never raise factual strength.
Unknown independence, a shared independence group, a shared derivation root, or a duplicate content
hash cannot support `moderate` or `strong`. Self-reports do not count as independent documentary
corroboration.

## Candidate shape

Use [../assets/claims.template.json](../assets/claims.template.json). Each candidate includes:

- stable `claim_id`, positive integer `revision`, exact `wording`, and `category`;
- dates and entities;
- source evidence edges; keep reserved `depends_on_claim_ids` empty in version 1;
- `proposed_strength` and calculated `max_strength`;
- uncertainty, conflict IDs, privacy and third-party flags;
- complete metric qualification when a metric is present;
- proposed visibility and review state;
- an approval snapshot only after owner approval.

Use categories: `profile`, `timeline`, `employment`, `education`, `project`, `skill`,
`accomplishment`, `decision`, `principle`, `failure_lesson`, `voice`, `faq`, `boundary`, and
`contact_path`.

Keep visibility to `private`, `restricted`, `internal`, or `public_candidate`. Public is a separate
publication decision, not a candidate visibility.

## Evidence edges

A source edge records:

- `source_occurrence_id`;
- exact coordinate or an honest provenance limitation;
- bounded supporting excerpt only when safe and appropriate;
- optional span hash;
- source role;
- lifecycle status (`active`, `stale`, or `retracted`).

Never store an entire document as an excerpt. Do not include confidential or third-party text merely
to make a claim look better supported.

Compose private narratives from approved records rather than claim-as-evidence links. Version 1
prohibits claim dependencies because a dependency's revision, approval, and deletion lifecycle
would otherwise create hidden support. Source derivation links remain explicit and acyclic.

## Metrics and attribution

Treat “led,” “owned,” “architected,” “delivered,” and similar verbs as ambiguous until the owner
defines their actual decisions and authority. Separate a team result from the owner's contribution.

Store each conflict in `candidates/conflicts.json` and reference it from every named claim; require
the conflict's `claim_ids` and each claim's `conflicts` list to agree. An unresolved link in either
direction blocks publication.

For a metric record scope, unit, denominator, population, and time window. If any are unknown, mark
them unknown in `uncertainty` and keep the wording qualified. Do not reconcile mismatched metrics by
choosing one silently.

## Approval digest

Bind approval to a canonical digest of:

- claim ID, revision, wording, visibility, confidentiality, metric, and evidence edges;
- referenced source occurrence IDs, content hashes, consent, lifecycle, confidentiality,
  derivation/independence state, third-party status, and publication rights.

Editing any bound field or referenced source snapshot changes the digest and invalidates approval.
The validator calculates this digest deterministically; do not hand-author a convenient replacement.
