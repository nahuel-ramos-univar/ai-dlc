---
name: validate-change
description: Validate an approved change against acceptance criteria using tests, review, contracts, security checks, and supported Bugbot handoff.
disable-model-invocation: true
---

# Validate change

## Start condition
Start when the user runs `/validate-change` with the changed paths, baseline, acceptance criteria, executed tests, and known gaps from implementation. Targeted fixes require an explicit `/implement-change` handoff, then a new `/validate-change` run for affected checks against the new code state.

## Workflow
1. Capture the branch, revision, working-tree state, changed paths, and acceptance criteria under review.
2. Map every acceptance criterion to a code inspection and the narrowest applicable unit, integration, E2E, manual, or unavailable check.
3. Run only relevant checks. Report command, revision, result, duration when known, and reason for skipped or unavailable checks.
4. Inspect dependency manifests, public contracts, migrations, and security-sensitive code when changed.
5. The main chat may request an independent `validator` or `implementation-reviewer` assessment for standard or deep-risk changes when a second review reduces uncertainty. Scope frontend/accessibility, backend/data integrity, infrastructure/permissions, contracts/integrations, QA/E2E, or architecture review only when relevant.
6. Coordinate Bugbot status as part of this workflow. Record it as passed, failed, blocked, not run, or not applicable with its reviewed code state.
7. Invalidate affected evidence if material code or configuration changes after a check.
8. Request `check-governance` for high-risk changes or materially stale review rules.
9. Return **ready to deliver** only when policy-required evidence is passed or an approved exception is recorded. Otherwise provide a targeted implementation handoff and identify the verification scope that must rerun.

## Bugbot
This plugin does not programmatically invoke Bugbot. When Bugbot is required or requested, ask the developer to run `/review-bugbot`, mark it pending user invocation, and never claim it ran or substitute another review engine. Observe remote Bugbot only when it appears in actual configured checks; do not assume it is configured. `deliver-change` inspects checks but does not coordinate Bugbot.

## Output
Return a concise acceptance-evidence matrix, reviewed Git state, failures, skipped checks, remaining risks, and explicit Bugbot status.

Read [evidence-and-bugbot.md](references/evidence-and-bugbot.md) and [skill composition](../../../references/skill-composition.md).
