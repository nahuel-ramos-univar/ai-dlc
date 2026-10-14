# Single Story

Ask about the user outcome, primary actor, observable success, exclusions, and open business questions. Do not ask implementation, schema, deployment, or test-runner questions.

Use the outcome-oriented form "As a [user or actor], I want [capability], so that [outcome]" when it fits the work. Do not force technical work into fake user-story wording; route that to [task.md](task.md) instead.

Propose:

- title;
- story statement or objective;
- business or user value;
- recommended parent Epic — see [epic-discovery.md](epic-discovery.md);
- scope;
- acceptance criteria expressed as observable, testable behavior; Given/When/Then is optional, not mandatory;
- relevant scenarios;
- exclusions;
- dependencies;
- assumptions and technical constraints, clearly labeled;
- validation or testing expectations, where appropriate — see [Testing and validation expectations](#testing-and-validation-expectations) below;
- a Story-specific goal or success measure, only when one actually exists — see [Story-specific goals and metrics](#story-specific-goals-and-metrics) below;
- a Story-level design reference, only when one actually exists — see [Design reference](#design-reference) below;
- source or traceability: what evidence this item is based on;
- any obvious duplicate noticed incidentally while inspecting a candidate parent or an explicitly referenced issue. Do not run a standalone duplicate search.

Do not invent behavior purely to make the acceptance criteria look complete; leave unresolved behavior as an explicit open question instead — see [Open questions and ambiguity](#open-questions-and-ambiguity) below. Technical constraints should explain the impact in business language. Hand implementation details to `refine-story`.

Do not fill or offer [jira-story-template.md](jira-story-template.md) while drafting. That template is a publication-payload step in the main skill, after the product content has been drafted and reviewed. Keep acceptance criteria out of the Jira description when that payload is prepared.

Approved scope and exclusions must survive that publication. Render them as Scope / Out of Scope when they state a boundary that is not already an Acceptance Criterion. Do not drop an approved exclusion because another section has no place for it.

## Testing and validation expectations

Acceptance criteria define required observable product behavior. Testing or validation expectations are different: they may add useful business-level scenarios, examples, or conditions that help exercise an acceptance criterion that already exists. They must not introduce a new required behavior, expected outcome, UX decision, or implementation decision that is absent from the acceptance criteria or another authoritative source.

If a candidate testing note would introduce new required product behavior, it does not belong in testing. Move it into the acceptance criteria if the Product Owner confirms it, or surface it as an open question if it is still unresolved.

A Product Owner note belongs in Testing only when it adds information that is not already in the acceptance criteria. Omit Testing entirely when the note would only restate or paraphrase them.

For example, an acceptance criterion already says the order list shows each order's status. The Product Owner then asks to exercise that list with an account that has both a completed order and one still in progress. That covering condition is a valid testing note: it names data to use, not a new required behavior. "A signed-out shopper is redirected to `/login`" is not a valid testing note unless that redirect is already defined; on its own it introduces new product behavior, so it belongs in the acceptance criteria or as an open question.

Do not introduce technical testing detail such as mocks, a unit-versus-integration strategy, environments, implementation-specific fixtures, or a test-framework choice, unless the Product Owner already supplied that as source evidence. Technical validation design belongs downstream, in `refine-story` and later implementation planning, not in this Story.

## Story-specific goals and metrics

A Story-specific goal or success measure is the exception, not the default. Include one only when the Product Owner or supporting evidence explicitly provides it and it adds information that is not already expressed by the acceptance criteria. Do not infer, derive, or invent a metric merely because the publication format supports one.

"Allow shoppers to see their orders" is not a Story-specific goal when that is already the Story or an acceptance criterion — it is redundant, not a measure. "Reduce order-status support contacts by X%" is a genuine example, but only when the Product Owner or authoritative evidence actually supplied it.

Epic- and Feature-level outcomes and success criteria remain owned by [feature-or-epic.md](feature-or-epic.md). Do not duplicate an Epic's goal into every child Story.

## Open questions and ambiguity

Preserve the rule above: do not invent behavior, and leave anything unresolved as an explicit open question. These are reusable ambiguity patterns worth challenging before finalizing a Story, not a checklist tied to any one domain:

- a label or status value whose user-facing meaning is unclear — it could mean the raw persisted value, a mapped business status, or a user-facing label;
- an access restriction with an unspecified resulting experience — "cannot access" does not say whether that means a redirect, an authentication prompt, an error page, or only an HTTP status;
- an error condition without defined observable behavior — "handle failures" does not say what the user sees;
- a term with more than one plausible product interpretation that would change implementation or the user experience.

Use existing project context, design, or product conventions first when they already resolve the ambiguity. Ask the Product Owner only when the available evidence does not resolve it.

## Design reference

`.ai-dlc-config.md`'s `## Project references` (see [artifact-home.md](../../sync-context/references/artifact-home.md)) tells AI-DLC where the project's design context lives in general. A Story-level design reference is narrower: it points to the specific design artifact relevant to this one Story — a Figma file, frame, page, section, prototype, or other specific artifact — when one actually exists.

Reuse the project-level Figma reference and role concepts; do not duplicate the whole project configuration into every Story. Carry only the concrete evidence relevant to this Story, for example the URL plus the node or frame identifier when available. Do not invent a design reference. Omit it when no Story-specific design exists. Do not replace a Story-specific reference with the project-level Figma URL.

This skill collects that reference while drafting a new Story or updating an existing one. The Jira publication template does not discover, infer, or inspect designs; it only publishes a reference already in the approved proposal.

During drafting or update-existing:

- Reuse a design URL the Product Owner supplied, or one already present on the target Jira issue.
- If an explicitly linked Design ticket is relevant and reachable with existing tools, retrieve that reference inside that issue. Do not crawl a Figma project or file.
- Preserve the concrete URL and the node or frame identifier when available.
- Distinguish a reference that was supplied or found from a design whose contents were inspected. A URL alone is not proof that its contents were read.
- Inspect design contents only when an existing supported host tool is available and this workflow authorizes that read. Follow the Figma access rule in [project-onboarding.md](../../../../references/project-onboarding.md): do not add a Figma client. If access is missing, keep the link as confirmed and unverified. Report unavailable access honestly; do not claim inspection.
- If several references conflict, or their relevance is unclear, ask one focused question rather than silently choosing one.

Still out of scope: a design lifecycle or readiness-state model; automated Jira or Figma synchronization; crawling an entire Figma project or file; a new MCP client, authentication layer, or integration framework; automatic screenshots, exports, or attachments.

Missing design is not a universal blocker. A Story may be drafted and published without a Figma reference. Flag the gap only when the missing design is needed to resolve a material requirement for the requested work.

## Semantic precedence

When more than one of these sections exists, none of them silently overrides another:

- acceptance criteria state required observable behavior;
- scope and exclusions state explicit boundaries;
- open questions state unresolved product decisions;
- a Story-specific goal or measure states a desired outcome; it cannot override acceptance criteria;
- testing and validation expectations state how existing behavior may be exercised; they cannot introduce or override behavior;
- a design reference is supporting evidence; it cannot silently override an explicitly approved requirement.

If two sources conflict — for example the acceptance criteria require error and empty states to be distinguishable, but the referenced design shows the same UI for both — surface that conflict for the Product Owner to resolve. Do not silently decide which source wins.

## Keep output concise through omission, not information loss

Minimum sufficient context, with no duplication, is the goal — not the shortest possible Story. A Story needs only the sections that add real information; a perfectly valid Story may be only title, story statement, acceptance criteria, and scope. Do not fill an optional section merely because it exists in this list. Do not shorten acceptance criteria by removing a distinction that changes behavior, such as empty state versus error state, authenticated versus unauthenticated behavior, or in-scope versus out-of-scope behavior.
