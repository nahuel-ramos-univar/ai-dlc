# Discovery and incremental refresh

Use code and versioned contracts as current evidence. Pick one internal mode.

## Initial discovery

Use initial discovery when the repository index or usable module context is
missing, when the user asks for a full refresh, or when the prior baseline
cannot be compared. Identify meaningful modules from workspace configuration,
manifests, deployment boundaries, entry points, contracts, and test structure.
Inspect representative source and relevant dependencies. Do not require a dirty
diff and do not read every source file by default.

Record examined paths, declared scope, and unknowns. “Initial discovery
completed” means only that the recorded scope was examined; it never means the
whole repository was read.

## Incremental refresh

Use incremental refresh only when usable prior context exists. Compare its
recorded baseline and fingerprint to current source plus staged, unstaged, and
relevant untracked changes. Refresh affected modules and index entries.
Expand to downstream consumers when shared contracts, packages, configuration,
or interfaces change. Detect new, removed, and renamed files or modules. If the
old baseline is unavailable, use bounded rediscovery instead of claiming
freshness.

Preserve unchanged content and avoid timestamp-only rewrites.

Each repository or module context record must include:

- repository path and, when the consumer is a Git root or nested tracked path,
  that Git root's revision;
- a freshness fingerprint of examined source paths; generated context files do
  not participate in that hash;
- relevant uncommitted modifications, without copying sensitive values;
- paths examined and direct dependencies;
- observed facts versus assumptions;
- a freshness boundary such as "valid for `src/payments/**` at revision `abc123`, fingerprint `a1b2c3d4`" or, for an unversioned tree, "unversioned; fingerprint `a1b2c3d4` for `services/checkout/**`".

Do not use a parent repository revision as freshness when that revision does not track the examined files.

Preserve human-authored content where it does not conflict with source. Flag and
refresh a stale summary; code and contracts remain authoritative. Do not scan
vendor, build, cache, generated, or inaccessible sibling directories.

Do not create an integration map for imports within one module. Create it only after observing a dependency across services, repositories, deployable systems, or a public contract boundary.

ADRs record approved architectural decisions. Discovery alone is not an ADR trigger.
