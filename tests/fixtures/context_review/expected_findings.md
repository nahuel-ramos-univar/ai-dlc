# Expected findings — context review fixture

**Status: unevaluated fixture.** No `context-reviewer` execution, live or
simulated, has run against `AIDLC_CONTEXT.md` in this fixture directory in
this repository. The table below documents what a correct review should
flag if `context-reviewer` (or a human reviewer following
[review-handoff.md](../../../.cursor/skills/sync-context/references/review-handoff.md))
is run against this fixture. It is not a passing semantic test, and no
automated check in this repository claims to reproduce a reviewer's
judgment. Do not cite this file as evidence that `context-reviewer` catches
these defects; only an actual review run is that evidence.

## Seeded defects

| Marker | Location | Defect | Why it should be flagged |
| --- | --- | --- | --- |
| `coverage-overclaim` | `## Identity and scope` → `Examined` | States "all 42 tracked files" were examined | Listing or fingerprinting tracked files is inventory, not inspection; the document does not name which files were actually read |
| `unsupported-claim` | `## Responsibility` | Claims Twilio SMS receipts are sent for every order | No source path, symbol, or configuration key supports this; a real module context must ground it in evidence or drop it |
| `omitted-dependency` | `## Dependencies and consumers` | Says the worker has no other consumer | Contradicts the intent that a `receipts` module depends on this worker's output; a real reviewer with access to that module's source would find the gap |
| `fact-contradicted-by-unknown` | `## Unknowns` | Lists the Twilio SMS behavior as unknown | The same document already states that behavior as fact in `## Responsibility`; an Unknown must not restate a claimed fact |

## Deterministic checks that do not catch these defects

Running `scripts/context_tools.py` validation helpers against this fixture
(line budget, link resolution, fingerprint comparison, duplicate detection)
passes or is not applicable, because those checks are mechanical and do not
read prose for contradictions or unsupported claims. That is expected: this
fixture exists to describe the semantic gap that only independent review
closes, not to demonstrate a deterministic-check failure.
