# Incremental refresh

Use code and versioned contracts as current evidence. Start from existing context, then update only sections affected by the request.

Each context record must include:

- repository path and Git revision;
- relevant uncommitted modifications, without copying sensitive values;
- paths examined and direct dependencies;
- observed facts versus assumptions;
- a freshness boundary, such as "valid for `src/payments/**` at revision `abc123`".

Do not create an integration map for imports within one module. Create it only after observing a dependency across services, repositories, deployable systems, or a public contract boundary.

ADRs record approved architectural decisions. Discovery alone is not an ADR trigger.
