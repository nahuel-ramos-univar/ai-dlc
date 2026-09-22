# Simplified AI-DLC lifecycle (experimental)

This is a Cursor Plugin. Its manifest is `.cursor-plugin/plugin.json` and it explicitly discovers its canonical sources from `.cursor/skills/<name>/SKILL.md`.

Install it from a local checkout for development. Do not treat this as Marketplace-ready until clean-consumer installation, skill discovery, agent delegation, and required host integrations have been manually verified.

Invoke the included skills directly:

```text
/sync-context
/plan-work Create a user story for guest checkout
/refine-story PAY-123 combined
/implement-change PAY-123
/validate-change PAY-123
/resolve-defect Checkout fails after a declined payment retry
/deliver-change
/check-governance
```

The skills are deliberately dry-run for Jira, Git, pull-request, merge, and deployment actions until the user approves an exact external change set. `plan-work` separates **ready for review** from **approved for publication**. It requests independent product review before publication, but records review as pending or unavailable when the host cannot delegate it. `/review-bugbot` remains a separate interactive Cursor command; `validate-change` coordinates its status but cannot run it itself.

## Host prerequisites and fallbacks

- **Jira:** The package uses an authenticated Atlassian MCP supplied by Cursor. It does not bundle credentials, a server ID, a site, or a project key. A disconnected, unauthorized, or unavailable MCP leaves the draft intact and marks Jira work pending.
- **Git:** Local Git supports repository inspection, branch, diff, commit, and push only. Each workflow resolves the actual Git root and preserves unrelated work.
- **Provider operations:** Pull requests, remote checks, approvals, and provider merge need a verified provider integration. GitHub can use an already installed and authenticated `gh` CLI. Without it, the plugin completes only supported local actions and provides a manual handoff.
- **Agents:** The plugin defines reviewer prompts, but does not expose a dispatch API. The main chat uses host-supported independent delegation when available. A host general-purpose subagent may receive a bounded reviewer prompt when named plugin-agent dispatch is unavailable; that is reported as general-purpose review, not native agent dispatch. Otherwise review remains visibly pending or requires a named human review or policy-permitted exception.
- **Canvas and Bugbot:** Canvas has structured-chat fallback. Bugbot requires user invocation through `/review-bugbot`; its presence in chat does not prove it ran.

The main chat drafts planning and refinement. Independent agents are used only for review or bounded implementation: `product-reviewer`, `refinement-reviewer`, `implementer`, `implementation-reviewer`, `validator`, and `governance-reviewer`. Reviewer agents declare `readonly: true`; Cursor must recognize that setting in the installed host for write restrictions to be enforced. This plugin does not provide an agent orchestration API.

There is no package-manager build or separate packager in this repository. The manifest and skill sources are authoritative. Structural checks do not verify runtime host behavior or external integrations. Run:

```sh
python3 tests/skill_contracts.py
```

Use [MANUAL_EVALUATION.md](MANUAL_EVALUATION.md) for clean-consumer and integration smoke tests.
