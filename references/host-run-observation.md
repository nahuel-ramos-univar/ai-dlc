# Host run observation

Optional Cursor adapter. It is not part of the methodology core, and it is
not required for any skill to complete.

Do not install this observer in consumer repositories automatically.
Copy it only when a person asks to measure tool calls, subagent runs, or
host-supplied token fields in that workspace.

## What it records

Keep a JSON line per event with `schema_version` 1 and only:

- event name;
- conversation, generation, parent, child, tool-call, and tool-use ids when present;
- model id and subagent model when present;
- tool name or subagent type;
- duration, message count, tool-call count, and loop count when present;
- success, failure type, or stop status;
- `input_tokens`, `output_tokens`, `cache_read_tokens`, and
  `cache_write_tokens` when the host payload includes them;
- for `preCompact` only: `trigger`, `context_usage_percent`,
  `context_tokens`, `context_window_size`, `message_count`,
  `messages_to_compact`, and `is_first_compaction`.

Missing token fields are unavailable, not zero. Null counters are
unavailable, not zero. Invalid numeric values are rejected, not stored
as counts. Official Cursor hook docs do not list those token fields on
every event. Treat them as optional. A parent-turn total is not a
per-skill total, and it does not prove subagents were included.

Do not invent skill identity or `run_id` from host metadata. A
conversation may contain several skill runs.

Do not store prompts, file contents, tool arguments, or MCP bodies.
Do not store shell commands, reviewer task text, or secrets.

`preCompact` is observational. The hook returns `{}`. It does not send
`user_message`, inject context, block compaction, or change compaction.

Records without `schema_version` are legacy. A later version is
unsupported. Do not treat either as silent current-schema data.

## How to enable it

Keep hooks already present in the workspace. Do not overwrite consumer
or user hook configuration automatically. Merge only the events below.

1. Copy `optional/cursor-observation/observe.py` to
   `.cursor/hooks/observe.py` in the target workspace. Executable
   permission is not required.
2. Merge `optional/cursor-observation/hooks.fragment.json` into that
   workspace `.cursor/hooks.json`. Keep any hooks already there.
   Hook commands use `python3 .cursor/hooks/observe.py` so the file
   does not need to be executable. `subagentStart` must keep
   `--permission-allow` so a logging failure still returns
   `{"permission":"allow"}`.
3. Leave `AIDLC_OBSERVE_LOG` unset to write outside the source
   repository, under the process temp directory. Set it only to override
   that path. If you point it at `.aidlc/observation.jsonl` inside the
   repo, `content_fingerprint` still excludes that known telemetry file.
   It does not exclude the rest of `.aidlc/`. Fingerprint exclusion does
   not itself make a file Git-ignored.
4. Confirm the Hooks output channel shows the script. Restart Cursor if
   the file is not loaded.

Fail open. A hook crash must not block the agent. `subagentStart` is a
permission hook: it always allows. Other observational hooks return `{}`.
This adapter does not approve writes, deny tools, or follow up with more
agent turns. Observation files are never source evidence.

On a logging failure the process still prints valid hook JSON to stdout
and exits 0. It may print a short `observation: logging failed
(ErrorType)` line to stderr. That line has no payload and no path.

Show recorded numbers on Canvas only through the Run cost rules in
[canvas-review.md](canvas-review.md). A missing log is unavailable, not
an empty successful run.

## Storage location

The default file is keyed by the process current working directory, not
by conversation or skill. Several conversations in the same cwd share
one file.

Default path:

1. Resolve the cwd (`Path.cwd().resolve()`).
2. Take the first 12 hex characters of the SHA-256 of that string.
3. Write `{tempfile.gettempdir()}/aidlc-observation/{digest}.jsonl`.

Discover the path used for the current cwd:

```
python3 .cursor/hooks/observe.py --print-log-path
```

Temporary logs may disappear when the OS clears the temp directory.
For a durable file, set `AIDLC_OBSERVE_LOG` to an absolute path outside
the repository.

Cloud Agent logs live on that agent's remote machine. Export them
explicitly if you need them locally. Runtime logs and summaries are not
committed or pushed.

There is no automatic rotation. Delete or truncate the JSONL by hand
when it grows too large.

## Smoke check

A successful hook response is not evidence that a record was written.
After copying the adapter:

```
python3 .cursor/hooks/observe.py --print-log-path
echo '{"hook_event_name":"stop"}' | python3 .cursor/hooks/observe.py
```

Confirm a JSON line was appended to the printed path. Then:

```
python3 .cursor/hooks/observe.py --summary
```

That synthetic check does not prove Cursor dispatched the hook.

## Summary

Do not generate a summary after every event. Read the JSONL later:

```
python3 .cursor/hooks/observe.py --summary
python3 .cursor/hooks/observe.py --summary --conversation CONVERSATION_ID
python3 .cursor/hooks/observe.py --summary --output /tmp/observation-summary.json
```

The summary goes to stdout. `--output` writes the same JSON to an
explicit path. It refuses `--output` when that path is the input log,
including symlink and hardlink aliases, and exits nonzero without
writing. It reports received events, identifiable tool or subagent
invocations, and uncorrelated events separately. Repeated invocations
are counted by type without calling them redundant reviews. Invocation
ids are scoped by conversation. It reports correlation coverage,
unmatched starts and stops, malformed lines, available durations versus
elapsed `recorded_at` time, `preCompact` count and maximum pressure from
those events only, and token-field coverage with limitations. Invalid
metrics are excluded from sums and maxima. It does not sum token
counters. It does not load transcripts.

## What it does not replace

Independent review, Bugbot, acceptance evidence, and Jira as the work
record stay required. Observation can explain why a reviewer ran more
than once. It cannot authorize skipping that review.
