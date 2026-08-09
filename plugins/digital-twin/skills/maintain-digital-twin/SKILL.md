---
name: maintain-digital-twin
description: "Maintain an existing consenting owner's governed professional digital twin through explicit source refreshes, confirmed corrections, visibility reviews, retractions, deletions, freshness checks, and replacement snapshots. Use when an owner says information changed, an answer is wrong or outdated, a selected document has a new version, or data must be withdrawn. Plan before mutation, apply conservative invalidation, rerun the two-stage document-delta and gap-interview workflow, require owner reapproval, and never answer ordinary career questions or operate public website chat."
---

# Maintain a governed digital twin

Apply changes only through an explicit owner-controlled transaction. A conversation, model output,
or feedback item is never sufficient authority to mutate the bundle.

## Establish scope

1. Confirm the represented owner's identity and the explicit workspace path.
2. Classify the request as source refresh, correction, visibility review, retraction, deletion, or
   freshness check.
3. Restate the exact mutation and likely dependencies. Obtain explicit confirmation before apply.
4. For a changed source, require the owner to select the exact file; never rediscover it by scanning.

Read [references/update-transaction.md](references/update-transaction.md) before planning or
applying an update. Reuse the builder's privacy, evidence, review, and deletion rules.

If status reports schema `0.1.0`, migrate explicitly before any update. Migration invalidates old
policy-bound approvals rather than silently reinterpreting them:

```bash
python3 scripts/migrate_workspace.py /explicit/workspace --confirm --format json
```

## Plan before mutation

For a selected source refresh, create a metadata-only plan:

```bash
python3 scripts/update_bundle.py plan /explicit/workspace \
  --source-id source-opaque-id --file /explicit/selected/file
```

Show the base snapshot, no-op or changed status, impacted claim/record counts, and planned actions.
Never print the selected path, source content, excerpts, or suspected secret values in a report.

Run `status` for freshness or recovery checks:

```bash
python3 scripts/update_bundle.py status /explicit/workspace --format json
```

## Apply only after confirmation

```bash
python3 scripts/update_bundle.py apply /explicit/workspace \
  --plan update-opaque-id --confirm
```

Apply must verify the plan digest, source hash, base bundle digest, current snapshot, and workspace
revision under a single-writer lock. A changed source creates a new occurrence; it never overwrites
the previous occurrence or increases independent corroboration. Conservatively invalidate affected
edges, approvals, records, publications, and evaluations. Block private serving until a valid
replacement snapshot is compiled.

## Complete the delta workflow

After deterministic invalidation:

1. Review and organize only the selected document delta.
2. Produce changed candidates, conflicts, coverage gaps, and a focused interview agenda.
3. Interview only against affected gaps or conflicts, using text by default and voice optionally.
4. Present atomic revisions for owner edit, rejection, deferral, or approval.
5. Validate the complete working bundle with the builder's `scripts/validate_bundle.py`.
6. Compile a replacement snapshot with the builder's `scripts/compile_private_snapshot.py` only
   after validation passes.

If the owner abandons review, leave serving blocked rather than returning stale facts. For
deletion, also remove affected retained snapshots and locally controlled caches according to the
owner's retention decision.

## Finish

Report the update/session ID, old and new source occurrence IDs, invalidated dependency counts,
current serving state, unresolved review work, and the next smallest action. Do not answer from the
twin until status reports a ready current private snapshot.
