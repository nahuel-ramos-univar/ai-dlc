# Bugbot configuration

After context discovery, inspect each confirmed consumer Git root for `.cursor/BUGBOT.md` and relevant nested `<module>/.cursor/BUGBOT.md` files. Do not inspect inaccessible sibling repositories.

Use verified code, contracts, tests, and module context to decide whether a concise root file would help Bugbot find concrete regressions. Propose a nested file only when a module has distinct, actionable review concerns. Do not create files per folder or source file.

## Placement

Always consider `<repo-root>/.cursor/BUGBOT.md`. Propose a nested `<boundary>/.cursor/BUGBOT.md` only for a meaningful review boundary: distinct runtime, deployment, trust, framework, domain invariant, testing expectation, or high-risk integration.

Prefer one root file. If two nested files would repeat a rule, lift it to the root. Do not create BUGBOT files under generated, vendor, build, coverage, lockfile, or fixture directories. A nested file supplements root guidance; it must not repeat it.

## Rule quality

Each proposed rule must name an observed path and helper, interface, or invariant. State the concrete regression it prevents. One rule, one invariant. Do not mix unrelated tables, services, or contracts in the same bullet. Review only changed lines. Prefer silence over speculation. Do not add generic security, style, formatter, lint, type-check, or test-runner rules.

Use the narrow shape: "When a change in `<path>` affects `<named invariant>`, verify `<behavior>` because failure would `<impact>`." Do not prescribe an implementation order, algorithm, or storage sequence unless reversing it would itself cause a user-visible defect. Do not put ownership, DevOps-task routing, or approval policy in BUGBOT.md; those belong to governance.

Add a leave-alone rule only for an observed intentional, generated, fixture, snapshot, or compatibility pattern.

Those approved BUGBOT paths are the only `.cursor/BUGBOT.md` writes allowed by the context-generation contract. Show a preview with file paths and diffs. Ask once per repository before creating missing files. Create `.ai-dlc-config.md` in that repository root if it is absent. Record the decision in a `## Context decisions` section:

```markdown
## Context decisions
- Bugbot configuration: declined at revision <git-rev>
```

Use `approved`, `declined`, or `deferred`. Do not ask again after `declined` unless the user explicitly asks to reconsider. If a nested module root cannot be written, do not write `<module>/.cursor/BUGBOT.md` there; keep the proposal as fallback-only or skip that nested file.

If BUGBOT files already exist, preserve them. Propose a narrow patch separately only when current evidence makes a rule stale, duplicated, contradictory, or tied to a missing path. Do not restate generic style guidance, invent company policy, duplicate unseen team rules, or claim that BUGBOT enables or invokes Bugbot.

Example root proposal:

```markdown
# Review focus

- Check public payment API changes against `contracts/payment.openapi.yaml`.
- Check retry changes keep duplicate-charge protection covered by tests.
```

Example nested proposal:

```markdown
# Checkout review focus

- When a change in `services/checkout/src/index.ts` affects `PUT /v1/carts/:cartId`, verify the path `cartId`, the DynamoDB item key, and the Redis key still identify the same cart, because a mismatch would return or persist the wrong cart.
```

Colocated `AIDLC_CONTEXT.md` holds module workflow context. The artifact-home fallback exists when the source repository or that module root cannot be written. `.cursor/BUGBOT.md` holds Bugbot review instructions. Neither ordinary `.cursor/rules/*.mdc` files nor a BUGBOT file proves that `/review-bugbot` ran.
