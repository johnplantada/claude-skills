# Professional Digital Twin

`digital-twin` is a Claude Code plugin for building, using, and maintaining a private,
evidence-backed professional digital twin about a consenting owner. It separates lifecycle
authority across four skills:

- `digital-twin` routes ambiguous or multi-stage requests without reading or changing twin data.
- `build-digital-twin` reviews selected documents, interviews against gaps, and compiles approved
  records into a private snapshot.
- `use-career-twin` provides grounded career assistance from that snapshot and captures feedback
  without changing facts.
- `maintain-digital-twin` plans source refreshes, invalidates stale dependencies, and guides owner
  review before a replacement snapshot becomes current.

It does not create avatars, clone a voice, impersonate the owner, publish automatically, connect
broad accounts, or act on anyone's behalf.

## What it produces

- A reviewable career timeline, project and decision records, principles, voice guidance, FAQs,
  and explicit privacy and authority boundaries.
- Machine-readable approved records with atomic evidence provenance and evidence-strength ceilings.
- Conflict and coverage reports that turn gaps into focused interview questions.
- Private evaluation cases for facts, uncertainty, privacy, refusal, identity, and authority.

Every extracted or interview-derived statement begins as a candidate. Only the owner decides its
accuracy, wording, evidence classification, visibility, publication rights, and approval state.

## Product direction

The current plugin implements the governed private source of truth, a local private career-assistant
workflow, owner feedback capture, content-addressed private snapshots, and controlled source-refresh
transactions. The end goal remains website chat backed by a physically separate, minimal public
snapshot—not direct access to the private workspace.

- [Design and architecture](docs/design-and-architecture.md): twin lifecycle, data model,
  owner-controlled updates, failure handling, and current-versus-proposed capabilities.
- [Private assistant and public website chat](docs/serving-and-feedback.md): serving profiles,
  response contract, public boundary, feedback loop, threats, evaluation, and rollout gates.

The private interface currently runs through Claude Code plus standard-library local helpers; it is
not a standalone application. Public projection, public website chat, hosting, deployment, and
automatic publication are not implemented.

## Privacy model

Claude Code may send selected content to the configured model provider; it is not automatically a
local-processing environment. The skill discloses this before reading private material and requires
explicit processing consent. It inventories only paths the owner selects, treats imported content as
untrusted data, and stops on possible credentials, high-risk personal information, confidential
employer or client material, or substantial third-party content without echoing a suspected value.

The generated owner workspace belongs outside source repositories and uses restrictive permissions
where supported. No owner documents, transcripts, or profile data ship in this plugin.

## Install and use

Add this repository as a marketplace, then install only this plugin:

```text
/plugin marketplace add ~/codebase/claude-skills
/plugin install digital-twin@devenv-marketplace
```

For local development, load this plugin directory directly:

```bash
claude --plugin-dir ~/codebase/claude-skills/plugins/digital-twin
```

Then ask, “Review and organize these documents, then interview me to fill the gaps,” or invoke:

```text
/digital-twin:build-digital-twin
```

For an existing twin, ask “Use my career twin to prepare me for this interview” or “Maintain my
digital twin from this updated résumé.” The thin `digital-twin` router can select the workflow for
ambiguous requests.

The deterministic helpers are standard-library Python 3.9+:

```bash
python3 skills/build-digital-twin/scripts/init_workspace.py /private/path/my-twin
python3 skills/build-digital-twin/scripts/validate_bundle.py /private/path/my-twin --format json
python3 skills/build-digital-twin/scripts/compile_private_snapshot.py /private/path/my-twin --format json
python3 skills/use-career-twin/scripts/career_twin.py query /private/path/my-twin "What should I emphasize?" --format json
python3 skills/maintain-digital-twin/scripts/update_bundle.py status /private/path/my-twin --format json
```

Validate the plugin itself with:

```bash
claude plugin validate --strict plugins/digital-twin
```

## Voice limitation

Voice is a capture adapter, not a separate truth source. Version 1 supplies a reusable voice prompt
and a transcript import/correction workflow, but does not record or store audio, clone speech, or
claim that this Claude Code skill runs automatically inside a mobile voice surface. Text-only
sessions support the complete workflow.

## License

[MIT](../../LICENSE)
