# Independent context review

`context-reviewer` is a read-only agent that checks generated or updated
repository context against current source. It does not replace deterministic
validation, and a result of no findings does not prove the entire repository
context is correct; it reports findings within the scope it was given.

## When to request review

Request an independent `context-reviewer` assessment for:

- initial context generation for a repository or workspace;
- a material architectural or module-boundary change;
- a shared contract or cross-module integration change;
- a context migration or substantial restructuring;
- significant conflicting evidence between code and prior context, or
  material uncertainty;
- an explicit user request.

Do not trigger review solely by file count or number of changed lines. For a
small factual update with no material boundary change, deterministic
validation plus targeted source checking can be enough. State plainly that
independent review was skipped and why.

## Handoff contents

Give the reviewer:

- repository or workspace identity and the declared scope;
- the generated or changed context documents, with their diff against the
  prior version when one exists;
- relevant source paths and affected module boundaries beyond the snippets
  the main chat already selected, so the reviewer can find omissions;
- known inspection limitations recorded during generation;
- the deterministic validation result from [validation.md](validation.md).

Do not pass the entire main-chat conversation by default. For an initial
generation, the reviewer independently inspects enough representative
source to challenge the proposal: the generated documents, their
material claims, and omitted boundaries. Do not blindly re-scan every
file. For an incremental change, focus the reviewer on changed claims,
affected modules, and relevant shared boundaries; do not require a second
exhaustive repository scan for every minor update.

## Expected findings shape

```text
Review scope:
- Documents and source areas inspected.

Findings:
- Severity: blocker | major | minor
- Dimension: accuracy | completeness
- Context document and section.
- Incorrect, unsupported, or missing assertion.
- Source evidence.
- Recommended correction.

Limitations:
- What could not be verified.

Result:
- No findings within reviewed scope.
- Changes required.
- Review incomplete.
```

**Accuracy** findings are about a claim that does not match the source: a
coverage row marked `verified` with no matching evidence, a stale behavior
description, an incorrect dependency. **Completeness** findings are about
what the document should cover for this module's actual responsibility but
does not: an omitted consumer, a missing runtime flow, a coverage table
with no row for a dimension this module plainly has. See
[context-quality.md](context-quality.md) for the dimension list and what
"good enough" means for each.

An honestly marked `unknown` or `not applicable` row is not itself a
finding. Only report it when the state is wrong — the dimension was
actually inspected and should read `verified` or `partial`, or `not
applicable` has no real reason behind it.

## Resolving findings

The main chat owns corrections. It applies confirmed findings, then reruns
the affected deterministic checks and source inspection. It may disagree with
a finding, but must cite the source evidence supporting that decision. Use at
most one targeted follow-up review for unresolved major findings or a
material correction; if problems remain after that, report them clearly and
ask the user for a decision instead of looping indefinitely.

A result of "no findings within reviewed scope" covers only that scope.
Never report it as proof the whole repository context is correct.

## Delegation reality

An agent Markdown file under `agents/` is configuration, not proof that a
callable dispatch API exists. Use `context-reviewer` through the host's
actual supported delegation; do not invent a tool name, a `subagent_type`
value, or a slash command for internal dispatch. If the host exposes only a
general-purpose independent subagent and cannot invoke a named plugin agent
directly, hand it the `context-reviewer` agent file as bounded task context
and report the result as a general-purpose independent review, not native
named-agent dispatch. If the host cannot run an independent subagent at all, continue with
deterministic validation. Report independent semantic review as
unavailable and quality assurance as partial. Clearly labeled self-review
may continue drafting; it is not equivalent to independent review and must
not be reported as fully reviewed, quality verified, or complete semantic
review. For an initial/full sync or a material architecture change, still
show the proposal, disclose the unavailability, and require explicit user
approval before persistence. Do not add an extra approval prompt for a
small factual update or a no-op, and never call main-chat self-review
independent. Do not claim this delegation path was tested beyond
what was actually invoked in this session.
