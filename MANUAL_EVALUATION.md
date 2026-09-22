# Manual evaluation checklist

These checks require a clean consumer workspace or authenticated host integration. They are not covered by the structural test.

- [ ] Install the plugin into a clean consumer and confirm all eight skills and six agents are discovered.
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
