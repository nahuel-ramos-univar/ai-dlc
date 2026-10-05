# Context quality

This reference defines when a drafted or refreshed context document is good
enough, and what the `## Coverage` section records. It replaces document
length as the signal for quality. A document can be short and excellent, or
long and shallow; neither line count nor section count decides which.

## The coverage section

A module `AIDLC_CONTEXT.md` records a `## Coverage` table naming the
dimensions from
[architecture-discovery.md](architecture-discovery.md) that belong in the
published document. Coverage is an index of architectural understanding,
not the full architecture documentation. `context-architect` evaluates
every dimension in its inventory and reports material findings. The
published table is a subset: material dimensions, relevant unknowns, and
a `not applicable` row only when that absence is important or
non-obvious to a downstream engineer. Do not pad the table with a
`not applicable` row for every dimension on the master list. Do not
reduce discovered persistence, auth, retries, feature flags, or
integrations to one-line Coverage rows.

```markdown
## Coverage

| Dimension | State | Evidence |
| --- | --- | --- |
| Entry points | verified | `services/orders/handler.py` → `create_order` |
| External integrations | verified | `services/orders/payment_client.py` → `charge()` |
| Retry and idempotency | partial | retry exists in `payment_client.py`; idempotency key not confirmed |
| Security and trust boundaries | unknown | auth middleware not inspected this pass |
| Deployment topology | not applicable | library module; a downstream engineer might otherwise look for a deploy unit here |
```

No deterministic validator counts rows, requires a fixed number of
dimensions, or fails a document for an `unknown` or `not applicable` row.
`context-reviewer` is where a coverage table gets checked against reality:
whether a row claiming `verified` is actually backed by the cited evidence,
and whether a dimension that plainly matters to this module (for example
security on a module that handles payment data) was skipped without a
stated reason. A dimension irrelevant to a given module does not need a
published row. Include `not applicable` only when the absence is important
or non-obvious — for example a library that a reader might assume has its
own deploy unit. Do not pad the table with `not applicable` rows for every
dimension on the master list.

A Coverage state of `verified` means the material aspects of that
dimension within the declared inspection scope were directly inspected
and the published claims are supported by that evidence. Opening some
related file is not enough. Prefer `partial` when only part of a material
dimension was inspected, `inferred` when evidence suggests but does not
directly establish the claim, `unknown` when it could not be determined,
and `not applicable` when it genuinely does not apply. An honest
`unknown` is better than an unsupported `verified`.

## Material architecture details

After Coverage, the module document records `## Material architecture
details`. Generate subsections only for dimensions that are materially
important to that module. Examples, not a mandatory heading list:

- Data and persistence
- Security and trust boundaries
- Failure handling, retries, and idempotency
- Configuration and feature flags
- Events and asynchronous processing
- Observability
- Deployment/runtime topology
- Architectural constraints and invariants

Do not create empty or generic sections merely to fill the template. The
objective is that Coverage tells a reader what was considered and at what
confidence, while Material architecture details tells a downstream
planning or implementation agent what it actually needs to know. The
final context should preserve enough architectural information that those
agents do not rediscover major system behavior from scratch.

## Evidence catalog

`## Evidence and existing docs` is the canonical catalog of
repository-relative local evidence paths referenced by the context. Any
local path used as supporting evidence in Coverage, runtime flows,
Material architecture details, or architectural decisions and constraints
must also appear there. Prose elsewhere may still name a symbol next to
the path (`src/auth.py` → `validate_token()`), but the path itself belongs
in this catalog. Python only checks that a catalogued path exists inside
an authorized root. `context-reviewer` judges whether the source actually
supports the claim.

## The quality bar

Before treating a draft as ready for independent review (or, for a small
update where review is skipped per
[review-handoff.md](review-handoff.md), before closing the sync), check
whether the document actually answers the questions a downstream engineer
would ask. These are examples, not a Python-checkable list:

1. If I need to change this module's main behavior, which file do I open
   first?
2. What does this module do when its main dependency is unavailable?
3. What other module breaks if I change this module's public contract?
4. Where does untrusted input first get validated here?
5. If this module publishes or consumes an event, what happens on
   duplicate delivery?
6. What state does this module hold, and what happens to it on restart?
7. Which configuration value would I change to alter this module's
   behavior in production, and where is it read?
8. What test would actually fail if I broke this module's main flow?
9. What does this module's owner not yet know about it (the honest
   unknowns), and why would that matter to my change?
10. If I only read this document and never opened the source, what would I
    get wrong?

A document that cannot answer most of these for a module with real
behavior (not a thin pass-through or a pure data class) is not ready, no
matter how many lines it has. A short document that answers them plainly,
citing evidence, is ready.

## What good and bad look like

See [MANUAL_EVALUATION.md](../../../../MANUAL_EVALUATION.md) for named
scenarios across repository types, and
[tests/fixtures/context_review](../../../../tests/fixtures/context_review)
for a concrete fixture with seeded defects and an answer key used to
evaluate whether review actually catches them. Four patterns are explicit
regressions, never an acceptable output of this skill:

- **Shallow service context** — a module with real external calls, state,
  or a trust boundary gets a context document that only restates its
  framework scaffolding (routes exist, a controller exists) with no
  runtime flow, no integration detail, and no mention of what happens on
  failure. Depth was available in the source and was not captured.
- **False completeness** — a coverage row, an `Examined` field, or prose
  claims a dimension is verified when it was not actually inspected (a
  guess from the module's name or framework convention, not from reading
  the file). This is worse than an honest unknown: it tells a downstream
  reader something false with confidence.
- **Length gaming** — padding a document toward a target line count with
  generic, non-specific prose ("this module handles orders and ensures
  reliability") instead of specific, evidence-backed statements, to look
  thorough without being thorough.
- **Honest unknown beats invented behavior.** When evidence genuinely runs
  out, write `unknown` with what is missing and where it would likely be
  found. Do not invent a plausible-sounding behavior to fill the gap. An
  honest `unknown` is a correct answer; a confident guess is a defect even
  when it happens to be right, because the next reader cannot tell the
  difference between a verified fact and a lucky guess.

## Relationship to line budgets

[context-templates.md](context-templates.md)'s module-context budget is an
authoring guideline, not a quality gate: `validate_generated_context` never
fails a document for exceeding it. Quality is judged by this reference and
by `context-reviewer`, not by `scripts/context_tools.py` counting lines.
Do not use an advisory budget as a reason to omit a dimension that matters,
and do not treat "under budget" as evidence that a document is complete.
