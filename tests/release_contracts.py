"""Unit checks for Conventional Commit bump and changelog grouping."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "release"))

from apply_version import apply_version  # noqa: E402
from changelog import classify, prepend_changelog, render_entry  # noqa: E402
from semver_from_commits import (  # noqa: E402
    apply_bump,
    bump_from_commits,
    commit_range,
    is_skipped_release_message,
    parse_version,
)


def test_bump_rules() -> None:
    assert bump_from_commits(["docs: readme"]) is None
    assert bump_from_commits(["chore: ignore", "fix: bug"]) == "patch"
    assert bump_from_commits(["fix: a", "feat: b"]) == "minor"
    assert bump_from_commits(["feat!: break api\n"]) == "major"
    assert bump_from_commits(["feat: x\n\nBREAKING CHANGE: gone"]) == "major"
    assert bump_from_commits(["chore(release): 1.2.3 [skip release]"]) is None
    assert commit_range(None) is None
    assert commit_range("v0.1.0") == "v0.1.0..HEAD"
    assert is_skipped_release_message("chore(release): 0.2.0 [skip release]")
    assert is_skipped_release_message("docs: mention [skip release] in the subject")
    assert not is_skipped_release_message(
        "feat: add release\n\nSee chore(release): and [skip release] in the body."
    )
    assert apply_bump(0, 1, 0, "patch") == "0.1.1"
    assert apply_bump(0, 1, 0, "minor") == "0.2.0"
    assert apply_bump(1, 4, 2, "major") == "2.0.0"
    assert parse_version("v0.1.0") == (0, 1, 0)


def test_changelog_grouping_and_links() -> None:
    commits = [
        ("abc1234", "abc1234deadbeef", "feat: add release workflow", ""),
        ("def5678", "def5678deadbeef", "fix: preserve BUGBOT files", ""),
        ("aaa1111", "aaa1111deadbeef", "feat!: rename ids", ""),
        ("bbb2222", "bbb2222deadbeef", "docs: ignore", ""),
    ]
    entry = render_entry(
        "0.2.0",
        "minor",
        commits,
        "nahuel-ramos-univar/ai-dlc",
        "v0.1.0",
        "2026-09-23",
    )
    assert "## 0.2.0 — 2026-09-23" in entry
    assert "### Breaking changes" in entry
    assert "### Added" in entry
    assert "### Fixed" in entry
    assert "https://github.com/nahuel-ramos-univar/ai-dlc/commit/abc1234deadbeef" in entry
    assert "compare/v0.1.0...v0.2.0" in entry
    section, _ = classify("fix: x", "")
    assert section == "fix"


def test_prepend_changelog_and_apply_version() -> None:
    scratch = ROOT / "tests" / ".tmp-plugin.json"
    scratch.write_text(json.dumps({"name": "x", "version": "0.1.0"}, indent=2) + "\n")
    apply_version("0.1.1", scratch)
    assert json.loads(scratch.read_text())["version"] == "0.1.1"
    scratch.unlink()
    dest = ROOT / "tests" / ".tmp-changelog.md"
    dest.write_text("# Changelog\n\nold\n", encoding="utf-8")
    prepend_changelog("## 0.2.0 — 2026-09-23\n\nBump: `minor`\n", dest)
    text = dest.read_text(encoding="utf-8")
    dest.unlink()
    assert text.startswith("# Changelog\n\n## 0.2.0")
    assert "old" in text


if __name__ == "__main__":
    tests = [
        test_bump_rules,
        test_changelog_grouping_and_links,
        test_prepend_changelog_and_apply_version,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
