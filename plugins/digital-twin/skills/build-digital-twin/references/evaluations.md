# Private evaluations

Build evaluations alongside the context bundle so the owner can test grounded facts, judgment,
privacy, abstention, and authority before any downstream use.

## Contents

- [Ask the owner for cases](#ask-the-owner-for-cases)
- [Evaluation case shape](#evaluation-case-shape)
- [Essential categories](#essential-categories)
- [Serving profile suites](#serving-profile-suites)
- [Grade safely](#grade-safely)
- [Re-run after lifecycle changes](#re-run-after-lifecycle-changes)

## Ask the owner for cases

Collect examples progressively:

- representative questions the intended audience asks;
- facts that must be cited to approved records;
- acceptable uncertainty and desired qualifications;
- unacceptable claims or exaggerations;
- privacy and restricted-topic probes;
- identity/authority and impersonation tests;
- refusal and abstention cases;
- examples of good modeled judgment and known counterexamples.

Use [../assets/private-evals.template.json](../assets/private-evals.template.json).

## Evaluation case shape

Each case records:

- stable evaluation ID and category;
- question;
- approved record IDs allowed as evidence;
- required facts and citations;
- prohibited claims and data categories;
- acceptable uncertainty behavior;
- expected refusal/abstention/authority behavior;
- draft or owner-approved golden answer;
- owner review state and date.

Generated golden answers remain `draft` until the owner approves their exact wording. A changed
approved record invalidates any dependent approved golden answer.

## Essential categories

Include at least:

1. grounded professional facts;
2. metric qualification;
3. conflict and uncertainty disclosure;
4. privacy/refusal boundaries;
5. identity and authority limitations;
6. abstention when evidence is absent;
7. modeled decision judgment tied to approved decision records;
8. deletion/retraction regression cases.

## Serving profile suites

Maintain separate suites for the proposed serving profiles:

- **Private career assistant:** representative owner questions, writing and interview-preparation
  tasks, private citation accuracy, gap detection, recognizable usefulness, and owner correction
  controls. Compare it with a résumé-plus-generic-prompt baseline before investing in update or
  public-serving infrastructure.
- **Public website chat:** public-only citations, missing/private/conflicted questions, prompt
  injection, identity disclosure, contact routing, commitment refusal, bulk-extraction attempts,
  stale snapshot behavior, and public feedback isolation.

Public test cases may reference only separately approved public records. A successful public answer
must not reveal that a private record exists. Visitor questions and feedback are untrusted inputs,
never facts or golden-answer updates.

## Grade safely

Prefer deterministic checks where possible:

- required approved record IDs were cited;
- prohibited record IDs or categories were absent;
- required qualifiers were present;
- refused commitments or impersonation;
- abstained when support was absent;
- did not expose private/restricted material.

Use human review for nuance, judgment, and recognizability. Do not use an LLM grader as the only
authority over facts about the owner.

## Re-run after lifecycle changes

When a claim, source, approval, or publication record changes:

1. identify dependent evaluation cases;
2. invalidate approved golden answers when their record digest changed;
3. rerun deletion, privacy, abstention, and authority regressions;
4. ask the owner to re-approve changed golden answers.

Also rerun the public suite when the public snapshot, serving policy, retrieval method, model, or
website response pipeline changes. Bind each recorded evaluation result to its snapshot and policy
versions so a later result cannot be mistaken for current behavior.

Report evaluation coverage by category, not as one universal truth score.
