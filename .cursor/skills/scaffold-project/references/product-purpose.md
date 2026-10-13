# Product purpose and scaffolding boundary

Use this from `scaffold-project`, step 2 (before the stack), step 6 (the approval proposal), and step 10 (the reviewer's input).

## Establish the purpose before the stack

Before proposing a stack and file structure, establish:

- what is being built, and what problem it solves;
- who uses it — human users and their roles, or system and API consumers;
- the primary user journey or system interaction;
- the intended initial scope, and what is explicitly excluded;
- an existing constraint that materially affects the foundation.

Reuse a fact already supplied in the request, this conversation, or a confirmed project reference (see [project onboarding](../../../../references/project-onboarding.md)). Do not repeat a question the user already answered.

When these facts are missing, ask one small batch of focused questions, starting with purpose, users, and the primary interaction. Ask a follow-up only when the answer would materially change the proposed stack, module split, or entrypoint — not as a fixed checklist run every time.

Not every project needs the same follow-ups:

- A static website does not need a backend question.
- An internal tool does not need a monetization question.
- An API or library may have system consumers rather than human users; ask about the caller, not a persona.
- Do not infer authentication, a database, a payment flow, an AI agent, a queue, or infrastructure merely from a broad category such as "e-commerce" or "SaaS." Ask about it directly, or leave it out of scope.

## When the purpose is deliberately unknown

If the user explicitly wants a generic technical starter, or does not yet know the product's purpose, allow that choice. State the limitation in the proposal, and keep the foundation deliberately minimal. Do not fill that gap with an invented health check, screen, or infrastructure topology.

## Scaffolding boundary

Resolve, from the request or one question, whether this is:

- a technical foundation — this skill's actual scope;
- a navigable prototype — still foundation-level: fake data, no real behavior, and the proposal says so;
- a working business feature — out of scope for this skill.

A health endpoint, a minimal entrypoint, or a smoke test is a normal part of a technical foundation. Do not treat one as proof a business feature was implemented, and do not use it as a way to actually implement one.

If the requested outcome includes real business behavior beyond a foundation, say so plainly and hand off to `/plan-work` for that work. Do not silently expand this skill into backlog creation or feature implementation. Do not require Jira access or a complete business model merely to scaffold a foundation.

## Connect the proposal to the purpose

Open the approval proposal with a short purpose summary: the confirmed purpose, its users or consumers, the primary interaction, what this scaffold enables, and what stays out of scope. Present the technical proposal only after that summary.

For each major component — a backend service, a frontend app, a datastore, infrastructure — say briefly why it exists: tied to the confirmed purpose, or an explicit technical requirement the user stated. Label each choice as one of:

- a technology the user explicitly selected;
- a constraint verified from an existing file or a confirmed project reference;
- a recommendation that still needs approval.

Do not claim an earlier run invented a stack merely because its transcript is incomplete. Describe only what this run's own proposal adds.

## Reviewer input

When requesting the scaffolding review in [foundation and review](foundation-and-review.md), include the confirmed purpose and the scaffolding boundary (technical foundation, navigable prototype, or working business feature) in what the reviewer receives. Ask it to flag a concrete mismatch: a backend or datastore generated for a purpose stated as static-only; authentication, a payment flow, or other business behavior added without approval; a component missing that the approved smoke behavior actually needs; or a claim that a business feature exists when only a placeholder was created. This is still the same single `implementation-reviewer` in scaffolding mode. Do not add a second reviewer, and do not turn this into a speculative business or architecture review.
