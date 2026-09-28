"""Unit checks for Conventional Commit bump and changelog grouping."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def commit(repo: Path, subject: str) -> None:
    marker = repo / f"{len(list(repo.glob('*.txt')))}.txt"
    marker.write_text(subject + "\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", subject)


def check_commits(repo: Path, commit_range: str = "HEAD") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(ROOT / "scripts" / "release" / "check_conventional_commits.sh"), commit_range],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "RELEASE_ROOT": str(repo)},
    )


def test_conventional_commit_validator() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        repo = Path(temporary)
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Test User")
        git(repo, "config", "user.email", "test@example.invalid")

        commit(repo, "invalid subject")
        invalid = check_commits(repo)
        assert invalid.returncode == 1
        assert "invalid subject" in invalid.stdout

        commit(repo, "fix: accepted final record")
        valid = check_commits(repo, "HEAD^..HEAD")
        assert valid.returncode == 0

        commit(repo, "still invalid")
        multiple = check_commits(repo, "HEAD~2..HEAD")
        assert multiple.returncode == 1
        assert "still invalid" in multiple.stdout

        invalid_range = check_commits(repo, "missing..HEAD")
        assert invalid_range.returncode == 2
        assert "cannot read commit range" in invalid_range.stderr

        commit(repo, "Merge pull request #123 from example/branch")
        merge = check_commits(repo, "HEAD^..HEAD")
        assert merge.returncode == 0


if __name__ == "__main__":
    tests = [
        test_bump_rules,
        test_changelog_grouping_and_links,
        test_prepend_changelog_and_apply_version,
        test_conventional_commit_validator,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
