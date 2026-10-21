# Work record

Where approved work lives. Jira is the source of truth for Stories, scope,
acceptance criteria, non-functional requirements (NFR — constraints such as
security, performance, accessibility, or compatibility when they are
approved), and technical refinement. Git holds code, tests, configuration,
and sanitized fixtures. Do not create `artifacts/tickets/<ID>/`, Markdown
Story mirrors, or mandatory `spec.md` / `plan.md` / `review.md` per run. Do
not add automatic cleanup at merge.

## What goes where

- **Story, scope, acceptance criteria, and approved NFR:** Jira fields or
  description on that issue. Follow the calling skill for field location.
- **Technical refinement (development or QA):** the matching Task, Subtask,
  or technical issue in Jira.
- **Shared validation result:** a compact Jira comment on the validated
  item, only when that write is authorized.
- **Long report:** an optional Jira attachment, only when it adds information
  that should not sit in the comment body.
- **Code, tests, configuration, sanitized fixtures:** Git.
- **Repository context and durable architecture decisions:** existing
  context documents and architecture decision records. Follow
  [architecture-decisions.md](architecture-decisions.md). Do not copy
  that log into module context.
- **Intermediate drafts:** chat, Canvas, or throwaway files. They do not
  need versioning.

A historical attachment is not a second live specification. Label it with
purpose, Jira item, date, code state, and the requirement snapshot digest
when those values exist. Do not invent them.

Do not attach a report for every attempt. Prefer one summary per milestone,
then a delta when a later review replaces earlier evidence.

Keep compatibility with a Product Owner's custom Jira template. Propose an
adjustment when one is needed. Do not overwrite that template.

## Optional validation comment

After `/validate-change` has shown the result in chat or Canvas, offer a
compact comment on the validated issue. Show the exact destination and
payload before any write. Follow [approval-contract.md](approval-contract.md)
and [Jira integration](jira-integration.md). Running `/validate-change` does
not by itself authorize a comment. Reuse an authorization already given in
this session only when it covers that exact payload.

Include:

- baseline and reviewed code state, including uncommitted changes;
- compared requirements and drift status;
- criteria verified, failed, pending, or not-verifiable;
- checks run and mock or environment limits;
- independent validator status, Bugbot status, and blockers;
- links to existing, reachable evidence.

If more than one issue is in play, show how the content would be split. Do
not publish automatically to every parent and Subtask.

Do not change status, assignee, or acceptance criteria, and do not create
issues, by implication.

Example shape (values must come from this run):

```markdown
Validation for PAY-123
Code: `abc123def` plus uncommitted `src/foo.ts`
Requirements: unchanged (digest `9f3a2c1b0d4e5f67`)
Criteria: AC-01 verified; AC-02 pending
Checks: `pytest tests/test_foo.py` passed; end-to-end skipped (no environment)
Validator: completed. Bugbot: passed on that code state.
Blockers: none
Ready for the developer to deliver: no (AC-02 pending)
```

## Optional attachment

Offer an attachment only when the compact comment cannot hold the evidence.
Name the file, purpose, and content in the same proposal. Use only an
attachment capability that this host actually exposes. If a temporary file
is required, write it outside the versioned tree. Do not claim it was
attached without confirmation. Do not create a Markdown file in the
repository as a fallback. Do not publish secrets, sensitive data, or raw
logs.

After a timeout or partial failure, read the issue before retrying. If
success cannot be determined, report uncertainty. Do not duplicate the
comment or attachment.

Technical validation and publication status are separate. Declining the
comment, or failing to publish it, does not by itself change the technical
conclusion.
