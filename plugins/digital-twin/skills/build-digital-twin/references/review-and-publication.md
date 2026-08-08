# Owner review and publication

Review atomic claims in small batches. Show exact wording, source roles and coordinates, proposed
and maximum evidence strength, conflicts, uncertainty, privacy flags, visibility, and publication
rights. Never hide a weak area behind a polished project narrative.

## Review outcomes

- `edit`: create a new revision and invalidate any prior approval.
- `split`: create separate atomic candidates with their own evidence.
- `merge`: create a new candidate only when the combined wording remains atomic; reject otherwise.
- `reject`: preserve the audit decision but make the candidate ineligible.
- `defer`: leave unresolved and exclude from compilation.
- `approve`: bind the exact reviewed state to an approval snapshot.

Record decisions append-only in `reviews/decisions.jsonl` without copying unnecessary source text.
Each line contains `decision_id`, `claim_id`, `claim_revision`, `action`, the current
`evidence_graph_digest` (required for `approve`), and `decided_at`. File order determines the latest
decision. A later edit, rejection, deferral, or retraction invalidates any earlier inline approval
and dependent record.

## Approval snapshot

Require all of:

- exact final wording and claim revision;
- current evidence-graph digest;
- owner-selected evidence strength no higher than the calculated ceiling;
- visibility and confidentiality;
- publication-right status;
- complete metric scope or explicit qualification;
- review date;
- schema and policy version.

Approval is invalid if wording, revision, evidence, source hash/lifecycle/consent, visibility,
confidentiality, rights, metric scope, schema, or policy changes. Re-review the new state; never patch
the digest to preserve a stale approval.

The digest detects drift; it is not a cryptographic signature or proof of the owner's identity.
Detached owner signatures are outside version 1.

## Approved records

`publication/approved-records.json` is the private compilation index. Each record references a valid
approved claim and repeats only the exact approved wording, revision, strength, visibility, and
approval digest. It may contain private/internal records because the file itself is private.

Context documents may be generated only from this index. When a record becomes invalid, remove or
mark it stale before regenerating documents.

## Public publication manifest

Use [../assets/publication-manifest.template.json](../assets/publication-manifest.template.json).
Keep `owner_review_state` as `draft` while reviewing. A record can enter the manifest only when:

- its candidate visibility is `public_candidate`;
- the claim approval is valid and current;
- publication rights are `confirmed`;
- confidentiality is `public` or `sanitized`;
- no source is stale, deleted, consent-withdrawn, confidential, restricted, or substantially third-
  party;
- the owner separately sets the publication manifest to `approved` and promotes the record to
  `public`.

That promotion is a new owner decision. Never infer it from public source material or a
`public_candidate` label.

## Preview before finish

Show:

- exact public wording and why it is eligible;
- excluded records and the rule excluding each;
- invalidated approvals and their changed dependency;
- privacy warnings and unresolved rights;
- the approved contact/next-step path;
- identity and authority disclaimer.

Never publish automatically. Return files for owner inspection and describe the separate action the
owner would need to take in their downstream system.
