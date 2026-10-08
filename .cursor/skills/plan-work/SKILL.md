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
Use [context retrieval](../../../references/context-retrieval.md). Read only enough current repository and Jira evidence to understand product impact; do not load implementation detail unless scope or feasibility requires it. This skill answers "what work should we define from what we already know," not "what do we know about this project." Missing or stale context triggers a `/sync-context` handoff only for claims that depend on current implementation evidence. It does not block business-only planning, and it does not mean stop drafting.

## Planning hierarchy
Epic → User Story → Task. A Task does not require a Story parent, and a Story does not require an Epic parent, when the methodology does not need one — do not force every item through all three levels. Sprint Backlog is a planning collection of selected work items; it is not a fourth parent level in this hierarchy.

This is this plugin's own conceptual drafting model. It is not Jira's issue-type hierarchy. A recommended parent is a logical relationship, for example "this Task supports Story X", not a Jira issue type. When preparing a Jira write for a Task that supports a Story, discover the site's issue types and hierarchy, then put the exact issue type in the payload the Product Owner approves. Offer the options the site actually allows, typically: create a Jira Subtask under that Story, or create a Jira Task and link it to that Story. Do not silently change a Task into a Subtask because a Story was recommended as its parent. See [Jira integration](../../../references/jira-integration.md).

## Input and routing
Accept natural language plus optional Jira key or URL and repository URL. Infer the planning level — Epic, User Story, Task, or Sprint Backlog — from the request's own language rather than defaulting every request to one level; route an update to existing work separately. Ask one focused question only when the level is genuinely ambiguous and the ambiguity is material to how the item should be defined.

## Prerequisites
Read current repository context when it already exists. A missing or stale repository context blocks only the parts of this skill that genuinely need it: a technical feasibility claim, a parent recommendation that depends on reading current code, or any statement about what the codebase already does. It does not block business-only planning — a Product Owner can define an Epic or a Story before any code exists. When context is missing or stale and this item needs it, say so, mark that part unavailable rather than guessed, and offer a `/sync-context` handoff; do not claim that it ran automatically, and do not refuse to draft the rest of the item while that part is pending. For existing work, read the current issue, linked work, and relevant implementation before proposing changes. Use the Jira integration contract to retrieve Jira data. If it is unavailable, request the issue content or produce a clearly labeled local-only proposal.

## Story description template
Apply this when preparing a User Story's Jira write payload, not earlier. By that point the Product Owner and the draft already agree on the story's content, so this is a publication formatting choice, not a drafting one, and it must not compete with the product questions in step 2 of the workflow below. At that point, read any `## Planning template` decision from `.ai-dlc-config.md` and call `decision_reprompt_allowed(decision, same_run)`. With no recorded decision, or when it returns true, offer [jira-story-template.md](references/jira-story-template.md). The Product Owner may accept it, edit the headings, or decline it. A recorded `declined` is never re-offered without an explicit request to reconsider. A recorded `deferred` is not re-offered within the same run, but is offered again on a later run — a `## Planning template` section existing is not by itself "already decided."

The template is the description only. Acceptance criteria go in the issue type's acceptance-criteria field when Jira exposes one. Discover that field from the issue type. Do not hardcode a custom field id. If the field is missing, keep the criteria in the local proposal and say the Jira field was not found. Do not copy them into the description unless the Product Owner explicitly chooses that exception for this write.

## Workflow
1. Classify the request's planning level from the user's words and explain the classification in one sentence.
2. Ask only the small number of Product Owner questions that materially improve this specific item, drawn from what the request, synchronized context, and Jira evidence do not already answer. Do not ask a generic questionnaire, and do not re-ask something already supplied.
3. Inspect scoped code and connected Jira work before claiming feasibility. When repository context is missing or stale and this item does not yet depend on existing code, continue with business-only planning and mark technical feasibility as not yet assessed instead of blocking the draft.
4. Separate facts, constraints, and assumptions in business language.
5. For a new User Story, read [epic-discovery.md](references/epic-discovery.md) and recommend a parent Epic, or recommend defining a new one. For a new Task, use the same reference to recommend a parent User Story when one genuinely applies, or an Epic directly only when none does. Never create a recommended parent silently.
6. Use the routed reference to produce a proposal, in this skill's own planning model, that can be edited in chat. The main chat drafts; do not delegate drafting to a specialist agent. Do not apply the Jira Story description template at this step — see "Story description template" above for when that applies.
7. Run deterministic validation over the drafted proposal before requesting independent review. Resolve `scripts/context_tools.py` relative to this skill, the same way [validation.md](../sync-context/references/validation.md) resolves it for `/sync-context`. From this file the script is `../../../scripts/context_tools.py`. Do not resolve it from the consumer repository's working directory. Write the proposal JSON to a temporary file outside the consumer repository, or pass it on standard input with `python3 ../../../scripts/context_tools.py plan-validate -`. Do not create `proposal.json` inside the consumer repository. The JSON shape is documented on `plan_validate_proposal`. Resolve every failed or unresolved check before review. An `external` check names a Jira issue key that is not an item in this proposal. It is not a structural failure. Confirm that issue exists with a Jira read and give that evidence to the reviewer. Do not drop the dependency or invent a stub item to make the check disappear. Invalid input is a failed or unresolved check. Do not show a Python traceback as the result.
8. When the PO says the draft is ready for review, request an independent `product-reviewer` assessment through a supported host agent facility.
9. If the host cannot delegate independently, keep independent review visibly pending. Do not present self-review as independent review. Allow a named human review or a policy-permitted exception; otherwise block publication while drafting continues.
10. Consolidate blocking findings and only the PO questions needed to resolve business uncertainty. For a straightforward correctness or quality fix, the main chat may apply it before presenting the final review; for a finding that would change product scope, behavior, assumptions, or intent, surface it to the PO instead of deciding it silently. Re-run affected review scope only after a material revision, then surface unresolved disagreement to the human instead of looping.
11. For existing work, show a minimal field-level update diff that preserves unrelated content and links; preserve previously approved content unless new evidence conflicts, and surface the conflict instead of silently overwriting it. A second identical run must not create a duplicate planning artifact.
12. Mark the draft **ready for review** after PO drafting. Record independent review as completed, unavailable, or pending. Resolve blockers, then request **approved for publication** only for the exact Jira mutation or optional Git intent PR. Approval of the local plan is never, by itself, approval to mutate Jira.
13. When preparing the Jira write payload for a new User Story, apply the Story description template above before showing the final payload for approval.
14. At the same point, include each drafted dependency and any optional suggested field in that one publication confirmation. Approve each dependency as a plain-language relationship between draft identifiers, for example "Story A blocks Story B", not as a pair of Jira keys that do not exist yet. After the issues exist, create the link and re-read it — see [Jira integration](../../../references/jira-integration.md), "Dependencies as issue links" and "Optional suggested fields," and [approval-contract.md](../../../references/approval-contract.md).
15. After an approved write, re-read the written record, report publication completed, pending, or partially completed, and distinguish local persistence from confirmed Jira state. Reconcile an uncertain write before retrying.

## Sprint Backlog mode
Act as a Product Owner planning the sprint, not drafting one isolated item. Distinguish selecting already-defined work already visible in Jira from creating new work that still needs definition. Surface sprint goal, candidate items, dependency order, blockers, and open questions from available evidence. Never invent team capacity, velocity, story points, estimates, or dates; report them as unknown when evidence is missing and material. This capacity rule governs planning the whole sprint. Suggesting a Sprint or Story Points value for one item at publication time (see "Optional suggested fields" in [Jira integration](../../../references/jira-integration.md)) is a narrower, evidence-based action and never substitutes for this capacity rule.

## Duplicate safety
Do not run a standalone duplicate search in this version. If an obvious duplicate is encountered incidentally while inspecting the candidate parent or an explicitly referenced issue, surface it. Do not search Jira for duplicates of the item being drafted.

A partial Jira write is not duplicate detection. Re-read the target record and reconcile it before retrying. That is write recovery, not a duplicate search.

## Plan state
Each item moves through one status, in order: `drafted`, then `reviewed`, then `approved`, then `persisted`. `blocked` and `unavailable` can apply at any point and are not approval.

- `drafted` includes the moment the draft is marked ready for review. Ready for review is not approval. `local_plan_approved` is false.
- `reviewed` means independent review finished with no unresolved blocker. `local_plan_approved` is still false.
- `approved` means the Product Owner approved the local plan. That sets `local_plan_approved` true. It does not approve a Jira write.
- Jira publication approval is a separate decision, `jira_mutation_approved`. `jira_mutation_authorized` is true only when both are true. Ask for it only for the exact payload, after the local plan is `approved`.
- `persisted` means the approved write was re-read from Jira.

Do not set `local_plan_approved` from ready-for-review, from review completion, or from a Canvas edit.

## Approval boundary
Planning is dry-run by default. Canvas edits do not authorize external writes. Reviewer findings never replace PO approval. A Jira write must name the project, the exact issue type, issue key or creation fields, issue links, and comments. Retry partial approved writes by reading the target record before retrying. That re-read is write recovery, not a duplicate search.

## Final review
Show the ready-for-review draft, and the result after an approved write, with the shared [canvas review](../../../references/canvas-review.md): use the host Canvas capability when available, otherwise the same sections go in chat and the reply says Canvas is unavailable on this host. Include the proposed item or backlog, acceptance criteria, Epic relationship, dependencies, assumptions, open questions, Jira parent recommendation, deterministic validation result, reviewer findings, and any change already applied from review. A run with nothing to show gets a short chat reply, not a Canvas open or refresh.

## Outputs
Return the route, evidence sources, editable proposal, approval-ready Jira payload or update diff, assumptions, and unresolved questions. Do not create Story mirrors, empty subtasks, or capacity commitments. A suggested Priority, Label, Fix Version, Sprint, or Story Points value is optional, sourced from existing evidence per "Optional suggested fields" in [Jira integration](../../../references/jira-integration.md), always shown as a suggestion, and included in the same publication confirmation as the rest of the payload. Return each approved dependency as the plain-language relationship that was confirmed, then the issue link created after the issues exist and checked by a re-read.

Read only the routed reference, [jira-story-template.md](references/jira-story-template.md), [epic-discovery.md](references/epic-discovery.md), [product-review.md](references/product-review.md), [approval-contract.md](../../../references/approval-contract.md), [canvas review](../../../references/canvas-review.md), [Jira integration](../../../references/jira-integration.md), and [skill composition](../../../references/skill-composition.md).
