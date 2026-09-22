# Skill composition

Each skill is a manual slash entry point. Naming another skill or showing its slash command does not execute it.

Use local references as shared instructions inside the current workflow. When work must move to another skill, provide a clear handoff such as `/refine-story PAY-123` and state what evidence the user should carry forward.

The plugin manifest discovers agent files from its relative `agents/` path. Do not assume an agent filename or frontmatter name is a valid runtime `subagent_type`.

When the host exposes a general-purpose independent subagent but cannot invoke a named plugin agent directly, the main chat may provide the relevant agent file as bounded task context. Report that as a general-purpose independent review, not as native named-agent dispatch. If the host cannot run an independent subagent, keep the review unavailable or pending.

Do not create circular calls. A later skill can return a focused question or finding to an earlier skill, but it must not claim that the earlier slash command ran automatically.

All reference paths are relative to the installed plugin. Do not use machine-specific absolute paths.
