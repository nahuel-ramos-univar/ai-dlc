# Architecture decisions

Optional record of accepted architectural decisions. It is not current
module architecture, and it is not the non-functional requirement (NFR)
catalog. Current architecture stays in `AIDLC_CONTEXT.md` and the
integration map. NFRs stay in Jira.

An architecture decision record (ADR) is a named decision that later work
must follow. New ADRs live in `aidlc-docs/architecture.md` only when the
repository has no authoritative ADR location yet. If one already exists,
reuse that path. Do not create a second file. Do not merge existing ADRs
into this file unless the user approves that consolidation.

## When to write

`/scaffold-project` and `/refine-story` may add or update entries after the
same approval that already covers that exact content. Do not add a second
approval ceremony. `/sync-context` discovers and links the record. It does
not invent an ADR. `/plan-work` reads constraints and surfaces a conflict.
It does not turn a product wish into an accepted decision.
`/implement-change` and `/validate-change` read applicable accepted
decisions. A material deviation is a proposal, not a silent acceptance.

Do not record a Story, a per-run plan, a test log, or a Jira description
copy. Record a decision only when it constrains later work: a component
boundary, a shared contract, storage, authentication, or a comparable
deployment choice. Do not add an ADR for a routine library or file choice.

## Entry shape

Each new entry needs a stable local id, status, and an explicit **Binding
clause**. The binding clause is the sentence later work must follow. Recover
it by copying that line exactly. Do not paraphrase it. Context,
alternatives, rationale, trade-offs, consequences, and a Jira key are
supporting record, not snapshot text.

```markdown
## ADR-001: Private object storage

- Status: accepted
- Binding clause: Objects go to a private bucket. Public-read is not allowed.
- Context: Uploaded files must stay inside the account boundary.
- Alternatives considered: A public bucket with prefix rules.
- Rationale: Prefix rules still leave a public principal on the bucket.
- Trade-offs: Private storage needs an authorized download path.
- Consequences: Callers use a short-lived URL instead of a public object URL.
- Jira: PAY-123
```

Omit a supporting field that has no evidence. Do not invent a target,
approval, alternative, or retrospective rationale. Code that exists is
evidence of what shipped. It is not evidence that someone approved the
decision.

Status is `accepted` or `superseded`. Proposed decisions stay in the
reviewable proposal until they are approved. Do not persist `proposed` here.
When an accepted decision changes materially, mark it `superseded`, link
`Superseded by: ADR-002`, and keep a short history. Git supplies the rest.

## Snapshot recovery

Put each **applicable accepted** decision in the existing snapshot
`constraints` list. Do not use `relevant_decisions` for this: that field is
a string list. Copy the binding clause into `text` with no edits. Set
`source` to the repository-relative path plus `#` and the local id, for
example `aidlc-docs/architecture.md#ADR-001`.

Qualify `id` with the persisted repository ID from artifact-home identity,
the same `{repository-id}/{local-id}` shape criterion identifiers use for
`AID-32/AC-01`. Local headings stay `ADR-001`. `web/ADR-001` and
`api/ADR-001` are different constraints. Two rows with the same qualified
id in one snapshot are invalid.

A decision is applicable when it constrains this change's component,
contract, or boundary. Do not load every ADR into every snapshot.
Superseded entries stay in the file for history and stay out of the
snapshot. The replacement enters if it is applicable.

Resolve `scripts/context_tools.py` from this plugin. Extract with
`python3 ../../../scripts/context_tools.py architecture-decisions <path> --repository-id <id> --root <repo-root>`,
or call `extract_architecture_decisions` in process with that same owning
repository root. `--root` is required. Source paths are repository-relative
to that root. Do not omit it. Do not fall back to a basename. A shared
ADR uses the owning repository's id and authorized root, not the caller's.
Compare with the existing `snapshot-compare` helper. Do not invent a second
snapshot schema.

The helper returns `absent` when the path is missing, `ok` when the file is
the recognized `## ADR-N` list shape (including a confirmed empty or
superseded-only record), `unsupported` when an existing ADR is present but
not that shape, and `error` when recovery cannot be trusted. `ok` with an
empty list is only a recognized empty record. An unrecognized existing ADR
must not disappear into that empty success.

If the record is absent, recovery is complete with no architecture
constraints from that path. If the path exists and cannot be read, the
format is unsupported, a required binding clause is missing, fields or ids
are duplicated, or the root is missing or does not contain the file,
recovery is incomplete: set `source_complete` to `false`. Do not reuse a
remembered clause. Incomplete recovery is `not-compared`, never unchanged.

The helper recognizes only `## ADR-001` entries with `- Status:` and
`- Binding clause:` list fields. It ignores fenced examples and HTML
comments. It does not parse `# ADR-001` plus `## Status` / `## Decision`,
YAML status, or other templates, and it does not migrate those files.
Recover authoritative text from an unsupported format in an approved
`/refine-story` or `/scaffold-project` change set by copying the decision
into a recognized Binding clause. Until that recovery is complete, keep
`source_complete` false.

At `/validate-change`, compare against the **implementation** snapshot, not
only the latest file. A disappeared, replaced, or no-longer-applicable
decision is an explicit constraints delta (`removed`, `added`,
`clause-changed`). Do not treat that as unchanged.

Fingerprint generation stays on source the context describes. Do not add
this file to `EXCLUDED_PARTS` or remove `aidlc-docs` from it to detect
decision drift.

## Retrieval

`repository-context.md` and `AIDLC_CONTEXT.md` link the record. They do
not copy the decision log. When `/scaffold-project` or `/refine-story`
creates the first record, the same approved change set adds the minimum
navigation link: `## Architecture decisions` in the repository index, and
an evidence bullet in each constrained module's `AIDLC_CONTEXT.md`.
Preserve unrelated context. Recompute freshness and re-read the destination
before writing, as for any other approved edit. Verify the links resolve
before reporting completion. If the record is written and the required link
cannot be updated, report partial completion. Do not start `/sync-context`
to finish that handoff, and do not regenerate all context.

A later `/implement-change` or `/validate-change` session loads the record
through that link. If this work needs the record and the link is missing or
broken, treat architecture recovery as incomplete. Do not scan for an
unlinked file as a substitute.

For a multi-repository product, keep a repo-local record local. A shared
decision has one explicit authoritative path, referenced by the other
repositories. Do not infer that path from adjacency, and do not duplicate
the shared file.
