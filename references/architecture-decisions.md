# Architecture decisions

Persist material, explicitly approved architectural decisions in the
repository's authoritative decision record. Do not leave them only in chat.

Create `aidlc-docs/architecture.md` when the first such decision needs to
be recorded and no authoritative ADR location already exists. Otherwise,
reuse the existing location. Do not create an empty or duplicate record.

Include the exact record changes in the existing approval scope.
If persistence is not authorized or cannot be completed, report it as
pending; do not claim the decision was recorded.

Current architecture stays in `AIDLC_CONTEXT.md` and the integration map.
NFRs stay in Jira.

An architecture decision record (ADR) is a named decision that later work
must follow. Creating the file is conditional. Recording a material
approved decision is not optional.

## When to write

`/scaffold-project` and `/refine-story` persist a material, explicitly
approved decision in the same approval that already covers that exact
content. Do not add a second approval ceremony. A pending decision stays
in the proposal; do not mark it accepted. If the record cannot be written,
report that persistence as pending.

`/sync-context` discovers and links the record. Ordinary sync does not
invent an ADR, accept a decision, or rewrite a binding clause to match
code. An explicitly approved legacy migration may relocate or faithfully
consolidate existing records; see
[legacy-migration.md](../.cursor/skills/sync-context/references/legacy-migration.md).
`/plan-work` reads constraints and surfaces a conflict. It does not turn a
product wish into an accepted decision. `/implement-change` and
`/validate-change` read applicable accepted decisions. A material deviation
is a proposal, not a silent acceptance.

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

New authoring through `/scaffold-project`, `/refine-story`, or any other
new ADR creation persists only `accepted` or `superseded`. Proposed
decisions stay in the reviewable proposal until they are approved. Do not
persist `proposed` here, and do not create a durable `accepted` record
merely because the agent proposed something.

Legacy migration may preserve a record's existing lifecycle state, including
`proposed`, `draft`, `rejected`, `accepted`, or `superseded`, when that
state is already present in source evidence. Approval to migrate a record
is approval to preserve it, not approval of the architectural decision.
Never convert `proposed` to `accepted` because migration was approved.

When an accepted decision changes materially, mark it `superseded`, link
`Superseded by: ADR-002`, and keep a short history. Git supplies the rest.

## Snapshot recovery

Put each **applicable accepted** decision in the existing snapshot
`constraints` list. Do not use `relevant_decisions` for this: that field is
a string list. Copy the recovered decision text into `text` with no edits.
Set `source` to the repository-relative path plus `#` and the local id, for
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
When the source is a directory, the helper inspects nested Markdown files
inside that authorized path. It does not follow nested symlinks, does not
scan unrelated directories, and does not report an empty record merely
because no files sit at the first directory level. Inaccessible nested
content is incomplete recovery. An authorized source path that is itself a
symlink is read only after its target is confirmed to stay inside the
repository root. A broken symlink is incomplete recovery, not an absent
record. A symlink that leaves the repository is `error`.

Compare with the existing `snapshot-compare` helper. Do not invent a second
snapshot schema.

Authorize the requested source against the repository root before
classifying existence. A missing path outside that root is `error`, not
`absent`. The helper returns `absent` when the authorized path is
genuinely missing, `ok` when every detected ADR-like record was recovered
unambiguously (including a confirmed empty or superseded-only record, and
including a valid existing format whose decision text was recovered by the
read fallback), `unsupported` when the source exists but its semantic
meaning cannot safely be recovered, and `error` when the operation is
unauthorized or the source cannot be trusted. `ok` with an empty list is
only a confirmed empty record. An unrecovered existing decision must not
disappear into that empty success, including when another entry was parsed
successfully. Duplicate semantic fields, conflicting frontmatter and body
values, duplicate Status or Decision sections, and YAML the fallback
parser cannot interpret unambiguously are `unsupported`. Do not collapse
that ambiguity into `ok`, and do not publish a binding constraint from
that record.

If the authorized record is absent, recovery is complete with no
architecture constraints from that path. If the path exists and cannot be
read, a symlink is broken, nested content is inaccessible, ADR-like text
remains unrecovered, a required binding clause is missing, fields or ids
are duplicated, representations conflict, or the root is missing or does
not contain the file, recovery is incomplete: set `source_complete` to
`false`. Do not reuse a remembered clause. Incomplete recovery is
`not-compared`, never unchanged. A failed or incomplete recovery must
never become unchanged through an empty constraints list.

The supported write format is `## ADR-001` with `- Status:` and
`- Binding clause:` list fields. The helper also reads, without rewriting
the file, a small set of other authoritative shapes: `# ADR-001` or
`# 1. Title` with `## Status` and `## Decision` sections, and YAML
frontmatter with `id` and `status` followed by a decision. The fallback YAML parser supports only unquoted scalars and simple quoted
scalars with no escape sequences. Full-line `#` comments are ignored.
Block scalars, inline comments, nested mappings, arrays, anchors, aliases,
and quoted values with escapes are unsupported. Unsupported syntax is
incomplete recovery, never a YAML indicator or comment stored as decision
text. Multiple representations of the same field are allowed only when
they agree. Copy recovered decision text exactly. Do not require a
consumer to rewrite a valid existing ADR merely so a snapshot can read
it. Do not parse every Markdown template. Until the relevant decision text
is actually recovered, keep `source_complete` false. Proposed, draft, or
rejected records stay out of accepted constraints; do not promote them.

The helper ignores backtick and tilde fences and HTML comments together, so
a fence opener inside a comment cannot hide a later real ADR, and a comment
delimiter inside a fenced example is not a comment. Unclosed comments or
fences are incomplete recovery.

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
broken, treat architecture recovery as incomplete. Do not treat a broken
architecture link as an absent record. Do not scan for an unlinked file as a
substitute.

`/refine-story` may include Jira mutations and repository ADR or context
mutations in one reviewable change set. Show the Jira target and payload,
the exact ADR destination and content, and the related navigation edits
before approval. Approval of a Jira payload alone does not implicitly
authorize unlisted repository writes. If the user approves Jira changes
and excludes the ADR, do not write the ADR. If the Jira refinement depends
on that decision, surface the inconsistency rather than silently
proceeding. If one mutation succeeds and the other fails, report partial
completion, inspect the actual current state, and retry only the
unresolved mutation after freshness checks. Do not claim the writes were
atomic.

For a multi-repository product, keep a repo-local record local. A shared
decision has one explicit authoritative path, referenced by the other
repositories. Do not infer that path from adjacency, and do not duplicate
the shared file.
