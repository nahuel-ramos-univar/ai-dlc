# Artifact home and identity

Resolve the artifact home before generating context.

- **Single repository:** default to the confirmed repository root.
- **Nested tracked module:** default to its owning Git root. Preserve the
  requested module as analysis scope.
- **Multi-repository engagement:** reuse the existing configured artifact
  home. If none exists, apply the placement policy below: stay distributed
  (each repository keeps its own artifact home) unless a coordinator is
  already configured, or the user explicitly confirms one. Never choose a
  shared location merely because it looks like the engagement home.
- **Read-only source:** analyze it, then use a separate authorized writable
  artifact home. Do not create a Git repository for artifacts.
- **Unversioned tree:** permit discovery with baseline `unversioned`. Save only
  when its write scope or an artifact home is explicit and writable.

The artifact home owns:

- `aidlc-docs/repository-context.md`
- optional `aidlc-docs/integration-map.md`
- fallback `aidlc-docs/context/<repo-id>/<module-id>.md`
- `.ai-dlc-config.md`

One configured scope has one canonical index. Link an existing repository
index instead of making a competing workspace index.

## Stable IDs

Prefer a persisted repository ID from the artifact-home configuration. On the
first run, derive it from a verified canonical remote after normalizing only
known equivalent SSH and HTTPS forms. Remove credentials. Never guess a
canonical remote when several remotes are plausible.

If no usable remote exists, ask for or assign an explicit ID once, then persist
it in the artifact-home configuration. A derived ID is a readable slug plus a
short hash of the canonical identity. Keep a valid persisted ID unchanged.
Detect collisions against stored IDs before writing. Do not derive identity
from absolute paths, checkout names, open-workspace collisions, or a human
responsibility label. Preserve module IDs across renames and moves when source
evidence links them. Report ambiguous duplicate documents; do not delete human
content.

## Minimal configuration

```markdown
## Context identities
- Repository: `payments-api`
  - Canonical remote: `github.com/example/payments-api`
  - Artifact home: `.`
  - Root: `.`
- Module: `payments-api`
  - ID: `payments-api`
  - Source: `services/payments`
```

An optional `## Project references` section may follow `## Context identities`.
It is not part of identity. Omit the whole section when nothing is confirmed.
The field names and the example values below are illustrations, not defaults.
`parse_project_references` reads this section and ignores `## Context identities`.
Parsing of `## Context identities` stops at this heading, so these lines never
become identity fields.

```markdown
## Project references
- Jira site: `example.atlassian.net`
- Jira project: `PROJ`
- Jira board: `https://example.atlassian.net/jira/software/c/projects/PROJ/boards/1`
- Figma reference: `https://www.figma.com/design/EXAMPLE/file`
- Figma role: `design-system`
```

Supported fields are `Jira site` (host only), `Jira project` (project key),
optional `Jira board` (URL), optional `Figma reference` (URL), and optional
`Figma role` (`approved-design`, `design-system`, or `inspiration`). Write
only confirmed values, through the approved config change. See
[project-onboarding.md](../../../../references/project-onboarding.md).

Do not create `.ai-dlc-config.md` in every source repository to record a
Bugbot decision. Store decisions under the configured artifact home, keyed by
the stable repository ID.

## Multi-repository `Root`

For a workspace that spans more than one repository (an engagement index that
links to sibling repositories, or a repository index that links into a shared
package repository), record each linked repository's own `Root:` field
relative to the artifact home, for example `Root: ../payments-api` or
`Root: ../../shared/design-system`. This `Root` is what
[validation.md](validation.md) turns into an `authorized_roots` entry: a
mapping from repository ID to that repository's actual root path, so
`resolve_markdown_links` and `resolve_source_path` know which local
directories are in scope without guessing from the filesystem or treating the
whole machine as authorized.

`Root` in `.ai-dlc-config.md` must stay a path relative to the artifact home,
never an absolute local checkout path; only the running validator resolves it
to an absolute path in memory for that one run. Do not write an absolute
machine-local path into `.ai-dlc-config.md`, `AIDLC_CONTEXT.md`, or any other
portable generated document — a different checkout of the same workspace has
a different absolute path, and a committed absolute path would leak local
machine layout into shared, versioned context.

A repository with no declared `Root` cannot be added to `authorized_roots`
for that validation run. Its own links and source paths report `unresolved`,
not silently `ok`; report this to the user as a workspace configuration gap,
not as a passing check.

## Placement: distributed or adopted coordinator

Record the placement mode explicitly once it is established:

```markdown
## Context identities
- Repository: `payments-api`
  - Placement: `distributed`
```

or, when an external coordinator already owns this engagement's context:

```markdown
## Context identities
- Repository: `payments-api`
  - Placement: `adopted-coordinator`
  - Coordinator: `payments-platform-aidlc`
  - Coordinator root: `../payments-platform-aidlc`
```

**Distributed is the default.** Each product Git repository owns its own
context unless adoption is established. Call `resolve_placement` in
`scripts/context_tools.py` with the persisted value: missing config returns
`distributed`, and any other string raises instead of choosing a
destination. A folder name is not an argument to that function.

**Adopt a coordinator** only from persisted configuration already recorded
here, or from unambiguous existing configuration in this repository — for
example a structured operating-model table that names this repository's role
and an explicit artifact-home path for a sibling repository. Never adopt a
coordinator because a folder or repository name happens to end in a
particular suffix; a name is not configuration. If no persisted or
unambiguous configuration exists, stay distributed and say so rather than
guessing.

**In adopted-coordinator mode, module placement is policy, not a
writability fallback.** Call `module_context_destination(placement,
repository_id, module_id)`. For `adopted-coordinator` it always returns
`aidlc-docs/context/<repo-id>/<module-id>.md`. Writability is not an
argument, so a writable source repository cannot move that file. This is different from
the ordinary fallback described in
[context-generation.md](context-generation.md), which only centralizes when
the module root cannot be written — adoption centralizes unconditionally,
by the recorded policy, regardless of writability.

**When the configured coordinator is unavailable** (only one source
repository is open, and the coordinator repository is not reachable from
this window): say plainly that the coordinator-owned index could not be read
or updated, and that this run's findings for this repository are not yet
reflected there. Continue read-only analysis of the repository that is open.
Do not silently create a competing local index for that repository, and do
not write a fallback copy under this repository's own `aidlc-docs/` as if it
were canonical — propose it clearly as pending reconciliation with the
coordinator instead, and ask whether to persist it as a temporary local note
or hold it until the coordinator is reachable.

## Migrating from adopted coordinator to distributed

**Distributed is the only supported migration destination.** There is no
"migrate to a different coordinator" path; a migration always ends with each
product repository owning its own context, per the placement rule above.

A repository's existing `adopted-coordinator` configuration, and the legacy
coordinator repository it points to, are **evidence for discovering the
current layout** — which repositories exist, what each one currently
documents, and what still needs to be preserved. That evidence must never
silently become the permanent destination of a new migration. Concretely,
call `migration_destination_placement(current_placement, migration_approved)`
in `scripts/context_tools.py`. It validates `current_placement` through
`resolve_placement` before choosing a destination. An unknown value raises
`ValueError` whether or not the migration is approved; it is never rewritten
into `"distributed"`.

- During discovery and proposal preparation (`migration_approved=False`),
  it returns the validated current placement unchanged. Preparing a migration
  proposal never flips persisted placement on its own.
- Only an approved migration (`migration_approved=True`) returns
  `"distributed"`, the value then persisted back into `## Context
  identities`.
- A repository that is already `distributed` is unaffected either way, so an
  ordinary refresh of an already-distributed repository never changes
  behavior through this function — it is only relevant once a migration from
  `adopted-coordinator` is actually in play.

`Placement: adopted-coordinator` records the operating mode of a repository
that uses a coordinator. It does not identify the repository currently being
read as that coordinator. Coordinator identity comes only from a `Coordinator`
or `Coordinator root` value, or from operating-model metadata whose subject
is that repository, checked with `repository_is_named_coordinator`. See
[legacy-migration.md](legacy-migration.md).

**If the persisted configuration already explicitly selects
`adopted-coordinator`**, do not silently override it with the distributed
default. Explain the difference between the current adopted-coordinator
placement and the proposed distributed destination in plain terms (where
context currently lives versus where it would move), and include the
placement change explicitly as part of the proposal the user approves — the
same approval gate as any other change set A content. If the user chooses to
keep the adopted-coordinator architecture, honor that choice: leave
`Placement: adopted-coordinator` unchanged, and report plainly that
distributed migration was not completed, rather than reporting partial
completion or asking again later in the same run.

Preparing distributed outputs and the mandatory retirement decision for the
legacy coordinator are both covered in
[legacy-migration.md](legacy-migration.md).
