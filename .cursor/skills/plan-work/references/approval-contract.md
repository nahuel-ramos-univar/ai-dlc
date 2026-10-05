# Approval contract

Before any external write, present the exact target and material changes:

- Jira project, issue key, fields, links, comments, or newly created records;
- description and acceptance criteria as separate fields when the issue type has an acceptance-criteria field;
- Git branch and files for an optional intent PR;
- any duplicate noticed incidentally, not the result of a standalone duplicate search;
- any tool-documented idempotency behavior for a retried write, which is write recovery and not a duplicate search;
- known partial-failure recovery behavior.

Approval applies only to that listed change set. A later scope change requires new approval. If the write fails after partial success, inspect the target before retrying and report the confirmed state. If creation may have succeeded but no reliable record can be identified, stop and report the ambiguity rather than creating another issue.
