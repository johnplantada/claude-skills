# Update transaction

Separate analysis from mutation. A plan is a metadata-only proposal bound to the exact current
workspace and explicitly selected source bytes; apply is the sole deterministic mutation step.

## Plan contract

Use [../assets/update-plan.template.json](../assets/update-plan.template.json). Bind every plan to:

- opaque update ID;
- base private snapshot and workspace revision;
- canonical digest of the governed working bundle;
- stable logical source ID and current occurrence ID;
- locally calculated hash of the explicitly selected file;
- impacted claim and approved-record IDs; and
- planned invalidation actions.

The private plan may retain the selected path so apply can recheck it. Never include that path or
source text in terminal or JSON reports.

## Apply invariants

1. Acquire `locks/update.lock` without replacing an existing lock.
2. Recompute plan, bundle, pointer, revision, and source hashes.
3. Refuse stale or altered input without mutation.
4. Append a content-free `started` event.
5. Create a new occurrence linked by `supersedes_occurrence_id`.
6. Mark prior dependent evidence stale and remove active approvals.
7. Mark dependent approved records stale and public records retracted.
8. Block private serving before exposing any potentially stale answer.
9. Write structured files through restrictive temporary siblings and atomic replacement.
10. Record `awaiting_owner_review`, `completed`, or `failed`; replay of a completed no-op is a no-op.

The current private snapshot remains an audit artifact during review but must not be served while
state is blocked. A validated replacement snapshot clears the block.

## Delta review

Apply performs no model-assisted interpretation. After apply, repeat the builder's two content
stages over only the change:

1. inspect and organize the selected document delta;
2. compare it with affected claims and conflicts;
3. ask only questions needed by the changed coverage map;
4. collect exact owner decisions for revised claims; and
5. validate and compile a replacement snapshot.

Changed bytes do not prove that earlier wording remains true. Formatting-only or materially
equivalent changes may be restored only after owner review; the model cannot make that decision
binding by itself.

## Recovery and deletion

- A stale plan is discarded and replanned.
- A lock conflict makes the second writer stop.
- A failed apply leaves serving blocked if invalidation may have begun and reports the session for
  review.
- Deletion propagates through evidence, approvals, records, snapshots, public artifacts, evaluation
  answers, and locally controlled caches.
- Event logs retain only opaque metadata permitted by the owner's retention policy.
