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
    check_document_budget,
    classify_repository_scope,
    content_fingerprint,
    detect_repository_id_collision,
    extract_table_column,
    find_duplicate_values,
    find_stale_source_paths,
    normalize_remote,
    parse_recorded_fingerprint,
    resolve_markdown_links,
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
        (root / ".env.local").write_text("secret-local\n")
        unchanged, _ = content_fingerprint(root)
        assert initial == unchanged

        (root / ".env.example").write_text("KEY=\n")
        with_template, template_paths = content_fingerprint(root)
        assert with_template != initial
        assert template_paths == (".env.example", "src/a.ts")
        (root / ".env.example").unlink()
        restored, restored_paths = content_fingerprint(root)
        assert restored == initial
        assert restored_paths == ("src/a.ts",)

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


def test_generated_context_does_not_change_source_fingerprint() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "src").mkdir()
        (root / "src" / "app.ts").write_text("export const app = 1;\n")
        initial, paths = content_fingerprint(root)
        assert paths == ("src/app.ts",)

        (root / "AIDLC_CONTEXT.md").write_text("fingerprint: deadbeef\n")
        (root / ".ai-dlc-config.md").write_text("## Context identities\n")
        (root / ".cursor").mkdir()
        (root / ".cursor" / "BUGBOT.md").write_text("When a change in src/app.ts...\n")
        after_write, after_paths = content_fingerprint(root)
        assert after_write == initial
        assert after_paths == ("src/app.ts",)

        (root / "AIDLC_CONTEXT.md").write_text(f"fingerprint: {after_write}\n")
        after_update, _ = content_fingerprint(root)
        assert after_update == initial


def test_skill_source_changes_invalidate_fingerprint() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        skill = root / ".cursor" / "skills" / "sync-context"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Sync context\n")
        (root / "src").mkdir()
        (root / "src" / "app.ts").write_text("export const app = 1;\n")
        initial, paths = content_fingerprint(root)
        assert ".cursor/skills/sync-context/SKILL.md" in paths

        (skill / "SKILL.md").write_text("# Sync context\n\nChanged instruction.\n")
        updated, _ = content_fingerprint(root)
        assert updated != initial


def test_parent_fingerprint_skips_nested_git_repository() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "outer"
        nested = root / "nested"
        module = root / "packages" / "types"
        nested.mkdir(parents=True)
        module.mkdir(parents=True)
        (root / "root.ts").write_text("export const root = 1;\n")
        (module / "index.ts").write_text("export type Id = string;\n")
        (nested / "private.py").write_text("SECRET = 1\n")
        init_repo(root)
        init_repo(nested)
        run(nested, "git", "add", ".")
        run(nested, "git", "commit", "-qm", "feat: nested")

        fingerprint, paths = content_fingerprint(root)
        assert "nested/private.py" not in paths
        assert "root.ts" in paths
        assert "packages/types/index.ts" in paths

        nested_hash, nested_paths = content_fingerprint(nested)
        assert nested_paths == ("private.py",)
        assert nested_hash != fingerprint


def test_fingerprint_includes_symlink_scope_root() -> None:
    with tempfile.TemporaryDirectory() as temp:
        real = Path(temp) / "real"
        (real / "src").mkdir(parents=True)
        (real / "src" / "a.ts").write_text("export const a = 1;\n")
        link = Path(temp) / "link"
        link.symlink_to(real)
        direct, paths = content_fingerprint(real)
        via_link, link_paths = content_fingerprint(link)
        assert direct == via_link
        assert paths == link_paths == ("src/a.ts",)


def test_fingerprint_rejects_unavailable_scope() -> None:
    with tempfile.TemporaryDirectory() as temp:
        empty = Path(temp) / "empty"
        empty.mkdir()
        missing = Path(temp) / "missing"
        as_file = Path(temp) / "not-a-dir.txt"
        as_file.write_text("export const x = 1;\n")
        empty_hash, empty_paths = content_fingerprint(empty)
        assert empty_paths == ()
        assert empty_hash
        try:
            content_fingerprint(missing)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("missing scope must not fingerprint")
        try:
            content_fingerprint(as_file)
        except NotADirectoryError:
            pass
        else:
            raise AssertionError("file scope must not fingerprint")

        blocked = Path(temp) / "blocked"
        inner = blocked / "inner"
        inner.mkdir(parents=True)
        (inner / "a.ts").write_text("export const a = 1;\n")
        os.chmod(inner, 0)
        try:
            try:
                content_fingerprint(blocked)
            except OSError:
                pass
            else:
                raise AssertionError("unreadable scope must not fingerprint")
        finally:
            os.chmod(inner, 0o755)


def test_identity_normalization_and_persistence() -> None:
    assert normalize_remote("git@github.com:owner/repo.git") == "github.com/owner/repo"
    assert normalize_remote("https://github.com/owner/repo.git") == "github.com/owner/repo"
    assert normalize_remote("https://example.test/owner/repo.git") is None
    assert stable_repository_id("team-payment-api", "github.com/a/b", None) == "team-payment-api"
    first = stable_repository_id(None, "github.com/a-b/c", None)
    second = stable_repository_id(None, "github.com/a/b-c", None)
    third = stable_repository_id(None, "github.com/owner/repo", None)
    assert first != second
    assert first.startswith("github-com-a-b-c-")
    assert second.startswith("github-com-a-b-c-")
    assert third.startswith("github-com-owner-repo-")
    assert detect_repository_id_collision(first, "github.com/a-b/c", {first: "github.com/a-b/c"}) is None
    assert (
        detect_repository_id_collision(
            first, "github.com/other/repo", {first: "github.com/a-b/c"}
        )
        == "github.com/a-b/c"
    )


def test_document_budget_flags_documents_over_the_limit() -> None:
    with tempfile.TemporaryDirectory() as temp:
        short = Path(temp) / "short.md"
        short.write_text("\n".join(f"line {i}" for i in range(50)) + "\n")
        assert check_document_budget(short, max_lines=300)

        long = Path(temp) / "long.md"
        long.write_text("\n".join(f"line {i}" for i in range(301)) + "\n")
        assert not check_document_budget(long, max_lines=300)


def test_resolve_markdown_links_classifies_targets() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "aidlc-docs").mkdir()
        index = root / "aidlc-docs" / "repository-context.md"
        (root / "apps" / "web").mkdir(parents=True)
        (root / "apps" / "web" / "AIDLC_CONTEXT.md").write_text("# web\n")
        index.write_text(
            "\n".join(
                [
                    "[web](../apps/web/AIDLC_CONTEXT.md)",
                    "[missing](../apps/admin/AIDLC_CONTEXT.md)",
                    "[outside](../../../../etc/passwd)",
                    "[anchor](#scope)",
                    "[remote](https://example.test)",
                ]
            )
        )
        statuses = resolve_markdown_links(index, root)
        assert statuses["../apps/web/AIDLC_CONTEXT.md"] == "ok"
        assert statuses["../apps/admin/AIDLC_CONTEXT.md"] == "missing"
        assert statuses["../../../../etc/passwd"] == "unresolvable"
        assert statuses["#scope"] == "external"
        assert statuses["https://example.test"] == "external"


def test_extract_table_column_and_duplicate_detection() -> None:
    text = "\n".join(
        [
            "## Modules",
            "",
            "| Module | Source | Context |",
            "| --- | --- | --- |",
            "| `web` | `apps/web` | [x](a.md) |",
            "| `admin` | `apps/admin` | [x](b.md) |",
            "| `web` | `apps/web-copy` | [x](c.md) |",
        ]
    )
    modules = extract_table_column(text, "## Modules", "Module")
    assert modules == ["web", "admin", "web"]
    assert find_duplicate_values(modules) == ["web"]
    assert extract_table_column(text, "## Missing", "Module") == []
    assert extract_table_column(text, "## Modules", "Nope") == []


def test_find_stale_source_paths_flags_deleted_and_escaping_paths() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "apps" / "web").mkdir(parents=True)
        stale = find_stale_source_paths(
            ["apps/web", "apps/removed", "../outside"], root
        )
        assert stale == ["apps/removed", "../outside"]


def test_parse_recorded_fingerprint_round_trips_with_content_fingerprint() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "src").mkdir()
        (root / "src" / "a.ts").write_text("export const a = 1;\n")
        fingerprint, _ = content_fingerprint(root)
        baseline = "4aaa827d45771edd23464e767f24f27eef2033b7"  # 40-hex Git revision
        doc = f"- Baseline and fingerprint: `{baseline}` / `{fingerprint}`\n"
        assert parse_recorded_fingerprint(doc) == fingerprint

        unchanged, _ = content_fingerprint(root)
        assert parse_recorded_fingerprint(doc) == unchanged

        (root / "src" / "a.ts").write_text("export const a = 2;\n")
        changed, _ = content_fingerprint(root)
        assert parse_recorded_fingerprint(doc) != changed


if __name__ == "__main__":
    tests = [
        test_scope_classification_and_relocation,
        test_untracked_and_nested_repository_ownership,
        test_fingerprint_detects_changes_and_excludes_generated_output,
        test_generated_context_does_not_change_source_fingerprint,
        test_skill_source_changes_invalidate_fingerprint,
        test_parent_fingerprint_skips_nested_git_repository,
        test_fingerprint_includes_symlink_scope_root,
        test_fingerprint_rejects_unavailable_scope,
        test_identity_normalization_and_persistence,
        test_document_budget_flags_documents_over_the_limit,
        test_resolve_markdown_links_classifies_targets,
        test_extract_table_column_and_duplicate_detection,
        test_find_stale_source_paths_flags_deleted_and_escaping_paths,
        test_parse_recorded_fingerprint_round_trips_with_content_fingerprint,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
