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
    _canonical_remote_or_problem,
    bugbot_reprompt_allowed,
    check_document_budget,
    checkout_deletion_readiness,
    classify_fingerprint_change,
    classify_markdown_target,
    classify_repository_role,
    classify_repository_scope,
    cli_plan_validate,
    decision_reprompt_allowed,
    external_jira_dependencies,
    diff_module_sources,
    find_live_section,
    cli_validate,
    content_fingerprint,
    classify_legacy_ci_workflow,
    detect_canonical_remote_collision,
    detect_legacy_aidlc_installation,
    detect_repository_id_collision,
    extract_table_column,
    find_duplicate_context_targets,
    find_duplicate_identities,
    find_duplicate_values,
    find_stale_source_paths,
    GitDiscoveryError,
    git_output,
    historical_content_blocks_checkout_deletion,
    is_declared_submodule,
    legacy_architecture_prompt_required,
    legacy_baseline_comparison,
    legacy_inventory_fingerprint,
    legacy_inventory_needs_approval,
    legacy_standard_file_treatment,
    legacy_supporting_evidence,
    match_related_repositories,
    migration_destination_placement,
    migration_outcome,
    module_context_destination,
    repository_is_named_coordinator,
    normalize_remote,
    parse_project_references,
    parse_related_repositories,
    plan_validate_proposal,
    proposal_is_current,
    relocate_workspace_folder_path,
    resolve_legacy_provenance,
    resolve_placement,
    resolve_related_context_index,
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
    jira_mutation_authorized,
    plan_outcome,
    topological_plan_order,
    validate_dependency_graph,
    validate_parent_reference,
    validate_plan_item_id,
    validate_work_item_type,
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


def test_canonical_remote_collision_detects_reverse_direction() -> None:
    # Reproduced defect: the same canonical remote persisted under two
    # different repository IDs is a genuine identity collision that
    # `detect_repository_id_collision` alone cannot see, because its own
    # check only ever looks up `occupied.get(repo_id)` -- a different key
    # entirely from the one that collides here.
    assert (
        detect_canonical_remote_collision(
            "api-new", "github.com/example/api", {"api-old": "github.com/example/api"}
        )
        == "api-old"
    )
    # `detect_repository_id_collision` itself must not be changed to also
    # report this direction -- its own return contract (a canonical
    # identity string, or None) stays exactly as it always has been.
    assert (
        detect_repository_id_collision(
            "api-new", "github.com/example/api", {"api-old": "github.com/example/api"}
        )
        is None
    )


def test_canonical_remote_collision_is_none_for_valid_shared_identity() -> None:
    # Two checkouts or worktrees of the same repository, both already
    # persisted under the same repository ID and the same canonical
    # remote, are not a collision -- this is the ordinary case, not an
    # edge case to special-case away.
    occupied = {"payments-api": "github.com/example/payments-api"}
    assert (
        detect_canonical_remote_collision(
            "payments-api", "github.com/example/payments-api", occupied
        )
        is None
    )
    # No entry at all sharing this canonical identity is also not a
    # collision.
    assert detect_canonical_remote_collision("brand-new", "github.com/example/new", {}) is None


def test_document_budget_flags_documents_over_the_limit() -> None:
    with tempfile.TemporaryDirectory() as temp:
        short = Path(temp) / "short.md"
        short.write_text("\n".join(f"line {i}" for i in range(50)) + "\n")
        assert check_document_budget(short)

        long = Path(temp) / "long.md"
        long.write_text("\n".join(f"line {i}" for i in range(151)) + "\n")
        assert not check_document_budget(long)
        # This helper is the repository-index gate. A 300-line cap is not
        # a module validity check; callers that want a module line count
        # use document_metrics instead.
        assert check_document_budget(long, max_lines=300)


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


def _module_envelope_after_identity() -> list[str]:
    return [
        "## Coverage",
        "",
        "| Dimension | State | Evidence |",
        "| --- | --- | --- |",
        "",
        "## Evidence and existing docs",
        "",
        "No local paths to resolve.",
        "",
        "## Unknowns",
        "",
        "- None recorded.",
        "",
    ]


def _valid_module_generated_text(
    repository_id: str, module_id: str, source: str, fingerprint: str
) -> str:
    return "\n".join(
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
            *_module_envelope_after_identity(),
            "<!-- AI-DLC:generated:end -->",
            "",
        ]
    )


def _write_valid_module(module_dir: Path, repository_id: str, module_id: str, source: str) -> str:
    fingerprint, _ = content_fingerprint(module_dir)
    (module_dir / "AIDLC_CONTEXT.md").write_text(
        _valid_module_generated_text(repository_id, module_id, source, fingerprint)
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
        module_text = _valid_module_generated_text(
            "web", "storefront", "apps/storefront", module_fingerprint
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
        proposed_text = _valid_module_generated_text(
            "web", "storefront", "apps/storefront", module_fingerprint
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
        module_text = _valid_module_generated_text(
            "web", "storefront", "apps/storefront", module_fingerprint
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


def test_validate_generated_context_module_budget_is_not_a_validation_result() -> None:
    """A module document's line count is never a ValidationCheck.

    The repository index stays a hard-gated short index (covered by
    `test_validate_generated_context_fails_when_over_budget`). A long
    module document must not produce `modules:budget:<label>` as passed
    or failed; callers that want the number use `document_metrics`.
    """
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        (web / "apps" / "storefront").mkdir(parents=True)
        (web / "apps" / "storefront" / "index.ts").write_text("export const x = 1;\n")
        fingerprint = _write_valid_module(
            web / "apps" / "storefront", "web", "storefront", "apps/storefront"
        )
        module_path = web / "apps" / "storefront" / "AIDLC_CONTEXT.md"
        padding = "\n".join(f"- Verified detail line {i}" for i in range(500))
        module_path.write_text(
            module_path.read_text().replace(
                "<!-- AI-DLC:generated:end -->",
                f"\n## Extra detail\n\n{padding}\n\n<!-- AI-DLC:generated:end -->",
            )
        )
        (web / "aidlc-docs").mkdir()
        index = web / "aidlc-docs" / "repository-context.md"
        _write_valid_index(index, web)

        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        assert not any(check.name.startswith("modules:budget:") for check in checks)
        identity = next(
            c for c in checks if c.name == "modules:identity:../apps/storefront/AIDLC_CONTEXT.md"
        )
        assert identity.status == "passed", "padding must not break identity or freshness"
        assert fingerprint  # the padded context document never enters its own fingerprint


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
                "No local paths to resolve.",
                "- `OrderPlacedEvent`\n- `apps/storefront/deleted.ts`",
            )
        )
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        evidence = [check for check in checks if "evidence" in check.name]
        assert any(check.status == "failed" and "deleted.ts" in check.name for check in evidence)
        assert any(
            check.status == "failed"
            and "deleted.ts" in check.name
            and "referenced evidence path does not exist" in check.detail
            for check in evidence
        )
        assert not any("OrderPlacedEvent" in check.name for check in checks)
        assert cli_validate([str(index), "--root", f"web={web}", "--index-repository-id", "web"]) == 1


def test_empty_evidence_catalog_is_not_applicable_not_passed() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        evidence = next(
            check
            for check in checks
            if check.name == "modules:evidence:../apps/storefront/AIDLC_CONTEXT.md"
        )
        assert evidence.status == "not_applicable"
        assert "no local evidence paths to resolve" in evidence.detail
        assert evidence.status != "passed"


def test_valid_evidence_path_resolves_with_mechanical_wording() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        module_doc.write_text(
            module_doc.read_text().replace(
                "No local paths to resolve.",
                "- `apps/storefront/index.ts`",
            )
        )
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        evidence = next(
            check for check in checks if check.name.endswith("apps/storefront/index.ts")
        )
        assert evidence.status == "passed"
        assert evidence.detail == "evidence references resolved"


def test_evidence_path_outside_authorized_root_fails() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        module_doc.write_text(
            module_doc.read_text().replace(
                "No local paths to resolve.",
                "- `../outside/secret.py`",
            )
        )
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        evidence = next(check for check in checks if "outside/secret.py" in check.name)
        assert evidence.status == "failed"
        assert "evidence path is outside authorized root" in evidence.detail


def test_empty_modules_table_is_valid_index_only() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web = Path(temp) / "web"
        web.mkdir()
        (web / "README.md").write_text("# docs only\n")
        (web / "aidlc-docs").mkdir()
        index = web / "aidlc-docs" / "repository-context.md"
        fingerprint, _ = content_fingerprint(web)
        index.write_text(
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
                    f"- Fingerprint: `{fingerprint}`",
                    "",
                    "## Modules",
                    "",
                    "| Module | Source | Context | Status |",
                    "| --- | --- | --- | --- |",
                    "",
                    "<!-- AI-DLC:generated:end -->",
                    "",
                ]
            )
        )
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        assert all(check.status in ("passed", "not_applicable") for check in checks)
        assert not any(check.name.startswith("modules:link:") for check in checks)


def test_empty_context_cell_fails_as_missing_local_context() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        index.write_text(
            index.read_text().replace(
                "| `storefront` | `apps/storefront` | [x](../apps/storefront/AIDLC_CONTEXT.md) | current |",
                "| `storefront` | `apps/storefront` |  | current |",
            )
        )
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        empty = next(check for check in checks if check.name.startswith("modules:link:"))
        assert empty.status == "failed"
        assert "module row requires a local context file" in empty.detail
        assert cli_validate([str(index), "--root", f"web={web}", "--index-repository-id", "web"]) == 1


def test_module_rows_without_context_column_fail() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        index.write_text(
            index.read_text()
            .replace("| Module | Source | Context | Status |", "| Module | Source | Status |")
            .replace("| --- | --- | --- | --- |", "| --- | --- | --- |")
            .replace(
                "| `storefront` | `apps/storefront` | [x](../apps/storefront/AIDLC_CONTEXT.md) | current |",
                "| `storefront` | `apps/storefront` | current |",
            )
        )
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        column = next(check for check in checks if check.name == "modules:context-column")
        assert column.status == "failed"
        assert "every module row requires a local context file" in column.detail


def test_module_envelope_passes_with_required_headings() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, _module_doc = _single_repo_fixture(temp)
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        structure = next(
            check
            for check in checks
            if check.name == "modules:structure:../apps/storefront/AIDLC_CONTEXT.md"
        )
        assert structure.status == "passed"
        assert all(check.status in ("passed", "not_applicable") for check in checks)


def test_module_envelope_fails_when_identity_is_missing() -> None:
    _assert_missing_module_heading_fails("## Identity and scope")


def test_module_envelope_fails_when_coverage_is_missing() -> None:
    _assert_missing_module_heading_fails("## Coverage")


def test_module_envelope_fails_when_evidence_is_missing() -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        _remove_generated_heading(module_doc, "## Evidence and existing docs")
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        label = "../apps/storefront/AIDLC_CONTEXT.md"
        structure = next(check for check in checks if check.name == f"modules:structure:{label}")
        evidence = next(check for check in checks if check.name == f"modules:evidence:{label}")
        assert structure.status == "failed"
        assert "## Evidence and existing docs" in structure.detail
        assert evidence.status == "failed"
        assert "missing required heading" in evidence.detail
        assert cli_validate([str(index), "--root", f"web={web}", "--index-repository-id", "web"]) == 1


def test_module_envelope_fails_when_unknowns_is_missing() -> None:
    _assert_missing_module_heading_fails("## Unknowns")


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
            "The colocated file was not writable. Source root: `apps/storefront`.\n\n"
            + _valid_module_generated_text("web", "storefront", "apps/storefront", fingerprint)
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


def _remove_generated_heading(path: Path, heading: str) -> None:
    lines = path.read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == heading)
    end = start + 1
    while end < len(lines):
        if lines[end].startswith("## ") or lines[end].strip() == "<!-- AI-DLC:generated:end -->":
            break
        end += 1
    path.write_text("\n".join(lines[:start] + lines[end:]) + "\n")


def _assert_missing_module_heading_fails(heading: str) -> None:
    with tempfile.TemporaryDirectory() as temp:
        web, index, module_doc = _single_repo_fixture(temp)
        _remove_generated_heading(module_doc, heading)
        checks = validate_generated_context(index, {"web": web}, index_repository_id="web")
        structure = next(
            check
            for check in checks
            if check.name == "modules:structure:../apps/storefront/AIDLC_CONTEXT.md"
        )
        assert structure.status == "failed"
        assert heading in structure.detail
        assert cli_validate([str(index), "--root", f"web={web}", "--index-repository-id", "web"]) == 1


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
        module_doc.write_text(
            module_doc.read_text().replace(
                "No local paths to resolve.",
                "- [guide](https://example.com/guide)",
            )
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
            has_unrecovered_stash=False,
            has_dependent_worktrees=False,
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
        has_unrecovered_stash=False,
        has_dependent_worktrees=False,
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
        has_unrecovered_stash=False,
        has_dependent_worktrees=False,
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
        has_unrecovered_stash=False,
        has_dependent_worktrees=False,
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


def test_checkout_deletion_readiness_blocks_on_unrecovered_stash() -> None:
    # Scenario: "Clean current worktree with an unrecovered stash." A clean
    # working tree (has_uncommitted_changes=False) must not by itself prove
    # readiness when a stash still holds unrecovered material.
    ready = dict(
        explicit_target="engagement/legacy-aidlc",
        approved_target="engagement/legacy-aidlc",
        migration_confirmed=True,
        has_uncommitted_changes=False,
        has_unestablished_recovery=False,
        retention_established=True,
        repository_role="product-coordination-repository",
        has_active_references=False,
        has_unrecovered_stash=False,
        has_dependent_worktrees=False,
    )
    assert checkout_deletion_readiness(**ready) == ()

    stashed = checkout_deletion_readiness(**{**ready, "has_unrecovered_stash": True})
    assert any("stash" in reason for reason in stashed)
    # A clean tree plus an unrecovered stash is still exactly one blocking
    # reason; the stash check is independent of the dirty-tree check.
    assert len(stashed) == 1


def test_checkout_deletion_readiness_blocks_on_dependent_worktree() -> None:
    # Scenario: "Main checkout whose removal would break a linked worktree."
    # A pushed remote and clean main worktree (every other flag "ready")
    # must not be enough when a linked worktree still depends on this
    # checkout's Git common directory.
    ready = dict(
        explicit_target="engagement/legacy-aidlc",
        approved_target="engagement/legacy-aidlc",
        migration_confirmed=True,
        has_uncommitted_changes=False,
        has_unestablished_recovery=False,
        retention_established=True,
        repository_role="product-coordination-repository",
        has_active_references=False,
        has_unrecovered_stash=False,
        has_dependent_worktrees=False,
    )
    assert checkout_deletion_readiness(**ready) == ()

    dependent = checkout_deletion_readiness(**{**ready, "has_dependent_worktrees": True})
    assert any("worktree" in reason for reason in dependent)
    assert len(dependent) == 1


def test_checkout_deletion_readiness_failed_inspection_remains_blocked() -> None:
    # Scenario: "Failed inspection remains blocked." When stash or worktree
    # inspection could not be completed, the caller reports that as the
    # blocking value (True), per this function's own documented contract --
    # an inspection failure must never silently resolve to an empty result.
    ready = dict(
        explicit_target="engagement/legacy-aidlc",
        approved_target="engagement/legacy-aidlc",
        migration_confirmed=True,
        has_uncommitted_changes=False,
        has_unestablished_recovery=False,
        retention_established=True,
        repository_role="product-coordination-repository",
        has_active_references=False,
        has_unrecovered_stash=False,
        has_dependent_worktrees=False,
    )
    stash_inspection_failed = checkout_deletion_readiness(
        **{**ready, "has_unrecovered_stash": True}
    )
    assert stash_inspection_failed != ()

    worktree_inspection_failed = checkout_deletion_readiness(
        **{**ready, "has_dependent_worktrees": True}
    )
    assert worktree_inspection_failed != ()


def test_checkout_deletion_readiness_fully_verified_checkout_still_passes() -> None:
    # Scenario: "A fully verified eligible checkout still passes the
    # readiness contract." Every precondition, including the two added
    # here, genuinely inspected and clear: deletion remains ready.
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
            has_unrecovered_stash=False,
            has_dependent_worktrees=False,
        )
        == ()
    )


def test_real_git_stash_and_worktree_inspection_feeds_the_readiness_booleans() -> None:
    # This test exercises actual `git stash list` / `git worktree list`
    # output on a disposable repository, then feeds that real result into
    # `checkout_deletion_readiness`. It is distinct from the pure-function
    # tests above: those prove the readiness combination logic given
    # already-supplied booleans; this one proves `git_output` actually
    # surfaces a stash and a dependent worktree the way the caller
    # instructions in legacy-migration.md assume. Neither proves the other.
    with tempfile.TemporaryDirectory() as temp:
        main = Path(temp) / "coordinator"
        main.mkdir()
        init_repo(main)
        (main / "README.md").write_text("placeholder\n")
        run(main, "git", "add", ".")
        run(main, "git", "commit", "-qm", "feat: initial")

        # No stash, no worktree yet: a real inspection reports both clear.
        assert git_output(main, "stash", "list") == ""
        worktrees_before = git_output(main, "worktree", "list", "--porcelain") or ""
        assert worktrees_before.count("worktree ") == 1
        assert (
            checkout_deletion_readiness(
                explicit_target=str(main),
                approved_target=str(main),
                migration_confirmed=True,
                has_uncommitted_changes=False,
                has_unestablished_recovery=False,
                retention_established=True,
                repository_role="product-coordination-repository",
                has_active_references=False,
                has_unrecovered_stash=bool(git_output(main, "stash", "list")),
                has_dependent_worktrees=(
                    (git_output(main, "worktree", "list", "--porcelain") or "").count(
                        "worktree "
                    )
                    > 1
                ),
            )
            == ()
        )

        # Create real uncommitted work, stash it: `git stash list` is now
        # non-empty, independent of a clean `git status`.
        (main / "README.md").write_text("changed\n")
        run(main, "git", "stash", "push", "-qm", "wip")
        assert git_output(main, "stash", "list") != ""
        blocked_by_stash = checkout_deletion_readiness(
            explicit_target=str(main),
            approved_target=str(main),
            migration_confirmed=True,
            has_uncommitted_changes=False,
            has_unestablished_recovery=False,
            retention_established=True,
            repository_role="product-coordination-repository",
            has_active_references=False,
            has_unrecovered_stash=bool(git_output(main, "stash", "list")),
            has_dependent_worktrees=False,
        )
        assert any("stash" in reason for reason in blocked_by_stash)
        run(main, "git", "stash", "drop", "-q")

        # Add a real linked worktree: `git worktree list` now reports two
        # entries for the same common Git directory.
        linked = Path(temp) / "linked-worktree"
        run(main, "git", "worktree", "add", "-q", str(linked), "-b", "linked-branch")
        worktrees_after = git_output(main, "worktree", "list", "--porcelain") or ""
        assert worktrees_after.count("worktree ") == 2
        blocked_by_worktree = checkout_deletion_readiness(
            explicit_target=str(main),
            approved_target=str(main),
            migration_confirmed=True,
            has_uncommitted_changes=False,
            has_unestablished_recovery=False,
            retention_established=True,
            repository_role="product-coordination-repository",
            has_active_references=False,
            has_unrecovered_stash=False,
            has_dependent_worktrees=worktrees_after.count("worktree ") > 1,
        )
        assert any("worktree" in reason for reason in blocked_by_worktree)


def _legacy_detection_from_checkout(root: Path) -> str:
    project_type = root / ".ai-dlc-project-type"
    text = project_type.read_text(encoding="utf-8") if project_type.is_file() else None
    return detect_legacy_aidlc_installation(
        text,
        (root / "prompts/discovery/prompt_01_codebase_discovery.md").is_file(),
        (root / ".cursor/rules/aidlc-context.mdc").is_file(),
    )


def test_legacy_aidlc_fixture_selects_distributed_proposal_without_placement() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "prompts/discovery").mkdir(parents=True)
        (root / ".cursor/rules").mkdir(parents=True)
        (root / ".ai-dlc-project-type").write_text("brownfield\n", encoding="utf-8")
        (root / "prompts/discovery/prompt_01_codebase_discovery.md").write_text(
            "# discovery\n", encoding="utf-8"
        )
        (root / ".cursor/rules/aidlc-context.mdc").write_text("# rule\n", encoding="utf-8")
        # Discovery output is corroboration, not a required marker.
        (root / "aidlc-docs/discovery/output/api").mkdir(parents=True)
        detection = _legacy_detection_from_checkout(root)
        assert detection == "full"
        provenance = resolve_legacy_provenance(detection, inspection="ruled-out")
        assert provenance == "confirmed"
        # Persisted Placement is not an argument. No recorded architecture
        # means the distributed proposal is still required.
        assert legacy_architecture_prompt_required(provenance, None, same_run=True) is True


def test_partial_legacy_fixture_stays_inspect_until_provenance_is_established() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / ".ai-dlc-project-type").write_text("brownfield\n", encoding="utf-8")
        detection = _legacy_detection_from_checkout(root)
        assert detection == "partial"
        assert resolve_legacy_provenance(detection) == "inspect"
        assert (
            legacy_architecture_prompt_required("inspect", None, same_run=False) is False
        )
        assert resolve_legacy_provenance(detection, inspection="confirmed") == "confirmed"
        assert resolve_legacy_provenance(detection, inspection="ruled-out") == "ruled-out"
        assert (
            resolve_legacy_provenance(detection, inspection="unavailable")
            == "inspection-unavailable"
        )
        assert (
            legacy_architecture_prompt_required(
                "inspection-unavailable", None, same_run=False
            )
            is False
        )


def test_legacy_detection_rejects_unrecognized_project_type_and_discovery_output_alone() -> None:
    assert detect_legacy_aidlc_installation("custom", False, False) == "absent"
    assert detect_legacy_aidlc_installation("  greenfield  ", True, True) == "full"
    assert detect_legacy_aidlc_installation(None, True, True) == "partial"
    assert detect_legacy_aidlc_installation("", False, False) == "absent"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "aidlc-docs/discovery/output/api").mkdir(parents=True)
        (root / "aidlc-docs/discovery/output/api/repo_tech_profile.md").write_text(
            "# profile\n", encoding="utf-8"
        )
        assert _legacy_detection_from_checkout(root) == "absent"
        assert (
            legacy_supporting_evidence(
                name_matches_legacy_pattern=True,
                operating_model_heading_only=True,
                discovery_path_only=True,
            )
            is False
        )
        assert resolve_legacy_provenance("absent") == "absent"
        assert (
            resolve_legacy_provenance(
                "absent",
                supporting_evidence=legacy_supporting_evidence(
                    inspected_framework_content=True
                ),
            )
            == "inspect"
        )
        assert (
            resolve_legacy_provenance(
                "absent",
                supporting_evidence=True,
                inspection="confirmed",
            )
            == "confirmed"
        )
        assert (
            resolve_legacy_provenance(
                "absent",
                supporting_evidence=True,
                inspection="unavailable",
            )
            == "inspection-unavailable"
        )
        try:
            resolve_legacy_provenance("absent", inspection="confirmed")
        except ValueError as error:
            assert "no marker or supporting evidence warranted" in str(error)
        else:
            raise AssertionError("unwarranted inspection confirmed provenance")


def test_legacy_architecture_and_inventory_are_separate_approvals() -> None:
    assert (
        legacy_architecture_prompt_required("confirmed", "migrate-distributed", True)
        is False
    )
    assert (
        legacy_architecture_prompt_required(
            "confirmed", "retain-active-coordinator", False
        )
        is False
    )
    assert legacy_architecture_prompt_required("confirmed", "defer", True) is False
    assert legacy_architecture_prompt_required("confirmed", "defer", False) is True
    try:
        legacy_architecture_prompt_required("confirmed", "retire-and-delete", False)
    except ValueError as error:
        assert "checkout disposition" in str(error)
    else:
        raise AssertionError("checkout disposition was accepted as architecture")
    try:
        retirement_decision_pending("retain-active-coordinator", same_run=True)
    except ValueError as error:
        assert "architectural decision" in str(error)
    else:
        raise AssertionError("architecture decision was accepted as checkout disposition")
    # An earlier checkout disposition cannot approve this inventory.
    try:
        legacy_inventory_needs_approval(
            "retire-and-retain-checkout", None, None, same_run=True
        )
    except ValueError as error:
        assert "does not approve" in str(error)
    else:
        raise AssertionError("checkout disposition approved an inventory")
    try:
        legacy_inventory_needs_approval(
            "migrate-distributted", None, None, same_run=True
        )
    except ValueError as error:
        assert "unknown legacy architecture" in str(error)
    else:
        raise AssertionError("unknown architecture was treated as not applicable")
    assert (
        legacy_inventory_needs_approval("retain-active-coordinator", None, None, True)
        == "not-applicable"
    )
    assert legacy_inventory_needs_approval("defer", None, None, False) == "not-applicable"
    assert legacy_inventory_needs_approval(None, None, None, False) == "not-applicable"


def _inventory_entry(**overrides: str) -> dict[str, str]:
    entry = {
        "repository_id": "payments-api",
        "relative_path": "aidlc-docs/repository-context.md",
        "action": "create",
        "before": "missing",
        "after": "a" * 64,
    }
    entry.update(overrides)
    return entry


def test_legacy_inventory_fingerprint_is_scoped_and_order_independent() -> None:
    first = _inventory_entry()
    second = _inventory_entry(
        repository_id="payments-app",
        relative_path="docs/adr/0001.md",
        action="preserve",
        before="b" * 64,
        after="b" * 64,
    )
    moved = _inventory_entry(
        relative_path="old.code-workspace",
        action="move",
        before="c" * 64,
        after="c" * 64,
        destination_repository_id="payments-app",
        destination_relative_path="old.code-workspace",
    )
    assert legacy_inventory_fingerprint([first, second]) == legacy_inventory_fingerprint(
        [second, first]
    )
    original = legacy_inventory_fingerprint([first])
    assert legacy_inventory_fingerprint(
        [_inventory_entry(after="d" * 64)]
    ) != original
    assert legacy_inventory_fingerprint(
        [_inventory_entry(action="update", before="a" * 64, after="a" * 64)]
    ) != original
    assert legacy_inventory_fingerprint([moved]) != original
    assert legacy_inventory_fingerprint(
        [_inventory_entry(repository_id="payments-app")]
    ) != original
    empty = legacy_inventory_fingerprint([])
    assert (
        legacy_inventory_needs_approval("migrate-distributed", empty, None, True)
        == "not-applicable"
    )
    current = legacy_inventory_fingerprint([first, moved])
    assert (
        legacy_inventory_needs_approval("migrate-distributed", current, None, True)
        == "needs-approval"
    )
    assert (
        legacy_inventory_needs_approval("migrate-distributed", current, current, True)
        == "approved"
    )
    assert proposal_is_current(current, current, "proposed text", "edited text") is False
    try:
        legacy_inventory_fingerprint(
            [_inventory_entry(relative_path="/Users/nahuel/secrets.env")]
        )
    except ValueError as error:
        assert "repository-relative" in str(error)
    else:
        raise AssertionError("absolute path was accepted into the inventory")
    try:
        legacy_inventory_fingerprint([first, dict(first)])
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate inventory entry was accepted")
    conflict = dict(first)
    conflict["after"] = "e" * 64
    try:
        legacy_inventory_fingerprint([first, conflict])
    except ValueError as error:
        assert "conflicting" in str(error)
    else:
        raise AssertionError("conflicting inventory entry was accepted")


def test_prior_run_approval_does_not_authorize_current_writes() -> None:
    fingerprint = legacy_inventory_fingerprint([_inventory_entry()])
    assert (
        legacy_inventory_needs_approval(
            "migrate-distributed", fingerprint, fingerprint, same_run=False
        )
        == "needs-approval"
    )
    assert (
        legacy_architecture_prompt_required("absent", None, same_run=False) is False
    )


def test_historical_content_blocks_only_deletion_of_the_only_copy() -> None:
    assert historical_content_blocks_checkout_deletion(True, True) is True
    assert historical_content_blocks_checkout_deletion(True, False) is False
    assert historical_content_blocks_checkout_deletion(False, True) is False


def test_legacy_ci_and_customized_files_are_not_classified_by_name() -> None:
    assert classify_legacy_ci_workflow(True, False) == "retire"
    assert classify_legacy_ci_workflow(True, True) == "review-control"
    assert classify_legacy_ci_workflow(False, True) == "review-control"
    assert classify_legacy_ci_workflow(False, False) == "inspect"
    assert legacy_baseline_comparison(True, True) == "unchanged"
    assert legacy_baseline_comparison(True, False) == "differs"
    assert legacy_baseline_comparison(False, None) == "unavailable"
    try:
        legacy_baseline_comparison(False, True)
    except ValueError as error:
        assert "missing legacy baseline" in str(error)
    else:
        raise AssertionError("a missing baseline was recorded as a match")
    assert legacy_standard_file_treatment("retire", "unchanged") == "retire"
    assert legacy_standard_file_treatment("retire", "differs") == "unresolved"
    assert legacy_standard_file_treatment("replace", "unavailable") == "unresolved"
    assert legacy_standard_file_treatment("preserve", "differs") == "preserve"
    assert (
        legacy_standard_file_treatment("reconcile", "differs", "reconcile") == "reconcile"
    )
    assert legacy_standard_file_treatment("retire", "unavailable", "retire") == "retire"
    assert (
        historical_content_blocks_checkout_deletion(False, True) is False
    )
    try:
        legacy_standard_file_treatment("delete", "unchanged")
    except ValueError as error:
        assert "unknown legacy file treatment" in str(error)
    else:
        raise AssertionError("unknown treatment was accepted")


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
    # "pending" is only ever a return value of this function, never a valid
    # input. A caller that passes it back in (confusing the output
    # vocabulary with the input vocabulary) gets a message that says so,
    # not a generic "unknown disposition" message.
    try:
        migration_outcome(distributed, "pending")
    except ValueError as error:
        message = str(error)
        assert "'pending' is a result" in message
        assert "deferred" in message and "unresolved" in message
    else:
        raise AssertionError("'pending' must never be accepted as an input disposition")
    # Distributed repositories plus an active adopted-coordinator choice is
    # contradictory: option B after a distributed migration is "completed".
    try:
        migration_outcome(distributed, "retained")
    except ValueError as error:
        assert "only valid when every" in str(error)
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


def test_related_repositories_missing_when_no_entries_declared() -> None:
    # No `## Context identities` heading at all, and a live heading with
    # only a `Repository:`/`Module:` block and no `Related repository`
    # entry, must both be "missing" -- not proof this repository has no
    # siblings, just that membership is unconfigured here.
    absent = parse_related_repositories("## Project references\n- Jira project: `PROJ`\n")
    assert absent.status == "missing"
    assert absent.entries == ()

    identity_only = parse_related_repositories(
        "## Context identities\n"
        "- Repository: `payments-api`\n"
        "  - Canonical remote: `github.com/example/payments-api`\n"
        "- Module: `payments-api`\n"
        "  - ID: `payments-api`\n"
        "  - Source: `services/payments`\n"
    )
    assert identity_only.status == "missing"
    assert identity_only.entries == ()


def test_related_repositories_parses_role_and_context_index() -> None:
    # The repository's own `Repository:`/`Module:` blocks sit alongside one
    # or more `Related repository:` entries in the same section; only the
    # `Related repository` blocks are read here, each keeping its own
    # `Role` and `Context index` without leaking into a neighboring entry.
    config = "\n".join(
        [
            "## Context identities",
            "- Repository: `payments-api`",
            "  - Canonical remote: `github.com/example/payments-api`",
            "  - Product: `checkout-platform`",
            "- Related repository: `github.com/example/payments-web`",
            "  - Repository ID: `payments-web`",
            "  - Role: `frontend`",
            "  - Context index: `aidlc-docs/repository-context.md`",
            "- Related repository: `github.com/example/payments-infra`",
            "  - Role: `infrastructure`",
            "",
        ]
    )
    related = parse_related_repositories(config)
    assert related.status == "ok"
    assert len(related.entries) == 2
    web, infra = related.entries
    assert web.canonical_remote == "github.com/example/payments-web"
    assert web.repository_id == "payments-web"
    assert web.role == "frontend"
    assert web.context_index == "aidlc-docs/repository-context.md"
    # A `Related repository` entry with no confirmed `Repository ID` yet is
    # still a valid, well-formed entry: the sibling's own ID may not be
    # known from this side yet.
    assert infra.repository_id is None
    assert infra.context_index is None


def test_related_repositories_requires_canonical_remote() -> None:
    # A `Related repository` entry with no value on its own label line has
    # no join key at all. It must be reported as "invalid", never dropped
    # silently -- a malformed entry must not disappear and look like "no
    # related repositories declared".
    config = "## Context identities\n- Related repository:\n  - Role: `frontend`\n"
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert "canonical remote" in related.detail


def test_related_repositories_rejects_invalid_repository_id() -> None:
    config = (
        "## Context identities\n"
        "- Related repository: `github.com/example/payments-web`\n"
        "  - Repository ID: `Payments_Web`\n"
    )
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert "Repository ID" in related.detail


def test_related_repositories_duplicate_remote_is_invalid() -> None:
    # The same canonical remote declared twice in one document is a
    # malformed entry, distinct from the identity-collision case that
    # `detect_repository_id_collision` catches across *different*
    # documents' declarations.
    config = (
        "## Context identities\n"
        "- Related repository: `github.com/example/payments-web`\n"
        "  - Role: `frontend`\n"
        "- Related repository: `github.com/example/payments-web`\n"
        "  - Role: `ui`\n"
    )
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert "declared more than once" in related.detail
    # The first well-formed occurrence is still reported, not withheld.
    assert len(related.entries) == 1


def test_related_repositories_valid_entry_survives_a_sibling_problem() -> None:
    # One malformed entry must not hide a well-formed sibling entry; a
    # caller inspecting `entries` on an "invalid" result still sees what
    # was readable.
    config = (
        "## Context identities\n"
        "- Related repository: `github.com/example/payments-web`\n"
        "  - Role: `frontend`\n"
        "- Related repository:\n"
    )
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert len(related.entries) == 1
    assert related.entries[0].canonical_remote == "github.com/example/payments-web"


def test_related_repositories_rejects_non_remote_canonical_value() -> None:
    # Reproduced defect A: a string with no remote shape at all (here it
    # even fails on whitespace alone) must never be accepted as "ok".
    config = "## Context identities\n- Related repository: `not a remote`\n"
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert related.entries == ()
    assert "canonical remote" in related.detail


def test_related_repositories_rejects_unsupported_host() -> None:
    # A syntactically remote-shaped value on a host this plugin's identity
    # layer does not support must be reported, not silently accepted as a
    # new provider.
    config = "## Context identities\n- Related repository: `gitlab.com/example/api`\n"
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert related.entries == ()


def test_related_repositories_accepts_raw_ssh_remote_normalized_to_canonical() -> None:
    # A raw SSH remote is a supported equivalent transport form; it is
    # normalized through `normalize_remote`, not rejected outright.
    config = "## Context identities\n- Related repository: `git@github.com:example/api.git`\n"
    related = parse_related_repositories(config)
    assert related.status == "ok"
    assert related.entries[0].canonical_remote == "github.com/example/api"


def test_canonical_and_transport_remotes_match_the_same_checkout() -> None:
    # Parsing alone is not enough: the value stored from a declaration must
    # be the same string `match_related_repositories` compares with a
    # checkout remote that `normalize_remote` already produced.
    available = {"api": "github.com/example/api"}
    declarations = (
        "https://github.com/example/api.git",
        "github.com/example/api.git",
        "github.com/example/api",
        "git@github.com:example/api.git",
    )
    for raw in declarations:
        related = parse_related_repositories(
            f"## Context identities\n- Related repository: `{raw}`\n"
        )
        assert related.status == "ok", raw
        remote = related.entries[0].canonical_remote
        assert remote == "github.com/example/api", raw
        matched = match_related_repositories((remote,), available)
        assert matched[remote] == "api", raw


def test_related_repositories_rejects_query_and_fragment_without_echoing_them() -> None:
    # A query or fragment is not part of a repository identity. Accepting it
    # would both miss the real checkout and persist a parameter that does
    # not belong there. The problem text must not repeat that parameter.
    for raw in (
        "github.com/example/api?token=secret",
        "github.com/example/api#readme",
        "https://github.com/example/api.git?token=secret",
    ):
        related = parse_related_repositories(
            f"## Context identities\n- Related repository: `{raw}`\n"
        )
        assert related.status == "invalid", raw
        assert related.entries == (), raw
        assert "secret" not in related.detail
        assert "token=" not in related.detail
        assert "readme" not in related.detail


def test_related_repositories_rejects_context_index_path_traversal() -> None:
    # Reproduced defect B: a `Context index` that climbs above the related
    # repository's own root must never be accepted as "ok", regardless of
    # how many `../` segments it takes to get there.
    config = (
        "## Context identities\n"
        "- Related repository: `github.com/example/api`\n"
        "  - Context index: `../../private/context.md`\n"
    )
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert related.entries == ()
    assert "Context index" in related.detail


def test_related_repositories_rejects_absolute_and_windows_context_index() -> None:
    for bad_path in (
        "/etc/passwd",
        "C:\\Windows\\System32\\config",
        "\\\\server\\share\\context.md",
        "https://example.invalid/context.md",
        "",
    ):
        config = (
            "## Context identities\n"
            "- Related repository: `github.com/example/api`\n"
            f"  - Context index: `{bad_path}`\n"
        )
        related = parse_related_repositories(config)
        assert related.status == "invalid", bad_path
        assert related.entries == (), bad_path


def test_related_repositories_rejects_malformed_repository_id_without_backticks() -> None:
    # Reproduced defect C: a recognized field present without the
    # canonical backtick format must be reported as invalid, never
    # silently treated as absent (`repository_id=None`).
    config = (
        "## Context identities\n"
        "- Related repository: `github.com/example/api`\n"
        "  - Repository ID: api\n"
    )
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert related.entries == ()
    assert "Repository ID" in related.detail


def test_related_repositories_rejects_duplicate_repository_id_even_when_one_is_malformed() -> None:
    # Reproduced defect D: `parse_labeled_fields` alone would only ever see
    # the backtick-formatted occurrence and silently ignore the malformed
    # duplicate. The dedicated occurrence helper must see both and report
    # the duplicate instead of guessing which value is correct.
    config = (
        "## Context identities\n"
        "- Related repository: `github.com/example/api`\n"
        "  - Repository ID: `api`\n"
        "  - Repository ID: other\n"
    )
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert related.entries == ()
    assert "duplicate fields" in related.detail
    assert "Repository ID" in related.detail


def test_related_repositories_absent_optional_field_is_distinct_from_invalid() -> None:
    # An absent `Repository ID` is a valid, well-formed entry (the sibling's
    # own ID may not be known yet); this must not be confused with a
    # *present but malformed* `Repository ID`, which is invalid.
    config = "## Context identities\n- Related repository: `github.com/example/api`\n"
    related = parse_related_repositories(config)
    assert related.status == "ok"
    assert related.entries[0].repository_id is None


def test_related_repositories_rejects_empty_optional_field_value() -> None:
    config = (
        "## Context identities\n"
        "- Related repository: `github.com/example/api`\n"
        "  - Role: ``\n"
    )
    related = parse_related_repositories(config)
    assert related.status == "invalid"
    assert "Role" in related.detail


def test_canonical_remote_or_problem_never_echoes_credentials_in_problem() -> None:
    normalized, problem = _canonical_remote_or_problem(
        "https://user:secret-token@github.com/example/api.git"
    )
    assert normalized == "github.com/example/api"
    assert problem is None
    # And an unsupported credentials-bearing value must not echo the
    # credential back into the problem string either.
    _, problem = _canonical_remote_or_problem("https://user:secret-token@gitlab.com/example/api")
    assert problem is not None
    assert "secret-token" not in problem


def test_resolve_related_context_index_blocks_symlink_escape() -> None:
    # Filesystem-resolution time containment check: a symlink inside the
    # related repository that points outside it must not be followed into
    # a readable path, reusing the same containment logic as the rest of
    # this module (`_resolved_inside`) rather than a bespoke check.
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        outside = Path(temp) / "outside"
        root.mkdir()
        outside.mkdir()
        secret = outside / "secret.md"
        secret.write_text("do not read\n")
        link = root / "escape.md"
        link.symlink_to(secret)

        escaped = resolve_related_context_index(root, "escape.md")
        assert escaped is None

        inside = root / "aidlc-docs"
        inside.mkdir()
        (inside / "repository-context.md").write_text("ok\n")
        resolved = resolve_related_context_index(root, "aidlc-docs/repository-context.md")
        assert resolved == (inside / "repository-context.md").resolve()


def test_resolve_related_context_index_returns_a_missing_file_path() -> None:
    # Containment and existence are different checks. A path that stays
    # inside the repository is returned even when the file is not there;
    # the caller must test existence before reading.
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        resolved = resolve_related_context_index(root, "missing.md")
        assert resolved == (root / "missing.md").resolve()
        assert resolved is not None
        assert not resolved.exists()


def test_match_related_repositories_resolves_available_and_unavailable() -> None:
    available = {
        "app": "github.com/example/payments-web",
        "api": "github.com/example/payments-api",
    }
    result = match_related_repositories(
        ("github.com/example/payments-web", "github.com/example/payments-missing"),
        available,
    )
    assert result["github.com/example/payments-web"] == "app"
    assert result["github.com/example/payments-missing"] == "unavailable"


def test_match_related_repositories_flags_ambiguous_duplicate_remote() -> None:
    # Two checkouts already in scope that both normalize to the same
    # canonical remote (for example two local clones) must be reported as
    # ambiguous, never silently resolved to whichever happens to be first.
    available = {
        "app-clone-1": "github.com/example/payments-web",
        "app-clone-2": "github.com/example/payments-web",
    }
    result = match_related_repositories(("github.com/example/payments-web",), available)
    assert result["github.com/example/payments-web"] == "ambiguous"


def test_context_sync_outcome_membership_pending_is_reachable() -> None:
    # A pending, confirmed membership change (adding a `Related repository`
    # entry, or a `Product` label) must stay reachable even though the
    # source fingerprint is unchanged, the same guarantee already proven
    # above for `project_reference_pending`.
    outcome = context_sync_outcome("unchanged", False, False, False, membership_pending=True)
    assert outcome == "relevant_updates_found"

    # The default (no pending membership change) must not disturb the
    # pre-existing no-op outcome.
    assert context_sync_outcome("unchanged", False, False, False) == "no_relevant_changes"

    # Membership pending alongside other set B/C work is still "relevant
    # updates found", not the migration-pending outcome: set A itself has
    # actionable work.
    assert (
        context_sync_outcome("unchanged", True, False, False, membership_pending=True)
        == "relevant_updates_found"
    )


def test_validate_work_item_type_accepts_hierarchy_rejects_sprint_backlog() -> None:
    # Epic, user story, and task are the three planning levels this
    # function recognizes. Sprint Backlog is a collection of selected work
    # items, not a level in the hierarchy, so it is never a valid input.
    for item_type in ("epic", "user-story", "task"):
        assert validate_work_item_type(item_type) == item_type
    for bad_type in ("sprint-backlog", "feature", "Epic", ""):
        try:
            validate_work_item_type(bad_type)
            raise AssertionError(f"expected ValueError for {bad_type!r}")
        except ValueError:
            pass


def test_validate_plan_item_id_accepts_slug_and_jira_key_rejects_sentence() -> None:
    assert validate_plan_item_id("cancel-order-before-fulfillment") == (
        "cancel-order-before-fulfillment"
    )
    assert validate_plan_item_id("CTY-321") == "CTY-321"
    for bad_id in (
        "We need a story that allows cancellation",
        "cty 321",
        "",
        "-leading-hyphen",
    ):
        try:
            validate_plan_item_id(bad_id)
            raise AssertionError(f"expected ValueError for {bad_id!r}")
        except ValueError:
            pass


def test_validate_parent_reference_hierarchy_rules() -> None:
    # A user story with a recommended Epic parent is structurally valid.
    assert validate_parent_reference("user-story", "epic", "cancel-order", "CTY-296") == ()
    # A task under a user story is structurally valid.
    assert validate_parent_reference("task", "user-story", "configure-gateway", "cancel-order") == ()
    # A user story with no declared parent at all is structurally valid:
    # the methodology does not require a parent before drafting.
    assert validate_parent_reference("user-story", None, "cancel-order", None) == ()
    # An epic must never declare a parent.
    assert validate_parent_reference("epic", "epic", "checkout", "other-epic") != ()
    # A user story's parent must be an epic, not another story or a task.
    assert validate_parent_reference("user-story", "task", "cancel-order", "configure-gateway") != ()
    # Self-parenting is always invalid regardless of type.
    assert validate_parent_reference("task", "task", "same-id", "same-id") != ()
    # A declared parent id without a parent type (or vice versa) is invalid.
    assert validate_parent_reference("user-story", None, "cancel-order", "CTY-296") != ()
    assert validate_parent_reference("user-story", "epic", "cancel-order", None) != ()
    # Against a proposal, a local parent id must name an item of the declared type.
    known = {"cancel-order": "user-story", "checkout": "epic"}
    assert validate_parent_reference(
        "task", "user-story", "configure-gateway", "cancel-order", known
    ) == ()
    mismatch = validate_parent_reference(
        "user-story", "epic", "cancel-order", "configure-gateway",
        {"configure-gateway": "task"},
    )
    assert any("does not match" in reason for reason in mismatch)
    unknown_local = validate_parent_reference(
        "user-story", "epic", "cancel-order", "missing-epic", known
    )
    assert any("unknown local parent" in reason for reason in unknown_local)
    # A Jira key that is not in the proposal is not a structural failure.
    assert validate_parent_reference(
        "user-story", "epic", "cancel-order", "CTY-296", known
    ) == ()


def test_validate_dependency_graph_detects_self_and_unknown_dependencies() -> None:
    problems = validate_dependency_graph(
        {
            "cancel-order": ["self-dependency-check", "payment-refund-task"],
            "payment-refund-task": [],
            "self-dependency-check": ["self-dependency-check"],
        }
    )
    assert "unknown dependency: 'self-dependency-check'" not in str(problems)
    assert "cancel-order" not in problems  # no problems: omitted, not an empty tuple
    assert any("depends on itself" in reason for reason in problems["self-dependency-check"])

    # A well-formed Jira key that is not an item in this proposal is not a
    # structural failure. A local slug that is missing from the proposal is.
    external = validate_dependency_graph({"cancel-order": ["CTY-999"]})
    assert "cancel-order" not in external
    assert external_jira_dependencies({"cancel-order": ["CTY-999"]})["cancel-order"] == ("CTY-999",)
    local_unknown = validate_dependency_graph({"cancel-order": ["missing-story"]})
    assert local_unknown["cancel-order"] == ("unknown local dependency: 'missing-story'",)


def test_validate_dependency_graph_detects_duplicate_and_malformed_edges() -> None:
    # Review finding: a repeated edge in one item's dependency list was
    # previously invisible -- {"a": ["b", "b"], "b": []} used to return {}.
    duplicate = validate_dependency_graph({"a": ["b", "b"], "b": []})
    assert duplicate == {"a": ("duplicate dependency: 'b'",)}

    # A malformed id -- neither this plugin's local slug shape nor a real
    # Jira issue key shape -- is reported instead of silently accepted as
    # an "unknown dependency".
    malformed = validate_dependency_graph({"cancel-order": ["not a valid id!"]})
    assert malformed["cancel-order"] == (
        "not a valid local id or Jira issue key: 'not a valid id!'",
    )

    # A malformed item id (the dict key itself) is reported too.
    malformed_key = validate_dependency_graph({"Not Valid": []})
    assert malformed_key["Not Valid"] == (
        "not a valid local id or Jira issue key: 'Not Valid'",
    )


def test_topological_plan_order_orders_dependencies_before_dependents_and_raises_on_cycle() -> None:
    order = topological_plan_order(
        {
            "cancel-order": ["payment-refund-task"],
            "payment-refund-task": ["configure-gateway"],
            "configure-gateway": [],
        }
    )
    assert order.index("configure-gateway") < order.index("payment-refund-task")
    assert order.index("payment-refund-task") < order.index("cancel-order")

    try:
        topological_plan_order({"a": ["b"], "b": ["a"]})
        raise AssertionError("expected ValueError for a dependency cycle")
    except ValueError as exc:
        assert "cycle" in str(exc)


def test_plan_outcome_combines_item_statuses_without_implying_atomicity() -> None:
    assert plan_outcome({"a": "persisted", "b": "persisted"}) == "ready"
    assert plan_outcome({"a": "approved", "b": "persisted"}) == "approved"
    assert plan_outcome({"a": "blocked", "b": "persisted"}) == "blocked"
    assert plan_outcome({"a": "unavailable", "b": "unavailable"}) == "unavailable"
    assert plan_outcome({"a": "drafted", "b": "unavailable"}) == "drafting"
    assert plan_outcome({"a": "drafted", "b": "persisted"}) == "partial"
    assert plan_outcome({}) == "unavailable"
    # A fully reviewed plan (review complete, no blocker, not yet approved
    # for publication) is its own distinct, more advanced state than
    # ordinary mixed-progress "partial" -- Bugbot CTY-303-finding-1.
    assert plan_outcome({"a": "reviewed", "b": "reviewed"}) == "reviewed"
    # Reviewed mixed with an earlier stage still disagrees enough to stay
    # "partial": review is not uniformly complete across the plan.
    assert plan_outcome({"a": "reviewed", "b": "drafted"}) == "partial"
    try:
        plan_outcome({"a": "pending"})
        raise AssertionError("expected ValueError for an unrecognized status")
    except ValueError:
        pass


def test_jira_mutation_authorized_requires_both_local_and_jira_approval() -> None:
    # Review finding: the previous implementation ignored
    # local_plan_approved entirely (`return bool(jira_mutation_approved)`),
    # so a plan that was never locally approved could still "authorize" a
    # Jira write. Both approvals are now required.
    assert jira_mutation_authorized(local_plan_approved=True, jira_mutation_approved=False) is False
    assert jira_mutation_authorized(local_plan_approved=False, jira_mutation_approved=True) is False
    assert jira_mutation_authorized(local_plan_approved=True, jira_mutation_approved=True) is True
    assert jira_mutation_authorized(local_plan_approved=False, jira_mutation_approved=False) is False


def test_decision_reprompt_allowed_same_shape_as_bugbot_reprompt() -> None:
    # decision_reprompt_allowed is the generic contract; bugbot_reprompt_allowed
    # is kept as a thin, same-behavior alias for existing Bugbot call sites.
    for decision, same_run in (
        ("declined", True),
        ("declined", False),
        ("deferred", True),
        ("deferred", False),
        ("approved", True),
        ("approved", False),
        ("", False),
        ("unknown", False),
    ):
        assert decision_reprompt_allowed(decision, same_run) == bugbot_reprompt_allowed(
            decision, same_run
        )
    assert decision_reprompt_allowed("deferred", same_run=False) is True
    assert decision_reprompt_allowed("deferred", same_run=True) is False
    assert decision_reprompt_allowed("declined", same_run=False) is False
    assert decision_reprompt_allowed("approved", same_run=False) is False
    assert decision_reprompt_allowed("", same_run=False) is True


def test_plan_validate_proposal_runs_every_deterministic_check() -> None:
    valid = plan_validate_proposal(
        {
            "items": [
                {
                    "id": "cancel-order",
                    "type": "user-story",
                    "parent_type": "epic",
                    "parent_id": "CTY-100",
                    "status": "reviewed",
                    "dependencies": ["payment-refund-task"],
                },
                {
                    "id": "payment-refund-task",
                    "type": "task",
                    "parent_type": "user-story",
                    "parent_id": "cancel-order",
                    "status": "reviewed",
                    "dependencies": [],
                },
            ]
        }
    )
    assert all(check.status in ("passed", "external") for check in valid)
    outcome_checks = [c for c in valid if c.name == "plan:outcome"]
    assert outcome_checks and "outcome: reviewed" in outcome_checks[0].detail
    order_checks = [c for c in valid if c.name == "plan:order"]
    assert order_checks and "payment-refund-task" in order_checks[0].detail
    assert any(
        check.name == "plan:external:cancel-order:parent"
        and check.status == "external"
        and "CTY-100" in check.detail
        for check in valid
    )

    # A structurally broken proposal (bad parent, duplicate edge, no status
    # anywhere) is reported as failed/unresolved, not silently passed.
    broken = plan_validate_proposal(
        {
            "items": [
                {"id": "a", "type": "task", "parent_type": "task", "parent_id": "b"},
                {"id": "b", "type": "task", "dependencies": ["a", "a"]},
            ]
        }
    )
    statuses = {check.status for check in broken}
    assert "failed" in statuses

    empty = plan_validate_proposal({"items": []})
    assert len(empty) == 1
    assert empty[0].name == "plan:items"
    assert empty[0].status == "unresolved"
    assert empty[0].detail == "proposal has no items"


def test_plan_validate_proposal_fail_closed_on_reported_shape_bugs() -> None:
    # A persisted sibling must not make a plan with a status-less item look ready.
    mixed = plan_validate_proposal(
        {
            "items": [
                {"id": "a", "type": "epic", "status": "persisted"},
                {"id": "b", "type": "epic"},
            ]
        }
    )
    outcome = next(check for check in mixed if check.name == "plan:outcome")
    assert outcome.status == "failed"
    assert "ready" not in outcome.detail
    assert any(check.name == "plan:item:b:status" and check.status == "failed" for check in mixed)

    # Duplicate ids must fail. They must not collapse to one passed item.
    duplicates = plan_validate_proposal(
        {
            "items": [
                {"id": "a", "type": "epic", "status": "drafted"},
                {"id": "a", "type": "epic", "status": "persisted", "dependencies": ["a"]},
            ]
        }
    )
    assert any(check.status == "failed" and check.detail == "duplicate item id" for check in duplicates)
    assert not any(
        check.name == "plan:outcome" and check.status == "passed" and "ready" in check.detail
        for check in duplicates
    )

    # An unsupported parent type is a failed check, not a traceback.
    try:
        unsupported = plan_validate_proposal(
            {
                "items": [
                    {
                        "id": "a",
                        "type": "task",
                        "parent_type": "subtask",
                        "parent_id": "b",
                        "status": "drafted",
                    }
                ]
            }
        )
    except ValueError as error:
        raise AssertionError(f"validator raised instead of failing closed: {error}") from error
    assert any("unsupported parent type: 'subtask'" in check.detail for check in unsupported)

    # A parent id that is not a slug or a Jira key fails the parent check.
    bad_parent_id = plan_validate_proposal(
        {
            "items": [
                {
                    "id": "a",
                    "type": "task",
                    "parent_type": "epic",
                    "parent_id": "this is not a valid id",
                    "status": "drafted",
                }
            ]
        }
    )
    assert any(
        check.name == "plan:item:a:parent"
        and check.status == "failed"
        and "not a valid local id or Jira issue key" in check.detail
        for check in bad_parent_id
    )

    # A parent_id in this proposal must match the declared parent_type.
    wrong_sibling = plan_validate_proposal(
        {
            "items": [
                {
                    "id": "story-a",
                    "type": "user-story",
                    "parent_type": "epic",
                    "parent_id": "task-b",
                    "status": "drafted",
                },
                {"id": "task-b", "type": "task", "status": "drafted"},
            ]
        }
    )
    assert any(
        check.name == "plan:item:story-a:parent"
        and check.status == "failed"
        and "does not match" in check.detail
        for check in wrong_sibling
    )

    # A local parent slug that is not an item fails, like an unknown dependency.
    missing_parent = plan_validate_proposal(
        {
            "items": [
                {
                    "id": "story-a",
                    "type": "user-story",
                    "parent_type": "epic",
                    "parent_id": "missing-epic",
                    "status": "drafted",
                }
            ]
        }
    )
    assert any(
        check.name == "plan:item:story-a:parent"
        and check.status == "failed"
        and "unknown local parent" in check.detail
        for check in missing_parent
    )

    # An external Jira key is evidence to confirm, not a structural failure.
    external = plan_validate_proposal(
        {
            "items": [
                {
                    "id": "cancel-order",
                    "type": "user-story",
                    "status": "drafted",
                    "dependencies": ["CTY-100"],
                }
            ]
        }
    )
    assert all(check.status != "failed" for check in external)
    assert any(
        check.status == "external" and "CTY-100" in check.detail for check in external
    )

    # The proposal root, each item, and dependencies are shape-checked
    # before any semantic validator can misread them.
    assert plan_validate_proposal([])[0].detail == "proposal must be a JSON object"
    hello = plan_validate_proposal({"items": ["hello"]})
    assert any(check.detail == "item must be an object" for check in hello)
    split_dependency = plan_validate_proposal(
        {
            "items": [
                {
                    "id": "a",
                    "type": "epic",
                    "status": "drafted",
                    "dependencies": "CTY-100",
                }
            ]
        }
    )
    assert any(check.detail == "dependencies must be a list of strings" for check in split_dependency)
    assert "'C'" not in " ".join(check.detail for check in split_dependency)


def test_cli_plan_validate_exit_codes_match_check_results() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        passing = temp_path / "passing.json"
        passing.write_text(
            '{"items": [{"id": "a", "type": "epic", "status": "persisted"}]}',
            encoding="utf-8",
        )
        assert cli_plan_validate([str(passing)]) == 0

        failing = temp_path / "failing.json"
        failing.write_text(
            '{"items": [{"id": "a", "type": "epic", "parent_type": "epic", '
            '"parent_id": "b"}]}',
            encoding="utf-8",
        )
        assert cli_plan_validate([str(failing)]) == 1

        unresolved = temp_path / "unresolved.json"
        unresolved.write_text('{"items": []}', encoding="utf-8")
        assert cli_plan_validate([str(unresolved)]) == 2

        missing = temp_path / "does-not-exist.json"
        assert cli_plan_validate([str(missing)]) == 2

        external = temp_path / "external.json"
        external.write_text(
            '{"items": [{"id": "cancel-order", "type": "user-story", '
            '"status": "drafted", "dependencies": ["CTY-100"]}]}',
            encoding="utf-8",
        )
        assert cli_plan_validate([str(external)]) == 0

    script = ROOT / "scripts" / "context_tools.py"
    stdin_result = subprocess.run(
        [sys.executable, str(script), "plan-validate", "-"],
        input='{"items": [{"id": "a", "type": "epic", "status": "persisted"}]}\n',
        text=True,
        capture_output=True,
        check=False,
    )
    assert stdin_result.returncode == 0, stdin_result.stderr

    crash_result = subprocess.run(
        [sys.executable, str(script), "plan-validate", "-"],
        input=(
            '{"items": [{"id": "a", "type": "task", "parent_type": "subtask", '
            '"parent_id": "b", "status": "drafted"}]}\n'
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert crash_result.returncode == 1
    assert "Traceback" not in crash_result.stdout
    assert "Traceback" not in crash_result.stderr


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
        test_canonical_remote_collision_detects_reverse_direction,
        test_canonical_remote_collision_is_none_for_valid_shared_identity,
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
        test_validate_generated_context_module_budget_is_not_a_validation_result,
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
        test_empty_evidence_catalog_is_not_applicable_not_passed,
        test_valid_evidence_path_resolves_with_mechanical_wording,
        test_evidence_path_outside_authorized_root_fails,
        test_empty_modules_table_is_valid_index_only,
        test_empty_context_cell_fails_as_missing_local_context,
        test_module_rows_without_context_column_fail,
        test_module_envelope_passes_with_required_headings,
        test_module_envelope_fails_when_identity_is_missing,
        test_module_envelope_fails_when_coverage_is_missing,
        test_module_envelope_fails_when_evidence_is_missing,
        test_module_envelope_fails_when_unknowns_is_missing,
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
        test_checkout_deletion_readiness_blocks_on_unrecovered_stash,
        test_checkout_deletion_readiness_blocks_on_dependent_worktree,
        test_checkout_deletion_readiness_failed_inspection_remains_blocked,
        test_checkout_deletion_readiness_fully_verified_checkout_still_passes,
        test_real_git_stash_and_worktree_inspection_feeds_the_readiness_booleans,
        test_legacy_aidlc_fixture_selects_distributed_proposal_without_placement,
        test_partial_legacy_fixture_stays_inspect_until_provenance_is_established,
        test_legacy_detection_rejects_unrecognized_project_type_and_discovery_output_alone,
        test_legacy_architecture_and_inventory_are_separate_approvals,
        test_legacy_inventory_fingerprint_is_scoped_and_order_independent,
        test_prior_run_approval_does_not_authorize_current_writes,
        test_historical_content_blocks_only_deletion_of_the_only_copy,
        test_legacy_ci_and_customized_files_are_not_classified_by_name,
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
        test_related_repositories_missing_when_no_entries_declared,
        test_related_repositories_parses_role_and_context_index,
        test_related_repositories_requires_canonical_remote,
        test_related_repositories_rejects_invalid_repository_id,
        test_related_repositories_duplicate_remote_is_invalid,
        test_related_repositories_valid_entry_survives_a_sibling_problem,
        test_related_repositories_rejects_non_remote_canonical_value,
        test_related_repositories_rejects_unsupported_host,
        test_related_repositories_accepts_raw_ssh_remote_normalized_to_canonical,
        test_canonical_and_transport_remotes_match_the_same_checkout,
        test_related_repositories_rejects_query_and_fragment_without_echoing_them,
        test_related_repositories_rejects_context_index_path_traversal,
        test_related_repositories_rejects_absolute_and_windows_context_index,
        test_related_repositories_rejects_malformed_repository_id_without_backticks,
        test_related_repositories_rejects_duplicate_repository_id_even_when_one_is_malformed,
        test_related_repositories_absent_optional_field_is_distinct_from_invalid,
        test_related_repositories_rejects_empty_optional_field_value,
        test_canonical_remote_or_problem_never_echoes_credentials_in_problem,
        test_resolve_related_context_index_blocks_symlink_escape,
        test_resolve_related_context_index_returns_a_missing_file_path,
        test_match_related_repositories_resolves_available_and_unavailable,
        test_match_related_repositories_flags_ambiguous_duplicate_remote,
        test_context_sync_outcome_membership_pending_is_reachable,
        test_validate_work_item_type_accepts_hierarchy_rejects_sprint_backlog,
        test_validate_plan_item_id_accepts_slug_and_jira_key_rejects_sentence,
        test_validate_parent_reference_hierarchy_rules,
        test_validate_dependency_graph_detects_self_and_unknown_dependencies,
        test_validate_dependency_graph_detects_duplicate_and_malformed_edges,
        test_topological_plan_order_orders_dependencies_before_dependents_and_raises_on_cycle,
        test_plan_outcome_combines_item_statuses_without_implying_atomicity,
        test_jira_mutation_authorized_requires_both_local_and_jira_approval,
        test_decision_reprompt_allowed_same_shape_as_bugbot_reprompt,
        test_plan_validate_proposal_runs_every_deterministic_check,
        test_plan_validate_proposal_fail_closed_on_reported_shape_bugs,
        test_cli_plan_validate_exit_codes_match_check_results,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
