---
name: refine-story
description: Refine an approved Story with development, QA, or combined technical analysis while preserving business acceptance criteria.
disable-model-invocation: true
---

# Refine story

## Input
Accept an existing work item or approved draft and `development`, `qa`, or `combined` mode. Read the Story through Jira MCP using the Jira integration contract when available; otherwise require supplied content and mark the result local-only. If a draft has no approved parent work item, provide a `/plan-work` handoff before creating subtasks.

## Workflow
1. Record the Story revision, analyzed Git baseline, affected paths, and local modifications.
2. Confirm each acceptance criterion is business-facing before adding technical detail.
3. In development mode, inspect behavior, callers, contracts, dependencies, compatibility, rollback, and risk.
4. In QA mode, map every criterion to positive, negative, boundary, regression, fixture, environment, and automation needs.
5. In combined mode, resolve conflicts between development feasibility and acceptance evidence. The main chat performs this analysis; do not delegate drafting of the refinement to a specialist agent.
6. Select fast, standard, or deep review from semantic risk, uncertainty, and blast radius. Fast refinement stays lightweight. Standard and deep material refinement request an independent `refinement-reviewer` assessment through a supported host agent facility.
7. If independent delegation is unavailable, disclose the limitation. Never present the main chat’s own refinement as an independent review.
8. Consolidate only relevant reviewer findings. If a technical finding changes approved business scope, provide a `/plan-work` handoff before changing the Story.
9. Propose additive Jira sections or meaningful subtasks. Never replace business acceptance criteria.

## Approval boundary
Do not create or update Jira records without approval of the exact change set. Do not create a PR or mandatory technical-plan document. A proposed subtask must have a specific owner purpose and acceptance evidence.

## Output
Return the analyzed baseline, scoped findings with file references, uncertainty, recommended test coverage, and Jira update payload.

Read [modes-and-drift.md](references/modes-and-drift.md), [review-profiles.md](references/review-profiles.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
