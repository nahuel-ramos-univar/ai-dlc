# Risk and specialist handoffs

Use **fast** depth for well-understood, reversible, isolated changes. Independent implementation review is optional.

Use **standard** depth when behavior, contracts, regressions, or cross-component impact may change. Request an independent `implementation-reviewer` assessment before validation.

Use **deep** depth for security, identity, infrastructure, payments, data integrity, destructive operations, public/shared contracts, or substantial uncertainty. Request an independent review and involve `governance-reviewer` when applicable.

The main chat may use an `implementer` for bounded frontend, backend, infrastructure, integration, or testing work. Give the agent its objective, boundaries, baseline, paths, acceptance criteria, dependencies, constraints, expected output, validation responsibility, and stop conditions. Avoid concurrent edits to the same path.

Use agents only when the host supports independent delegation. They must return concise findings with file references and uncertainty. Do not create mandatory reports merely because a specialist ran.

Choose a model only through a verified supported configuration. If unavailable, recommend a depth and let the user choose.
