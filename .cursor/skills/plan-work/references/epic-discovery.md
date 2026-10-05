# Parent discovery for a new Story or Task

When drafting a new User Story, find the right Epic to attach it to rather than leaving the relationship unresolved or guessing from word overlap. When drafting a new Task, find the most specific right parent instead: an existing or newly-defined User Story when the Task genuinely supports one, and an Epic directly only when no such Story applies — see [task.md](task.md), which allows either.

1. State the product capability (for a Story) or the supporting purpose (for a Task) this item represents in one sentence.
2. Search Jira using the Jira integration contract: Epics for a Story; both Stories and Epics for a Task. If no Jira project is confirmed for this engagement, report that as a limitation and hand off to `/sync-context`; do not run project onboarding from inside this skill.
3. For each candidate, read enough to judge fit: title, summary, description, objective, labels or components, status, and already-declared scope.
4. Compare the strongest candidates on semantic and product fit, not on matching words. Do not attach a Story to an Epic, or a Task to a Story or an Epic, merely because titles share terms.
5. Report one of:
   - a strong match, with a short explanation of why it fits;
   - several plausible candidates, with the ambiguity stated so the Product Owner decides, not an arbitrary pick;
   - no reasonable fit, with a recommendation to define a new Epic — help define it if the Product Owner wants to proceed, but do not create it without explicit approval.

This step does not run a general semantic search for a duplicate Story. If an exact matching issue is already referenced by the user, or is found naturally while reading a candidate's existing scope, do not propose creating an obvious duplicate of it; that is this step's only duplicate-safety responsibility.
