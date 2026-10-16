---
name: validate-change
description: Validate an approved change against acceptance criteria using tests, review, contracts, security checks, and real Bugbot results or a pending handoff.
disable-model-invocation: true
---

# Validate change

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Context retrieval
Use [context retrieval](../../../references/context-retrieval.md). Read selected module context, then current source, tests, contracts, and reviewed diff before making validation claims.

## Start condition
Start when the user runs `/validate-change`, or when `/implement-change` continues here because the user authorized that successor workflow in the same request. Use the changed paths, baseline, acceptance criteria, executed tests, and known gaps from implementation.

This skill owns Bugbot coordination and the final evidence map. It does not require an extra `/implement-change` slash command for otherwise authorized in-scope fixes.

If the user asked for review only, or no modifications, propose targeted fixes and do not apply them.

## Workflow
1. Run [repository preflight](../../../references/repository-preflight.md). Confirm the authorized repository, actual Git root, branch, and unrelated staged, unstaged, and untracked modifications to preserve. Capture the revision, changed paths, and acceptance criteria under review.
2. Map every acceptance criterion to a code inspection and the narrowest applicable unit, integration, end-to-end, manual, or unavailable check. Assess what each check actually demonstrates; do not only rerun the author's suite. Follow [verification evidence](../../../references/verification-evidence.md). Run an end-to-end test only when one already exists and is relevant. Load [end-to-end environment](../../../references/e2e-environment.md) before classifying or running that check. Do not generate a new end-to-end suite, a new journey, or a first framework. Do not claim `create-e2e-tests` ran.
3. Run only relevant checks. Report command, revision, result, duration when known, and reason for skipped or unavailable checks. Classify a failure as a regression this change introduced, a pre-existing failure with baseline evidence, an environment problem, or uncertain. Do not call a failure pre-existing without evidence.
4. Inspect dependency manifests, public contracts, migrations, and security-sensitive code when changed. When a shared file changed, check affected contracts, consumers, and tests.
5. The main chat may request an independent `validator` assessment when a second evidence pass reduces uncertainty. Do not request `implementation-reviewer` for a post-code architecture review or a full code review of the diff. Approach review belongs to `/implement-change` before code. Bugbot owns the diff.
6. Coordinate Bugbot as part of this workflow — see [evidence-and-bugbot.md](references/evidence-and-bugbot.md).
7. Invalidate affected evidence if material code or configuration changes after a check. Rerun only the checks that the change invalidates.
8. For high-risk changes or materially stale review rules, identify the required review and approval. Dedicated governance integration is deferred.
9. Close with distinct statuses, not a single "done": new behavior verified and what the checks exercised, regression executed and its scope, pre-existing failures, checks that failed or did not run, Bugbot status and the code state reviewed, limitations that affect delivery, and whether the change is ready for the developer to deliver. Passing mocks do not prove deployed integration. Return **ready for the developer to deliver** only when policy-required evidence is passed, including Bugbot, or an explicit applicable policy records an approved exception. A pending, partial, or execution-error Bugbot review is not passed. Delivery means the developer commits, pushes, opens the pull request, obtains approvals, and merges with normal Git and pull-request tools. This skill does not commit, push, open a pull request, or merge.

## In-run corrections
Do not apply a fix when the user asked for review only or no modifications. Propose it instead.

Before the first edit, reuse repository preflight and the same implementation protections: stay in the authorized repository, preserve unrelated staged, unstaged, and untracked changes, and do not perform unauthorized external writes or apply/deploy operations. Do not run `terraform apply`, `sam deploy`, or an equivalent apply or deploy. Do not create or update a Jira record unless the user authorizes that write.

Apply a targeted fix in this run only when all of these hold:

- the user did not ask for review only or no modifications;
- the fix stays inside the authorized functional scope;
- evidence justifies it;
- it needs no new business decision and no unauthorized external operation.

Shared files may change when the authorized behavior requires it. Check affected contracts, consumers, and tests. Do not treat file paths as belonging to one Story. Do not require another slash command for those authorized in-scope fixes.

If the same failing check returns without material progress toward the cause, stop and report the diagnosis. Do not keep retrying. Do not change tests so they pass by dropping the expected behavior. Do not delete tests, add skips, weaken assertions, or update snapshots only to get a green result.

If the fix needs a new business decision, hand off to `/plan-work`. If the approved technical design no longer applies, hand off to `/refine-story`. Do not claim those slash commands ran.

After an applied fix, invalidate affected test and Bugbot evidence and rerun only the checks that the change invalidates, including Bugbot for the new code state.

## Bugbot
`validate-change` owns Bugbot. For a code change in this flow, attempt the real supported Bugbot invocation without asking the user to request it again. Use a supported host facility to run the official review-bugbot skill or the host `bugbot` subagent. If that facility is not available, ask the developer to run `/review-bugbot` and mark Bugbot pending. Never invent findings. Never claim it ran without a real result. Static contract tests in this plugin do not prove that Bugbot was invoked.

Do not declare delivery ready while Bugbot is pending, partial, or an execution error, unless an explicit applicable policy permits an approved exception.

Record the repository, the reviewed diff and working-tree state, whether the run finished, whether the review was complete or partial, the findings, and later edits that invalidate that evidence.

Distinguish a code finding from an execution error and from a partial review. An execution error is not a code finding. A partial review is not passed. A result of no bugs is not evidence that acceptance criteria passed. A pending review is not passed.

Use **not-applicable** only with a concrete reason, for example that this run changed no code. Do not mark a code change not-applicable because the user did not mention Bugbot.

Observe remote Bugbot only when it appears in actual configured checks; do not assume it is configured. This skill does not merge.

## Output
Return a concise acceptance-evidence matrix that says what each check proved, reviewed Git state, failures classified as regression, pre-existing, environment, or uncertain, skipped checks, remaining risks, limitations, and explicit Bugbot status with the code state it actually reviewed.

Read [evidence-and-bugbot.md](references/evidence-and-bugbot.md), [verification evidence](../../../references/verification-evidence.md), [repository preflight](../../../references/repository-preflight.md), and [skill composition](../../../references/skill-composition.md). Load [end-to-end environment](../../../references/e2e-environment.md) only when an existing end-to-end check is in play.
