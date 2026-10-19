# Requirement snapshot

Shared by `/implement-change` and `/validate-change`. Capture the approved
requirement content that the work is judged against. Carry the snapshot in
the handoff and the close-out. Do not write a new file in the consumer
repository. An approved optional validation comment or attachment may quote
the digest as historical evidence.

The digest detects whether relevant content is equal. It does not prove who
approved that version.

## Relevant content

Include:

- scope and exclusions;
- acceptance criteria;
- approved NFR or other constraints, each with its source;
- relevant contracts;
- approved technical refinement.

A comment is relevant only when it records an approved decision that changes
the work. Do not drop that decision only because it lives in a comment.

Exclude administrative changes that do not change requirements: assignee,
sprint, timestamps, or comments that are not such a decision.

## Input format

Each snapshot is one JSON object:

- `source_complete` (required boolean). `true` means this side was recovered
  correctly. Omit it, set it to `false`, or pass a non-boolean value when
  recovery is incomplete. Those cases are `not-compared`.
- `acceptance_criteria` (required list of objects). Each item has a unique
  non-empty `id`, non-empty `text`, and optional `source` string. `null`, an
  empty string, or a non-object item is not a valid list. An empty list is
  comparable only when `absence_confirmed` is the boolean `true` and
  `absence_reason` is a non-empty string. Do not infer confirmed absence from
  `[]` alone.
- optional text: `scope`, `exclusions`, `technical_refinement` (strings).
- optional `constraints`: same object shape as criteria.
- optional `contracts` and `relevant_decisions`: lists of non-empty strings.

Administrative keys are ignored. Do not coerce `null`, empty strings, or
invalid objects into empty lists.

## How to compare

Resolve `scripts/context_tools.py` from this plugin. From a skill file under
`.cursor/skills/<name>/`, that path is `../../../scripts/context_tools.py`,
the same way plan-work resolves `plan-validate`. Do not resolve it from the
consumer working directory.

Pass one JSON object on standard input or a temporary file outside the
consumer repository:

```json
{
  "baseline": { "source_complete": true, "acceptance_criteria": [{"id": "AC-01", "text": "..."}] },
  "current": { "source_complete": true, "acceptance_criteria": [{"id": "AC-01", "text": "..."}] }
}
```

Documented invocation:

```
python3 <plugin>/scripts/context_tools.py snapshot-compare -
```

The helper prints `unchanged`, `changed`, or `not-compared`, a digest when
comparison succeeded, and a detail line. Exit `0` is unchanged, `1` is
changed, `2` is not-compared or unreadable input.

`compare_requirement_snapshots` in the same module is the same check for
in-process callers. Comparison is independent of criterion order.

## Status

- **unchanged** — both sides were recovered completely and relevant content
  matches.
- **changed** — relevant content differs. Show the relevant delta, invalidate
  affected evidence, and ask for a product decision or `/refine-story` as
  appropriate. Do not declare the work ready against outdated requirements.
  Do not promise that only one criterion is affected when the impact may
  span the whole item.
- **not-compared** — there is no baseline, recovery failed, or the payload is
  malformed. Incomplete recovery never equals unchanged.

The independent `validator` must re-read the Jira sources when it can. If it
must rely on coordinator-supplied snapshot text, say that limitation.
