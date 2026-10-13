# Simplified AI-DLC lifecycle

This Cursor plugin helps a team describe a product, plan the work, build a small technical foundation, and check that a change matches what was approved.

You run the workflows in **your product folders**. You do not edit the plugin installation to describe your application.

This package is still experimental. A clean install on a new machine, agent delegation, and the host integrations are listed in [MANUAL_EVALUATION.md](MANUAL_EVALUATION.md). Static checks in this repository do not prove those live steps.

## Start here

1. Install the plugin (below). Reload Cursor, then confirm the slash commands appear in agent chat.
2. Open the product folder in the local Cursor IDE. Use the table to choose the folder and the first command.
3. Read the proposal. Approve it before the agent writes files or changes Jira.

The local Cursor IDE is the path this guide describes. Open one repository, or an existing `.code-workspace`, in that IDE and use agent chat. Whether a separate Agents window treats a multi-root workspace the same way has not been verified. Use the IDE window.

## Words used in this guide

- **Plugin.** The installed set of skills, reviewer prompts, and rules. The manifest is `.cursor-plugin/plugin.json`.
- **Skill.** One workflow. You start it with a slash command such as `/sync-context`.
- **Project repository.** The Git repository that holds your application or infrastructure code.
- **Module.** One component inside a single repository, such as a backend or a frontend package.
- **Monorepo.** One Git repository that contains several components and one Git history.
- **Multi-repository product.** Several independent Git repositories that belong to one product.
- **Workspace.** An optional local `.code-workspace` file that opens those folders together in Cursor. It is not another way to organize Git repositories.

## Where should I start?

| Your situation | What to open | First command | What to expect |
| --- | --- | --- | --- |
| An existing application in one repository | That repository | `/sync-context` | A proposal for repository context, then files only after you approve |
| An existing monorepo | The repository root | `/sync-context` | The skill looks for meaningful modules inside that one Git root |
| An existing multi-repository product | The cloned repositories together, for example an existing `.code-workspace` | `/sync-context` | Each open Git root is recorded on its own. Product membership comes from confirmed `Product` and `Related repository` entries, not from folders that merely sit next to each other |
| A new project in an empty directory | That empty directory | `/scaffold-project` | Questions about purpose first, then a proposed foundation |
| A new component inside an existing monorepo | The monorepo root, and name the new component directory | `/scaffold-project` | One destination this run. A root manifest or workspace file changes only when the proposal names that file |
| A new product that will use several repositories | The first folder you want created | `/scaffold-project` | Say that you want multiple repositories. This run scaffolds one destination. It does not run `git init`, create remotes, or clone the others |
| A product that still uses the older AI-DLC coordinator | The existing product workspace | `/sync-context` | A migration proposal. Useful knowledge is preserved. Cleanup is a separate approval. Do not delete the old coordinator or methodology checkout before that review |
| Only one repository of a multi-repository product is on this machine | The repository you have | `/sync-context` | Context for the repositories that are actually open. A missing sibling is reported as unavailable. It is not inspected and not described as verified. Run `/sync-context` again when that sibling is cloned |

Details for Git classification live in [repository preflight](references/repository-preflight.md). Migration limits live in [legacy migration](.cursor/skills/sync-context/references/legacy-migration.md).

## Install and connect

Normal use does not require cloning this repository. An admin imports it as a Team Marketplace:

1. Dashboard → **Plugins & MCPs** → **Import from Repo**
2. Use `https://github.com/nahuel-ramos-univar/ai-dlc`
3. Cursor indexes `.cursor-plugin/marketplace.json` and lists `simplified-ai-dlc-lifecycle`
4. Each developer installs it from **Customize**

`Univar/digital-ai-dlc` is a different repository. Do not import it for this plugin.

To develop the plugin itself, clone it and reload:

```sh
git clone https://github.com/nahuel-ramos-univar/ai-dlc.git \
  ~/.cursor/plugins/local/simplified-ai-dlc-lifecycle
```

Then run **Developer: Reload Window**. The plugin should appear as `simplified-ai-dlc-lifecycle` in Customize. Enterprise needs **Allow Local Plugin Imports**. If another plugin already uses the same name, the marketplace copy wins.

After a reload, the agent chat should offer:

```text
/sync-context
/scaffold-project
/plan-work
/refine-story
/implement-change
/validate-change
/create-e2e-tests
```

`/sync-context` can also start from a plain request such as "refresh the repository context". The other six commands stay slash-only. Choosing a skill does not by itself approve a write.

Cursor does not refresh an already installed plugin by itself. After a new release tag, reinstall or reload if you need that version.

### What you need locally

- **Git**, so repository boundaries and freshness can be read from the product checkout.
- **Starting the conversation** with `/sync-context` or `/scaffold-project` does not require Node, Terraform, or another stack runtime.
- **Python 3** is required for this plugin's deterministic checks, including `python3 scripts/context_tools.py validate`. If Python is missing, those checks did not run. That is not a pass.
- A stack tool such as Node or Terraform is required only when the approved scaffold or a later check actually runs that tool. If the tool is missing, that check stays unavailable. It is not a pass.

### Jira, Git, and Figma

You do not need Jira, a GitHub integration, and Figma connected before the first command. Connect the one the workflow you are running actually uses.

Pasting a Jira, Git, or Figma URL names the resource. It does not sign you in. This plugin does not store tokens.

- **Jira** is used when a workflow reads or proposes work items. The host must already provide an authenticated Atlassian connection. A board URL is a planning view and can contain issues from more than one project. A project key is where new issues would be created. They are not the same choice. See [Jira integration](references/jira-integration.md).
- **Git** for these workflows is the local checkout. A remote URL is optional identity information. These skills do not commit, push, open a pull request, or merge.
- **Figma** is optional and matters for UI or design work. A design link on one work item stays with that item. It becomes the project default only when you ask to save it that way. See [project onboarding](references/project-onboarding.md).

If a connection is missing, the run says so and continues the local work that does not need it. It does not claim the external content was read.

## First `/sync-context`

Open the product repository, or the workspace that already contains the repositories you want described. Then paste a request like this, replacing the placeholders:

```text
/sync-context
Describe the repository that is open.
Jira site: example.atlassian.net
Jira project: PROJ
Figma: none
```

Omit the Jira lines when you are not using Jira. Omit Figma when this repository has no UI design to record.

The skill then:

1. Checks which folder is open, which Git roots are really present, and which related repositories are only named.
2. Reads repository boundaries, meaningful modules, relevant submodules, existing configuration, any context already written, and legacy AI-DLC markers when they are present.
3. Separates a known fact, an assumption, a repository that is not available, and a decision that is still pending.
4. Shows a proposal before it writes. The usual groups are context documents, project rules and `BUGBOT.md`, and legacy cleanup. A context refresh approves context documents only. Rules, `BUGBOT.md`, and cleanup stay pending until you approve those groups.
5. Writes only the approved group.

After approval, look at:

| Path | What it is |
| --- | --- |
| `aidlc-docs/repository-context.md` | Short index for the repository. The artifact home may be the Git root or another approved folder. |
| `<module-root>/AIDLC_CONTEXT.md` | Context for one meaningful module. A single-module application still gets this file. |
| `aidlc-docs/context/<repo-id>/<module-id>.md` | Fallback module context when the module root cannot be written. |
| `aidlc-docs/integration-map.md` | Written only after a verified dependency between repositories. |
| `.ai-dlc-config.md` | Placement, repository identity, project references, and recorded Bugbot decisions. |

A project rule under `.cursor/rules/<slug>.mdc` and a `.cursor/BUGBOT.md` file are separate proposals. They are not created on every sync.

When the host can open a Canvas, the proposal and the written result can be shown there. The Canvas is a view of the same material, not a second copy. If this host cannot open one, the same sections appear in chat and the reply says Canvas is unavailable. A run that finds nothing new stays a short chat reply. See [canvas review](references/canvas-review.md).

Run `/sync-context` again later. If the examined source, project references, rules, and migration cleanup have nothing new, the skill stops without rewriting files and without asking for approval again.

`context-architect` is read-only architecture exploration for a behaviorful `/sync-context` when the host can delegate it. `context-reviewer` checks the generated context against the source. If that delegation is unavailable, the result says independent review was not performed. Mechanical checks can still pass. That is partial quality assurance, not a full review.

## First `/scaffold-project`

Open the empty destination, or the monorepo root if you are adding a component. Paste a purpose, not a stack:

```text
/scaffold-project
Create a foundation for an internal order-note tool.
Operations staff look up one order and add an internal note.
Start with that lookup and note only.
Do not include customer payment or public signup.
The folder open in Cursor is the destination.
I have not chosen a stack yet.
```

The conversation fills in what you have not already said:

- who the product is for, and the main thing they do
- what this first slice includes, and what it leaves out
- constraints that are already true, such as an existing repository or a required language
- one repository, a monorepo, or several repositories
- whether a local `.code-workspace` would help open those folders
- stack and local tooling, after the purpose is clear
- Jira, Git, or Figma references when this project needs them

It does not ask again for a fact you already gave. A missing Jira or Figma reference does not block a local foundation.

The proposal splits three kinds of statement:

- something you selected
- something already verified in the folder or Git
- a recommendation that still needs your approval

It also lists files to create, existing files to modify, and any install or generator command. That command runs when the exact command is part of the proposal you approve. Approving a project rule on its own does not approve an install. If the command was missing from the proposal, or the command changes, the skill asks again before running it.

This skill builds a technical foundation, a navigable prototype, or the smallest slice you approved. It does not implement a full business feature. When you need Stories for that behavior, the next command is `/plan-work`.

It does not initialize Git, create a remote, deploy, or provision infrastructure. Creating a directory is not creating a Git repository. For several repositories, this run creates one destination and names the others as planned.

If Node, Terraform, or another tool the scaffold expected is not installed, the matching check is reported unavailable. It is not reported as passed.

Initial context is written from the files this run actually created. A sibling that was not created is not described as done.

When the change is more than a trivial file layout, the skill asks `implementation-reviewer` to read the generated files. If the host cannot delegate that review, the result says independent review was not performed and leaves it pending. The scaffold chat does not label its own check as that review.

## What to run next

| Command | Typical user | When | You provide | Main result |
| --- | --- | --- | --- | --- |
| `/sync-context` | Developer or anyone preparing a repository | Context is missing or stale | The open product folder, plus optional Jira or Figma references | Approved repository and module context |
| `/scaffold-project` | Developer starting a repository or component | A new foundation is needed | Purpose, users, scope, and the destination folder | An approved minimal foundation and initial context for what was created |
| `/plan-work` | Product owner | The business work is not in Jira yet | The outcome in plain language, and a Jira target when you want it published | A proposed Epic, Story, Task, or backlog update. Jira changes wait for an approved change set |
| `/refine-story` | Developer | A Jira item is ready for a technical plan | The issue key, for example `PROJ-123` | A technical proposal that keeps the business acceptance criteria |
| `/implement-change` | Developer | The technical proposal is approved | The issue key and the repository to change | The code or infrastructure change in the approved scope |
| `/validate-change` | Developer | The change is ready to check | The issue key and how to run the relevant tests | Evidence against the acceptance criteria, including tests that already exist |
| `/create-e2e-tests` | Developer or QA | A journey needs browser coverage | The issue key or the journey | End-to-end tests. This command is optional and is not run by `/validate-change` |

A normal sequence is context or foundation, then business planning, then technical refinement, then implementation, then validation. You can start later in that sequence when the earlier artifact already exists. Naming a later command does not run it. See [skill composition](references/skill-composition.md).

Jira holds the business work items and the technical refinement. This plugin does not require a Markdown copy of each Story in the repository.

These files do different jobs, and the ones you approve can live in Git:

- repository context explains the system
- the product README explains how to run that product
- a project rule is a durable instruction for the agent
- `BUGBOT.md` is review guidance for a later `/review-bugbot` run, which you start yourself

After validation says the change is ready, you commit, push, open the pull request, and merge with your normal Git tools. This plugin does not do those steps.

## When something looks wrong

- **The slash command is missing.** Reload the window. In Customize, confirm `simplified-ai-dlc-lifecycle` is installed. A marketplace copy with the same name overrides a local clone.
- **The wrong folder is open.** The skill uses the folder you opened, not the plugin repository. Open the product root, or say which destination you mean, and start again.
- **A new folder sits inside an unrelated Git repository.** The skill can classify that folder as an untracked tree and must not take the parent repository's identity. Confirm that before you approve any write. See [repository preflight](references/repository-preflight.md).
- **A related repository is not on this machine.** The run reports it as unavailable. Do not treat that sibling as inspected. Clone it, open it, and run `/sync-context` again.
- **Jira or Figma cannot be read.** Local files can still be proposed. The run must say the external read did not happen. Reconnect the host integration and retry the part that needed it.
- **Python, Node, Terraform, or another tool is missing.** Starting the conversation does not need a stack runtime. Deterministic plugin checks need Python 3. A missing stack tool leaves that check unavailable. None of those gaps is a pass.
- **Existing files changed since the proposal.** The skill stops, keeps the unexpected edit, and asks again before writing over it.
- **Canvas does not open.** Use the same sections in chat. That is the documented fallback.
- **The reviewer did not run.** The result should say independent review is pending or unavailable. Ask for a named human review, or run the workflow again when delegation works. There is no automatic repair.
- **You ran the same command and nothing changed.** That is a complete result. No files should be rewritten.

## Maintainer notes

`.cursor-plugin/plugin.json` is the plugin version. After a merge to `main`, GitHub Actions inspects Conventional Commits since the last tag. A `feat:` commit bumps the minor version. A `fix:` or `perf:` commit bumps the patch version. A breaking change bumps the major version. Documentation-only commits do not publish a release.

A release updates `plugin.json`, prepends [CHANGELOG.md](CHANGELOG.md), tags `vX.Y.Z`, and creates a GitHub Release.

Plugin maintainers can run:

```sh
python3 tests/skill_contracts.py
python3 tests/context_tools_tests.py
python3 tests/release_contracts.py
```

Those checks do not open Cursor, Jira, Figma, or Canvas. Use [MANUAL_EVALUATION.md](MANUAL_EVALUATION.md) for the live scenarios.

When you open a pull request for this repository, fill in [.github/pull_request_template.md](.github/pull_request_template.md) from the diff and the checks you actually ran.
