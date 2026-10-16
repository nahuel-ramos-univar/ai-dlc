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
1. Run [repository preflight](../../../references/repository-preflight.md). Confirm the working directory, Git root, and unrelated changes to preserve. Do not inspect a repository that is not in the authorized scope merely because it sits nearby.
2. Discover the environment before assuming one. Inspect existing tests, the runner and its config, start/build/test scripts, README and development docs, fixtures and authentication helpers, secret-free env examples, CI, and Docker or Compose when they exist. Do not print or persist secrets. Follow [end-to-end environment](../../../references/e2e-environment.md).
3. Classify the run: a locally executable application, an application already deployed to a confirmed Dev or QA target, a local UI with a simulated backend, or coverage that can be authored but cannot currently execute. A configuration file does not prove the environment works and does not authorize remote execution. Ask only for an unresolved choice that materially affects the work.
4. Reuse the existing framework. When none exists, propose the smallest setup that matches the repository and stop for approval before adding it. Playwright is a candidate for a web UI, not a universal requirement. Do not force browser tests onto a service with no UI. Reuse the runner's native configuration before inventing a wrapper.
5. Add or update only the tests and files that the requested journey needs. Do not invent selectors, routes, or UI behavior that does not exist. Do not embed credentials or secrets. Keep auth state and sensitive artifacts out of Git. Do not rewrite unrelated tests.
6. Keep authoring distinct from installing dependencies or browsers, starting services, and running tests. Do not ask again when the current request already authorizes the action. For remote execution, confirm the authorized target, test data, expected effects, and cleanup first. Having a URL or credentials does not authorize mutations. Do not run against production by default.
7. Run the applicable tests when scope and environment allow. Report the command and result. Identify simulated-backend tests as such. Creating a test is not the same as a successful execution. Proposed coverage is not an executable suite.
8. When a run is not possible, say exactly what could not run and why, and which checks were still possible.

## Boundaries
This skill is optional. It is not a mandatory lifecycle stage, and no other skill invokes it automatically. `validate-change` may run end-to-end tests that already exist. It does not run this skill.

Reuse Docker or Compose only when it already exists and is relevant. A test-runner container is not the application stack. Propose a new container only for a concrete need inside the approved scope. Do not install Docker or introduce a cloud emulator by default.

Do not commit, push, open a pull request, merge, or deploy. Do not invent a passing result. Do not add a new agent or command wrapper.

## Output
Return the environment class, journeys covered, files added or updated, the command that ran or the reason it did not, whether a simulated backend was used, any setup still waiting for approval, and remaining execution requirements.

Read [end-to-end environment](../../../references/e2e-environment.md), [repository preflight](../../../references/repository-preflight.md), and [skill composition](../../../references/skill-composition.md).
