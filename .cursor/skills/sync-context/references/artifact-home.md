# Artifact home and identity

Resolve the artifact home before generating context.

- **Single repository:** default to the confirmed repository root.
- **Nested tracked module:** default to its owning Git root. Preserve the
  requested module as analysis scope.
- **Multi-repository engagement:** reuse the existing configured artifact home.
  If none exists, choose one writable location inside the user-authorized
  workspace only when one location is clearly the engagement home. Otherwise
  ask one focused question.
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
