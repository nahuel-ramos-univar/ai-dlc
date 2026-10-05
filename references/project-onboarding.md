# Project onboarding

Use this reference only when project references are missing, ambiguous, or the user is explicitly reconsidering them. Do not read it on every `sync-context` or `scaffold-project` run. Reading it is an instruction for that run, not a loader.

This file does not replace [jira-integration.md](jira-integration.md), [repository-preflight.md](repository-preflight.md), or the project-rule contract in `sync-context`'s [project-rules.md](../.cursor/skills/sync-context/references/project-rules.md). Those remain the source of truth for Jira access, repository identity, and rule writes.

## Discover before asking

Inside the authorized scope, look at what is already there before asking:

- the Git root and configured remotes, from local Git;
- persisted repository identity and artifact-home placement;
- `.ai-dlc-config.md`, including `## Context identities` and any existing `## Project references`;
- README, CONTRIBUTING, and engineering docs that state a convention;
- existing Cursor rules and other agent instructions;
- formatter, linter, type-check, test, and build configuration;
- project commands and CI configuration that are already present;
- a Jira or design link the user supplied for this request;
- a recurring ticket-key pattern (for example `NBA2-677`, `CTY-311`) in file
  names, branch names, commit messages, or archived task docs. This is not
  proof of a confirmed project — it is evidence that one is likely already
  in daily use. Treat it the same as any other discovered-but-unconfirmed
  signal: worth asking about, never worth writing into `## Project
  references` on its own.

A repository already having a persisted `## Context identities` entry does
not mean Jira or Figma onboarding already happened for it. Identity and
project references are two different, independently-confirmed things;
check for `## Project references` on its own merits, including during a
legacy-coordinator migration where every repository being moved to
distributed context may still be missing it.

Check each repository's section independently, then ask once for the
engagement. When the repositories in scope show the same confirmed Jira
project, reuse that confirmation for the others. Do not ask the same
question again for every repository. A ticket-key pattern is not permission
to write the project, the site, or a board. A confirmed project key is not
permission to invent a site or a board that nobody confirmed.

Do not scan unrelated repositories, private files, secrets, or the whole workspace by default. Do not treat a remote URL as permission to reach it over the network.

Label each item as one of: configured and verified, confirmed by the user but not verified, an observed convention that is not a team policy, missing, or conflicting. An existing config file does not prove its commands pass. A URL does not prove authenticated access. A repeated coding pattern is not a team policy.

## Ask only for a real gap

Ask one grouped question, with a recommended option when the evidence supports one. Offer to skip optional setup. Do not ask for a fact already established. Do not ask a business user to choose low-level technical conventions. Do not invent a standard the responsible person has not confirmed.

Separate what is required to continue from what is optional. A missing Jira or Figma reference does not block local discovery or a local scaffold.

## Jira

Follow [jira-integration.md](jira-integration.md) for how to classify MCP access. Do not add a client, a server id, or a stored credential.

A user may supply a board URL, a project URL or key, or an existing issue URL. They mean different things:

- A board is a planning view. It can include issues from more than one project.
- A project is the destination for future issue creation.
- An issue is context for this task. It is not a project-wide default unless the user says so.

When a board URL is supplied, resolve that board with the host's authenticated Atlassian tools. Prefer a direct lookup. If the available tool can only find the board by listing boards, that read-only lookup is allowed for the supplied link. Do not list every board as an onboarding step, and do not ask the user to pick again when the link already identifies the board. Inspect associated projects or the board filter only when the tool supports it. If the issue-creation project is still ambiguous, ask one question. Access to the board is not permission to create issues.

Without a link, reuse a confirmed `## Project references` entry. If none exists and Jira is relevant to the request, ask for a board or project link. Do not enumerate boards by default.

If the MCP is unavailable, unauthenticated, or cannot resolve the target, say so. A user-confirmed value may still be saved, but call it confirmed, not verified. Continue local work that does not need Jira. Do not claim the Jira content was read. Do not ask for credentials in chat or write tokens into project files.

`sync-context` and `scaffold-project` do not create or modify Jira issues, boards, sprints, or workflows.

## Git

Discover the Git root and remotes with local Git. Do not ask for a GitHub URL when the repository is already identified. Do not require GitHub. Keep GitLab, Bitbucket, and local-only repositories.

Leave identity as it is. Persisted identity wins. If several remotes are plausible, use the existing unresolved behavior in [repository-preflight.md](repository-preflight.md). Do not change `normalize_remote` or invent a new id. Do not initialize Git, clone, create a remote, or create a hosted repository.

For an empty scaffold destination, a remote URL stays optional unless the approved scaffold proposal needs one. If the request requires `git init`, cloning, or a new remote, say that this skill does not do that and ask how to proceed.

## Figma

Ask about a design reference only for UI work, or when the user mentions design. Accept a file or frame link. Clarify the role only when it is not already clear: `approved-design`, `design-system`, or `inspiration`. Inspiration is not an approved requirement.

Use an existing host tool for a read-only check when it is authenticated and the reference matters to this request. Do not add a Figma client. If access is missing, keep the link as confirmed and unverified. Do not claim that frames, components, or tokens were inspected.

Do not block backend or infrastructure work because Figma is absent. A feature-specific frame stays with that task. Do not save it as a project default unless the user asks.

## What to persist

Persist only values the user confirmed, inside the approved change set for `.ai-dlc-config.md`. Put them in `## Project references`, immediately after `## Context identities`. Do not add these keys inside `## Context identities`.

Supported fields, each omitted when unknown:

- `Jira site`: host only, such as `example.atlassian.net`. Not a URL.
- `Jira project`: the project key, such as `PROJ`.
- `Jira board`: optional board URL.
- `Figma reference`: optional URL.
- `Figma role`: `approved-design`, `design-system`, or `inspiration`.

Those examples are illustrations, not defaults for this plugin. Do not write a placeholder or an empty section. Do not store a one-off issue link as a project default unless the user asks. Do not store credentials, tokens, machine paths, or a claim that authentication will still work next time.

Write each field in the canonical format: a line starting with `- `, the field name, `: `, and the value wrapped in backticks (for example `` - Jira site: `example.atlassian.net` ``). A value that is not wrapped in backticks is not a formatting nicety here — `parse_project_references` treats a recognized field name in that shape as `invalid`, not as missing, so always write the backtick form. Omit a field you do not know. Do not write it with an empty or whitespace-only value; that is `invalid`, not "absent."

`parse_project_references` in `scripts/context_tools.py` reads the section. A missing section is valid (`"missing"`). A live heading with no recognized field — empty, or holding only an unrelated note — is also `"missing"`: nothing was confirmed in it, so it must never be read as completed onboarding. A second live `## Project references` heading, or a recognized field name that appears more than once — even once in the canonical backtick form and once without it — is `"ambiguous"`: show the conflict and do not pick one of the values. Duplicate detection happens before any value is chosen, including when one of the copies is empty. A recognized field whose value fails validation (empty, not a bare host, not an absolute `http`/`https` URL, an unrecognized Figma role, a role with no reference) is `"invalid"`. For every status other than `"ok"`, including `"invalid"`, the parser reports no values at all — a rejected or ambiguous field is never available to be reused as if it were confirmed. Reuse the existing section when updating it. Preserve unrelated configuration and human-authored lines. Propose a change to an existing value explicitly.

`"ok"` means the fields that are present passed parsing and syntax validation. It does not mean every field the current operation needs is present. It does not prove the user confirmed the value for this run, that a host integration is authenticated, that the resource exists, or that the user has permission. Before an operation, check the inputs that operation actually needs. Do not require every optional field, and do not reopen onboarding questions only because a board URL or a Figma reference is absent. There is no separate readiness schema for this section.

Validation of `Jira site`, `Jira board`, and `Figma reference` checks only syntax, using URL parsing plus a small host check: a bare host for the site (no empty DNS label such as `jira..example.com`, no backslash), an absolute `http`/`https` URL with no userinfo at all for the board and the Figma reference (including `https://@host/...`). A single trailing DNS dot, a single-label internal host, IPv4, and a bracketed IPv6 URL are valid syntax. A syntactically valid value here does not mean the host is reachable, the resource exists, or the user has permission to read it — that is still a separate, best-effort read-only check, not something this parser confirms.

A pending, user-confirmed change to this section (switching the Jira board, for example) is still change-set-A work even when every source document's content fingerprint is `"unchanged"` — a fingerprint never covers this section. Surface it through `context_sync_outcome`'s `project_reference_pending` input so it stays reachable instead of folding into "no relevant changes."

A supplied link allows the read-only discovery described above. It does not authorize a write. Include the config diff in the existing approval flow.

There is no separate memory of declined answers. Reuse the decline and defer behavior already defined for project rules and Bugbot when the question is one of those decisions. Do not add a new state machine for Jira or Figma. If the user declines an optional reference, leave the field out and do not ask again in the same run.

## Conventions

Discover existing formatters, linters, test setup, documented conventions, and project rules. Do not turn an observed pattern into a mandatory policy.

A project rule is proposed only through [project-rules.md](../.cursor/skills/sync-context/references/project-rules.md), as change set B. Approving coding guidelines does not approve Bugbot configuration, and the reverse is also true.

`sync-context` does not install dependencies, change tooling or CI, or reformat source. If that work is needed, report it as a follow-up.

`scaffold-project` may include already confirmed conventions and existing tooling in its normal initial proposal. Approval of a prose rule does not approve dependency installation or CI changes. Do not start a second `sync-context` run in order to repeat onboarding, and do not claim that another slash command ran.
