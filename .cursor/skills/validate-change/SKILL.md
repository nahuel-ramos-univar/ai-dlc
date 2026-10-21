---
name: validate-change
description: Validate an approved change against acceptance criteria by dispatching an independent validator and coordinating real Bugbot results or a pending handoff.
disable-model-invocation: true
---

# Validate change

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Context retrieval
Use [context retrieval](../../../references/context-retrieval.md). Read selected module context, then current source, tests, contracts, and the reviewed diff only as needed to prepare a bounded handoff and to apply authorized fixes. Do not treat the implementer's summary as proof.

## Start condition
Start when the user runs `/validate-change`, or when `/implement-change` continues here because the user authorized that successor workflow in the same request. Every invocation, including that continuation, starts a **new** independent `validator` delegation. The chat that implemented the change coordinates; it does not evaluate its own conclusions.

This skill owns Bugbot coordination, authorized in-run fixes, and the closing report. It does not require an extra `/implement-change` slash command for otherwise authorized in-scope fixes. Independent validation is the `validator` agent's assessment, not this chat's re-check.

If the user asked for review only, or no modifications, propose targeted fixes and do not apply them.

## Independent validator
Use the host's real independent-delegation facility. Prefer the named plugin agent `validator`. If the host exposes only a general-purpose independent subagent, give it [validator.md](../../../agents/validator.md) as bounded task context and report that as general-purpose independent review, not native named-agent dispatch. Follow [skill composition](../../../references/skill-composition.md).

If independent delegation is unavailable, report **independent validation pending**. Useful checks may still run. Do not declare independent validation completed. Do not label this chat's own assessment independent.

Do not pass the whole conversation history by default. If the host cannot isolate the validator from this chat's context, say that limitation. Static contract tests in this plugin do not prove that a validator agent was invoked.

Give the validator a bounded handoff:

- objective and authorized Jira items, acceptance criteria, approved constraints with sources, and the approved refinement;
- the requirement snapshot (scope, exclusions, criteria, constraints including applicable architecture decisions, contracts, refinement) labeled as claims to re-read, not as proof;
- repositories, baseline, and current diff state, including relevant new files;
- changed dependency manifests, public contracts, migrations, security-sensitive paths, and shared files, when those paths are in the diff;
- unrelated staged, unstaged, and untracked changes to preserve;
- applicable rules, known commands, and environment restrictions;
- prior evidence, labeled as claims the validator must verify, not as results;
- after a fix: the prior evidence matrix labeled standing, invalidated, or still-open, plus the delta to recheck;
- when the change affects model or generative-system behavior, the approved evaluation contract and its sources: dataset and versions, metrics or rubric, thresholds, configuration, evaluation budget, and restrictions when those exist. Do not assume the independent validator inherits this chat's file reads.

Do not request `implementation-reviewer` for a post-code architecture review or a full code review of the diff. Approach review belongs to `/implement-change` before code. Bugbot owns the diff. The validator owns acceptance and evidence sufficiency. Do not require the validator to launch subagents.

## Workflow
1. Run [repository preflight](../../../references/repository-preflight.md). Confirm the authorized repository, actual Git root, branch, and unrelated staged, unstaged, and untracked modifications to preserve. Capture the revision, changed paths, and a [requirement snapshot](../../../references/requirement-snapshot.md). Recover applicable accepted architecture decisions into `constraints` with the implementation snapshot's binding clauses as the baseline — see [architecture-decisions.md](../../../references/architecture-decisions.md). Extract with `--repository-id` and `--root` set to the owning repository. Compare with `python3 ../../../scripts/context_tools.py snapshot-compare -` on a JSON object with `baseline` and `current`, resolved from this plugin, not from the consumer working directory. Pass that JSON on standard input or a temporary file outside the consumer repository. Compare again before close-out. After an authorized write that changes those requirements, re-read and compare. Report constraint `clause-changed`, `removed`, and `added` ids. A disappeared, replaced, or no-longer-applicable decision is that delta. An unreadable or unsupported architecture source is `not-compared`. Do not declare the work ready against outdated requirements. Incomplete recovery is `not-compared`, not unchanged.
2. Build the bounded handoff above. Then start a new independent `validator` delegation. Wait for that result, or for a documented unavailable/pending outcome, before treating the change as independently validated.
3. Coordinate Bugbot in this chat — see [evidence-and-bugbot.md](references/evidence-and-bugbot.md). Do not ask the validator to invoke Bugbot.
4. Keep findings, test results, and Bugbot status distinct. The independent validator assesses what each check actually demonstrates and classifies a failure as a regression this change introduced, a pre-existing failure with baseline evidence, an environment problem, or uncertain. Follow [verification evidence](../../../references/verification-evidence.md). Passing mocks do not prove deployed integration. Do not generate a new end-to-end suite, a new journey, or a first framework. Do not claim `create-e2e-tests` ran.
5. Invalidated evidence is not current. If material code or configuration changes after a check, drop the affected validator and Bugbot results.
6. For high-risk changes or materially stale review rules, identify the required review and approval. Dedicated governance integration is deferred. Do not widen documented review exceptions by implication.
7. Before the closing report, run `python3 ../../../scripts/context_tools.py closeout-validate -` on a JSON payload of declared criteria, independent validation, Bugbot, requirement drift, blockers, and `ready_to_deliver`. Resolve the script from this plugin, not from the consumer working directory. Write the JSON to a temporary file outside the consumer repository, or pass it on standard input. Do not create that file inside the consumer repository. The helper checks coherence of declared data; it does not prove agents or tests ran and does not replace the independent `validator` or Bugbot. Unknown statuses fail closed. Then close with separate statuses, not a single "done": implementation; independent validation and criteria; tests, regression, and environment; Bugbot; requirement drift; blockers and delivery readiness. Required independent validation still pending means this flow is not complete. Return **ready for the developer to deliver** only when policy-required evidence is passed, including independent validation and Bugbot, and requirement drift is unchanged, or an explicit applicable policy records an approved exception for a named gate. A pending, partial, or execution-error Bugbot review is not passed. A required not-compared snapshot is not unchanged. Delivery means the developer commits, pushes, opens the pull request, obtains approvals, and merges with normal Git and pull-request tools. This skill does not commit, push, open a pull request, or merge. After showing that result, offer an optional Jira comment per [work record](../../../references/work-record.md). Publication is a separate approval.

## In-run corrections
Do not apply a fix when the user asked for review only or no modifications. Propose it instead.

Before the first edit, reuse repository preflight and the same implementation protections: stay in the authorized repository, preserve unrelated staged, unstaged, and untracked changes, and do not perform unauthorized external writes or apply/deploy operations. Do not run `terraform apply`, `sam deploy`, or an equivalent apply or deploy. Do not create or update a Jira record unless the user authorizes that write.

Apply a targeted fix in this run only when all of these hold:

- the user did not ask for review only or no modifications;
- the fix stays inside the authorized functional scope;
- evidence justifies it;
- it needs no new business decision and no unauthorized external operation.

Shared files may change when the authorized behavior requires it. Check affected contracts, consumers, and tests. Do not treat file paths as belonging to one Story. Do not require another slash command for those authorized in-scope fixes.

If the same failing check returns without material progress toward the cause, stop and report the diagnosis. Do not keep retrying. Do not change tests so they pass by dropping the expected behavior. Do not delete tests, add skips, weaken assertions, or update snapshots only to get a green result. Do not rerun the whole suite without a concrete reason.

If the fix needs a new business decision, hand off to `/plan-work`. If the approved technical design no longer applies, hand off to `/refine-story`. Do not claim those slash commands ran.

After an applied fix, invalidate affected validator and Bugbot evidence. Start a **new** independent `validator` delegation for the delta and the affected tests, with a bounded handoff that includes the prior evidence matrix and those states. The new agent rechecks the delta. The closing report must still cover every acceptance criterion: keep standing evidence, drop invalidated evidence, add delta evidence, and carry open findings. Do not treat a delta-only result as complete validation. Do not rerun the whole suite without a concrete reason. Renew Bugbot for the new code state when the diff changed. Do not treat the earlier assessment as current.

## Bugbot
`validate-change` owns Bugbot. For a code change in this flow, attempt the real supported Bugbot invocation without asking the user to request it again. Use a supported host facility to run the official review-bugbot skill or the host `bugbot` subagent. If that facility is not available, ask the developer to run `/review-bugbot` and mark Bugbot pending. Never invent findings. Never claim it ran without a real result. Static contract tests in this plugin do not prove that Bugbot was invoked.

Do not declare delivery ready while Bugbot is pending, partial, or an execution error, unless an explicit applicable policy permits an approved exception.

Record the repository, the reviewed diff and working-tree state, whether the run finished, whether the review was complete or partial, the findings, and later edits that invalidate that evidence.

Distinguish a code finding from an execution error and from a partial review. An execution error is not a code finding. A partial review is not passed. A result of no bugs is not evidence that acceptance criteria passed. A pending review is not passed.

Use **not-applicable** only with a concrete reason, for example that this run changed no code. Do not mark a code change not-applicable because the user did not mention Bugbot.

Observe remote Bugbot only when it appears in actual configured checks; do not assume it is configured. This skill does not merge.

## Output
Return distinct sections for implementation, independent validation and criteria (verified, failed, pending, or not-verifiable), tests/regression and environment, Bugbot with the code state reviewed, and blockers or delivery readiness. Required independent validation pending is not a completed flow.

Read [evidence-and-bugbot.md](references/evidence-and-bugbot.md), [verification evidence](../../../references/verification-evidence.md), [requirement snapshot](../../../references/requirement-snapshot.md), [work record](../../../references/work-record.md), [criterion identifiers](../../../references/criterion-ids.md), [architecture decisions](../../../references/architecture-decisions.md), [repository preflight](../../../references/repository-preflight.md), [skill composition](../../../references/skill-composition.md), [approval-contract.md](../../../references/approval-contract.md), and [validator.md](../../../agents/validator.md). Load [end-to-end environment](../../../references/e2e-environment.md) only when an existing end-to-end check is in play. Load [model evaluation](../../../references/model-evaluation.md) only when the change affects model or generative-system behavior.
