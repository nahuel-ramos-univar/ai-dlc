---
name: scaffold-project
description: Establish an approved minimal technical foundation for a new project. Use when the user asks to scaffold, bootstrap, or set up a new application project.
disable-model-invocation: true
---

# Scaffold project

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Workflow
1. Inspect the requested destination, existing files, project configuration, and unrelated changes. Do not assume the current directory is the project root. Discover an existing Git root and remotes with local Git. Do not initialize Git, clone, or create a remote.
2. Identify the requested application type and technologies already decided. Ask only questions needed to define a minimal foundation. Read [project onboarding](../../../references/project-onboarding.md) only when project references are missing, ambiguous, or explicitly being reconsidered. This is an instruction for the current run, not a conditional loader. `parse_project_references`'s `"invalid"` status is also a gap, not a confirmed value — treat it the same as missing or ambiguous. `"ok"` only means the fields that are present passed syntax checks; do not treat a missing optional board or Figma reference as a reason to ask every onboarding question again. Include confirmed conventions in the proposal below. Do not start `sync-context` to repeat that step.
3. Resolve whether this is a single repository, a monorepo, or a new repository meant to sit alongside others as part of one product. Membership for the *new* project comes only from the explicit request, existing configuration that already applies to it, context already confirmed earlier in this session, or a focused confirmation question when none of those resolve it — never from location alone. Ask only when none of those already establish it; do not ask when the user already said "add a repo to the X product." A destination that happens to sit next to a sibling repository with a confirmed `Product` label, or that shares a directory-name prefix with one, is a discovery hint worth surfacing in that one focused question, never automatic membership on its own -- an adjacent folder is not evidence of product membership by itself. For a new repository joining an existing product, agree on its components, its responsibility relative to the siblings, and its target location before proposing files.
4. Classify the destination as a directory without a Git root, a Git repository without a remote, or a repository with an established identity. Establish separately whether a Git root exists, whether HEAD resolves to a commit, whether a canonical remote is established, and whether a repository ID is already persisted or explicitly assigned. Follow [foundation and review](references/foundation-and-review.md). Never fabricate a remote, a revision, or a claim that an identity was verified. Record a revision only when HEAD resolves; otherwise a Git working tree uses baseline `no-commit` and stays on Git file discovery. If the existing context format cannot represent a required value honestly, defer that artifact and say why. Do not invent a second context format, and do not initialize Git to satisfy context validation.
5. If an application already exists, propose a bounded addition or stop for clarification. A destructive overwrite and an approved edit are different. A narrowly scoped edit to an existing manifest, workspace file, index, or README is allowed when the proposal names that file and that edit. Preserve unrelated content and local changes. Stop when ownership or a conflicting edit is ambiguous. Preserving existing files does not forbid a legitimate monorepo update the proposal named.
6. Present a short proposal before writing anything. Include destination, stack, assumptions that still need confirmation, repository structure, files to create, existing files to modify, a minimal entrypoint or representative smoke behavior, required configuration with safe example values, any install or generator command, how to start and validate the result, and which context files can be generated now. A library does not need an application server. A documentation-only foundation does not need an artificial build pipeline. Also name the initial context artifacts this scaffold will generate (a repository index and, for each created module, concise module context -- see [context-generation.md](../sync-context/references/context-generation.md) and [context-templates.md](../sync-context/references/context-templates.md), reused rather than reinvented here) and, when this scaffold is part of a multi-repository product, the planned `Product` label and `Related repository` entries (per [artifact-home.md](../sync-context/references/artifact-home.md)) and whether a local multi-root `.code-workspace` would help. Mark every component this proposal does not actually create as planned, not implemented or verified -- a proposal describing three repositories when only one is being scaffolded now must say so plainly, and the same separation applies to context: propose generating context only for what this run actually creates, never for a sibling or a not-yet-written component.
7. Obtain approval for that exact proposal before writing. Approval of a prose project rule does not authorize dependency installation or execution of a project generator. If a generator initializes Git or performs another out-of-scope action, use a supported way to disable that action or propose a safe alternative. Do not run it blindly.
8. Create only the approved foundation, including a `.code-workspace` file when approved -- preserve any existing one's unrelated settings, tasks, and comments (treat it as JSONC, not plain JSON) rather than overwriting it wholesale. Once, before applying the approved change set, recompute `content_fingerprint` for the proposal's source scope and read every destination, including a path expected not to exist. Call `proposal_is_current` with the fingerprint and destination text captured for the proposal and with the values just read. If it returns false, preserve the unexpected edit and ask again before any write. During application, do not compare the evolving source tree to that original fingerprint. This run's approved writes are expected. Before each write, compare only that destination with its expected state: the pre-run text if this run has not written it, or the last text this run wrote. A new path must still be absent; if it appeared, preserve it and do not overwrite it. If an unexpected edit appears after some writes, stop the affected work, report what was already applied and what remains pending, preserve the intervening edit, and do not claim the writes were atomic. Ask again only for the part of the proposal that changed. Then generate the repository index and module context from the actual resulting source, scoped to the files this run actually created -- one meaningful module context per real, approved module, never one per arbitrary directory. Reuse the existing context-generation conventions and size budget ([context-generation.md](../sync-context/references/context-generation.md)); do not invent a second context format for a scaffolded project. For each Git case, write only the context and metadata that case supports, as stated in [foundation and review](references/foundation-and-review.md). Do not launch `sync-context` from inside this skill to perform this generation; this skill writes the initial context directly, reusing the same references. Include a concise README with actual setup and validation instructions.
9. Run the relevant available checks, including `validate_generated_context` on the index and module context this run wrote. Report each check as passed, failed, skipped, or unable to run, with the reason. Separate mechanically valid context, source-supported prose, and a check that was not executable. A passing validation check does not prove the prose. Do not launch `sync-context` to validate this context.
10. Request one independent review when [foundation and review](references/foundation-and-review.md) says the change warrants it. Use `implementation-reviewer` in its scaffolding review mode. The main chat creates the scaffold; the reviewer is read-only and must inspect the generated files, not only this chat's summary. A trivial structural or documentation-only scaffold may take a documented review skip; say why. That skip is complete. When a required review cannot run, say independent review was not performed, do not label a self-review as independent, and leave that review pending. Resolve a concrete blocker inside the approved scope and rerun the affected checks. If that fix changes source evidence, refresh the affected context before reporting it as current. Scope expansion needs a new proposal and a new approval. Do not open an unbounded review loop, and do not write a review report into the consumer repository.

## Boundaries
Preserve user files and changes. Follow existing project conventions when present.
Do not implement business features; create Jira work; initialize or restructure Git;
commit, push, open a PR, merge, deploy, or provision infrastructure; generate
credentials or write secrets. Do not add authentication, databases, containers,
continuous integration, or end-to-end testing unless the approved scope includes it.
Approval of a prose project rule does not authorize dependency installation or
CI changes. A missing Figma or Jira reference does not block a local scaffold.
Do not fabricate a remote URL, a commit revision, or a claim that identity
was verified for a repository that has no Git root yet; a folder without a
Git root is not yet a verified Git repository. An explicit repository ID the
user confirms for an unversioned tree or a repository without a remote is an
assigned ID, not a verified remote identity. Evaluate each confirmed `Related repository` entry on its own. The entry
needs the referenced repository's real canonical remote, not this project's
remote. Defer only the entry whose target remote cannot be established, name
that entry and why, and proceed with the rest of the approved scaffold
instead of inventing a value. Do not launch another `sync-context`
session from inside this skill; reuse [artifact-home.md](../sync-context/references/artifact-home.md)
and [repository preflight](../../../references/repository-preflight.md)
directly.

Do not claim a named slash command ran automatically. If a later context sync or
validation would help, describe it honestly as a next step.

## Output
Return the approved scope, files created, files modified, how to run the foundation, checks passed, failed, skipped, or unavailable, independent review status and any unresolved finding, context artifacts generated or deferred and the missing prerequisite for each deferred artifact, and remaining prerequisites.

A generated file tree alone does not prove the foundation works. A successful build does not prove all runtime behavior works. Review completion does not replace executable validation.

Read [foundation and review](references/foundation-and-review.md),
[repository preflight](../../../references/repository-preflight.md) for Git
classification, authorization, and preservation rules,
[artifact-home.md](../sync-context/references/artifact-home.md) for the
`Product` and `Related repository` convention this skill reuses rather than
inventing its own,
[context-generation.md](../sync-context/references/context-generation.md) and
[context-templates.md](../sync-context/references/context-templates.md) for
the initial repository-index and module-context format and size budget this
skill reuses rather than inventing its own,
[validation.md](../sync-context/references/validation.md) for
`validate_generated_context`, and
[skill composition](../../../references/skill-composition.md). The
context-discovery write list does not apply to approved scaffold files, except
that the `.code-workspace` write still follows the bounded conditions in
[repository preflight](../../../references/repository-preflight.md).
