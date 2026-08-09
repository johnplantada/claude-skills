---
name: use-career-twin
description: "Use a consenting owner's existing approved private career-twin snapshot for grounded professional Q&A, interview preparation, role comparison, biography and portfolio drafts, provenance explanation, gap detection, and owner feedback capture. Use when the owner wants help from an already built twin. Read only the current private snapshot and never build the twin, edit claims, approve facts, change visibility, apply updates, publish records, impersonate the owner, or make commitments."
---

# Use the private career twin

Treat the current compiled private snapshot as the only factual answer source. Assist the owner;
never claim to be the owner and never turn a conversation into evidence or silent learning.

## Preconditions

1. Confirm that the requester is the represented owner or is using an owner-authorized private
   session.
2. Ask for the explicit private workspace path. Do not search for a workspace.
3. Run the read-only snapshot query helper before answering:

```bash
python3 scripts/career_twin.py query /explicit/workspace "owner question" --format json
```

4. Stop if the workspace has no current snapshot, the snapshot fails integrity checks, or serving
   is blocked pending maintenance review.

Read [references/private-serving-contract.md](references/private-serving-contract.md) before
answering, drafting, comparing a role, or recording feedback.

## Answer and draft

- Use only records returned from the current snapshot.
- Cite every factual statement with its approved record ID.
- Distinguish approved facts, interpretation, and suggested wording.
- State relevant uncertainty and abstain when approved evidence is absent.
- For interview preparation, select grounded examples and name known gaps; do not invent a story.
- For role comparison, separate demonstrated evidence, partial overlap, missing evidence, and
  unknowns.
- For drafts, label the result owner-reviewable and preserve citations outside polished copy when
  appropriate.
- Explain evidence strength or provenance when asked, without exposing it to anyone outside the
  private owner session.

Always state that the twin represents the owner but is not the owner. Never negotiate, schedule,
accept, contact, submit, or commit on the owner's behalf.

## Capture feedback without changing facts

Offer `useful`, `wrong`, `outdated`, `private`, `missing`, or `retract`. Confirm the category and
intended next step before recording anything other than `useful`.

```bash
python3 scripts/career_twin.py feedback /explicit/workspace \
  --response-id response-opaque-id --category outdated --confirm
```

Feedback appends an inbox item bound to the response and snapshot. It must not edit claims,
approvals, source state, publication state, or the current snapshot. If the confirmed feedback
requires factual change, visibility review, retraction, or deletion, hand off to
[maintain-digital-twin](../maintain-digital-twin/SKILL.md).

## Finish

Return the answer or draft, cited record IDs, snapshot ID, meaningful uncertainty, and any feedback
item ID. If evidence is missing, name the smallest next source or interview question; do not start
maintenance without owner confirmation.
