# Canvas review

The closing result of `/sync-context` and `/plan-work` is a Canvas when the host can open one beside the chat. Cursor agents cannot open a Canvas today. On that host, present the same sections in chat and say Canvas is unavailable. Do not claim that writing a `.tsx` file opened a panel.

The Canvas is a view of the proposal and of the files actually written. It is not a second source of truth. An edit in the Canvas is not approval. After a write, refresh the Canvas from the files or the Jira record just read back. Do not restate the earlier proposal as if it were the saved result.

Write one canvas file for the active workspace, where the host keeps canvases, and update that same file on the next run:

- `sync-context-result.canvas.tsx`
- `plan-work-result.canvas.tsx`

Follow the host canvas skill for the file format. Do not commit the canvas into the consumer repository, and do not add a Markdown twin under `aidlc-docs/` just to fill it.

When the Canvas opens, the chat reply is a short outcome plus a link to that file. Do not paste the full report again in chat. When the Canvas is unavailable, the chat reply is the full report.

A run with no relevant changes still shows this closing result. It does not open an approval prompt and it does not rewrite documents.

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

## plan-work

Show:

- the planning level and each proposed item;
- the description, and the acceptance criteria as their own block;
- the parent recommendation and why it fits;
- dependencies, assumptions, and open questions;
- reviewer findings, or a visible "no findings" result;
- the Jira payload split into description and acceptance criteria, and whether a Jira write is approved;
- after a write, the issue key and URL from the record just read, or a pending write.

A Task or an Epic uses its own fields. Do not force either into the User Story description skeleton.
