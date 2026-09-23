# Manual evaluation checklist

These checks require a clean consumer workspace or authenticated host integration. They are not covered by the structural test.

- [ ] Install the plugin into a clean consumer and confirm all eight skills and six agents are discovered.
- [ ] Run `sync-context` against a small single-module repository. Confirm it creates one concise repository index and no manufactured `AIDLC_CONTEXT.md`.
- [ ] Run `sync-context` against a monorepo. Confirm it creates `<module-root>/AIDLC_CONTEXT.md` only for meaningful architectural modules.
- [ ] Run `sync-context` against two accessible Git roots. Confirm the short index distinguishes both roots, links to their colocated contexts, and adds `integration-map.md` only after a verified cross-repository dependency.
- [ ] Use a non-writable module root. Confirm the index links to `aidlc-docs/context/<repo-id>/<module-id>.md` fallback instead of writing in the source tree.
- [ ] Re-run `sync-context` without relevant source changes. Confirm it preserves human content and does not rewrite unaffected module context.
- [ ] Change one module after context generation. Confirm only that module is refreshed and stale evidence is flagged.
- [ ] Confirm context retrieval reads the short index first, then selected colocated `AIDLC_CONTEXT.md` or its fallback, then current source and tests for implementation or review.
- [ ] Decline the proposed BUGBOT files. Confirm `.ai-dlc-config.md` records `## Context decisions` and later sync runs do not prompt again.
- [ ] Approve a proposed BUGBOT file in a disposable repository. Confirm only the previewed file is written and existing BUGBOT content is preserved.
- [ ] Confirm BUGBOT guidance is not reported as Bugbot execution.
- [ ] Run a single Story intake. Confirm the draft becomes ready for review, product review is requested, and publication needs an exact approved change set.
- [ ] Run an Epic intake. Confirm overlapping Stories and missing outcome coverage are reported.
- [ ] Run a backlog proposal. Confirm dependencies are identified without inventing sprint capacity.
- [ ] Update an existing Story. Confirm unrelated fields are preserved in the proposed diff.
- [ ] Confirm duplicate Jira search runs before product review. Disconnect Jira and confirm the result says search unavailable.
- [ ] Disconnect Jira during a prepared operation. Reconnect and confirm the draft resumes without restarting intake.
- [ ] Simulate an uncertain Jira write. Confirm the workflow reads the target before retrying.
- [ ] Use a plugin source directory inside a parent Git repository. Confirm preflight asks for the intended consumer repository and does not stage the parent workspace.
- [ ] Run delivery without an authenticated provider CLI. Confirm PR, check, and merge actions are pending with a manual handoff.
- [ ] Open a draft PR before validation completes. Confirm outstanding checks are visible and it is not marked ready to merge.
- [ ] Attempt a merge with missing or stale evidence. Confirm the workflow blocks merge.
- [ ] Leave Bugbot pending. Confirm `validate-change` records it as pending and `deliver-change` consumes, rather than coordinates, that status.
- [ ] Change code after validation. Confirm only affected checks are rerun against the new code state.
