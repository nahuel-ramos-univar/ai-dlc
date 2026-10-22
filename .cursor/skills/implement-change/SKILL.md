---
name: implement-change
description: Implement an approved application, frontend, backend, infrastructure, or integration change with scoped analysis and baseline revalidation. May update existing end-to-end tests when the authorized behavior requires it.
disable-model-invocation: true
---

# Implement change

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Context retrieval
Use [context retrieval](../../../references/context-retrieval.md). Read selected module context, then current source, tests, and contracts before editing or delegating.

## Prerequisites
Require approved scope and acceptance criteria. Run repository preflight, then read the Story, or the refined technical Task or Subtask, through Jira MCP when available. When the input is a technical item, read its identified business source and that source's acceptance criteria. The Jira parent is not assumed to be that source: a Task may sit under an Epic while the business source is a linked Story. A Subtask's parent is the Story, Task, or Bug it sits under. Do not treat every dependency link as the business source, and the technical item supplements them, it does not replace them. Read the technical acceptance criteria from the issue's acceptance-criteria field, or from the description section named Technical acceptance criteria when that is where they were stored. Recover approved constraints even when they sit outside that heading; keep each source. Recover applicable accepted architecture decisions into that same `constraints` list — see [architecture-decisions.md](../../../references/architecture-decisions.md). Extract with `--repository-id` and `--root` set to the owning repository. Copy each binding clause exactly. Qualify each decision id with the persisted repository ID. If that source cannot be read, is unsupported, or its navigation link is missing, set `source_complete` to `false`. Do not treat a material deviation as an accepted decision. Also read relevant dependencies. Capture a [requirement snapshot](../../../references/requirement-snapshot.md) at the start. Revalidate the item against affected code, contracts, dependencies, and local modifications immediately before edits. Compare the snapshot again before close-out. If the business source, a dependency, or the baseline materially changed since refinement, or if material drift needs refinement, provide the user with a `/refine-story` handoff; do not claim it ran automatically. Do not declare the implementation current against outdated requirements.

## Input and scope
Accept a Jira key or URL, plus the repository to change. Resolve the authorized functional scope from the user's instruction and the items that already exist. Do not implement an Epic by implication.

If the instruction already names the items — for example every development Subtask under a Story — do not ask again. Identify development work versus QA work from each item's approved deliverable and its own content. Use the issue type or a label when one exists and agrees with that content. Do not depend on refine-story mode metadata that may not be persisted on the issue. Ask only when development work and QA work cannot be distinguished.

A QA item is not included in an implementation run unless the instruction names it. When the named item is QA work, distinguish unit or integration tests (this skill) from new end-to-end authorship (`/create-e2e-tests`, a handoff only) from running validation (`/validate-change`). Naming `/create-e2e-tests` does not execute it.

Inspect stack, modules, related repositories, current code, tests, and policies before asking. Separate verified facts from open decisions. Do not re-ask a decision `refine-story` already resolved.

## Workflow
1. Confirm the requested working directory, actual Git root, intended remote and branch, baseline, and unrelated staged, unstaged, and untracked modifications to preserve. Before editing, follow the baseline in [verification evidence](../../../references/verification-evidence.md): discover existing relevant tests and commands, run them when they can run on this host, and record observed failures with the code state they belong to. If a relevant check is or includes an end-to-end run, load and apply [end-to-end environment](../../../references/e2e-environment.md) before executing it, including this baseline. Inspect the command and runner configuration for the target environment; a locally invoked runner can still reach a remote URL. Reuse an authorization already given in this session. If a baseline could not be obtained, say that limitation. Do not reset, clean, or move unrelated changes to obtain a baseline.
2. Assess semantic risk: behavior, dependency impact, security, data integrity, reversibility, novelty, and uncertainty. See [risk-and-specialists.md](references/risk-and-specialists.md).
3. Present a brief approach: what will be reused, what will change, affected behavior and contracts, runtime and commands found, required dependencies and configuration, which components the planned checks exercise versus replace, what can be verified in the available environment, and what needs a different environment or an unavailable dependency. Follow [verification evidence](../../../references/verification-evidence.md). Ask only for a material alternative, an irreversible decision, or an ambiguous scope.
4. Request an independent `implementation-reviewer` assessment in **approach review mode**, before writing code, only when a material new decision, uncertainty, or a relevant change against the already-reviewed design appears — for example authentication, a shared contract, a data migration, or identity and access isolation. Presence of Terraform or IAM (identity and access management) files is not that trigger. If the approved refinement still covers the approach, skip this review and say why. When that review is required, give the reviewer a bounded handoff: pass reason, the approved refinement, the proposed approach, and the delta against that refinement. Do not send the full conversation. Then wait for its result. Resolve blocking findings and material pending decisions before editing the affected scope. Independent work may continue only when it does not depend on that decision. The reviewer does not review a later diff; Bugbot owns that, in `/validate-change`.
5. If independent delegation is unavailable when that review is required, disclose it and leave the affected scope pending unless an explicit applicable policy permits an exception. Do not call an implementation self-review independent. Do not edit the gated scope while that review is pending.
6. The main chat may delegate bounded frontend, backend, infrastructure, integration, or test work to the `implementer` agent only when separate context or parallel work is useful. Give objective, boundaries, story, criteria, baseline, paths, dependencies, constraints, expected output, validation responsibility, and stop conditions.
7. Make minimal scoped changes and add the narrowest tests that prove the requested behavior. Follow [verification evidence](../../../references/verification-evidence.md) for characterization of unprotected existing behavior, mock boundaries, external-failure checks, required dependencies, a separate QA item, and after-change regression. After the change, run the new or updated tests and the affected existing regression, including consumers and shared contracts the change can affect. Run the full suite when that is reasonable; use a justified subset when it is expensive, not pertinent, or needs an unavailable environment. Do not call a failure pre-existing without evidence. Fix regressions introduced inside the authorized scope. Do not delete tests, add skips, weaken assertions, or update snapshots only to get a green result. An existing end-to-end spec may be updated when the authorized behavior requires it, even if the user did not name those files. Do not add a new journey, a first suite, or a framework. Do not weaken end-to-end assertions. Load and apply [end-to-end environment](../../../references/e2e-environment.md) before modifying or executing existing end-to-end coverage, including this regression. New end-to-end authorship is a `/create-e2e-tests` handoff; do not claim that skill ran. Shared files may change when the authorized behavior requires it; check affected contracts, consumers, and tests. Do not treat file paths as belonging to one Story. Avoid conflicting concurrent edits. Writing Terraform or similar files is not approval to apply them.
8. Treat public contracts, migrations, and infrastructure as explicit scope. Do not add them by implication. Updating an existing end-to-end spec for authorized behavior is not a new journey and does not require the user to name those files.
9. After implementation finishes, report changed behavior, files, baseline, tests, known risks, the approach-review result or skip reason, and the implementation [verification close-out](../../../references/verification-evidence.md). That report does not own independent validation or Bugbot. Do not invent those statuses. Do not start `/validate-change` or Bugbot unless the user authorized continuing into validation. If the user authorized continuing into validation in the same request, load and follow [validate-change](../validate-change/SKILL.md) and report the seam. That continuation still starts a new independent `validator`; this chat does not evaluate its own conclusions. Otherwise give a `/validate-change` handoff. Do not claim that slash command ran when the user did not authorize the successor workflow. An implementation-only close-out is not delivery-ready validation.

## Defect mode
Use this mode for a bug report, a supplied reproduction, or an existing ticket. Stay inside the authorized repository and a non-production environment.

1. Try to reproduce the reported behavior. Say what you reproduced and what is still a hypothesis. Do not invent a confirmed root cause or a successful reproduction.
2. Separate a defect from intended behavior, a configuration problem, and a new feature request. Return a feature request to `/plan-work`.
3. State the expected outcome. Ask when that outcome is still unclear.
4. Make a scoped fix and add a regression test that fails before the fix and passes after it, when the project can run that test.
5. After the fix, follow the same validation continuation rule as step 9 of the main workflow.
6. Do not create or update a Jira record unless the user authorizes that write.

## Boundaries
Infrastructure, IAM, security, data migration, and production-affecting changes require explicit review and scoped approval before state-changing operations. Dedicated governance integration is deferred. Use local Git for read-only baseline inspection. Do not commit, push, open a PR, or deploy. Do not run `terraform apply`, `sam deploy`, or an equivalent apply or deploy.

## Output
Return changed behavior, files, baseline, tests added or updated, known risks, the approach-review outcome or skip reason, the implementation verification close-out, and either a validation continuation or a validation handoff. Do not invent independent-validation or Bugbot status on an implementation-only run.

## Reference loading
The links below are an allowlist. Do not open every file at the start of the run.

- [repository preflight](../../../references/repository-preflight.md) during start-of-run confirmation.
- [requirement snapshot](../../../references/requirement-snapshot.md) when capturing or comparing requirements.
- [risk-and-specialists.md](references/risk-and-specialists.md) when assessing semantic risk and whether approach review applies.
- [verification evidence](../../../references/verification-evidence.md) for baseline, checks, and close-out.
- [architecture decisions](../../../references/architecture-decisions.md) when recovering constraints.
- [Jira integration](../../../references/jira-integration.md) when reading Jira.
- [skill composition](../../../references/skill-composition.md) when dispatching, continuing into validate-change, or handing off.
- [work record](../../../references/work-record.md) and [criterion identifiers](../../../references/criterion-ids.md) when those records are in play.
- [end-to-end environment](../../../references/e2e-environment.md) before modifying or executing existing end-to-end coverage, including baseline and regression, not only when a spec changes.
- [model evaluation](../../../references/model-evaluation.md) only when the change affects model or generative-system behavior.
