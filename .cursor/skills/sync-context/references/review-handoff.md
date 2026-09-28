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
generation, the reviewer inspects the generated documents and their material
claims. For an incremental change, focus the reviewer on changed claims,
affected modules, and relevant shared boundaries; do not require a second
exhaustive repository scan for every minor update.

## Expected findings shape

```text
Review scope:
- Documents and source areas inspected.

Findings:
- Severity: blocker | major | minor
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
named-agent dispatch. If the host cannot run an independent subagent at all,
continue with deterministic validation and clearly labeled self-review,
report independent review as unavailable, and never call main-chat
self-review independent. Do not claim this delegation path was tested beyond
what was actually invoked in this session.
