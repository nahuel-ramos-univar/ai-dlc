---
name: implement-change
description: Implement an approved application, frontend, backend, infrastructure, integration, or E2E change with scoped analysis and baseline revalidation.
disable-model-invocation: true
---

# Implement change

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Context retrieval
Use [context retrieval](../../../references/context-retrieval.md). Read selected module context, then current source, tests, and contracts before editing or delegating.

## Prerequisites
Require approved scope and acceptance criteria. Run repository preflight, then read the Story, or the refined technical Task or Subtask, through Jira MCP when available. When the input is a technical item, read its identified business source and that source's acceptance criteria. The Jira parent is not assumed to be that source: a Task may sit under an Epic while the business source is a linked Story. A Subtask's parent is the Story, Task, or Bug it sits under. Do not treat every dependency link as the business source, and the technical item supplements them, it does not replace them. Read the technical acceptance criteria from the issue's acceptance-criteria field, or from the description section named Technical acceptance criteria when that is where they were stored. Also read relevant dependencies. Revalidate the item against affected code, contracts, dependencies, and local modifications immediately before edits. If the business source, a dependency, or the baseline materially changed since refinement, or if material drift needs refinement, provide the user with a `/refine-story` handoff; do not claim it ran automatically.

## Input and scope
Accept a Jira key or URL, plus the repository to change. Resolve the authorized functional scope from the user's instruction and the items that already exist. Do not implement an Epic by implication.

If the instruction already names the items — for example every development Subtask under a Story — do not ask again. Identify development work versus QA work from each item's approved deliverable and its own content. Use the issue type or a label when one exists and agrees with that content. Do not depend on refine-story mode metadata that may not be persisted on the issue. Ask only when development work and QA work cannot be distinguished.

A QA item is not included in an implementation run unless the instruction names it. When the named item is QA work, distinguish writing tests (this skill) from running validation (`/validate-change`).

Inspect stack, modules, related repositories, current code, tests, and policies before asking. Separate verified facts from open decisions. Do not re-ask a decision `refine-story` already resolved.

## Workflow
1. Confirm the requested working directory, actual Git root, intended remote and branch, baseline, and unrelated staged, unstaged, and untracked modifications to preserve.
2. Assess semantic risk: behavior, dependency impact, security, data integrity, reversibility, novelty, and uncertainty. See [risk-and-specialists.md](references/risk-and-specialists.md).
3. Present a brief approach: what will be reused, what will change, affected contracts, and the tests that will prove the result. Ask only for a material alternative, an irreversible decision, or an ambiguous scope.
4. Request an independent `implementation-reviewer` assessment in **approach review mode**, before writing code, only when a material new decision, uncertainty, or a relevant change against the already-reviewed design appears — for example authentication, a shared contract, a data migration, or identity and access isolation. Presence of Terraform or IAM (identity and access management) files is not that trigger. If the approved refinement still covers the approach, skip this review and say why. When that review is required, wait for its result. Resolve blocking findings and material pending decisions before editing the affected scope. Independent work may continue only when it does not depend on that decision. The reviewer does not review a later diff; Bugbot owns that, in `/validate-change`.
5. If independent delegation is unavailable when that review is required, disclose it and leave the affected scope pending unless an explicit applicable policy permits an exception. Do not call an implementation self-review independent. Do not edit the gated scope while that review is pending.
6. The main chat may delegate bounded frontend, backend, infrastructure, integration, or test work to the `implementer` agent only when separate context or parallel work is useful. Give objective, boundaries, story, criteria, baseline, paths, dependencies, constraints, expected output, validation responsibility, and stop conditions.
7. Make minimal scoped changes and add the narrowest tests that prove the requested behavior. Shared files may change when the authorized behavior requires it; check affected contracts, consumers, and tests. Do not treat file paths as belonging to one Story. Avoid conflicting concurrent edits. Writing Terraform or similar files is not approval to apply them.
8. Treat public contracts, migrations, infrastructure, and E2E support as explicit scope. Do not add them by implication.
9. After implementation finishes, report changed behavior, files, baseline, tests, known risks, and the approach-review result or skip reason. If the user authorized continuing into validation in the same request, load and follow [validate-change](../validate-change/SKILL.md) and report the seam. Otherwise give a `/validate-change` handoff. Do not claim that slash command ran when the user did not authorize the successor workflow.

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
Return changed behavior, files, baseline, tests added or updated, known risks, the approach-review outcome or skip reason, and either a validation continuation or a validation handoff.

Read [risk-and-specialists.md](references/risk-and-specialists.md), [repository preflight](../../../references/repository-preflight.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
