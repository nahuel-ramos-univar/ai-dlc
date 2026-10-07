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
Require approved scope and acceptance criteria. Run repository preflight, then read the Story, or the refined technical Task or Subtask, through Jira MCP when available. When the input is a technical item, read its identified business source and that source's acceptance criteria. The Jira parent is not assumed to be that source: a Task may sit under an Epic while the business source is a linked Story. A Subtask's parent is the Story, Task, or Bug it sits under. Do not treat every dependency link as the business source, and the technical item supplements them, it does not replace them. Also read relevant dependencies. Revalidate the item against affected code, contracts, dependencies, and local modifications immediately before edits. If the business source, a dependency, or the baseline materially changed since refinement, or if material drift needs refinement, provide the user with a `/refine-story` handoff; do not claim it ran automatically.

## Workflow
1. Confirm the requested working directory, actual Git root, intended remote and branch, baseline, and unrelated staged, unstaged, and untracked modifications to preserve.
2. Assess semantic risk: behavior, dependency impact, security, data integrity, reversibility, novelty, and uncertainty.
3. Use a brief, ordered plan only when multiple files, a contract change, or a migration requires coordination.
4. The main chat may delegate bounded frontend, backend, infrastructure, integration, or test work to the `implementer` agent only when separate context or parallel work is useful. Give objective, boundaries, story, criteria, baseline, paths, dependencies, constraints, expected output, validation responsibility, and stop conditions.
5. Make minimal scoped changes and add the narrowest tests that prove the requested behavior. Avoid conflicting concurrent edits.
6. For standard or deep semantic risk, request an independent `implementation-reviewer` assessment through a supported agent facility before final verification. Scope it to relevant frontend accessibility, backend/data integrity, infrastructure/permissions, contract/integration, QA/E2E, or architecture concerns.
7. If independent delegation is unavailable, disclose it and continue only under the applicable repository policy. Do not call an implementation self-review independent.
8. Treat public contracts, migrations, infrastructure, and E2E support as explicit scope. Do not add them by implication.
9. Give the user a `/validate-change` handoff with changed paths, commands, baseline, reviewer findings, and known gaps. Do not claim the slash command ran automatically.

## Defect mode
Use this mode for a bug report, a supplied reproduction, or an existing ticket. Stay inside the authorized repository and a non-production environment.

1. Try to reproduce the reported behavior. Say what you reproduced and what is still a hypothesis. Do not invent a confirmed root cause or a successful reproduction.
2. Separate a defect from intended behavior, a configuration problem, and a new feature request. Return a feature request to `/plan-work`.
3. State the expected outcome. Ask when that outcome is still unclear.
4. Make a scoped fix and add a regression test that fails before the fix and passes after it, when the project can run that test.
5. Hand off to `/validate-change` with the reproduction, the fix, and the test result. Do not claim that command ran.
6. Do not create or update a Jira record unless the user authorizes that write.

## Boundaries
Infrastructure, IAM, security, data migration, and production-affecting changes require explicit review and scoped approval before state-changing operations. Dedicated governance integration is deferred. Use local Git for read-only baseline inspection. Do not commit, push, open a PR, or deploy.

## Output
Return changed behavior, files, baseline, tests added or updated, known risks, and validation handoff.

Read [risk-and-specialists.md](references/risk-and-specialists.md), [repository preflight](../../../references/repository-preflight.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
