# Context retrieval

Resolve the active repository, requested module scope, and configured artifact
home from the request, Jira item when available, and affected paths. Read the
artifact-home `.ai-dlc-config.md` and short
`aidlc-docs/repository-context.md` index first. Do not assume the working
directory is the artifact home.

Read only the selected colocated `<module-root>/AIDLC_CONTEXT.md` files. If the
index identifies an artifact-home fallback, read that linked file instead. Read
`integration-map.md` and adjacent module context only when the change crosses a
verified boundary. If a context link is missing, stale, or broken, say so,
inspect current source selectively, and offer `/sync-context`; do not silently
load every module context.

For refinement, implementation, validation, defects, and review, inspect current source, tests, and contracts before making claims or edits. A summary is not authoritative over code.

When delegating, provide the task and scope, repository and module identity,
resolved source paths, module or fallback context paths, relevant interfaces
and dependencies, baseline and local changes, unknowns, and stop conditions.
Do not assume an agent inherits the main chat's reads.

Plan work reads only enough code and Jira context to understand product impact. Refinement can inspect technical contracts more deeply. Implementation and validation require current code and test evidence.
