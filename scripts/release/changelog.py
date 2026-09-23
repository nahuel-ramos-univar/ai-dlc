#!/usr/bin/env python3
"""Build a grouped CHANGELOG.md entry from Conventional Commits."""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

from semver_from_commits import HEADER_RE, REPO, is_skipped_release_message

CHANGELOG = REPO / "CHANGELOG.md"
SECTIONS = (
    ("breaking", "Breaking changes"),
    ("feat", "Added"),
    ("fix", "Fixed"),
    ("perf", "Performance"),
    ("other", "Other"),
)
REMOTE_RE = re.compile(
    r"(?:git@github\.com:|https://github\.com/)(?P<repo>[^/]+/[^/]+?)(?:\.git)?$"
)


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=REPO, text=True).strip()


def github_repo() -> str | None:
    try:
        remote = run(["git", "config", "--get", "remote.origin.url"])
    except subprocess.CalledProcessError:
        return None
    match = REMOTE_RE.search(remote.strip())
    return match.group("repo") if match else None


def commit_link(short: str, full: str, repo: str | None) -> str:
    if not repo:
        return f"`{short}`"
    return f"[`{short}`](https://github.com/{repo}/commit/{full})"


def classify(subject: str, body: str) -> tuple[str, str]:
    match = HEADER_RE.match(subject)
    breaking = "BREAKING CHANGE:" in body.upper() or bool(
        match and match.group("breaking")
    )
    if breaking:
        return "breaking", subject
    if not match:
        return "other", subject
    commit_type = match.group("type").lower()
    if commit_type in ("feat", "fix", "perf"):
        return commit_type, subject
    return "other", subject


def collect_commits(previous_tag: str | None) -> list[tuple[str, str, str, str]]:
    rng = f"{previous_tag}..HEAD" if previous_tag else None
    if rng is None:
        return []
    out = run(["git", "log", rng, "--pretty=format:%h%x00%H%x00%s%x00%b%x1e"])
    rows: list[tuple[str, str, str, str]] = []
    if not out:
        return rows
    for raw in out.split("\x1e"):
        raw = raw.strip()
        if not raw:
            continue
        short, full, subject, body = (raw.split("\x00") + ["", "", ""])[:4]
        message = f"{subject}\n{body}"
        if is_skipped_release_message(message):
            continue
        rows.append((short, full, subject.strip(), body))
    return rows


def render_entry(
    version: str,
    bump: str,
    commits: list[tuple[str, str, str, str]],
    repo: str | None,
    previous_tag: str | None,
    today: str,
) -> str:
    grouped: dict[str, list[str]] = {key: [] for key, _ in SECTIONS}
    for short, full, subject, body in commits:
        section, _ = classify(subject, body)
        link = commit_link(short, full, repo)
        grouped[section].append(f"- {subject} ({link})")

    lines = [f"## {version} — {today}", "", f"Bump: `{bump}`"]
    if repo and previous_tag:
        lines.append(
            f"Compare: [{previous_tag}...v{version}]"
            f"(https://github.com/{repo}/compare/{previous_tag}...v{version})"
        )
    lines.append("")
    for key, title in SECTIONS:
        items = grouped[key]
        if not items:
            continue
        lines.append(f"### {title}")
        lines.append("")
        lines.extend(items)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def prepend_changelog(entry: str, path: Path = CHANGELOG) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Changelog\n"
    if not existing.startswith("# Changelog"):
        existing = "# Changelog\n\n" + existing
    rest = existing.split("\n", 1)[1].lstrip("\n")
    path.write_text("# Changelog\n\n" + entry.strip() + "\n\n" + rest, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("bump")
    parser.add_argument("--previous-tag", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    previous = args.previous_tag or None
    entry = render_entry(
        args.version.lstrip("v"),
        args.bump,
        collect_commits(previous),
        github_repo(),
        previous,
        dt.datetime.now(dt.timezone.utc).date().isoformat(),
    )
    if args.write:
        prepend_changelog(entry)
        print(f"• {CHANGELOG.relative_to(REPO)} updated")
        return 0
    print(entry, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
