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
- Module: `payments-api`
  - ID: `payments-api`
  - Source: `services/payments`
```

Do not create `.ai-dlc-config.md` in every source repository to record a
Bugbot decision. Store decisions under the configured artifact home, keyed by
the stable repository ID.
