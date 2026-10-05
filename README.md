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
/create-e2e-tests PAY-123 guest checkout journey
```

`create-e2e-tests` is optional. `validate-change` may run end-to-end tests that already exist. It does not run `create-e2e-tests`.

### Natural-language invocation

`sync-context` does not require the slash command. Its `SKILL.md` omits
`disable-model-invocation`, so Cursor's native "Agent Decides" selection may
include it from a plain request — for example "refresh the repository
context" or "sincronizá el contexto del repo". An informational question
such as "what does sync-context do?" or "show me what would change without
touching files" gets an answer or a proposal only; selecting the skill never
by itself authorizes a write.

The other six skills (`plan-work`, `refine-story`, `implement-change`,
`validate-change`, `create-e2e-tests`, `scaffold-project`) keep
`disable-model-invocation: true` and remain slash-only in this release.
Their blast radius (writing, deleting, or scaffolding) or their dependency
on an already-approved upstream state is higher than a false-positive
natural-language match should risk; broadening this list is a separate,
deliberate decision, not a side effect of enabling `sync-context`.

The skills are deliberately dry-run for Jira writes until the user approves an exact external change set. `plan-work` separates **ready for review** from **approved for publication**. It requests independent product review before publication, but records review as pending or unavailable when the host cannot delegate it. `/review-bugbot` remains a separate interactive Cursor command; `validate-change` records its status but cannot run it itself.

Delivery stays a developer step, not a skill. After validation says the change is ready, the developer commits, pushes, opens the pull request, obtains approvals, and merges with normal Git and pull-request tools. This plugin does not commit, push, open a pull request, or merge. When opening a pull request for this repository, read `.github/pull_request_template.md` and fill it in from the actual diff and verification results; never invent a Jira issue or claim tests ran when they did not.

## Host prerequisites and fallbacks

- **Jira:** The package uses an authenticated Atlassian MCP supplied by Cursor. It does not bundle credentials, a server ID, a site, or a project key. A disconnected, unauthorized, or unavailable MCP leaves the draft intact and marks Jira work pending.
- **Context:** `/sync-context` runs discover → detect changes → explore
  architecture → rich inventory with material findings → AI synthesis →
  mechanical safety validation → independent AI review → approve → apply
  → report.
  When nothing relevant changed
  since the last recorded fingerprint, it stops after detection: no file
  rewrite and no approval prompt. The closing result is still shown.
  Otherwise it stages a proposal
  (affected module, evidence inspected, proposed diff) before writing
  anything, resolves placement as distributed-by-default or an
  explicitly-adopted coordinator, writes one short index under
  `<artifact-home>/aidlc-docs/` plus `AIDLC_CONTEXT.md` for each
  meaningful architectural module listed in `## Modules` — including a
  single-module service. Repository size or module count does not decide
  documentation depth. Index-only (empty Modules table, no module context
  file) is reserved for a repository with no meaningful architectural
  module, such as a documentation-only tree or an extremely small passive
  package. A listed module always points at a local context file.
  Context files are not implicitly loaded by Cursor; a plugin-owned
  rule (`rules/ai-dlc-context-and-evidence.mdc`, Agent Decides) makes that
  discipline reachable even without a typed slash command, and lifecycle
  skills otherwise read the index and selected module context explicitly.
  Architecture exploration (`context-architect` when the scope warrants
  it) produces a coverage inventory plus material findings and runtime
  flows. The Coverage table is an index of architectural understanding,
  not the full architecture documentation; `## Material architecture
  details` preserves what downstream agents need. The main chat
  synthesizes those into documents without mechanically re-scanning the
  whole tree. Before treating context as final, it
  runs deterministic validation (index line budget, links, fingerprints,
  stale or duplicate entries, evidence-path existence) and requests an
  independent `context-reviewer` assessment for initial generation or a
  material change; it states plainly when that review was skipped or
  unavailable. Legacy migration stays inside this skill as its own change
  set, separate from context generation; generating new context never by
  itself means migration is complete.
- **Git and delivery:** Skills may inspect the local Git root, branch, and diff. They do not commit, push, open a pull request, or merge. The developer does that delivery with normal tools after validation.
- **Provider checks:** Remote checks and approvals are observed only when a verified provider integration shows them. `validate-change` records that evidence. It does not merge.
- **Agents:** The plugin defines reviewer prompts, but does not expose a dispatch API. The main chat uses host-supported independent delegation when available. A host general-purpose subagent may receive a bounded reviewer prompt when named plugin-agent dispatch is unavailable; that is reported as general-purpose review, not native agent dispatch. Otherwise review remains visibly pending or requires a named human review or policy-permitted exception.
- **Canvas and Bugbot:** `/sync-context` and `/plan-work` close with the host's Canvas capability when the current host can open one. The Canvas is a view of the same proposal and written files, not a second copy. On a host that cannot open a Canvas, those runs use the same sections in chat and say Canvas is unavailable on this host; a run with nothing new to show gets a short chat reply either way, not a mandatory Canvas. Bugbot requires user invocation through `/review-bugbot`; its presence in chat does not prove it ran.

The main chat drafts planning, refinement, and context synthesis. Independent agents are used for discovery, review, or bounded implementation: `context-architect` (read-only architecture exploration for `/sync-context`), `product-reviewer`, `refinement-reviewer`, `implementer`, `implementation-reviewer`, `validator`, and `context-reviewer`. `context-architect` returns an inventory, not a finished document. `context-reviewer` checks generated or updated repository context against current source for `sync-context`; it does not replace deterministic validation and a clean result covers only the scope it reviewed. Reviewer and architect agents declare `readonly: true`; Cursor must recognize that setting in the installed host for write restrictions to be enforced. This plugin does not provide an agent orchestration API.

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
