# Jira integration contract

Use the Atlassian MCP supplied by the host Cursor session. Do not hardcode an MCP server ID, an Atlassian site, or a project key.

At the start of a Jira operation, discover which Jira tools are available. Resolve the site and project from the user-provided URL, key, or approved project context. Verify access plus the required issue types and fields before preparing a write.

A board URL identifies a planning board. It does not by itself identify the project that will receive new issues, because one board can show issues from several projects. When a skill needs a stable site, project, or optional board reference, follow [project-onboarding.md](project-onboarding.md). That reference does not authorize creating or editing Jira records.

Classify Jira results precisely:

- **Disconnected:** the MCP server cannot be reached.
- **Unauthorized:** the server responds but the current user lacks access.
- **Unavailable:** the requested tool or capability is not exposed.
- **Successful empty:** the query ran successfully and found no matching records.
- **Successful:** the query returned records or fields.

For reads, retrieve only the current issue fields and relationships needed for the workflow. For duplicate search, report the query limits. If Jira is unavailable, say that the search was unavailable; never report that no duplicates exist.

Before a write, show the exact creation or update payload. Author description and other rich-text fields as Markdown. Do not hand-write Jira wiki markup. The Atlassian MCP converts Markdown on write, and wiki input is stored as literal text or escaped markers. When the issue type has an acceptance-criteria field, write acceptance criteria only in that field. Discover the field from the issue type. Do not hardcode a custom field id, and do not also place those criteria in the description.

Preserve unrelated fields. Re-read relevant fields before applying an approved update. If concurrent edits materially change the approved payload, show the revised diff and seek approval again.

After an uncertain or partial write, read the target before retrying. Do not claim idempotency unless the available tool documents it. If a creation may have succeeded but no reliable record can be identified, stop and report the ambiguity. Confirmed writes must report their issue key and URL. Keep disconnected operations pending and resume them without restarting the intake.
