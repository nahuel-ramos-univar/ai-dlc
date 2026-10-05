# Project-specific Cursor rules

Questions about missing project references or conventions belong in
[project-onboarding.md](../../../../references/project-onboarding.md). This
file stays the contract for writing a rule. Onboarding may propose a rule
only through the flow below.

This is change set B, alongside Bugbot configuration. A context document
records an **observed fact** ("this service uses PostgreSQL"). A scoped rule
records a **team policy** ("schema changes must use the approved migration
mechanism"). Keep facts in context; move only an established or explicitly
agreed policy into a rule. Do not turn an incidental coding pattern seen in
one or two files into a mandatory policy, and do not assume an IAM, security,
or ownership rule from one engagement applies to every consumer repository.

## When a proposal is justified

Propose a project rule only when the policy is one of:

- stated in existing project documentation or an existing (even informal)
  team rule that this file would consolidate rather than duplicate;
- explicitly confirmed by the user during this conversation as a standing
  policy, not merely a pattern this run happened to observe.

Do not propose a rule to encode a single file's style choice, a generated or
vendored pattern, or a one-off decision with no stated intent to repeat it.

## Placement and shape

Propose at most one narrowly scoped rule per confirmed policy, placed at
`<source-root>/.cursor/rules/<slug>.mdc`. Never propose a rule that:

- duplicates this plugin's own skills, agents, or shared references — those
  stay inside the plugin, never copied into the consumer;
- restates generic style, lint, or formatting guidance already enforced by
  the project's own tooling;
- is empty, a placeholder, or exists only to create a directory.

State the specific regression or inconsistency the rule prevents, and name
the observed path, command, or convention it is based on.

## Approval and persistence

Use the same approve/decline/defer contract as
[bugbot-configuration.md](bugbot-configuration.md): show the proposed file
content before writing it, ask once per confirmed policy, and persist the
decision in the configured artifact home's configuration keyed by the stable
repository ID. Do not ask again after `declined` unless the user explicitly
asks to reconsider; `decision_reprompt_allowed` in `scripts/context_tools.py`
encodes this same decision shape and may be reused for the same check.

Approval of change set A (context documents) does not authorize set B.
Approval of a Bugbot proposal does not authorize a project rule, and the
reverse is also true — ask once per set, not once per run for everything.

## Preservation

Call `unrelated_rules_preserved(existing, approved_writes)` and leave every
returned path untouched. Do not rewrite an existing rule merely to silence
an unrelated review finding.
If an existing rule appears stale, duplicated, or contradicted by current
evidence, propose a narrow, separate patch to that specific rule rather than
folding it into an unrelated change.

Create `.cursor/` in the consumer only when an approved file actually needs
it. Never populate it with a copy of this plugin's skills or agents.
