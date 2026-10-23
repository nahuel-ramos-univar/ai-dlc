#!/usr/bin/env python3
"""Optional Cursor observation hook. Fail open. Store no prompt or payload bodies."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CURRENT_SCHEMA_VERSION = 1
PERMISSION_ALLOW_FLAG = "--permission-allow"
UNAVAILABLE = "unavailable"
INVALID = "invalid"

ALLOWED_KEYS = (
    "hook_event_name",
    "conversation_id",
    "generation_id",
    "parent_conversation_id",
    "child_conversation_id",
    "tool_call_id",
    "tool_use_id",
    "parent_tool_call_id",
    "model",
    "model_id",
    "tool_name",
    "subagent_type",
    "subagent_id",
    "subagent_model",
    "mcp_server_name",
    "status",
    "failure_type",
    "trigger",
)
TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)
COUNTER_KEYS = (
    "message_count",
    "tool_call_count",
    "loop_count",
)
DURATION_KEYS = ("duration", "duration_ms")
PRECOMPACT_METRIC_KEYS = (
    "context_usage_percent",
    "context_tokens",
    "context_window_size",
    "messages_to_compact",
)
METRIC_KEYS = TOKEN_KEYS + COUNTER_KEYS
PERCENT_KEYS = frozenset({"context_usage_percent"})
BOOL_KEYS = ("is_first_compaction",)
IDENTIFIABLE_TOOL_EVENTS = frozenset(
    {"postToolUse", "postToolUseFailure", "afterMCPExecution"}
)
IDENTIFIABLE_SUBAGENT_EVENTS = frozenset({"subagentStart", "subagentStop"})


def _finite_number(value: object) -> int | float | None:
    if type(value) is bool:
        return None
    if type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            return None
        return value
    return None


def metric_value(value: object, *, percent: bool = False) -> int | float | str:
    if value is None:
        return UNAVAILABLE
    number = _finite_number(value)
    if number is None:
        return INVALID
    if number < 0:
        return INVALID
    if percent and number > 100:
        return INVALID
    return number


def summarize(payload: object) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    data = payload if isinstance(payload, dict) else {}
    event_name = data.get("hook_event_name")
    for key in ALLOWED_KEYS:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, str):
            record[key] = value
    for key in METRIC_KEYS:
        record[key] = metric_value(data.get(key))
    for key in DURATION_KEYS:
        if key not in data:
            continue
        record[key] = metric_value(data[key])
    include_precompact = event_name == "preCompact" or any(
        key in data for key in PRECOMPACT_METRIC_KEYS
    )
    if include_precompact:
        for key in PRECOMPACT_METRIC_KEYS:
            if event_name == "preCompact" or key in data:
                record[key] = metric_value(
                    data.get(key), percent=key in PERCENT_KEYS
                )
    if "trigger" in data and isinstance(data["trigger"], str):
        record["trigger"] = data["trigger"]
    for key in BOOL_KEYS:
        if key not in data:
            continue
        value = data[key]
        if type(value) is bool:
            record[key] = value
    return record


def default_log_path(cwd: Path | None = None) -> Path:
    root = (cwd or Path.cwd()).resolve()
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / "aidlc-observation" / f"{digest}.jsonl"


def log_path(cwd: Path | None = None) -> Path:
    configured = os.environ.get("AIDLC_OBSERVE_LOG", "").strip()
    if configured:
        return Path(configured)
    return default_log_path(cwd)


def permission_allow_requested(argv: list[str]) -> bool:
    return PERMISSION_ALLOW_FLAG in argv


def hook_response(permission_allow: bool) -> str:
    if permission_allow:
        return json.dumps({"permission": "allow"}, separators=(",", ":"))
    return "{}"


def diagnostic_message(exc: BaseException) -> str:
    return f"observation: logging failed ({type(exc).__name__})"


def append_record(record: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")


def paths_identify_same_log(source: Path, dest: Path) -> bool:
    try:
        if source.resolve() == dest.resolve():
            return True
    except OSError:
        pass
    try:
        source_stat = source.stat()
        dest_stat = dest.stat()
    except OSError:
        return False
    return source_stat.st_dev == dest_stat.st_dev and source_stat.st_ino == dest_stat.st_ino


def _conversation_scope(record: dict[str, object]) -> str | None:
    value = record.get("conversation_id")
    if isinstance(value, str) and value:
        return value
    return None


def _first_id(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _tool_identity(record: dict[str, object]) -> str | None:
    scope = _conversation_scope(record)
    invocation = _first_id(record.get("tool_use_id"), record.get("tool_call_id"))
    if scope is None or invocation is None:
        return None
    return f"{scope}\0tool:{invocation}"


def _subagent_identity(record: dict[str, object]) -> str | None:
    scope = _conversation_scope(record)
    invocation = _first_id(record.get("subagent_id"), record.get("tool_call_id"))
    if scope is None or invocation is None:
        return None
    return f"{scope}\0subagent:{invocation}"


def option_value(argv: list[str], name: str) -> str | None:
    if name not in argv:
        return None
    index = argv.index(name)
    if index + 1 >= len(argv):
        return None
    value = argv[index + 1]
    if value.startswith("--"):
        return None
    return value


def _parse_recorded_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def _schema_bucket(record: dict[str, object]) -> str:
    if "schema_version" not in record:
        return "legacy"
    version = record.get("schema_version")
    if version == CURRENT_SCHEMA_VERSION:
        return "current"
    return "unsupported"


def recorded_metric(
    record: dict[str, object], key: str, *, percent: bool = False
) -> int | float | str | None:
    if key not in record:
        return None
    value = record[key]
    if value == UNAVAILABLE:
        return UNAVAILABLE
    if value == INVALID:
        return INVALID
    return metric_value(value, percent=percent)


def _valid_number(value: object) -> int | float | None:
    if type(value) in (int, float) and type(value) is not bool:
        if type(value) is float and not math.isfinite(value):
            return None
        return value
    return None


def _coverage(values: list[object]) -> dict[str, object]:
    numeric = 0
    zero = 0
    unavailable = 0
    invalid = 0
    missing = 0
    for value in values:
        if value is None:
            missing += 1
        elif value == UNAVAILABLE:
            unavailable += 1
        elif value == INVALID:
            invalid += 1
        else:
            number = _valid_number(value)
            if number is None:
                invalid += 1
            elif number == 0:
                zero += 1
                numeric += 1
            else:
                numeric += 1
    return {
        "numeric": numeric,
        "zero": zero,
        "unavailable": unavailable,
        "invalid": invalid,
        "missing": missing,
    }


def load_jsonl(path: Path) -> tuple[list[dict[str, object]], int]:
    records: list[dict[str, object]] = []
    malformed = 0
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(parsed, dict):
            malformed += 1
            continue
        records.append(parsed)
    return records, malformed


def summarize_records(
    records: list[dict[str, object]],
    *,
    malformed: int = 0,
    conversation_id: str | None = None,
) -> dict[str, object]:
    scoped = records
    if conversation_id is not None:
        scoped = [
            record
            for record in records
            if record.get("conversation_id") == conversation_id
        ]
    current: list[dict[str, object]] = []
    legacy: list[dict[str, object]] = []
    unsupported_versions: dict[str, int] = {}
    for record in scoped:
        bucket = _schema_bucket(record)
        if bucket == "current":
            current.append(record)
        elif bucket == "legacy":
            legacy.append(record)
        else:
            version = record.get("schema_version")
            unsupported_versions[str(version)] = (
                unsupported_versions.get(str(version), 0) + 1
            )
    usable = current + legacy
    by_type: dict[str, int] = {}
    for record in usable:
        name = record.get("hook_event_name")
        if isinstance(name, str) and name:
            by_type[name] = by_type.get(name, 0) + 1

    tool_ids: set[str] = set()
    uncorrelated_tool_events = 0
    tool_by_type: dict[str, int] = {}
    subagent_ids: set[str] = set()
    uncorrelated_subagent_events = 0
    subagent_by_type: dict[str, int] = {}
    start_ids: set[str] = set()
    stop_ids: set[str] = set()

    for record in usable:
        event = record.get("hook_event_name")
        tool_name = record.get("tool_name")
        subagent_type = record.get("subagent_type")
        if event in IDENTIFIABLE_TOOL_EVENTS:
            identity = _tool_identity(record)
            if identity is None:
                uncorrelated_tool_events += 1
            elif identity not in tool_ids:
                tool_ids.add(identity)
                label = tool_name if isinstance(tool_name, str) and tool_name else "untyped"
                tool_by_type[label] = tool_by_type.get(label, 0) + 1
        if event in IDENTIFIABLE_SUBAGENT_EVENTS:
            identity = _subagent_identity(record)
            if identity is None:
                uncorrelated_subagent_events += 1
            else:
                type_name = (
                    subagent_type if isinstance(subagent_type, str) and subagent_type else "untyped"
                )
                if identity not in subagent_ids:
                    subagent_ids.add(identity)
                    subagent_by_type[type_name] = subagent_by_type.get(type_name, 0) + 1
                if event == "subagentStart":
                    start_ids.add(identity)
                elif event == "subagentStop":
                    stop_ids.add(identity)

    with_conversation = sum(
        1 for record in usable if isinstance(record.get("conversation_id"), str)
    )
    timestamps = [
        parsed
        for parsed in (_parse_recorded_at(record.get("recorded_at")) for record in usable)
        if parsed is not None
    ]
    elapsed: int | str
    if len(timestamps) >= 1:
        elapsed = int((max(timestamps) - min(timestamps)).total_seconds() * 1000)
    else:
        elapsed = UNAVAILABLE

    duration_sums: dict[str, dict[str, object]] = {}
    for key in DURATION_KEYS:
        validated = [recorded_metric(record, key) for record in usable]
        present = [item for item in validated if _valid_number(item) is not None]
        duration_sums[key] = {
            "available": len(present),
            "sum": sum(present) if present else UNAVAILABLE,
            "invalid": sum(1 for item in validated if item == INVALID),
            "zero": sum(1 for item in present if item == 0),
        }

    precompact_records = [
        record for record in usable if record.get("hook_event_name") == "preCompact"
    ]
    pressures = [
        recorded_metric(record, "context_usage_percent", percent=True)
        for record in precompact_records
    ]
    pressure_values = [item for item in pressures if _valid_number(item) is not None]
    token_fields = {
        key: _coverage([recorded_metric(record, key) for record in usable])
        for key in TOKEN_KEYS
    }
    conversations = sorted(
        {
            record["conversation_id"]
            for record in usable
            if isinstance(record.get("conversation_id"), str)
        }
    )
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "filter": {"conversation_id": conversation_id},
        "conversations": conversations,
        "records": {
            "read": len(records),
            "current_schema": len(current),
            "legacy_without_schema_version": len(legacy),
            "unsupported_schema_version": sum(unsupported_versions.values()),
            "unsupported_versions": unsupported_versions,
            "malformed": malformed,
        },
        "events": {
            "received": len(usable),
            "by_type": by_type,
        },
        "invocations": {
            "identifiable_tool": len(tool_ids),
            "identifiable_subagent": len(subagent_ids),
            "repeated_by_type": {
                "tool": tool_by_type,
                "subagent": subagent_by_type,
            },
        },
        "uncorrelated": {
            "tool_events": uncorrelated_tool_events,
            "subagent_events": uncorrelated_subagent_events,
            "limitation": (
                "Events without a conversation-scoped invocation id are not "
                "counted as identifiable invocations."
            ),
        },
        "correlation": {
            "records_with_conversation_id": with_conversation,
            "records_without_conversation_id": len(usable) - with_conversation,
            "unmatched_starts": len(start_ids - stop_ids),
            "unmatched_stops": len(stop_ids - start_ids),
        },
        "durations": {
            **duration_sums,
            "elapsed_recorded_at_ms": elapsed,
            "limitation": (
                "The sum of available duration fields is not elapsed wall time. "
                "duration and duration_ms are not converted between units."
            ),
        },
        "precompact": {
            "count": len(precompact_records),
            "max_context_usage_percent": (
                max(pressure_values) if pressure_values else UNAVAILABLE
            ),
            "invalid_context_usage_percent": sum(
                1 for item in pressures if item == INVALID
            ),
            "limitation": "Pressure is taken only from preCompact events.",
        },
        "tokens": {
            "fields": token_fields,
            "summed": False,
            "limitation": (
                "Token fields are not summed. Scope and cumulative versus "
                "per-call semantics are unknown. A parent-turn total is not a "
                "per-skill total, and it does not prove subagents were included."
            ),
        },
        "limitations": [
            "This summary does not infer skill identity or run_id.",
            "A conversation may contain several skill runs.",
            "Repeated invocations are counts by type, not redundant reviews.",
            "Uncorrelated events are reported separately from invocations.",
            "Invocation ids are scoped by conversation_id.",
            "Legacy records without schema_version are labeled and included.",
            "Unsupported schema versions are counted and excluded from aggregations.",
        ],
    }


def run_summary(argv: list[str]) -> int:
    override = option_value(argv, "--log")
    destination = option_value(argv, "--output")
    conversation_id = option_value(argv, "--conversation")
    path = Path(override) if override else log_path()
    if destination:
        dest = Path(destination)
        if paths_identify_same_log(path, dest):
            print("observation: --output identifies the input log", file=sys.stderr)
            return 1
    try:
        records, malformed = load_jsonl(path)
        payload = summarize_records(
            records, malformed=malformed, conversation_id=conversation_id
        )
        payload["log_status"] = "ok"
    except OSError as exc:
        print(diagnostic_message(exc), file=sys.stderr)
        payload = summarize_records(
            [], malformed=0, conversation_id=conversation_id
        )
        payload["log_status"] = "unreadable"
    rendered = json.dumps(payload, indent=2)
    print(rendered)
    if destination:
        try:
            out = Path(destination)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered + "\n", encoding="utf-8")
        except OSError as exc:
            print(diagnostic_message(exc), file=sys.stderr)
            return 1
    return 0


def run_hook(argv: list[str]) -> int:
    response = hook_response(permission_allow_requested(argv))
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        override = option_value(argv, "--log")
        path = Path(override) if override else log_path()
        append_record(summarize(payload), path)
    except Exception as exc:
        print(diagnostic_message(exc), file=sys.stderr)
    print(response)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--print-log-path" in args:
        print(log_path())
        return 0
    if "--summary" in args:
        return run_summary(args)
    return run_hook(args)


if __name__ == "__main__":
    raise SystemExit(main())
