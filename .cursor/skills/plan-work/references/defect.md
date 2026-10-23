# Defect

Use this reference when the request is a new defect, a bug report, or an
existing ticket that still lacks expected versus actual behavior. Do not
use it for a User Story, Task, Epic, or Sprint Backlog.

A defect is a drafting kind. It is not a fourth parent level in Epic →
User Story → Task. Discover the connected site's actual issue type before
publication. Do not assume that type is named Bug.

When an existing ticket already has expected versus actual behavior,
reproduction, and observable resolution criteria, and the user did not
ask to draft or update it here, do not re-draft it. Give a
`/implement-change` handoff. Honor an explicit request to draft or
update that ticket.

## What to draft

Propose:

- title;
- expected behavior;
- actual behavior;
- impact;
- reproduction steps and environment, when those are known;
- evidence, with a source for each claim;
- open questions;
- observable resolution criteria.

Do not force this into "As a user, I want…". Do not invent a fake actor
to make it look like a User Story.

## Facts, hypotheses, and diagnoses

Separate:

- facts, with their source;
- hypotheses, labeled as hypotheses;
- a confirmed diagnosis, only when evidence supports it.

Do not require a confirmed root cause to draft or publish a defect.
Preserve a diagnosis the reporter already supplied. Leave deep causal
investigation to `/implement-change`, or to `/refine-story` when the
change needs a technical or QA split this ticket does not already cover.

## Approval and publication

The authorized user in this session approves the exact Jira payload.
Do not invent a second Product Owner step or a dedicated defect-owner
role. Follow [approval-contract.md](../../../../references/approval-contract.md)
and [Jira integration](../../../../references/jira-integration.md).

Do not apply the User Story description template to a defect. Put
resolution criteria in the issue type's acceptance-criteria field when
that field is identified and writable. Otherwise use the agreed
destination in the same payload.

## Related work

A recommended parent or related item is a logical relationship, for
example "this defect affects Story X" or "this Task supports that
defect". It is not by itself a Jira parent link. Discover the site's
issue types before proposing a relationship. Publication still discovers
whether to create a Subtask under that ticket or a linked Task. Never
create a related item silently.
