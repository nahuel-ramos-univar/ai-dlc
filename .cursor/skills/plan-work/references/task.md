# Task

Use this route for work that is not naturally a user-facing Story: technical or supporting work with no genuine user or product outcome of its own.

Do not create a fake persona to force Story wording, for example "As a developer, I want to configure the API Gateway, so that..." when there is no real user outcome behind it. If the work does genuinely deliver a user or product outcome, route it to [single-story.md](single-story.md) instead.

Propose:

- title;
- objective, stated as the technical outcome this work produces;
- reason or context: why this work is needed now;
- parent User Story or Epic, when one applies — see [epic-discovery.md](epic-discovery.md) for a Story or Epic parent recommendation. That parent is a logical relationship ("this Task supports that Story"), not a Jira issue type. When preparing the Jira write, discover the site's hierarchy and let the Product Owner approve the exact issue type: a Jira Subtask under the Story, or a Jira Task linked to the Story. Do not silently change a Task into a Subtask. See [Jira integration](../../../../references/jira-integration.md);
- completion criteria, observable and specific;
- affected area or repository, when known from context already read;
- dependencies;
- validation expectations;
- open questions.

A Task does not require all three hierarchy levels above it. Do not publish a Task with the User Story description template. Keep the Jira mutation boundary in the main skill workflow. Do not run a standalone duplicate search.
