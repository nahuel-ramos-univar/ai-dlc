# Legacy migration

This is change set C. Migration stays inside `sync-context`, but context
generation (set A) and cleanup (set C) are different change sets with
different evidence and different approval. A run that generated new context
while cleanup remains pending must report exactly that, and must not claim
migration is complete. Only an applied, verified cleanup set earns that
claim.

A full migration away from a legacy adopted coordinator touches both sets at
once: set A creates each product repository's own distributed context (see
[artifact-home.md](artifact-home.md), "Migrating from adopted coordinator to
distributed"), and set C retires the coordinator's superseded files and
walks through the mandatory retirement decision below. This is still not a
separate skill or a new orchestration engine — it is the existing seven-stage
pipeline in [SKILL.md](../SKILL.md), applied to both sets in the same run,
with the usual independent approval per set.

**This reference describes a generic migration path for any engagement.**
No project name, repository name, or prior engagement is hardcoded into this
behavior; every example repository name below is illustrative.

## Classify repository role before classifying components

Before inventorying individual files, classify each repository actually
present in the authorized scope by its role. Call
`classify_repository_role(...)` in `scripts/context_tools.py`. It checks
evidence in a fixed priority order and never classifies from a name match
alone:

1. `has_plugin_manifest` (a real `.cursor-plugin/plugin.json` for this
   plugin, or an equivalent installed-plugin marker) → **plugin
   installation**.
2. Otherwise `has_shared_methodology_marker` (this checkout is the shared
   digital-ai-dlc methodology repository itself, not a product-specific
   coordinator) → **shared methodology checkout**. This wins even when
   `Coordinator` metadata also names this repository. A shared methodology
   checkout must not become a product coordination repository, because that
   role is the only one eligible for local checkout deletion.
3. Otherwise, this repository is the **product coordination repository**
   only when `repository_is_named_coordinator(coordinator_name,
   coordinator_root, repository_id, repository_root)` is true. Pass the
   configured `Coordinator` name and `Coordinator root`, or the subject of
   an operating-model record that explicitly assigns the coordinator role
   to this repository, together with this repository's own id and comparable
   root. `Placement: adopted-coordinator` is the operating mode of a
   repository that *uses* a coordinator. It is not evidence that the
   repository being classified *is* the coordinator, and it must not be
   passed as `coordinator_name` or `coordinator_root`. The placement-mode
   strings themselves never match.
4. Otherwise, if only the repository's name matches a legacy-sounding
   pattern (for example anything containing `aidlc`) with none of the above
   evidence → **unresolved**, not a classification that authorizes anything.
   A name is a hint to look closer, never a verdict.
5. With no legacy evidence and no name match → **product source
   repository**.

A nested `.git` marker alone does not prove a real Git submodule (see
`is_declared_submodule` in [SKILL.md](../SKILL.md) Stage 1); the same
"evidence over naming" discipline applies here. Report each repository's
classified role plainly, and treat an **unresolved** role as a gap to
disclose, not as grounds to retire or delete anything.

Repository role and project references are two independent checks. Each
repository being moved to distributed context during this migration may
already have a persisted `## Context identities` entry from a prior sync
and still have no confirmed `## Project references` section — a missing
Jira site, project, or board is not resolved just because identity already
exists. Check each repository's `## Project references` on its own merits
per [project-onboarding.md](../../../../references/project-onboarding.md),
then ask once for the engagement. Reuse a project reference the user
already confirmed when the repositories in scope belong to that same
project. Do not ask the identical question again for every repository. A
recurring ticket-key pattern (seen in file names, branches, or archived
docs) is a signal worth asking about. It is not a confirmed project, site,
or board, and it must not be written into `## Project references` before
the user confirms it.

## Inventory before classifying

Inspect the actual installed legacy components in each repository; do not
assume a prior inventory from a different repository or engagement applies
here. Look for: `.cursor/rules`, `.cursor/skills` and `.cursor/commands`
copied from a prior framework, `.cursor/agents`, `AGENTS.md` or Copilot
instruction files written by that framework, installer and guard scripts
under `scripts/`, GitHub workflows that check out or execute an external
framework checkout, `.gitattributes` blocks tied to that framework's file
paths, and workspace files referencing a sibling framework checkout. For a
migration specifically, also inventory: configuration and manifest files,
discovery reports, design documents, architecture decision records,
prompts, commands, skills, agents, project rules, scripts, Git hooks, CI
workflows, and workspace references that the legacy coordinator holds.

A script present in the repository is not proof of what is actually active.
A precommit or pre-push guard script only takes effect once installed into
`.git/hooks/`, which is per developer machine and is never itself tracked by
Git; removing the installer or the script from the repository does not
remove an already-installed local hook copy, and this cannot be verified
from the repository alone. State that limitation explicitly rather than
claiming hooks are retired.

Do not remove an unrelated project rule, security check, CI behavior, or
developer change merely because it was discovered while inventorying the
legacy coordinator. Inventory only what the legacy framework actually
installed or generated; leave everything else alone.

## Classify, do not bulk-delete

Classify each actual component, individually, as one of five categories:

- **Preserve** — product knowledge, an approved architecture decision, or an
  unresolved requirement that is still true and would be lost if removed.
  Preserve, do not retire by default, every requirements or decision
  document that still describes a live decision. An observed coding pattern
  is not automatically a team policy: when the implementation differs from a
  confirmed requirement or decision, preserve the confirmed requirement and
  report the difference rather than deleting the requirement to match the
  code.
- **Reconcile and migrate** — a team-specific policy, requirement, or
  discovery document worth keeping, but reconciled against current code and
  moved into this plugin's format: a project rule
  ([project-rules.md](project-rules.md)), distributed context, or an
  `## Context identities` / `## Project references` entry — rather than left
  in the old framework's format. Current code describes implemented
  behavior; an approved requirement or decision can describe intended
  behavior that code has not caught up to yet. Keep both where they still
  disagree usefully, and record the discrepancy instead of silently choosing
  one.
- **Replace with an existing plugin capability** — superseded by a specific,
  already-shipped capability of this plugin, with that capability named
  explicitly (a skill, reference, or deterministic helper). Do not assume a
  1:1 command replacement without showing the mapping: what the old command
  or file did, and which skill or reference now covers the same ground.
- **Retire** — superseded or redundant for a reason other than a specific
  named plugin capability (for example, duplicated by another surviving
  document, or describing a decision that no longer applies at all). Retire
  a document only once it is actually superseded or redundant after
  reconciliation; do not keep every discovery document indefinitely by
  default, and do not claim every legacy document has been converted when
  only some have been inspected.
- **Unresolved** — customized beyond the shipped template, or not
  sufficiently understood from available evidence. Leave it alone and say
  why it is unresolved; never fold an unresolved item into a bulk
  retirement.

This five-category list supersedes any narrower prior shorthand (for
example, treating "adapt" and "replace" as one undifferentiated "retire"
bucket): splitting "superseded by this plugin specifically" from "retired
for another reason" keeps the explicit replacement mapping honest, and
"reconcile and migrate" keeps the distinction between a document that is
moving format and one that is simply gone.

Do not delete every path merely because it matches a naming pattern (for
example anything containing `aidlc`). A product's own coordinator repository
or discovery documents are not legacy just because their name contains that
string; classify by actual content and provenance, not by name — this is
the same discipline as "Classify repository role before classifying
components" above, applied one level down to individual files.

Preserve a currently useful security or process control, or identify its
verified replacement, before removing the old one. A prompt instruction
alone is not an executable control and does not replace one; if the old
control was enforced by CI or a Git hook, the replacement must be enforced
the same way, or the gap must be reported, not assumed closed.

## Present one cleanup set, then wait

Present one concrete, named cleanup set for approval — the specific paths to
retire or replace, with the replacement each one maps to, the items being
reconciled and migrated, and the unresolved items left aside. Ask separately
only about a genuine ambiguity the classification could not resolve on its
own; do not ask once per file. Apply the cleanup only after that explicit
approval, and only the items actually approved.

Reuse an approval already given in this run for the same cleanup set and
scope; do not ask again for it. This is the same respected-authorization rule
as [SKILL.md](../SKILL.md) Stage 5 for change sets A and B.

Do not perform cleanup against a real consumer repository as a side effect
of any other request. Context generation (set A) never implies cleanup
authorization (set C); see [SKILL.md](../SKILL.md) Stage 5.

## Mandatory coordinator-retirement decision

When a legacy coordinator repository is identified during a migration,
`sync-context` must surface an explicit retirement decision before it can
report the migration complete. This is a **mandatory decision**, not
mandatory consent to deletion — the user can decline deletion entirely and
the run still reaches a valid, reportable outcome.

Name the exact repository and local path under discussion, then present
exactly three options:

- **A. Migrate and delete.** Migrate the useful content (set A and the
  reconciled set-C items), retire the superseded legacy files, remove the
  coordinator from the workspace, and delete its local checkout — only after
  the checkout-deletion preconditions below all pass.
- **B. Migrate and retain checkout.** Migrate the useful content and remove
  the coordinator from the active workspace (for example, from the
  `.code-workspace` folder list), but keep its local checkout on disk for
  reference. No deletion happens.
- **C. Defer.** Do not retire anything yet. Report that migration cleanup
  for this coordinator remains pending, per [SKILL.md](../SKILL.md) Stage 7.

Call `retirement_decision_pending(recorded_decision, same_run)` in
`scripts/context_tools.py` to decide whether to ask again, mirroring the
existing `bugbot_reprompt_allowed` reprompt pattern:

- No recorded decision (`None`) → always ask.
- A recorded `"defer"` → do not re-ask within the same run
  (`same_run=True`), but it remains pending and is asked again in a later
  run.
- A recorded `"retire-and-delete"` or `"retire-and-retain-checkout"` → never
  re-ask; the decision stands.
- Anything else (an unrecognized value) → treat as not yet decided and ask.

**Three different actions must never be conflated:**

1. Deleting a local checkout (removing the directory from disk).
2. Removing a workspace folder (removing an entry from a `.code-workspace`
   file so the repository no longer appears in the open workspace).
3. Archiving or deleting a *remote* repository (a GitHub/GitLab-hosted
   repository, its history, and its visibility).

This workflow performs only the first two, and only with explicit approval
for the exact target. **Never archive or delete a remote repository as part
of this workflow.** A remote repository's lifecycle is outside
`sync-context`'s authority entirely, regardless of which retirement option
the user picks.

A generic sync approval does not authorize checkout deletion. Local checkout
deletion requires an explicit approval that names that exact target — not
"clean up the old stuff" or an approval given for a different repository.
**Never use wildcard deletion, and never delete every folder matching a
pattern like `*aidlc*`.** Each deletion target is named individually, is
backed by its own classification evidence (see "Classify repository role"
above), and gets its own explicit approval.

**Never delete a shared methodology checkout merely because one engagement
no longer uses it.** A repository classified as a shared methodology
checkout is not a per-engagement coordinator; removing it would affect other
engagements that may still rely on it, which this run cannot see or confirm.
If a repository classifies as a shared methodology checkout, option A is not
available for it in this workflow — route only to option B or C.

## Checkout deletion preconditions

Before performing any approved checkout deletion, verify every precondition
with `checkout_deletion_readiness(...)` in `scripts/context_tools.py`. It
returns an empty tuple only when every precondition passes; otherwise it
returns the specific blocking reasons, and deletion must not proceed while
any reason is present. There is no default that skips a safety argument.

- **`explicit_target` must name one checkout and must match
  `approved_target` exactly.** A missing target, a wildcard or glob such as
  `*aidlc*` (`*`, `?`, or `[`), or a target that does not match what was
  actually approved blocks deletion. A generic or differently-scoped
  approval never satisfies this.
- **`repository_role` must be `product-coordination-repository`.** A shared
  methodology checkout has its own blocking reason. A plugin installation,
  a product source repository, an unresolved role, or any other role is
  also ineligible. Option A is not available for those roles.
- **`migration_confirmed`** — all required content (distributed context,
  reconciled documents, approved project rules) must already be migrated or
  explicitly retained elsewhere before the source is removed.
- **`has_uncommitted_changes`** — inspect staged, unstaged, untracked, and
  relevant ignored assets in the coordinator checkout before deleting it,
  without exposing secrets in the process (do not print `.env` contents or
  other recognized secret files to satisfy this check). Any relevant
  uncommitted content blocks deletion until it is migrated, retained, or the
  user explicitly accepts its loss.
- **`has_unestablished_recovery`** — check for local commits or branches
  that exist only in this checkout and have no established recovery path
  (not pushed to a remote, not otherwise backed up). Blocks deletion while
  true.
- **`retention_established`** — a recoverable retention or backup approach
  must exist before deletion: real Git history on an available remote, or an
  explicit, confirmed backup location. **Never place the only recovery copy
  inside the directory being deleted.** If remote availability or
  recoverability cannot be established from this window, retain the
  checkout and report plainly why deletion is pending, rather than deleting
  on the assumption that a remote exists.
- **`has_active_references`** — set this true when any workspace file or
  repository reference inspected in the authorized scope still points at
  this checkout. True blocks deletion. Disclose the limits of what could be
  checked (for example, a sibling repository that was not open in this
  window cannot be checked) rather than asserting no dependency exists, and
  do not pass false for a scope that was not actually inspected.

## Preserving the workspace file before coordinator removal

A `.code-workspace` file sometimes lives inside the coordinator repository
being retired. Before removing that repository from disk or from the open
workspace, propose an explicit, durable destination for the workspace file —
prefer an existing versioned repository already in scope; ask the user only
if the right destination is genuinely ambiguous. Writing the new workspace
file does not by itself prove Cursor opened it; report only that the file
was written and where, not that it is now the active workspace.

When relocating the workspace file:

- Preserve its other relevant settings, folders, tasks, and launch
  configuration; do not drop fields merely because they were not the focus
  of this migration.
- Recalculate every `folders[].path` entry relative to the new location with
  `relocate_workspace_folder_path(old_workspace_dir, folder_path,
  new_workspace_dir)` in `scripts/context_tools.py`. An already-absolute
  folder path is not joined onto the old workspace directory. Relative and
  absolute inputs must use one coordinate system; a mix raises `ValueError`
  instead of resolving a relative directory through the process working
  directory. This is a pure path computation with no filesystem access, so
  it does not confirm that either directory actually exists on disk. Still
  validate the results below.
- After recomputing paths, validate that each product repository's path
  actually resolves from the new workspace file's location before treating
  the relocation as complete.
- Remove the legacy coordinator's workspace reference only once the
  replacement workspace file is approved and in place.

**Never delete the folder containing the only usable workspace file before
its replacement is available.** If the destination for the relocated
workspace file is not yet confirmed, keep the existing workspace file in
place and report the relocation as pending, rather than removing the old one
first.

## Reviewing a migration in Canvas

Use the shared [canvas review](../../../../references/canvas-review.md) for the proposal and again for the result. A migration does not get a separate Canvas mechanism. The sections below are what that view shows for change set C. Canvas interaction is never deletion approval or retirement approval.

**Before approval**, the Canvas (or its chat-section equivalent) should make
these genuinely readable, not just summarized:

- the repositories in scope and each one's classified role;
- current placement versus proposed placement, per repository;
- files to create, update, move, preserve, or delete, grouped by
  repository;
- a readable preview of each proposed distributed context document, not
  only a file-count summary;
- a readable preview of any `BUGBOT.md` change, consistent with
  [bugbot-configuration.md](bugbot-configuration.md)'s existing
  preserve-and-preview rules;
- the retirement options (A/B/C above) for each identified coordinator, and
  which decisions are still pending;
- unresolved evidence gaps and validation limitations found so far.

**After applying**, refresh the Canvas (or chat sections) from the actual
saved files — read them back rather than re-describing the proposal — grouped
by repository, with paths and readable content, clearly labeled as created,
updated, unchanged, failed, or pending. Report the actual retirement outcome
for each coordinator (migrated and deleted / migrated and retained / deferred)
and link to files where the host supports it.

Do not create a mandatory extra Markdown report or a duplicate artifact
purely to populate the Canvas; the Canvas presents the same proposal and
result objects the chat and the written files already hold. Canvas
interaction (expanding a section, scrolling a preview) is never itself
deletion approval or retirement approval — approval is still the explicit
answer captured in Stage 5.

## Applying a migration in a recoverable sequence

Apply a migration in this order, matching [SKILL.md](../SKILL.md)'s
existing seven-stage pipeline rather than introducing a parallel one:

1. **Discover and inventory** — classify repository roles and individual
   components, per the sections above.
2. **Prepare distributed outputs and workspace updates** — stage the
   proposed context documents, project-rule migrations, and workspace
   relocation as a proposal; do not write anything yet.
3. **Validate and obtain approvals** — run deterministic validation per
   [validation.md](validation.md), request independent review when
   warranted per [review-handoff.md](review-handoff.md), and obtain the
   explicit approvals for sets A, B, and C, including the mandatory
   retirement decision above.
4. **Apply and validate destination files** — write only the approved
   content, recomputing fingerprints immediately before each write per
   [context-generation.md](context-generation.md)'s staleness check, and
   validate the result.
5. **Retire approved legacy instructions and references** — remove only the
   items actually approved for retirement or replacement.
6. **Perform any separately authorized checkout deletion** — only after
   every precondition in "Checkout deletion preconditions" passes for that
   exact target.
7. **Report actual results per repository** — see below.

Recheck source evidence and destination contents immediately before each
write, the same staleness discipline as any other change in this skill; a
proposal prepared earlier in a long migration run can go stale if a user
edits a file mid-run.

**Do not imply an atomic transaction across Git repositories.** Each
repository's migration can succeed, fail, or be skipped independently. On a
partial failure, preserve the old content still needed for recovery in the
repositories that did not complete, and identify plainly what remains
pending — never roll back a repository that already succeeded merely because
a sibling repository failed.

Combine per-repository results with
`migration_outcome(repository_statuses, coordinator_disposition)` in
`scripts/context_tools.py`. Unknown repository states and unknown
dispositions raise `ValueError`; they are not treated as a partial success.
`coordinator_disposition` and the value this function returns are two
different lists. A word that appears in both does not mean the same thing
in both places.

Input, `coordinator_disposition`: `"completed"`, `"retained"`,
`"deferred"`, `"blocked"`, `"unresolved"`, `"not-applicable"`.

Output: `"complete"`, `"retained"`, `"pending"`, `"blocked"`, `"partial"`.

`"pending"` is only an output. `"retained"` as an input means the
adopted-coordinator architecture stays active. `"retained"` as an output
means that choice is what the run reports. `"blocked"` is an input when
deletion cannot proceed, and an output when the run must stop.

- Every repository is `"distributed"` and the disposition is
  `"completed"` or `"not-applicable"` → `"complete"`. `"completed"` covers
  option A (checkout removed) and option B (checkout kept only as a
  historical copy; it no longer acts as the coordinator).
  `"not-applicable"` means this run has no legacy coordinator.
- `"retained"` means the user kept the adopted-coordinator architecture
  active. It is valid only when every repository is
  `"retained-adopted-coordinator"`, and that pair returns `"retained"`,
  not `"complete"`. Pairing `"retained"` with any `"distributed"`
  repository raises `ValueError`.
- Every repository is `"distributed"` and the disposition is `"deferred"`
  or `"unresolved"` → `"pending"`, not `"complete"`.
- Every repository is `"distributed"`, or every repository is
  `"retained-adopted-coordinator"`, and the disposition is `"blocked"`
  (including a deletion whose preconditions failed) → `"blocked"`, not
  `"complete"`.
- Every repository explicitly `"retained-adopted-coordinator"` (the user
  chose to keep that architecture; see artifact-home.md) and the disposition
  is `"completed"`, `"retained"`, or `"not-applicable"` → `"retained"`.
  The same repository states with a deferred or unresolved disposition →
  `"pending"`.
- A mix that includes at least one `"distributed"` repository alongside
  others not yet migrated → `"partial"`, including when the disposition is
  blocked, deferred, or unresolved. This stays `"partial"` even when
  another repository succeeded. Do not imply one transaction across
  repositories.
- No repository statuses at all, or none reaching `"distributed"` or
  `"retained-adopted-coordinator"` → `"blocked"`.

Report the final outcome distinguishing, per repository: distributed
context created, legacy instructions retired, the workspace file updated
and its paths validated, and the coordinator's status (retained by explicit
decision / deletion pending / local checkout removed). **Do not call the
migration complete merely because new Markdown files exist, and do not call
it complete while coordinator retirement is deferred, blocked, or
unresolved.** Completion requires the approved cleanup and, where chosen,
the approved checkout disposition to have actually been applied and
validated.
