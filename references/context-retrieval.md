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

## Resolving related repositories

A task may need evidence from more than one repository: a declared sibling in
`.ai-dlc-config.md`'s `## Context identities` (see
[artifact-home.md](../.cursor/skills/sync-context/references/artifact-home.md)
for `Product` and `Related repository`), or a module whose source lives in
another authorized root. Resolve this with the same procedure every
consuming skill uses, instead of inventing a one-off scan:

1. Identify the target repository, and the scope this session is actually
   authorized to inspect (the open folder, the selected multi-root
   `.code-workspace`, or an explicitly supplied set of paths). Do not expand
   scope beyond what was authorized or opened.
2. Discover the Git roots that already exist inside that scope with Git-aware
   inspection, per [repository-preflight.md](repository-preflight.md); a
   worktree, a submodule, and a nested repository are not the same thing,
   and `.git` is not always a directory (`is_declared_submodule`).
3. Read the target repository's own `.ai-dlc-config.md` and
   `aidlc-docs/repository-context.md` first, per the steps above.
4. Resolve any declared `Related repository` entries
   (`parse_related_repositories`) against the roots discovered in step 2,
   matching by canonical remote with `match_related_repositories` — never by
   directory name, workspace-folder label, or checkout naming convention.
   `parse_related_repositories` returns one of four statuses, and each one
   is handled differently, never collapsed into a single "it worked" or "it
   didn't" check:
   - `"missing"` — no sibling declared here. Valid and ordinary; proceed
     with no related-repository context, and do not report this as a
     problem.
   - `"ok"` — every declared entry parsed cleanly. Use `entries` as-is.
   - `"ambiguous"` — the `## Context identities` heading itself is
     duplicated, so nothing under it can be read with confidence. Report
     this plainly and proceed without related-repository context; do not
     guess which copy of the heading is the real one.
   - `"invalid"` — at least one declared entry is malformed (an
     unsupported or unparseable canonical remote, a malformed or
     duplicated `Repository ID`, or a `Context index` that is empty,
     absolute, a URL, or escapes the sibling's own root). `entries` may
     still contain other, separately well-formed entries from the same
     document. Use those well-formed entries, but report the malformed
     one by name (`detail` names which declaration and why) — a
     well-formed entry sitting next to an invalid one is not evidence
     that the whole declaration is trustworthy, so still disclose the
     malformed part even while using what did parse. Never silently treat
     the whole result as "ok" because some entries happened to be fine,
     and never silently drop the malformed entry without saying so.
5. Load only the sibling index and module context that are actually relevant
   to this task, from repositories the match in step 4 found available. Do
   not load every related repository's full context by default. Once a
   related repository is actually open, resolve its declared `Context
   index` with `resolve_related_context_index`, not by joining the string
   onto a path by hand — that function reuses the same symlink-escape
   containment check (`_resolved_inside`) the rest of this module relies
   on, instead of a one-off path join that a crafted symlink inside the
   sibling could escape.
6. Verify an important or stale-looking claim against current source in that
   sibling, the same way this file already requires for the active
   repository; a summary from another repository's index is not
   authoritative over its own code.
7. Report plainly which declared repositories were unavailable this session,
   any ambiguous match, and the resulting limits of the analysis. A related
   repository that could not be opened is a fact to report, not a reason to
   invent a competing context home, and not a reason to block work that does
   not actually depend on it.

Do not scan arbitrary parent directories or the rest of the machine looking
for a declared sibling, and do not clone a missing one automatically. A
canonical remote recorded in configuration is not evidence that a checkout is
actually available this session — only an actual discovered Git root is. Do
not require every repository in a product to be open before answering a
task that only touches one of them, and do not claim a complete
cross-repository analysis after inspecting only one repository when more
were declared. If the host offers no way to enumerate open workspace roots,
use explicitly supplied paths or the selected `.code-workspace` file instead
of guessing, and ask a focused question when the scope truly cannot be
established any other way.

An asymmetric declaration — repository A lists repository B, B does not yet
list A back — is not by itself a conflict; it is usually one side having
synced more recently than the other. Report it as unconfirmed on the side
that is missing it. Treat it as a genuine conflict only when both sides'
declarations are actually available and disagree on the same identity: two
different canonical remotes claiming the same repository ID
(`detect_repository_id_collision`), or the same canonical remote claimed
under two different repository IDs (`detect_canonical_remote_collision`) —
reuse whichever of those two precise checks matches the shape of the
mismatch, and otherwise let the agent explain the difference to the user
rather than blocking on it.
