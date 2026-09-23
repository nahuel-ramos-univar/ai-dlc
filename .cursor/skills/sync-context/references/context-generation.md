# Context generation

Before writing, confirm the consumer repository root, generated-document root, and approved module roots. Write only under `<consumer-root>/aidlc-docs/`, `<consumer-root>/.ai-dlc-config.md`, and the narrow exception `<approved-module-root>/AIDLC_CONTEXT.md`. A plugin source directory inside another Git repository is not automatically the consumer root.

Keep `.ai-dlc-config.md` minimal. Keep `aidlc-docs/repository-context.md` as a short workspace index. It lists each actual Git root, its repository ID, meaningful modules, source paths, freshness marker, and links to colocated context. It is not a codebase dump.

Use `<module-root>/AIDLC_CONTEXT.md` for useful modules. A module has an architectural responsibility: app, API, service, shared package, or infrastructure stack. Do not infer a module from directory depth. A small single-module repository keeps one concise repository context and no manufactured module file.

If the source repository or module root cannot be written, use the documented fallback `aidlc-docs/context/<repo-id>/<module-id>.md` and link it from the repository index. Do not write arbitrary Markdown elsewhere in source repositories.

Generate IDs from verified paths for the index and fallback only:

- Slug: lowercase, replace any character outside `[a-z0-9]` with `-`, collapse repeated `-`, and trim leading or trailing `-`. If the slug is empty, use `repo` or `module`.
- `repo-id`: slug of the repository-root basename plus `-` plus the first eight hexadecimal characters of a SHA-256 hash of its resolved root path.
- `module-id`: slug of the responsibility name plus `-` plus the first eight hexadecimal characters of a SHA-256 hash of its repository-relative source path.

Reject IDs outside `[a-z0-9-]`. Never use raw user input as a path. Record the resolved source paths inside each document to prevent collisions and path traversal.

Each module `AIDLC_CONTEXT.md` states repository identity, source paths, responsibility, entry points, interfaces, callers or dependencies, verified tests and commands, constraints, evidence paths, freshness, and explicit unknowns. Do not copy source, generated output, vendor content, cache content, or secrets.

Refresh only modules affected by changed paths, requested scope, or stale evidence. Preserve human-authored sections. If a safe merge is unclear, show a targeted diff. Current code and contracts override a stale summary. Create `aidlc-docs/integration-map.md` only for verified cross-module or cross-repository dependencies. Link existing ADRs when relevant; never invent one.

## Examples

Single-module repository:

```text
aidlc-docs/
  repository-context.md
```

`repository-context.md` identifies the Git root, `src/`, entry point, tests, evidence revision, and unknowns. No module file is created.

Monorepo:

```text
aidlc-docs/
  repository-context.md
apps/
  storefront/
    AIDLC_CONTEXT.md
services/
  orders/
    AIDLC_CONTEXT.md
```

Multi-repository workspace (two Git roots; do not write `aidlc-docs/` at a parent folder that is not a confirmed consumer Git root):

```text
web/                              # Git root
  aidlc-docs/
    repository-context.md
  apps/
    storefront/
      AIDLC_CONTEXT.md
payments/                         # Git root
  aidlc-docs/
    repository-context.md
    integration-map.md            # only after a verified web-to-payments contract, in the consumer root that requested the sync
```

If `payments/` is itself a small single-module repository, keep context in its index and do not create `payments/AIDLC_CONTEXT.md`.
