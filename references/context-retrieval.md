# Context retrieval

Identify the selected consumer repository and likely modules from the request, Jira item when available, and affected paths. Read `.ai-dlc-config.md` and the short `aidlc-docs/repository-context.md` index first.

Read only the selected colocated `<module-root>/AIDLC_CONTEXT.md` files. If the repository index identifies an artifact-home fallback, read that linked file instead. Read `integration-map.md` and adjacent module context only when the change crosses a verified boundary. If module selection is uncertain, say so, search paths, and expand context selectively.

For refinement, implementation, validation, defects, and review, inspect current source, tests, and contracts before making claims or edits. A summary is not authoritative over code.

When delegating, provide repository ID, module root or fallback context path, source paths, contract concerns, evidence revision, and uncertainties. Do not assume an agent inherits the main chat's reads.

Plan work reads only enough code and Jira context to understand product impact. Refinement can inspect technical contracts more deeply. Implementation and validation require current code and test evidence.
