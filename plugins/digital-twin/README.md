# Digital Twin Builder

`digital-twin` is a Claude Code plugin for building a private, evidence-backed professional
context bundle about a consenting owner. Its `build-digital-twin` skill starts with a guided
voice-or-text interview, turns statements and explicitly selected documents into atomic candidate
claims, and compiles only owner-approved material.

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

Then ask, “Interview me and build my professional context,” or invoke:

```text
/digital-twin:build-digital-twin
```

The deterministic helpers are standard-library Python 3.9+:

```bash
python3 skills/build-digital-twin/scripts/init_workspace.py /private/path/my-twin
python3 skills/build-digital-twin/scripts/validate_bundle.py /private/path/my-twin --format json
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
