#!/usr/bin/env python3
"""Optional Cursor observation hook. Fail open. Store no prompt or payload bodies."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_KEYS = (
    "hook_event_name",
    "conversation_id",
    "generation_id",
    "parent_conversation_id",
    "child_conversation_id",
    "tool_call_id",
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
    "duration",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "message_count",
    "tool_call_count",
    "loop_count",
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
METRIC_KEYS = TOKEN_KEYS + COUNTER_KEYS
PERMISSION_ALLOW_FLAG = "--permission-allow"


def summarize(payload: object) -> dict[str, object]:
    record: dict[str, object] = {
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    data = payload if isinstance(payload, dict) else {}
    for key in ALLOWED_KEYS:
        if key in METRIC_KEYS or key not in data:
            continue
        value = data[key]
        if isinstance(value, (str, int, float, bool)):
            record[key] = value
    for key in METRIC_KEYS:
        value = data.get(key)
        if type(value) in (int, float):
            record[key] = value
        else:
            record[key] = "unavailable"
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


def append_record(record: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    response = hook_response(permission_allow_requested(args))
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        append_record(summarize(payload), log_path())
    except Exception:
        pass
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
