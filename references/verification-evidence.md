# Verification evidence

Shared by `/implement-change` and `/validate-change`. Keep this in the existing
approach, handoff, and closing report. Do not create a verification-plan file
or a per-run Markdown report.

Static contract tests in this plugin do not prove that an agent ran this
workflow.

## Approach and handoff

Include, briefly:

- the behavior and contracts being changed;
- runtime, commands, and tooling actually found in the authorized scope;
- required dependencies and configuration;
- which components the planned checks exercise, and which they replace;
- what can be verified in the environment that is available now;
- what needs a different environment or a dependency that is not available.

Do not assume a cloud provider, a container runtime, a local stack, or a
hosted Git forge. Use what the repository already has.

## What a check proves

Mocks are valid for a bounded unit of logic. A test does not prove behavior
it replaced with a fake.

Distinguish:

- isolated logic;
- connected components composed together;
- integration with a real client, adapter, or request contract;
- execution against a deployed environment.

Passing tests that inject fakes in place of the code under validation do not
prove that composition, configuration, or a deployed integration works.

When the change touches an external client, adapter, configuration, or
request contract, say which related risk the existing tests still leave
uncovered. When that risk is concrete, prefer a local check of real
composition and configuration, with I/O intercepted at the appropriate
boundary — a project-appropriate stub, recorded response, or equivalent.
Do not replace the implementation being validated merely to make a suite
green. Do not impose a mocking library, SDK, cloud vendor, or emulator.

Do not require connected-component or client checks for a trivial change
with no related risk. Do not ask for cloud credentials or a deploy to
prove something that is verifiable on this host.

## External failures

When the change touches a client, adapter, or request contract, check the
expected failure behavior already specified by:

- the approved acceptance criteria;
- existing public contracts, for example an OpenAPI document, a schema, or a
  documented error response;
- relevant failures of the modified client or adapter, for example a timeout,
  refused authentication, or an error shape callers already depend on.

Do not require catching every exception. Do not invent a new error contract.
Do not limit the check to failures a Jira field listed verbatim. If the
expected outcome is undefined and a public contract would change, record the
pending decision instead of guessing.

## Dependencies and setup docs

When the change introduces a required dependency or configuration, declare it
in the project's existing install mechanism. Keep existing scripts, examples,
and setup documentation consistent with that declaration. Do not generate
extra generic documentation when an existing setup place already exists.

## Development tests and a separate QA item

A separate QA item does not remove this development work's duty to add the
unit and integration tests the change needs.

`/implement-change` may update an existing end-to-end spec when the authorized
behavior requires it, even if the user did not name those files. Do not add a
new journey, a first suite, or a framework. Do not weaken assertions. New
end-to-end authorship is a `/create-e2e-tests` handoff. Naming that skill does
not execute it.

Running an end-to-end test that already exists may be part of
`/validate-change`. That skill does not generate a new suite and does not
start `/create-e2e-tests`.

## Baseline before edits

Before editing, discover existing relevant tests and coverage. Run the
pertinent checks when they can run on this host. Record observed failures and
the code state they belong to. If a baseline could not be obtained, say that
limitation. Do not reset, clean, or move unrelated changes to obtain a
baseline.

## After the change

Run the new or updated tests. Run the affected existing regression. Include
consumers and shared contracts the change can affect. Run the full suite when
that is reasonable. Use a justified subset when the suite is expensive, not
pertinent, or depends on an environment that is not available. Do not expand
tests indefinitely without a concrete risk.

## Failures

Do not call a failure pre-existing without evidence. Distinguish:

- a regression this change introduced;
- a pre-existing failure, with the baseline evidence;
- an environment problem;
- an uncertain result.

Fix regressions introduced inside the authorized scope. Do not delete tests,
add skips, weaken assertions, or update snapshots only to get a green
result. Change existing expectations only when the behavior change is
approved, and say why.

`validate-change` assesses whether the evidence is sufficient. It does not
only rerun the author's suite.

## Close-out

The closing report distinguishes:

- new behavior verified, and what the checks actually exercised;
- regression executed, and its scope;
- pre-existing failures;
- checks that failed or did not run;
- independent review or Bugbot status, and the code state reviewed;
- limitations that affect delivery.

Name the regression that actually ran. Do not claim the change broke nothing
outside that scope.
