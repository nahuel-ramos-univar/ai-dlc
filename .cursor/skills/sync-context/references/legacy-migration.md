# Legacy migration

This is change set C. Migration stays inside `sync-context`, but context
generation (set A) and cleanup (set C) are different change sets with
different evidence and different approval. A run that generated new context
while cleanup remains pending must report exactly that, and must not claim
migration is complete. Only an applied, verified cleanup set earns that
claim.

## Inventory before classifying

Inspect the actual installed legacy components in this repository; do not
assume a prior inventory from a different repository or engagement applies
here. Look for: `.cursor/rules`, `.cursor/skills` and `.cursor/commands`
copied from a prior framework, `.cursor/agents`, `AGENTS.md` or Copilot
instruction files written by that framework, installer and guard scripts
under `scripts/`, GitHub workflows that check out or execute an external
framework checkout, `.gitattributes` blocks tied to that framework's file
paths, and workspace files referencing a sibling framework checkout.

A script present in the repository is not proof of what is actually active.
A precommit or pre-push guard script only takes effect once installed into
`.git/hooks/`, which is per developer machine and is never itself tracked by
Git; removing the installer or the script from the repository does not
remove an already-installed local hook copy, and this cannot be verified
from the repository alone. State that limitation explicitly rather than
claiming hooks are retired.

## Classify, do not bulk-delete

Classify each actual component, individually, as one of:

- **Retire** — superseded by this plugin's equivalent capability, with that
  equivalent named explicitly. Do not assume a 1:1 command replacement
  without showing the mapping: what the old command did, and which skill or
  reference now covers the same ground.
- **Preserve** — product knowledge, an approved architecture decision, or an
  unresolved requirement that is still true and would be lost if removed.
  Preserve, do not retire by default, every requirements or decision
  document that still describes a live decision.
- **Adapt or consolidate** — a team-specific policy worth keeping, but as a
  project rule (`project-rules.md`) or in context rather than in the old
  format.
- **Unresolved** — customized beyond the shipped template, or not
  sufficiently understood from available evidence. Leave it alone and say
  why it is unresolved; never fold an unresolved item into a bulk retirement.

Do not delete every path merely because it matches a naming pattern (for
example anything containing `aidlc`). A product's own coordinator repository
or discovery documents are not legacy just because their name contains that
string; classify by actual content and provenance, not by name.

Preserve a currently useful security or process control, or identify its
verified replacement, before removing the old one. A prompt instruction
alone is not an executable control and does not replace one; if the old
control was enforced by CI or a Git hook, the replacement must be enforced
the same way, or the gap must be reported, not assumed closed.

Reconcile legacy documents rather than deleting them sight unseen: current
code describes implemented behavior; an approved requirement or decision can
describe intended behavior that code has not caught up to yet. Keep both
where they still disagree usefully. Retire a document only once it is
superseded or redundant after this reconciliation; do not keep every
discovery document indefinitely by default, and do not claim every legacy
document has been converted when only some have been inspected.

## Present one cleanup set, then wait

Present one concrete, named cleanup set for approval — the specific paths to
retire, with the replacement each one maps to, and the unresolved items left
aside. Ask separately only about a genuine ambiguity the classification
could not resolve on its own; do not ask once per file. Apply the cleanup
only after that explicit approval, and only the items actually approved.
Removing a locally checked-out copy of the old framework itself needs its
own confirmation that it is not shared by another engagement and that it is
recoverable (it is Git history or an external remote, not something this
run invented).

Do not perform cleanup against a real consumer repository as a side effect
of any other request. Context generation (set A) never implies cleanup
authorization (set C); see [SKILL.md](../SKILL.md) Stage 5.
