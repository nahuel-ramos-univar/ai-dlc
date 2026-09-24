# Compact chat response style

## Scope

This rule applies only to the assistant's chat-facing reply: status updates, questions, summaries, and handoffs. It reduces chat output tokens. It is not a content budget.

Do not apply this rule to file contents or other deliverables. Code, tests, generated Markdown, design artifacts, acceptance criteria, Jira payloads, review findings, commands, diagrams, changelogs, and evidence must contain the detail needed for correctness. Do not omit a requirement, test case, finding, constraint, or evidence merely to make a chat reply shorter.

## Chat replies

Default to a concise answer that starts with the outcome or decision. Use no more than five bullets unless the user asks for detail or the workflow needs a complete approval payload.

Do not repeat the request, narrate routine tool work, paste logs, or restate unchanged fields. Link to relevant files or issue keys instead of copying their content. Mention only evidence, assumptions, risks, blockers, and next actions that affect the decision.

Use a short status line for an in-progress workflow. Ask one focused question only when its answer changes scope, approval, or safety.

Keep exact field names, acceptance criteria, commands, issue keys, and external change payloads intact. For an approval, partial failure, security concern, or failed validation, include the necessary detail even when it exceeds the normal compact shape.

Offer deeper detail on request: "I can provide the evidence, full diff, or complete payload."
