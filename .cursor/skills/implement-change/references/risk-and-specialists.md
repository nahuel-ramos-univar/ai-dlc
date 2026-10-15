# Risk and specialist handoffs

Use **fast** depth for well-understood, reversible, isolated changes. Independent approach review is optional.

Use **standard** depth when behavior, contracts, regressions, or cross-component impact may change. Independent approach review still runs only when [implement-change](../SKILL.md) finds a material new decision, uncertainty, or a relevant change against the already-reviewed design.

Use **deep** depth for security, identity, infrastructure, payments, data integrity, destructive operations, public or shared contracts, or substantial uncertainty. Identify required approvals. Dedicated governance integration is deferred. Approach review still requires that material-new-decision trigger. Presence of Terraform or IAM (identity and access management) files is not enough.

When that trigger holds, the main chat requests `implementation-reviewer` in **approach review mode** before writing code, waits for the result, and treats it as a gate on the affected scope. The reviewer receives the approved refinement, current code evidence, and the proposed approach. It returns risks, alternatives, blocking findings, and pending decisions. Resolve those blockers before editing the gated scope. If the review is unavailable, leave that scope pending unless an explicit applicable policy permits an exception. Independent work may continue only when it does not depend on that decision. The reviewer does not review the later implementation diff. After code exists, Bugbot coordination belongs to `validate-change`. Do not use this reviewer as a substitute for Bugbot.

The main chat may use an `implementer` for bounded frontend, backend, infrastructure, integration, or testing work. Give the agent its objective, boundaries, baseline, paths, acceptance criteria, dependencies, constraints, expected output, validation responsibility, and stop conditions. Avoid concurrent edits to the same path.

Use agents only when the host supports independent delegation. They must return concise findings with file references and uncertainty. Do not create mandatory reports merely because a specialist ran.

Choose a model only through a verified supported configuration. If unavailable, recommend a depth and let the user choose.
