# Manual evaluation checklist

- [ ] Merge a `feat:` or `fix:` commit to `main` and confirm `plugin.json`, `CHANGELOG.md`, tag `vX.Y.Z`, and a GitHub Release update together.

- [ ] Install the plugin into a clean consumer and confirm all seven skills and six agents are discovered.
- [ ] Run `scaffold-project` in an empty authorized destination. Confirm it presents an approved minimal proposal before writing, preserves existing files, writes a concise README, and reports actual validation results.
- [ ] Run `scaffold-project` in an existing application. Confirm it proposes a bounded addition or stops for clarification without overwriting the application.
- [ ] Run `sync-context` against a small single-module repository. Confirm it creates one concise repository index and no manufactured `AIDLC_CONTEXT.md`.
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
- [ ] Confirm duplicate Jira search runs before product review. Disconnect Jira and confirm the result says search unavailable.
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

Jira discovery during migration (instruction behavior; not proved by the Python tests):

- [ ] Run a distributed migration where `## Context identities` already exists and `## Project references` does not. Confirm onboarding is still considered, and identity alone is not treated as a confirmed Jira project.
- [ ] Place repeated ticket keys such as `CTY-321` in branch names, commits, or archived docs. Confirm the agent asks whether `CTY` is the Jira project and does not write it into `## Project references` before confirmation.
- [ ] Use a ticket-key pattern when the Jira site and board are unknown. Confirm neither value is inferred or written.
- [ ] Confirm the same Jira project across several repositories in one engagement. Confirm the agent asks once and reuses that confirmation, instead of asking the same question for every repository.
