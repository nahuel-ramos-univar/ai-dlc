# Discovery and incremental refresh

Use code and versioned contracts as current evidence. Pick one internal mode.

## Initial discovery

Use initial discovery when the repository index or usable module context is
missing, when the user asks for a full refresh, or when the prior baseline
cannot be compared. Identify meaningful modules from workspace configuration,
manifests, deployment boundaries, entry points, contracts, and test structure.
Inspect representative source and relevant dependencies. Do not require a dirty
diff and do not read every source file by default.

Record examined paths, declared scope, and unknowns. “Initial discovery
completed” means only that the recorded scope was examined; it never means the
whole repository was read. Never equate a Git listing or a fingerprint's file
set with having examined, analyzed, or verified every one of those files;
inventoried, inspected, and verified are different evidence levels and the
generated record must not blur them.

## Incremental refresh

Use incremental refresh only when usable prior context exists. Compare its
recorded baseline and fingerprint to current source plus staged, unstaged, and
relevant untracked changes. Refresh affected modules and index entries.
Expand to downstream consumers when shared contracts, packages, configuration,
or interfaces change. Detect new, removed, and renamed files or modules. If the
old baseline is unavailable, use bounded rediscovery instead of claiming
freshness.

Preserve unchanged content and avoid timestamp-only rewrites.

Each repository or module context record must include:

- repository path and, when the consumer is a Git root or nested tracked path,
  that Git root's revision;
- a freshness fingerprint of examined source paths; generated context files do
  not participate in that hash;
- relevant uncommitted modifications, without copying sensitive values;
- paths examined and direct dependencies;
- observed facts versus assumptions;
- a freshness boundary such as "valid for `src/payments/**` at revision `abc123`, fingerprint `a1b2c3d4`" or, for an unversioned tree, "unversioned; fingerprint `a1b2c3d4` for `services/checkout/**`".

Do not use a parent repository revision as freshness when that revision does not track the examined files.

The fingerprint algorithm is `content_fingerprint` in `scripts/context_tools.py`: a deterministic SHA-256 over each examined file's repository-relative path and content hash, truncated to 16 hexadecimal characters. For a Git-backed scope, `iter_fingerprint_files` discovers the included files with Git — every tracked file plus every untracked file `.gitignore` does not exclude — so an ignored-and-untracked file never enters the hash, and a tracked file is never dropped merely because a later ignore rule would have excluded it if it were untracked; for a genuinely unversioned tree it walks the filesystem instead. A directory that has a `.git` marker, including a nested module of that checkout, is not unversioned when Git cannot read the metadata: that failure is reported instead of falling back to the walk. A Git query failure for a Git-backed scope raises rather than silently falling back to that walk. The fingerprint detects a change in the included inputs; it does not prove semantic accuracy or that every file was fully inspected. It is a working-tree snapshot: each included file's content hash comes from the bytes currently on disk, never from the Git index. A recorded Git revision by itself does not cover uncommitted working-tree changes, so the fingerprint reflects the actual working tree rather than only the last commit — but it does not separately reflect staged (Git index) content. When a file's staged content differs from its current working-tree content, report that with `staged_working_tree_divergence`; never describe the fingerprint itself as covering staged content. If the prior baseline is missing or incompatible with the current scope, perform a fresh scoped inspection and report that limitation rather than reusing a stale comparison. Generated context files never enter their own source fingerprint, so refreshing context never invalidates itself on the next run.

### Staged versus working-tree divergence

A file can be staged (added to the Git index) and then edited again before
commit, so its staged content and its current on-disk content differ.
`content_fingerprint` never sees the staged copy, only the working tree.
Call `staged_working_tree_divergence(scope_root)` to list the
repository-relative paths where this applies, and report them separately
from the freshness fingerprint — never resolve the difference silently in
either direction. An empty result means Git checked and found no
difference. If the helper raises `GitDiscoveryError`, report the
staged-versus-working-tree comparison as unavailable. Do not describe
that failure as no difference.

Compare the previous module source paths with the paths found now using
`diff_module_sources`. Report added and removed paths explicitly. Do not
treat two different paths as a rename unless other evidence links them.

Summarize availability with `scope_verification_status`. `"complete"` is
allowed only when every requested scope was available. Any unavailable
repository, submodule, or dependency is `"partial"` or `"unavailable"`,
never a claim that the whole scope is current.

## No relevant changes

Classify the recorded fingerprint with `classify_fingerprint_change`, then
combine it with the other change sets using `context_sync_outcome`. Missing
evidence is not a successful no-op.

- `"unavailable"` — no usable prior fingerprint. This is first-time
  generation or an incompatible baseline, not "no relevant changes."
- `"unchanged"` — change set A needs no rewrite, no Canvas, and no approval.
  Still evaluate pending work in set B (Bugbot and project rules) and set C
  (legacy cleanup). Respect a declined decision, and do not re-prompt an
  unchanged deferred proposal in the same run. Existing approval covers only
  its recorded scope and content.
- `"changed"` — set A needs a proposal.

`context_sync_outcome(context_change, bugbot_pending, project_rule_pending,
legacy_cleanup_pending)` returns `"no_relevant_changes"` only when set A is
`"unchanged"` and sets B and C have no actionable work. That is the only
full no-op: no writes and no new approval question. It returns
`"context_current_migration_pending"` when set A is unchanged but B or C
still has work, and `"relevant_updates_found"` otherwise. An unchanged
context fingerprint must not end the run while B or C still has work.

## Submodules and unavailable related repositories

A nested `.git` marker is not proof of a real Git submodule; confirm against
`.gitmodules` with `is_declared_submodule` before treating a nested path
differently from an ordinary nested repository. A declared submodule that is
not checked out, is detached, or is otherwise unreachable from the current
window produces **partial status** for that specific path: report exactly
what could and could not be verified for it, continue the rest of the sync
where it is safe to do so, and never report the whole scope as current
because the unavailable part was skipped.

Preserve human-authored content where it does not conflict with source. Flag and
refresh a stale summary; code and contracts remain authoritative. Do not scan
vendor, build, cache, generated, or inaccessible sibling directories.

Do not create an integration map for imports within one module. Create it only after observing a dependency across services, repositories, deployable systems, or a public contract boundary.

ADRs record approved architectural decisions. Discovery alone is not an ADR trigger.
