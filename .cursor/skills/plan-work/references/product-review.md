# Product review gate

The product owner owns the draft. **Ready for review** is when the Product Owner finishes a drafting round or asks to review. No exact phrase is required. Open product questions do not delay that review. **Ready to implement** and **approved for publication** stay separate: a blocking unresolved product decision must not be treated as ready to implement, even after review ran.

When review is due, request an independent `product-reviewer` assessment through a supported host agent facility, following [skill composition](../../../../references/skill-composition.md). If the host cannot invoke that named agent, a general-purpose independent subagent may take the `product-reviewer` file as bounded task context; report that as general-purpose independent review, not native named-agent dispatch. If no independent subagent is available, say so and keep review unavailable or pending. Never present the main chat's own assessment as independent review.

Give the reviewer a bounded handoff. Every handoff names:

- pass reason: first review after this drafting round, or re-review of a material revision;
- draft version identifier;
- delta since the previous review when this is a re-review: what changed, and what is unchanged;
- the sources the reviewer must read: affected work, scoped context, the deterministic validation result, open product questions, and any obvious duplicate noticed in passing while reading a candidate parent Epic.

Do not send the full conversation. Do not re-review unchanged scope. Do not pass a duplicate-candidates list as if a search ran, and do not ask the reviewer to search Jira for duplicates. This skill does not run a dedicated duplicate search, so there are no search limits to report. The reviewer evaluates open questions and names which ones block implementation or publication. It returns evidence-based blocking findings, optional improvements, open questions, and a readiness recommendation.

Report the reviewed scope and draft version, findings or a visible "no findings" result, and the actual delegation outcome, in the same closing view the Product Owner sees. Do not replace that with a status phrase. Mark review `completed` only when the reviewer responded. If delegation is unavailable, keep the requirement visible. A named human review or a policy-permitted exception may satisfy it; otherwise publication stays blocked while drafting can continue.

The reviewer inspects clarity, product value, scope, correct granularity, acceptance-criteria quality and testability, missing important scenarios, unsupported assumptions, contradictions, ambiguous behavior, dependency correctness, parent Epic fit, a Task incorrectly modeled as a Story, a Story that is really Epic-sized, implementation detail leaking into the product requirement, implementation-readiness, and whether an open question materially blocks implementation. For a Sprint Backlog, the reviewer also checks sprint-goal coherence, dependency ordering, missing prerequisite work, blockers, and scope coherence given any capacity information actually supplied. Findings use a small severity vocabulary: Blocker, Major, Minor, Suggestion. **No findings** within reviewed scope is a valid, complete review result — a reviewer must never manufacture a finding merely to show that review happened.

The main chat consolidates findings. Ask the product owner only questions that resolve business uncertainty. Re-review only the changed scope after material revisions, including a proposal materially changed by an incidental-duplicate finding. If the reviewer and product owner disagree, present the disagreement and request a human decision.

**Approved for publication** is separate. It requires product-owner approval of the exact Jira or Git changes after blockers are resolved. The reviewer cannot approve publication. After a write, record publication as completed, pending, or partially completed and reconcile uncertainty before retrying.
