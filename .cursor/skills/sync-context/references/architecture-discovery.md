# Architecture discovery

This reference governs the exploration phase: deciding what a module or
repository actually does before any context document is drafted or
refreshed. It is read by `context-architect` and by the main `sync-context`
flow when it explores without a dispatched subagent. It does not define
document structure or line budgets; see
[context-templates.md](context-templates.md) for the shape content lands in,
and [context-quality.md](context-quality.md) for how a dimension's state is
judged good enough to write down.

## When exploration runs, and how deep

Exploration is scaled to what changed and what the scope looks like. It is
never a fixed per-module checklist that runs identically regardless of
size.

- **Initial or full sync** — explore every dimension below for each
  meaningful module. A small single-file utility module needs a few
  minutes of reading, not a dispatched subagent; a module with real
  integrations, persistence, or a trust boundary needs the time that
  actually takes.
- **A material architecture change** (new integration, new data store, a
  changed trust boundary, a new background process, a changed public
  contract) — explore the dimensions that change touches plus its direct
  neighbors (callers, consumers, shared contracts). Do not re-explore every
  unaffected module.
- **A small factual update** (a rename, a dependency bump with no behavior
  change, a comment or config value fix) — targeted inspection of the
  changed paths is enough. Do not run architecture discovery for this tier;
  see [SKILL.md](../SKILL.md) for the three-tier model this maps to.

Scale parallelism to actual complexity, not to a default pattern:

- Do not dispatch one subagent per directory or per file by default.
- Do not dispatch one subagent per architectural dimension by default.
- A small repository or module is explored directly in the main flow, or by
  one `context-architect` call for the whole scope. Reserve a dispatched
  `context-architect` call, or more than one in parallel, for a scope large
  or unfamiliar enough that one pass would plausibly miss a dimension —
  for example several independently deployable services in one sync, or a
  monorepo with package boundaries nobody has mapped yet.
- Justify parallel dispatch with the actual scope in front of you, not with
  "this is standard practice for a sync."

## Dimensions

Explore each dimension that is plausibly relevant to the scope. A
dimension this scope genuinely does not have is `not applicable`, stated
with a reason — it is not skipped silently and it is not forced to a
non-empty answer.

1. **Responsibility and boundary** — what this module owns, and what it
   explicitly does not own (the neighboring module that owns that instead).
2. **Entry points** — HTTP routes, CLI commands, queue consumers, scheduled
   jobs, event handlers, exported library functions actually called from
   outside the module.
3. **Representative runtime flows** — see "Runtime flows" below.
4. **Domain rules and invariants** — business rules enforced in code (a
   validation, a state-transition guard, a uniqueness constraint), not a
   restated requirements document.
5. **Data model and persistence** — tables, collections, files, or external
   stores this module reads or writes, and who else touches the same data.
6. **State and lifecycle** — in-memory state, caches, sessions, or a
   resource with a lifecycle (open/close, start/stop) that matters to
   correctness.
7. **External integrations** — other services, SaaS APIs, or third-party
   systems called, with the actual client or SDK call site.
8. **Events and asynchronous processing** — what this module publishes,
   subscribes to, or processes in the background, and the delivery
   guarantees the code actually relies on (at-least-once, ordering,
   idempotency) rather than the guarantee a comment claims.
9. **Configuration and feature flags** — settings that change behavior
   across environments, and where they are read.
10. **Security and trust boundaries** — authentication, authorization,
    tenant or scope checks, and where untrusted input first gets
    validated.
11. **Secrets and sensitive data handling** — where credentials or
    personal data are read, and whether they are logged or persisted in
    the clear; never copy an actual secret value into generated context.
12. **Error handling and failure modes** — what happens when a dependency
    is unavailable or an operation fails partway.
13. **Retry, idempotency, and concurrency** — whether a retried operation
    is safe to repeat, and what guards against a double-apply or a race.
14. **Dependencies and consumers** — what this module calls, and who calls
    it; a declared dependency is not proof of runtime use, so prefer an
    actual call site.
15. **Public contracts** — the schemas, OpenAPI/GraphQL definitions, event
    shapes, or shared types this module exposes to other modules or
    repositories.
16. **Testing** — what verified commands actually exercise, and what the
    tests do not cover.
17. **Observability** — logging, metrics, tracing, or alerting that would
    surface a failure in this module.
18. **Deployment and infrastructure topology** — how this module ships and
    runs (process model, container, function, pipeline) when that shapes
    its behavior or constraints.
19. **Architectural decisions and constraints** — a real constraint
    (performance, compliance, a platform limit) or a linked ADR that
    explains why the code is shaped the way it is; link an existing ADR,
    never invent one.
20. **Known gaps and risk areas** — a part of the module nobody has
    verified recently, a workaround, or a known limitation worth a future
    engineer's attention.

This list is a prompt for judgment, not a Python-enforced checklist: no
deterministic validator counts these twenty items or fails a document for
missing one. Whether a dimension is genuinely covered is a `context-reviewer`
and human judgment call, assessed through
[context-quality.md](context-quality.md).

## Evidence and state

For each dimension, the exploring agent decides one state:

- **Verified** — the material aspects of this dimension within the
  declared inspection scope were directly inspected, and the published
  claims are supported by that inspected evidence. Opening some related
  file is not enough. If only part of a material dimension was inspected,
  prefer `partial`. If evidence strongly suggests something but does not
  directly establish it, prefer `inferred`. An honest `unknown` is better
  than an unsupported `verified`.
- **Partial** — some of the dimension was inspected; name what was and was
  not.
- **Inferred** — a reasonable conclusion from an adjacent pattern (a
  framework convention, a naming pattern, a sibling module's shape), not
  from reading the thing itself. State what it was inferred from.
- **Unknown** — not yet inspected, or inspected and genuinely unresolved.
  State what evidence is missing and where it would likely be found.
- **Not applicable** — this scope does not have this concern. State why.

Cite a repository-relative path plus the symbol, route, table, or
configuration key for every verified or partial claim, exactly as
[context-generation.md](context-generation.md) already requires for
material claims. Reading a filename, a directory listing, or a fingerprint
manifest is never verification by itself. An honest `unknown` is not a
defect; a confident claim with no matching evidence is.

Respect exactly the repository or module scope the parent task authorized.
Never open secret-value files merely to inspect their contents. That
includes `.env`, private keys, credentials files, token stores,
secret-value files, ignored private or local files, and files outside the
authorized repository scope. Inspecting code that reads environment
variables, secret names, Secrets Manager or Parameter Store references,
IAM configuration, configuration schemas, or secret-handling logic is
allowed. Retrieving, reproducing, summarizing, or exposing a secret value
is not. "The service reads `DB_PASSWORD` from Secrets Manager" is the
correct shape; writing the value is not.

## Runtime flows

Document at least one representative end-to-end flow per module that has
one, in this shape:

```text
Flow: <short name, e.g. "place an order">
Trigger: <entry point — route, event, command>
1. <component or function> — <what it does, with its file path>
2. <next hop> — <what it does, with its file path>
   ...
Outcome: <observable result — response, event published, row written>
Failure path: <what happens if step N fails, if known>
```

A flow with unknown steps still gets written down with the gap marked
`unknown` at the step where evidence runs out, rather than omitted
entirely or extrapolated past where the trail was actually followed. A
module with no end-to-end flow (a pure library of helpers, for example)
records that as `not applicable` with the reason, not a fabricated flow.

## Reporting back to the drafting step

Hand the main flow one architectural inventory per scope, in this shape —
stable enough for the author and reviewer to consume, not a schema:

```text
Module: <id>

Inspection scope:
- <repository-relative glob or path>
- ...

Coverage:
| Dimension | State | Evidence | Notes |
| --- | --- | --- | --- |
| <every dimension from the list above> | verified / partial / inferred / unknown / not applicable | <path and symbol, or reason> | <optional>

Representative runtime flows:
### <short name>
Trigger: <entry point>
1. <hop> — <file>
Outcome: <observable result>
Failure path: <if known, else unknown>

Material findings:
Include only sections that are material to this module. Do not emit empty
or generic headings.

### Domain / business rules
- ...

### Data and persistence
- ...

### Security and trust boundaries
- ...

### Integrations
- ...

### Failure / retry / idempotency
- ...

### Configuration
- ...

### Observability
- ...

### Infrastructure / deployment
- ...

Architectural constraints:
- ...

Unknowns:
- <question for the author or the user>

Inspection limitations:
- <what was not opened, or could not be verified>
```

Evaluate every dimension in this inventory, including those that are `not
applicable`. Keep the Coverage summary, but do not reduce important
findings to that table alone. Material findings exist so the author can
synthesize without reopening the whole repository. The main flow turns
that inventory into the published `## Coverage` table and
`## Material architecture details` per
[context-quality.md](context-quality.md): Coverage is the index of what
was considered; Material architecture details is what downstream agents
need to know. Published Coverage includes material dimensions, relevant
unknowns, and a `not applicable` row only when the absence is important or
non-obvious. `context-architect` does not produce final document prose or
apply a line budget. This handoff is an agent contract, not a JSON schema.
