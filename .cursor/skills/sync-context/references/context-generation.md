# Context generation

Read [artifact-home.md](artifact-home.md) before selecting output paths. Confirm
the artifact home, source repository root, requested module scope, and approved
module roots before writing. Write only under:

- `<artifact-home>/aidlc-docs/` (change set A)
- `<artifact-home>/.ai-dlc-config.md` (change set A, and the decisions for B).
  An approved `## Project references` update belongs in this same file, after
  `## Context identities`. It is not a separate config file. A missing or
  present project-references section does not change identity parsing.
- `<approved-module-root>/AIDLC_CONTEXT.md` (change set A)
- after the per-repository Bugbot approval in
  [bugbot-configuration.md](bugbot-configuration.md) (change set B):
  `<source-root>/.cursor/BUGBOT.md` and
  `<approved-boundary-root>/.cursor/BUGBOT.md`
- after the per-policy approval in [project-rules.md](project-rules.md)
  (change set B): `<source-root>/.cursor/rules/<slug>.mdc`, one file per
  confirmed policy, never a copy of this plugin's own skills, agents, or
  shared references

Nothing here authorizes change set C (legacy migration cleanup); that
remains its own approval per [legacy-migration.md](legacy-migration.md).

A plugin source directory inside another Git repository is not automatically the
consumer root. Do not write other Markdown in source trees. A nested tracked
module uses its owning Git root for the baseline, but preserves the requested
module as the analysis scope. An unversioned tree may be analyzed with baseline
`unversioned`; save only when its artifact home and write scope are clear.

## Proposal staleness before applying

A proposal prepared in an earlier stage of the same run can go stale before
it is applied: a user may edit a destination file, or source evidence may
change mid-conversation. Immediately before writing, recompute
`content_fingerprint` for the proposal's declared source scope and read the
current content of each destination file. Call `proposal_is_current` with
the fingerprint and destination text captured when the proposal was
prepared, and with the values just read. If it returns false, stop writing
that part of the proposal, recalculate the affected changes, preserve the
intervening edit, and present the material difference for renewed approval
before writing. Do not silently overwrite a destination
file that moved since the proposal was prepared.

Keep `.ai-dlc-config.md` minimal. Keep `aidlc-docs/repository-context.md` as a short workspace index. It lists each actual Git root, its repository ID, meaningful modules, source paths, freshness marker, and links to colocated context. It is not a codebase dump.

Use `<module-root>/AIDLC_CONTEXT.md` for useful modules. A module has an architectural responsibility: app, API, service, shared package, or infrastructure stack. Do not infer a module from directory depth. A small single-module repository keeps one concise repository context and no manufactured module file. Do not create one context file per source file or directory; generate module context only where it provides useful, distinct information beyond the repository index.

If the source repository or module root cannot be written, use the documented
fallback `<artifact-home>/aidlc-docs/context/<repo-id>/<module-id>.md` and link
it from the repository index. A read-only source remains analyzable. If no
writable artifact home exists, return a draft or proposal and do not claim files
were saved.

Generate IDs from stable, portable identity for the index and fallback only:

- Reuse an existing persisted repository ID first.
- Otherwise derive a first-time ID from a verified canonical remote. Normalize
  only known equivalent SSH and HTTPS forms. Remove credentials. Combine a
  readable slug with a short hash of the full canonical identity so similar
  remotes do not collide.
- Detect an ID collision against IDs already stored in the artifact home before
  writing fallback paths or Bugbot decisions.
- If no remote is usable, assign an explicit ID once and persist it in the
  artifact-home configuration.
- Never derive identity from absolute paths, clone directory names, workspace
  collisions, or changing responsibility labels.
- Preserve a module ID across a source move when evidence links the old and new
  module. Report ambiguous duplicate documents rather than deleting them.

Reject IDs outside `[a-z0-9-]`. Never use raw user input as a path. Record
repository-relative source paths and the verified remote when available. Do not
write absolute local checkout paths into generated context.

Each module `AIDLC_CONTEXT.md` states repository identity, source paths, responsibility, entry points, interfaces, callers or dependencies, verified tests and commands, constraints, evidence paths, freshness, and explicit unknowns. Do not copy source, generated output, vendor content, cache content, or secrets.

Ground a material claim about architecture, behavior, integrations, configuration, security boundaries, or testing in source evidence: a repository-relative path plus the relevant symbol or configuration key. Avoid relying only on a line number, because it goes stale. A test file proves that test code exists, not that it passed. A CI configuration proves that a job is configured, not that it ran successfully. A declared dependency does not prove runtime usage. A configured integration does not prove authenticated connectivity. Repository documentation supports evidence; it does not automatically override current code.

Distinguish a verified fact, an inference labeled as such, and an unresolved unknown. Do not list an assertion under Unknowns when the same or another generated document already states it as a verified fact elsewhere; that is a contradiction, not an unknown. For each material unknown, state briefly what remains unknown, what evidence is missing, and how it could be verified. Where code and documentation conflict, record the discrepancy rather than silently choosing a narrative. Skip a generic unknown that is irrelevant to the module's own responsibility.

Never describe all tracked or fingerprinted files as examined, analyzed, or verified merely because their paths were listed by Git or included in a fingerprint. Reading a manifest does not verify every component it lists; reading part of a file does not verify the whole file. State the repository index's `Examined` field as the boundaries and representative paths actually inspected, not a count of tracked or fingerprinted files.

Freshness is a deterministic content fingerprint of the declared source scope
and its examined paths. Use `scripts/context_tools.py`:

1. For a Git-backed scope, discover included files with Git: every tracked
   path (`git ls-files`) plus every untracked path `.gitignore` does not
   exclude (`git ls-files --others --exclude-standard`). A tracked file is
   still included even if a later-added ignore pattern would exclude it if
   it were untracked; only an untracked-and-ignored file is left out. For a
   genuinely unversioned tree, walk the filesystem instead. A Git query
   failure for a Git-backed scope raises; it is never silently replaced by
   the filesystem walk.
2. Sort normalized repository-relative paths.
3. Hash each file's path and SHA-256 content hash with NUL delimiters.
4. Hash that sequence with SHA-256 and record the first 16 hexadecimal
   characters.
5. This is a working-tree snapshot: each included file's content hash comes
   from the bytes currently on disk, not from the Git index. If a file's
   staged content differs from its current working-tree content, this
   fingerprint reflects only the working tree; call
   `staged_working_tree_divergence` to report that difference separately —
   never describe this fingerprint itself as covering staged content.
6. Exclude generated context (`AIDLC_CONTEXT.md`, `.ai-dlc-config.md`,
   `aidlc-docs/`, and `.cursor/BUGBOT.md`), `.git`, nested Git checkouts,
   caches, build output, vendor directories, recognized secret files
   (`.env` and non-template `.env.*`, key/certificate files), and symlinks
   outside authorized roots. Include committed templates such as `.env.example`.
   Do not exclude product source under `.cursor/skills` or `.cursor/rules`.
7. If the declared scope is missing, is not a directory, or the walk or Git
   query fails for a reason other than "not a Git repository," do not
   record a fingerprint. Treat freshness as unavailable.

Record declared scope separately from examined files. The helper discovers
additions, deletions, and renames inside scope through the current sorted file
set. Recheck affected evidence when a source or contract changes during
analysis; otherwise report a mixed snapshot as uncertain. A Git root or nested
tracked module records its owning root revision plus the fingerprint. An
unversioned tree records `unversioned` plus the fingerprint. Never use a parent
revision that does not track the examined files.

Refresh only modules affected by changed paths, requested scope, or stale
evidence. Preserve human-authored sections. If a safe merge is unclear, show a
targeted diff. Current code and contracts override a stale summary. Create
`integration-map.md` only for verified cross-module or cross-repository
dependencies. Link existing ADRs when relevant; never invent one.

Use [context-templates.md](context-templates.md) for generated structure and
size budgets. Generated sections may refresh in place. Preserve human-authored
sections. Existing documents without ownership markers receive a targeted merge
proposal. Remove a deleted module only from active navigation after evidence;
never delete its document blindly. A second sync without relevant changes must
produce no content changes.

When creating a new generated context document, use minimal ownership markers:

```markdown
<!-- AI-DLC:generated:start -->
<!-- generated facts and links -->
<!-- AI-DLC:generated:end -->
```

Only content inside those markers may refresh automatically. Human text outside
them is preserved. Do not retrofit markers into an existing human-authored
document without showing a targeted proposal first.

## Examples

Single-module repository:

```text
aidlc-docs/
  repository-context.md
```

`repository-context.md` identifies the Git root, `src/`, entry point, tests, evidence revision, and unknowns. No module file is created.

Monorepo:

```text
aidlc-docs/
  repository-context.md
apps/
  storefront/
    AIDLC_CONTEXT.md
services/
  orders/
    AIDLC_CONTEXT.md
```

Multi-repository workspace (two Git roots; keep one engagement artifact home
when the user authorized it, even if that home is not itself a Git root):

```text
engagement/                       # authorized artifact home
  aidlc-docs/
    repository-context.md
    integration-map.md            # only after a verified web-to-payments contract
web/                              # Git root
  apps/
    storefront/
      AIDLC_CONTEXT.md
payments/                         # Git root
```

If `payments/` is itself a small single-module repository, keep context in its index and do not create `payments/AIDLC_CONTEXT.md`.
