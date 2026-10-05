# Expected findings — context review fixture

**Status: one recorded fallback review.** A general-purpose fallback run,
not native `context-reviewer` dispatch, was recorded under "Live evaluation
record" below. That record is not native named-agent verification and it is
not an automated semantic regression test. The table documents what a
correct review should flag if `context-reviewer` (or a human reviewer
following
[review-handoff.md](../../../.cursor/skills/sync-context/references/review-handoff.md))
is run against `AIDLC_CONTEXT.md` plus the `source/` tree in this same
directory. No automated check in this repository reproduces a reviewer's
judgment. Do not cite this file, or that one fallback run, as proof that
native `context-reviewer` catches these defects on every run.

## Limitation: this file sits next to the material under review

`AIDLC_CONTEXT.md` and `source/` are the material a reviewer should inspect.
This file is the answer key. Both live in the same directory
(`tests/fixtures/context_review/`). A reviewer given unrestricted filesystem
access to this directory, or to this repository generally, could read this
file directly instead of forming its own judgment from `AIDLC_CONTEXT.md`
and `source/`.

To run a fair evaluation, do one of:

- Copy `AIDLC_CONTEXT.md` and `source/` alone into an isolated directory that
  does not contain this file, and point the reviewer only at that copy.
- If the reviewer runs with access to this whole repository, explicitly
  instruct it not to open `expected_findings.md`, and record that
  instruction (and whether it was honored) in the live evaluation record
  below. Treat a run that skipped this instruction as invalid evidence, not
  as a passing review.

## Seeded defects

| Marker | Location | Defect | Why it should be flagged |
| --- | --- | --- | --- |
| `unsupported-coverage-claim` | `## Identity and scope` → `Examined` | States "all 4 tracked files in `source/notifications`" were examined | `source/notifications/` contains 2 files (`notifications_worker.py`, `email_templates.py`), not 4. This is a checkable mismatch between a coverage claim and the actual file count, not proof about whether the author read either file. |
| `unsupported-claim` | `## Responsibility` | Claims Twilio SMS receipts are sent for every order | Neither `notifications_worker.py` nor `email_templates.py` sends SMS or references Twilio; the claim has no source path, symbol, or configuration key backing it. |
| `omitted-dependency` | `## Dependencies and consumers` | Says the worker has no other consumer | `source/receipts/receipts_digest.py` imports `NOTIFICATION_SENT_TOPIC` from `notifications.notifications_worker` and subscribes to it to build a reorder digest. That import is a real, inspectable dependency this section omits. |
| `fact-contradicted-by-unknown` | `## Unknowns` | Lists the Twilio SMS behavior as unknown | The same document already states that behavior as fact in `## Responsibility`; an Unknown must not restate a claimed fact. |
| `false-completeness-coverage` | `## Coverage` → `Retry and idempotency` row | Marks "Retry and idempotency" `verified` with evidence pointing at `_handle` | `source/notifications/notifications_worker.py`'s `_handle` has no idempotency guard at all: it unconditionally sends the email and republishes `NOTIFICATION_SENT_TOPIC` on every call, so a redelivered `OrderPlacedEvent` sends a duplicate confirmation email. This is the "false completeness" pattern in [context-quality.md](../../../.cursor/skills/sync-context/references/context-quality.md): a confident `verified` claim that does not match the cited source, which is worse than an honest `unknown` row. |

## Deterministic checks that do not catch these defects

An end-to-end run of `validate_generated_context` (via the
`context_tools.py validate` CLI) against an isolated copy of this fixture,
with a representative one-module repository index built on top of it and
this module's real content fingerprint recorded, reports all 10 applicable
checks as `passed`: index line budget, required structure, index
fingerprint, the Modules table, duplicate identity, duplicate context
target, the link to this module document, this module's required
structure, this module's own fingerprint, and the declared source
path. None of that mechanical evidence reads prose for contradictions,
unsupported claims, a mismatch between a stated file count and the actual
file count in `source/notifications/`, or whether a `## Coverage` row's
`verified` state is actually backed by the file it cites. Module line
count is not a validation result at all (`document_metrics` can report it
as a metric), so it has no opinion on these defects either. Closing that
gap is what independent review is for, not deterministic validation.

## Live evaluation record

**Coverage note:** the first recorded run below predates the `## Coverage`
section and the seeded `false-completeness-coverage` defect; it evaluated
the original four defects only. A second run, recorded further down, was
performed specifically to check the fifth defect once it was added.

### Run 1 — original four defects

**Date:** 2026-09-28.

**Invocation:** A `generalPurpose` subagent (native Cursor `Task` dispatch;
`context-reviewer` is not yet registered as a native `subagent_type` in this
session, so this is the documented general-purpose fallback from
[review-handoff.md](../../../.cursor/skills/sync-context/references/review-handoff.md),
not native named-agent dispatch). The prompt inlined the full text of
`agents/context-reviewer.md` as the subagent's role, then pointed it only at
an isolated copy of this fixture under `/tmp/fixture_e2e.<random>/` that
contained `AIDLC_CONTEXT.md`, `source/`, and a representative
`aidlc-docs/repository-context.md` — and explicitly nothing else. This
directory (`tests/fixtures/context_review/`, including this
`expected_findings.md` file) was never copied into that isolated location, so
the constraint "do not read `expected_findings.md`" was enforced by absence,
not only by instruction.

**Outcome — all 4 defects seeded at the time of this run were found; the
fifth, `false-completeness-coverage`, was added later (see Run 2 below):**

| Marker | Found? | Matched reviewer finding |
| --- | --- | --- |
| `unsupported-coverage-claim` | Yes | Finding 4 (coverage statement does not match inventory) |
| `unsupported-claim` | Yes | Finding 1 (blocker: false SMS/Twilio claim) |
| `omitted-dependency` | Yes | Finding 3 (major: omitted outbound contract and `receipts` consumer) |
| `fact-contradicted-by-unknown` | Yes | Finding 2 (major: Unknown restates a fact already asserted) |

**Extra finding not in the seeded set:** Finding 5 (minor: imprecise event
naming, "publishes an order-confirmation email" versus the code actually
sending email then publishing a separate confirmation event). This is a
reasonable additional observation, not a false claim about the fixture; it
is not counted as a false positive.

**Result reported by the reviewer:** "Changes required," with an explicit
limitations section (fingerprint/baseline not recomputed, `queue_client` and
`email_client` implementations not in scope, no claim about correctness
beyond the four inspected Python files).

**Caveat on this record:** this is a single run of a general-purpose
fallback, not `context-reviewer` running as a native named subagent, and not
a statistically meaningful sample. Treat it as evidence that the review
workflow can catch these four defect categories when actually invoked, not
as a guarantee for every future run.

### Run 2 — `false-completeness-coverage` added

**Date:** 2026-10-05.

**Invocation:** Same documented general-purpose fallback as Run 1 (a
`generalPurpose` subagent given the current `agents/context-reviewer.md`
text inline as its role). The isolated copy for this run was placed under
`/tmp/fixture_eval_<random>/` and contained only `AIDLC_CONTEXT.md`,
`source/`, and a minimal `aidlc-docs/repository-context.md` — again, nothing
from `tests/fixtures/context_review/` itself, so `expected_findings.md` was
unreachable from that scope rather than merely instructed-against.

**Outcome — the targeted defect was found, plus every defect from Run 1:**

| Marker | Found? | Matched reviewer finding |
| --- | --- | --- |
| `false-completeness-coverage` | Yes | Finding 1 (blocker, accuracy: `_handle` has no idempotency guard; the `verified` Retry-and-idempotency row does not match the source it cites) |
| `unsupported-claim` | Yes | Finding 2 (major, accuracy: the Twilio/SMS claim) |
| `fact-contradicted-by-unknown` | Yes | Finding 3 (major, accuracy: the SMS Unknown restates and contradicts the Responsibility claim) |
| `omitted-dependency` | Yes | Finding 4 (major, completeness: omitted `NOTIFICATION_SENT_TOPIC` interface and the `receipts` consumer) |
| `unsupported-coverage-claim` | Yes | Finding 7 (minor, accuracy: the "4 tracked files" Examined count does not match the 2 files actually in `source/notifications`) |

**Extra findings not in the seeded set:** Finding 5 (major, completeness:
no runtime-flow row and no mention of the `email_client` dependency) and
Finding 6 (major, accuracy: the `not applicable` Security-and-trust-boundaries
row is itself wrong, because the worker does handle `customer_email` and an
outbound integration). Both are reasonable observations grounded in the
actual source, not false claims about the fixture; neither is counted as a
false positive. Finding 6 is a useful reminder that `not applicable` needs a
real reason, exactly as `context-reviewer`'s contract requires, and that a
reviewer should check that reason rather than accept it at face value.

**Result reported by the reviewer:** "changes required," with an explicit
limitations section naming what was and was not inspected.

**Caveat on this record:** same as Run 1 — one fallback run, not a
statistically meaningful sample, and not native `context-reviewer`
dispatch. Treat it as evidence the strengthened Accuracy/Completeness
contract and the `## Coverage` table can surface a false-`verified` claim
when actually invoked, not as a guarantee for every future run.
