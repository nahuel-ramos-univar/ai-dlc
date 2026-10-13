# Context templates and budgets

Use these templates only after the discovery mode selects an artifact home and
meaningful modules. They are generated-artifact templates, not instructions
that Cursor loads automatically.

## Budgets

| Artifact | Target | Guideline ceiling | Enforcement |
| --- | --- | --- | --- |
| `aidlc-docs/repository-context.md` | 60–100 lines | 150 lines | hard — `validate_generated_context` fails an over-cap index |
| `AIDLC_CONTEXT.md` or fallback | 100–200 lines | 300 lines | metric only — not a validation result |
| `.cursor/BUGBOT.md` | 30–100 lines | 150 lines | not validated by this module |
| `SKILL.md` | — | 500 lines | checked by `tests/skill_contracts.py`, not a runtime gate |

These are authoring guidelines, not minimums, and for `AIDLC_CONTEXT.md` not a
correctness property either: an AI-DLC policy choice about how much a document
should normally take to say, not a Cursor or Anthropic requirement and not
proof that a document covers what it needs to cover. A module document under
budget can still be shallow; one slightly over budget because a module
genuinely has more verified integrations, flows, and failure modes to record
is not thereby a defective document. Measure both line count and approximate
context cost (`ceil(characters / 4)`) for visibility, not as a pass/fail gate
for module context. Do not apply these limits to application source,
changelogs, or unrelated user documents.

**The repository index stays a hard target.** It is deliberately a short
index, not an architecture document, so `index:budget` in
`validate_generated_context` still reports `failed` when it is over its
150-line cap; an over-long index usually means module detail leaked into it
rather than into the module's own document.

**The module-context ceiling is advisory, not a validity gate.** Anthropic
recommends keeping `CLAUDE.md` under 200 lines and `SKILL.md` under 500 lines;
our 300-line module-context guideline borrows that instinct for a different
kind of document. `validate_generated_context` does not emit a
`modules:budget` check at all. If you want the number, call `document_metrics`
and report it as a metric (`lines: N`, `advisory guideline: 300`), never as
passed or failed. See [context-quality.md](context-quality.md) for what
actually decides whether a module document is good enough.
`AIDLC_CONTEXT.md` is our own convention; Cursor does not load it implicitly.

If a generated artifact is noticeably larger than its target, look for
duplicated generic prose first and link existing documentation instead of
restating it. Split only at real architectural boundaries. **Never cut a
verified dimension, a runtime flow, or evidence just to land under the
guideline ceiling** — a module that genuinely has more to say should say it,
and the honest response to "this got long" is usually "this module does more
than most," not "shorten it." Never hide required evidence in a dense line or
silently drop it.

Remediate a module document that has grown mostly from repetition, in this
order: (1) remove repetition and unnecessary source-code narration; (2) link
existing authoritative documentation instead of restating it; (3) split only
when a real architectural boundary justifies a new module document. Never
truncate a document silently and never create arbitrary numbered fragments
(`repository-context-2.md`) to dodge a budget. Do not create one context file
per source file or directory merely to stay under budget; generate module
context only where it is useful and distinct. Do not introduce a minimum line
count either — a genuinely small module's accurate, evidence-backed document
can be short.

## Repository index template

Use one of the two shapes below. The instructions between them are not part
of either document.

A single-repository index declares `Index: \`single-repository\`` and one
`Repository ID`. Its fingerprint covers that repository. Do not add a
`Repository` column unless every row repeats that same repository ID.
The Context cell is a link to a local context file, not a URL or a
same-document anchor. Every module row requires that local file. An empty
or missing Context cell is invalid. Index-only repositories keep the
Modules header and leave the table empty; they do not list a module that
points nowhere. Each generated index has one `## Scope` and one
`## Modules`. Each module document has one `## Identity and scope`, one
`## Coverage`, one `## Evidence and existing docs`, and one `## Unknowns`.
Those four headings are the deterministic structural envelope. Runtime
flows and `## Material architecture details` are not mechanically required.

A Git working tree whose `HEAD` does not resolve to a commit uses baseline
`no-commit` in this same field. That is not `unversioned`: a `.git` marker
is present, and file discovery stays Git-based. Do not invent a SHA. The
validator compares the fingerprint, not the baseline token, so `no-commit`
needs no second format. The module `Baseline and fingerprint` field uses the
same three tokens: a git revision, `no-commit`, or `unversioned`. A directory
without Git records `unversioned` there too. Do not put `no-commit` on a tree
that has no Git root.

```markdown
# Repository context

<!-- AI-DLC:generated:start -->

## Scope

- Index: `single-repository`
- Repository ID: `<persisted-id>`
- Repository root: `<portable workspace-relative path>`
- Artifact home: `<portable workspace-relative path>`
- Baseline: `<git revision, no-commit, or unversioned>`
- Fingerprint: `<fingerprint>`
- Examined: `<paths and boundaries>`

## Modules

| Module | Source | Context | Status |
| --- | --- | --- | --- |
| `<module-id>` | `<path>` | `<relative link>` | current / stale / unknown |

## Verified integration boundaries

<Link to integration map only when verified.>

## Unknowns

- <Unknown, evidence gap, or intentionally unexamined area.>

<!-- AI-DLC:generated:end -->
```

A multi-repository engagement index declares `Index: \`multi-repository\``
and does not declare one `Repository ID` or one repository-wide fingerprint.
Every Modules row needs a `Repository` column. The same module ID may appear
in two repositories. Without that column, validation cannot assign a source
path and must not guess. The number of authorized roots does not decide
which shape this is.

```markdown
# Repository context

<!-- AI-DLC:generated:start -->

## Scope

- Index: `multi-repository`
- Artifact home: `<portable workspace-relative path>`
- Examined: `<paths and boundaries>`

## Modules

| Module | Repository | Source | Context | Status |
| --- | --- | --- | --- | --- |
| `<module-id>` | `<repository-id>` | `<path>` | `<relative link>` | current / stale / unknown |

## Verified integration boundaries

<Link to integration map only when verified.>

## Unknowns

- <Unknown, evidence gap, or intentionally unexamined area.>

<!-- AI-DLC:generated:end -->
```

## Module context template

`Repository ID`, `Module ID`, and `Source` must match the index row.
`Source` is the repository-relative scope that freshness is computed
against. The context file itself may live in the module directory or in an
artifact-home fallback path.

Evidence bullets have three path forms, and only those forms are checked:

- A bullet that is only a Markdown link is resolved relative to this
  document. Use it for a file in this checkout, including a sibling
  repository when that repository is an authorized root.
- A bullet that is only `` `apps/storefront/index.ts` `` (a slash, or a
  filename extension, and nothing else in the bullet) is resolved in this
  module's owning repository.
- A bullet that is only `` `payments-api:services/payments/handler.ts` ``
  is a path in another authorized repository. The text before the colon is
  the repository ID.

A symbol name such as `` `OrderPlacedEvent` `` is not a file path. Prose
that mentions a path inline is not checked. A path that exists is not proof
that it supports the surrounding claim. A catalog with no path references
is mechanically `not_applicable` (`no local evidence paths to resolve`),
not a semantic pass. A missing `## Evidence and existing docs` heading
fails structural validation.

```markdown
# AIDLC context — <module name>

<!-- AI-DLC:generated:start -->

## Identity and scope

- Repository ID: `<persisted-id>`
- Module ID: `<stable-id>`
- Source: `<repository-relative directory>`
- Baseline and fingerprint: `<git revision, no-commit, or unversioned>` / `<fingerprint>`
- Examined: `<source, contracts, tests>`

## Responsibility

<What this module owns and explicit boundary with neighbours.>

## Entry points and interfaces

- `<entry point or contract>` — `<observable behavior>`

## Representative runtime flows

<One end-to-end flow per behavior that matters, in the shape defined in
[architecture-discovery.md](architecture-discovery.md): trigger, each hop
with its file path, outcome, and failure path when known. State
`not applicable` with a reason for a module that has no flow of its own,
for example a pure helper library.>

## Dependencies and consumers

- `<dependency or consumer>` — `<verified relationship>`

## Tests and commands

- `<verified command>` — `<what it covers>`

## Coverage

<The published coverage table from [context-quality.md](context-quality.md).
The architecture inventory evaluates every dimension. This table includes
material dimensions, relevant unknowns, and a `not applicable` row only
when that absence is important or non-obvious. Do not pad it with every
dimension from the master list.>

| Dimension | State | Evidence |
| --- | --- | --- |
| `<dimension>` | verified / partial / inferred / unknown / not applicable | `<path and symbol, or reason>` |

## Material architecture details

<Subsections only for dimensions that are materially important to this
module. Coverage is a summary; this section preserves the discovered
architecture a downstream agent needs. Do not emit empty or generic
headings. Example subsection names, not a mandatory list: Data and
persistence; Security and trust boundaries; Failure handling, retries,
and idempotency; Configuration and feature flags; Events and asynchronous
processing; Observability; Deployment/runtime topology; Architectural
constraints and invariants.>

## Evidence and existing docs

<Canonical catalog of repository-relative local evidence paths. Any local
path used as supporting evidence in Coverage, runtime flows, Material
architecture details, or constraints must also appear here.>

- `services/payments/handler.ts`
- document-relative Markdown link to `services/payments/handler.ts`

## Unknowns

- <Evidence that was not available or not inspected.>

<!-- AI-DLC:generated:end -->
```

Use the same body for an artifact-home fallback module context. Its title must
also state the original source root and why the colocated file was unavailable.

## Integration map template

```markdown
# Integration map

## Verified boundaries

| From | To | Contract | Evidence |
| --- | --- | --- | --- |
| `<module>` | `<module or external system>` | `<HTTP/event/schema>` | `<relative path>` |

## Unknowns

- <Unverified relationship or absent runtime evidence.>
```
