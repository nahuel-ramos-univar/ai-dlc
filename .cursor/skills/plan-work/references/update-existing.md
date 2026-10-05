# Update existing work

Read the current issue fields, comments needed for context, linked work, and relevant implementation. Preserve unrelated text. Preserve content the Product Owner already approved unless newly read evidence actually conflicts with it; when it does, surface the conflict and let the Product Owner decide rather than silently overwriting the approved value. Running this on an unchanged item must not create a duplicate planning artifact.

Show changes as a field-level diff:

- current value or "unchanged";
- proposed value;
- reason and supporting evidence.

Do not run a standalone duplicate search. If an obvious duplicate is encountered incidentally while reading the current issue or an explicitly referenced issue, surface it. If a prior partial write is possible, identify the existing record by key and content before retrying. That re-read is write recovery, not a duplicate search.
