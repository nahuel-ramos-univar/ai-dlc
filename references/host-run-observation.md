# Host run observation

Optional Cursor adapter. It is not part of the methodology core, and it is
not required for any skill to complete.

Do not install this observer in consumer repositories automatically.
Copy it only when a person asks to measure tool calls, subagent runs, or
host-supplied token fields in that workspace.

## What it records

Keep a JSON line per event with only:

- event name;
- conversation, generation, parent, child, and tool-call ids when present;
- model id and subagent model when present;
- tool name or subagent type;
- duration, message count, tool-call count, and loop count when present;
- success, failure type, or stop status;
- `input_tokens`, `output_tokens`, `cache_read_tokens`, and
  `cache_write_tokens` when the host payload includes them.

Missing token fields are unavailable, not zero. Null counters are
unavailable, not zero. Official Cursor hook docs do not list those
token fields on every event. Treat them as optional. A parent-turn
total is not a per-skill total, and it does not prove subagents were
included.

Do not store prompts, file contents, tool arguments, or MCP bodies.
Do not store shell commands, reviewer task text, or secrets.

## How to enable it

1. Copy `optional/cursor-observation/observe.py` to
   `.cursor/hooks/observe.py` in the target workspace.
2. Merge `optional/cursor-observation/hooks.fragment.json` into that
   workspace `.cursor/hooks.json`. Keep any hooks already there.
   `subagentStart` must keep `--permission-allow` so a logging failure
   still returns `{"permission":"allow"}`.
3. Leave `AIDLC_OBSERVE_LOG` unset to write outside the source
   repository, under the process temp directory. Set it only to override
   that path. If you point it at `.aidlc/observation.jsonl` inside the
   repo, `content_fingerprint` still excludes that known telemetry file.
   It does not exclude the rest of `.aidlc/`.
4. Confirm the Hooks output channel shows the script. Restart Cursor if
   the file is not loaded.

Fail open. A hook crash must not block the agent. `subagentStart` is a
permission hook: it always allows. Other observational hooks return `{}`.
This adapter does not approve writes, deny tools, or follow up with more
agent turns. Observation files are never source evidence.

Show recorded numbers on Canvas only through the Run cost rules in
[canvas-review.md](canvas-review.md). A missing log is unavailable, not
an empty successful run.

## What it does not replace

Independent review, Bugbot, acceptance evidence, and Jira as the work
record stay required. Observation can explain why a reviewer ran more
than once. It cannot authorize skipping that review.
