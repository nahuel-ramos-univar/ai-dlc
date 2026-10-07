# Technical implementation template

Use this template for the Jira technical item `refine-story` proposes or updates — a Task, a Subtask, or an updated existing technical issue. It supplements the business source's acceptance criteria; it does not replace them.

Omit a section that has no real content for this change. Do not fill a section with generic boilerplate just to appear complete, and do not require every section for trivial work. Do not invent a file path, an API, an architecture decision, or a test command that was not actually read or run. Leave an open question open rather than promising implementation will never need clarification.

The fenced block below is description content. Technical acceptance criteria are not part of the description.

```markdown
#### 🎯 Objective
[The technical outcome this item produces, and how it serves the business source's outcome.]

#### 📌 Business source
- Issue: [key and URL of the issue whose approved acceptance criteria this work implements, or "standalone technical work — no business source".]
- Relationship: [how this item connects to that issue: Jira parent, or a named issue link such as "implements PAY-123". Not a dependency.]

#### 📦 Scope
- In scope: [what this item covers.]
- Out of scope: [what it deliberately does not cover, and why — for example, routed to a separate item or a DevOps task.]

#### 🔎 Verified current implementation
[What the code actually does today, with file references. State only what was read, not what is assumed.]

#### 🛠️ Proposed approach
[The approach, and the reasoning behind the decisions that matter — including a material alternative that was considered and rejected, and why.]

#### 🧩 Implementation details
- [Affected component or area]: [what changes.]

#### 🔗 Contracts, data, and compatibility
[Public contracts, data shape changes, and backward-compatibility impact, when relevant to this item. Omit if nothing changes here.]

#### 🚧 Dependencies
- **Dependency:** [what this item needs, as a plain-language relationship — see [Jira integration](../../../../references/jira-integration.md), "Dependencies as issue links," for how it becomes a real Jira link at publication. A dependency is not the business source.]

#### 🧪 Validation strategy
[Test scenarios, test data, and expected outcomes. For QA-mode refinement, cover positive, negative, boundary, regression, fixture, and environment needs explicitly.]

#### 🔐 Security and operational considerations
[Only when relevant to this item — permissions, data exposure, rollback, monitoring, or operational risk.]

#### ❓ Open questions
- **Blocking:** [cannot proceed without an answer.]
- **Nonblocking:** [known uncertainty that does not stop implementation.]

#### 📚 Source references
[Files, contracts, and tests actually inspected, and the Git baseline used.]
```

## Technical acceptance criteria

Put technical acceptance criteria in the issue type's acceptance-criteria field when that field exists. Do not also place them in the description. Discover the field from the issue type. Do not hardcode a custom field id. If the field is missing, keep the criteria in the local proposal and say the field was not found.

```markdown
- [Observable, verifiable result. Supplements the business source's acceptance criteria; does not replace them.]
```

## Business source and issue type

The business source is the issue whose approved acceptance criteria this work implements. The Jira parent is a separate fact. Do not treat every dependency link as the business source. If more than one linked issue could be the source, ask one focused question instead of picking one.

A Subtask's parent is a Story, a Task, or a Bug. Do not parent a Subtask under an Epic. For work that starts from an Epic, create a Task linked to that Epic, or another issue type the site actually allows under an Epic. Approved standalone technical work records "no business source" rather than an invented parent.

Discover the target project's actual Jira hierarchy and let the approver the calling skill authorizes approve the exact issue type. Do not silently change a Task into a Subtask.

## QA-mode emphasis

When refining in `qa` mode, lead with scenarios, regressions, test layers, fixtures, environments, and the evidence each criterion needs. Create a separate QA item only when it is independently verifiable or owned on its own — not by convention.
