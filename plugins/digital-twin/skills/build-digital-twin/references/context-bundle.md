# Portable context bundle

Compile only records whose owner approval remains valid. Keep human-readable context, private
provenance, and publication candidates separate so a downstream consumer does not receive more than
its intended scope.

## Contents

- [Workspace layout](#workspace-layout)
- [Human-readable context](#human-readable-context)
- [Machine-readable layers](#machine-readable-layers)
- [Coverage and conflicts](#coverage-and-conflicts)
- [Validation contract](#validation-contract)
- [Portability boundary](#portability-boundary)

## Workspace layout

```text
<workspace>/
  sources/source-manifest.json
  interviews/<session-id>/
    consent.json
    transcript.md
    corrections.json
    candidate-claims.json
  candidates/
    claims.json
    conflicts.json
    coverage.json
  reviews/decisions.jsonl
  context/
    profile.md
    timeline.md
    projects/
    decisions/
    principles.md
    voice.md
    boundaries.md
    faq.md
  publication/
    approved-records.json
    publication-manifest.json
  evals/
    private-evals.json
    reports/
```

The initializer creates directories and starter manifests, not source files, transcripts, or
generated narratives.

## Human-readable context

Generate owner-reviewable drafts for:

- profile and career/education timeline;
- employment and project dossiers;
- skills and accomplishments with evidence boundaries;
- stories and decision records;
- principles, trade-off preferences, failures, reversals, and lessons;
- communication/voice guidance;
- FAQs, privacy/refusal boundaries, and authority limits;
- approved contact or next-step path.

A decision record should state situation, constraints, considered options, applied principles,
trade-offs, decision, the owner's actual role/authority, result, and what changed afterward.

Do not insert a sentence into context merely because it sounds plausible. Every factual sentence
must map to a current approved record. Clearly label interpretation and style guidance.

## Machine-readable layers

- `sources/source-manifest.json`: private source/consent/lifecycle metadata.
- `candidates/claims.json`: private candidate graph, including approvals and stale states.
- `publication/approved-records.json`: private approved compilation index.
- `publication/publication-manifest.json`: minimal separately approved public selection.
- `evals/private-evals.json`: owner-reviewed evaluation cases and draft/approved golden answers.

Keep raw paths, excerpts, transcripts, and source hashes out of public publication data.

## Coverage and conflicts

Report coverage by category rather than one completeness number:

- timeline;
- projects;
- decisions;
- outcomes;
- principles;
- failures and lessons;
- voice;
- boundaries;
- evaluation questions.

For each category report approved, pending, weak/self-reported, conflicted, and missing counts plus
the next best question/source. Keep conflicts open until the owner resolves or deliberately defers
them.

## Validation contract

Run:

```bash
python3 scripts/validate_bundle.py /explicit/workspace --format json
```

The validator checks starter/document shape, IDs, enums, revisions, references, evidence ceilings,
duplicate hashes, stale/deleted evidence, reserved dependency fields, append-only owner decisions,
approval digests, approved-record links, publication eligibility, and metadata-only privacy
findings.

Exit codes:

- `0`: valid bundle;
- `1`: validation errors or privacy findings;
- `2`: usage, path, or unreadable-JSON error.

Validation is a preflight, not proof that every fact is true or every secret is detected. Owner
review remains authoritative.

## Portability boundary

Do not depend on this plugin repository, a private schema service, a portfolio implementation, or a
connector. Use relative bundle-internal references and the declared schema version. The bundle may
feed another system only after that consumer accepts the privacy, visibility, and authority model.
