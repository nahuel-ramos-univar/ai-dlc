# Product review gate

The product owner owns the draft. A draft becomes **ready for review** when the product owner finishes refining scope, exclusions, and acceptance criteria.

Before requesting publication approval, the main chat must request an independent `product-reviewer` assessment through a supported agent facility. Give the reviewer the draft version, affected work, scoped context, the deterministic validation result, and any obvious duplicate noticed in passing while reading a candidate parent Epic — this skill does not run a dedicated duplicate search, so there are no search limits to report. The reviewer returns evidence-based blocking findings, optional improvements, open questions, and a readiness recommendation.

The main chat records review as completed, unavailable, or pending. If independent delegation is unavailable, keep the requirement visible. A named human review or policy-permitted exception may satisfy it; otherwise publication stays blocked while drafting can continue.

The reviewer inspects clarity, product value, scope, correct granularity, acceptance-criteria quality and testability, missing important scenarios, unsupported assumptions, contradictions, ambiguous behavior, dependency correctness, parent Epic fit, a Task incorrectly modeled as a Story, a Story that is really Epic-sized, implementation detail leaking into the product requirement, implementation-readiness, and whether an open question materially blocks implementation. For a Sprint Backlog, the reviewer also checks sprint-goal coherence, dependency ordering, missing prerequisite work, blockers, and scope coherence given any capacity information actually supplied. Findings use a small severity vocabulary: Blocker, Major, Minor, Suggestion. **No findings** within reviewed scope is a valid, complete review result — a reviewer must never manufacture a finding merely to show that review happened.

The main chat consolidates findings. Ask the product owner only questions that resolve business uncertainty. Re-review only the changed scope after material revisions, including a proposal materially changed by duplicate findings. If the reviewer and product owner disagree, present the disagreement and request a human decision.

**Approved for publication** is separate. It requires product-owner approval of the exact Jira or Git changes after blockers are resolved. The reviewer cannot approve publication. After a write, record publication as completed, pending, or partially completed and reconcile uncertainty before retrying.
