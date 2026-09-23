#!/usr/bin/env python3
"""Compute next SemVer from Conventional Commits since the last git tag.

Bump rules (highest wins across the range):
  major  — BREAKING CHANGE in body/footer, or type with '!' (feat!:, fix!:, …)
  minor  — feat:
  patch  — fix: | perf:
  none   — docs|chore|test|ci|build|style|refactor|… only (no release)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN_JSON = REPO / ".cursor-plugin" / "plugin.json"
HEADER_RE = re.compile(
    r"^(?P<type>feat|fix|perf|refactor|docs|chore|test|ci|build|style|revert)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<summary>.+)$",
    re.IGNORECASE | re.MULTILINE,
)
BREAKING_FOOTER_RE = re.compile(r"^BREAKING CHANGE:", re.MULTILINE | re.IGNORECASE)
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=REPO, text=True).strip()


def latest_tag() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=REPO,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return None


def parse_version(value: str) -> tuple[int, int, int]:
    text = value.lstrip("v")
    if not VERSION_RE.match(text):
        raise ValueError(f"unsupported version (need X.Y.Z): {value}")
    major, minor, patch = text.split(".")
    return int(major), int(minor), int(patch)


def plugin_version() -> str:
    data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    version = str(data["version"]).lstrip("v")
    parse_version(version)
    return version


def commit_range(tag: str | None) -> str | None:
    """Range to analyze for bumps. None means untagged baseline: do not scan history."""
    return f"{tag}..HEAD" if tag else None


def commits_since(tag: str | None) -> list[str]:
    rng = commit_range(tag)
    if rng is None:
        return []
    out = run(["git", "log", rng, "--pretty=format:%B%x1e"])
    if not out:
        return []
    return [c.strip() for c in out.split("\x1e") if c.strip()]


def is_skipped_release_message(message: str) -> bool:
    first = message.split("\n", 1)[0].strip().lower()
    return first.startswith("chore(release):") or "[skip release]" in first


def bump_from_commits(messages: list[str]) -> str | None:
    level = 0  # 0 none, 1 patch, 2 minor, 3 major
    for msg in messages:
        if is_skipped_release_message(msg):
            continue
        if BREAKING_FOOTER_RE.search(msg):
            level = max(level, 3)
        first = msg.split("\n", 1)[0].strip()
        match = HEADER_RE.match(first)
        if not match:
            continue
        if match.group("breaking"):
            level = max(level, 3)
            continue
        commit_type = match.group("type").lower()
        if commit_type == "feat":
            level = max(level, 2)
        elif commit_type in ("fix", "perf"):
            level = max(level, 1)
    return {0: None, 1: "patch", 2: "minor", 3: "major"}[level]


def apply_bump(major: int, minor: int, patch: int, bump: str) -> str:
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(bump)


def compute_release() -> dict[str, object]:
    tag = latest_tag()
    if tag:
        major, minor, patch = parse_version(tag)
        base = f"{major}.{minor}.{patch}"
    else:
        major, minor, patch = parse_version(plugin_version())
        base = f"{major}.{minor}.{patch}"

    messages = [m for m in commits_since(tag) if not is_skipped_release_message(m)]
    bump = bump_from_commits(messages)
    next_ver = apply_bump(major, minor, patch, bump) if bump else None
    return {
        "latest_tag": tag,
        "base_version": base,
        "bump": bump,
        "next_version": next_ver,
        "commit_count": len(messages),
        "baseline_tag": None if tag else f"v{base}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print", choices=("text", "json"), default="text", dest="fmt")
    args = parser.parse_args()
    payload = compute_release()
    if args.fmt == "json":
        print(json.dumps(payload, indent=2))
        return 0
    print(f"latest_tag={payload['latest_tag'] or '(none)'}")
    print(f"base_version={payload['base_version']}")
    print(f"bump={payload['bump'] or 'none'}")
    print(f"next_version={payload['next_version'] or '(no release)'}")
    print(f"commit_count={payload['commit_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
