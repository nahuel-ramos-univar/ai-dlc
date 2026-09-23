# Bugbot configuration

After context discovery, inspect each confirmed consumer Git root for `.cursor/BUGBOT.md` and relevant nested `<module>/.cursor/BUGBOT.md` files. Do not inspect inaccessible sibling repositories.

Use verified code, contracts, tests, and module context to decide whether a concise root file would help Bugbot find concrete regressions. Propose a nested file only when a module has distinct, actionable review concerns. Do not create files per folder or source file.

Show a preview with file paths and diffs. Ask once per repository before creating missing files. Create `.ai-dlc-config.md` in that repository root if it is absent. Record the decision in a `## Context decisions` section:

```markdown
## Context decisions
- Bugbot configuration: declined at revision <git-rev>
```

Use `approved`, `declined`, or `deferred`. Do not ask again after `declined` unless the user explicitly asks to reconsider. If a nested module root cannot be written, do not write `<module>/.cursor/BUGBOT.md` there; keep the proposal as fallback-only or skip that nested file.

If BUGBOT files already exist, preserve them. Propose a narrow update separately only when current evidence makes a rule stale. Do not restate generic style guidance, invent company policy, duplicate unseen team rules, or claim that BUGBOT enables or invokes Bugbot.

Example root proposal:

```markdown
# Review focus

- Check public payment API changes against `contracts/payment.openapi.yaml`.
- Check retry changes keep duplicate-charge protection covered by tests.
```

Example nested proposal:

```markdown
# Orders API review focus

- Check order-status transitions preserve the terminal-state guard.
```

Colocated `AIDLC_CONTEXT.md` holds module workflow context. The artifact-home fallback exists when the source repository or that module root cannot be written. `.cursor/BUGBOT.md` holds Bugbot review instructions. Neither ordinary `.cursor/rules/*.mdc` files nor a BUGBOT file proves that `/review-bugbot` ran.
