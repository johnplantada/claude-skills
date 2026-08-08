# Voice and text interview workflow

Use one interview state machine for typed conversation and voice-captured transcripts. Version 1
does not record or retain audio and does not clone, imitate, or synthesize the owner's voice.

## Start the session

Create an interview session only after onboarding and explicit consent. Use
[../assets/interview-consent.template.json](../assets/interview-consent.template.json) and
[../assets/interview-session.template.json](../assets/interview-session.template.json).

Confirm four items before the first substantive question:

1. model-processing consent and its source scope;
2. transcript-retention preference;
3. sensitive or off-limits topics;
4. no direct publication from the transcript.

For external voice capture, use
[../assets/voice-interview-prompt.md](../assets/voice-interview-prompt.md), then import the transcript
as an explicitly selected source. Do not claim that the skill automatically runs inside the voice
surface.

## Ask adaptively

Ask one concise question at a time. Let the owner answer naturally, then follow the most useful
thread. Avoid leading language and invented conclusions.

Cover these areas over the session:

1. Purpose, audience, and boundaries.
2. Career and education timeline.
3. Representative projects and the owner's precise role.
4. Decisions, alternatives, constraints, and trade-offs.
5. Outcomes and qualified metrics.
6. Failures, reversals, and lessons.
7. Principles and working style.
8. Communication and voice preferences.
9. FAQs, refusals, and authority limitations.
10. Coverage-driven follow-ups.

Probe ownership with questions such as “Which decisions were yours?” and distinguish individual
actions from team outcomes. For every number confirm unit, denominator, population, and time window.
For proper names and dates, read back the spelling or range and ask for confirmation.

## Use checkpoints

After each topic or roughly every five questions:

- summarize candidate facts separately from interpretation;
- identify names, dates, roles, numbers, and attribution needing confirmation;
- ask what is wrong or missing;
- offer to mark any item private or retract it;
- write a small batch of atomic `pending` candidates.

Do not accumulate an authoritative narrative silently. Every interview-derived factual candidate
starts at `self_reported`, even when the owner repeats it confidently.

## Preserve provenance

For each candidate, keep the transcript source occurrence and a bounded coordinate such as heading,
turn range, timestamp range supplied by the capture surface, or line span. If no stable coordinate
exists, state `coordinate unavailable after import`; never invent one.

Use [../assets/transcript-corrections.template.json](../assets/transcript-corrections.template.json)
for corrections. A correction creates a new claim revision or replaces the transcript span; it does
not erase prior review history silently.

## Honor control words

- `skip`: omit the current question and move on without inference.
- `pause`: stop questioning and save only the consented state.
- `private`: keep the current topic/candidate private and ineligible for publication.
- `retract`: mark the named statement retracted and invalidate dependent approvals.
- `delete`: clarify whether to delete transcript text, source metadata, derived candidates, or the
  full session; then apply dependency propagation.

If the scope of `delete` is ambiguous, pause and clarify before acting.

## Close the session

Provide a checkpoint containing:

- candidate claims grouped by category;
- confirmations and corrections still needed;
- conflicts and ownership ambiguities;
- coverage gaps;
- suggested next interview question or lowest-risk source;
- transcript retention/deletion action due next.

Do not compile or publish at interview close. Route candidates to owner review.
