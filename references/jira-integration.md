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

For reads, retrieve only the current issue fields and relationships needed for the workflow. `/plan-work` does not run a standalone duplicate search. If some other workflow does search for duplicates, report the query limits, and if Jira is unavailable say the search was unavailable rather than reporting that no duplicates exist.

Before a write, show the exact creation or update payload. Author description and other rich-text fields as Markdown. Do not hand-write Jira wiki markup. The Atlassian MCP converts Markdown on write, and wiki input is stored as literal text or escaped markers. When the issue type has an acceptance-criteria field, write acceptance criteria only in that field. Discover the field from the issue type. Do not hardcode a custom field id, and do not also place those criteria in the description. When that field is missing, follow the calling skill. `plan-work` keeps business criteria in the local proposal unless the Product Owner explicitly chooses the description for that write. `refine-story` offers technical criteria as a Technical acceptance criteria section in the description, inside the same approved payload, and keeps publication pending when no location is approved.

Jira's own issue-type hierarchy is not the same shape as this plugin's Epic → User Story → Task planning levels. In standard Jira, Epic is the top level; Story, Task, and Bug normally sit as peers directly under an Epic, with no parent relationship among themselves; Subtask sits under a Story, a Task, or a Bug. Before creating any Jira parent link, discover the connected site's actual issue types and hierarchy for the target project; do not assume a `parent` or `epicLink` field accepts the same shape as this plugin's conceptual model.

A recommended parent in this plugin is a logical relationship, for example "this Task supports Story X". It does not by itself choose the Jira issue type. When a Task supports a Story, put the exact issue type in the payload the approver the calling skill authorizes approves, after discovering what the site allows. Typical options are: create a Jira Subtask under that Story, or create a Jira Task and link it to that Story. Do not parent a Subtask under an Epic. Do not silently change a Task into a Subtask because a Story was recommended as its parent. If the site's hierarchy configuration cannot be discovered, say so and ask which issue type to use rather than guessing. Who that approver is comes from the calling skill: `plan-work` uses the Product Owner for business content, and `refine-story` uses the authorized developer for technical content inside approved business scope.

## Dependencies as issue links
A dependency drafted in a proposal is prose until it is approved for publication. At publication, create it as a real Jira issue link, not only text in a description. Discover which Jira tools are available in this session before calling them. A tool name in this contract is not proof that this session can call it.

Approve the relationship in plain language, using the draft's own identifiers, for example "Story A blocks Story B". A new issue has no Jira key yet, so do not wait for both keys before asking. One confirmation covers the issues, the relationships, and any optional fields below. Do not ask again only because the keys were missing at approval time.

After that confirmation:

1. Create the authorized issues and record the keys Jira returns.
2. Discover the site's link types with `listJiraIssueLinkTypes`. Map the approved sentence onto one discovered type using that type's own inward and outward labels. Do not apply one type's orientation to every type. A site can configure Blocks and Depends so the same dependency points opposite ways. When the discovered type is Blocks, the verified mapping on this organization's Jira is inward = the blocker and outward = the blocked issue. For any other type, use the labels just read.
3. Call `createJiraIssueLink` with the keys from step 1.
4. Re-read both issues' links. A successful create response does not prove the direction. If the stored relationship does not mean the approved sentence, delete that link, stop, and ask. Do not flip the keys and continue.
5. If the destination issue or the meaning of the relationship changes after approval, ask again before creating the link.

## Optional suggested fields
When preparing a Jira write payload, the approver the calling skill authorizes may also want Priority, Labels, Fix Version, Sprint, or Story Points filled in. Offer a value only when real evidence supports it, and label it as a suggestion. Present every offered value in the same confirmation as the rest of the payload. That approver can accept, edit, or skip any of them in that one reply. Do not ask once per field. Do not invent a value with no evidence behind it, and do not write a skipped or unconfirmed value.

- **Priority** — base it on urgency or risk already stated in this draft, not a default.
- **Labels** — reuse labels already used by the parent Epic or already common in this project; do not invent a new taxonomy.
- **Fix Version** — offer only a version that already exists in the project, confirmed with a Jira read; never invent a release name or date.
- **Sprint** — offer only a sprint that already exists, active or explicitly named, confirmed with a Jira read (for example `listJiraBoardSprints`). Never invent a sprint, a start or end date, or team capacity. This is one item's field value, not Sprint Backlog mode's capacity planning.
- **Story Points** — suggest a number only from already-pointed issues that share this item's team, estimation convention, and a similar scope. Show those issues as the basis. If you cannot confirm that the comparison is on the same scale, do not suggest a number. A number the authorized approver supplies is a human estimate: label it that way, and do not present it as the result of a comparison.

Preserve unrelated fields. Re-read relevant fields before applying an approved update. If concurrent edits materially change the approved payload, show the revised diff and seek approval again.

After an uncertain or partial write, read the target before retrying. Do not claim idempotency unless the available tool documents it. If a creation may have succeeded but no reliable record can be identified, stop and report the ambiguity. Confirmed writes must report their issue key and URL. Keep disconnected operations pending and resume them without restarting the intake.
