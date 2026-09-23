# Repository preflight

Before reading or changing Git state, resolve the requested working directory and run Git discovery from that directory. Record the actual Git root, current branch, intended remote, and target branch.

The plugin source or installation directory may be a subdirectory of a consumer repository. That can be valid, especially in a monorepo. It does not authorize using the parent repository for delivery or generated context writes.

Inspect staged, unstaged, and relevant untracked files. Preserve work outside the requested scope. If the target repository, remote, branch, consumer root, or generated-document root is unclear, ask the user before any Git or filesystem write.

For each repository in a multi-repository request, run this preflight separately. Do not imply one atomic delivery action across repositories.

Generated writes are limited to `.ai-dlc-config.md`, `aidlc-docs/`, an approved module root's `AIDLC_CONTEXT.md`, and after the per-repository Bugbot approval, `<git-root>/.cursor/BUGBOT.md` plus a nested `<approved-boundary-root>/.cursor/BUGBOT.md`. Do not use these exceptions to create arbitrary Markdown in source trees.

Never initialize Git, stage the parent workspace, run `git add .` across unrelated work, or change parent repository configuration implicitly.
