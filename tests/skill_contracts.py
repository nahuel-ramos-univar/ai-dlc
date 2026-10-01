"""Structural checks for plugin layout and local references, not runtime behavior."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
EXPECTED_SKILLS = {
    "sync-context",
    "plan-work",
    "scaffold-project",
    "refine-story",
    "implement-change",
    "validate-change",
    "create-e2e-tests",
}
EXPECTED_AGENTS = {
    "product-reviewer",
    "refinement-reviewer",
    "implementer",
    "implementation-reviewer",
    "validator",
    "context-reviewer",
}
READONLY_AGENTS = EXPECTED_AGENTS - {"implementer"}
# Skills whose `disable-model-invocation` is deliberately false/absent, so
# Cursor's native "Agent Decides" selection may include them from a natural-
# language request. Every other skill in EXPECTED_SKILLS must stay
# slash-only: its blast radius (writing, deleting, or scaffolding) or its
# dependency on an already-approved upstream state is higher than a
# false-positive natural-language match should risk.
NATURAL_LANGUAGE_SKILLS = {"sync-context"}
EXPECTED_RULES = {"ai-dlc-context-and-evidence"}
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def parse_frontmatter(path: Path) -> dict[str, object]:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n"), f"{path} is missing frontmatter"
    _, raw_frontmatter, _ = content.split("---", 2)
    values: dict[str, object] = {}
    for line in raw_frontmatter.strip().splitlines():
        key, separator, value = line.partition(":")
        assert separator, f"{path} has invalid frontmatter line: {line}"
        value = value.strip()
        values[key.strip()] = {"true": True, "false": False}.get(value, value)
    return values


def assert_within_root(path: Path) -> None:
    path.resolve().relative_to(ROOT.resolve())


def test_manifest_paths_and_plugin_identity() -> None:
    manifest = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "simplified-ai-dlc-lifecycle"
    for component in ("skills", "agents", "rules"):
        relative_path = Path(manifest[component])
        assert not relative_path.is_absolute()
        resolved = ROOT / relative_path
        assert resolved.is_dir()
        assert_within_root(resolved)


def test_rule_frontmatter_is_agent_decides_not_always_or_routing() -> None:
    rule_files = sorted((ROOT / "rules").glob("*.mdc"))
    names = {path.stem for path in rule_files}
    assert names == EXPECTED_RULES
    for path in rule_files:
        metadata = parse_frontmatter(path)
        assert metadata["description"]
        # Agent Decides, not Always: this rule must not load on every turn,
        # and must not be the one-routing-rule-per-skill pattern it replaces.
        assert metadata["alwaysApply"] is False
        assert "globs" not in metadata
        content = path.read_text(encoding="utf-8")
        # Minimal, not a routing table: a one-rule-per-skill pattern or a
        # full copy of the sync-context workflow would both show up as
        # several "## Workflow"-shaped stage headings, which this file must
        # not contain.
        assert content.count("## ") <= 1
        assert len(content.splitlines()) <= 40


def test_team_marketplace_indexes_this_plugin() -> None:
    marketplace = json.loads((ROOT / ".cursor-plugin" / "marketplace.json").read_text())
    assert marketplace["name"] == "ai-dlc"
    plugins = marketplace["plugins"]
    assert len(plugins) == 1
    entry = plugins[0]
    assert entry["name"] == "simplified-ai-dlc-lifecycle"
    assert entry["source"] == "."
    assert (ROOT / ".cursor-plugin" / "plugin.json").is_file()


def test_skill_frontmatter_and_unique_names() -> None:
    skill_files = sorted((ROOT / ".cursor" / "skills").glob("*/SKILL.md"))
    names = set()
    for path in skill_files:
        metadata = parse_frontmatter(path)
        name = metadata["name"]
        assert name == path.parent.name
        assert metadata["description"]
        if name in NATURAL_LANGUAGE_SKILLS:
            # Enabled for native "Agent Decides" selection: either the key is
            # absent, or explicitly false. Never true for this skill.
            assert metadata.get("disable-model-invocation") is not True
        else:
            assert metadata["disable-model-invocation"] is True
        assert name not in names
        names.add(name)
    assert names == EXPECTED_SKILLS
    assert NATURAL_LANGUAGE_SKILLS <= EXPECTED_SKILLS


def test_removed_components_are_not_exposed_or_referenced() -> None:
    removed_skills = {"check-governance", "resolve-defect", "deliver-change"}
    assert not any(
        (ROOT / ".cursor" / "skills" / skill).exists() for skill in removed_skills
    )
    assert not (ROOT / "agents" / "governance-reviewer.md").exists()

    for path in ROOT.rglob("*.md"):
        if path.name == "CHANGELOG.md":
            continue
        content = path.read_text(encoding="utf-8")
        for name in (*removed_skills, "governance-reviewer"):
            assert name not in content, f"{path} still references {name}"


def test_agent_frontmatter_and_readonly_boundaries() -> None:
    agent_files = sorted((ROOT / "agents").glob("*.md"))
    names = set()
    for path in agent_files:
        metadata = parse_frontmatter(path)
        name = metadata["name"]
        assert metadata["description"]
        assert name not in names
        names.add(name)
        if name in READONLY_AGENTS:
            assert metadata["readonly"] is True
        else:
            assert "readonly" not in metadata
    assert names == EXPECTED_AGENTS


def test_local_markdown_references_resolve() -> None:
    for path in (*ROOT.rglob("*.md"), *ROOT.rglob("*.mdc")):
        content = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(content):
            if "://" in target or target.startswith("#"):
                continue
            local_path = target.split("#", 1)[0]
            if not local_path:
                continue
            resolved = (path.parent / local_path).resolve()
            assert_within_root(resolved)
            assert resolved.exists(), f"{path} references missing {target}"


def test_every_skill_uses_compact_response_style() -> None:
    style = (ROOT / "references" / "response-style.md").read_text(encoding="utf-8")
    assert "chat-facing reply" in style
    assert "not a content budget" in style
    assert "Do not apply this rule to file contents or other deliverables" in style
    assert "Do not omit a requirement, test case, finding, constraint, or evidence" in style
    for skill_name in EXPECTED_SKILLS:
        skill = ROOT / ".cursor" / "skills" / skill_name / "SKILL.md"
        assert "../../../references/response-style.md" in skill.read_text(
            encoding="utf-8"
        )


def test_context_retrieval_contract_is_wired() -> None:
    retrieval = ROOT / "references" / "context-retrieval.md"
    assert retrieval.is_file()
    context_aware_skills = EXPECTED_SKILLS - {"sync-context", "scaffold-project"}
    for skill_name in context_aware_skills:
        skill = ROOT / ".cursor" / "skills" / skill_name / "SKILL.md"
        assert "../../../references/context-retrieval.md" in skill.read_text(
            encoding="utf-8"
        )
    for agent in (ROOT / "agents").glob("*.md"):
        assert "../references/context-retrieval.md" in agent.read_text(
            encoding="utf-8"
        )


def test_context_generation_contract_has_required_examples() -> None:
    sync_dir = ROOT / ".cursor" / "skills" / "sync-context"
    generation = (sync_dir / "references" / "context-generation.md").read_text(
        encoding="utf-8"
    )
    bugbot = (sync_dir / "references" / "bugbot-configuration.md").read_text(
        encoding="utf-8"
    )
    refresh = (sync_dir / "references" / "incremental-refresh.md").read_text(
        encoding="utf-8"
    )
    preflight = (ROOT / "references" / "repository-preflight.md").read_text(
        encoding="utf-8"
    )
    templates = (sync_dir / "references" / "context-templates.md").read_text(
        encoding="utf-8"
    )
    artifact_home = (sync_dir / "references" / "artifact-home.md").read_text(
        encoding="utf-8"
    )
    assert "<module-root>/AIDLC_CONTEXT.md" in generation
    assert "aidlc-docs/context/<repo-id>/<module-id>.md" in generation
    assert "<source-root>/.cursor/BUGBOT.md" in generation
    assert "absolute local checkout paths into generated context" in generation
    assert "deterministic content fingerprint" in generation
    assert "Initial discovery" in refresh
    assert "Incremental refresh" in refresh
    assert "Report actionable defects introduced by the change" in bugbot
    assert "Inspect surrounding code" in bugbot
    assert "IAM or security defects introduced by a diff" in bugbot
    assert "artifact home's configuration" in bugbot
    assert "meaningful review boundary" in bugbot
    assert "over speculation" in bugbot
    assert "generated, vendor, build, coverage, lockfile, or fixture" in bugbot
    assert "One rule, one invariant" in bugbot
    assert "Ownership, task assignment" in bugbot
    assert "Nested tracked" in preflight
    assert "Unversioned tree" in preflight
    assert "Nested repository, submodule, or worktree" in preflight
    assert "permit discovery" in preflight
    assert "Context-discovery writes" in preflight
    assert "Scaffold-project writes follow the approved proposal" in preflight
    assert "freshness fingerprint" in refresh
    assert "| 150 lines |" in templates
    assert "| 300 lines |" in templates
    assert "Anthropic requirement" in templates
    assert "persisted repository ID" in artifact_home
    assert "short hash of the full canonical identity" in generation
    assert "Do not exclude product source under `.cursor/skills`" in generation
    for scenario in (
        "Single-module repository",
        "Monorepo",
        "Multi-repository workspace",
    ):
        assert scenario in generation
    assert "once per repository for initial setup" in bugbot
    assert "declined" in bugbot


def test_context_artifact_contract_and_skill_budgets() -> None:
    sync_dir = ROOT / ".cursor" / "skills" / "sync-context"
    for relative in (
        "references/artifact-home.md",
        "references/context-templates.md",
        "references/context-generation.md",
        "references/incremental-refresh.md",
        "references/bugbot-configuration.md",
        "references/validation.md",
        "references/review-handoff.md",
        "references/project-rules.md",
        "references/legacy-migration.md",
    ):
        assert (sync_dir / relative).is_file()
    for skill in (ROOT / ".cursor" / "skills").glob("*/SKILL.md"):
        assert len(skill.read_text(encoding="utf-8").splitlines()) < 500


def test_context_review_contract_has_required_language() -> None:
    sync_dir = ROOT / ".cursor" / "skills" / "sync-context"

    def flat(relative: Path) -> str:
        return " ".join(relative.read_text(encoding="utf-8").split())

    skill = flat(sync_dir / "SKILL.md")
    generation = flat(sync_dir / "references" / "context-generation.md")
    refresh = flat(sync_dir / "references" / "incremental-refresh.md")
    validation = flat(sync_dir / "references" / "validation.md")
    handoff = flat(sync_dir / "references" / "review-handoff.md")
    reviewer = flat(ROOT / "agents" / "context-reviewer.md")

    assert "inventoried" in skill.lower()
    assert "inspected" in skill.lower()
    assert "verified" in skill.lower()
    assert "context-reviewer" in skill
    assert "at most one targeted follow-up" in skill

    assert "proves that test code exists, not that it passed" in generation
    assert "proves that a job is configured, not that it ran successfully" in generation
    assert "does not prove runtime usage" in generation
    assert "does not prove authenticated connectivity" in generation
    assert "Never describe all tracked or fingerprinted files as examined" in generation
    assert "Do not create one context file per source file or directory" in generation

    assert "does not prove semantic accuracy or that every file was fully inspected" in refresh
    assert "does not cover uncommitted working-tree changes" in refresh

    assert "check_document_budget" in validation
    assert "resolve_markdown_links" in validation
    assert "resolve_source_path" in validation
    assert "find_stale_source_paths" in validation
    assert "find_duplicate_values" in validation
    assert "find_duplicate_identities" in validation
    assert "find_duplicate_context_targets" in validation
    assert "parse_recorded_fingerprint" in validation
    assert "validate_generated_context" in validation
    assert "authorized_roots" in validation
    assert "not semantic correctness" in validation
    assert "Never treat this as passing" in validation
    assert "Do not write an absolute local path" in validation

    assert "at most one targeted follow-up" in handoff
    assert "Do not trigger review solely by file count" in handoff
    assert "never call main-chat self-review independent" in handoff
    assert "is not proof that the entire repository context is correct" in reviewer


def test_release_workflow_files_exist() -> None:
    assert (ROOT / ".github" / "workflows" / "release.yml").is_file()
    assert (ROOT / ".github" / "workflows" / "conventional-commits.yml").is_file()
    assert (ROOT / "scripts" / "release" / "release.sh").is_file()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.startswith("# Changelog")
    version = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text())["version"]
    assert re.match(r"^\d+\.\d+\.\d+$", version)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__/" in gitignore


def test_context_review_fixture_documents_expected_findings() -> None:
    """Structural check only: the fixture exists and names its seeded defects.

    This does not run `context-reviewer` and does not assert that any
    reviewer catches these defects. It only confirms the fixture and its
    expected-findings document are present, labeled unevaluated, and agree
    on which defect markers they describe. The reviewer-facing document
    (`AIDLC_CONTEXT.md`) must not label its own defects inline; the answer
    key lives only in `expected_findings.md`.
    """
    fixture_dir = ROOT / "tests" / "fixtures" / "context_review"
    fixture = (fixture_dir / "AIDLC_CONTEXT.md").read_text(encoding="utf-8")
    findings = (fixture_dir / "expected_findings.md").read_text(encoding="utf-8")

    assert "one recorded fallback review" in findings.lower()
    assert "not native named-agent verification" in findings
    assert "not an automated semantic regression test" in findings
    assert "answer key" in findings.lower()
    assert "Live evaluation record" in findings

    markers = {
        "unsupported-coverage-claim",
        "unsupported-claim",
        "omitted-dependency",
        "fact-contradicted-by-unknown",
    }
    for marker in markers:
        # The reviewer-facing fixture must never label its own seeded defects.
        assert f"fixture-defect: {marker}" not in fixture, (
            f"AIDLC_CONTEXT.md must not reveal its own seeded defect {marker}"
        )
        assert marker in findings, f"expected_findings.md is missing marker {marker}"
    assert "fixture-defect" not in fixture
    assert "expected_findings.md" not in fixture

    # The fixture's source tree must back the omitted-dependency finding with
    # a real, grep-able import, not just prose.
    receipts = (fixture_dir / "source" / "receipts" / "receipts_digest.py").read_text(
        encoding="utf-8"
    )
    assert "from notifications.notifications_worker import NOTIFICATION_SENT_TOPIC" in receipts
    notifications_files = sorted(
        (fixture_dir / "source" / "notifications").glob("*.py")
    )
    assert len(notifications_files) == 2, (
        "the coverage-claim finding depends on source/notifications having "
        "exactly 2 files, not the 4 the fixture claims to have examined"
    )


def test_manual_evaluation_and_shared_contracts_exist() -> None:
    assert (ROOT / "MANUAL_EVALUATION.md").is_file()
    for filename in (
        "repository-preflight.md",
        "jira-integration.md",
        "skill-composition.md",
        "response-style.md",
        "context-retrieval.md",
    ):
        assert (ROOT / "references" / filename).is_file()


if __name__ == "__main__":
    tests = [
        test_manifest_paths_and_plugin_identity,
        test_rule_frontmatter_is_agent_decides_not_always_or_routing,
        test_team_marketplace_indexes_this_plugin,
        test_skill_frontmatter_and_unique_names,
        test_removed_components_are_not_exposed_or_referenced,
        test_agent_frontmatter_and_readonly_boundaries,
        test_local_markdown_references_resolve,
        test_every_skill_uses_compact_response_style,
        test_context_retrieval_contract_is_wired,
        test_context_generation_contract_has_required_examples,
        test_context_artifact_contract_and_skill_budgets,
        test_context_review_contract_has_required_language,
        test_context_review_fixture_documents_expected_findings,
        test_release_workflow_files_exist,
        test_manual_evaluation_and_shared_contracts_exist,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
