---
name: plan-work
description: Plan a business Story, feature or Epic, proposed backlog, or update to existing work from natural-language intent.
disable-model-invocation: true
---

# Plan work

## Purpose
Turn business intent into an editable, evidence-based proposal without prematurely creating Jira work.

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Context retrieval
Use [context retrieval](../../../references/context-retrieval.md). Read only enough current repository and Jira evidence to understand product impact; do not load implementation detail unless scope or feasibility requires it.

## Input and routing
Accept natural language plus optional Jira key or URL and repository URL. Classify as a single Story, feature or Epic, sprint backlog, or update to existing work. Ask one focused question only when classification changes scope.

## Prerequisites
Read current repository context. If it is missing or stale, provide a `/sync-context` handoff before proceeding; do not claim that it ran automatically. For existing work, read the current issue, linked work, and relevant implementation before proposing changes. Use the Jira integration contract to retrieve Jira data. If it is unavailable, request the issue content or produce a clearly labeled local-only proposal.

## Workflow
1. Classify the request from the user’s words and explain the classification in one sentence.
2. Collect business outcome, users, trigger, success measures, exclusions, and unresolved business questions.
3. Inspect scoped code and connected Jira work before claiming feasibility.
4. Separate facts, constraints, and assumptions in business language.
5. Use the routed reference to produce a proposal that can be edited in chat. The main chat drafts; do not delegate drafting to a specialist agent.
6. Search Jira for likely duplicate titles and behavior before independent review. Give duplicate candidates and search limits to the reviewer. If Jira is unavailable, mark duplicate search unavailable rather than reporting no duplicates.
7. When the PO says the draft is ready for review, request an independent `product-reviewer` assessment through a supported host agent facility.
8. If the host cannot delegate independently, keep independent review visibly pending. Do not present self-review as independent review. Allow a named human review or a policy-permitted exception; otherwise block publication while drafting continues.
9. Consolidate blocking findings and only the PO questions needed to resolve business uncertainty. Re-run affected review scope after material revisions, then surface unresolved disagreement to the human instead of looping.
10. For existing work, show a minimal field-level update diff that preserves unrelated content and links.
11. Mark the draft **ready for review** after PO drafting. Record independent review as completed, unavailable, or pending. Resolve blockers, then request **approved for publication** only for the exact Jira mutation or optional Git intent PR.
12. After an approved write, report publication completed, pending, or partially completed. Reconcile an uncertain write before retrying.

## Approval boundary
Planning is dry-run by default. Canvas edits do not authorize external writes. Reviewer findings never replace PO approval. A Jira write must name the project, issue key or creation fields, issue links, and comments. Retry partial approved writes idempotently by reading the target record before retrying.

## Outputs
Return the route, evidence sources, editable proposal, approval-ready Jira payload or update diff, assumptions, and unresolved questions. Do not create Story mirrors, empty subtasks, capacity commitments, sprint IDs, or priorities.

Read only the routed reference, [product-review.md](references/product-review.md), [approval-contract.md](references/approval-contract.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
