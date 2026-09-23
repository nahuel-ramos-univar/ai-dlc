# Incremental refresh

Use code and versioned contracts as current evidence. Start from the short repository index and existing module context, then update only modules affected by the request, changed paths, or stale evidence.

Each repository or module context record must include:

- repository path and Git revision;
- relevant uncommitted modifications, without copying sensitive values;
- paths examined and direct dependencies;
- observed facts versus assumptions;
- a freshness boundary, such as "valid for `src/payments/**` at revision `abc123`".

Preserve human-authored content where it does not conflict with source. Flag and refresh a stale summary; code and contracts remain authoritative. Do not scan vendor, build, cache, generated, or inaccessible sibling directories.

Do not create an integration map for imports within one module. Create it only after observing a dependency across services, repositories, deployable systems, or a public contract boundary.

ADRs record approved architectural decisions. Discovery alone is not an ADR trigger.
