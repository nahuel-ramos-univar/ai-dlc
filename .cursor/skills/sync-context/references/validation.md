# Deterministic validation

Run these checks with `scripts/context_tools.py` before treating generated or
refreshed context as final. Each check confirms a measurable property, not
semantic correctness. A passing result never proves an Unknown is accurate,
that a described dependency is correct, or that a claim is well-supported.
Those judgments belong to independent review; see
[review-handoff.md](review-handoff.md).

## Authorized roots: the multi-repository model

Every check that resolves a link or a source path takes an explicit
`authorized_roots` mapping: repository ID to that repository's actual root
path on this machine (`dict[str, Path]`). Build this mapping from the
`Root:` field recorded per repository under `## Context identities` in
`.ai-dlc-config.md` (see [artifact-home.md](artifact-home.md)), resolved
against the artifact home.

This mapping is never guessed from the filesystem, and it is never treated as
"the whole filesystem is authorized." A reference that resolves outside every
mapped root — including through `..` segments or a symlink — is rejected as
`"unresolvable"`, not silently accepted. `authorized_roots` holds real
absolute machine paths only in the running validator's memory for that one
run. Do not write an absolute local path into `.ai-dlc-config.md`,
`AIDLC_CONTEXT.md`, or any other portable generated document.

## Checks

- **Line budget.** `check_document_budget(path, max_lines)` counts lines with
  `document_metrics`. Use 150 for `aidlc-docs/repository-context.md` and 300
  for a module context or fallback document, per
  [context-templates.md](context-templates.md).
- **Required structure.** Confirm the generated document still has its
  required headings (`## Identity and scope` for a module, `## Scope` for the
  repository index) inside the `<!-- AI-DLC:generated:start -->` /
  `<!-- AI-DLC:generated:end -->` markers. A missing heading means a merge
  dropped content; do not report the document as current.
- **Workspace references.** For every link in the repository index's Modules
  table, resolve it with `resolve_markdown_links(index_path, authorized_roots)`.
  It returns one of five states per link: `"ok"` (resolves inside an
  available authorized root), `"missing"` (the owning root is available but
  the target does not exist there), `"unavailable"` (the target's configured
  root is not an accessible directory), `"unresolvable"` (the target falls
  outside every authorized root after resolving symlinks and `..` segments —
  this is the traversal/escape rejection, treat it the same as missing, never
  as passing), or `"external"` (a URL or a same-document anchor, not verified
  here).
- **Declared source paths.** For each `(repository_id, relative_path)` pair
  in a Modules table's `Source` column together with its row's repository
  identity, resolve it against **its own owning repository**, never against
  the artifact home, with `resolve_source_path(repository_id, relative_path,
  authorized_roots)` or in bulk with `find_stale_source_paths(entries,
  authorized_roots)`. States: `"ok"`, `"missing"` (repository available, path
  is not), `"unavailable"` (the repository's configured root is not an
  accessible directory), `"unresolved"` (`repository_id` is not in
  `authorized_roots` at all — an unresolved repository identity, distinct
  from a missing file), and `"unresolvable"` (the path escapes its own
  repository root).
- **Fingerprint metadata and freshness.** Parse the recorded fingerprint with
  `parse_recorded_fingerprint(document_text)`. It reads only the canonical
  field inside the `<!-- AI-DLC:generated:start/end -->` block and inside
  that document type's metadata section (`## Scope` for a repository index,
  `## Identity and scope` for a module): a standalone `` - Fingerprint:
  `<16 hex>` `` line, or a combined `` - Baseline and fingerprint: `<git
  revision>` / `<16 hex>` `` line. It never mistakes a Git revision for a
  fingerprint (the two field shapes require an exact 16-hex-character token)
  and never reads a human note, an unrelated mention of the word, or a fenced
  example outside that section. Its `status` is `"ok"`, `"missing"`,
  `"malformed"` (a fingerprint-labeled line that matches neither canonical
  shape), or `"ambiguous"` (more than one differing candidate, or a
  well-formed field alongside a malformed one) — never a silent pick among
  candidates. Recompute the current value with `content_fingerprint(scope_root)`
  over the document's declared scope and compare. A mismatch means the
  document is stale for that scope; it does not by itself mean the prose is
  wrong, and a match does not by itself mean the prose is right. If a format
  or algorithm change makes a previously recorded baseline incompatible with
  the current parser, report that the baseline needs regeneration; do not
  silently claim it is still comparable.
- **Section-aware Modules table.** Read a column with
  `extract_table_column(markdown_text, heading, column)`. It stops at the
  next heading of the same or higher level, so a missing table under
  `## Modules` never falls through into a different section's table, and it
  ignores fenced-code examples, so a documented example table is never read
  as live data. Its `status` is `"ok"` (`values` holds that column, which may
  be empty for a deliberately empty table), `"missing_section"`,
  `"missing_table"`, `"malformed_table"` (invalid separator row or a data
  row whose cell count does not match the header — reported, never silently
  dropped), or `"missing_column"`. Only `"ok"` is safe to treat as real data.
- **Duplicate module identity.** A module is never identified globally by
  `module_id` alone. `find_duplicate_identities(module_ids, repository_ids)`
  flags a duplicate `(repository_id, module_id)` pair; two different
  repositories may each declare a module named `api` without that being a
  duplicate. When the index is genuinely single-repository, call it with
  `repository_ids=None` and derive that single identity only from an
  unambiguous declared scope — never guess it in a multi-repository
  workspace.
- **Duplicate outputs.** `find_duplicate_context_targets(context_cells,
  markdown_path)` resolves every Modules-table `Context` link and flags
  targets shared by more than one row, even when two entries spell the same
  file differently (for example `apps/web/AIDLC_CONTEXT.md` versus
  `./apps/web/AIDLC_CONTEXT.md`).
- **Generic duplicate values.** `find_duplicate_values(values)` is a small
  general-purpose helper for a flat list with no repository or path
  structure; prefer the two checks above for Modules-table data.

## Aggregate entry point

`validate_generated_context(index_path, authorized_roots,
index_repository_id=None, index_budget=150, module_budget=300)` runs every
check above against one repository index and its linked module documents, and
returns a list of `ValidationCheck(name, status, detail)`. `status` is one of:

- `"passed"` — the check ran and the property held.
- `"failed"` — the check ran and the property did not hold.
- `"unresolved"` — the check could not be completed: missing configuration,
  an inaccessible repository, or a parsing failure. Never treat this as
  passing.
- `"not_applicable"` — the check does not apply here, for example an
  external link, or a top-level fingerprint comparison for a true
  multi-repository engagement index that has no single owning repository
  (pass `index_repository_id=None` for that case).

Do not treat missing configuration, an inaccessible repository, or a parsing
failure as passing or `not_applicable`. This function is read-only: it never
writes, moves, or deletes a document.

## Running it

Do not assume `scripts/context_tools.py` exists relative to the target
repository's current working directory — it does not; it ships inside this
plugin's own installation. Resolve it relative to a file you already loaded
from this skill. From this skill's own reference files (for example this
file, `references/validation.md`), the script is four directories up, then
into `scripts/`: `../../../../scripts/context_tools.py`. From `SKILL.md`
itself, it is three directories up: `../../../scripts/context_tools.py`. If
you loaded either file by absolute path, use that same absolute path's parent
plugin root instead of a relative guess.

```bash
python3 <resolved-path-to>/context_tools.py validate <index-path> \
  --root <repo-id>=<repo-root> [--root <repo-id>=<repo-root> ...] \
  [--index-repository-id <repo-id>] [--index-budget 150] [--module-budget 300]
```

Exit code `0` means every check passed or was not applicable. Exit code `1`
means at least one check failed. Exit code `2` means at least one check was
unresolved (or the arguments themselves were invalid) — incomplete validation
must never look like a clean success. Report the exit code and every
individual check result; do not summarize a mixed run as simply "passed."

## Boundaries

These checks are read-only and mechanical. They do not confirm that an
Unknown is accurate, that a described dependency is correct, that a claim is
well-supported, or that a coverage statement matches actual inspection depth.
Do not build a keyword-matching system on top of these checks that claims to
catch semantic contradictions; that is what `context-reviewer` is for, and a
clean deterministic run does not prove semantic correctness. Report each
check's result explicitly, including when a reference is unresolved because
the path or repository is unavailable; never report an unavailable reference
as successfully verified.
