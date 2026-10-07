# Modes and drift

Development refinement explains how current code behaves, the affected callers and contracts, compatibility risks, and dependencies. QA refinement describes evidence needed to prove each acceptance criterion, including failure paths.

## Before publication

Re-read the business source and, when the change updates an existing technical issue, that issue. Check the source files, contracts, and dependencies that supported a material refinement decision. This check covers creating a new technical item, not only updating an existing one. Reuse the baseline recorded at the start of the refinement. Do not rescan the entire repository because an unrelated file changed.

A revision change, such as a new comment or a whitespace edit, is not by itself a material semantic change. If acceptance criteria, the business source, contracts, or the code behind a material decision actually changed, explain the impact and revise only the affected part of the proposal. Review that affected scope again before publication, and get renewed approval when the authorized change set changed. Route a change to business scope, expected behavior, or business acceptance criteria to the Product Owner through `/plan-work`.

If that evidence cannot be re-read, do not claim freshness was verified. Keep the affected publication pending unless an applicable project policy explicitly permits proceeding with the uncertainty disclosed. Do not claim the Jira read and the later write are atomic, and do not invent an optimistic-locking API.

## Before implementation

Immediately before implementation, re-read the business source and the technical item, and inspect the affected code, dependencies, and local modifications. If acceptance criteria, baseline, contracts, or relevant callers materially changed, stop and perform focused re-refinement. Record the new baseline rather than treating the old analysis as current.
