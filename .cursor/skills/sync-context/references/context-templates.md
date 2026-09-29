# Context templates and budgets

Use these templates only after the discovery mode selects an artifact home and
meaningful modules. They are generated-artifact templates, not instructions
that Cursor loads automatically.

## Budgets

| Artifact | Target | Maximum |
| --- | --- | --- |
| `aidlc-docs/repository-context.md` | 60–100 lines | 150 lines |
| `AIDLC_CONTEXT.md` or fallback | 100–200 lines | 300 lines |
| `.cursor/BUGBOT.md` | 30–100 lines | 150 lines |
| `SKILL.md` | — | 500 lines |

These limits are targets and caps, not minimums. Small modules need less.
Measure both line count and approximate context cost (`ceil(characters / 4)`).
Do not apply these limits to application source, changelogs, or unrelated user
documents.

Anthropic recommends keeping `CLAUDE.md` under 200 lines and `SKILL.md` under
500 lines. Our 300-line module-context cap is an AI-DLC policy, not a Cursor or
Anthropic requirement. `AIDLC_CONTEXT.md` is our convention; Cursor does not
load it implicitly.

If a generated artifact is over budget, remove duplicated generic prose first
and link existing documentation. Split only at real architectural boundaries.
Never hide required evidence in a giant line or silently drop it. Report any
remaining over-budget result.

Remediate an over-budget document in this order: (1) remove repetition and
unnecessary source-code narration; (2) move module-specific detail into the
relevant existing `AIDLC_CONTEXT.md` instead of expanding the index; (3) split
only when a real architectural boundary justifies a new module document.
Never truncate a document silently and never create arbitrary numbered
fragments (`repository-context-2.md`) to dodge the limit. Do not create one
context file per source file or directory merely to stay under budget;
generate module context only where it is useful and distinct.

## Repository index template

Use one of the two shapes below. The instructions between them are not part
of either document.

A single-repository index declares `Index: \`single-repository\`` and one
`Repository ID`. Its fingerprint covers that repository. Do not add a
`Repository` column unless every row repeats that same repository ID.

```markdown
# Repository context

<!-- AI-DLC:generated:start -->

## Scope

- Index: `single-repository`
- Repository ID: `<persisted-id>`
- Repository root: `<portable workspace-relative path>`
- Artifact home: `<portable workspace-relative path>`
- Baseline: `<git revision or unversioned>`
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
that it supports the surrounding claim.

```markdown
# AIDLC context — <module name>

<!-- AI-DLC:generated:start -->

## Identity and scope

- Repository ID: `<persisted-id>`
- Module ID: `<stable-id>`
- Source: `<repository-relative directory>`
- Baseline and fingerprint: `<git revision>` / `<fingerprint>`
- Examined: `<source, contracts, tests>`

## Responsibility

<What this module owns and explicit boundary with neighbours.>

## Entry points and interfaces

- `<entry point or contract>` — `<observable behavior>`

## Dependencies and consumers

- `<dependency or consumer>` — `<verified relationship>`

## Tests and commands

- `<verified command>` — `<what it covers>`

## Evidence and existing docs

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
