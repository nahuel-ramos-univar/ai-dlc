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
3. If an application already exists, propose a bounded addition or stop for clarification. Never overwrite existing files or changes.
4. Present a short proposal: destination, stack, repository structure, files or components to create, and intended local validation.
5. Obtain approval for that exact proposal before writing.
6. Create only the approved foundation. Include a concise README with actual setup and validation instructions.
7. Run relevant available checks. Report each as passed, failed, or unable to run, with the reason.

## Boundaries
Preserve user files and changes. Follow existing project conventions when present.
Do not implement business features; create Jira work; initialize or restructure Git;
commit, push, open a PR, merge, deploy, or provision infrastructure; generate
credentials or write secrets. Do not add authentication, databases, containers,
continuous integration, or end-to-end testing unless the approved scope includes it.
Approval of a prose project rule does not authorize dependency installation or
CI changes. A missing Figma or Jira reference does not block a local scaffold.

Do not claim a named slash command ran automatically. If a later context sync or
validation would help, describe it honestly as a next step.

## Output
Return the approved scope, files created, actual validation results, preserved
content, and any deferred work.

Read [repository preflight](../../../references/repository-preflight.md) for Git
classification, authorization, and preservation rules, and
[skill composition](../../../references/skill-composition.md). The
context-discovery write list does not apply to approved scaffold files.
