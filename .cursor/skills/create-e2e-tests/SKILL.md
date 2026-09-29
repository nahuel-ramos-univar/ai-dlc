---
name: create-e2e-tests
description: Create or update end-to-end tests for a story, acceptance criteria, or user journey. Use when the user asks for browser or end-to-end coverage. Optional and independently invocable.
disable-model-invocation: true
---

# Create end-to-end tests

## Response shape
Follow the shared [compact response style](../../../references/response-style.md).

## Context retrieval
Use [context retrieval](../../../references/context-retrieval.md). Read the selected module context, then the current end-to-end tests, fixtures, and runner config before adding coverage.

## Inputs
Accept a Story, acceptance criteria, a user journey, or a scoped natural-language request. Ask a focused question only when the behavior or the journey boundary is still unclear.

## Workflow
1. Run repository preflight. Confirm the working directory, Git root, and unrelated changes to preserve.
2. Read the existing end-to-end framework, conventions, fixtures, and nearby tests. Reuse them.
3. When no framework exists, propose the smallest setup that matches the repository and stop for approval before adding it.
4. Add or update only the tests that cover the requested journey. Do not embed credentials or secrets. Do not rewrite unrelated tests.
5. Run the applicable tests when the environment and credentials are already available. Report the command and result.
6. When a run is not possible, say exactly what could not run and why. Creating a test is not the same as a successful execution.

## Boundaries
This skill is optional. It is not a mandatory lifecycle stage, and no other skill invokes it automatically. `validate-change` may run end-to-end tests that already exist. It does not run this skill.

Do not commit, push, open a pull request, merge, or deploy. Do not invent a passing result. Do not add a new agent or command wrapper.

## Output
Return the journeys covered, files added or updated, the command that ran or the reason it did not, and any setup that is still waiting for approval.

Read [repository preflight](../../../references/repository-preflight.md) and [skill composition](../../../references/skill-composition.md).
