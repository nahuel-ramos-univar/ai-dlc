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
content before writing it, and ask once per confirmed policy. Do not ask
again after `declined` unless the user explicitly asks to reconsider;
`decision_reprompt_allowed` in `scripts/context_tools.py` encodes this same
decision shape and may be reused for the same check.

**Identity is the pair (stable repository ID, stable policy slug), not the
repository ID alone.** A repository can have several independent project-rule
policies under review at once -- "database changes must use migrations,"
"use pnpm for package management," and so on. Each is a separate decision.
Keying only by repository ID would let a `declined` recorded for one policy
silently suppress the prompt for an unrelated policy in the same repository;
that is a real collision, not a theoretical one, so key every decision by
both parts together.

The **policy slug** is a short, stable, kebab-case identifier for the policy
itself, in the same `[a-z0-9]+(?:-[a-z0-9]+)*` shape `REPOSITORY_ID_PATTERN`
already validates repository IDs with (for example `database-migrations`,
`package-manager`). Choose it once, when the policy is first confirmed, from
the policy's substance -- not from the eventual rule file's path, because a
`declined` or `deferred` policy may never materialize a rule file at all.
Keep a chosen slug stable across every later reconsideration of that same
policy; do not mint a new slug for the same policy on a later run.

**`Rule` is optional metadata, not identity.** Record the rule file's path
only once a proposal for that policy is actually `approved` and the file is
written. A `declined` or `deferred` entry has no `Rule` line. If an approved
rule file is later moved or renamed, update `Rule` in place; the policy slug
that identifies the decision does not change.

```markdown
## Project rule decisions
- Repository: `payments-api`
  - Policy: `database-migrations`
  - Decision: declined
  - Baseline: `abc123`
  - Fingerprint: `<fingerprint>`
- Repository: `payments-api`
  - Policy: `package-manager`
  - Decision: approved
  - Rule: `.cursor/rules/package-manager.mdc`
  - Baseline: `abc123`
  - Fingerprint: `<fingerprint>`
```

Look up the decision for the exact (repository ID, policy slug) pair this
proposal is about before calling `decision_reprompt_allowed`. A `declined` or
`deferred` result for one policy slug never changes what is allowed for a
different policy slug in the same repository, even on the same run.

Approval of change set A (context documents) does not authorize set B.
Approval of a Bugbot proposal does not authorize a project rule, and the
reverse is also true — ask once per set, not once per run for everything.
Within set B, approving one policy's rule does not authorize a different
policy's rule in the same run; each (repository, policy) pair is its own ask.

## Preservation

Call `unrelated_rules_preserved(existing, approved_writes)` and leave every
returned path untouched. Do not rewrite an existing rule merely to silence
an unrelated review finding.
If an existing rule appears stale, duplicated, or contradicted by current
evidence, propose a narrow, separate patch to that specific rule rather than
folding it into an unrelated change.

Create `.cursor/` in the consumer only when an approved file actually needs
it. Never populate it with a copy of this plugin's skills or agents.
