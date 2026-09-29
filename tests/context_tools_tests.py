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
    cli_validate,
    content_fingerprint,
    detect_repository_id_collision,
    extract_table_column,
    find_duplicate_context_targets,
    find_duplicate_identities,
    find_duplicate_values,
    find_stale_source_paths,
    normalize_remote,
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
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
