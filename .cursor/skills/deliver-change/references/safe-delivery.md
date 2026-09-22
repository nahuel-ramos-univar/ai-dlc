# Safe delivery

An authorization must identify the permitted action and target: commit contents, remote, pull request base/head, or merge target. Re-check repository scope, branch, target remote, and worktree state immediately before execution.

Local Git supports local repository operations and push. Provider operations require a verified integration. For GitHub, check whether authenticated `gh` is available before creating or inspecting a pull request. Do not infer provider support from a Git remote alone.

A draft PR can be created with explicit approval before validation completes. It must list outstanding checks and validation status, and it is not ready to merge.

Before merge, consume the current `validate-change` evidence. It must cover the candidate content, relevant uncommitted changes, acceptance criteria, and integration baseline. Re-run only affected checks after a material content, configuration, or acceptance-criteria change. Do not treat a changed commit SHA alone as proof that validation is stale or current.

If checks, approvals, provider access, or evidence are unavailable, report the condition and provide a manual handoff. Do not replace required checks with a local assertion, merge around branch protections, or call a local Git merge a merged provider PR. Exceptions require repository-policy support and explicit human approval of the identified exception.

Never state that deployment occurred unless it was separately authorized and evidenced.
