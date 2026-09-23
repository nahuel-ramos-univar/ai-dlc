---
name: resolve-defect
description: Reproduce, diagnose, implement, and verify an authorized defect without duplicate reports or nested workflow loops.
disable-model-invocation: true
---

# Resolve defect

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Workflow
1. Read the reported behavior, environment, and existing linked Bugs through Jira MCP using the Jira integration contract when available.
2. Search Jira for likely duplicates using symptoms, affected area, and error wording before proposing a new Bug. If Jira is unavailable, report duplicate search as unavailable.
3. Reproduce only in a confirmed non-production environment. Record exact expected and observed behavior, input, environment, and revision.
4. Diagnose with scoped code, tests, logs that are safe to access, and contract evidence. Classify cause, impact, confidence, and whether scope exceeds a defect fix.
5. Provide a `/plan-work` handoff for scope expansion. Otherwise provide explicit `/implement-change` and `/validate-change` handoffs; do not claim those skills ran automatically.
6. Add an appropriate regression test when feasible, or explicitly explain why coverage is unavailable.

## Approval boundary
Creating or updating a Bug, changing issue links, and external writes need exact approval. Preserve partial-write safety by checking the target before retrying. Do not expose production data or credentials in a Bug.

## Output
Return reproduction status, root cause or uncertainty, fix scope, regression coverage, validation evidence, and approved external updates.

Read [triage-boundaries.md](references/triage-boundaries.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
