# User Story description template

Offer the template only when preparing the Jira publication payload, after the product content has been drafted and reviewed. Do not offer it while the Product Owner is still answering product questions or while the story is being drafted. The Product Owner may accept it, edit the headings, or decline it.

Record the decision in the artifact home `.ai-dlc-config.md`:

```markdown
## Planning template
- Decision: `approved`
- Source: `plugin-default`
```

Use `approved`, `declined`, or `deferred`. Pass that decision to `decision_reprompt_allowed`. An approved shape is reused. A decline is not offered again unless the Product Owner asks to reconsider. A defer is not offered again in the same run.

If the Product Owner edits the shape, show the edited template and wait for approval before writing it. Save the approved text at `aidlc-docs/planning-template.md` under the artifact home, and record `Source: aidlc-docs/planning-template.md` instead of `plugin-default`. Do not write an absolute local path. A Product Owner-edited template is the approved shape. Do not rewrite it into this default order.

## Authoring rules

Author the description in Markdown. Follow [Jira integration](../../../../references/jira-integration.md). Do not author Jira wiki markup. The Atlassian MCP treats the body as Markdown and converts it on write when that is the available write path. Wiki headings, wiki tables, and status icons are stored as literal text or escaped markers. When writing to Jira, use the format the available tool actually supports. Do not assume a raw Markdown `---` separator renders as a horizontal rule.

Discover the issue type's acceptance-criteria field before the write. Do not hardcode a custom field id. Write each criterion as an observable statement. Do not prefix criteria with status icons. Show the destination in the payload the Product Owner approves. Do not ask for a second approval of an "exception."

- Identified and writable: put business acceptance criteria only in that field. Omit the Acceptance Criteria heading below.
- Confirmed absent: include the Acceptance Criteria heading below as the Description fallback. A Product Owner-edited template must still carry every approved criterion.
- Exists but not writable, incomplete metadata, or access error: do not treat the field as absent. Report the limitation and agree the destination inside the approved payload.
- Never publish operational disclaimers about Jira fields, MCP, or fallback inside the ticket.

This skeleton is for a User Story. Do not wrap a Task or an Epic in the "As a …" line. A Task uses [task.md](task.md). An Epic uses [feature-or-epic.md](feature-or-epic.md).

When filling the skeleton:

- Start with the user-story line. Do not add a Description heading above it.
- Separate sections with Markdown `---`, surrounded by blank lines, in this skeleton.
- Replace a bracket with approved content when it exists.
- Preserve optional headings with reader-facing placeholders when approved content is absent. Do not omit an empty optional heading. This supersedes the previous omit-empty-optional-sections presentation rule.
- Optional-section placeholders are not requirements or readiness blockers. Never invent content to fill them. Never replace actual unresolved questions with them.
- Actor, capability, benefit, and Acceptance Criteria placeholders must never count as completed or approved requirements. Handle missing required content through the existing planning flow. Do not invent it.
- Validation Notes may add a business-level scenario that exercises an existing acceptance criterion, per [single-story.md](single-story.md), "Testing and validation expectations." It must not introduce new product behavior. If the approved Story has no such note, keep the heading and placeholder. Do not paraphrase the acceptance criteria.
- Technical notes are known constraints in business language. Hand implementation detail to `refine-story`. If none were approved, keep the heading and placeholder.
- Scope / Out of Scope publishes an approved boundary that is not already an Acceptance Criterion, per [single-story.md](single-story.md). Do not invent scope or exclusions. Do not copy Acceptance Criteria into this section. If none were approved, keep the heading and placeholder.
- Goals & Metrics publishes a Story-specific outcome or measure, per [single-story.md](single-story.md), "Story-specific goals and metrics." Do not invent one. If none was approved, keep the heading and placeholder.
- Design / References publishes a Story-level design reference already in the approved Story, per [single-story.md](single-story.md), "Design reference." Do not discover, infer, or inspect a design here. Retrieval happens while drafting or updating the proposal. If none was approved, keep the heading and placeholder.
- Keep Stakeholder Questions as a Question / Answer table. Put real unresolved questions in that table. Do not replace them with the placeholder row.
- Keep Acceptance Criteria last in Description only when Description is the approved destination for acceptance criteria. If a dedicated field is used, do not duplicate that section. Omit the Acceptance Criteria heading from Description in that case.
- Do not invent goals, metrics, dependencies, risks, scope, exclusions, or a design reference.
- If a custom Product Owner template is the approved shape, use that shape. Preserve all approved Story content. When stable criterion identifiers are authorized, propose how they fit that shape; do not overwrite the custom template.

This template renders the approved Story model; it does not define it. It keeps optional headings with reader-facing placeholders when approved content is absent. It may omit a restatement that would only duplicate content already published in another field of the same payload, such as Acceptance Criteria. Deduplication is allowed only when meaning and traceability are preserved. It must not infer or introduce product behavior, a goal, a metric, a validation expectation, a dependency, a risk, a design reference, a scope boundary, or any other semantic content that is absent from the approved Story proposal. It must preserve every meaningful approved requirement, boundary, unresolved question, dependency, and reference. Formatting and placeholders must not cause information loss.

## Default description

```markdown
As a [user], I want [capability], so that [benefit].

---

#### 🎯 Context

[Add background a reader needs, if applicable]

---

#### 📌 Scope / Out of Scope

- **In scope:** [Add an in-scope boundary, if applicable]
- **Out of scope:** [Add an out-of-scope exclusion, if applicable]

---

#### 🎨 Design / References

[Add a story-specific design reference, if applicable]

---

#### 💬 Stakeholder Questions

| Question | Answer |
| --- | --- |
| [Open question] | [Answer, or "open"] |

---

#### 🛠️ Technical Notes

[Add confirmed technical constraints, if applicable]

---

#### 🧪 Validation Notes

[Add additional business validation guidance, if needed]

---

#### 📊 Goals & Metrics

[Add a story-specific goal or metric, if applicable]

---

#### 🔗 Dependencies & Risks

- **Dependency:** [Add a dependency, if applicable]
- **Risk:** [Add a risk, if applicable]

---

#### ✅ Acceptance Criteria

- [Observable result 1.]
```

This prose line is human-readable context, not the operative relationship. An approved dependency is also created as a real Jira issue link at publication time — see [Jira integration](../../../../references/jira-integration.md), "Dependencies as issue links." The two are not duplicates: the link is what Jira actually tracks, this text explains it in the story's own words.

## Acceptance criteria field

When the issue type has a writable acceptance-criteria field, put this content in that field, not under Description:

```markdown
- [Observable result 1.]
- [Observable result 2.]
```

When identifiers are authorized for a new publication, prefix each criterion with a local id such as `AC-01`. Preserve ids that already exist. Do not renumber an existing ticket silently.

When that field is confirmed absent, use the Acceptance Criteria heading in the Description skeleton above instead. Do not write both. If the field exists but is not writable, agree the destination in the approved payload rather than assuming Description. Do not add a sentence in the ticket explaining why.
