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
  `document_metrics`. It is the repository-index hard gate only. Default
  `max_lines` is 150, matching `aidlc-docs/repository-context.md` in
  [context-templates.md](context-templates.md). Do not call it as a module
  validity gate. Inside `validate_generated_context`, `index:budget` reports
  `"failed"` over 150 lines. Module line count is not a validation result;
  call `document_metrics` and report `lines` plus the 300-line advisory
  guideline as a metric, never as passed or failed. A line budget on the
  index is a measurable property; whether a module document is *complete*
  is not something this module can measure.
- **Required structure.** Confirm exactly one well-formed
  `<!-- AI-DLC:generated:start -->` / `<!-- AI-DLC:generated:end -->` block,
  and confirm the required heading (`## Identity and scope` for a module,
  `## Scope` for the repository index) is inside that block. A heading
  outside the block does not count. Missing, repeated, nested, or unclosed
  markers fail this check. Fenced examples are ignored, including example
  headings and example marker strings.
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
  `parse_recorded_fingerprint(document_text)`. It reads only a canonical
  field line inside the one generated block and inside that document type's
  metadata section (`## Scope` for a repository index, `## Identity and
  scope` for a module): a line that is exactly `` - Fingerprint: `<16 hex>` ``,
  or exactly `` - Baseline and fingerprint: `<git revision>` / `<16 hex>` ``.
  A sentence that merely contains "fingerprint" or "fingerprinted" is not a
  field. Duplicate canonical fields are ambiguous even when the values match.
  Missing generated markers are "missing"; the parser does not scan the rest
  of the document. Repeated or malformed marker pairs are not a silent choice
  of one block. It never mistakes a Git revision for a fingerprint. Its
  `status` is `"ok"`, `"missing"`, `"malformed"`, or `"ambiguous"`. Recompute the current value with `content_fingerprint(scope_root)`
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
index_repository_id=None, index_budget=150, module_budget=300,
candidate_content=None)` runs every check above against one repository index
and its linked module documents, and returns a list of
`ValidationCheck(name, status, detail)`. `status` is one of:

- `"passed"` — the check ran and the property held.
- `"failed"` — the check ran and the property did not hold.
- `"unresolved"` — the check could not be completed: missing configuration,
  an inaccessible repository, or a parsing failure. Never treat this as
  passing.
- `"not_applicable"` — the check does not apply here, for example an
  external link, or a repository-wide fingerprint on an index whose
  generated `## Scope` declares `Index: \`multi-repository\``. Omitting
  `--index-repository-id`, or passing more than one `--root`, does not make
  an index multi-repository. A single-repository index is identified by
  `Repository ID` in that section (optionally with
  `Index: \`single-repository\``). A supplied `--index-repository-id` must
  match that field. A conflict fails. Missing or duplicate identity metadata
  is unresolved, and that run does not return exit code 0.

Index rows are also checked against each module document's `Repository ID`,
`Module ID`, and `Source` inside its generated metadata. Freshness is
computed only after those three agree. A fallback document may live outside
the source directory. A Modules-table Context target must be a local,
authorized, readable file. A URL or a same-document anchor is not a
substitute, and the check fails without fetching anything. A `#fragment`
on that local path is allowed. An external link in ordinary documentation
or in `## Evidence and existing docs` is different: it stays
`not_applicable` when it is explicitly unverified. `missing` and
`unresolvable` references fail. A directory target fails instead of being
read as text. `unavailable` and an unresolved repository identity stay
`unresolved`.

A generated repository index has exactly one live `## Scope` and exactly
one live `## Modules`. A generated module document has exactly one live
`## Identity and scope`. A second copy fails even when the text matches.
Headings inside backtick or tilde fences, and headings outside the
generated block, are not that copy. When the metadata section is
ambiguous, identity and fingerprint are not reported as passed. An
ambiguous freshness check is not a successful freshness check.

`## Evidence and existing docs` path references are checked too. A bullet
that is only a Markdown link is resolved relative to the context document.
A bullet that is only `` `repository-relative/path` `` is resolved in the
row's owning repository. A bullet that is only `` `repository-id:relative/path` ``
is resolved in that authorized repository. A backtick symbol name, or prose
with inline code, is not a path. A passing evidence check means the path
resolved inside an authorized root (`evidence reference resolves`); it does
not prove the file supports the surrounding claim. An evidence section
with no path references is `not_applicable` (`no path references to
resolve`), not passed. A missing evidence section is also
`not_applicable`. Every module row's Context cell must be a local
readable context file; an empty Context cell fails (`module row requires
a local context file`). An empty Modules table is a valid index-only
representation.

Do not treat missing configuration, an inaccessible repository, or a parsing
failure as passing or `not_applicable`. This function is read-only: it never
writes, moves, or deletes a document.

## Validating a proposal before it is written

`candidate_content` is an optional, minimal mapping from a document's
intended final absolute path to its proposed text:
`{final_absolute_path: proposed_document_text}`. Before that text is
accepted, each destination is checked. It must resolve inside an authorized
root, which may be the source repository or an explicitly authorized
coordinator. A missing file and missing parent directories inside that root
are allowed. An existing destination must be a regular file: a directory, a
symlink, a symlink escape, or a file sitting where a parent directory is
required fails validation. Two entries that resolve to the same destination
fail instead of one being chosen silently. The mapping does not add an
authorized root and does not write anything.

When a destination passes that check and `index_path` or a linked module's
resolved path is a key, that text is validated as if it already existed at
that path — including resolving links between two mapped candidates —
without writing anything. An unmapped target still falls back to the real
file on disk. A Git discovery failure while comparing a fingerprint is
`unresolved`, not a crash and not a pass.

This is not a general-purpose virtual filesystem: it only changes what text
is read for the specific paths supplied. Presence in the mapping never
authorizes writing it — that approval and the actual write happen later, in
the `sync-context` workflow's Stage 5 and Stage 6.

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
  [--index-repository-id <repo-id>] [--index-budget 150] \
  [--candidate <final-absolute-path>=<staged-file> ...]
```

`--module-budget` is still accepted so older invocations do not fail; it
does not produce a check. Module line count is a metric from
`document_metrics`, not a validation result.

To check a proposal before writing it, write each proposed document's text to
a temporary staging file, then pass `--candidate
<final-absolute-path>=<staged-file>` once per proposed document (repeatable).
`<final-absolute-path>` is where the document would live once applied; it is
read only to resolve links and compute identity, never written to.
`<index-path>` itself may be a `--candidate` final path for a brand-new index
that does not exist on disk yet.

Exit code `1` means at least one check failed. That takes precedence when
failed and unresolved checks are both present. Exit code `2` means no check
failed, but at least one is unresolved, or the arguments are invalid. Exit
code `0` means every check passed or was not applicable. Incomplete
validation must never look like a clean success. Report the exit code and
every individual check result; do not summarize a mixed run as simply
"passed."

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
