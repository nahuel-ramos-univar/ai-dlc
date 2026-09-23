---
name: check-governance
description: Apply repository policy and approval checks proportionate to semantic risk, including proposed BUGBOT.md maintenance.
disable-model-invocation: true
---

# Check governance

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Workflow
1. Identify applicable repository policies, protected paths, required approvals, environment boundaries, and external-write targets.
2. Assess semantic risk from changed behavior, dependency impact, security, data integrity, reversibility, novelty, and uncertainty.
3. Perform routine checks for all work. Recommend fast, standard, or deep review with evidence for the selected depth.
4. The main chat may request `governance-reviewer` through a supported host agent facility only when security, data integrity, policy, or approval uncertainty warrants independent review.
5. Inspect documented BUGBOT.md locations and inheritance before proposing updates.
6. Base any BUGBOT.md proposal on observed repository invariants and concrete bug risks.

## Approval boundary
Policy files, infrastructure, permissions, authentication, authorization, Jira writes, and production-related actions require explicit review and scoped approval. Existing session approval applies only to the material change set it covers.

## Output
Return applicable controls, assessed depth, required approvals, observed evidence, and any proposed—not applied—policy changes.

Read [risk-rubric.md](references/risk-rubric.md).
