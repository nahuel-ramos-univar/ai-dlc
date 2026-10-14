# User Story description template

Offer the template only when preparing the Jira publication payload, after the product content has been drafted and reviewed. Do not offer it while the Product Owner is still answering product questions or while the story is being drafted. The Product Owner may accept it, edit the headings, or decline it.

Record the decision in the artifact home `.ai-dlc-config.md`:

```markdown
## Planning template
- Decision: `approved`
- Source: `plugin-default`
```

Use `approved`, `declined`, or `deferred`. Pass that decision to `decision_reprompt_allowed`. An approved shape is reused. A decline is not offered again unless the Product Owner asks to reconsider. A defer is not offered again in the same run.

If the Product Owner edits the shape, show the edited template and wait for approval before writing it. Save the approved text at `aidlc-docs/planning-template.md` under the artifact home, and record `Source: aidlc-docs/planning-template.md` instead of `plugin-default`. Do not write an absolute local path.

## Authoring rules

Author the description in Markdown. Follow [Jira integration](../../../../references/jira-integration.md). Do not author Jira wiki markup. The Atlassian MCP treats the body as Markdown and converts it on write. Wiki headings, wiki tables, and status icons are stored as literal text or escaped markers.

Acceptance criteria are not part of the description. Jira keeps them in the issue type's acceptance-criteria field. Discover that field from the issue type before the write. Do not hardcode a custom field id. Write each criterion as an observable statement. Do not prefix criteria with status icons.

If that field is missing, keep the criteria in the local proposal and say the field was not found. Do not copy them into the description unless the Product Owner explicitly chooses that exception for this write.

This skeleton is for a User Story. Do not wrap a Task or an Epic in the "As a …" line. A Task uses [task.md](task.md). An Epic uses [feature-or-epic.md](feature-or-epic.md).

When filling the skeleton:

- Replace every bracket with real content, or omit that line.
- Do not publish placeholder text.
- Omit a section that has no real content; do not render an empty heading.
- Testing / Validation Notes is an optional business-level scenario or condition that helps exercise an existing acceptance criterion, per [single-story.md](single-story.md), "Testing and validation expectations." It must not introduce new product behavior. Omit it when it would only restate or paraphrase the acceptance criteria.
- Technical notes are known constraints in business language. Hand implementation detail to `refine-story`.
- Scope / Out of Scope is included only when the approved Story carries a scope or exclusion that is not already fully expressed as an Acceptance Criterion, per [single-story.md](single-story.md). Do not invent scope or exclusions. Do not copy Acceptance Criteria into this section. Omit it when absent.
- Goals & Metrics is included only when the approved Story carries a Story-specific outcome or measure, per [single-story.md](single-story.md), "Story-specific goals and metrics." Do not invent one to populate this section; omit it when absent.
- Design Reference is included only when the approved Story carries a Story-level design reference, per [single-story.md](single-story.md), "Design reference." Do not discover, infer, or inspect a design here. Retrieval happens while drafting or updating the proposal. This template only publishes a reference already in the approved Story. Omit it when absent.
- Do not invent goals, metrics, dependencies, risks, scope, exclusions, or a design reference.

This template renders the approved Story model; it does not define it. It may omit an empty optional section, and it may omit a restatement that would only duplicate content already published in another field of the same payload, such as Acceptance Criteria. Deduplication is allowed only when meaning and traceability are preserved. It must not infer or introduce product behavior, a goal, a metric, a validation expectation, a dependency, a risk, a design reference, a scope boundary, or any other semantic content that is absent from the approved Story proposal. It must preserve every meaningful approved requirement, boundary, unresolved question, dependency, and reference. Formatting and omission of empty sections must not cause information loss.

## Default description

```markdown
#### 📋 Description

**User story:** As a [actor], I want [capability], so that [outcome].

**Context:** [Background that a reader needs and that is not already in the user-story line.]

#### 📐 Scope / Out of Scope

- **In scope:** [Approved boundary that is not already an Acceptance Criterion.]
- **Out of scope:** [Approved exclusion that must survive publication.]

#### 🧪 Testing / Validation Notes

- [Optional business-level validation scenario or condition that adds useful information for exercising an existing Acceptance Criterion without introducing new behavior.]

#### 💼 Stakeholder Questions

| Question | Answer |
| --- | --- |
| [Open question] | [Answer, or "open"] |

#### 🛠️ Technical Notes

- [Known constraint, stated in business language.]

#### 🎯 Goals & Metrics

- [Story-specific outcome or measure, only when the Product Owner or supporting evidence actually supplied one that adds information beyond the Acceptance Criteria. Omit this section when there is none.]

#### 🎨 Design Reference

- [Specific Figma file, frame, page, section, or other design artifact relevant to this Story, only when one actually exists. Omit this section when there is none.]

#### 🚧 Dependencies & Risks

- **Dependency:** [What this story needs before it can be delivered.]
- **Risk:** [What could block delivery.]
```

This prose line is human-readable context, not the operative relationship. An approved dependency is also created as a real Jira issue link at publication time — see [Jira integration](../../../../references/jira-integration.md), "Dependencies as issue links." The two are not duplicates: the link is what Jira actually tracks, this text explains it in the story's own words.

## Acceptance criteria field

Put this content in the acceptance-criteria field, not under Description:

```markdown
- [Observable result 1.]
- [Observable result 2.]
```
