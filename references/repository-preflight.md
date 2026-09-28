# Repository preflight

Before reading or changing Git state, resolve the requested working directory and
run Git discovery from that directory. Record the actual Git root, current
branch, intended remote, and target branch. Classify the requested path as one
of:

- **Git root:** the working directory is the repository root.
- **Nested tracked module:** it is inside that Git root and Git tracks files
  there (`git ls-files` is non-empty for that path).
- **Nested repository, submodule, or worktree:** Git discovery from the path
  reports that repository's own root. It owns its identity and baseline.
- **Unversioned tree:** it has no Git root, or the containing repository does
  not track the requested path.
- **Multi-repository workspace:** each discovered Git root is classified
  independently.

The plugin source or installation directory may be a nested tracked path. That
can be valid, especially in a monorepo. It does not authorize treating the
parent as the delivery target or writing generated context at a non-consumer
root.

For a **nested tracked module**, preserve the requested directory as the analysis
scope. Its owning Git root provides the revision and local-change baseline.
Generated navigation context belongs at the resolved artifact home. A colocated
`AIDLC_CONTEXT.md` may be written at the approved module root. Do not block,
call it untracked, offer `git init`, or expand the analysis scope by default.

For a **nested repository, submodule, or worktree**, use its own Git root and
never silently use the parent identity or revision. For an **unversioned tree**,
permit discovery and use baseline `unversioned`. Record enclosing Git discovery
only as a warning; do not use the parent `git_root` or commit SHA as identity
or freshness. Ask only when artifact-home or write scope is ambiguous. Never
run `git init`.

Inspect staged, unstaged, and relevant untracked files. Preserve work outside
the requested scope. If the target repository, remote, branch, artifact home,
or generated-document root is unclear, ask the user before any Git or
filesystem write.

For each repository in a multi-repository request, run this preflight separately. Do not imply one atomic delivery action across repositories.

Context-discovery writes are limited to the configured artifact home's
`.ai-dlc-config.md` and `aidlc-docs/`, an approved module root's
`AIDLC_CONTEXT.md`, and after per-repository Bugbot approval,
`<source-root>/.cursor/BUGBOT.md` plus a nested
`<approved-boundary-root>/.cursor/BUGBOT.md`. Do not use those exceptions to
create arbitrary Markdown in source trees.

Scaffold-project writes follow the approved proposal and authorized destination.
That approved scope may include source files, project configuration, and
README files. Do not apply the context-discovery write list to those files.

Never initialize Git, stage the parent workspace, run `git add .` across unrelated work, or change parent repository configuration implicitly.
