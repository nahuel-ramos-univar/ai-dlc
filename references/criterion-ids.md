# Criterion identifiers and approved constraints

Keep traceability inside Jira content. Do not create a parallel catalog in
Git.

## Recovering approved requirements

Read approved constraints even when they are not under an Acceptance
Criteria heading: the acceptance-criteria field, Description, named
restriction sections, and referenced contracts or designs. Each evaluated
requirement keeps its source.

Do not treat an observation, a recommendation, or a contradictory design
note as an approved requirement. Do not add empty NFR headings. Do not
invent security, performance, accessibility, or compatibility thresholds.

## Stable identifiers

Preserve identifiers that already exist. When new ones are needed, propose
local ids on that issue, for example `AC-01`. The fully qualified form may
be `AID-32/AC-01`. Technical criteria on a Subtask use a distinct prefix
such as `TAC-01` and stay distinct from inherited business `AC-01`.

Assign or persist identifiers only in an approved publication payload.
On an existing ticket, do not renumber and do not edit silently. If there
are no identifiers and adding them is not authorized, use run-scoped
references and say that they will not survive a reorder.

Identifiers stay stable when criteria are reordered. Do not reuse a retired
identifier for a different requirement. When the meaning of a criterion
changes, keep or replace its identity only after an explicit decision, and
always reconsider the evidence. The identifier is not the content version.

Refinement, tests, and close-out may cite these identifiers. Do not impose
one test-name syntax on every framework. A criterion may map to many tests,
and a test may cover many criteria.

## Mechanical check

Use `validate_criterion_traceability` in `scripts/context_tools.py` to
detect a missing identifier, a duplicate, a reference to an unknown
identifier, or a criterion with no associated evidence. That check is not
semantic coverage. The independent `validator` still decides whether the
evidence demonstrates the requirement.
