# Deterministic validation

Run these checks with `scripts/context_tools.py` before treating generated or
refreshed context as final. Each check confirms a measurable property, not
semantic correctness. A passing result never proves an Unknown is accurate,
that a described dependency is correct, or that a claim is well-supported.
Those judgments belong to independent review; see
[review-handoff.md](review-handoff.md).

## Checks

- **Line budget.** `check_document_budget(path, max_lines)` counts lines with
  `document_metrics`. Use 150 for `aidlc-docs/repository-context.md` and 300
  for a module context or fallback document, per
  [context-templates.md](context-templates.md). A failing result reports the
  actual line count; never truncate silently or split into arbitrary numbered
  fragments to hide it.
- **Required structure.** Confirm the generated document still has its
  required headings (`## Identity and scope` for a module, `## Scope` for the
  repository index) inside the `<!-- AI-DLC:generated:start -->` /
  `<!-- AI-DLC:generated:end -->` markers. A missing heading means a merge
  dropped content; do not report the document as current.
- **Root-to-module links.** For every link in the repository index's Modules
  table, resolve it with `resolve_markdown_links(index_path, repo_root)`.
  `"missing"` means the target file does not exist. `"unresolvable"` means
  the link escapes the repository root; treat that the same as missing, never
  as passing. `"external"` (a URL or an anchor) is not verified here.
- **Source-reference paths.** For repository-relative paths listed under an
  `Evidence and existing docs` section, confirm each exists with
  `find_stale_source_paths(paths, repo_root)`. A path inside an external
  repository or an unavailable workspace is reported as unresolved, never as
  verified.
- **Fingerprint comparison.** Parse the recorded fingerprint with
  `parse_recorded_fingerprint(document_text)` and recompute it with
  `content_fingerprint(scope_root)` over the document's declared scope. A
  mismatch means the document is stale for that scope; it does not by itself
  mean the prose is wrong, and a match does not by itself mean the prose is
  right.
- **Deleted or renamed modules.** Compare each Modules-table `Source` cell
  (read with `extract_table_column(index_text, "## Modules", "Source")`)
  against the working tree with `find_stale_source_paths`. A missing source
  path means that module entry needs removal from active navigation or an
  update to its new path. Never delete the linked document blindly; report
  the discrepancy first.
- **Duplicate outputs.** Extract the Modules-table `Module` column with
  `extract_table_column` and pass it to `find_duplicate_values`. A duplicate
  module ID means two entries reference the same module by accident.

## Boundaries

These checks are read-only and mechanical. They do not confirm that an
Unknown is accurate, that a described dependency is correct, that a claim is
well-supported, or that a coverage statement matches actual inspection depth.
Do not build a keyword-matching system on top of these checks that claims to
catch semantic contradictions; that is what `context-reviewer` is for. Report
each check's result explicitly, including when a reference is unresolved
because the path or repository is unavailable; never report an unavailable
reference as successfully verified.
