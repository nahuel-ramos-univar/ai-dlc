# Skill composition

Each skill is a manual slash entry point. Naming another skill or showing its slash command does not execute it.

The only authorized continuous-flow exception is `/implement-change` continuing into `/validate-change` when the user asked for that sequence in the same request. No other skill pair is started this way. `create-e2e-tests` is never started this way. After implementation finishes, load and follow the validate-change workflow and report the seam. Do not claim the user typed `/validate-change`.

Use local references as shared instructions inside the current workflow. When work must move to another skill, provide a clear handoff such as `/refine-story PAY-123` and state what evidence the user should carry forward. Plan-work, refine-story, sync-context, scaffold-project, and create-e2e-tests stay handoffs. Do not generalize this exception.

The plugin manifest discovers agent files from its relative `agents/` path. Do not assume an agent filename or frontmatter name is a valid runtime `subagent_type`.

When the host exposes a general-purpose independent subagent but cannot invoke a named plugin agent directly, the main chat may provide the relevant agent file as bounded task context. Report that as a general-purpose independent review, not as native named-agent dispatch. If the host cannot run an independent subagent, keep the review unavailable or pending.

`/validate-change` always dispatches an independent `validator` for the evidence assessment. That dispatch is work inside the skill, not a second slash command and not a new skill pair. A self-check in the implementing chat is not independent validation.

`/scaffold-project` dispatches an independent `implementation-reviewer` in scaffolding mode except for a documented docs-only skip, always dispatches an independent `context-reviewer` for generated context, and for a code change attempts Bugbot in the main chat. Those dispatches are work inside the skill, not slash commands and not a new skill pair. A self-check in the scaffolding chat is not independent review. A paragraph claiming a review ran is not the review. Writing `BUGBOT.md` is not the Bugbot run.

Do not create circular calls. A later skill can return a focused question or finding to an earlier skill, but it must not claim that the earlier slash command ran automatically.

All reference paths are relative to the installed plugin. Do not use machine-specific absolute paths.
