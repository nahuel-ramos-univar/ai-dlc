"""Behavioral tests for deterministic repository-context helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from context_tools import (  # noqa: E402
    classify_repository_scope,
    content_fingerprint,
    normalize_remote,
    stable_repository_id,
)


def run(path: Path, *args: str) -> None:
    subprocess.run(args, cwd=path, check=True, stdout=subprocess.DEVNULL)


def init_repo(path: Path) -> None:
    run(path, "git", "init", "-q")
    run(path, "git", "config", "user.name", "Test User")
    run(path, "git", "config", "user.email", "test@example.invalid")


def test_scope_classification_and_relocation() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        module = root / "packages" / "types"
        module.mkdir(parents=True)
        (module / "index.ts").write_text("export type Id = string;\n")
        init_repo(root)
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")

        assert classify_repository_scope(root).kind == "git-root"
        nested = classify_repository_scope(module)
        assert nested.kind == "nested-tracked"
        assert nested.git_root == root.resolve()

        fingerprint, paths = content_fingerprint(module)
        relocated = Path(temp) / "relocated"
        shutil.copytree(root, relocated)
        moved_fingerprint, moved_paths = content_fingerprint(relocated / "packages" / "types")
        assert fingerprint == moved_fingerprint
        assert paths == moved_paths == ("index.ts",)


def test_untracked_and_nested_repository_ownership() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "outer"
        root.mkdir()
        init_repo(root)
        (root / "tracked.txt").write_text("tracked\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: outer")
        untracked = root / "scratch"
        untracked.mkdir()
        untracked_scope = classify_repository_scope(untracked)
        assert untracked_scope.kind == "untracked-tree"
        assert untracked_scope.git_root is None
        assert untracked_scope.enclosing_git_root == root.resolve()

        nested = root / "nested"
        nested.mkdir()
        init_repo(nested)
        (nested / "main.ts").write_text("export {};\n")
        run(nested, "git", "add", ".")
        run(nested, "git", "commit", "-qm", "feat: nested")
        scope = classify_repository_scope(nested)
        assert scope.kind == "git-root"
        assert scope.git_root == nested.resolve()


def test_fingerprint_detects_changes_and_excludes_generated_output() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "src").mkdir()
        (root / "src" / "a.ts").write_text("export const a = 1;\n")
        initial, paths = content_fingerprint(root)
        assert paths == ("src/a.ts",)

        (root / "aidlc-docs").mkdir()
        (root / "aidlc-docs" / "repository-context.md").write_text("generated\n")
        (root / ".env").write_text("secret\n")
        unchanged, _ = content_fingerprint(root)
        assert initial == unchanged

        (root / "src" / "b.ts").write_text("export const b = 2;\n")
        added, paths = content_fingerprint(root)
        assert added != initial and paths == ("src/a.ts", "src/b.ts")
        (root / "src" / "a.ts").unlink()
        removed, paths = content_fingerprint(root)
        assert removed != added and paths == ("src/b.ts",)
        os.rename(root / "src" / "b.ts", root / "src" / "c.ts")
        renamed, paths = content_fingerprint(root)
        assert renamed != removed and paths == ("src/c.ts",)

        with tempfile.TemporaryDirectory() as outside_dir:
            outside = Path(outside_dir)
            (outside / "leaked.ts").write_text("export const leak = 1;\n")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "pkg.js").write_text("module.exports = 1;\n")
            (root / "vendor-link").symlink_to(outside)
            (root / "src" / "alias.ts").symlink_to(outside / "leaked.ts")
            pruned, pruned_paths = content_fingerprint(root)
            assert pruned == renamed
            assert pruned_paths == ("src/c.ts",)


def test_identity_normalization_and_persistence() -> None:
    assert normalize_remote("git@github.com:owner/repo.git") == "github.com/owner/repo"
    assert normalize_remote("https://github.com/owner/repo.git") == "github.com/owner/repo"
    assert normalize_remote("https://example.test/owner/repo.git") is None
    assert stable_repository_id("team-payment-api", "github.com/a/b", None) == "team-payment-api"
    assert stable_repository_id(None, "github.com/owner/repo", None) == "github-com-owner-repo"


if __name__ == "__main__":
    tests = [
        test_scope_classification_and_relocation,
        test_untracked_and_nested_repository_ownership,
        test_fingerprint_detects_changes_and_excludes_generated_output,
        test_identity_normalization_and_persistence,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
