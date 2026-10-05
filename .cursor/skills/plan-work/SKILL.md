---
name: plan-work
description: Plan a business Epic, User Story, Task, proposed sprint backlog, or update to existing work from natural-language intent.
disable-model-invocation: true
---

# Plan work

## Purpose
Act as a Product Owner copilot: turn business intent into an editable, evidence-based proposal at the right planning level, without prematurely creating Jira work. A request to define one item is not a request to generate a full backlog.

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Context retrieval
Use [context retrieval](../../../references/context-retrieval.md). Read only enough current repository and Jira evidence to understand product impact; do not load implementation detail unless scope or feasibility requires it. This skill answers "what work should we define from what we already know," not "what do we know about this project" — if context is clearly missing or stale, say so and hand off to `/sync-context` instead of rediscovering it here.

## Planning hierarchy
Epic → User Story → Task. A Task does not require a Story parent, and a Story does not require an Epic parent, when the methodology does not need one — do not force every item through all three levels. Sprint Backlog is a planning collection of selected work items; it is not a fourth parent level in this hierarchy.

## Input and routing
Accept natural language plus optional Jira key or URL and repository URL. Infer the planning level — Epic, User Story, Task, or Sprint Backlog — from the request's own language rather than defaulting every request to one level; route an update to existing work separately. Ask one focused question only when the level is genuinely ambiguous and the ambiguity is material to how the item should be defined.

## Prerequisites
Read current repository context. If it is missing or stale, provide a `/sync-context` handoff before proceeding; do not claim that it ran automatically. For existing work, read the current issue, linked work, and relevant implementation before proposing changes. Use the Jira integration contract to retrieve Jira data. If it is unavailable, request the issue content or produce a clearly labeled local-only proposal.

## Story description template
On the first `plan-work` run for an engagement, if `.ai-dlc-config.md` has no `## Planning template` decision, offer [jira-story-template.md](references/jira-story-template.md) before drafting a User Story description. The Product Owner may accept it, edit the headings, or decline it. Call `bugbot_reprompt_allowed` with the recorded decision so a later run reuses an approval and does not ask again after a decline or an in-run defer.

The template is the description only. Acceptance criteria go in the issue type's acceptance-criteria field when Jira exposes one. Discover that field from the issue type. Do not hardcode a custom field id. If the field is missing, keep the criteria in the local proposal and say the Jira field was not found. Do not copy them into the description unless the Product Owner explicitly chooses that exception for this write.

## Workflow
1. Classify the request's planning level from the user's words and explain the classification in one sentence.
2. Ask only the small number of Product Owner questions that materially improve this specific item, drawn from what the request, synchronized context, and Jira evidence do not already answer. Do not ask a generic questionnaire, and do not re-ask something already supplied.
3. Inspect scoped code and connected Jira work before claiming feasibility.
4. Separate facts, constraints, and assumptions in business language.
5. For a new User Story, read [epic-discovery.md](references/epic-discovery.md) and recommend a parent Epic, or recommend defining a new one. For a new Task, use the same reference to recommend a parent User Story when one genuinely applies, or an Epic directly only when none does. Never create a recommended parent silently.
6. Use the routed reference to produce a proposal that can be edited in chat. The main chat drafts; do not delegate drafting to a specialist agent.
7. Search Jira for an obvious exact duplicate of the item before independent review; this is a basic safety check, not a general semantic duplicate-story search, which stays out of scope. Give duplicate candidates and search limits to the reviewer. If Jira is unavailable, mark duplicate search unavailable rather than reporting no duplicates.
8. When the PO says the draft is ready for review, request an independent `product-reviewer` assessment through a supported host agent facility.
9. If the host cannot delegate independently, keep independent review visibly pending. Do not present self-review as independent review. Allow a named human review or a policy-permitted exception; otherwise block publication while drafting continues.
10. Consolidate blocking findings and only the PO questions needed to resolve business uncertainty. For a straightforward correctness or quality fix, the main chat may apply it before presenting the final review; for a finding that would change product scope, behavior, assumptions, or intent, surface it to the PO instead of deciding it silently. Re-run affected review scope only after a material revision, then surface unresolved disagreement to the human instead of looping.
11. For existing work, show a minimal field-level update diff that preserves unrelated content and links; preserve previously approved content unless new evidence conflicts, and surface the conflict instead of silently overwriting it. A second identical run must not create a duplicate planning artifact.
12. Mark the draft **ready for review** after PO drafting. Record independent review as completed, unavailable, or pending. Resolve blockers, then request **approved for publication** only for the exact Jira mutation or optional Git intent PR. Approval of the local plan is never, by itself, approval to mutate Jira.
13. After an approved write, re-read the written record, report publication completed, pending, or partially completed, and distinguish local persistence from confirmed Jira state. Reconcile an uncertain write before retrying.

## Sprint Backlog mode
Act as a Product Owner planning the sprint, not drafting one isolated item. Distinguish selecting already-defined work already visible in Jira from creating new work that still needs definition. Surface sprint goal, candidate items, dependency order, blockers, and open questions from available evidence. Never invent team capacity, velocity, story points, estimates, or dates; report them as unknown when evidence is missing and material.

## Approval boundary
Planning is dry-run by default. Canvas edits do not authorize external writes. Reviewer findings never replace PO approval. A Jira write must name the project, issue key or creation fields, issue links, and comments. Retry partial approved writes idempotently by reading the target record before retrying.

## Final review
Show the ready-for-review draft, and the result after an approved write, with the shared [canvas review](../../../references/canvas-review.md). Cursor agents cannot open a Canvas today; the same sections then go in chat, and the reply says Canvas is unavailable. Include the proposed item or backlog, acceptance criteria, Epic relationship, dependencies, assumptions, open questions, Jira parent recommendation, reviewer findings, and any change already applied from review.

## Outputs
Return the route, evidence sources, editable proposal, approval-ready Jira payload or update diff, assumptions, and unresolved questions. Do not create Story mirrors, empty subtasks, capacity commitments, sprint IDs, or priorities.

Read only the routed reference, [jira-story-template.md](references/jira-story-template.md), [epic-discovery.md](references/epic-discovery.md), [product-review.md](references/product-review.md), [approval-contract.md](references/approval-contract.md), [canvas review](../../../references/canvas-review.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
