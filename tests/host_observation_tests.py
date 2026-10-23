"""Sanitizer and fail-open checks for the optional Cursor observation adapter."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "optional" / "cursor-observation"))

from observe import (  # noqa: E402
    PERMISSION_ALLOW_FLAG,
    default_log_path,
    hook_response,
    main,
    summarize,
)

SENSITIVE_FIELDS = (
    "task",
    "prompt",
    "summary",
    "tool_input",
    "tool_output",
    "agent_message",
    "transcript_path",
    "modified_files",
    "credentials",
    "tokens",
    "secrets",
)
CORRELATION_FIELDS = (
    "parent_conversation_id",
    "tool_call_id",
    "parent_tool_call_id",
    "child_conversation_id",
    "subagent_model",
    "conversation_id",
    "generation_id",
    "subagent_type",
    "subagent_id",
    "tool_name",
)


def _run_main(stdin_text: str, argv: list[str], log_path: Path | None = None) -> tuple[int, str]:
    stdout = io.StringIO()
    stdin = io.StringIO(stdin_text)
    context = patch.object(sys, "stdin", stdin)
    out = patch.object(sys, "stdout", stdout)
    if log_path is None:
        log_patch = patch("observe.log_path", side_effect=OSError("disk full"))
    else:
        log_patch = patch("observe.log_path", return_value=log_path)
    with context, out, log_patch:
        code = main(argv)
    return code, stdout.getvalue()


def test_summarize_keeps_safe_fields_and_marks_missing_tokens_unavailable() -> None:
    record = summarize(
        {
            "hook_event_name": "postToolUse",
            "tool_name": "Shell",
            "duration": 12,
            "tool_input": {"command": "cat .env"},
            "tool_output": "SECRET=1",
            "task": "review this prompt",
        }
    )
    assert record["hook_event_name"] == "postToolUse"
    assert record["tool_name"] == "Shell"
    assert record["duration"] == 12
    assert "tool_input" not in record
    assert "tool_output" not in record
    assert "task" not in record
    assert record["input_tokens"] == "unavailable"
    assert record["output_tokens"] == "unavailable"


def test_summarize_keeps_present_token_counts() -> None:
    record = summarize({"input_tokens": 10, "output_tokens": 2})
    assert record["input_tokens"] == 10
    assert record["output_tokens"] == 2
    assert record["cache_read_tokens"] == "unavailable"


def test_summarize_null_tokens_are_unavailable() -> None:
    record = summarize(
        {
            "input_tokens": None,
            "output_tokens": None,
            "cache_read_tokens": None,
            "cache_write_tokens": None,
        }
    )
    assert record["input_tokens"] == "unavailable"
    assert record["output_tokens"] == "unavailable"
    assert record["cache_read_tokens"] == "unavailable"
    assert record["cache_write_tokens"] == "unavailable"


def test_summarize_preserves_correlation_fields_and_strips_sensitive_ones() -> None:
    payload = {
        "hook_event_name": "subagentStart",
        "conversation_id": "conv-1",
        "generation_id": "gen-1",
        "parent_conversation_id": "parent-1",
        "child_conversation_id": "child-1",
        "tool_call_id": "tc-1",
        "parent_tool_call_id": "ptc-1",
        "subagent_type": "product-reviewer",
        "subagent_id": "sa-1",
        "subagent_model": "composer",
        "tool_name": "Task",
        "message_count": 3,
        "tool_call_count": 2,
        "loop_count": 0,
        "unknown_field": "drop-me",
        "task": "read the secrets",
        "prompt": "system prompt",
        "summary": "do not store",
        "tool_input": {"command": "cat .env"},
        "tool_output": "SECRET=1",
        "agent_message": "internal",
        "transcript_path": "/tmp/transcript.json",
        "modified_files": ["src/app.ts"],
        "credentials": "token",
        "tokens": "secret-token",
        "secrets": "password",
    }
    record = summarize(payload)
    for field in CORRELATION_FIELDS:
        assert record[field] == payload[field], field
    assert record["message_count"] == 3
    assert record["tool_call_count"] == 2
    assert record["loop_count"] == 0
    assert "unknown_field" not in record
    for field in SENSITIVE_FIELDS:
        assert field not in record, field


def test_summarize_null_counters_are_unavailable_not_zero() -> None:
    record = summarize(
        {
            "message_count": None,
            "tool_call_count": None,
            "loop_count": None,
        }
    )
    assert record["message_count"] == "unavailable"
    assert record["tool_call_count"] == "unavailable"
    assert record["loop_count"] == "unavailable"


def test_subagent_start_returns_allow_for_valid_payload() -> None:
    with tempfile.TemporaryDirectory() as raw:
        log = Path(raw) / "observation.jsonl"
        code, stdout = _run_main(
            json.dumps({"hook_event_name": "subagentStart", "subagent_type": "validator"}),
            [PERMISSION_ALLOW_FLAG],
            log,
        )
        assert code == 0
        assert json.loads(stdout) == {"permission": "allow"}
        assert log.is_file()


def test_subagent_start_fails_open_on_malformed_payload() -> None:
    code, stdout = _run_main("{not-json", [PERMISSION_ALLOW_FLAG], log_path=None)
    assert code == 0
    assert json.loads(stdout) == {"permission": "allow"}


def test_subagent_start_fails_open_on_missing_payload() -> None:
    code, stdout = _run_main("", [PERMISSION_ALLOW_FLAG], log_path=None)
    assert code == 0
    assert json.loads(stdout) == {"permission": "allow"}


def test_subagent_start_fails_open_when_logging_fails() -> None:
    code, stdout = _run_main(
        json.dumps({"hook_event_name": "subagentStart"}),
        [PERMISSION_ALLOW_FLAG],
        log_path=None,
    )
    assert code == 0
    assert json.loads(stdout) == {"permission": "allow"}


def test_observational_hooks_return_empty_object() -> None:
    with tempfile.TemporaryDirectory() as raw:
        log = Path(raw) / "observation.jsonl"
        code, stdout = _run_main("{}", [], log)
        assert code == 0
        assert stdout.strip() == "{}"
        assert json.loads(stdout) == {}


def test_permission_allow_comes_from_argv_not_payload() -> None:
    assert hook_response(True) == '{"permission":"allow"}'
    assert hook_response(False) == "{}"
    fragment = json.loads(
        (ROOT / "optional" / "cursor-observation" / "hooks.fragment.json").read_text(
            encoding="utf-8"
        )
    )
    assert PERMISSION_ALLOW_FLAG in fragment["hooks"]["subagentStart"][0]["command"]
    assert PERMISSION_ALLOW_FLAG not in fragment["hooks"]["postToolUse"][0]["command"]


def test_default_log_path_is_outside_the_source_repository() -> None:
    repo = Path("/tmp/consumer-app")
    path = default_log_path(repo)
    assert repo not in path.parents
    assert path.parent.name == "aidlc-observation"
    previous = os.environ.get("AIDLC_OBSERVE_LOG")
    os.environ["AIDLC_OBSERVE_LOG"] = "/var/log/custom.jsonl"
    try:
        from observe import log_path

        assert log_path() == Path("/var/log/custom.jsonl")
    finally:
        if previous is None:
            os.environ.pop("AIDLC_OBSERVE_LOG", None)
        else:
            os.environ["AIDLC_OBSERVE_LOG"] = previous


if __name__ == "__main__":
    tests = [
        test_summarize_keeps_safe_fields_and_marks_missing_tokens_unavailable,
        test_summarize_keeps_present_token_counts,
        test_summarize_null_tokens_are_unavailable,
        test_summarize_preserves_correlation_fields_and_strips_sensitive_ones,
        test_summarize_null_counters_are_unavailable_not_zero,
        test_subagent_start_returns_allow_for_valid_payload,
        test_subagent_start_fails_open_on_malformed_payload,
        test_subagent_start_fails_open_on_missing_payload,
        test_subagent_start_fails_open_when_logging_fails,
        test_observational_hooks_return_empty_object,
        test_permission_allow_comes_from_argv_not_payload,
        test_default_log_path_is_outside_the_source_repository,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
