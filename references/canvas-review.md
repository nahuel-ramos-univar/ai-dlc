# Canvas review

`/sync-context` and `/plan-work` close with the host's Canvas capability when the current host can open one beside the chat. Follow the host's own canvas skill for whether Canvas is available on this host, where the file lives, and its exact format; this contract does not hardcode a canvas path, and it does not restate Cursor's own file-naming or linking rules. When Canvas is available, the host creates the file and places the reference in the chat reply; when the host cannot open a Canvas, present the same sections in chat instead and say Canvas is unavailable on this host. Do not assume either way without checking — host support for Canvas changes over time, and this contract must not freeze in an assumption about which hosts can or cannot open one. Do not claim that writing a `.tsx` file opened a panel on a host that cannot render one.

The Canvas is a view of the proposal and of the files actually written. It is not a second source of truth. An edit in the Canvas is not approval. After a write, refresh the Canvas from the files or the Jira record just read back. Do not restate the earlier proposal as if it were the saved result.

When this skill names a canvas file for an example, such as `plan-work-result.canvas.tsx` or `sync-context-result.canvas.tsx`, that is an illustrative, descriptive, kebab-case name, not a required literal filename; reuse the same file on the next run for the same skill in this workspace so the Canvas stays the current result rather than accumulating stale copies.

Follow the host canvas skill for the file format. Do not commit the canvas into the consumer repository, and do not add a Markdown twin under `aidlc-docs/` just to fill it.

Open or refresh a Canvas only for a result that genuinely benefits from a visual, interactive, or structured view: a proposal, a backlog, a migration diff, or a written result with several parts worth seeing at once. A run with no relevant changes, or any other short status with nothing new to show, gets a short chat reply instead — do not open or refresh a Canvas just to report that nothing changed, and do not treat opening a Canvas as mandatory ceremony independent of whether it helps this result.

## sync-context

Show:

- the outcome: first-time generation, relevant updates applied, no relevant changes, partial verification, or blocked;
- each repository and module, with its status;
- files created, updated, unchanged, failed, or pending;
- evidence examined, and the unknowns;
- the deterministic validation result;
- the independent review result, or the skip or unavailable reason;
- change sets A, B, and C: applied, proposed and pending approval, declined, or not applicable.

When change set C is in play, also show the migration review content in [legacy-migration.md](../.cursor/skills/sync-context/references/legacy-migration.md).

A run whose outcome is "no relevant changes" states that outcome in a short chat reply; it does not open or refresh a Canvas for it.

## plan-work

Show:

- the planning level and each proposed item;
- the description, and the acceptance criteria as their own block;
- the parent recommendation and why it fits;
- dependencies, assumptions, and open questions;
- the deterministic validation result;
- reviewer findings, or a visible "no findings" result;
- the Jira payload split into description and acceptance criteria, and whether a Jira write is approved;
- after a write, the issue key and URL from the record just read, or a pending write.

A Task or an Epic uses its own fields. Do not force either into the User Story description skeleton.
