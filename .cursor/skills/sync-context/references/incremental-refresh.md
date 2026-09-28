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
whole repository was read. Never equate a Git listing or a fingerprint's file
set with having examined, analyzed, or verified every one of those files;
inventoried, inspected, and verified are different evidence levels and the
generated record must not blur them.

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

The fingerprint algorithm is `content_fingerprint` in `scripts/context_tools.py`: a deterministic SHA-256 over each examined file's repository-relative path and content hash, truncated to 16 hexadecimal characters. It detects a change in the included inputs; it does not prove semantic accuracy or that every file was fully inspected. A recorded Git revision by itself does not cover uncommitted working-tree changes; the fingerprint must include relevant staged, unstaged, and selected untracked source so the recorded freshness reflects the actual working tree, not only the last commit. If the prior baseline is missing or incompatible with the current scope, perform a fresh scoped inspection and report that limitation rather than reusing a stale comparison.

Preserve human-authored content where it does not conflict with source. Flag and
refresh a stale summary; code and contracts remain authoritative. Do not scan
vendor, build, cache, generated, or inaccessible sibling directories.

Do not create an integration map for imports within one module. Create it only after observing a dependency across services, repositories, deployable systems, or a public contract boundary.

ADRs record approved architectural decisions. Discovery alone is not an ADR trigger.
