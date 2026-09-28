# Context generation

Read [artifact-home.md](artifact-home.md) before selecting output paths. Confirm
the artifact home, source repository root, requested module scope, and approved
module roots before writing. Write only under:

- `<artifact-home>/aidlc-docs/`
- `<artifact-home>/.ai-dlc-config.md`
- `<approved-module-root>/AIDLC_CONTEXT.md`
- after the per-repository Bugbot approval in `bugbot-configuration.md`:
  `<source-root>/.cursor/BUGBOT.md` and
  `<approved-boundary-root>/.cursor/BUGBOT.md`

A plugin source directory inside another Git repository is not automatically the
consumer root. Do not write other Markdown in source trees. A nested tracked
module uses its owning Git root for the baseline, but preserves the requested
module as the analysis scope. An unversioned tree may be analyzed with baseline
`unversioned`; save only when its artifact home and write scope are clear.

Keep `.ai-dlc-config.md` minimal. Keep `aidlc-docs/repository-context.md` as a short workspace index. It lists each actual Git root, its repository ID, meaningful modules, source paths, freshness marker, and links to colocated context. It is not a codebase dump.

Use `<module-root>/AIDLC_CONTEXT.md` for useful modules. A module has an architectural responsibility: app, API, service, shared package, or infrastructure stack. Do not infer a module from directory depth. A small single-module repository keeps one concise repository context and no manufactured module file.

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

Freshness is a deterministic content fingerprint of the declared source scope
and its examined paths. Use `scripts/context_tools.py`:

1. Sort normalized repository-relative paths.
2. Hash each file's path and SHA-256 content hash with NUL delimiters.
3. Hash that sequence with SHA-256 and record the first 16 hexadecimal
   characters.
4. Include relevant staged, unstaged, and selected untracked source because the
   helper reads the current working tree.
5. Exclude generated context (`AIDLC_CONTEXT.md`, `.ai-dlc-config.md`,
   `aidlc-docs/`, and `.cursor/BUGBOT.md`), `.git`, nested Git checkouts,
   caches, build output, vendor directories, recognized secret files
   (`.env` and non-template `.env.*`, key/certificate files), and symlinks
   outside authorized roots. Include committed templates such as `.env.example`.
   Do not exclude product source under `.cursor/skills` or `.cursor/rules`.
6. If the declared scope is missing, is not a directory, or the walk fails,
   do not record a fingerprint. Treat freshness as unavailable.

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
