# Jira integration contract

Use the Atlassian MCP supplied by the host Cursor session. Do not hardcode an MCP server ID, an Atlassian site, or a project key.

At the start of a Jira operation, discover which Jira tools are available. Resolve the site and project from the user-provided URL, key, or approved project context. Verify access plus the required issue types and fields before preparing a write.

Classify Jira results precisely:

- **Disconnected:** the MCP server cannot be reached.
- **Unauthorized:** the server responds but the current user lacks access.
- **Unavailable:** the requested tool or capability is not exposed.
- **Successful empty:** the query ran successfully and found no matching records.
- **Successful:** the query returned records or fields.

For reads, retrieve only the current issue fields and relationships needed for the workflow. For duplicate search, report the query limits. If Jira is unavailable, say that the search was unavailable; never report that no duplicates exist.

Before a write, show the exact creation or update payload. Preserve unrelated fields. Re-read relevant fields before applying an approved update. If concurrent edits materially change the approved payload, show the revised diff and seek approval again.

After an uncertain or partial write, read the target before retrying. Do not claim idempotency unless the available tool documents it. If a creation may have succeeded but no reliable record can be identified, stop and report the ambiguity. Confirmed writes must report their issue key and URL. Keep disconnected operations pending and resume them without restarting the intake.
