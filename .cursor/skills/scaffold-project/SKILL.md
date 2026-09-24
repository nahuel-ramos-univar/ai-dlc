---
name: scaffold-project
description: Establish an approved minimal technical foundation for a new project. Use when the user asks to scaffold, bootstrap, or set up a new application project.
disable-model-invocation: true
---

# Scaffold project

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Workflow
1. Inspect the requested destination, existing files, project configuration, and unrelated changes. Do not assume the current directory is the project root.
2. Identify the requested application type and technologies already decided. Ask only questions needed to define a minimal foundation.
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

Do not claim a named slash command ran automatically. If a later context sync or
validation would help, describe it honestly as a next step.

## Output
Return the approved scope, files created, actual validation results, preserved
content, and any deferred work.

Read [repository preflight](../../../references/repository-preflight.md) for Git
classification, authorization, and preservation rules, and
[skill composition](../../../references/skill-composition.md). The
context-discovery write list does not apply to approved scaffold files.
