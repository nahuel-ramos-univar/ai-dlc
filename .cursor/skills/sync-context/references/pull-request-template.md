# Pull request templates

Shared by `scaffold-project` and `sync-context`. This is an optional
repository-configuration file, not a project rule and not Bugbot review
guidance. Do not duplicate this policy in those skills.

Writing a template does not authorize commit, push, pull-request creation, or
merge. Creating the file does not publish it to the team.

## Discover first

Complete repository preflight before offering a template. From local Git,
inspect configured remotes. Classify the Git host from the remote hostname,
not from a word in the repository path:

- a `github.com` host is GitHub;
- a `gitlab.com` host is GitLab;
- a `bitbucket.org` host is Bitbucket Cloud;
- anything else, including GitHub Enterprise Server, self-hosted GitLab,
  Bitbucket Server or Data Center, and a local-only repository with no
  remote, is unknown.

Do not treat `gitlab` or `bitbucket` in the path of a `github.com` remote as
GitLab or Bitbucket. Do not assume GitHub. Do not require a network round-trip
only to create a locally approved file. Do not invent a host from a directory
name.

Then look for an existing template already present in the authorized tree.
GitHub filenames are not case sensitive and may use `.md` or `.txt`:

- GitHub: `pull_request_template.md` at the repository root,
  `docs/pull_request_template.md`, `.github/pull_request_template.md`, and a
  `PULL_REQUEST_TEMPLATE/` directory at the root, in `docs/`, or in `.github/`;
- GitLab: `.gitlab/merge_request_templates/`;
- Bitbucket Cloud: `.bitbucket/pull_request_template.md`.

A root `pull_request_template.md` on a Bitbucket Cloud repository is not that
host's template. Leave it untouched. It does not satisfy Cloud, and it does
not block offering `.bitbucket/pull_request_template.md`. Do not invent a
Bitbucket Server or Data Center file path.

An organization-wide template that lives only on the host cannot be verified
from a local checkout. Mention that possibility as unverified. Do not fetch
it unless an authenticated host tool is already available and the user asked
for that read.

If a supported template file or directory already exists for the identified
host, preserve the customization. Do not overwrite it. Do not add a second
default that duplicates it. Report the existing path as unchanged. This is
not a declined decision.

For an unknown host, treat `.github/`, `.gitlab/`, or
`.bitbucket/pull_request_template.md` only as a hypothesis. Ask which host it
is before proposing a write. Do not write a GitHub path by implication.

## Destination

Propose a file only when no supported template exists yet for that host and
the host is identified:

- GitHub: `<source-root>/.github/pull_request_template.md`;
- GitLab: `<source-root>/.gitlab/merge_request_templates/Default.md`;
- Bitbucket Cloud: `<source-root>/.bitbucket/pull_request_template.md`.

If the host is unknown, record `deferred` and do not write a GitHub path by
implication. If the host is identified but that host's path is not one of
the three above, defer rather than invent a location.

Those three paths, after their own per-repository approval, are the only
pull-request or merge-request template writes allowed by
[repository preflight](../../../../references/repository-preflight.md) and
[context-generation.md](context-generation.md). This is not permission to
write other files under `.github/`, `.gitlab/`, `.bitbucket/`, or a
`PULL_REQUEST_TEMPLATE/` directory.

## Content

Keep the skeleton short. Do not copy this plugin's own
`.github/pull_request_template.md`. Do not paste a whole Jira Story. Do not
invent results. Do not pre-mark checks as passed. Do not include plugin
instructions.

```markdown
## Summary
<!-- Jira or other reference, and why this change exists. -->

## Changes
<!-- Main changes. -->

## Verification
<!-- What was actually checked, and the result. -->

## Risks
<!-- Relevant risks or limitations. Write none if there are none. -->

## Screenshots
<!-- Include only when they help a reviewer. -->
```

Omit Screenshots when the repository has no UI.

## Approval and persistence

Show the exact path and content before writing. Ask once per repository for
the initial offer. Approval of context documents, of a Bugbot proposal, or of
a project rule does not authorize this file, and the reverse is also true.

Identity is the stable repository ID. One default template decision per
repository is enough; this is not a project-rule slug, and it is not keyed
that way because Bugbot happens to use the same cardinality.

Reuse `decision_reprompt_allowed` in `scripts/context_tools.py`. Do not ask
again after `declined` unless the user explicitly asks to reconsider. A
`deferred` result may be reconsidered on a later run, including when a
remote is added later and the host becomes known. Call it with
`same_run=True` before asking again inside the same run.

Persist the decision in the configured artifact home's configuration, keyed
by stable repository ID. Do not create configuration in an unrelated source
repository just to record a decision.

```markdown
## Pull request template decisions
- Repository: `<stable-repository-id>`
  - Decision: declined
  - Host: `github`
  - Baseline: `<git-rev or unversioned>`
  - Fingerprint: `<fingerprint>`
```

Use `approved`, `declined`, or `deferred`. Record `Host` when it was
identified (`github`, `gitlab`, `bitbucket` for Bitbucket Cloud). Omit `Host`
when the host was unknown. Record `Path` only after an `approved` write.

A declined or deferred result is a complete, valid outcome. It does not fail
`scaffold-project` or `sync-context`.

## Freshness

A pull-request template is ordinary source. It is not excluded from
`content_fingerprint` the way a generated index, module context, or
`BUGBOT.md` is. After an approved write, follow the calling skill's existing
finalization order and refresh the affected context. Do not widen
`EXCLUDED_PARTS` or `GENERATED_FILENAMES` to hide that write.
