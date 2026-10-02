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
    bugbot_reprompt_allowed,
    check_document_budget,
    checkout_deletion_readiness,
    classify_fingerprint_change,
    classify_markdown_target,
    classify_repository_role,
    classify_repository_scope,
    diff_module_sources,
    find_live_section,
    cli_validate,
    content_fingerprint,
    detect_repository_id_collision,
    extract_table_column,
    find_duplicate_context_targets,
    find_duplicate_identities,
    find_duplicate_values,
    find_stale_source_paths,
    GitDiscoveryError,
    is_declared_submodule,
    migration_destination_placement,
    migration_outcome,
    module_context_destination,
    repository_is_named_coordinator,
    normalize_remote,
    parse_project_references,
    proposal_is_current,
    relocate_workspace_folder_path,
    resolve_placement,
    retirement_decision_pending,
    context_sync_outcome,
    scope_verification_status,
    staged_working_tree_divergence,
    unrelated_rules_preserved,
    parse_recorded_fingerprint,
    resolve_markdown_links,
    resolve_source_path,
    stable_repository_id,
    validate_generated_context,
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


# --- Git-aware fingerprint discovery (finding 1) ---------------------------


def test_git_aware_fingerprint_excludes_ignored_untracked_file() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        init_repo(root)
        (root / "tracked.ts").write_text("export const a = 1;\n")
        (root / ".gitignore").write_text("ignored.log\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial, ignore log files")

        (root / "ignored.log").write_text("noisy debug output\n")
        (root / "kept.ts").write_text("export const b = 2;\n")

        fingerprint, paths = content_fingerprint(root)
        assert "ignored.log" not in paths
        assert "kept.ts" in paths
        assert "tracked.ts" in paths
        assert ".gitignore" in paths

        (root / "ignored.log").unlink()
        after_removing_ignored, after_paths = content_fingerprint(root)
        assert after_removing_ignored == fingerprint
        assert after_paths == paths


def test_git_aware_fingerprint_keeps_tracked_file_matching_a_later_ignore_pattern() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        init_repo(root)
        (root / "legacy.log").write_text("tracked before the ignore rule existed\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial, before ignoring logs")

        before, paths_before = content_fingerprint(root)
        assert "legacy.log" in paths_before

        (root / ".gitignore").write_text("*.log\n")
        run(root, "git", "add", ".gitignore")
        run(root, "git", "commit", "-qm", "chore: ignore future log files")

        after, paths_after = content_fingerprint(root)
        # Already-tracked legacy.log stays included even though it now
        # matches an ignore pattern; only an untracked-and-ignored file is
        # excluded.
        assert "legacy.log" in paths_after
        assert after != before  # .gitignore itself is a new tracked file


def test_git_aware_fingerprint_respects_nested_gitignore_for_a_module_scope() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        module = root / "services" / "billing"
        module.mkdir(parents=True)
        init_repo(root)
        (module / "handler.ts").write_text("export const handler = 1;\n")
        (module / ".gitignore").write_text("*.local.ts\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: billing service")

        (module / "secrets.local.ts").write_text("export const leaked = 1;\n")
        fingerprint, paths = content_fingerprint(module)
        assert "secrets.local.ts" not in paths
        assert "handler.ts" in paths
        assert ".gitignore" in paths


def test_git_aware_fingerprint_detects_additions_deletions_and_renames() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        init_repo(root)
        (root / "a.ts").write_text("export const a = 1;\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")

        initial, paths = content_fingerprint(root)
        assert paths == ("a.ts",)

        (root / "b.ts").write_text("export const b = 2;\n")  # untracked addition
        added, paths = content_fingerprint(root)
        assert added != initial and paths == ("a.ts", "b.ts")

        os.remove(root / "a.ts")
        removed, paths = content_fingerprint(root)
        assert removed != added and paths == ("b.ts",)

        os.rename(root / "b.ts", root / "c.ts")
        renamed, paths = content_fingerprint(root)
        assert renamed != removed and paths == ("c.ts",)


def test_git_aware_fingerprint_excludes_generated_context() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        init_repo(root)
        (root / "src").mkdir()
        (root / "src" / "app.ts").write_text("export const app = 1;\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")
        initial, paths = content_fingerprint(root)
        assert paths == ("src/app.ts",)

        # Untracked, generated: must never enter the source fingerprint.
        (root / "AIDLC_CONTEXT.md").write_text("fingerprint: deadbeef\n")
        after, after_paths = content_fingerprint(root)
        assert after == initial
        assert after_paths == ("src/app.ts",)


def test_git_discovery_failure_raises_instead_of_falling_back_to_the_walk() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        init_repo(root)
        (root / "a.ts").write_text("export const a = 1;\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")

        # Corrupt the Git index so `git rev-parse --show-toplevel` still
        # succeeds (it does not need the index) but `git ls-files` fails.
        (root / ".git" / "index").write_bytes(b"not a real git index")

        try:
            content_fingerprint(root)
        except RuntimeError as error:
            assert "ls-files" in str(error)
        else:
            raise AssertionError(
                "a Git query failure for a Git-backed scope must raise, "
                "never silently fall back to the filesystem walk"
            )


# --- Working-tree-only fingerprint semantics (finding 5) --------------------


def test_fingerprint_reflects_working_tree_not_the_staged_git_index() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        init_repo(root)
        target = root / "service.py"
        target.write_text("version = 1\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: v1")

        v1_fingerprint, _ = content_fingerprint(root)
        assert staged_working_tree_divergence(root) == ()

        # Stage v2 in the index, but do not commit it.
        target.write_text("version = 2\n")
        run(root, "git", "add", "service.py")

        staged_v2_fingerprint, _ = content_fingerprint(root)
        assert staged_v2_fingerprint != v1_fingerprint
        assert staged_working_tree_divergence(root) == ()  # working tree matches the index here

        # Restore the working tree to v1 while v2 remains staged in the index.
        target.write_text("version = 1\n")

        restored_fingerprint, _ = content_fingerprint(root)
        assert restored_fingerprint == v1_fingerprint, (
            "content_fingerprint is a working-tree snapshot: staging v2 and "
            "then restoring the working tree to v1 must reproduce the "
            "original v1 fingerprint, not the staged v2 value"
        )

        divergence = staged_working_tree_divergence(root)
        assert divergence == ("service.py",), (
            "staged (v2) and working-tree (v1) content differ here and must "
            "be reported separately from the fingerprint, never folded into it"
        )


def test_corrupt_index_makes_staged_comparison_unavailable() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        init_repo(root)
        (root / "a.ts").write_text("export const a = 1;\n")
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")

        # rev-parse does not need the index. git diff does.
        (root / ".git" / "index").write_bytes(b"not a real git index")
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert toplevel.returncode == 0

        try:
            staged_working_tree_divergence(root)
        except GitDiscoveryError as error:
            message = str(error)
            assert "diff" in message
            assert "unavailable" in message
        else:
            raise AssertionError(
                "a failed git diff must raise GitDiscoveryError, not return "
                "the same empty tuple that means Git found no differences"
            )


def test_git_fingerprint_skips_a_tracked_file_behind_an_external_directory_symlink() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        outside = Path(temp) / "outside"
        (root / "src").mkdir(parents=True)
        outside.mkdir()
        (root / "keep.txt").write_text("kept\n")
        (root / "src" / "data.txt").write_text("original\n")
        init_repo(root)
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")

        shutil.rmtree(root / "src")
        external = outside / "data.txt"
        external.write_text("external secret\n")
        os.chmod(external, 0)
        (root / "src").symlink_to(outside)
        try:
            _fingerprint, paths = content_fingerprint(root)
        finally:
            os.chmod(external, 0o644)
        assert "src/data.txt" not in paths
        assert "keep.txt" in paths
        assert external.read_text(encoding="utf-8") == "external secret\n"


def test_git_fingerprint_skips_a_directory_symlink_that_points_inside_the_repository() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        (root / "nested").mkdir(parents=True)
        (root / "nested" / "data.txt").write_text("tracked\n")
        (root / "plain.txt").write_text("plain\n")
        init_repo(root)
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")

        shutil.rmtree(root / "nested")
        real = root / "real"
        real.mkdir()
        (real / "data.txt").write_text("inside\n")
        (root / "nested").symlink_to(real)
        _fingerprint, paths = content_fingerprint(root)
        assert "nested/data.txt" not in paths
        assert "plain.txt" in paths


def test_git_fingerprint_accepts_a_symlink_scope_root() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        (root / "src").mkdir(parents=True)
        (root / "src" / "a.ts").write_text("export const a = 1;\n")
        init_repo(root)
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")
        link = Path(temp) / "link"
        link.symlink_to(root)
        direct, paths = content_fingerprint(root)
        via_link, link_paths = content_fingerprint(link)
        assert direct == via_link
        assert paths == link_paths == ("src/a.ts",)


def test_broken_git_metadata_is_not_fingerprinted_as_an_unversioned_tree() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        module = root / "services" / "billing"
        private = module / "private"
        private.mkdir(parents=True)
        (root / ".gitignore").write_text("private/\n")
        key = private / "key.json"
        key.write_text('{"token":"fake-test-token"}\n')
        (module / "handler.ts").write_text("export const handler = 1;\n")
        os.chmod(key, 0)
        (root / ".git").write_text(f"gitdir: {Path(temp) / 'missing-gitdir'}\n")
        try:
            try:
                content_fingerprint(root)
            except GitDiscoveryError as error:
                assert "fake-test-token" not in str(error)
            else:
                raise AssertionError("a broken .git pointer must not be scanned as unversioned")
            try:
                content_fingerprint(module)
            except GitDiscoveryError as error:
                assert "fake-test-token" not in str(error)
            else:
                raise AssertionError("a nested module of a broken checkout must not be scanned")
        finally:
            os.chmod(key, 0o644)


def test_valid_git_worktree_fingerprint_includes_tracked_files() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        (root / "a.ts").write_text("export const a = 1;\n")
        init_repo(root)
        run(root, "git", "add", ".")
        run(root, "git", "commit", "-qm", "feat: initial")
        worktree = Path(temp) / "worktree"
        run(root, "git", "worktree", "add", "-q", str(worktree), "HEAD")
        assert (worktree / ".git").is_file()
        _fingerprint, paths = content_fingerprint(worktree)
        assert paths == ("a.ts",)


def test_unversioned_tree_still_uses_the_filesystem_walk() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "plain"
        root.mkdir()
        (root / ".gitignore").write_text("a.ts\n")
        (root / "a.ts").write_text("export const a = 1;\n")
        _fingerprint, paths = content_fingerprint(root)
        assert "a.ts" in paths


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


# --- Multi-repository workspace reference resolution ----------------------


def test_resolve_markdown_links_across_multiple_authorized_repositories() -> None:
    """An artifact home can link to modules that live in sibling repositories."""
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        engagement = base / "engagement"
        web = base / "web"
        payments = base / "payments"
        (engagement / "aidlc-docs").mkdir(parents=True)
        (web / "apps" / "storefront").mkdir(parents=True)
        (payments / "services" / "billing").mkdir(parents=True)
        (web / "apps" / "storefront" / "AIDLC_CONTEXT.md").write_text("# storefront\n")
        (payments / "services" / "billing" / "AIDLC_CONTEXT.md").write_text("# billing\n")

        index = engagement / "aidlc-docs" / "repository-context.md"
        index.write_text(
            "\n".join(
                [
                    "[storefront](../../web/apps/storefront/AIDLC_CONTEXT.md)",
                    "[billing](../../payments/services/billing/AIDLC_CONTEXT.md)",
                    "[missing](../../web/apps/admin/AIDLC_CONTEXT.md)",
                    "[unavailable-repo](../../reporting/module/AIDLC_CONTEXT.md)",
                    "[escape](../../../../../etc/passwd)",
                    "[anchor](#scope)",
                    "[remote](https://example.test)",
                ]
            )
        )
        # "reporting" is a configured repository whose root was never created.
        roots = {"web": web, "payments": payments, "reporting": base / "reporting"}
        statuses = resolve_markdown_links(index, roots)
        assert statuses["../../web/apps/storefront/AIDLC_CONTEXT.md"] == "ok"
        assert statuses["../../payments/services/billing/AIDLC_CONTEXT.md"] == "ok"
        assert statuses["../../web/apps/admin/AIDLC_CONTEXT.md"] == "missing"
        assert statuses["../../reporting/module/AIDLC_CONTEXT.md"] == "unavailable"
        assert statuses["../../../../../etc/passwd"] == "unresolvable"
        assert statuses["#scope"] == "external"
        assert statuses["https://example.test"] == "external"


def test_resolve_markdown_links_rejects_symlink_escape_from_authorized_root() -> None:
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        web = base / "web"
        secret = base / "secret"
        (web / "aidlc-docs").mkdir(parents=True)
        secret.mkdir()
        (secret / "leaked.md").write_text("not authorized\n")
        (web / "escape-link").symlink_to(secret)
        index = web / "aidlc-docs" / "repository-context.md"
        index.write_text("[leak](../escape-link/leaked.md)\n")
        statuses = resolve_markdown_links(index, {"web": web})
        assert statuses["../escape-link/leaked.md"] == "unresolvable"


def test_resolve_source_path_distinguishes_repository_and_path_problems() -> None:
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        web = base / "web"
        (web / "apps" / "api").mkdir(parents=True)
        unavailable_root = base / "reporting"  # configured, never created

        assert resolve_source_path("web", "apps/api", {"web": web}) == "ok"
        assert resolve_source_path("web", "apps/missing", {"web": web}) == "missing"
        assert resolve_source_path("ghost", "apps/api", {"web": web}) == "unresolved"
        assert (
            resolve_source_path("reporting", "module", {"reporting": unavailable_root})
            == "unavailable"
        )
        assert (
            resolve_source_path("web", "../payments/secret", {"web": web})
            == "unresolvable"
        )


def test_find_stale_source_paths_flags_every_non_ok_reason() -> None:
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        web = base / "web"
        (web / "apps" / "web").mkdir(parents=True)
        unavailable_root = base / "reporting"
        entries = [
            ("web", "apps/web"),
            ("web", "apps/removed"),
            ("web", "../outside"),
            ("reporting", "module"),
            ("ghost", "module"),
        ]
        problems = find_stale_source_paths(entries, {"web": web, "reporting": unavailable_root})
        assert problems == {
            ("web", "apps/removed"): "missing",
            ("web", "../outside"): "unresolvable",
            ("reporting", "module"): "unavailable",
            ("ghost", "module"): "unresolved",
        }


# --- Duplicate module identity vs. duplicate output detection --------------


def test_duplicate_module_id_across_two_repositories_is_allowed() -> None:
    """Two different repositories may each declare a module named "api"."""
    duplicates = find_duplicate_identities(["api", "api"], ["web", "payments"])
    assert duplicates == []


def test_duplicate_repository_and_module_id_pair_is_flagged() -> None:
    duplicates = find_duplicate_identities(["api", "web", "api"], ["web", "web", "web"])
    assert duplicates == [("web", "api")]


def test_duplicate_module_id_without_repository_ids_uses_module_id_only() -> None:
    """The single-repository case has one unambiguous repository identity."""
    assert find_duplicate_identities(["api", "web", "api"]) == [("", "api")]


def test_find_duplicate_identities_rejects_misaligned_lists() -> None:
    try:
        find_duplicate_identities(["api"], ["web", "payments"])
    except ValueError:
        pass
    else:
        raise AssertionError("misaligned repository_ids must raise")


def test_find_duplicate_context_targets_detects_shared_output_with_different_labels() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        index = root / "repository-context.md"
        index.write_text("placeholder\n")
        (root / "apps" / "shared").mkdir(parents=True)
        (root / "apps" / "shared" / "AIDLC_CONTEXT.md").write_text("# shared\n")
        cells = [
            "[storefront](apps/shared/AIDLC_CONTEXT.md)",
            "[checkout](./apps/shared/AIDLC_CONTEXT.md)",
            "[other](apps/other/AIDLC_CONTEXT.md)",
        ]
        duplicates = find_duplicate_context_targets(cells, index)
        assert duplicates == [(root / "apps" / "shared" / "AIDLC_CONTEXT.md").resolve()]


def test_find_duplicate_values_generic_helper() -> None:
    assert find_duplicate_values(["web", "admin", "web"]) == ["web"]
    assert find_duplicate_values(["a", "b", "c"]) == []


# --- Section-aware Markdown table parsing -----------------------------------


def test_extract_table_column_reads_populated_table() -> None:
    text = "\n".join(
        [
            "## Modules",
            "",
            "| Module | Source | Context |",
            "| --- | --- | --- |",
            "| `web` | `apps/web` | [x](a.md) |",
            "| `admin` | `apps/admin` | [x](b.md) |",
        ]
    )
    result = extract_table_column(text, "## Modules", "Module")
    assert result.status == "ok"
    assert result.values == ("web", "admin")


def test_extract_table_column_missing_table_does_not_leak_into_next_section() -> None:
    """A missing table under one heading must never read a later section's table."""
    text = "\n".join(
        [
            "## Modules",
            "",
            "No table declared yet.",
            "",
            "## Other section",
            "",
            "| Module | Source |",
            "| --- | --- |",
            "| `web` | `apps/web` |",
        ]
    )
    result = extract_table_column(text, "## Modules", "Module")
    assert result.status == "missing_table"
    assert result.values == ()


def test_extract_table_column_valid_empty_table_is_distinguished_from_malformed() -> None:
    text = "\n".join(
        [
            "## Modules",
            "",
            "| Module | Source |",
            "| --- | --- |",
            "",
            "## Other section",
        ]
    )
    result = extract_table_column(text, "## Modules", "Module")
    assert result.status == "ok"
    assert result.values == ()


def test_extract_table_column_missing_section_reported_distinctly() -> None:
    result = extract_table_column("# Doc\n\nno headings match\n", "## Modules", "Module")
    assert result.status == "missing_section"


def test_extract_table_column_reports_malformed_separator_row() -> None:
    text = "\n".join(
        [
            "## Modules",
            "",
            "| Module | Source |",
            "| not-a-separator | --- |",
            "| `web` | `apps/web` |",
        ]
    )
    assert extract_table_column(text, "## Modules", "Module").status == "malformed_table"


def test_extract_table_column_reports_malformed_row_cell_count() -> None:
    text = "\n".join(
        [
            "## Modules",
            "",
            "| Module | Source |",
            "| --- | --- |",
            "| `web` |",
        ]
    )
    assert extract_table_column(text, "## Modules", "Module").status == "malformed_table"


def test_extract_table_column_reports_missing_column() -> None:
    text = "\n".join(
        [
            "## Modules",
            "",
            "| Module | Source |",
            "| --- | --- |",
            "| `web` | `apps/web` |",
        ]
    )
    assert extract_table_column(text, "## Modules", "Context").status == "missing_column"


def test_extract_table_column_ignores_fenced_example_table() -> None:
    """A documented example table must never be mistaken for live module data."""
    text = "\n".join(
        [
            "## Modules",
            "",
            "Example format:",
            "",
            "```",
            "| Module | Source |",
            "| --- | --- |",
            "| `example` | `apps/example` |",
            "```",
            "",
        ]
    )
    assert extract_table_column(text, "## Modules", "Module").status == "missing_table"


# --- Canonical fingerprint metadata parsing --------------------------------


def test_parse_recorded_fingerprint_module_document_shape() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "src").mkdir()
        (root / "src" / "a.ts").write_text("export const a = 1;\n")
        fingerprint, _ = content_fingerprint(root)
        baseline = "4aaa827d45771edd23464e767f24f27eef2033b7"  # 40-hex Git revision
        doc = "\n".join(
            [
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Identity and scope",
                "",
                f"- Baseline and fingerprint: `{baseline}` / `{fingerprint}`",
                "",
                "<!-- AI-DLC:generated:end -->",
            ]
        )
        field = parse_recorded_fingerprint(doc)
        assert field.status == "ok"
        assert field.value == fingerprint
        assert field.value != baseline  # never confuse a Git revision with the fingerprint


def test_parse_recorded_fingerprint_repository_index_shape() -> None:
    doc = "\n".join(
        [
            "<!-- AI-DLC:generated:start -->",
            "",
            "## Scope",
            "",
            "- Fingerprint: `2222222222222222`",
            "",
            "<!-- AI-DLC:generated:end -->",
        ]
    )
    field = parse_recorded_fingerprint(doc)
    assert field.status == "ok"
    assert field.value == "2222222222222222"


def test_parse_recorded_fingerprint_ignores_notes_and_examples_outside_metadata() -> None:
    doc = "\n".join(
        [
            "A teammate once noted a fingerprint of `0000000000000000` here for context.",
            "",
            "```",
            "- Fingerprint: `1111111111111111`",
            "```",
            "",
            "<!-- AI-DLC:generated:start -->",
            "",
            "## Scope",
            "",
            "- Fingerprint: `2222222222222222`",
            "",
            "<!-- AI-DLC:generated:end -->",
        ]
    )
    field = parse_recorded_fingerprint(doc)
    assert field.status == "ok"
    assert field.value == "2222222222222222"


def test_parse_recorded_fingerprint_reports_missing_metadata() -> None:
    assert parse_recorded_fingerprint("# A document with no identity section\n").status == "missing"

    doc_without_field = "\n".join(
        [
            "<!-- AI-DLC:generated:start -->",
            "",
            "## Scope",
            "",
            "- Owner: `platform-team`",
            "",
            "<!-- AI-DLC:generated:end -->",
        ]
    )
    assert parse_recorded_fingerprint(doc_without_field).status == "missing"


def test_parse_recorded_fingerprint_reports_malformed_field() -> None:
    doc = "\n".join(
        [
            "<!-- AI-DLC:generated:start -->",
            "",
            "## Scope",
            "",
            "- Fingerprint: not-a-hex-value",
            "",
            "<!-- AI-DLC:generated:end -->",
        ]
    )
    assert parse_recorded_fingerprint(doc).status == "malformed"


def test_parse_recorded_fingerprint_reports_ambiguous_duplicate_fields() -> None:
    doc = "\n".join(
        [
            "<!-- AI-DLC:generated:start -->",
            "",
            "## Scope",
            "",
            "- Fingerprint: `1111111111111111`",
            "- Fingerprint: `2222222222222222`",
            "",
            "<!-- AI-DLC:generated:end -->",
        ]
    )
    assert parse_recorded_fingerprint(doc).status == "ambiguous"


# --- Aggregate deterministic validation -------------------------------------


def _write_valid_module(module_dir: Path, repository_id: str, module_id: str, source: str) -> str:
    fingerprint, _ = content_fingerprint(module_dir)
    (module_dir / "AIDLC_CONTEXT.md").write_text(
        "\n".join(
            [
                f"# AIDLC context — {module_id}",
                "",
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Identity and scope",
                "",
                f"- Repository ID: `{repository_id}`",
                f"- Module ID: `{module_id}`",
                f"- Source: `{source}`",
                f"- Baseline and fingerprint: `deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` / `{fingerprint}`",
                "",
                "<!-- AI-DLC:generated:end -->",
                "",
            ]
        )
    )
    return fingerprint


def _write_valid_index(index_path: Path, repo_root: Path) -> None:
    index_fingerprint, _ = content_fingerprint(repo_root)
    index_path.write_text(
        "\n".join(
            [
                "# Repository context",
                "",
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Scope",
                "",
                "- Index: `single-repository`",
                "- Repository ID: `web`",
                f"- Fingerprint: `{index_fingerprint}`",
                "",
                "## Modules",
                "",
                "| Module | Source | Context | Status |",
                "| --- | --- | --- | --- |",
                "| `storefront` | `apps/storefront` | [x](../apps/storefront/AIDLC_CONTEXT.md) | current |",
                "",
                "<!-- AI-DLC:generated:end -->",
                "",
            ]
        )
    )


def test_validate_generated_context_passes_for_a_well_formed_document_set() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        (web / "apps" / "storefront").mkdir(parents=True)
        (web / "apps" / "storefront" / "index.ts").write_text("export const x = 1;\n")
        _write_valid_module(web / "apps" / "storefront", "web", "storefront", "apps/storefront")
        (web / "aidlc-docs").mkdir()
        index = web / "aidlc-docs" / "repository-context.md"
        _write_valid_index(index, web)

        before = index.read_text()
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        assert index.read_text() == before, "validation must never modify a document"

        statuses = {check.name: check.status for check in checks}
        assert statuses["index:budget"] == "passed"
        assert statuses["index:structure"] == "passed"
        assert statuses["index:fingerprint"] == "passed"
        assert statuses["modules:table"] == "passed"
        assert statuses["modules:duplicate-identity"] == "passed"
        assert statuses["modules:duplicate-context-target"] == "passed"
        assert all(check.status in ("passed", "not_applicable") for check in checks)


# --- Candidate-content validation before a canonical write (finding 2) ----


def test_candidate_content_validates_first_time_generation_without_canonical_docs() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        module_dir = web / "apps" / "storefront"
        module_dir.mkdir(parents=True)
        (module_dir / "index.ts").write_text("export const x = 1;\n")

        module_fingerprint, _ = content_fingerprint(module_dir)
        index_fingerprint, _ = content_fingerprint(web)

        index_path = (web / "aidlc-docs" / "repository-context.md").resolve()
        module_path = (module_dir / "AIDLC_CONTEXT.md").resolve()
        assert not index_path.exists()
        assert not module_path.exists()

        index_text = "\n".join(
            [
                "# Repository context",
                "",
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Scope",
                "",
                "- Index: `single-repository`",
                "- Repository ID: `web`",
                f"- Fingerprint: `{index_fingerprint}`",
                "",
                "## Modules",
                "",
                "| Module | Source | Context | Status |",
                "| --- | --- | --- | --- |",
                "| `storefront` | `apps/storefront` | [x](../apps/storefront/AIDLC_CONTEXT.md) | current |",
                "",
                "<!-- AI-DLC:generated:end -->",
                "",
            ]
        )
        module_text = "\n".join(
            [
                "# AIDLC context — storefront",
                "",
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Identity and scope",
                "",
                "- Repository ID: `web`",
                "- Module ID: `storefront`",
                "- Source: `apps/storefront`",
                f"- Baseline and fingerprint: `deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` / `{module_fingerprint}`",
                "",
                "<!-- AI-DLC:generated:end -->",
                "",
            ]
        )

        checks = validate_generated_context(
            index_path,
            {"web": web},
            candidate_content={index_path: index_text, module_path: module_text},
        )
        by_name = {check.name: check.status for check in checks}
        assert by_name["index:structure"] == "passed"
        assert by_name["index:fingerprint"] == "passed"
        assert by_name["modules:link:../apps/storefront/AIDLC_CONTEXT.md"] == "passed"
        assert by_name["modules:structure:../apps/storefront/AIDLC_CONTEXT.md"] == "passed"
        assert by_name["modules:fingerprint:../apps/storefront/AIDLC_CONTEXT.md"] == "passed"
        # Validating a proposal never writes it.
        assert not index_path.exists()
        assert not module_path.exists()


def test_classify_markdown_target_resolves_a_candidate_to_candidate_link() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo_root = Path(temp) / "web"
        repo_root.mkdir()
        index_path = repo_root / "aidlc-docs" / "repository-context.md"
        candidate_module = (repo_root / "apps" / "storefront" / "AIDLC_CONTEXT.md").resolve()

        without_candidate = classify_markdown_target(
            index_path,
            "../apps/storefront/AIDLC_CONTEXT.md",
            {"web": repo_root},
            require_file=True,
        )
        assert without_candidate == "missing"

        with_candidate = classify_markdown_target(
            index_path,
            "../apps/storefront/AIDLC_CONTEXT.md",
            {"web": repo_root},
            require_file=True,
            candidate_paths=frozenset({candidate_module}),
        )
        assert with_candidate == "ok"


def test_candidate_content_fails_a_malformed_proposal_even_when_disk_copy_is_valid() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        module_dir = web / "apps" / "storefront"
        module_dir.mkdir(parents=True)
        (module_dir / "index.ts").write_text("export const x = 1;\n")
        _write_valid_module(module_dir, "web", "storefront", "apps/storefront")
        module_path = module_dir / "AIDLC_CONTEXT.md"
        (web / "aidlc-docs").mkdir()
        index_path = web / "aidlc-docs" / "repository-context.md"
        _write_valid_index(index_path, web)

        baseline = {
            c.name: c.status
            for c in validate_generated_context(index_path, {"web": web})
        }
        assert baseline["modules:structure:../apps/storefront/AIDLC_CONTEXT.md"] == "passed"

        malformed_proposal = "\n".join(
            [
                "# AIDLC context — storefront",
                "",
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Wrong heading",
                "",
                "<!-- AI-DLC:generated:end -->",
                "",
            ]
        )
        checks = {
            c.name: c.status
            for c in validate_generated_context(
                index_path,
                {"web": web},
                candidate_content={module_path.resolve(): malformed_proposal},
            )
        }
        assert checks["modules:structure:../apps/storefront/AIDLC_CONTEXT.md"] == "failed"
        # The valid on-disk document is untouched by checking the proposal.
        assert "## Identity and scope" in module_path.read_text(encoding="utf-8")


def test_candidate_content_checks_the_proposal_instead_of_a_stale_on_disk_copy() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        module_dir = web / "apps" / "storefront"
        module_dir.mkdir(parents=True)
        (module_dir / "index.ts").write_text("export const x = 1;\n")
        module_path = module_dir / "AIDLC_CONTEXT.md"
        stale_text = "stale and malformed, no generated block\n"
        module_path.write_text(stale_text)
        (web / "aidlc-docs").mkdir()
        index_path = web / "aidlc-docs" / "repository-context.md"
        _write_valid_index(index_path, web)

        baseline = {
            c.name: c.status
            for c in validate_generated_context(index_path, {"web": web})
        }
        assert baseline["modules:structure:../apps/storefront/AIDLC_CONTEXT.md"] == "failed"

        module_fingerprint, _ = content_fingerprint(module_dir)
        proposed_text = "\n".join(
            [
                "# AIDLC context — storefront",
                "",
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Identity and scope",
                "",
                "- Repository ID: `web`",
                "- Module ID: `storefront`",
                "- Source: `apps/storefront`",
                f"- Baseline and fingerprint: `deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` / `{module_fingerprint}`",
                "",
                "<!-- AI-DLC:generated:end -->",
                "",
            ]
        )
        checks = {
            c.name: c.status
            for c in validate_generated_context(
                index_path,
                {"web": web},
                candidate_content={module_path.resolve(): proposed_text},
            )
        }
        assert checks["modules:structure:../apps/storefront/AIDLC_CONTEXT.md"] == "passed"
        assert checks["modules:fingerprint:../apps/storefront/AIDLC_CONTEXT.md"] == "passed"
        # The stale on-disk copy is still untouched.
        assert module_path.read_text(encoding="utf-8") == stale_text


def test_candidate_content_mapping_does_not_grant_an_authorized_root_escape() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo_root = Path(temp) / "web"
        repo_root.mkdir()
        index_path = repo_root / "aidlc-docs" / "repository-context.md"
        outside_module = (Path(temp) / "elsewhere" / "AIDLC_CONTEXT.md").resolve()

        status = classify_markdown_target(
            index_path,
            "../../elsewhere/AIDLC_CONTEXT.md",
            {"web": repo_root},
            require_file=True,
            candidate_paths=frozenset({outside_module}),
        )
        assert status == "unresolvable", (
            "a candidate-content mapping entry must never grant a traversal "
            "escape outside every authorized root"
        )


def test_candidate_content_never_writes_to_the_real_index_file() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        (web / "aidlc-docs").mkdir()
        index_path = web / "aidlc-docs" / "repository-context.md"
        _write_valid_index(index_path, web)
        original_text = index_path.read_text(encoding="utf-8")

        validate_generated_context(
            index_path,
            {"web": web},
            candidate_content={index_path.resolve(): "a deliberately different, malformed proposal\n"},
        )
        assert index_path.read_text(encoding="utf-8") == original_text, (
            "validating a candidate must never overwrite the real file on disk"
        )


def test_validate_generated_context_without_candidates_still_works_after_a_candidate_run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        module_dir = web / "apps" / "storefront"
        module_dir.mkdir(parents=True)
        (module_dir / "index.ts").write_text("export const x = 1;\n")
        _write_valid_module(module_dir, "web", "storefront", "apps/storefront")
        (web / "aidlc-docs").mkdir()
        index_path = web / "aidlc-docs" / "repository-context.md"
        _write_valid_index(index_path, web)

        # A candidate-content run checking a proposal before applying it
        # must not affect a later, ordinary on-disk validation run for the
        # same final paths.
        validate_generated_context(
            index_path,
            {"web": web},
            candidate_content={index_path.resolve(): "unrelated candidate text\n"},
        )

        checks = {c.name: c.status for c in validate_generated_context(index_path, {"web": web})}
        assert checks["index:structure"] == "passed"
        assert checks["modules:structure:../apps/storefront/AIDLC_CONTEXT.md"] == "passed"


def _assert_destination_rejected(checks: list) -> None:
    assert checks, "validation must return a result"
    assert any(check.status == "failed" for check in checks)
    assert not all(check.status in {"passed", "not_applicable"} for check in checks)


def test_index_candidate_outside_authorized_roots_fails() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        outside = Path(temp) / "elsewhere" / "repository-context.md"
        checks = validate_generated_context(
            outside, {"web": web}, candidate_content={outside: "# proposed\n"}
        )
        _assert_destination_rejected(checks)
        assert not outside.exists()


def test_index_candidate_whose_destination_is_a_directory_fails() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        destination = web / "aidlc-docs" / "repository-context.md"
        destination.mkdir(parents=True)
        checks = validate_generated_context(
            destination, {"web": web}, candidate_content={destination: "# proposed\n"}
        )
        _assert_destination_rejected(checks)
        assert destination.is_dir()


def test_module_candidate_whose_destination_is_a_directory_fails() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        module_dir = web / "apps" / "storefront"
        module_dir.mkdir(parents=True)
        (module_dir / "index.ts").write_text("export const x = 1;\n")
        module_path = module_dir / "AIDLC_CONTEXT.md"
        module_path.mkdir()
        (web / "aidlc-docs").mkdir()
        index = web / "aidlc-docs" / "repository-context.md"
        _write_valid_index(index, web)
        before = index.read_text(encoding="utf-8")
        checks = validate_generated_context(
            index, {"web": web}, candidate_content={module_path: "# proposed\n"}
        )
        _assert_destination_rejected(checks)
        assert module_path.is_dir()
        assert index.read_text(encoding="utf-8") == before


def test_candidate_fails_when_a_parent_path_is_a_file() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        parent = web / "aidlc-docs"
        parent.write_text("not a directory\n")
        destination = parent / "repository-context.md"
        checks = validate_generated_context(
            destination, {"web": web}, candidate_content={destination: "# proposed\n"}
        )
        _assert_destination_rejected(checks)
        assert parent.read_text(encoding="utf-8") == "not a directory\n"
        assert not destination.exists()


def test_candidate_symlink_escape_fails_without_writing() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        outside = Path(temp) / "outside"
        outside.mkdir()
        (web / "escape").symlink_to(outside)
        destination = web / "escape" / "repository-context.md"
        checks = validate_generated_context(
            destination, {"web": web}, candidate_content={destination: "# proposed\n"}
        )
        _assert_destination_rejected(checks)
        assert not (outside / "repository-context.md").exists()


def test_authorized_coordinator_candidate_passes_without_creating_files() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        module_dir = web / "apps" / "storefront"
        module_dir.mkdir(parents=True)
        (module_dir / "index.ts").write_text("export const x = 1;\n")
        coordinator = Path(temp) / "payments-platform-aidlc"
        coordinator.mkdir()
        index_path = (coordinator / "aidlc-docs" / "repository-context.md").resolve()
        module_path = (
            coordinator / "aidlc-docs" / "context" / "web" / "storefront.md"
        ).resolve()
        index_fingerprint, _ = content_fingerprint(web)
        module_fingerprint, _ = content_fingerprint(module_dir)
        index_text = "\n".join(
            [
                "# Repository context",
                "",
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Scope",
                "",
                "- Index: `single-repository`",
                "- Repository ID: `web`",
                f"- Fingerprint: `{index_fingerprint}`",
                "",
                "## Modules",
                "",
                "| Module | Source | Context | Status |",
                "| --- | --- | --- | --- |",
                "| `storefront` | `apps/storefront` | [x](context/web/storefront.md) | current |",
                "",
                "<!-- AI-DLC:generated:end -->",
                "",
            ]
        )
        module_text = "\n".join(
            [
                "# AIDLC context — storefront",
                "",
                "<!-- AI-DLC:generated:start -->",
                "",
                "## Identity and scope",
                "",
                "- Repository ID: `web`",
                "- Module ID: `storefront`",
                "- Source: `apps/storefront`",
                f"- Baseline and fingerprint: `deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` / `{module_fingerprint}`",
                "",
                "<!-- AI-DLC:generated:end -->",
                "",
            ]
        )
        roots = {"web": web, "payments-platform-aidlc": coordinator}
        checks = validate_generated_context(
            index_path,
            roots,
            candidate_content={index_path: index_text, module_path: module_text},
        )
        assert all(check.status in {"passed", "not_applicable"} for check in checks)
        assert not index_path.exists()
        assert not module_path.exists()

        rejected = validate_generated_context(
            index_path,
            {"web": web},
            candidate_content={index_path: index_text, module_path: module_text},
        )
        _assert_destination_rejected(rejected)


def test_conflicting_candidate_paths_are_rejected() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        first = web / "aidlc-docs" / "repository-context.md"
        second = web / "aidlc-docs" / "nested" / ".." / "repository-context.md"
        checks = validate_generated_context(
            first,
            {"web": web},
            candidate_content={first: "one\n", second: "two\n"},
        )
        _assert_destination_rejected(checks)
        assert "same destination" in checks[0].detail
        assert not first.exists()


def test_cli_rejects_a_candidate_outside_authorized_roots() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        outside = Path(temp) / "elsewhere" / "repository-context.md"
        staged = Path(temp) / "staged.md"
        staged.write_text("# proposed\n")
        code = cli_validate(
            [
                str(outside),
                f"--root=web={web}",
                f"--candidate={outside}={staged}",
            ]
        )
        assert code == 1
        assert not outside.exists()


def test_git_discovery_failure_is_unresolved_validation_not_a_crash() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        module_dir = web / "apps" / "storefront"
        module_dir.mkdir(parents=True)
        (module_dir / "index.ts").write_text("export const x = 1;\n")
        init_repo(web)
        run(web, "git", "add", ".")
        run(web, "git", "commit", "-qm", "feat: initial")
        _write_valid_module(module_dir, "web", "storefront", "apps/storefront")
        (web / "aidlc-docs").mkdir()
        index = web / "aidlc-docs" / "repository-context.md"
        _write_valid_index(index, web)
        (web / ".git" / "index").write_bytes(b"not a real git index")
        checks = validate_generated_context(index, {"web": web})
        fingerprint = next(check for check in checks if check.name == "index:fingerprint")
        assert fingerprint.status == "unresolved"


def test_validate_generated_context_fails_on_missing_markers_and_headings() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        index = web / "repository-context.md"
        index.write_text("# Repository context\n\nNo generated markers here.\n")
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        structure = next(c for c in checks if c.name == "index:structure")
        assert structure.status == "failed"


def test_validate_generated_context_fails_when_over_budget() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        index = web / "repository-context.md"
        lines = ["# Repository context", "", "<!-- AI-DLC:generated:start -->", "", "## Scope", ""]
        lines += [f"padding line {i}" for i in range(200)]
        lines += ["", "<!-- AI-DLC:generated:end -->", ""]
        index.write_text("\n".join(lines))
        checks = validate_generated_context(
            index, {"web": web}, index_repository_id="web", index_budget=150
        )
        budget = next(c for c in checks if c.name == "index:budget")
        assert budget.status == "failed"


def test_validate_generated_context_reports_unresolved_for_missing_index() -> None:
    with tempfile.TemporaryDirectory() as temp:
        index = Path(temp) / "does-not-exist.md"
        checks = validate_generated_context(index, {})
        assert len(checks) == 1
        assert checks[0].status == "unresolved"


def test_validate_generated_context_multi_repo_requires_repository_column() -> None:
    """Repository identity for each module row must never be guessed."""
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        web = base / "web"
        payments = base / "payments"
        web.mkdir()
        payments.mkdir()
        index = web / "repository-context.md"
        index.write_text(
            "\n".join(
                [
                    "<!-- AI-DLC:generated:start -->",
                    "",
                    "## Scope",
                    "",
                    "- Index: `multi-repository`",
                    "",
                    "## Modules",
                    "",
                    "| Module | Source | Context | Status |",
                    "| --- | --- | --- | --- |",
                    "| `api` | `apps/api` | [x](a.md) | current |",
                    "",
                    "<!-- AI-DLC:generated:end -->",
                ]
            )
        )
        checks = validate_generated_context(index, {"web": web, "payments": payments})
        identity = next(c for c in checks if c.name == "modules:repository-identity")
        assert identity.status == "unresolved"


def test_validate_generated_context_true_multi_repo_engagement_passes() -> None:
    """Same module ID in two repositories, disambiguated by a Repository column."""
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        engagement = base / "engagement"
        web = base / "web"
        payments = base / "payments"
        (engagement / "aidlc-docs").mkdir(parents=True)
        (web / "apps" / "api").mkdir(parents=True)
        (payments / "services" / "api").mkdir(parents=True)
        (web / "apps" / "api" / "index.ts").write_text("export const web = 1;\n")
        (payments / "services" / "api" / "index.ts").write_text("export const pay = 1;\n")
        _write_valid_module(web / "apps" / "api", "web", "api", "apps/api")
        _write_valid_module(payments / "services" / "api", "payments", "api", "services/api")

        index = engagement / "aidlc-docs" / "repository-context.md"
        index.write_text(
            "\n".join(
                [
                    "<!-- AI-DLC:generated:start -->",
                    "",
                    "## Scope",
                    "",
                    "- Index: `multi-repository`",
                    "",
                    "## Modules",
                    "",
                    "| Module | Repository | Source | Context | Status |",
                    "| --- | --- | --- | --- | --- |",
                    "| `api` | `web` | `apps/api` | [x](../../web/apps/api/AIDLC_CONTEXT.md) | current |",
                    "| `api` | `payments` | `services/api` | [x](../../payments/services/api/AIDLC_CONTEXT.md) | current |",
                    "",
                    "<!-- AI-DLC:generated:end -->",
                ]
            )
        )
        checks = validate_generated_context(index, {"web": web, "payments": payments})
        statuses = {check.name: check.status for check in checks}
        assert statuses["modules:duplicate-identity"] == "passed"
        assert statuses["modules:link:../../web/apps/api/AIDLC_CONTEXT.md"] == "passed"
        assert statuses["modules:link:../../payments/services/api/AIDLC_CONTEXT.md"] == "passed"
        assert statuses["modules:source:web:apps/api"] == "passed"
        assert statuses["modules:source:payments:services/api"] == "passed"
        assert statuses["modules:fingerprint:../../web/apps/api/AIDLC_CONTEXT.md"] == "passed"
        assert statuses["modules:fingerprint:../../payments/services/api/AIDLC_CONTEXT.md"] == "passed"
        assert all(check.status in ("passed", "not_applicable") for check in checks)
        assert cli_validate(
            [str(index), "--root", f"web={web}", "--root", f"payments={payments}"]
        ) == 0


def test_cli_validate_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        (web / "apps" / "api").mkdir(parents=True)
        (web / "apps" / "api" / "index.ts").write_text("export const x = 1;\n")
        _write_valid_module(web / "apps" / "api", "web", "api", "apps/api")
        (web / "aidlc-docs").mkdir()
        index = web / "aidlc-docs" / "repository-context.md"
        index_fingerprint, _ = content_fingerprint(web)
        index.write_text(
            "\n".join(
                [
                    "<!-- AI-DLC:generated:start -->",
                    "",
                    "## Scope",
                    "",
                    "- Index: `single-repository`",
                    "- Repository ID: `web`",
                    f"- Fingerprint: `{index_fingerprint}`",
                    "",
                    "## Modules",
                    "",
                    "| Module | Source | Context | Status |",
                    "| --- | --- | --- | --- |",
                    "| `api` | `apps/api` | [x](../apps/api/AIDLC_CONTEXT.md) | current |",
                    "",
                    "<!-- AI-DLC:generated:end -->",
                ]
            )
        )
        ok_code = cli_validate([str(index), "--root", f"web={web}", "--index-repository-id", "web"])
        assert ok_code == 0

        missing_index_code = cli_validate([str(Path(temp) / "missing.md"), "--root", f"web={web}"])
        assert missing_index_code == 2

        bad_arg_code = cli_validate([str(index), "--root", "not-a-pair"])
        assert bad_arg_code == 2


def test_extract_table_column_ignores_fenced_heading_before_real_section() -> None:
    text = "\n".join(
        [
            "```markdown",
            "## Modules",
            "",
            "| Module | Source |",
            "| --- | --- |",
            "| `fake` | `apps/fake` |",
            "```",
            "",
            "## Modules",
            "",
            "| Module | Source |",
            "| --- | --- |",
            "| `real` | `apps/real` |",
        ]
    )
    result = extract_table_column(text, "## Modules", "Module")
    assert result.status == "ok"
    assert result.values == ("real",)


def test_extract_table_column_ignores_tilde_fenced_heading() -> None:
    text = "\n".join(
        [
            "~~~",
            "## Modules",
            "",
            "| Module | Source |",
            "| --- | --- |",
            "| `fake` | `apps/fake` |",
            "~~~",
            "",
            "## Modules",
            "",
            "| Module | Source |",
            "| --- | --- |",
            "| `real` | `apps/real` |",
        ]
    )
    result = extract_table_column(text, "## Modules", "Module")
    assert result.status == "ok"
    assert result.values == ("real",)


def test_structure_heading_outside_generated_block_fails() -> None:
    with tempfile.TemporaryDirectory() as temp:
        index = Path(temp) / "repository-context.md"
        index.write_text(
            "\n".join(
                [
                    "## Scope",
                    "",
                    "<!-- AI-DLC:generated:start -->",
                    "<!-- AI-DLC:generated:end -->",
                ]
            )
        )
        checks = validate_generated_context(index, {})
        structure = next(check for check in checks if check.name == "index:structure")
        assert structure.status == "failed"


def test_parse_recorded_fingerprint_rejects_duplicate_equal_values() -> None:
    doc = "\n".join(
        [
            "<!-- AI-DLC:generated:start -->",
            "",
            "## Scope",
            "",
            "- Fingerprint: `1111111111111111`",
            "- Fingerprint: `1111111111111111`",
            "",
            "<!-- AI-DLC:generated:end -->",
        ]
    )
    assert parse_recorded_fingerprint(doc).status == "ambiguous"


def test_parse_recorded_fingerprint_rejects_multiple_or_malformed_blocks() -> None:
    repeated = "\n".join(
        [
            "<!-- AI-DLC:generated:start -->",
            "## Scope",
            "- Fingerprint: `1111111111111111`",
            "<!-- AI-DLC:generated:end -->",
            "<!-- AI-DLC:generated:start -->",
            "## Scope",
            "- Fingerprint: `1111111111111111`",
            "<!-- AI-DLC:generated:end -->",
        ]
    )
    assert parse_recorded_fingerprint(repeated).status == "ambiguous"
    unclosed = "<!-- AI-DLC:generated:start -->\n## Scope\n- Fingerprint: `1111111111111111`\n"
    assert parse_recorded_fingerprint(unclosed).status == "malformed"
    outside = "## Scope\n\n- Fingerprint: `1111111111111111`\n"
    assert parse_recorded_fingerprint(outside).status == "missing"


def test_parse_recorded_fingerprint_ignores_fingerprinted_prose() -> None:
    doc = "\n".join(
        [
            "<!-- AI-DLC:generated:start -->",
            "",
            "## Scope",
            "",
            "- Fingerprint: `2222222222222222`",
            "- Examined: fingerprinted paths were not all inspected",
            "",
            "<!-- AI-DLC:generated:end -->",
        ]
    )
    field = parse_recorded_fingerprint(doc)
    assert field.status == "ok"
    assert field.value == "2222222222222222"


def _single_repo_fixture(temp: str) -> tuple[Path, Path, Path]:
    web = Path(temp) / "web"
    module = web / "apps" / "storefront"
    module.mkdir(parents=True)
    (module / "index.ts").write_text("export const x = 1;\n")
    _write_valid_module(module, "web", "storefront", "apps/storefront")
    (web / "aidlc-docs").mkdir()
    index = web / "aidlc-docs" / "repository-context.md"
    _write_valid_index(index, web)
    return web, index, module / "AIDLC_CONTEXT.md"


def test_omitted_index_repository_id_still_detects_stale_context() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        (web / "notes.ts").write_text("export const note = 1;\n")
        checks = validate_generated_context(index, {"web": web, "payments": web.parent / "payments"})
        fingerprint = next(check for check in checks if check.name == "index:fingerprint")
        assert fingerprint.status == "failed"
        code = cli_validate([str(index), "--root", f"web={web}"])
        assert code == 1


def test_extra_authorized_root_does_not_skip_single_repo_checks() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        payments = Path(temp) / "payments"
        payments.mkdir()
        checks = validate_generated_context(index, {"web": web, "payments": payments})
        statuses = {check.name: check.status for check in checks}
        assert statuses["modules:repository-identity"] == "passed"
        assert statuses["modules:duplicate-identity"] == "passed"
        assert statuses["modules:source:web:apps/storefront"] == "passed"
        assert statuses["index:fingerprint"] == "passed"


def test_conflicting_supplied_repository_id_fails() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        checks = validate_generated_context(index, {"web": web}, index_repository_id="payments")
        identity = next(check for check in checks if check.name == "index:identity")
        assert identity.status == "failed"
        assert cli_validate(
            [str(index), "--root", f"web={web}", "--index-repository-id", "payments"]
        ) == 1


def test_missing_index_identity_is_unresolved_not_success() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        text = index.read_text().replace("- Index: `single-repository`\n", "").replace(
            "- Repository ID: `web`\n", ""
        )
        index.write_text(text)
        checks = validate_generated_context(index, {"web": web})
        identity = next(check for check in checks if check.name == "index:identity")
        fingerprint = next(check for check in checks if check.name == "index:fingerprint")
        assert identity.status == "unresolved"
        assert fingerprint.status == "unresolved"
        assert cli_validate([str(index), "--root", f"web={web}"]) == 2


def test_module_metadata_must_match_the_index_row() -> None:
    replacements = {
        "repository": ("- Repository ID: `web`", "- Repository ID: `other`"),
        "module": ("- Module ID: `storefront`", "- Module ID: `checkout`"),
        "source": ("- Source: `apps/storefront`", "- Source: `apps/missing`"),
    }
    for label, (old, new) in replacements.items():
        with tempfile.TemporaryDirectory() as temp:
            web, index, module_doc = _single_repo_fixture(temp)
            module_doc.write_text(module_doc.read_text().replace(old, new, 1))
            checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
            identity = next(
                check for check in checks if check.name.endswith("AIDLC_CONTEXT.md") and "identity" in check.name
            )
            assert identity.status == "failed", label
            fingerprint = next(
                check
                for check in checks
                if check.name.endswith("AIDLC_CONTEXT.md") and "fingerprint" in check.name
            )
            assert fingerprint.status != "passed", label


def test_missing_evidence_file_fails_without_treating_symbols_as_paths() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        module_doc.write_text(
            module_doc.read_text().replace(
                "<!-- AI-DLC:generated:end -->",
                "\n".join(
                    [
                        "## Evidence and existing docs",
                        "",
                        "- `OrderPlacedEvent`",
                        "- `apps/storefront/deleted.ts`",
                        "",
                        "<!-- AI-DLC:generated:end -->",
                    ]
                ),
            )
        )
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        evidence = [check for check in checks if "evidence" in check.name]
        assert any(check.status == "failed" and "deleted.ts" in check.name for check in evidence)
        assert not any("OrderPlacedEvent" in check.name for check in checks)
        assert cli_validate([str(index), "--root", f"web={web}", "--index-repository-id", "web"]) == 1


def test_directory_context_target_is_a_structured_failure() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        index.write_text(
            index.read_text().replace(
                "../apps/storefront/AIDLC_CONTEXT.md",
                "../apps/storefront",
            )
        )
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        link = next(check for check in checks if check.name == "modules:link:../apps/storefront")
        assert link.status == "failed"
        assert cli_validate([str(index), "--root", f"web={web}", "--index-repository-id", "web"]) == 1


def test_failed_check_takes_exit_precedence_over_unresolved() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        index = web / "repository-context.md"
        lines = ["# Repository context", "", "<!-- AI-DLC:generated:start -->", "", "## Scope", ""]
        lines += [f"padding line {i}" for i in range(200)]
        lines += ["", "<!-- AI-DLC:generated:end -->", ""]
        index.write_text("\n".join(lines))
        code = cli_validate([str(index), "--root", f"web={web}", "--index-budget", "150"])
        assert code == 1


def test_unavailable_repository_is_unresolved_not_failed() -> None:
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        web = base / "web"
        engagement = base / "engagement"
        (web / "apps" / "api").mkdir(parents=True)
        (engagement / "aidlc-docs").mkdir(parents=True)
        (web / "apps" / "api" / "index.ts").write_text("export const x = 1;\n")
        _write_valid_module(web / "apps" / "api", "reporting", "api", "services/api")
        index = engagement / "aidlc-docs" / "repository-context.md"
        index.write_text(
            "\n".join(
                [
                    "<!-- AI-DLC:generated:start -->",
                    "",
                    "## Scope",
                    "",
                    "- Index: `multi-repository`",
                    "",
                    "## Modules",
                    "",
                    "| Module | Repository | Source | Context | Status |",
                    "| --- | --- | --- | --- | --- |",
                    "| `api` | `reporting` | `services/api` | [x](../../web/apps/api/AIDLC_CONTEXT.md) | current |",
                    "",
                    "<!-- AI-DLC:generated:end -->",
                ]
            )
        )
        roots = {"web": web, "reporting": base / "reporting"}
        checks = validate_generated_context(index, roots)
        source = next(check for check in checks if check.name == "modules:source:reporting:services/api")
        assert source.status == "unresolved"
        assert all(check.status != "failed" for check in checks)
        assert cli_validate(
            [str(index), "--root", f"web={web}", "--root", f"reporting={base / 'reporting'}"]
        ) == 2


def test_artifact_home_fallback_document_is_not_required_inside_source() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        source = web / "apps" / "storefront"
        source.mkdir(parents=True)
        (source / "index.ts").write_text("export const x = 1;\n")
        fallback_dir = web / "aidlc-docs" / "context" / "web"
        fallback_dir.mkdir(parents=True)
        fingerprint, _ = content_fingerprint(source)
        fallback = fallback_dir / "storefront.md"
        fallback.write_text(
            "\n".join(
                [
                    "# AIDLC context — storefront",
                    "",
                    "The colocated file was not writable. Source root: `apps/storefront`.",
                    "",
                    "<!-- AI-DLC:generated:start -->",
                    "",
                    "## Identity and scope",
                    "",
                    "- Repository ID: `web`",
                    "- Module ID: `storefront`",
                    "- Source: `apps/storefront`",
                    f"- Baseline and fingerprint: `deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` / `{fingerprint}`",
                    "",
                    "<!-- AI-DLC:generated:end -->",
                    "",
                ]
            )
        )
        index = web / "aidlc-docs" / "repository-context.md"
        index_fingerprint, _ = content_fingerprint(web)
        index.write_text(
            "\n".join(
                [
                    "<!-- AI-DLC:generated:start -->",
                    "",
                    "## Scope",
                    "",
                    "- Index: `single-repository`",
                    "- Repository ID: `web`",
                    f"- Fingerprint: `{index_fingerprint}`",
                    "",
                    "## Modules",
                    "",
                    "| Module | Source | Context | Status |",
                    "| --- | --- | --- | --- |",
                    "| `storefront` | `apps/storefront` | [x](context/web/storefront.md) | current |",
                    "",
                    "<!-- AI-DLC:generated:end -->",
                ]
            )
        )
        before = {path: path.read_text() for path in (index, fallback)}
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        assert {path: path.read_text() for path in (index, fallback)} == before
        statuses = {check.name: check.status for check in checks}
        assert statuses["modules:fingerprint:context/web/storefront.md"] == "passed"
        assert statuses["modules:identity:context/web/storefront.md"] == "passed"
        assert not fallback.is_relative_to(source)
        assert cli_validate([str(index), "--root", f"web={web}", "--index-repository-id", "web"]) == 0


def _insert_before_generated_end(path: Path, extra: str) -> None:
    text = path.read_text()
    path.write_text(text.replace("<!-- AI-DLC:generated:end -->", f"{extra}\n<!-- AI-DLC:generated:end -->", 1))


def _duplicate_section(path: Path, heading: str) -> None:
    lines = path.read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == heading)
    end = start + 1
    while end < len(lines):
        if lines[end].startswith("## ") or lines[end].strip() == "<!-- AI-DLC:generated:end -->":
            break
        end += 1
    block = "\n".join(lines[start:end]).rstrip()
    _insert_before_generated_end(path, block)


def _replace_context_target(index: Path, target: str) -> None:
    text = index.read_text().replace("[x](../apps/storefront/AIDLC_CONTEXT.md)", f"[x]({target})")
    index.write_text(text)


def test_https_context_target_fails_without_skipping_the_module() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        _replace_context_target(index, "https://example.com/context.md")
        module_doc.write_text("this is not a valid context document\n")
        checks = validate_generated_context(index, {"web": web})
        link = next(check for check in checks if check.name == "modules:link:https://example.com/context.md")
        assert link.status == "failed"
        assert not any(check.name.startswith("modules:identity:") and check.status == "passed" for check in checks)
        assert not any(check.name.startswith("modules:fingerprint:") and check.status == "passed" for check in checks)
        assert cli_validate([str(index), "--root", f"web={web}"]) == 1


def test_anchor_context_target_fails() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        _replace_context_target(index, "#scope")
        module_doc.write_text("this is not a valid context document\n")
        checks = validate_generated_context(index, {"web": web})
        link = next(check for check in checks if check.name == "modules:link:#scope")
        assert link.status == "failed"
        assert not any(check.status == "passed" and check.name.startswith("modules:identity:") for check in checks)
        assert cli_validate([str(index), "--root", f"web={web}"]) == 1


def test_local_context_target_may_include_a_fragment() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        target = "../apps/storefront/AIDLC_CONTEXT.md#identity"
        _replace_context_target(index, target)
        checks = validate_generated_context(index, {"web": web})
        statuses = {check.name: check.status for check in checks}
        assert statuses[f"modules:link:{target}"] == "passed"
        assert statuses[f"modules:identity:{target}"] == "passed"
        assert statuses[f"modules:fingerprint:{target}"] == "passed"
        assert cli_validate([str(index), "--root", f"web={web}"]) == 0


def test_external_evidence_link_stays_not_applicable() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        _insert_before_generated_end(
            module_doc,
            "\n".join(
                [
                    "## Evidence and existing docs",
                    "",
                    "- [guide](https://example.com/guide)",
                    "",
                ]
            ),
        )
        checks = validate_generated_context(index, {"web": web})
        evidence = next(
            check for check in checks if check.name.endswith("https://example.com/guide")
        )
        assert evidence.status == "not_applicable"
        assert all(check.status in ("passed", "not_applicable") for check in checks)
        assert cli_validate([str(index), "--root", f"web={web}"]) == 0


def test_duplicate_module_identity_sections_with_conflicting_values_fail() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        _insert_before_generated_end(
            module_doc,
            "\n".join(
                [
                    "## Identity and scope",
                    "",
                    "- Repository ID: `wrong`",
                    "- Module ID: `wrong`",
                    "- Source: `missing`",
                    "",
                ]
            ),
        )
        label = "../apps/storefront/AIDLC_CONTEXT.md"
        checks = validate_generated_context(index, {"web": web})
        statuses = {check.name: check.status for check in checks}
        assert statuses[f"modules:structure:{label}"] == "failed"
        assert statuses[f"modules:identity:{label}"] == "failed"
        assert statuses[f"modules:fingerprint:{label}"] != "passed"
        assert cli_validate([str(index), "--root", f"web={web}"]) == 1


def test_duplicate_module_identity_sections_with_identical_values_fail() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        _duplicate_section(module_doc, "## Identity and scope")
        label = "../apps/storefront/AIDLC_CONTEXT.md"
        checks = validate_generated_context(index, {"web": web})
        statuses = {check.name: check.status for check in checks}
        assert statuses[f"modules:structure:{label}"] == "failed"
        assert statuses[f"modules:identity:{label}"] == "failed"
        assert statuses[f"modules:fingerprint:{label}"] != "passed"
        assert cli_validate([str(index), "--root", f"web={web}"]) == 1


def test_duplicate_index_scope_sections_fail() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        _duplicate_section(index, "## Scope")
        checks = validate_generated_context(index, {"web": web})
        statuses = {check.name: check.status for check in checks}
        assert statuses["index:structure"] == "failed"
        assert statuses["index:identity"] != "passed"
        assert statuses["index:fingerprint"] != "passed"
        assert cli_validate([str(index), "--root", f"web={web}"]) == 1


def test_duplicate_index_modules_sections_fail() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        _duplicate_section(index, "## Modules")
        checks = validate_generated_context(index, {"web": web})
        statuses = {check.name: check.status for check in checks}
        assert statuses["modules:table"] == "failed"
        assert cli_validate([str(index), "--root", f"web={web}"]) == 1


def _assert_fenced_heading_is_not_a_duplicate(fence: str) -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        _insert_before_generated_end(
            module_doc,
            "\n".join(
                [
                    fence,
                    "## Identity and scope",
                    "",
                    "- Repository ID: `wrong`",
                    "- Module ID: `wrong`",
                    "- Source: `missing`",
                    fence,
                    "",
                ]
            ),
        )
        _insert_before_generated_end(
            index,
            "\n".join(
                [
                    fence,
                    "## Scope",
                    "",
                    "- Repository ID: `wrong`",
                    fence,
                    "",
                    fence,
                    "## Modules",
                    fence,
                    "",
                ]
            ),
        )
        checks = validate_generated_context(index, {"web": web})
        assert all(check.status in ("passed", "not_applicable") for check in checks)
        assert cli_validate([str(index), "--root", f"web={web}"]) == 0


def test_backtick_fenced_canonical_headings_are_not_duplicate_sections() -> None:
    _assert_fenced_heading_is_not_a_duplicate("```")


def test_tilde_fenced_canonical_headings_are_not_duplicate_sections() -> None:
    _assert_fenced_heading_is_not_a_duplicate("~~~")


def test_canonical_heading_outside_generated_block_is_not_a_duplicate() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        module_doc.write_text(
            module_doc.read_text()
            + "\n## Identity and scope\n\n- Repository ID: `wrong`\n- Module ID: `wrong`\n- Source: `missing`\n"
        )
        index.write_text(
            index.read_text() + "\n## Scope\n\n- Repository ID: `wrong`\n\n## Modules\n\n| Module |\n| --- |\n| `other` |\n"
        )
        checks = validate_generated_context(index, {"web": web})
        assert all(check.status in ("passed", "not_applicable") for check in checks)
        assert cli_validate([str(index), "--root", f"web={web}"]) == 0


def test_valid_single_and_multi_repository_documents_still_pass() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        checks = validate_generated_context(index, {"web": web})
        assert all(check.status in ("passed", "not_applicable") for check in checks)
        assert cli_validate([str(index), "--root", f"web={web}"]) == 0
    test_validate_generated_context_true_multi_repo_engagement_passes()


def test_classify_fingerprint_change_distinguishes_unavailable_unchanged_changed() -> None:
    assert classify_fingerprint_change(None, "a1b2c3d4e5f6a1b2") == "unavailable"
    assert classify_fingerprint_change("", "a1b2c3d4e5f6a1b2") == "unavailable"
    assert classify_fingerprint_change("a1b2c3d4e5f6a1b2", "a1b2c3d4e5f6a1b2") == "unchanged"
    assert classify_fingerprint_change("a1b2c3d4e5f6a1b2", "deadbeefdeadbeef") == "changed"


def test_classify_fingerprint_change_drives_a_real_no_op_decision() -> None:
    """The same scope hashed twice with no edits must report "unchanged"."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        (root / "service.py").write_text("def handler():\n    return 1\n")
        first, _ = content_fingerprint(root)
        second, _ = content_fingerprint(root)
        assert classify_fingerprint_change(first, second) == "unchanged"

        (root / "service.py").write_text("def handler():\n    return 2\n")
        third, _ = content_fingerprint(root)
        assert classify_fingerprint_change(first, third) == "changed"


def test_is_declared_submodule_distinguishes_real_submodule_from_nested_checkout() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "coordinator"
        root.mkdir()
        init_repo(root)

        declared = root / "vendor" / "shared-lib"
        declared.mkdir(parents=True)
        init_repo(declared)
        (root / ".gitmodules").write_text(
            '[submodule "shared-lib"]\n'
            "\tpath = vendor/shared-lib\n"
            "\turl = https://example.invalid/shared-lib.git\n"
        )
        assert is_declared_submodule(declared, root) is True

        stray = root / "nested" / "unrelated-checkout"
        stray.mkdir(parents=True)
        init_repo(stray)
        assert is_declared_submodule(stray, root) is False

        # No .gitmodules at all: nothing nested is ever a declared submodule.
        no_file_root = Path(temp) / "plain"
        no_file_root.mkdir()
        plain_nested = no_file_root / "nested"
        plain_nested.mkdir()
        assert is_declared_submodule(plain_nested, no_file_root) is False


def test_bugbot_reprompt_allowed_respects_recorded_decisions() -> None:
    # Declined is never re-proposed by this helper, in any run.
    assert bugbot_reprompt_allowed("declined", same_run=True) is False
    assert bugbot_reprompt_allowed("declined", same_run=False) is False

    # Deferred is not re-proposed within the same run, but may be later.
    assert bugbot_reprompt_allowed("deferred", same_run=True) is False
    assert bugbot_reprompt_allowed("deferred", same_run=False) is True

    # Approved needs no reprompt; the existing approval applies instead.
    assert bugbot_reprompt_allowed("approved", same_run=True) is False
    assert bugbot_reprompt_allowed("approved", same_run=False) is False

    # No decision on record: a prompt is allowed.
    assert bugbot_reprompt_allowed("", same_run=False) is True
    assert bugbot_reprompt_allowed("unknown", same_run=False) is True


def test_diff_module_sources_reports_added_and_removed_paths() -> None:
    recorded = ["services/orders", "services/billing"]
    current = ["./services/billing", "services/notifications"]
    diff = diff_module_sources(recorded, current)
    assert diff["added"] == ("services/notifications",)
    assert diff["removed"] == ("services/orders",)
    assert diff["unchanged"] == ("services/billing",)


def test_scope_verification_status_is_partial_when_any_scope_is_unavailable() -> None:
    assert scope_verification_status([True, True]) == "complete"
    assert scope_verification_status([True, False]) == "partial"
    assert scope_verification_status([False, False]) == "unavailable"
    assert scope_verification_status([]) == "unavailable"


def test_adopted_coordinator_destination_ignores_source_writability() -> None:
    assert resolve_placement(None) == "distributed"
    assert resolve_placement("distributed") == "distributed"
    # A folder name is not an input. Missing config stays distributed.
    assert module_context_destination("distributed", "payments-api", "checkout") == "AIDLC_CONTEXT.md"
    coordinator_path = module_context_destination(
        "adopted-coordinator", "payments-api", "checkout"
    )
    assert coordinator_path == "aidlc-docs/context/payments-api/checkout.md"
    try:
        resolve_placement("payments-api-aidlc")
    except ValueError as error:
        assert "conflicting placement" in str(error)
    else:
        raise AssertionError("a name-like placement value must not be accepted")


def test_migration_destination_preserves_placement_until_approved() -> None:
    # Discovery and proposal preparation never switch persisted placement.
    assert (
        migration_destination_placement("adopted-coordinator", migration_approved=False)
        == "adopted-coordinator"
    )
    # Only an approved migration proposes the distributed destination.
    assert (
        migration_destination_placement("adopted-coordinator", migration_approved=True)
        == "distributed"
    )
    # An ordinary refresh of an already-distributed repository is unaffected
    # either way.
    assert migration_destination_placement("distributed", migration_approved=False) == "distributed"
    assert migration_destination_placement("distributed", migration_approved=True) == "distributed"
    # An unknown placement is a conflict in either approval state. It must
    # not be rewritten into "distributed".
    for approved in (False, True):
        try:
            migration_destination_placement("corrupt-value", migration_approved=approved)
        except ValueError as error:
            assert "conflicting placement" in str(error)
        else:
            raise AssertionError("an invalid placement must fail fast")


def test_repository_is_named_coordinator_ignores_placement_mode() -> None:
    # Placement mode is not an identity. The literal mode string never
    # proves this repository is the coordinator, even if it is also passed
    # as the repository id.
    assert (
        repository_is_named_coordinator(
            "adopted-coordinator", None, "product-app", None
        )
        is False
    )
    assert (
        repository_is_named_coordinator(
            "adopted-coordinator", None, "adopted-coordinator", None
        )
        is False
    )
    assert repository_is_named_coordinator(None, None, "legacy-aidlc", ".") is False
    assert repository_is_named_coordinator("", "  ", "legacy-aidlc", ".") is False
    # An explicit Coordinator name must equal this repository's id.
    assert (
        repository_is_named_coordinator(
            "legacy-aidlc", None, "legacy-aidlc", None
        )
        is True
    )
    assert (
        repository_is_named_coordinator(
            "legacy-aidlc", None, "product-app", None
        )
        is False
    )
    # An explicit Coordinator root must normalize to this repository's root.
    assert (
        repository_is_named_coordinator(
            None, "../legacy-aidlc/", None, "../legacy-aidlc"
        )
        is True
    )
    assert (
        repository_is_named_coordinator(
            None, "../legacy-aidlc", None, "../product-app"
        )
        is False
    )
    # When both fields are present, both must name this repository.
    assert (
        repository_is_named_coordinator(
            "legacy-aidlc", "../product-app", "legacy-aidlc", "../legacy-aidlc"
        )
        is False
    )


def test_classify_repository_role_never_decides_from_name_alone() -> None:
    # A name that merely looks legacy, with no other evidence, is
    # unresolved -- never "retire" and never deleted on that basis alone.
    assert (
        classify_repository_role(
            has_plugin_manifest=False,
            has_shared_methodology_marker=False,
            name_matches_legacy_pattern=True,
        )
        == "unresolved"
    )
    # Coordinator identity is an explicit name or root match, not the
    # adopted-coordinator placement mode recorded on a product repository.
    assert (
        classify_repository_role(
            has_plugin_manifest=False,
            has_shared_methodology_marker=False,
            name_matches_legacy_pattern=True,
            coordinator_name="legacy-aidlc",
            repository_id="legacy-aidlc",
        )
        == "product-coordination-repository"
    )
    assert (
        classify_repository_role(
            has_plugin_manifest=False,
            has_shared_methodology_marker=False,
            name_matches_legacy_pattern=False,
            coordinator_name="legacy-aidlc",
            repository_id="product-app",
        )
        == "product-source-repository"
    )
    assert (
        classify_repository_role(
            has_plugin_manifest=False,
            has_shared_methodology_marker=True,
            name_matches_legacy_pattern=False,
        )
        == "shared-methodology-checkout"
    )
    # Shared-methodology evidence wins over a coordinator name match, so the
    # checkout stays ineligible for deletion.
    assert (
        classify_repository_role(
            has_plugin_manifest=False,
            has_shared_methodology_marker=True,
            name_matches_legacy_pattern=False,
            coordinator_name="legacy-aidlc",
            repository_id="legacy-aidlc",
        )
        == "shared-methodology-checkout"
    )
    assert (
        classify_repository_role(
            has_plugin_manifest=True,
            has_shared_methodology_marker=True,
            name_matches_legacy_pattern=True,
            coordinator_name="legacy-aidlc",
            repository_id="legacy-aidlc",
        )
        == "plugin-installation"
    )
    # No evidence and no name match: an ordinary product source repository.
    assert (
        classify_repository_role(
            has_plugin_manifest=False,
            has_shared_methodology_marker=False,
            name_matches_legacy_pattern=False,
        )
        == "product-source-repository"
    )


def test_relocate_workspace_folder_path_recomputes_relative_paths() -> None:
    # Moving the workspace file into one of the sibling product repositories
    # (the destination for that repository's own folder entry becomes ".").
    assert (
        relocate_workspace_folder_path(
            "engagement/legacy-aidlc", "../product-app", "engagement/product-app"
        )
        == "."
    )
    # A sibling that is not the new workspace location recomputes to a
    # different relative path, not the old one.
    assert (
        relocate_workspace_folder_path(
            "engagement/legacy-aidlc", "../product-api", "engagement/product-app"
        )
        == "../product-api"
    )
    # Moving the workspace one level deeper adds a parent-directory segment.
    assert (
        relocate_workspace_folder_path(
            "engagement", "product-app", "engagement/nested/new-home"
        )
        == "../../product-app"
    )
    # An already-absolute folder path is not joined onto the old directory.
    assert (
        relocate_workspace_folder_path(
            "/work/engagement/legacy-aidlc",
            "/work/engagement/product-app",
            "/work/engagement/product-app",
        )
        == "."
    )
    assert (
        relocate_workspace_folder_path(
            "/work/engagement/legacy-aidlc",
            "/work/engagement/product-api",
            "/work/engagement/product-app",
        )
        == "../product-api"
    )
    try:
        relocate_workspace_folder_path(
            "engagement/legacy-aidlc",
            "/work/engagement/product-app",
            "engagement/product-app",
        )
    except ValueError as error:
        assert "same coordinate system" in str(error)
    else:
        raise AssertionError("mixed absolute and relative paths must fail")


def test_checkout_deletion_readiness_blocks_until_every_precondition_passes() -> None:
    # Every precondition satisfied: ready, no blocking reasons.
    assert (
        checkout_deletion_readiness(
            explicit_target="engagement/legacy-aidlc",
            approved_target="engagement/legacy-aidlc",
            migration_confirmed=True,
            has_uncommitted_changes=False,
            has_unestablished_recovery=False,
            retention_established=True,
            repository_role="product-coordination-repository",
            has_active_references=False,
        )
        == ()
    )
    # A generic approval that does not name this exact target blocks it.
    mismatched = checkout_deletion_readiness(
        explicit_target="engagement/legacy-aidlc",
        approved_target=None,
        migration_confirmed=True,
        has_uncommitted_changes=False,
        has_unestablished_recovery=False,
        retention_established=True,
        repository_role="product-coordination-repository",
        has_active_references=False,
    )
    assert len(mismatched) == 1 and "does not name this exact target" in mismatched[0]
    # Unmigrated content, local changes, unrecoverable commits, and missing
    # retention each report their own reason, and all can block at once.
    every_reason = checkout_deletion_readiness(
        explicit_target="x",
        approved_target="x",
        migration_confirmed=False,
        has_uncommitted_changes=True,
        has_unestablished_recovery=True,
        retention_established=False,
        repository_role="product-coordination-repository",
        has_active_references=False,
    )
    assert len(every_reason) == 4


def test_checkout_deletion_readiness_rejects_unsafe_targets() -> None:
    ready = dict(
        explicit_target="engagement/legacy-aidlc",
        approved_target="engagement/legacy-aidlc",
        migration_confirmed=True,
        has_uncommitted_changes=False,
        has_unestablished_recovery=False,
        retention_established=True,
        repository_role="product-coordination-repository",
        has_active_references=False,
    )
    assert checkout_deletion_readiness(**ready) == ()

    wildcard = checkout_deletion_readiness(
        **{**ready, "explicit_target": "*aidlc*", "approved_target": "*aidlc*"}
    )
    assert any("wildcard" in reason for reason in wildcard)

    mismatched = checkout_deletion_readiness(
        **{**ready, "approved_target": "engagement/other-aidlc"}
    )
    assert any("does not name this exact target" in reason for reason in mismatched)

    shared = checkout_deletion_readiness(
        **{**ready, "repository_role": "shared-methodology-checkout"}
    )
    assert any("shared methodology" in reason for reason in shared)

    dirty = checkout_deletion_readiness(**{**ready, "has_uncommitted_changes": True})
    assert any("untracked" in reason or "uncommitted" in reason or "staged" in reason for reason in dirty)

    unmigrated = checkout_deletion_readiness(**{**ready, "migration_confirmed": False})
    assert any("not confirmed" in reason for reason in unmigrated)

    unrecoverable = checkout_deletion_readiness(
        **{**ready, "has_unestablished_recovery": True}
    )
    assert any("unestablished recovery" in reason for reason in unrecoverable)

    no_retention = checkout_deletion_readiness(**{**ready, "retention_established": False})
    assert any("retention" in reason for reason in no_retention)

    referenced = checkout_deletion_readiness(**{**ready, "has_active_references": True})
    assert any("references still point" in reason for reason in referenced)


def test_retirement_decision_pending_mirrors_bugbot_reprompt_semantics() -> None:
    # No decision on record: always ask.
    assert retirement_decision_pending(None, same_run=False) is True
    # Deferred: not re-asked within the same run, but still pending later.
    assert retirement_decision_pending("defer", same_run=True) is False
    assert retirement_decision_pending("defer", same_run=False) is True
    # A final choice (A or B) is never re-asked, in any run.
    assert retirement_decision_pending("retire-and-delete", same_run=False) is False
    assert retirement_decision_pending("retire-and-retain-checkout", same_run=True) is False


def test_migration_outcome_reports_partial_without_implying_atomicity() -> None:
    distributed = {"app": "distributed", "api": "distributed"}
    # Distributed context plus a finished retirement is complete. Option B
    # (keep the checkout only as a historical copy) uses "completed".
    assert migration_outcome(distributed, "completed") == "complete"
    # No coordinator in scope does not by itself block an all-distributed run.
    assert migration_outcome(distributed, "not-applicable") == "complete"
    # Deferred, blocked, or missing retirement is never complete.
    assert migration_outcome(distributed, "deferred") == "pending"
    assert migration_outcome(distributed, "blocked") == "blocked"
    assert migration_outcome(distributed, "unresolved") == "pending"
    # One repository unavailable must report "partial," never "complete."
    assert (
        migration_outcome(
            {"app": "distributed", "api": "unavailable"}, "completed"
        )
        == "partial"
    )
    # Every repository explicitly retained is a deliberate outcome, not a
    # failure, once coordinator disposition is also resolved.
    assert (
        migration_outcome({"app": "retained-adopted-coordinator"}, "not-applicable")
        == "retained"
    )
    # Keeping the adopted-coordinator architecture is "retained", not a
    # finished distributed migration.
    assert (
        migration_outcome({"app": "retained-adopted-coordinator"}, "retained")
        == "retained"
    )
    # Nothing migrated and something failed or unavailable: blocked.
    assert (
        migration_outcome({"app": "failed", "api": "unavailable"}, "completed")
        == "blocked"
    )
    assert migration_outcome({}, "not-applicable") == "blocked"
    try:
        migration_outcome({"app": "distributed", "api": "typo-status"}, "completed")
    except ValueError as error:
        assert "typo-status" in str(error)
    else:
        raise AssertionError("an unknown repository state must fail")
    try:
        migration_outcome(distributed, "typo-disposition")
    except ValueError as error:
        assert "typo-disposition" in str(error)
    else:
        raise AssertionError("an unknown coordinator disposition must fail")
    # Distributed repositories plus an active adopted-coordinator choice is
    # contradictory: option B after a distributed migration is "completed".
    try:
        migration_outcome(distributed, "retained")
    except ValueError as error:
        assert "retained" in str(error)
    else:
        raise AssertionError("distributed repositories cannot use disposition retained")
    try:
        migration_outcome(
            {"app": "distributed", "api": "retained-adopted-coordinator"},
            "retained",
        )
    except ValueError as error:
        assert "retained" in str(error)
    else:
        raise AssertionError("a mixed repository set cannot use disposition retained")


def test_stale_proposal_does_not_match_a_newer_destination() -> None:
    assert proposal_is_current("abc", "abc", "old text", "old text") is True
    assert proposal_is_current("abc", "def", "old text", "old text") is False
    assert proposal_is_current("abc", "abc", "old text", "user edit") is False
    assert proposal_is_current("abc", "abc", None, "file appeared") is False


def test_unrelated_rules_are_not_part_of_the_approved_write_set() -> None:
    existing = [
        ".cursor/rules/team-tests.mdc",
        ".cursor/rules/migrations.mdc",
    ]
    approved = [".cursor/rules/migrations.mdc"]
    assert unrelated_rules_preserved(existing, approved) == (".cursor/rules/team-tests.mdc",)


# --- Stage 2 no-op must not hide pending set B/C work (finding 4) ---------
#
# These are unit tests of the deterministic decision helper
# `context_sync_outcome`, not an end-to-end run of the `sync-context` skill
# itself (the skill is Markdown instructions interpreted by an agent, not a
# Python entry point). They prove the *combination rule* is reachable and
# correct; they do not exercise Stage 1's discovery, Stage 3's proposal
# drafting, or any other skill behavior.


def test_context_sync_outcome_unchanged_with_first_time_missing_bugbot_config() -> None:
    # Context unchanged (set A), but Bugbot (set B) has never been proposed
    # for this repository: `bugbot_reprompt_allowed` on no recorded decision
    # is True, so set B still has pending work.
    bugbot_pending = bugbot_reprompt_allowed("", same_run=False)
    assert bugbot_pending is True
    outcome = context_sync_outcome("unchanged", bugbot_pending, False, False)
    assert outcome == "context_current_migration_pending"


def test_context_sync_outcome_unchanged_with_previously_declined_bugbot_proposal() -> None:
    # Context unchanged (set A); Bugbot (set B) was explicitly declined, so
    # it must not be re-proposed and must not count as pending work.
    bugbot_pending = bugbot_reprompt_allowed("declined", same_run=False)
    assert bugbot_pending is False
    outcome = context_sync_outcome("unchanged", bugbot_pending, False, False)
    assert outcome == "no_relevant_changes"


def test_context_sync_outcome_unchanged_with_pending_legacy_cleanup() -> None:
    # Context unchanged (set A); legacy migration cleanup (set C) still has
    # an unresolved, named cleanup set waiting on approval.
    outcome = context_sync_outcome("unchanged", False, False, True)
    assert outcome == "context_current_migration_pending"


def test_context_sync_outcome_full_no_op_when_nothing_is_actionable() -> None:
    # No relevant changes anywhere and no pending work in any set: this is
    # the only combination that reaches a full no-op (no write, no new
    # approval question).
    outcome = context_sync_outcome("unchanged", False, False, False)
    assert outcome == "no_relevant_changes"

    # A changed scope with no B/C work is "relevant updates found", not a
    # no-op, and is never confused with the no-op outcome above.
    assert context_sync_outcome("changed", False, False, False) == "relevant_updates_found"
    # An unavailable prior baseline is first-time generation, not a no-op.
    assert context_sync_outcome("unavailable", False, False, False) == "relevant_updates_found"


def test_context_sync_outcome_is_reachable_for_a_configuration_only_change() -> None:
    # A pending `## Project references` update (for example: switch Jira
    # boards) must stay reachable even though the source fingerprint is
    # unchanged. Before this fix, an unchanged fingerprint always produced
    # "no_relevant_changes" here, making a confirmed, user-requested
    # configuration change unreachable.
    outcome = context_sync_outcome(
        "unchanged", False, False, False, project_reference_pending=True
    )
    assert outcome == "relevant_updates_found"

    # A declined/absent configuration change (the default) must not change
    # the pre-existing no-op outcome.
    assert context_sync_outcome("unchanged", False, False, False) == "no_relevant_changes"
    assert (
        context_sync_outcome("unchanged", False, False, False, project_reference_pending=False)
        == "no_relevant_changes"
    )

    # A pending configuration change alongside other pending work is still
    # "relevant updates found", not the migration-pending outcome, since
    # set A itself now has actionable work.
    assert (
        context_sync_outcome("unchanged", True, False, False, project_reference_pending=True)
        == "relevant_updates_found"
    )


def test_duplicate_managed_configuration_heading_is_ambiguous() -> None:
    config = """
## Context identities
- Repository: `payments-api`

## Bugbot decisions
- Repository: `payments-api`

## Context identities
- Repository: `other`
"""
    identities = find_live_section(config, "## Context identities")
    decisions = find_live_section(config, "## Bugbot decisions")
    assert identities.status == "ambiguous"
    assert decisions.status == "ok"


def test_context_identities_stop_at_project_references() -> None:
    config = """
## Context identities
- Repository: `payments-api`
  - Canonical remote: `github.com/example/payments-api`

## Project references
- Jira site: `example.atlassian.net`
- Jira project: `PROJ`
- Jira board: `https://example.atlassian.net/jira/software/c/projects/PROJ/boards/1`
"""
    identities = find_live_section(config, "## Context identities")
    assert identities.status == "ok"
    identity_text = "\n".join(identities.lines)
    assert "Repository: `payments-api`" in identity_text
    assert "Jira site" not in identity_text
    assert "Project references" not in identity_text

    references = parse_project_references(config)
    assert references.status == "ok"
    assert references.values == {
        "Jira site": "example.atlassian.net",
        "Jira project": "PROJ",
        "Jira board": "https://example.atlassian.net/jira/software/c/projects/PROJ/boards/1",
    }


def test_missing_project_references_do_not_invalidate_identities() -> None:
    config = """
## Context identities
- Repository: `payments-api`
"""
    identities = find_live_section(config, "## Context identities")
    assert identities.status == "ok"
    assert "Repository: `payments-api`" in "\n".join(identities.lines)
    assert parse_project_references(config).status == "missing"


def test_duplicate_project_reference_sections_are_ambiguous() -> None:
    config = """
## Project references
- Jira project: `PROJ`

## Project references
- Jira project: `OTHER`
"""
    references = parse_project_references(config)
    assert references.status == "ambiguous"
    assert references.values == {}


def test_project_references_reject_a_site_url_and_an_unknown_figma_role() -> None:
    site = parse_project_references(
        "## Project references\n- Jira site: `https://example.atlassian.net/wiki`\n"
    )
    assert site.status == "invalid"
    assert "host only" in site.detail

    role = parse_project_references(
        "\n".join(
            [
                "## Project references",
                "- Figma reference: `https://www.figma.com/design/EXAMPLE/file`",
                "- Figma role: `inspiration-maybe`",
            ]
        )
    )
    assert role.status == "invalid"
    assert "not recognized" in role.detail

    role_without_url = parse_project_references(
        "## Project references\n- Figma role: `inspiration`\n"
    )
    assert role_without_url.status == "invalid"
    assert "without a Figma reference" in role_without_url.detail


def test_project_references_keep_a_board_without_treating_it_as_the_project() -> None:
    references = parse_project_references(
        "\n".join(
            [
                "## Project references",
                "- Jira board: `https://example.atlassian.net/jira/software/c/projects/PROJ/boards/1`",
                "- Figma reference: `https://www.figma.com/design/EXAMPLE/file`",
                "- Figma role: `approved-design`",
            ]
        )
    )
    assert references.status == "ok"
    assert "Jira project" not in references.values
    assert references.values["Figma role"] == "approved-design"


def test_project_references_flag_a_recognized_field_without_backticks() -> None:
    # A recognized field name written without the canonical backtick value
    # format must be flagged as invalid, not silently skipped. Before this
    # fix, `parse_labeled_fields`'s strict regex made the whole line
    # invisible, and the field was dropped from `values` with no error.
    references = parse_project_references(
        "## Project references\n"
        "- Jira site: example.atlassian.net\n"
        "- Jira project: PROJ\n"
    )
    assert references.status == "invalid"
    assert "Jira site" in references.detail
    assert "Jira project" in references.detail
    # A rejected field must never be mistaken for a confirmed one.
    assert references.values == {}


def test_project_references_detect_a_mixed_quoted_and_unquoted_duplicate() -> None:
    # A recognized field repeated with one canonical and one malformed
    # occurrence must be "ambiguous", not silently resolved to the first
    # (canonical) value. Before this fix, the malformed occurrence was
    # invisible to duplicate detection because it never matched the strict
    # labeled-field pattern.
    references = parse_project_references(
        "## Project references\n"
        "- Jira project: `PROJ`\n"
        "- Jira project: OTHER\n"
    )
    assert references.status == "ambiguous"
    assert "Jira project" in references.detail
    assert references.values == {}

    # Two canonical occurrences of the same field remain ambiguous too.
    both_canonical = parse_project_references(
        "## Project references\n"
        "- Jira project: `PROJ`\n"
        "- Jira project: `OTHER`\n"
    )
    assert both_canonical.status == "ambiguous"


def test_project_references_reject_syntax_errors_with_urllib_parsing() -> None:
    # A Jira site that merely lacks "://" and "/" and "@" is not
    # automatically a valid host: whitespace, control characters, and a
    # malformed port must also be rejected using real URL/host parsing
    # rather than substring checks.
    whitespace_site = parse_project_references(
        "## Project references\n- Jira site: `not a host`\n"
    )
    assert whitespace_site.status == "invalid"

    bad_port_site = parse_project_references(
        "## Project references\n- Jira site: `example.atlassian.net:notaport`\n"
    )
    assert bad_port_site.status == "invalid"

    # A self-hosted Jira host with an explicit port is a valid bare host.
    self_hosted = parse_project_references(
        "## Project references\n- Jira site: `jira.internal.example.com:8443`\n"
    )
    assert self_hosted.status == "ok"
    assert self_hosted.values["Jira site"] == "jira.internal.example.com:8443"

    # A board/Figma URL with no scheme, the wrong scheme, no host, or
    # embedded credentials is invalid syntax, not just "missing ://".
    no_scheme_board = parse_project_references(
        "## Project references\n- Jira board: `https://`\n"
    )
    assert no_scheme_board.status == "invalid"

    wrong_scheme_figma = parse_project_references(
        "## Project references\n- Figma reference: `file:///etc/passwd`\n"
    )
    assert wrong_scheme_figma.status == "invalid"

    credentials_in_board = parse_project_references(
        "## Project references\n"
        "- Jira board: `https://user:pass@example.atlassian.net/boards/1`\n"
    )
    assert credentials_in_board.status == "invalid"
    assert "credentials" in credentials_in_board.detail

    # A syntactically valid absolute https URL with a normal path is still
    # accepted; this checks syntax, not reachability or permission.
    valid_board = parse_project_references(
        "## Project references\n"
        "- Jira board: `https://example.atlassian.net/jira/software/projects/PROJ/boards/1`\n"
    )
    assert valid_board.status == "ok"


def test_project_references_reject_malformed_hostnames() -> None:
    # urlsplit accepts an empty interior DNS label and a backslash in the
    # authority. Both must be invalid. This is syntax only.
    empty_label = parse_project_references(
        "## Project references\n- Jira site: `jira..example.com`\n"
    )
    assert empty_label.status == "invalid"
    assert empty_label.values == {}

    backslash_board = parse_project_references(
        "## Project references\n"
        "- Jira board: `https://jira.example.com\\other/boards/1`\n"
    )
    assert backslash_board.status == "invalid"
    assert backslash_board.values == {}

    empty_userinfo = parse_project_references(
        "## Project references\n"
        "- Jira board: `https://@jira.example.com/boards/1`\n"
    )
    assert empty_userinfo.status == "invalid"
    assert "credentials" in empty_userinfo.detail
    assert empty_userinfo.values == {}

    leading_dot = parse_project_references(
        "## Project references\n- Jira site: `.jira.example.com`\n"
    )
    assert leading_dot.status == "invalid"

    # A trailing DNS dot, a single-label internal host, IPv4, an explicit
    # port, a bracketed IPv6 URL, and a Figma frame link stay valid.
    trailing_dot = parse_project_references(
        "## Project references\n- Jira site: `jira.example.com.`\n"
    )
    assert trailing_dot.status == "ok"
    assert trailing_dot.values["Jira site"] == "jira.example.com."

    single_label = parse_project_references(
        "## Project references\n- Jira site: `jira`\n"
    )
    assert single_label.status == "ok"

    ipv4_site = parse_project_references(
        "## Project references\n- Jira site: `192.168.1.10`\n"
    )
    assert ipv4_site.status == "ok"

    ipv4_board = parse_project_references(
        "## Project references\n"
        "- Jira board: `https://192.168.1.10:8443/boards/1?selectedIssue=PROJ-1#frag`\n"
    )
    assert ipv4_board.status == "ok"

    ipv6_board = parse_project_references(
        "## Project references\n"
        "- Jira board: `https://[2001:db8::1]:8443/boards/1`\n"
    )
    assert ipv6_board.status == "ok"

    figma_frame = parse_project_references(
        "## Project references\n"
        "- Figma reference: `https://www.figma.com/design/ABC/file?node-id=1-2`\n"
        "- Figma role: `approved-design`\n"
    )
    assert figma_frame.status == "ok"
    assert "node-id=1-2" in figma_frame.values["Figma reference"]


def test_project_references_reject_explicitly_empty_recognized_fields() -> None:
    # A recognized field that is written with an empty or whitespace-only
    # value is invalid. Omitting the line is how an optional field stays
    # absent. Invalid results expose no reusable values.
    empty = parse_project_references("## Project references\n- Jira project: ``\n")
    assert empty.status == "invalid"
    assert empty.values == {}
    assert "Jira project" in empty.detail

    whitespace = parse_project_references(
        "## Project references\n- Jira site: `   `\n"
    )
    assert whitespace.status == "invalid"
    assert whitespace.values == {}

    # An absent optional field is still valid.
    absent = parse_project_references(
        "## Project references\n- Jira project: `PROJ`\n"
    )
    assert absent.status == "ok"
    assert absent.values == {"Jira project": "PROJ"}

    # A duplicate is ambiguous even when one of the values is empty. Do not
    # pick the non-empty one.
    duplicate = parse_project_references(
        "## Project references\n- Jira project: ``\n- Jira project: `PROJ`\n"
    )
    assert duplicate.status == "ambiguous"
    assert duplicate.values == {}


def test_project_references_empty_live_section_is_reported_as_missing() -> None:
    # A live `## Project references` heading with no recognized fields —
    # empty, or holding only unrelated notes — must not be reported as
    # "ok". project-onboarding.md says a confirmed section is never written
    # empty, so this state means nothing was actually confirmed; treating
    # it as "ok" would make `sync-context`/`scaffold-project` skip
    # onboarding forever, since both only reopen it on "missing",
    # "ambiguous", or "invalid".
    heading_only = parse_project_references("## Project references\n")
    assert heading_only.status == "missing"
    assert heading_only.values == {}

    notes_only = parse_project_references(
        "## Project references\n- Owner: Platform team\n"
    )
    assert notes_only.status == "missing"
    assert notes_only.values == {}

    # One recognized, valid field is enough to make the section "ok", even
    # alongside the same kind of unrelated note.
    one_field = parse_project_references(
        "## Project references\n- Owner: Platform team\n- Jira project: `PROJ`\n"
    )
    assert one_field.status == "ok"
    assert one_field.values == {"Jira project": "PROJ"}


def test_project_references_preserve_fences_and_unrelated_lines() -> None:
    # A fenced code example showing the section's own syntax must not be
    # read as a second live heading, and an unrelated human-authored bullet
    # in the same section must not be flagged.
    config = "\n".join(
        [
            "## Project references",
            "- Jira site: `example.atlassian.net`",
            "- Owner: Platform team",
            "",
            "```markdown",
            "## Project references",
            "- Jira project: `OTHER`",
            "```",
        ]
    )
    references = parse_project_references(config)
    assert references.status == "ok"
    assert "Jira project" not in references.values
    assert references.values["Jira site"] == "example.atlassian.net"


def test_project_references_invalid_status_never_populates_values() -> None:
    # A rejected `## Project references` section must report an empty
    # `values`, the same as "missing" and "ambiguous", so a later refresh
    # can never treat a bad host or an unknown role as confirmed
    # configuration. This also closes the adjacent Bugbot finding on
    # SKILL.md's `invalid`-status reopen-onboarding behavior.
    bad_site = parse_project_references(
        "## Project references\n- Jira site: `https://example.atlassian.net/wiki`\n"
    )
    assert bad_site.status == "invalid"
    assert bad_site.values == {}

    unknown_role = parse_project_references(
        "## Project references\n"
        "- Figma reference: `https://www.figma.com/design/EXAMPLE/file`\n"
        "- Figma role: `inspiration-maybe`\n"
    )
    assert unknown_role.status == "invalid"
    assert unknown_role.values == {}


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
        test_git_aware_fingerprint_excludes_ignored_untracked_file,
        test_git_aware_fingerprint_keeps_tracked_file_matching_a_later_ignore_pattern,
        test_git_aware_fingerprint_respects_nested_gitignore_for_a_module_scope,
        test_git_aware_fingerprint_detects_additions_deletions_and_renames,
        test_git_aware_fingerprint_excludes_generated_context,
        test_git_discovery_failure_raises_instead_of_falling_back_to_the_walk,
        test_git_fingerprint_skips_a_tracked_file_behind_an_external_directory_symlink,
        test_git_fingerprint_skips_a_directory_symlink_that_points_inside_the_repository,
        test_git_fingerprint_accepts_a_symlink_scope_root,
        test_broken_git_metadata_is_not_fingerprinted_as_an_unversioned_tree,
        test_valid_git_worktree_fingerprint_includes_tracked_files,
        test_unversioned_tree_still_uses_the_filesystem_walk,
        test_fingerprint_reflects_working_tree_not_the_staged_git_index,
        test_corrupt_index_makes_staged_comparison_unavailable,
        test_identity_normalization_and_persistence,
        test_document_budget_flags_documents_over_the_limit,
        test_resolve_markdown_links_across_multiple_authorized_repositories,
        test_resolve_markdown_links_rejects_symlink_escape_from_authorized_root,
        test_resolve_source_path_distinguishes_repository_and_path_problems,
        test_find_stale_source_paths_flags_every_non_ok_reason,
        test_duplicate_module_id_across_two_repositories_is_allowed,
        test_duplicate_repository_and_module_id_pair_is_flagged,
        test_duplicate_module_id_without_repository_ids_uses_module_id_only,
        test_find_duplicate_identities_rejects_misaligned_lists,
        test_find_duplicate_context_targets_detects_shared_output_with_different_labels,
        test_find_duplicate_values_generic_helper,
        test_extract_table_column_reads_populated_table,
        test_extract_table_column_missing_table_does_not_leak_into_next_section,
        test_extract_table_column_valid_empty_table_is_distinguished_from_malformed,
        test_extract_table_column_missing_section_reported_distinctly,
        test_extract_table_column_reports_malformed_separator_row,
        test_extract_table_column_reports_malformed_row_cell_count,
        test_extract_table_column_reports_missing_column,
        test_extract_table_column_ignores_fenced_example_table,
        test_parse_recorded_fingerprint_module_document_shape,
        test_parse_recorded_fingerprint_repository_index_shape,
        test_parse_recorded_fingerprint_ignores_notes_and_examples_outside_metadata,
        test_parse_recorded_fingerprint_reports_missing_metadata,
        test_parse_recorded_fingerprint_reports_malformed_field,
        test_parse_recorded_fingerprint_reports_ambiguous_duplicate_fields,
        test_validate_generated_context_passes_for_a_well_formed_document_set,
        test_candidate_content_validates_first_time_generation_without_canonical_docs,
        test_classify_markdown_target_resolves_a_candidate_to_candidate_link,
        test_candidate_content_fails_a_malformed_proposal_even_when_disk_copy_is_valid,
        test_candidate_content_checks_the_proposal_instead_of_a_stale_on_disk_copy,
        test_candidate_content_mapping_does_not_grant_an_authorized_root_escape,
        test_candidate_content_never_writes_to_the_real_index_file,
        test_validate_generated_context_without_candidates_still_works_after_a_candidate_run,
        test_index_candidate_outside_authorized_roots_fails,
        test_index_candidate_whose_destination_is_a_directory_fails,
        test_module_candidate_whose_destination_is_a_directory_fails,
        test_candidate_fails_when_a_parent_path_is_a_file,
        test_candidate_symlink_escape_fails_without_writing,
        test_authorized_coordinator_candidate_passes_without_creating_files,
        test_conflicting_candidate_paths_are_rejected,
        test_cli_rejects_a_candidate_outside_authorized_roots,
        test_git_discovery_failure_is_unresolved_validation_not_a_crash,
        test_validate_generated_context_fails_on_missing_markers_and_headings,
        test_validate_generated_context_fails_when_over_budget,
        test_validate_generated_context_reports_unresolved_for_missing_index,
        test_validate_generated_context_multi_repo_requires_repository_column,
        test_validate_generated_context_true_multi_repo_engagement_passes,
        test_cli_validate_exit_codes,
        test_extract_table_column_ignores_fenced_heading_before_real_section,
        test_extract_table_column_ignores_tilde_fenced_heading,
        test_structure_heading_outside_generated_block_fails,
        test_parse_recorded_fingerprint_rejects_duplicate_equal_values,
        test_parse_recorded_fingerprint_rejects_multiple_or_malformed_blocks,
        test_parse_recorded_fingerprint_ignores_fingerprinted_prose,
        test_omitted_index_repository_id_still_detects_stale_context,
        test_extra_authorized_root_does_not_skip_single_repo_checks,
        test_conflicting_supplied_repository_id_fails,
        test_missing_index_identity_is_unresolved_not_success,
        test_module_metadata_must_match_the_index_row,
        test_missing_evidence_file_fails_without_treating_symbols_as_paths,
        test_directory_context_target_is_a_structured_failure,
        test_failed_check_takes_exit_precedence_over_unresolved,
        test_unavailable_repository_is_unresolved_not_failed,
        test_artifact_home_fallback_document_is_not_required_inside_source,
        test_https_context_target_fails_without_skipping_the_module,
        test_anchor_context_target_fails,
        test_local_context_target_may_include_a_fragment,
        test_external_evidence_link_stays_not_applicable,
        test_duplicate_module_identity_sections_with_conflicting_values_fail,
        test_duplicate_module_identity_sections_with_identical_values_fail,
        test_duplicate_index_scope_sections_fail,
        test_duplicate_index_modules_sections_fail,
        test_backtick_fenced_canonical_headings_are_not_duplicate_sections,
        test_tilde_fenced_canonical_headings_are_not_duplicate_sections,
        test_canonical_heading_outside_generated_block_is_not_a_duplicate,
        test_valid_single_and_multi_repository_documents_still_pass,
        test_classify_fingerprint_change_distinguishes_unavailable_unchanged_changed,
        test_classify_fingerprint_change_drives_a_real_no_op_decision,
        test_is_declared_submodule_distinguishes_real_submodule_from_nested_checkout,
        test_bugbot_reprompt_allowed_respects_recorded_decisions,
        test_diff_module_sources_reports_added_and_removed_paths,
        test_scope_verification_status_is_partial_when_any_scope_is_unavailable,
        test_adopted_coordinator_destination_ignores_source_writability,
        test_migration_destination_preserves_placement_until_approved,
        test_repository_is_named_coordinator_ignores_placement_mode,
        test_classify_repository_role_never_decides_from_name_alone,
        test_relocate_workspace_folder_path_recomputes_relative_paths,
        test_checkout_deletion_readiness_blocks_until_every_precondition_passes,
        test_checkout_deletion_readiness_rejects_unsafe_targets,
        test_retirement_decision_pending_mirrors_bugbot_reprompt_semantics,
        test_migration_outcome_reports_partial_without_implying_atomicity,
        test_stale_proposal_does_not_match_a_newer_destination,
        test_unrelated_rules_are_not_part_of_the_approved_write_set,
        test_context_sync_outcome_unchanged_with_first_time_missing_bugbot_config,
        test_context_sync_outcome_unchanged_with_previously_declined_bugbot_proposal,
        test_context_sync_outcome_unchanged_with_pending_legacy_cleanup,
        test_context_sync_outcome_full_no_op_when_nothing_is_actionable,
        test_duplicate_managed_configuration_heading_is_ambiguous,
        test_context_identities_stop_at_project_references,
        test_missing_project_references_do_not_invalidate_identities,
        test_duplicate_project_reference_sections_are_ambiguous,
        test_context_sync_outcome_is_reachable_for_a_configuration_only_change,
        test_project_references_reject_a_site_url_and_an_unknown_figma_role,
        test_project_references_keep_a_board_without_treating_it_as_the_project,
        test_project_references_flag_a_recognized_field_without_backticks,
        test_project_references_detect_a_mixed_quoted_and_unquoted_duplicate,
        test_project_references_reject_syntax_errors_with_urllib_parsing,
        test_project_references_reject_malformed_hostnames,
        test_project_references_reject_explicitly_empty_recognized_fields,
        test_project_references_empty_live_section_is_reported_as_missing,
        test_project_references_preserve_fences_and_unrelated_lines,
        test_project_references_invalid_status_never_populates_values,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
