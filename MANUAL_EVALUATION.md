# Manual evaluation checklist

- [ ] Merge a `feat:` or `fix:` commit to `main` and confirm `plugin.json`, `CHANGELOG.md`, tag `vX.Y.Z`, and a GitHub Release update together.

- [ ] Install the plugin into a clean consumer and confirm all seven skills and seven agents are discovered.
- [ ] Run `scaffold-project` in an empty authorized destination. Confirm it presents an approved minimal proposal before writing, preserves existing files, writes a concise README, and reports actual validation results.
- [ ] Run `scaffold-project` in an existing application. Confirm it proposes a bounded addition or stops for clarification without overwriting the application.
- [ ] Run `sync-context` against a small behaviorful single-module service (API handler, database, external integration, authentication, retries/errors). Confirm it creates `AIDLC_CONTEXT.md`, is not treated as index-only merely because it is single-module, and that `## Material architecture details` preserves the important discovered information rather than reducing it to one-line Coverage rows.
- [ ] Run `sync-context` against a genuinely trivial repository (documentation-only, trivial metadata/config, or an extremely small passive types/constants package). Confirm index-only behavior is an empty `## Modules` table with no module row pointing nowhere, and that validation still passes.
- [ ] Run `sync-context` against a monorepo. Confirm it creates `<module-root>/AIDLC_CONTEXT.md` only for meaningful architectural modules.
- [ ] Run initial discovery in a clean repository with no prior context. Confirm it finds representative modules without claiming every source file was read.
- [ ] Re-run as incremental refresh after a shared contract changes. Confirm affected consumers expand while unrelated contexts remain unchanged.
- [ ] Run `sync-context` against two accessible Git roots. Confirm the short index distinguishes both roots, links to their colocated contexts, and adds `integration-map.md` only after a verified cross-repository dependency.
- [ ] Use a read-only source repository with an authorized writable artifact home. Confirm the index and fallback context save there without modifying the source root.
- [ ] Use a non-writable module root. Confirm the index links to `aidlc-docs/context/<repo-id>/<module-id>.md` fallback instead of writing in the source tree.
- [ ] Confirm `repo-id` is stable across clones: persisted ID, or canonical remote when no ID exists; never an absolute checkout path.
- [ ] Re-run `sync-context` without relevant source changes. Confirm it preserves human content and does not rewrite unaffected module context.
- [ ] Change one module after context generation. Confirm only that module is refreshed and stale evidence is flagged.
- [ ] Confirm context retrieval reads the short index first, then selected colocated `AIDLC_CONTEXT.md` or its fallback, then current source and tests for implementation or review.
- [ ] Decline the proposed BUGBOT files. Confirm the artifact-home `.ai-dlc-config.md` records `## Bugbot decisions` and later sync runs do not prompt again.
- [ ] Approve a proposed BUGBOT file in a disposable repository. Confirm only the previewed file is written and existing BUGBOT content is preserved.
- [ ] Use a module with a distinct runtime or invariant. Confirm a nested BUGBOT proposal is created only for that boundary and does not repeat the root file.
- [ ] Confirm each proposed Bugbot rule names an observed path plus helper, interface, or invariant, and avoids formatter or generic-security guidance.
- [ ] Confirm generated, vendor, build, coverage, lockfile, and fixture directories receive no BUGBOT files.
- [ ] Confirm BUGBOT guidance is not reported as Bugbot execution.
- [ ] Run a single Story intake. Confirm the draft becomes ready for review, product review is requested, and publication needs an exact approved change set.
- [ ] Run an Epic intake. Confirm overlapping Stories and missing outcome coverage are reported.
- [ ] Run a backlog proposal. Confirm dependencies are identified without inventing sprint capacity.
- [ ] Update an existing Story. Confirm unrelated fields are preserved in the proposed diff.
- [ ] Confirm `plan-work` does not run a standalone duplicate search before product review. If an obvious duplicate is already referenced or appears while reading a candidate parent, it is surfaced. Disconnecting Jira is not reported as "no duplicates."
- [ ] Disconnect Jira during a prepared operation. Reconnect and confirm the draft resumes without restarting intake.
- [ ] Simulate an uncertain Jira write. Confirm the workflow reads the target before retrying.
- [ ] Use a plugin source directory inside a parent Git repository. Confirm preflight asks for the intended consumer repository and does not stage the parent workspace.
- [ ] Run `sync-context` from a tracked monorepo package folder. Confirm generated `aidlc-docs/` lands at the Git root and writes are not blocked.
- [ ] Run `sync-context` on an untracked folder inside another Git repository. Confirm discovery is permitted with baseline `unversioned` and writes wait until the write scope or artifact home is explicit.
- [ ] Confirm an untracked Bugbot decision records `unversioned` plus a fingerprint, never the parent commit SHA.
- [ ] Confirm freshness uses a content fingerprint of examined paths, never a parent revision that does not track those files.
- [ ] Confirm Bugbot proposals keep one invariant per rule and do not include DevOps ownership or apply-gate policy.
- [ ] Confirm a Bugbot review inspects surrounding callers, contracts, and tests for an introduced defect without reporting unrelated old defects.
- [ ] Confirm approved, declined, and deferred Bugbot decisions persist under the configured artifact home by stable repository ID.
- [ ] Confirm an unchanged second sync produces no content changes.
- [ ] Confirm an over-budget generated context reports its line and approximate size rather than silently dropping required evidence.
- [ ] Confirm the repository index's `Examined` field names actual inspected paths, not a count of tracked or fingerprinted files.
- [ ] Confirm an Unknowns entry never restates a fact already asserted elsewhere in the same context documents.
- [ ] Run initial `sync-context` discovery and confirm an independent `context-reviewer` assessment is requested, or reported unavailable with a reason, before the result is called final.
- [ ] Make a small factual update with no material boundary change and confirm `sync-context` states that independent review was skipped and why deterministic validation and targeted checking were enough.
- [ ] Confirm deterministic validation reports a broken root-to-module link, a stale module source path, and a duplicate module ID rather than silently passing.
- [ ] Confirm a `context-reviewer` finding is either applied with a rerun of the affected checks, or disputed with cited source evidence; confirm at most one targeted follow-up review runs before remaining issues are reported to the user.
- [ ] Confirm `validate-change` does not commit, push, open a pull request, or merge. Delivery stays with the developer, using normal Git and pull-request tools, after the skill reports ready.
- [ ] Leave Bugbot pending. Confirm `validate-change` records it as pending and does not treat that status as passed.
- [ ] Run `create-e2e-tests` for one journey. Confirm it reuses the existing framework, or proposes a minimal setup and waits for approval before adding one. Confirm a written test is not reported as a successful run when the environment cannot execute it.
- [ ] Run `implement-change` in defect mode with a supplied reproduction. Confirm it separates reproduced behavior from a hypothesis, adds a regression test, and hands off to `validate-change` without turning the bug into a new feature.
- [ ] Change code after validation. Confirm only affected checks are rerun against the new code state.
- [ ] In a clean Cursor consumer, run `/sync-context`, then `/plan-work` for one module. Confirm plan-work reads only the selected index/module context and current source.
- [ ] In a clean Cursor consumer, run a cross-module change. Confirm retrieval expands to the relevant adjacent context and contract only.

Project onboarding (instruction behavior; not proved by the Python tests):

- [ ] Config already has a confirmed `## Project references` section. Confirm `sync-context` does not ask the onboarding questions again.
- [ ] Supply one Jira board URL. Confirm the skill resolves that board and does not ask the user to pick from every board.
- [ ] Use a board whose issue-creation project is still ambiguous. Confirm it asks one question and does not treat the board as the project.
- [ ] Disconnect Jira MCP. Confirm a user-confirmed site and project can be saved as confirmed, not verified, and local discovery continues.
- [ ] Run against a backend project with no UI. Confirm it does not ask for Figma.
- [ ] Run against a repository that already has a Git remote. Confirm it does not ask for a GitHub URL.
- [ ] Scaffold a small foundation with an optional confirmed convention. Confirm the proposal includes it, a rule approval does not install dependencies or change CI, and a later `sync-context` does not repeat onboarding or duplicate `## Project references`.
- [ ] Open a repository with current context and a confirmed `## Project references` section (so every source fingerprint is `unchanged`). Ask `sync-context` to switch to a different Jira board. Confirm it shows a config-only diff limited to `## Project references`, does not propose any rewrite of `aidlc-docs/` or `AIDLC_CONTEXT.md`, and reaches the proposal step instead of reporting "no relevant changes." Approve the change, confirm only that field is updated, and re-run `sync-context` immediately after: confirm it reports a true no-op this time, with no repeated write and no repeated question. (Unexecuted unless actually performed in Cursor; `context_sync_outcome`'s `project_reference_pending` behavior is covered by `tests/context_tools_tests.py`, but reaching the proposal step through the live skill flow is not.)

Legacy-coordinator migration (instruction behavior; not proved by the Python tests — `migration_destination_placement`, `repository_is_named_coordinator`, `classify_repository_role`, `relocate_workspace_folder_path`, `checkout_deletion_readiness`, `retirement_decision_pending`, and `migration_outcome` are unit-tested as pure functions in `tests/context_tools_tests.py`, but the agent behavior around them below is only exercised by actually running the skill in Cursor against a disposable, non-production workspace):

- [ ] Open a disposable multi-repository workspace where one repository has `Placement: adopted-coordinator` in its `.ai-dlc-config.md`. Ask `sync-context` to migrate to distributed context. Confirm it explains the current placement versus the proposed distributed destination before writing anything, and that persisted placement is not changed until that proposal is explicitly approved.
- [ ] In the same scenario, decline the placement change. Confirm `.ai-dlc-config.md` still reads `Placement: adopted-coordinator`, and the report states plainly that distributed migration was not completed, not that it partially succeeded.
- [ ] During the same migration, confirm `sync-context` surfaces the mandatory coordinator-retirement decision (options A/B/C) before it will call the migration complete, and that it does not re-ask within the same run after a "defer" answer.
- [ ] Choose retirement option C (defer). Confirm the final report uses outcome `pending` (migration cleanup still open) and does not say the migration is `complete`, and that nothing under the coordinator repository was deleted.
- [ ] Confirm a product repository whose config says `Placement: adopted-coordinator` and whose `Coordinator` field names a different repository is not classified as the coordinator and is not offered for deletion.
- [ ] Choose retirement option A (migrate and delete) for a disposable coordinator checkout with no uncommitted changes and a pushed remote. Confirm `sync-context` asks for an explicit approval naming that exact repository path before deleting anything, verifies the checkout-deletion preconditions, and only then removes the local checkout.
- [ ] Repeat with uncommitted changes present in the coordinator checkout. Confirm deletion is blocked and the specific blocking reason (uncommitted changes) is reported, rather than deleting anyway.
- [ ] Repeat with no remote configured for the coordinator checkout (so recoverability cannot be established). Confirm the checkout is retained and the report explains why deletion is pending, rather than deleting on an assumed remote.
- [ ] Attempt to approve a deletion with a target name that does not exactly match the previously approved target (for example a different repository in the same workspace). Confirm the mismatch blocks deletion rather than deleting the first plausible match.
- [ ] In a workspace whose only `.code-workspace` file lives inside the coordinator being retired, confirm `sync-context` proposes a specific new location for that file, recalculates every repository's `folders[].path`, and validates that each resolved path still points at a real repository, before removing the coordinator's own workspace reference.
- [ ] Confirm the old workspace file and its folder are not removed before the relocated replacement is confirmed in place.
- [ ] On a host with Canvas available, run a migration proposal and confirm the Canvas (not just a chat summary) shows a readable preview of at least one proposed distributed context document and the pending retirement decision. Repeat on a host without Canvas and confirm the same information appears in chat sections with file links, and that the unavailability is disclosed.
- [ ] After applying an approved migration, confirm the result view (Canvas or chat) is refreshed from the actual files written on disk — not merely restating the earlier proposal — and that it labels each file created, updated, unchanged, failed, or pending.
- [ ] Simulate one repository in a two-repository migration failing partway (for example, an unwritable module root) while the other succeeds. Confirm the report distinguishes the two outcomes per repository, does not roll back the repository that succeeded, and does not call the overall migration "complete."
- [ ] Confirm a repository whose only legacy evidence is a name match (for example containing `aidlc`) with no plugin manifest, no operating-model evidence, and no shared-methodology marker is reported as unresolved, and that nothing is deleted or retired for it on that basis alone.
- [ ] Confirm a repository classified as a shared methodology checkout is never offered retirement option A (migrate and delete) in this workflow, even if the user asks to delete it.

Multi-root workspace, sibling-context retrieval, and scaffold membership
(instruction behavior; not proved by the Python tests). The deterministic
helpers behind these scenarios -- `parse_related_repositories`,
`match_related_repositories`, `detect_repository_id_collision`,
`detect_canonical_remote_collision`, `resolve_related_context_index`,
`checkout_deletion_readiness` -- are unit-tested as pure functions in
`tests/context_tools_tests.py` against supplied inputs. That is a different
claim from the one these checklist items make. A test asserting that
`SKILL.md` references `context-retrieval.md` proves wiring exists in the
instructions; it does not prove Cursor actually followed those instructions
in a live run. Every item below is unproven until actually performed in
Cursor, and none of it should be reported as passed on the strength of the
Python test suite alone:

- [ ] Open the same multi-root `.code-workspace` in the Cursor IDE and in a local Agents Window. Confirm the same set of intended repositories is available and discoverable in both.
- [ ] In that workspace, run a context-consuming skill against one repository and confirm it actually reads the relevant sibling's context (not just this repository's own), per [context-retrieval.md](references/context-retrieval.md), "Resolving related repositories."
- [ ] Repeat the same run with one declared sibling repository not open or unavailable this session. Confirm the agent reports that repository as unavailable and continues with the rest of the task, rather than blocking or inventing its content.
- [ ] Open an unconfigured sibling repository alongside this one (no `Related repository` entry declared either way). Confirm the agent does not treat the mere presence of that sibling as an identity conflict.
- [ ] Run `sync-context` a second time with no relevant source or declaration changes. Confirm it reports a true no-op and does not rewrite `.ai-dlc-config.md`, the repository index, or any module context file on disk.
- [ ] Run `scaffold-project` for a brand-new, unrelated project in a directory that happens to sit next to an existing repository with a confirmed `Product` label. Confirm membership is not inferred from that adjacency alone, and that the proposal either states no product membership or asks one focused confirmation question instead of assuming it.
- [ ] Approve a `scaffold-project` proposal and confirm the initial context artifacts it reports (repository index, module context) reflect the files actually created in that run, not a larger planned implementation that has not been written yet.
- [ ] Review a legacy-coordinator migration proposal through the point where `sync-context` surfaces the mandatory retirement decision, and stop there without approving deletion. Confirm no checkout, stash, or worktree was removed, and that the report states the retirement decision is still pending.

Jira discovery during migration (instruction behavior; not proved by the Python tests):

- [ ] Run a distributed migration where `## Context identities` already exists and `## Project references` does not. Confirm onboarding is still considered, and identity alone is not treated as a confirmed Jira project.
- [ ] Place repeated ticket keys such as `CTY-321` in branch names, commits, or archived docs. Confirm the agent asks whether `CTY` is the Jira project and does not write it into `## Project references` before confirmation.
- [ ] Use a ticket-key pattern when the Jira site and board are unknown. Confirm neither value is inferred or written.
- [ ] Confirm the same Jira project across several repositories in one engagement. Confirm the agent asks once and reuses that confirmation, instead of asking the same question for every repository.

Product Owner planning with `plan-work` (instruction behavior; not proved by the Python tests — `validate_work_item_type`, `validate_plan_item_id`, `validate_parent_reference`, `validate_dependency_graph`, `topological_plan_order`, `plan_outcome`, `jira_mutation_authorized`, `decision_reprompt_allowed`, and `plan_validate_proposal` are unit-tested as pure functions in `tests/context_tools_tests.py`, but none of them prove the agent's Product Owner judgment below, or that the agent actually calls `plan_validate_proposal` / `context_tools.py plan-validate` during a real run; every item here is unproven until actually run in Cursor):

- [ ] Ask `/plan-work` to define a User Story with a short, incomplete request. Confirm it asks only the small number of Product Owner questions that genuinely fill a gap, not a generic questionnaire.
- [ ] Ask `/plan-work` to define the same User Story but supply complete information up front. Confirm it does not ask a redundant question the request already answered.
- [ ] Ask `/plan-work` to define an Epic. Confirm the conversation and the resulting draft stay at Epic granularity, with no premature decomposition into implementation tasks unless explicitly requested.
- [ ] Ask `/plan-work` to define a technical Task, for example configuring an API Gateway integration. Confirm the draft is not rewritten as a fake "As a developer, I want..." Story.
- [ ] Ask `/plan-work` to define a brand-new Epic or Story in a repository with no `/sync-context` output yet (no code exists for this capability). Confirm business-only planning proceeds — facts, constraints, assumptions, draft content — and that only the technical-feasibility part is marked "not yet assessed" rather than the whole draft being blocked on a `/sync-context` handoff.
- [ ] Draft a new User Story where a matching Jira Epic genuinely exists. Confirm `plan-work` recommends that Epic and states a short, evidence-based reason, rather than picking an Epic because of shared words.
- [ ] Draft a new User Story where several Epics are plausible parents. Confirm the ambiguity is surfaced to the Product Owner rather than an arbitrary choice being made silently.
- [ ] Draft a new User Story where no Jira Epic reasonably fits. Confirm `plan-work` recommends defining a new Epic and offers to help define it, without creating it.
- [ ] Draft a new Task whose recommended parent is a User Story, then prepare a Jira write for it. Confirm the agent discovers the connected site's real issue-type hierarchy and asks the Product Owner to approve the exact issue type: a Jira Subtask under that Story, or a Jira Task linked to that Story. Confirm it does not silently publish the Task as a Subtask.
- [ ] Confirm this version of `plan-work` does not run a proactive, standalone Jira search for an exact duplicate of the item being drafted. Its Jira lookup stays limited to finding a parent Epic, understanding existing planning context, and sprint-backlog discovery; a duplicate is only avoided passively, if one is already referenced by the user or turns up naturally while reading a candidate Epic's existing scope.
- [ ] Run Sprint Backlog mode against a project with some existing Jira work. Confirm the proposal distinguishes selecting existing work from creating new work, surfaces dependencies, sprint-goal coherence, and blockers, and reports capacity as unknown rather than inventing it when no capacity evidence is available.
- [ ] Disconnect Jira and run any `plan-work` mode. Confirm planning still proceeds, and the report clearly states which parts (Epic discovery, Task parent discovery, backlog discovery) were unavailable rather than silently skipping them.
- [ ] Draft a proposal with a deliberately broken structure — for example a Task declaring itself as its own parent, or two items with a duplicated dependency edge. Confirm the agent actually runs deterministic validation (`context_tools.py plan-validate` over the staged proposal, or the equivalent direct calls) before requesting independent review, and that the reported failure blocks moving to review rather than being silently skipped.
- [ ] Complete a draft and mark it ready for review. Confirm an independent `product-reviewer` assessment actually runs (or is reported unavailable with a reason) before publication approval is requested.
- [ ] Deliberately draft a weak Story: a vague outcome, an untestable acceptance criterion, and a hidden assumption. Confirm the independent review returns meaningful findings that name each problem.
- [ ] Draft a genuinely strong, complete Story. Confirm **no findings** is accepted as a valid, complete review result, and that the skill does not manufacture a finding to prove review happened.
- [ ] Have the reviewer identify a finding that would change product scope, behavior, assumptions, or intent. Confirm the main chat surfaces that finding to the Product Owner for a decision rather than silently applying it.
- [ ] Approve the local plan but withhold approval for the Jira mutation. Confirm nothing is created or changed in Jira, and the report distinguishes the approved local plan from the still-unauthorized Jira write.
- [ ] During an early planning conversation (before the Story's content is agreed), confirm `plan-work` does not interrupt with the Jira description-template question. Only once the draft is ready and the agent is preparing the Jira write payload should it read the `## Planning template` decision and, when appropriate, offer the template.
- [ ] Run `/plan-work` for the first time in an engagement with no `## Planning template` decision, through to the point of preparing a Jira write. Confirm it offers the default User Story description once at that point and lets the Product Owner accept, edit, or decline it. Run it again after an approval and confirm it does not offer the template again. Defer it instead, start a new run, and confirm it is offered again (not permanently suppressed merely because a `## Planning template` section now exists).
- [ ] Publish a User Story whose issue type has an acceptance-criteria field. Confirm the criteria are in that field and the description does not repeat them.
- [ ] Finish `/sync-context` after a run with no relevant changes. Confirm the report is a short chat reply stating that outcome, not a Canvas open or refresh for nothing new.
- [ ] Finish `/sync-context` after a real write. Confirm the closing view uses the host's Canvas capability when available, with the outcome, files, unknowns, validation, and change-set status, refreshed from the files just written. Repeat on a host that cannot open a Canvas and confirm the same sections are in chat with the unavailability stated.
- [ ] Mark a `/plan-work` draft ready for review on a host that can open a Canvas. Confirm the Canvas shows the item, acceptance criteria separate from the description, the parent recommendation, dependencies, deterministic validation result, and reviewer findings. Repeat on a host that cannot open a Canvas and confirm the chat has those same sections and says Canvas is unavailable on that host.

Context quality across repository types (instruction behavior; not proved by the Python tests — `validate_generated_context`'s mechanical checks are unit-tested in `tests/context_tools_tests.py`, but none of them judge semantic quality; every item below is unproven until actually run against a real repository of that type). For each scenario, evaluate the generated context against these nine quality dimensions, defined in [context-quality.md](.cursor/skills/sync-context/references/context-quality.md) and [architecture-discovery.md](.cursor/skills/sync-context/references/architecture-discovery.md):

1. **Accuracy** — every `verified` or `partial` claim matches the source it cites.
2. **Completeness** — the dimensions that matter for this module's actual responsibility are covered, not padded with irrelevant ones.
3. **Runtime flows** — at least one representative end-to-end flow is documented when the module has one.
4. **Honest unknowns** — a genuine gap is recorded as `unknown` with what is missing, never filled with an invented behavior.
5. **Evidence citation** — every verified or partial claim names a repository-relative path plus the relevant symbol, route, table, or configuration key.
6. **Right-sized, not gamed** — length tracks what the module actually has to say; no padding toward a target, no truncation of real detail to dodge the guideline ceiling.
7. **Coverage table correctness** — each `## Coverage` row's state is backed by what was actually inspected, not a convention guess. Coverage is a summary; material architecture belongs in `## Material architecture details`.
8. **Independent review depth** — `context-reviewer` findings (or the lack of any) are split into accuracy and completeness, and an honest unknown is not reported as a defect.
9. **Right-tiered effort** — the sync used the exploration depth its tier (initial/full, material change, or small factual update) actually calls for: not a full architecture pass for a one-line config fix, and not a one-line pass for a new integration.

- [ ] Before treating this quality redesign as proven, run `/sync-context` against at least one real REST service, one Terraform or infrastructure repo, and one small frontend or utility, and compare the result with the previous index-only or shallow output. Unit tests cannot prove this.

- [ ] **Small single-file utility or library module** (a handful of pure functions, no I/O). If it is listed as a module, it still has its own `AIDLC_CONTEXT.md`. Confirm the architecture inventory evaluates dimensions such as security, error handling, retry/idempotency, and deployment as `not applicable` with a real reason. Confirm the published Coverage table does not pad every N/A dimension — it includes an N/A row only when the absence is important or non-obvious — and that this short document still answers the quality-bar questions in context-quality.md that actually apply to it.
- [ ] **REST/HTTP API service with an external integration** (for example a payment or email provider client). Confirm entry points, the external call site, retry/idempotency behavior, and at least one runtime flow from request to external call to response are all documented with evidence, not just the route existing.
- [ ] **Event-driven or asynchronous background worker** (a queue consumer or scheduled job). Confirm the delivery guarantee the code actually relies on (at-least-once, ordering, idempotency) is stated from the code, not assumed from a comment, and that a downstream consumer of anything this worker publishes is identified.
- [ ] **Frontend or UI application module.** Confirm state management, the API calls it makes, and user-facing error handling are covered, not just component existence and routing.
- [ ] **Infrastructure-as-code or Terraform repository.** Confirm the deployment topology dimension documents what actually provisions what, with resource names and files, and that a security- or access-boundary claim is backed by the actual policy or resource definition, not a assumed convention.
- [ ] **Monorepo with several independent packages.** Confirm each meaningful package gets its own `AIDLC_CONTEXT.md` only where it has a distinct responsibility, that a shared package used by several others has its consumers listed, and that exploration was not dispatched one subagent per package by default for a monorepo small enough for one pass.
- [ ] **Multi-repository engagement (two or more Git roots).** Confirm the repository index stays `multi-repository` with a `Repository` column, a cross-repository dependency is only recorded in `integration-map.md` once actually verified, and exploration scope stayed within the repository actually being synced rather than silently expanding to a sibling.
- [ ] **Repository with stale or misleading prior context** (an existing `AIDLC_CONTEXT.md` that no longer matches current code). Confirm the refresh flags the stale claim explicitly, cites the current source that contradicts it, and does not silently keep the old prose because the fingerprint happened to still read `unchanged` for an unrelated reason.
- [ ] **Repository with a security- or payment-sensitive module** (handles authentication, authorization, or payment data). Confirm the security-and-trust-boundary dimension is not marked `not applicable` without a specific, correct reason, and that secrets or sensitive values are never copied into the generated document even as an example.
- [ ] **Repository with heavy persistence and several external integrations** (a service with its own database plus two or more third-party API clients). Confirm the data-model/persistence dimension and each integration are each covered with their own evidence, not collapsed into one generic "talks to a database and some APIs" sentence.

Regression scenarios that must never pass review or be reported as a successful sync (see [context-quality.md](.cursor/skills/sync-context/references/context-quality.md), "What good and bad look like"; the fixture at `tests/fixtures/context_review/` demonstrates three of these four seeded into one module):

- [ ] **Shallow service context.** A module with real external calls, state, or a trust boundary produces a context document that only restates framework scaffolding (a route exists, a controller exists) with no runtime flow and no failure-mode mention. Confirm `context-reviewer` reports this as a completeness finding, not a pass.
- [ ] **False completeness.** A coverage row, an `Examined` field, or prose claims a dimension is `verified` when the cited evidence does not actually back it (see `tests/fixtures/context_review`'s `false-completeness-coverage` seeded defect: a `verified` idempotency claim for code that has no idempotency guard at all). Confirm this is reported as an accuracy finding with severity blocker or major, never waved through because the prose reads confidently.
- [ ] **Length gaming.** A document is padded toward its target line count with generic, non-specific prose ("this module handles orders and ensures reliability") instead of specific, evidence-backed statements. Confirm `context-reviewer` or a human reviewer flags the padding as a completeness problem even though the document is "within budget," and confirm that the absence of a `modules:budget` validation check is never cited as proof the document is actually complete.
- [ ] **Honest unknown must beat invented behavior.** Compare two drafts of the same module, one that marks a genuinely uninspected dimension `unknown` with what is missing, and one that fills the same gap with a plausible-sounding but unverified behavior. Confirm review treats the honest `unknown` draft as acceptable (not a finding) and the invented-behavior draft as a defect, even if the invented text happens to be true — the problem is that it is unverified, not that it is wrong.

Hardening scenarios for architectural preservation, index-only representation, evidence catalog, and secret safety (instruction behavior; not proved by Python):

- [ ] **A. Behaviorful single-module service.** One service or module with an API handler, database, external integration, authentication, and retries or errors. Confirm it gets `AIDLC_CONTEXT.md`, is not treated as index-only merely because it is single-module, and that Material architecture details preserve the important discovered information.
- [ ] **B. Truly trivial repository.** A genuinely passive or documentation-only repository. Confirm index-only is an empty `## Modules` table (or equivalent explicit representation) and that validation remains compatible — no module row with a missing Context target.
- [ ] **C. Rich architecture preservation.** Have `context-architect` discover persistence, auth, retries, a feature flag, and an external integration. Confirm the final context does not reduce all of that knowledge to only one-line Coverage rows.
- [ ] **D. Secret safety.** A repository containing `.env`, environment-variable references in source, and secret-manager configuration. Confirm explorer and reviewer describe secret handling without opening or reproducing actual secret values.
- [ ] **E. Evidence catalog.** Confirm material local evidence paths used throughout Coverage, runtime flows, Material architecture details, and constraints also appear in `## Evidence and existing docs`.
- [ ] **F. Honest partial coverage.** Only part of a security flow can be inspected. Confirm the Coverage state is `partial`, not incorrectly `verified`.

- [ ] **Initial behaviorful service.** Run `/sync-context` against a small-but-behaviorful service. Confirm `context-architect` is preferred when available, rich context is generated, and runtime behavior or material architecture is preserved.
- [ ] **Reviewer unavailable.** Run in an environment without independent subagent delegation. Confirm the proposal can still be presented, independent review is explicitly reported unavailable, quality assurance is reported partial, self-review is not presented as equivalent, and persistence requires explicit approval.
- [ ] **Empty structural context.** Confirm an almost-empty `AIDLC_CONTEXT.md` cannot pass mechanical validation just because `## Identity and scope` exists. Missing `## Coverage`, `## Evidence and existing docs`, or `## Unknowns` must fail.
- [ ] **Evidence catalog missing.** Confirm a generated module context without `## Evidence and existing docs` fails structural validation.
- [ ] **Evidence exists but no local paths.** Confirm the deterministic result is `not_applicable` with `no local evidence paths to resolve`, and does not say semantic evidence validation passed.

Real-world smoke evaluation (not executed in this change; do not treat these as passed until actually run against a consumer checkout, and do not modify a consumer repository from this plugin work):

- [ ] REST/backend service — compare generated context quality against previous shallow outputs.
- [ ] Terraform/infrastructure repository — same comparison.
- [ ] Frontend or small behaviorful service — same comparison.
