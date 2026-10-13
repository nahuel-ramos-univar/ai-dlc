# Foundation, identity, and review

Use this from `scaffold-project`. It does not add a second context format or a second validator.

## Usable foundation

The proposal shown before approval names, for this project type:

- destination, and whether the result is a single repository, a monorepo, or a new repository beside others;
- the chosen stack, and any assumption that still needs confirmation;
- files to create, and existing files to modify;
- a minimal entrypoint or one representative smoke behavior;
- required configuration, with safe example values only;
- a dependency install or generator command, when the approved scope needs one;
- how to start the result and how to validate it;
- which context files can be generated in this run, and which stay deferred.

Adapt the list to the project. A library does not need an application server. A documentation-only foundation does not need an artificial build pipeline. Omit a line that does not apply, and say why.

Do not add authentication, databases, containers, continuous integration, deployment, business features, or end-to-end tooling unless that item is in the approved scope.

Approval of a prose project rule does not authorize dependency installation or execution of a project generator. If a generator initializes Git or does anything else outside the approved scope, use a supported way to disable that action, or propose a safe alternative. Do not run it blindly.

## Repository organization and workspace

Resolve organization (single repository, monorepo, or multiple related repositories) and the optional local workspace as two separate decisions, per `SKILL.md` steps 3 and 3a. Neither decision infers membership from an adjacent folder, a similar directory name, or an enclosing Git repository.

A recommendation is about the confirmed product's needs, not the presence of multiple technical layers. A product with a frontend, a backend, and infrastructure still fits comfortably in one monorepo; recommend separate repositories only when a confirmed need actually calls for independent versioning, independent deployment, or a separate team boundary — state that reason plainly.

For a confirmed multi-repository product, track three distinct sets so the proposal never conflates them: repositories that already exist (with their own identity, resolved per [Git identity](#git-identity) below), project directories this run will actually create, and components that stay planned or deferred because this run does not scaffold them. A proposal describing three repositories when only one is being scaffolded now must say so plainly — the same separation [the usable foundation](#usable-foundation) and `## Related repository entries` already require for context generation and sibling references.

This skill scaffolds one destination per run. A new multi-repository product needs one approved run per repository; state that limit instead of writing files across several repository roots in one pass. Creating a project directory, including one later confirmed to be a monorepo module or a sibling repository's folder, is never itself proof that a Git repository exists there — `classify_repository_scope` still reports `unversioned` or `untracked-tree` for that folder until a real `.git` root is discovered or that destination is explicitly confirmed as a module of one. Say explicitly that Git setup (`git init`, a remote, a hosted repository) is a developer step this skill does not perform, for every repository this run did not already find with a Git root.

For the optional workspace, reuse the exact JSONC, path, and bounded-write rules already defined in [repository preflight](../../../../references/repository-preflight.md) under "`.code-workspace` writes" — this section does not restate them. A workspace is a local Cursor convenience; it never substitutes for the repository-organization decision, and recommending one is never a reason to skip asking the organization question first.

## Git identity

Classify the destination with [repository preflight](../../../../references/repository-preflight.md), then establish these four facts separately with read-only Git. Never fabricate a remote, a revision, or a claim that an identity was verified. Never run `git init`, create a commit, or invent a SHA to make validation pass. A missing commit does not block the approved scaffold.

1. **Git root.** `git rev-parse --show-toplevel` succeeds. If it fails and a `.git` marker exists at or above the destination, the repository is broken or inaccessible. Report that error. Do not record `unversioned` or `no-commit`, and do not treat it as a directory without Git. `classify_repository_scope` returns `unversioned` whenever toplevel fails, including this broken case, so do not use that one label by itself. A successful toplevel only reports the nearest enclosing Git root; it does not by itself make the destination part of that repository (see fact 1a).
1a. **Ownership, not just presence.** `classify_repository_scope` reports one of four kinds for the destination: `unversioned` (no `.git` marker anywhere above it), `git-root` (the destination is the toplevel itself), `nested-tracked` (inside a Git root, and Git already tracks it there), or `untracked-tree` (inside a Git root, but Git does not track it there — `git_root` is `None`, and the enclosing root is recorded only as `enclosing_git_root`, a fact, not an identity). Do not treat `enclosing_git_root` as this destination's own Git root unless step 3's membership confirmation — never inferred from location alone — says this destination is a module of that same repository, not merely a sibling repository confirmed as part of one product. Confirming product membership for a separate sibling repository never adopts any repository's Git identity for this destination; it only governs `Related repository` entries below.
2. **HEAD commit.** Only when a Git root exists, run `git rev-parse --verify HEAD`. Record that revision only when it resolves. An expected unborn HEAD fails with "Needed a single revision" or "unknown revision" while toplevel still succeeds. That baseline is `no-commit`, in the existing Baseline field. Any other Git error is not an empty repository; report it and do not disguise it as `no-commit`.
3. **Canonical remote.** Read the configured remote and normalize it with `normalize_remote`. Write `Canonical remote` only when that succeeds on an actual remote. A configured remote does not mean a commit exists.
4. **Repository ID.** Reuse a persisted ID. Do not ask for a new one merely because no remote exists. If none is persisted and no verified remote can derive one, ask once and assign an explicit ID with `stable_repository_id`. Say that this ID was assigned, not verified from a remote.

**Directory without a Git root (`unversioned` kind, no enclosing root).** No `.git` marker exists anywhere above the destination, and toplevel fails outright. This is an unversioned tree. The baseline is `unversioned`. `content_fingerprint` discovers files with its own filesystem walk here, because there is no Git metadata anywhere to discover them from. Do not record a commit SHA. Omit this project's `Canonical remote`. The repository ID follows fact 4. The index and module context may still be written when the artifact home is explicit and writable.

**Untracked tree inside an enclosing Git root (`untracked-tree` kind).** This is the common case for a brand-new, standalone project created inside an existing checkout — for example a sibling folder next to other repositories. Unless step 3 already confirmed this destination is a module of that same enclosing repository — distinct from confirming it is a sibling repository in the same product, which never adopts that repository's identity — give it the same identity as **Directory without a Git root**: baseline `unversioned`, no inherited revision, no inherited remote, no inherited repository ID. `content_fingerprint` does not use the enclosing repository's exclude rules for this kind. It lists the destination's files without that checkout's `.gitignore`, and it still drops generated context, caches, nested repositories, symlink escapes, secrets, and files excluded by an ignore rule inside the destination. Listing files this way does not grant this destination the enclosing repository's identity. An enclosing rule such as `new-project/` must not hide source or make a later edit look fresh. A genuinely empty destination still has an empty fingerprint. If an in-scope ignore rule cannot be applied safely, report freshness as unresolved; do not record an empty fingerprint as if the tree had no source. Never run `git init`, stage files, or otherwise modify the enclosing repository to force a different classification. Confirming monorepo membership changes the recorded identity, not this discovery rule. Enclosing exclude rules apply again only once Git tracks the path (`nested-tracked`).

**Confirmed new module of an existing monorepo.** When step 3's explicit confirmation — never inferred from location alone, and distinct from confirming only product membership for a sibling repository — says this destination is a new module of the same repository found at `enclosing_git_root`, that repository's own identity governs: its persisted repository ID, its real `HEAD` revision when one resolves, and its real canonical remote. Allowed writes are the approved files inside that module plus any explicitly named shared file in the approved proposal, such as a root manifest, workspace file, index, or README, and only the edit that proposal describes. Membership in the monorepo does not authorize an arbitrary edit at the repository root. Preserve unrelated content and local changes. Do not restage the repository or touch a file the proposal did not name.

**Git repository without a remote (`git-root` kind, no canonical remote).** A Git root exists and no canonical remote normalizes. Do not invent a remote. Omit `Canonical remote`. The fingerprint uses Git file discovery, not the unversioned walk, including when there are no commits. Do not classify that working tree as a directory without Git. If HEAD resolves, the baseline is that revision. If HEAD is an expected unborn HEAD, the baseline is `no-commit`. The repository ID follows fact 4.

**Established identity (`git-root` kind, with a remote or a persisted ID).** A canonical remote normalizes, or a persisted repository ID already exists. Keep that persisted ID. Derive an ID from the remote with `stable_repository_id` and `normalize_remote` only when no ID is persisted yet. The same HEAD rule applies here: a configured remote does not guarantee a commit. Record the revision only when HEAD resolves; otherwise record `no-commit`. The fingerprint stays Git-based.

## Related repository entries

Evaluate each proposed `Related repository` entry on its own. The entry stores the referenced repository's canonical remote, not this project's remote. This project's missing Git root or missing remote does not defer that entry.

Example: `payments-web` is being scaffolded and has no remote yet. Its product membership is already confirmed. `payments-api` already has the verified remote `github.com/example/payments-api`. Record the outgoing reference from `payments-web` to `payments-api` using that remote. Do not write the reverse reference into `payments-api` unless that sibling checkout is authorized for this write. Do not invent a reciprocal entry.

Require the referenced repository's real canonical remote, normalized the same way as any other remote. Adjacency or a similar directory name does not establish membership. Defer only the entry whose target remote cannot be established, name that entry, and say why. Keep every entry whose target remote is real. Do not create another membership format.

## Bounded edits

A destructive overwrite and an approved edit are different. An approved addition may edit an existing manifest, workspace file, index, or README when the proposal names that file and that edit. Preserve unrelated content and local changes. Stop and clarify when ownership or a conflicting edit is ambiguous. Preserving existing files does not forbid a legitimate monorepo update that the proposal named.

Once, before applying the approved change set, recompute `content_fingerprint` for the proposal's source scope and read every destination, including a path the proposal will create. Call `proposal_is_current` with the fingerprint and destination text captured for the proposal and with the values just read. `None` is the expected destination when the path should still be absent. If it returns false, preserve the unexpected edit and ask for approval of the affected revision before any write.

During application, do not compare the evolving source tree to that original fingerprint. Creating an approved source file changes `content_fingerprint`; that change is expected and is not a reason to ask again before the next approved edit. Before each write, compare only that destination with its expected state: the pre-run text if this run has not written it, or the last text this run wrote. Do not treat every current file as a new baseline. An unrelated or external edit is still unexpected. A new path must still be absent; if another process created it, preserve it and do not overwrite it. Keep the existing path, scope, symlink, and authorization limits.

If an unexpected edit appears after some writes, stop the affected work. Report what was already applied and what remains pending. Preserve the intervening edit. Do not roll the applied writes back, and do not claim the writes were atomic. Ask again only for the part of the proposal that changed.

After the approved files exist, generate or refresh context from the actual resulting source. If a review fix changes source evidence, refresh the affected context before reporting it as current. The once-before-write check in [context-generation.md](../../sync-context/references/context-generation.md) still governs a `sync-context` proposal. Do not weaken it, and do not reuse it between this run's own approved source writes.

## Context validation

After the index and module context for this run exist on disk, call `validate_generated_context` as specified in [validation.md](../../sync-context/references/validation.md). Build `authorized_roots` from the repository ID and root recorded for this destination. Do not start a `sync-context` session to generate or validate this context.

Report three layers separately:

- **Mechanically valid** — checks whose status is `passed`. A pass does not prove the prose is true.
- **Source-supported prose** — a claim tied to a file this run actually wrote or read. Validation does not decide this.
- **Not executable** — a check whose status is `unresolved`, or a command that could not be run. Do not treat either as a pass.

`index:budget` is a hard failure over 150 lines. Module line count is a metric from `document_metrics`, not a pass or fail. See [context-templates.md](../../sync-context/references/context-templates.md).

## Proportionate review

The main chat creates the approved scaffold. Review is read-only.

Skip independent review for a trivial structural or documentation-only scaffold. Say why. That documented review skip is complete for that trivial case.

Request one independent `implementation-reviewer` assessment, in its scaffolding review mode, when the scaffold is any of:

- a generated runnable application or library;
- a change to an existing manifest or workspace wiring;
- more than one component, or setup the approved scope marked security-sensitive.

Follow [skill composition](../../../../references/skill-composition.md) for dispatch. An agent file is not a `subagent_type`. When the host can run only a general-purpose subagent, pass `agents/implementation-reviewer.md` as bounded context and label the result a general-purpose independent review. When no independent subagent can run, say independent review was not performed. Do not label a self-review as independent. Leave the required review pending. Do not invent a policy exception that marks it complete.

Give the reviewer the approved scope and intended project type, the confirmed product purpose and the scaffolding boundary (technical foundation, navigable prototype, or working business feature; see [product-purpose.md](product-purpose.md)), the files created and modified, the relevant existing conventions, the commands actually run and their results, the unresolved assumptions, and the deferred work. The reviewer must open the generated files and the surrounding configuration. A summary from this chat is not that inspection. The reviewer looks for a concrete defect, including a missing entrypoint, a broken script, inconsistent configuration, invalid workspace wiring, an unsafe default or exposed secret, a README that does not match the generated behavior, an unintended edit, or an unsupported statement in generated context.

Resolve a concrete blocker that stays inside the approved scope, then rerun the affected checks. A fix that expands scope needs a new proposal and a new approval. Do not open an unbounded review loop.

Do not write a review report, an implementation plan, or a per-run Markdown file into the consumer repository.
