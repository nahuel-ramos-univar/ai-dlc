---
name: scaffold-project
description: Establish an approved minimal technical foundation for a new project. Use when the user asks to scaffold, bootstrap, or set up a new application project.
disable-model-invocation: true
---

# Scaffold project

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Workflow
1. Inspect the requested destination, existing files, project configuration, and unrelated changes. Do not assume the current directory is the project root. Discover an existing Git root and remotes with local Git. Do not initialize Git, clone, or create a remote.
2. Identify the requested application type and technologies already decided. Ask only questions needed to define a minimal foundation. Read [project onboarding](../../../references/project-onboarding.md) only when project references are missing, ambiguous, or explicitly being reconsidered. This is an instruction for the current run, not a conditional loader. `parse_project_references`'s `"invalid"` status is also a gap, not a confirmed value — treat it the same as missing or ambiguous. `"ok"` only means the fields that are present passed syntax checks; do not treat a missing optional board or Figma reference as a reason to ask every onboarding question again. Include confirmed conventions in the proposal below. Do not start `sync-context` to repeat that step.
3. Resolve whether this is a single repository, a monorepo, or a new repository meant to sit alongside others as part of one product. Membership for the *new* project comes only from the explicit request, existing configuration that already applies to it, context already confirmed earlier in this session, or a focused confirmation question when none of those resolve it — never from location alone. Ask only when none of those already establish it; do not ask when the user already said "add a repo to the X product." A destination that happens to sit next to a sibling repository with a confirmed `Product` label, or that shares a directory-name prefix with one, is a discovery hint worth surfacing in that one focused question, never automatic membership on its own -- an adjacent folder is not evidence of product membership by itself. For a new repository joining an existing product, agree on its components, its responsibility relative to the siblings, and its target location before proposing files.
4. If an application already exists, propose a bounded addition or stop for clarification. Never overwrite existing files or changes.
5. Present a short proposal: destination, stack, repository structure, files or components to create, intended local validation, the initial context artifacts this scaffold will generate (a repository index and, for each created module, concise module context -- see [context-generation.md](../sync-context/references/context-generation.md) and [context-templates.md](../sync-context/references/context-templates.md), reused rather than reinvented here), and, when this scaffold is part of a multi-repository product, the planned `Product` label and `Related repository` entries (per [artifact-home.md](../sync-context/references/artifact-home.md)) and whether a local multi-root `.code-workspace` would help. Mark every component this proposal does not actually create as planned, not implemented or verified -- a proposal describing three repositories when only one is being scaffolded now must say so plainly, and the same separation applies to context: propose generating context only for what this run actually creates, never for a sibling or a not-yet-written component.
6. Obtain approval for that exact proposal before writing.
7. Create only the approved foundation, including a `.code-workspace` file when approved -- preserve any existing one's unrelated settings, tasks, and comments (treat it as JSONC, not plain JSON) rather than overwriting it wholesale. Generate the repository index and module context the proposal named, scoped to the files this run actually created -- one meaningful module context per real, approved module, never one per arbitrary directory. Reuse the existing context-generation conventions and size budget ([context-generation.md](../sync-context/references/context-generation.md)); do not invent a second context format for a scaffolded project. For a destination with no Git root or remote yet, do not initialize Git and do not fabricate a canonical remote or a verified repository identity to make an artifact look complete -- follow the existing unversioned-context convention for what can be truthfully written now, and explicitly defer any artifact that needs an identity this destination does not have yet, naming the missing prerequisite in the output. Do not launch `sync-context` from inside this skill to perform this generation; this skill writes the initial context directly, reusing the same references. Include a concise README with actual setup and validation instructions.
8. Run relevant available checks. Report each as passed, failed, or unable to run, with the reason.

## Boundaries
Preserve user files and changes. Follow existing project conventions when present.
Do not implement business features; create Jira work; initialize or restructure Git;
commit, push, open a PR, merge, deploy, or provision infrastructure; generate
credentials or write secrets. Do not add authentication, databases, containers,
continuous integration, or end-to-end testing unless the approved scope includes it.
Approval of a prose project rule does not authorize dependency installation or
CI changes. A missing Figma or Jira reference does not block a local scaffold.
Do not fabricate a remote URL or a persisted repository identity for a
repository that has no Git root yet; a folder without a Git root is not yet a
verified Git repository. If recording a confirmed `Related repository` entry
would need a canonical remote that does not exist yet, defer that one field,
proceed with the rest of the approved scaffold, and report the prerequisite
plainly instead of inventing a value. Do not launch another `sync-context`
session from inside this skill; reuse [artifact-home.md](../sync-context/references/artifact-home.md)
and [repository preflight](../../../references/repository-preflight.md)
directly.

Do not claim a named slash command ran automatically. If a later context sync or
validation would help, describe it honestly as a next step.

## Output
Return the approved scope, files created, actual validation results, preserved
content, the initial context artifacts actually generated (clearly separated
from any deferred artifact and the missing prerequisite that deferred it), and
any other deferred work.

Read [repository preflight](../../../references/repository-preflight.md) for Git
classification, authorization, and preservation rules,
[artifact-home.md](../sync-context/references/artifact-home.md) for the
`Product` and `Related repository` convention this skill reuses rather than
inventing its own,
[context-generation.md](../sync-context/references/context-generation.md) and
[context-templates.md](../sync-context/references/context-templates.md) for
the initial repository-index and module-context format and size budget this
skill reuses rather than inventing its own, and
[skill composition](../../../references/skill-composition.md). The
context-discovery write list does not apply to approved scaffold files, except
that the `.code-workspace` write still follows the bounded conditions in
[repository preflight](../../../references/repository-preflight.md).
