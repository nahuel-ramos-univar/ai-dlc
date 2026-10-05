# Single Story

Ask about the user outcome, primary actor, observable success, exclusions, and open business questions. Do not ask implementation, schema, deployment, or test-runner questions.

Use the outcome-oriented form "As a [user or actor], I want [capability], so that [outcome]" when it fits the work. Do not force technical work into fake user-story wording; route that to [task.md](task.md) instead.

Propose:

- title;
- story statement or objective;
- business or user value;
- recommended parent Epic — see [epic-discovery.md](epic-discovery.md);
- scope;
- acceptance criteria expressed as observable, testable behavior; Given/When/Then is optional, not mandatory;
- relevant scenarios;
- exclusions;
- dependencies;
- assumptions and technical constraints, clearly labeled;
- validation or testing expectations, where appropriate;
- source or traceability: what evidence this item is based on;
- any obvious duplicate noticed incidentally while inspecting a candidate parent or an explicitly referenced issue. Do not run a standalone duplicate search.

Do not invent behavior purely to make the acceptance criteria look complete; leave unresolved behavior as an explicit open question instead. Technical constraints should explain the impact in business language. Hand implementation details to `refine-story`.

Do not fill or offer [jira-story-template.md](jira-story-template.md) while drafting. That template is a publication-payload step in the main skill, after the product content has been drafted and reviewed. Keep acceptance criteria out of the Jira description when that payload is prepared.
