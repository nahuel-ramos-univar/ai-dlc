---
name: deliver-change
description: Safely prepare or reuse branches and perform authorized Git, pull-request, check, and merge actions without implying deployment.
disable-model-invocation: true
---

# Deliver change

## Capability detection
Local Git supports repository inspection, diff, branch, commit, and push. It does not create provider pull requests, inspect provider checks or approvals, or merge a provider pull request.

Before a provider operation, verify the target host, repository, authentication, and supported provider tool. For GitHub, use an already installed and authenticated `gh` CLI when available. Do not require GitHub MCP or assume another provider is supported.

## Workflow
1. Run repository preflight. Confirm the requested working directory, actual Git root, intended remote, branch, target branch, and unrelated staged, unstaged, and untracked files.
2. Preserve the implementation workspace and unrelated local modifications. Do not stash, reset, rebase, discard work, initialize Git, stage a parent workspace, or run `git add .` without separate approval.
3. If a Jira key is present and Jira MCP is available, read it to verify delivery status matches the requested action.
4. Separate the requested action:
   - **Prepare:** commit, push, or open a draft PR. A draft PR may proceed with approval before complete validation, but must list outstanding checks and cannot claim readiness to merge.
   - **Ready for review:** validation evidence is current for the candidate content and required review/check status is known.
   - **Merge:** all repository-required checks and approvals have passed for the exact candidate change.
5. Before merge, read the current `validate-change` outcome. Reconstruct or request missing evidence. Confirm it covers the candidate content, acceptance criteria, integration baseline, and relevant uncommitted changes.
6. Revalidate affected evidence when code, configuration, acceptance criteria, or relevant integration content materially changes. A commit SHA change alone does not prove reviewed content changed or became stale; assess the diff and baseline.
7. Block merge when required evidence is missing, failed, blocked, or stale. Allow an exception only when repository policy permits it and the appropriate human explicitly approves the identified exception. User approval never bypasses branch protection.
8. Execute only authorized actions supported by the verified local Git or provider capability. If provider access is unavailable, complete supported actions, give a manual handoff, and mark PR, checks, or merge pending.
9. Inspect actual provider checks and approvals after each authorized provider action. Never report a local Git merge as a successfully merged provider PR.

## Boundaries
Do not commit, push, open a pull request, merge, publish, deploy, or alter production state without scoped approval. A provider merge proves only repository integration, not production deployment or business impact.

## Output
Return completed authorized actions, current branch and remote state, provider capability status, the validation outcome consumed, checks and approvals observed, and outstanding delivery actions.

Read [safe-delivery.md](references/safe-delivery.md), [repository preflight](../../../references/repository-preflight.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
