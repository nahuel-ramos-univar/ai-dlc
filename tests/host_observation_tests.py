"""Sanitizer, summary, and fail-open checks for the optional Cursor observer."""

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
    CURRENT_SCHEMA_VERSION,
    PERMISSION_ALLOW_FLAG,
    default_log_path,
    diagnostic_message,
    hook_response,
    main,
    summarize,
    summarize_records,
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
    "user_message",
)
CORRELATION_FIELDS = (
    "parent_conversation_id",
    "tool_call_id",
    "tool_use_id",
    "parent_tool_call_id",
    "child_conversation_id",
    "subagent_model",
    "conversation_id",
    "generation_id",
    "subagent_type",
    "subagent_id",
    "tool_name",
)


def _run_main(stdin_text: str, argv: list[str], log_path: Path | None = None) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    stdin = io.StringIO(stdin_text)
    context = patch.object(sys, "stdin", stdin)
    out = patch.object(sys, "stdout", stdout)
    err = patch.object(sys, "stderr", stderr)
    if log_path is None:
        log_patch = patch("observe.log_path", side_effect=OSError("disk full"))
    else:
        log_patch = patch("observe.log_path", return_value=log_path)
    with context, out, err, log_patch:
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


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
    assert record["schema_version"] == CURRENT_SCHEMA_VERSION
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
    assert record["schema_version"] == 1
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
        "tool_use_id": "use-1",
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
    assert "skill" not in record
    assert "run_id" not in record
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


def test_missing_zero_and_invalid_metrics() -> None:
    record = summarize(
        {
            "input_tokens": 0,
            "output_tokens": -1,
            "cache_read_tokens": True,
            "cache_write_tokens": "12",
            "message_count": float("nan"),
            "tool_call_count": float("inf"),
            "loop_count": None,
        }
    )
    assert record["input_tokens"] == 0
    assert record["output_tokens"] == "invalid"
    assert record["cache_read_tokens"] == "invalid"
    assert record["cache_write_tokens"] == "invalid"
    assert record["message_count"] == "invalid"
    assert record["tool_call_count"] == "invalid"
    assert record["loop_count"] == "unavailable"
    assert "input_tokens" in record


def test_precompact_sanitization_and_response() -> None:
    payload = {
        "hook_event_name": "preCompact",
        "trigger": "auto",
        "context_usage_percent": 85,
        "context_tokens": 120000,
        "context_window_size": 128000,
        "message_count": 45,
        "messages_to_compact": 30,
        "is_first_compaction": True,
        "user_message": "do not inject",
        "prompt": "hidden",
    }
    record = summarize(payload)
    assert record["hook_event_name"] == "preCompact"
    assert record["trigger"] == "auto"
    assert record["context_usage_percent"] == 85
    assert record["context_tokens"] == 120000
    assert record["context_window_size"] == 128000
    assert record["message_count"] == 45
    assert record["messages_to_compact"] == 30
    assert record["is_first_compaction"] is True
    assert "user_message" not in record
    assert "prompt" not in record
    over = summarize(
        {
            "hook_event_name": "preCompact",
            "context_usage_percent": 101,
            "is_first_compaction": "yes",
        }
    )
    assert over["context_usage_percent"] == "invalid"
    assert "is_first_compaction" not in over
    with tempfile.TemporaryDirectory() as raw:
        log = Path(raw) / "observation.jsonl"
        code, stdout, stderr = _run_main(json.dumps(payload), [], log)
        assert code == 0
        assert stdout.strip() == "{}"
        assert "user_message" not in stdout
        assert stderr == ""
        written = json.loads(log.read_text(encoding="utf-8"))
        assert written["hook_event_name"] == "preCompact"
        assert written["schema_version"] == 1


def test_subagent_start_returns_allow_for_valid_payload() -> None:
    with tempfile.TemporaryDirectory() as raw:
        log = Path(raw) / "observation.jsonl"
        code, stdout, _stderr = _run_main(
            json.dumps({"hook_event_name": "subagentStart", "subagent_type": "validator"}),
            [PERMISSION_ALLOW_FLAG],
            log,
        )
        assert code == 0
        assert json.loads(stdout) == {"permission": "allow"}
        assert log.is_file()


def test_subagent_start_fails_open_on_malformed_payload() -> None:
    code, stdout, stderr = _run_main("{not-json", [PERMISSION_ALLOW_FLAG], log_path=None)
    assert code == 0
    assert json.loads(stdout) == {"permission": "allow"}
    assert "observation: logging failed (JSONDecodeError)" in stderr
    assert "not-json" not in stderr


def test_subagent_start_fails_open_on_missing_payload() -> None:
    code, stdout, _stderr = _run_main("", [PERMISSION_ALLOW_FLAG], log_path=None)
    assert code == 0
    assert json.loads(stdout) == {"permission": "allow"}


def test_subagent_start_fails_open_when_logging_fails() -> None:
    code, stdout, stderr = _run_main(
        json.dumps({"hook_event_name": "subagentStart", "prompt": "secret", "path": "/tmp/hidden"}),
        [PERMISSION_ALLOW_FLAG],
        log_path=None,
    )
    assert code == 0
    assert json.loads(stdout) == {"permission": "allow"}
    assert stderr.strip() == "observation: logging failed (OSError)"
    assert "secret" not in stderr
    assert "/tmp/hidden" not in stderr
    assert "disk full" not in stderr


def test_observational_hooks_return_empty_object() -> None:
    with tempfile.TemporaryDirectory() as raw:
        log = Path(raw) / "observation.jsonl"
        code, stdout, _stderr = _run_main("{}", [], log)
        assert code == 0
        assert stdout.strip() == "{}"
        assert json.loads(stdout) == {}


def test_diagnostic_message_has_no_path_or_payload() -> None:
    message = diagnostic_message(OSError("/secret/consumer/.env: disk full"))
    assert message == "observation: logging failed (OSError)"
    assert "/secret" not in message
    assert ".env" not in message


def test_permission_allow_comes_from_argv_not_payload() -> None:
    assert hook_response(True) == '{"permission":"allow"}'
    assert hook_response(False) == "{}"
    fragment = json.loads(
        (ROOT / "optional" / "cursor-observation" / "hooks.fragment.json").read_text(
            encoding="utf-8"
        )
    )
    commands = [entry["command"] for hooks in fragment["hooks"].values() for entry in hooks]
    assert PERMISSION_ALLOW_FLAG in fragment["hooks"]["subagentStart"][0]["command"]
    assert PERMISSION_ALLOW_FLAG not in fragment["hooks"]["postToolUse"][0]["command"]
    assert PERMISSION_ALLOW_FLAG not in fragment["hooks"]["preCompact"][0]["command"]
    assert "preCompact" in fragment["hooks"]
    for command in commands:
        assert command.startswith("python3 .cursor/hooks/observe.py")


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


def test_legacy_and_unsupported_schema_handling() -> None:
    summary = summarize_records(
        [
            {"schema_version": 1, "hook_event_name": "stop", "conversation_id": "c1"},
            {"hook_event_name": "stop", "conversation_id": "c1"},
            {"schema_version": 2, "hook_event_name": "stop", "conversation_id": "c1"},
        ]
    )
    assert summary["records"]["current_schema"] == 1
    assert summary["records"]["legacy_without_schema_version"] == 1
    assert summary["records"]["unsupported_schema_version"] == 1
    assert summary["records"]["unsupported_versions"] == {"2": 1}
    assert summary["events"]["received"] == 2
    assert summary["events"]["by_type"]["stop"] == 2


def test_correlation_duplicates_and_partial_observations() -> None:
    summary = summarize_records(
        [
            {
                "schema_version": 1,
                "hook_event_name": "postToolUse",
                "tool_name": "Shell",
                "tool_call_id": "dup",
                "conversation_id": "c1",
            },
            {
                "schema_version": 1,
                "hook_event_name": "postToolUse",
                "tool_name": "Shell",
                "tool_call_id": "dup",
                "conversation_id": "c1",
            },
            {
                "schema_version": 1,
                "hook_event_name": "postToolUse",
                "tool_name": "Read",
                "tool_call_id": "other",
                "conversation_id": "c1",
            },
            {
                "schema_version": 1,
                "hook_event_name": "subagentStart",
                "subagent_type": "product-reviewer",
                "subagent_id": "sa-1",
                "conversation_id": "c1",
            },
            {
                "schema_version": 1,
                "hook_event_name": "subagentStop",
                "subagent_type": "validator",
                "subagent_id": "sa-missing-start",
                "conversation_id": "c1",
            },
        ]
    )
    assert summary["events"]["received"] == 5
    assert summary["invocations"]["identifiable_tool"] == 2
    assert summary["invocations"]["repeated_by_type"]["tool"]["Shell"] == 1
    assert summary["invocations"]["identifiable_subagent"] == 2
    assert summary["correlation"]["unmatched_starts"] == 1
    assert summary["correlation"]["unmatched_stops"] == 1
    assert "redundant" not in summary["invocations"]
    assert "run_id" not in summary
    assert "skill" not in summary["invocations"]


def test_multiple_conversations_and_filter() -> None:
    records = [
        {
            "schema_version": 1,
            "hook_event_name": "stop",
            "conversation_id": "alpha",
            "input_tokens": 4,
        },
        {
            "schema_version": 1,
            "hook_event_name": "preCompact",
            "conversation_id": "beta",
            "context_usage_percent": 90,
        },
        {
            "schema_version": 1,
            "hook_event_name": "preCompact",
            "conversation_id": "alpha",
            "context_usage_percent": 40,
        },
    ]
    all_conversations = summarize_records(records)
    assert all_conversations["conversations"] == ["alpha", "beta"]
    assert all_conversations["events"]["received"] == 3
    assert all_conversations["precompact"]["count"] == 2
    assert all_conversations["precompact"]["max_context_usage_percent"] == 90
    filtered = summarize_records(records, conversation_id="alpha")
    assert filtered["events"]["received"] == 2
    assert filtered["precompact"]["count"] == 1
    assert filtered["precompact"]["max_context_usage_percent"] == 40
    assert filtered["tokens"]["summed"] is False


def test_summary_output_and_malformed_lines() -> None:
    with tempfile.TemporaryDirectory() as raw:
        log = Path(raw) / "observation.jsonl"
        destination = Path(raw) / "out" / "summary.json"
        log.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "schema_version": 1,
                            "hook_event_name": "stop",
                            "conversation_id": "c1",
                            "duration_ms": 10,
                            "recorded_at": "2026-10-23T12:00:00Z",
                        }
                    ),
                    "{not-json",
                    json.dumps(["not", "an", "object"]),
                    json.dumps(
                        {
                            "schema_version": 1,
                            "hook_event_name": "stop",
                            "conversation_id": "c1",
                            "duration_ms": 5,
                            "recorded_at": "2026-10-23T12:00:02Z",
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        code, stdout, stderr = _run_main(
            "",
            ["--summary", "--log", str(log), "--output", str(destination)],
            log,
        )
        assert code == 0
        assert stderr == ""
        payload = json.loads(stdout)
        assert payload["records"]["malformed"] == 2
        assert payload["records"]["current_schema"] == 2
        assert payload["durations"]["duration_ms"]["sum"] == 15
        assert payload["durations"]["elapsed_recorded_at_ms"] == 2000
        assert "not elapsed wall time" in payload["durations"]["limitation"]
        assert destination.is_file()
        assert json.loads(destination.read_text(encoding="utf-8"))["records"]["malformed"] == 2


def test_fail_open_logging_stderr_is_safe() -> None:
    code, stdout, stderr = _run_main(
        json.dumps({"hook_event_name": "preCompact", "prompt": "do not leak"}),
        [],
        log_path=None,
    )
    assert code == 0
    assert json.loads(stdout) == {}
    assert stderr.strip() == "observation: logging failed (OSError)"
    assert "do not leak" not in stderr
    assert "/tmp" not in stderr


def test_output_rejects_same_path_symlink_and_hardlink() -> None:
    with tempfile.TemporaryDirectory() as raw:
        folder = Path(raw)
        log = folder / "observation.jsonl"
        original = '{"schema_version":1,"hook_event_name":"stop"}\n'
        log.write_text(original, encoding="utf-8")
        code, stdout, stderr = _run_main(
            "",
            ["--summary", "--log", str(log), "--output", str(log)],
            log,
        )
        assert code == 1
        assert "identifies the input log" in stderr
        assert log.read_text(encoding="utf-8") == original
        assert stdout.strip() == ""

        alias = folder / "via-symlink.jsonl"
        alias.symlink_to(log)
        code, _stdout, stderr = _run_main(
            "",
            ["--summary", "--log", str(log), "--output", str(alias)],
            log,
        )
        assert code == 1
        assert "identifies the input log" in stderr
        assert log.read_text(encoding="utf-8") == original

        hard = folder / "via-hardlink.jsonl"
        os.link(log, hard)
        code, _stdout, stderr = _run_main(
            "",
            ["--summary", "--log", str(log), "--output", str(hard)],
            log,
        )
        assert code == 1
        assert "identifies the input log" in stderr
        assert log.read_bytes() == original.encode("utf-8")
        assert hard.read_bytes() == original.encode("utf-8")


def test_unidentified_subagent_start_stop_is_not_two_invocations() -> None:
    summary = summarize_records(
        [
            {"schema_version": 1, "hook_event_name": "subagentStart", "subagent_type": "product-reviewer"},
            {"schema_version": 1, "hook_event_name": "subagentStop", "subagent_type": "product-reviewer"},
        ]
    )
    assert summary["events"]["received"] == 2
    assert summary["invocations"]["identifiable_subagent"] == 0
    assert summary["uncorrelated"]["subagent_events"] == 2
    assert summary["correlation"]["unmatched_starts"] == 0
    assert summary["correlation"]["unmatched_stops"] == 0
    assert summary["invocations"]["repeated_by_type"]["subagent"] == {}


def test_unidentified_tool_events_are_not_invocations() -> None:
    summary = summarize_records(
        [
            {
                "schema_version": 1,
                "hook_event_name": "afterMCPExecution",
                "tool_name": "search",
                "conversation_id": "c1",
            },
            {
                "schema_version": 1,
                "hook_event_name": "postToolUse",
                "tool_name": "search",
                "conversation_id": "c1",
            },
        ]
    )
    assert summary["invocations"]["identifiable_tool"] == 0
    assert summary["uncorrelated"]["tool_events"] == 2
    assert summary["invocations"]["repeated_by_type"]["tool"] == {}


def test_same_ids_in_different_conversations_stay_separate() -> None:
    summary = summarize_records(
        [
            {
                "schema_version": 1,
                "hook_event_name": "subagentStart",
                "conversation_id": "alpha",
                "subagent_id": "sa-1",
                "subagent_type": "product-reviewer",
            },
            {
                "schema_version": 1,
                "hook_event_name": "subagentStop",
                "conversation_id": "alpha",
                "subagent_id": "sa-1",
            },
            {
                "schema_version": 1,
                "hook_event_name": "subagentStart",
                "conversation_id": "beta",
                "subagent_id": "sa-1",
                "subagent_type": "product-reviewer",
            },
            {
                "schema_version": 1,
                "hook_event_name": "postToolUse",
                "conversation_id": "alpha",
                "tool_use_id": "use-1",
                "tool_name": "Shell",
            },
            {
                "schema_version": 1,
                "hook_event_name": "postToolUse",
                "conversation_id": "beta",
                "tool_use_id": "use-1",
                "tool_name": "Shell",
            },
        ]
    )
    assert summary["invocations"]["identifiable_subagent"] == 2
    assert summary["invocations"]["identifiable_tool"] == 2
    assert summary["correlation"]["unmatched_starts"] == 1
    assert summary["correlation"]["unmatched_stops"] == 0


def test_duplicate_events_within_one_identifiable_invocation() -> None:
    summary = summarize_records(
        [
            {
                "schema_version": 1,
                "hook_event_name": "postToolUse",
                "conversation_id": "c1",
                "tool_call_id": "dup",
                "tool_name": "Shell",
            },
            {
                "schema_version": 1,
                "hook_event_name": "postToolUseFailure",
                "conversation_id": "c1",
                "tool_call_id": "dup",
                "tool_name": "Shell",
            },
            {
                "schema_version": 1,
                "hook_event_name": "subagentStart",
                "conversation_id": "c1",
                "subagent_id": "sa-1",
                "subagent_type": "validator",
            },
            {
                "schema_version": 1,
                "hook_event_name": "subagentStop",
                "conversation_id": "c1",
                "subagent_id": "sa-1",
            },
        ]
    )
    assert summary["invocations"]["identifiable_tool"] == 1
    assert summary["invocations"]["repeated_by_type"]["tool"]["Shell"] == 1
    assert summary["invocations"]["identifiable_subagent"] == 1
    assert summary["correlation"]["unmatched_starts"] == 0
    assert summary["correlation"]["unmatched_stops"] == 0


def test_invalid_legacy_and_current_metrics_are_excluded() -> None:
    summary = summarize_records(
        [
            {
                "hook_event_name": "stop",
                "conversation_id": "c1",
                "duration_ms": -5,
                "input_tokens": True,
                "output_tokens": float("nan"),
                "cache_read_tokens": float("inf"),
                "cache_write_tokens": -2,
            },
            {
                "schema_version": 1,
                "hook_event_name": "preCompact",
                "conversation_id": "c1",
                "context_usage_percent": 250,
                "duration_ms": 10,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": "unavailable",
                "cache_write_tokens": "invalid",
            },
            {
                "schema_version": 1,
                "hook_event_name": "preCompact",
                "conversation_id": "c1",
                "context_usage_percent": 0,
                "duration_ms": 0,
                "input_tokens": 0,
            },
        ]
    )
    assert summary["durations"]["duration_ms"]["sum"] == 10
    assert summary["durations"]["duration_ms"]["invalid"] == 1
    assert summary["durations"]["duration_ms"]["zero"] == 1
    assert summary["precompact"]["max_context_usage_percent"] == 0
    assert summary["precompact"]["invalid_context_usage_percent"] == 1
    assert summary["tokens"]["fields"]["input_tokens"]["zero"] == 2
    assert summary["tokens"]["fields"]["input_tokens"]["invalid"] == 1
    assert summary["tokens"]["fields"]["output_tokens"]["invalid"] == 1
    assert summary["tokens"]["fields"]["cache_read_tokens"]["invalid"] == 1
    assert summary["tokens"]["fields"]["cache_write_tokens"]["invalid"] == 2


def test_valid_zero_metrics_are_preserved() -> None:
    record = summarize(
        {
            "input_tokens": 0,
            "output_tokens": 0,
            "duration_ms": 0,
            "context_usage_percent": 0,
            "hook_event_name": "preCompact",
        }
    )
    assert record["input_tokens"] == 0
    assert record["output_tokens"] == 0
    assert record["duration_ms"] == 0
    assert record["context_usage_percent"] == 0
    summary = summarize_records([record])
    assert summary["tokens"]["fields"]["input_tokens"]["zero"] == 1
    assert summary["precompact"]["max_context_usage_percent"] == 0
    assert summary["durations"]["duration_ms"]["sum"] == 0
    assert summary["durations"]["duration_ms"]["zero"] == 1


if __name__ == "__main__":
    tests = [
        test_summarize_keeps_safe_fields_and_marks_missing_tokens_unavailable,
        test_summarize_keeps_present_token_counts,
        test_summarize_null_tokens_are_unavailable,
        test_summarize_preserves_correlation_fields_and_strips_sensitive_ones,
        test_summarize_null_counters_are_unavailable_not_zero,
        test_missing_zero_and_invalid_metrics,
        test_precompact_sanitization_and_response,
        test_subagent_start_returns_allow_for_valid_payload,
        test_subagent_start_fails_open_on_malformed_payload,
        test_subagent_start_fails_open_on_missing_payload,
        test_subagent_start_fails_open_when_logging_fails,
        test_observational_hooks_return_empty_object,
        test_diagnostic_message_has_no_path_or_payload,
        test_permission_allow_comes_from_argv_not_payload,
        test_default_log_path_is_outside_the_source_repository,
        test_legacy_and_unsupported_schema_handling,
        test_correlation_duplicates_and_partial_observations,
        test_multiple_conversations_and_filter,
        test_summary_output_and_malformed_lines,
        test_fail_open_logging_stderr_is_safe,
        test_output_rejects_same_path_symlink_and_hardlink,
        test_unidentified_subagent_start_stop_is_not_two_invocations,
        test_unidentified_tool_events_are_not_invocations,
        test_same_ids_in_different_conversations_stay_separate,
        test_duplicate_events_within_one_identifiable_invocation,
        test_invalid_legacy_and_current_metrics_are_excluded,
        test_valid_zero_metrics_are_preserved,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
