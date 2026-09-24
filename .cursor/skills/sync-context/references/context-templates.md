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

## Repository index template

```markdown
# Repository context

## Scope

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
```

## Module context template

```markdown
# AIDLC context — <module name>

## Identity and scope

- Repository ID: `<persisted-id>`
- Module ID: `<stable-id>`
- Source: `<repository-relative paths>`
- Baseline and fingerprint: `<values>`
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

- `<relative source or document link>`

## Unknowns

- <Evidence that was not available or not inspected.>
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
