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
- Omit a section that has no real content.
- Testing lines are observable scenarios the Product Owner supplied. Do not invent test-runner cases.
- Technical notes are known constraints in business language. Hand implementation detail to `refine-story`.
- Do not invent goals, metrics, dependencies, or risks.

## Default description

```markdown
#### 📋 Description

**User story:** As a [actor], I want [capability], so that [outcome].

**Context:** [Background that a reader needs and that is not already in the user-story line.]

#### 🧪 Testing

- [Observable scenario that shows the story meets its acceptance criteria.]

#### 💼 Stakeholder Questions

| Question | Answer |
| --- | --- |
| [Open question] | [Answer, or "open"] |

#### 🛠️ Technical Notes

- [Known constraint, stated in business language.]

#### 🎯 Goals & Metrics

- [Goal or metric the Product Owner supplied.]

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
