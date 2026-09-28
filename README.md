# Simplified AI-DLC lifecycle (experimental)

This is a Cursor Plugin. Its plugin manifest is `.cursor-plugin/plugin.json`. The Team Marketplace index is `.cursor-plugin/marketplace.json`. Skills are discovered from `.cursor/skills/<name>/SKILL.md`.

Do not treat this as public Marketplace-ready until clean-consumer installation, skill discovery, agent delegation, and required host integrations have been manually verified.

### Local install (development)

```sh
git clone https://github.com/nahuel-ramos-univar/ai-dlc.git \
  ~/.cursor/plugins/local/simplified-ai-dlc-lifecycle
```

Then run **Developer: Reload Window**. The plugin should appear as `simplified-ai-dlc-lifecycle` in Customize. Enterprise needs **Allow Local Plugin Imports**. If another plugin already uses the same `name`, the marketplace copy wins.

### Team Marketplace (GitHub URL)

An admin imports the repo as a Team Marketplace:

1. Dashboard → **Plugins & MCPs** → **Import from Repo**
2. Use `https://github.com/nahuel-ramos-univar/ai-dlc`
3. Cursor indexes `.cursor-plugin/marketplace.json` and lists `simplified-ai-dlc-lifecycle`
4. Each developer installs it from **Customize**

`Univar/digital-ai-dlc` is not this plugin. Do not import that repo for this package.

Invoke the included skills directly:

```text
/sync-context
/plan-work Create a user story for guest checkout
/scaffold-project Create a new ecommerce project
/refine-story PAY-123 combined
/implement-change PAY-123
/validate-change PAY-123
/deliver-change
```

The skills are deliberately dry-run for Jira, Git, pull-request, merge, and deployment actions until the user approves an exact external change set. `plan-work` separates **ready for review** from **approved for publication**. It requests independent product review before publication, but records review as pending or unavailable when the host cannot delegate it. `/review-bugbot` remains a separate interactive Cursor command; `validate-change` coordinates its status but cannot run it itself.

## Host prerequisites and fallbacks

- **Jira:** The package uses an authenticated Atlassian MCP supplied by Cursor. It does not bundle credentials, a server ID, a site, or a project key. A disconnected, unauthorized, or unavailable MCP leaves the draft intact and marks Jira work pending.
- **Context:** `/sync-context` resolves the owning repository, requested module,
  and configured artifact home. It writes one short index under
  `<artifact-home>/aidlc-docs/`, selectively useful
  `<module-root>/AIDLC_CONTEXT.md` files, and fallback module context only when
  source roots cannot be written. It proposes BUGBOT guidance separately and
  writes it only after a per-repository approval. Context files are not
  implicitly loaded by Cursor; lifecycle skills read the index and selected
  module context explicitly.
- **Git:** Local Git supports repository inspection, branch, diff, commit, and push only. Each workflow resolves the actual Git root and preserves unrelated work.
- **Provider operations:** Pull requests, remote checks, approvals, and provider merge need a verified provider integration. GitHub can use an already installed and authenticated `gh` CLI. Without it, the plugin completes only supported local actions and provides a manual handoff.
- **Agents:** The plugin defines reviewer prompts, but does not expose a dispatch API. The main chat uses host-supported independent delegation when available. A host general-purpose subagent may receive a bounded reviewer prompt when named plugin-agent dispatch is unavailable; that is reported as general-purpose review, not native agent dispatch. Otherwise review remains visibly pending or requires a named human review or policy-permitted exception.
- **Canvas and Bugbot:** Canvas has structured-chat fallback. Bugbot requires user invocation through `/review-bugbot`; its presence in chat does not prove it ran.

The main chat drafts planning and refinement. Independent agents are used only for review or bounded implementation: `product-reviewer`, `refinement-reviewer`, `implementer`, `implementation-reviewer`, and `validator`. Reviewer agents declare `readonly: true`; Cursor must recognize that setting in the installed host for write restrictions to be enforced. This plugin does not provide an agent orchestration API.

There is no package-manager build or separate packager in this repository. The manifest and skill sources are authoritative. Structural checks do not verify runtime host behavior or external integrations. Run:

```sh
python3 tests/skill_contracts.py
```

Use [MANUAL_EVALUATION.md](MANUAL_EVALUATION.md) for clean-consumer and integration smoke tests.

## Versioning

`.cursor-plugin/plugin.json` is the plugin version. After a merge to `main`, GitHub Actions inspects Conventional Commits since the last tag:

| Commits since last tag | Bump |
| --- | --- |
| `feat:` | minor |
| `fix:` or `perf:` | patch |
| `BREAKING CHANGE` or `type!` | major |
| only `docs` / `chore` / `test` / `ci` / `build` / `style` / `refactor` | no release |

If `main` has no tag yet, the workflow tags the current `plugin.json` version as the baseline and does not replay earlier history. Later merges bump from that tag.

A releasable merge updates `plugin.json`, prepends [CHANGELOG.md](CHANGELOG.md), tags `vX.Y.Z`, and creates a GitHub Release. If the GitHub Release step fails after the tag is pushed, the next `main` run retries that release only. Cursor does not auto-refresh an installed plugin; reinstall or reload after the new tag if you need that version.

PRs to `main` must use Conventional Commit subjects. Merge commits are allowed. Prefer squash merges with a conventional squash title so the next release is predictable.
