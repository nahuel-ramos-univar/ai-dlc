# End-to-end environment

Shared by `/create-e2e-tests`, `/validate-change` when an end-to-end check is
in play, and `/implement-change` when existing end-to-end coverage is
modified or executed — including baseline, regression, and a required spec
update. Discover the project's own setup. Do not assume a local application,
a deployed environment, Docker, or a cloud account.

Do not print or persist secrets. Do not inspect a repository that is not in
the authorized scope merely because it sits nearby.

## Discover before assuming

Inside the authorized scope, inspect what is already there:

- existing end-to-end tests and the runner;
- runner configuration;
- start, build, and test scripts;
- README and development documentation;
- fixtures and authentication helpers;
- environment-variable examples that do not contain secrets;
- CI configuration, and Docker or Compose, when they exist;
- related components that the approved scope already includes.

A configuration file does not prove that the environment works. It does not
authorize remote execution. Inspect the test command and runner configuration
to tell whether a check is end-to-end and which environment it targets. A
locally invoked runner can still point at a remote Dev or QA URL. Apply the
remote-execution rules below before that run. Reuse an authorization already
given in this session.

## Environment classes

Classify the run as one of:

- a locally executable application;
- an application already deployed to a confirmed Dev or QA target;
- a local UI with a simulated backend;
- coverage that can be authored but cannot currently execute.

Ask only for an unresolved choice that materially affects the work. Reuse a
decision already confirmed in this session. Do not repeat onboarding.

## Runner and setup

Reuse the existing framework. When none exists, propose the smallest setup
that matches the repository and wait for approval. Playwright is a candidate
for a web application with a UI. It is not a universal requirement. Do not
force browser tests onto a service with no UI.

Reuse the runner's native configuration before inventing a wrapper or a
plugin-owned environment schema.

When Playwright is the chosen framework:

- keep `baseURL` configurable;
- use `webServer` only when this run should start local services;
- add projects and fixtures only when they separate a real concern;
- use locators and assertions based on observable application behavior;
- wait on conditions, not arbitrary sleeps;
- isolate data and sessions so tests do not depend on each other;
- do not use retries to hide a deterministic failure.

Propose only the files that are needed: runner config, specs, fixtures,
package-manager scripts, secret-free env examples, Git ignore entries for
auth state and sensitive artifacts, and a short update to existing
documentation. Keep auth state and sensitive artifacts out of Git.

Do not invent selectors, routes, or UI behavior that does not exist. Proposed
coverage is not an executable suite. Discovery or compilation of a spec is
not a passing journey.

## Authoring versus execution

Keep these distinct:

- creating or updating tests and configuration;
- installing dependencies or browsers;
- starting services;
- running tests against an environment.

Authorization can come from the current request and session. Do not ask again
when that authorization already covers the action.

For remote execution, confirm the authorized target and scope first.
Establish test data or accounts, expected effects, and cleanup. Having a URL,
credentials, or access does not by itself authorize mutations. Do not run
against production by default. Do not create real orders, send
communications, or delete data by implication.

If the tests cannot run, name the concrete missing requirement and the
checks that were still possible. Tests that use a simulated backend must be
identified as such. They are not full integration.

`/create-e2e-tests` owns new journeys, a first suite, and framework setup. It
may execute when scope and environment allow. `/implement-change` may update
an existing end-to-end spec when the authorized behavior requires it, even if
those files were not named, and may run existing end-to-end coverage during
baseline or regression. It does not add a new journey, a first suite, or a
framework, and it does not start `/create-e2e-tests`. `/validate-change` may
run end-to-end tests that already exist and are relevant. It does not generate
a new suite and does not start `/create-e2e-tests`. Naming another skill does
not execute it.

## Docker

Reuse Docker or Compose when it already exists and is relevant. A browser
test-runner container is not the application or dependency stack. Propose a
new container only for a concrete need inside the approved scope. Do not
install Docker. Do not introduce a cloud emulator or a full stack by default.
If a Playwright image is proposed, keep it consistent with the project's
Playwright version. Do not stop unrelated services or delete volumes when a
test finishes.
