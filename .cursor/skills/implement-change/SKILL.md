---
name: implement-change
description: Implement an approved application, frontend, backend, infrastructure, integration, or E2E change with scoped analysis and baseline revalidation.
disable-model-invocation: true
---

# Implement change

## Prerequisites
Require approved scope and acceptance criteria. Run repository preflight, then read the Story through Jira MCP when available. Revalidate it against affected code, contracts, dependencies, and local modifications immediately before edits. If material drift needs refinement, provide the user with a `/refine-story` handoff; do not claim it ran automatically.

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

## Boundaries
Infrastructure, IAM, security, data migration, and production-affecting changes require `check-governance` and explicit approvals before state-changing operations. Use local Git for read-only baseline inspection. Do not commit, push, open a PR, or deploy.

## Output
Return changed behavior, files, baseline, tests added or updated, known risks, and validation handoff.

Read [risk-and-specialists.md](references/risk-and-specialists.md), [repository preflight](../../../references/repository-preflight.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
