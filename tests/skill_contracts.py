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
    "context-architect",
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
    assert "exactly one pull-request or merge-request template path" in preflight
    assert "Do not treat that exception as permission to write" in preflight
    assert "write a GitHub path when the host is GitLab" in preflight
    assert "does not use the enclosing checkout's ignore rules" in preflight
    assert "does not create, configure, or imply a Cloud Agent environment" in preflight
    assert "freshness fingerprint" in refresh
    assert "pr_template_pending" in refresh
    assert "membership_pending" in refresh
    assert "does not use the enclosing repository's exclude rules" in refresh
    assert "does not use the enclosing repository's exclude rules" in generation
    assert "untracked-tree` is not the kind" in generation
    assert "| 150 lines |" in templates
    assert "| 300 lines |" in templates
    assert "Anthropic requirement" in templates
    assert "persisted repository ID" in artifact_home
    assert "short hash of the full canonical identity" in generation
    assert "Do not exclude product source under `.cursor/skills`" in generation
    for scenario in (
        "Single-module service",
        "Monorepo",
        "Multi-repository workspace",
        "Documentation-only or genuinely passive repository",
    ):
        assert scenario in generation
    assert "once per repository for initial setup" in bugbot
    assert "declined" in bugbot
    pr_template = (
        sync_dir / "references" / "pull-request-template.md"
    ).read_text(encoding="utf-8")
    assert "Do not assume GitHub" in pr_template
    assert ".github/pull_request_template.md" in pr_template
    assert ".gitlab/merge_request_templates/Default.md" in pr_template
    assert ".bitbucket/pull_request_template.md" in pr_template
    assert "docs/PULL_REQUEST_TEMPLATE" in pr_template or "docs/`" in pr_template
    assert "PULL_REQUEST_TEMPLATE/" in pr_template
    assert "from the remote hostname" in pr_template
    assert "path clearly names GitLab" not in pr_template
    assert "does not authorize commit, push" in pr_template
    assert "## Pull request template decisions" in pr_template
    assert "is ordinary source" in pr_template
    assert "EXCLUDED_PARTS" in pr_template
    assert "GENERATED_FILENAMES" in pr_template
    assert "pull-request-template.md" in generation
    assert ".bitbucket/pull_request_template.md" in preflight
    skill = (sync_dir / "SKILL.md").read_text(encoding="utf-8")
    skill_flat = " ".join(skill.split())
    assert "Conditional set B and C contracts" in skill
    assert "Load set B and C contracts only per" in skill
    assert "before deciding, proposing, or writing" in skill_flat
    assert "first-time offer is pending" in skill_flat
    assert "never suppresses another" in skill_flat
    assert "stable policy ID" in skill_flat


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
        "references/architecture-discovery.md",
        "references/context-quality.md",
        "references/pull-request-template.md",
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
    assert "*.py[cod]" in gitignore
    assert "tests/.tmp-*" in gitignore
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "Structural tests" in ci
    assert "does not launch Cursor" in ci
    assert "does not prove runtime plugin discovery" in ci
    assert "playwright" not in ci.lower()
    manual = (ROOT / "MANUAL_EVALUATION.md").read_text(encoding="utf-8")
    assert "Plugin discovery in Cursor" in manual
    assert "static layout and helper checks only" in manual


def test_architecture_discovery_contract_has_required_language() -> None:
    sync_dir = ROOT / ".cursor" / "skills" / "sync-context"

    def flat(relative: Path) -> str:
        return " ".join(relative.read_text(encoding="utf-8").split())

    discovery = flat(sync_dir / "references" / "architecture-discovery.md")
    quality = flat(sync_dir / "references" / "context-quality.md")
    templates = flat(sync_dir / "references" / "context-templates.md")
    generation = flat(sync_dir / "references" / "context-generation.md")
    skill = flat(sync_dir / "SKILL.md")
    reviewer = flat(ROOT / "agents" / "context-reviewer.md")
    architect = flat(ROOT / "agents" / "context-architect.md")
    validation = flat(sync_dir / "references" / "validation.md")
    handoff = flat(sync_dir / "references" / "review-handoff.md")

    # The five-state coverage model is AI-decided, not a Python checklist.
    for state in ("Verified", "Partial", "Inferred", "Unknown", "Not applicable"):
        assert state in discovery
    assert "not a Python-enforced checklist" in discovery
    assert "Runtime flows" in discovery
    assert "Trigger:" in discovery

    # Anti-over-orchestration: no default one-agent-per-directory/dimension.
    assert "Do not dispatch one subagent per directory or per file by default" in discovery
    assert "Do not dispatch one subagent per architectural dimension by default" in discovery

    # Adaptive, tiered exploration — not a fixed per-module mandate.
    assert "Initial or full sync" in discovery
    assert "A material architecture change" in discovery
    assert "A small factual update" in discovery

    # Coverage table and quality bar replace line count as the quality signal.
    assert "## Coverage" in quality
    assert "quality bar" in quality.lower()
    assert "No deterministic validator counts rows" in quality

    # The four explicit non-acceptable regression patterns.
    assert "Shallow service context" in quality
    assert "False completeness" in quality
    assert "Length gaming" in quality
    assert "Honest unknown beats invented behavior" in quality

    # Budgets are reframed as advisory for module context, not a correctness
    # property, while the repository index stays a hard, short-index gate.
    assert "not a correctness property" in templates
    assert "advisory, not a validity gate" in templates
    assert "stays a hard target" in templates
    assert "Never cut a verified dimension, a runtime flow, or evidence" in templates
    assert "## Coverage" in templates
    assert "## Representative runtime flows" in templates

    # Module line count is a metric, not a passed/failed validation result.
    assert "does not emit a `modules:budget` check at all" in templates
    assert "check_document_budget" in validation
    assert "Do not call it as a module validity gate" in validation
    assert "document_metrics" in validation
    assert "never as passed or failed" in validation

    # Module count is not documentation depth.
    assert "Do not skip `AIDLC_CONTEXT.md` merely because the repository is single-module" in generation
    assert "Do not skip `AIDLC_CONTEXT.md` merely because the repository is single-module" in skill
    assert "keep context in its index and do not create" not in generation
    assert "never a manufactured module file" not in skill
    assert "inspect enough current source" not in skill
    assert "For a first sync, follow the Initial/full sync exploration tier above" in skill
    assert "Do not mechanically re-inspect the whole scope already explored" in skill

    # Architecture inventory evaluates every dimension; the published table
    # only keeps material, relevant-unknown, and non-obvious N/A rows.
    assert "Evaluate every dimension in this inventory" in discovery
    assert "important or non-obvious" in quality
    assert "Inspection scope:" in discovery
    assert "Inspection limitations:" in discovery

    # context-generation.md hands drafting off to architecture discovery.
    assert "architecture-discovery.md" in generation
    assert "context-quality.md" in generation
    assert "This skill does not write `architecture.md`" in generation
    assert "architecture-decisions.md" in generation

    # SKILL.md wires the three-tier model and progressive disclosure.
    assert "Initial or full sync" in skill
    assert "Material architecture change" in skill
    assert "Small factual update" in skill
    assert "progressive disclosure" in skill.lower()
    assert "context-architect" in skill

    # context-reviewer splits Accuracy and Completeness, and treats an
    # honest Unknown as a non-finding.
    assert "Accuracy" in reviewer
    assert "Completeness" in reviewer
    assert "is not itself a finding" in reviewer

    # context-architect is read-only and discovery-only.
    assert "readonly: true" in architect
    assert "does not write Markdown structure" in architect
    assert "Never open secret-value files" in architect
    assert "Respect exactly the repository or module scope authorized" in architect
    assert "Never open secret-value files" in reviewer
    assert "Respect exactly the repository or module scope authorized" in reviewer
    assert "do not blindly re-scan every file" in reviewer

    # Coverage is a summary; material findings must survive into the document.
    assert "Material findings:" in discovery
    assert "Material architecture details" in quality
    assert "Material architecture details" in templates
    assert "canonical catalog" in quality
    assert "Opening some related file is not enough" in discovery
    assert "empty `## Modules` table" in generation
    assert "module row with an empty or missing Context target is invalid" in skill

    # Mechanical evidence wording must not look like semantic success.
    assert "evidence references resolved" in validation
    assert "no local evidence paths to resolve" in validation
    assert "missing required heading" in validation
    assert "structural envelope" in validation or "Coverage" in validation
    assert "prefer `context-architect`" in skill
    assert "prefer one `context-architect` call" in discovery
    assert "quality assurance is partial" in skill
    assert "quality assurance as partial" in handoff
    assert "self-review is not that approval" in skill
    assert "never call main-chat self-review independent" in handoff
    assert "module row requires a local context file" in validation

    readme = flat(ROOT / "README.md")
    assert "context-architect" in readme
    assert "read-only architecture exploration" in readme
    assert "used only for review or bounded implementation" not in readme


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
        "false-completeness-coverage",
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


def test_project_onboarding_is_conditionally_referenced() -> None:
    onboarding = (ROOT / "references" / "project-onboarding.md").read_text(encoding="utf-8")
    assert "## Project references" in onboarding
    assert "project-rules.md" in onboarding
    assert "do not create or modify Jira" in onboarding
    assert "normalize_remote" in onboarding
    instruction = (
        "only when project references are missing, ambiguous, or explicitly being reconsidered"
    )
    for skill_name in ("sync-context", "scaffold-project"):
        skill = " ".join(
            (ROOT / ".cursor" / "skills" / skill_name / "SKILL.md")
            .read_text(encoding="utf-8")
            .split()
        )
        assert "../../../references/project-onboarding.md" in skill
        assert instruction in skill
        assert "not a conditional loader" in skill
    for skill_name in EXPECTED_SKILLS - {"sync-context", "scaffold-project"}:
        skill = (ROOT / ".cursor" / "skills" / skill_name / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "project-onboarding.md" not in skill


def test_plan_work_contract_has_required_language() -> None:
    plan_dir = ROOT / ".cursor" / "skills" / "plan-work"

    def flat(relative: str) -> str:
        return " ".join((plan_dir / relative).read_text(encoding="utf-8").split())

    skill = flat("SKILL.md")
    task = flat("references/task.md")
    epic_discovery = flat("references/epic-discovery.md")
    feature_or_epic = flat("references/feature-or-epic.md")
    sprint_backlog = flat("references/sprint-backlog.md")
    update_existing = flat("references/update-existing.md")
    product_review = flat("references/product-review.md")
    story_template = (plan_dir / "references" / "jira-story-template.md").read_text(
        encoding="utf-8"
    )
    story_template_flat = " ".join(story_template.split())
    reviewer = " ".join((ROOT / "agents" / "product-reviewer.md").read_text(encoding="utf-8").split())
    jira = " ".join(
        (ROOT / "references" / "jira-integration.md").read_text(encoding="utf-8").split()
    )

    # Section 1/17: Epic, User Story, Task, Sprint Backlog hierarchy; Sprint
    # Backlog is a collection, not a fourth parent level.
    assert "Epic" in skill and "User Story" in skill and "Task" in skill
    assert "Sprint Backlog is a planning collection" in skill
    assert "project-onboarding.md" not in skill

    # Section 5: no fake "As a developer" Story-washing of technical work.
    assert "As a developer" in task
    assert "fake persona" in task

    # Section 7/8: parent discovery is evidence-based, never silent, and is
    # not a general semantic duplicate-story search.
    assert "merely because titles share terms" in epic_discovery
    assert "do not create it without explicit approval" in epic_discovery
    assert "does not run a general semantic search for a duplicate Story" in epic_discovery

    # Section 5 / Bugbot CTY-303-finding-2: a Task's parent discovery must
    # allow a User Story, not only an Epic.
    assert "recommend a parent User Story" in skill
    assert "an Epic directly only when none does" in skill
    assert "an Epic directly only when no such Story applies" in epic_discovery

    # Section 3: Epic fields and no premature decomposition.
    assert "problem or opportunity" in feature_or_epic
    assert "Do not split this into implementation Tasks" in feature_or_epic

    # Section 6: select vs. create, no invented capacity.
    assert "selected" in sprint_backlog and "created" in sprint_backlog
    assert "Do not invent team capacity" in sprint_backlog

    # Section 12: preserve approved content, surface conflicts, no duplicate
    # re-creation on an unchanged re-run.
    assert "Preserve content the Product Owner already approved" in update_existing
    assert "must not create a duplicate planning artifact" in update_existing

    # Section 13/14: severity vocabulary, no-findings is valid, reviewer
    # cannot silently decide a scope-changing finding.
    for vocabulary in product_review, reviewer:
        assert "Blocker" in vocabulary and "Major" in vocabulary and "Minor" in vocabulary
        assert "Suggestion" in vocabulary
    assert "No findings" in product_review or "no findings" in product_review.lower()
    assert "manufacture a finding" in product_review
    assert "skill-composition.md" in product_review
    assert "do not delay that review" in product_review
    assert "completed` only when the reviewer responded" in product_review or "only when the reviewer responded" in product_review

    # Bugbot: the reviewer must not run or assume a standalone duplicate search.
    assert "duplicate candidates" not in reviewer
    assert "Do not search Jira for duplicates" in reviewer
    assert "not evidence that no duplicates exist" in reviewer
    assert "Do not pass a duplicate-candidates list" in product_review

    # Section 9: local plan approval never implies Jira mutation approval.
    assert "is never, by itself, approval to mutate Jira" in skill

    # Story description template: Markdown, offered once. Business AC go
    # in the writable field when one exists, otherwise Description.
    assert "jira-story-template.md" in skill
    assert "## Planning template" in skill
    assert "decision_reprompt_allowed" in skill
    assert "confirmed absent" in skill
    assert "Do not ask for a second approval" in skill
    # Section 8 / review finding: the Jira format question is a publication
    # step, not a drafting-time competitor to the Product Owner's questions.
    assert "Apply this when preparing a User Story's Jira write payload, not earlier" in skill

    # Review finding: plan-work must not force sync-context before any
    # business-only planning, and must not run a proactive duplicate search.
    assert "business-only planning" in skill
    assert "Search Jira for an obvious exact duplicate" not in skill
    assert "does not mean stop drafting" in skill
    assert "hand off to `/sync-context` instead of rediscovering" not in skill
    assert "Do not run a standalone duplicate search" in skill
    assert "Search for duplicate work before proposing a new issue" not in update_existing
    assert "duplicate-search boundaries" not in task

    # Review finding: deterministic validators must be wired into a real,
    # runnable step, resolved from this skill, not from the consumer repo.
    assert "plan_validate_proposal" in skill
    assert "plan-validate" in skill
    assert "../../../scripts/context_tools.py" in skill
    assert "Do not create `proposal.json` inside the consumer repository" in skill
    assert "work-record.md" in skill
    assert "criterion-ids.md" in skill
    assert "Do not invent NFR headings or thresholds" in skill
    assert "architecture-decisions.md" in skill
    assert "Do not turn a product wish into an accepted technical decision" in skill
    assert "do not overwrite a custom Product Owner template" in skill

    # Dependencies become real Jira issue links at publication, not only
    # prose, and optional fields (Priority, Labels, Fix Version, Sprint,
    # Story Points) are evidence-based suggestions the Product Owner must
    # approve, edit, or skip individually — never invented.
    assert "Approve each dependency as a plain-language relationship between draft identifiers" in skill
    assert "Optional suggested fields" in skill
    assert "never substitutes for this capacity rule" in skill
    assert "included in the same publication confirmation" in skill
    assert "Dependencies as issue links" in jira
    assert "createJiraIssueLink" in jira
    assert "listJiraIssueLinkTypes" in jira
    assert "Do not apply one type's orientation to every type" in jira
    assert "A successful create response does not prove the direction" in jira
    assert "do not suggest a number" in jira
    assert "human estimate" in jira
    assert "Never invent a sprint, a start or end date, or team capacity" in jira
    approval_contract = " ".join(
        (ROOT / "references" / "approval-contract.md").read_text(encoding="utf-8").split()
    )
    assert "plain-language relationship between draft identifiers" in approval_contract
    assert "Shared by every skill that writes to Jira" in approval_contract
    assert "Approval must come from the role the calling skill authorizes" in approval_contract
    assert "does not itself name that role" in approval_contract
    assert "say what is missing" in feature_or_epic

    # Review finding: this plugin's Epic/User-Story/Task model is not Jira's
    # real issue-type hierarchy. A Task that supports a Story is not silently
    # published as a Subtask.
    assert "not Jira's issue-type hierarchy" in skill
    assert "Do not silently change a Task into a Subtask" in skill
    assert "Do not silently change a Task into a Subtask" in jira
    assert "normally Jira's Subtask" not in jira

    # The local-plan approval flag is a named state, distinct from review
    # and from Jira publication approval.
    assert "local_plan_approved" in skill
    assert "jira_mutation_approved" in skill
    assert "independent review finished with no unresolved blocker" in skill
    assert "sets the item to `blocked`, not `reviewed`" in skill
    assert "Offer the template only when preparing the Jira publication payload" in story_template_flat
    assert "before a User Story description is drafted" not in story_template_flat
    single_story = flat("references/single-story.md")
    assert "Do not fill or offer" in single_story
    assert "When a Jira description is needed, fill the approved shape" not in single_story
    assert "Author the description in Markdown" in story_template_flat
    assert "confirmed absent" in story_template_flat
    assert "Never publish operational disclaimers" in story_template_flat
    assert "As a [user], I want [capability], so that [benefit]." in story_template
    assert "#### 📋 Description" not in story_template
    assert "**User story:**" not in story_template
    heading_order = (
        "#### 🎯 Context",
        "#### 📌 Scope / Out of Scope",
        "#### 🎨 Design / References",
        "#### 💬 Stakeholder Questions",
        "#### 🛠️ Technical Notes",
        "#### 🧪 Validation Notes",
        "#### 📊 Goals & Metrics",
        "#### 🔗 Dependencies & Risks",
        "#### ✅ Acceptance Criteria",
    )
    heading_positions = [story_template.index(heading) for heading in heading_order]
    assert heading_positions == sorted(heading_positions)
    assert "\n\n---\n\n" in story_template
    assert "never count as completed or approved requirements" in story_template_flat
    assert "existing planning flow" in story_template_flat
    assert "format the available tool actually supports" in story_template_flat
    default_skeleton = (
        story_template.split("## Default description", 1)[1]
        .split("```markdown", 1)[1]
        .split("```", 1)[0]
    )
    assert "[Add confirmed technical constraints, if applicable]" in default_skeleton
    assert "[Add additional business validation guidance, if needed]" in default_skeleton
    assert "[Add a story-specific goal or metric, if applicable]" in default_skeleton
    assert "refine-story" not in default_skeleton
    assert "dedicated field" not in default_skeleton
    assert "approved destination" not in default_skeleton
    assert "h4." not in story_template
    assert "|| Question ||" not in story_template
    assert "Do not hand-write Jira wiki markup" in jira
    assert "format the available tool actually supports" in jira
    assert "that field only, no Description duplicate" in jira
    assert "exists but not writable" in jira

    # Closing review uses the host Canvas capability when available, with an
    # equivalent chat fallback when the host cannot open one -- never a
    # hardcoded claim about which hosts can or cannot open a Canvas.
    assert "canvas-review.md" in skill
    assert "use the host Canvas capability when available" in skill
    assert "Cursor agents cannot open a Canvas today" not in skill


def test_refine_story_contract_has_required_language() -> None:
    """Structural checks only: required phrases are present in the skill and
    its references. This does not prove Cursor follows the workflow, that
    the challenge step produces a real finding, or that a Jira write
    succeeds — see MANUAL_EVALUATION.md for the scenarios that require an
    actual run."""
    refine_dir = ROOT / ".cursor" / "skills" / "refine-story"

    def flat(relative: str) -> str:
        return " ".join((refine_dir / relative).read_text(encoding="utf-8").split())

    skill = flat("SKILL.md")
    template = flat("references/technical-task-template.md")
    reviewer = " ".join(
        (ROOT / "agents" / "refinement-reviewer.md").read_text(encoding="utf-8").split()
    )
    approval_contract = " ".join(
        (ROOT / "references" / "approval-contract.md").read_text(encoding="utf-8").split()
    )
    implement_change = " ".join(
        (ROOT / ".cursor" / "skills" / "implement-change" / "SKILL.md")
        .read_text(encoding="utf-8")
        .split()
    )

    # Input accepts a Jira key/URL and routes by the supplied issue's type;
    # an Epic can be refined directly, not forced through an artificial Story.
    assert "Jira key or URL" in skill
    assert "Epic" in skill and "refine it directly" in skill
    assert "artificial intermediate Story" in skill
    assert "Do not invent a root cause" in skill

    # The technical discussion/challenge step always runs, independent of
    # the fast/standard/deep review-profile selection, and must not invent
    # an objection to satisfy itself.
    assert "always runs" in skill
    assert "regardless of the review profile" in skill
    assert "Do not invent an objection" in skill
    assert "This selection governs only the independent" in skill

    # Work breakdown defaults to one coherent item; a split needs a stated
    # reason, and the DevOps-task-split rule is project-specific, not a
    # universal plugin policy baked in here.
    assert "Prefer one coherent technical item" in skill
    assert "this is a default, not a hard limit" in skill
    assert "do not assume every project this skill runs in has that policy" in skill
    assert "do not embed it here as a universal rule for every consumer" in skill

    # Approval authority: the shared contract defers the role to the calling
    # skill; refine-story names the developer for technical scope and routes
    # a business-scope change back to the Product Owner through /plan-work.
    assert "Approval must come from the role the calling skill authorizes" in approval_contract
    assert "allows the authorized developer to approve technical implementation content" in approval_contract
    assert "An authorized developer may approve the technical Jira change set" in skill
    assert "requires Product Owner approval through `/plan-work`" in skill
    assert "Do not resolve it unilaterally" in skill

    # Independent review is reused, not reinvented, and is never self-review.
    assert "refinement-reviewer" in skill and "refinement-reviewer" in reviewer
    assert "Never present the main chat's own refinement as an independent review" in skill
    assert "Do not alter the Story, requirements, source code, Jira records, or Git state" in reviewer

    # The technical template supplements, never replaces, business acceptance
    # criteria, and bans fabricated completeness.
    assert "does not replace them" in template
    assert "Do not invent a file path" in template
    assert "architecture-decisions.md" in skill
    assert "Persist a new or superseded entry only after the existing approval" in skill
    assert "A routine implementation choice is not an ADR" in skill
    assert "minimum index and module navigation-link edits" in skill
    assert "Do not start `/sync-context` to finish that handoff" in skill
    assert "report partial completion" in skill
    assert "unprotected existing behavior that needs characterization" in template
    assert "TAC-01" in template
    assert "criterion-ids.md" in skill
    assert "Characterization of existing behavior" in skill
    assert "Technical acceptance criteria" in template
    assert "keep publication pending" in template
    assert "Do not leave them only in the chat" in template
    assert "Identified and writable" in template
    assert "Confirmed absent" in template
    assert "Exists but not writable" in template
    assert "Do not write to a field Jira will reject" in template
    assert "identified and writable" in approval_contract
    assert "never an assumed Description fallback" in approval_contract
    assert "A missing parent is not the same as missing approval" in skill
    assert "technical acceptance criteria were persisted" in skill
    assert "description section named Technical acceptance criteria" in implement_change

    # implement-change can consume a refined technical item, not only a
    # Story, and follows the recorded business source rather than assuming
    # the Jira parent holds the requirements.
    assert "or the refined technical Task or Subtask" in implement_change
    assert "the technical item supplements them, it does not replace them" in implement_change
    assert "The Jira parent is not assumed to be that source" in implement_change
    assert "Do not treat every dependency link as the business source" in implement_change

    # Review readiness gates publication. A fast skip is legitimate.
    # Standard or deep review that cannot run stays pending.
    assert "required review stays pending" in skill
    assert "Developer approval of the payload does not waive required review" in skill
    assert "review that affected scope again before publication" in skill

    # Business source is distinct from the Jira parent, and a Subtask is
    # never parented under an Epic.
    assert "Do not treat every dependency link as the business source" in skill
    assert "Do not parent a Subtask under an Epic" in template
    assert "Business source" in template
    drift = flat("references/modes-and-drift.md")
    assert "Before publication" in drift
    assert "Do not rescan the entire repository because an unrelated file changed" in drift

    # Shared Jira instructions defer the approver to the calling skill.
    jira = " ".join(
        (ROOT / "references" / "jira-integration.md").read_text(encoding="utf-8").split()
    )
    assert "the approver the calling skill authorizes" in jira
    assert "the payload the Product Owner approves" not in jira

    # refine-story uses the shared Canvas contract.
    assert "canvas-review.md" in skill
    canvas = " ".join(
        (ROOT / "references" / "canvas-review.md").read_text(encoding="utf-8").split()
    )
    assert "/refine-story`" in canvas or "`/refine-story`" in canvas


def test_implement_and_validate_change_contract_has_required_language() -> None:
    """Structural markers only. Does not prove Cursor invoked Bugbot, dispatched
    a validator agent, applied a fix, or continued from implement-change into
    validate-change."""
    def flat_skill(name: str) -> str:
        return " ".join(
            (ROOT / ".cursor" / "skills" / name / "SKILL.md")
            .read_text(encoding="utf-8")
            .split()
        )

    implement = flat_skill("implement-change")
    validate = flat_skill("validate-change")
    risk = " ".join(
        (
            ROOT
            / ".cursor"
            / "skills"
            / "implement-change"
            / "references"
            / "risk-and-specialists.md"
        )
        .read_text(encoding="utf-8")
        .split()
    )
    evidence = " ".join(
        (
            ROOT
            / ".cursor"
            / "skills"
            / "validate-change"
            / "references"
            / "evidence-and-bugbot.md"
        )
        .read_text(encoding="utf-8")
        .split()
    )
    verification = " ".join(
        (ROOT / "references" / "verification-evidence.md")
        .read_text(encoding="utf-8")
        .split()
    )
    reviewer = " ".join(
        (ROOT / "agents" / "implementation-reviewer.md").read_text(encoding="utf-8").split()
    )
    validator_agent = " ".join(
        (ROOT / "agents" / "validator.md").read_text(encoding="utf-8").split()
    )
    composition = " ".join(
        (ROOT / "references" / "skill-composition.md").read_text(encoding="utf-8").split()
    )
    manual = (ROOT / "MANUAL_EVALUATION.md").read_text(encoding="utf-8")

    assert "approved deliverable and its own content" in implement
    assert "Do not depend on refine-story mode metadata" in implement
    assert "Ask only when development work and QA work cannot be distinguished" in implement
    assert "QA item is not included" in implement
    assert "approach review mode" in implement
    assert "before writing code" in implement
    assert "wait for its result" in implement
    assert "leave the affected scope pending" in implement
    assert "Do not edit the gated scope while that review is pending" in implement
    assert "Presence of Terraform or IAM" in implement
    assert "is not that trigger" in implement
    assert "Do not treat file paths as belonging to one Story" in implement
    assert "authorized continuing into validation" in implement
    assert "Do not run `terraform apply`" in implement
    assert "verification-evidence.md" in implement
    assert "exercise versus replace" in implement
    assert "Do not reset, clean, or move unrelated changes" in implement
    assert "Do not call a failure pre-existing without evidence" in implement
    assert "verification close-out" in implement
    assert "does not own independent validation or Bugbot" in implement
    assert "Do not invent those statuses" in implement
    assert "An implementation-only close-out is not delivery-ready validation" in implement

    assert "authorized that successor workflow" in validate
    assert "does not require an extra `/implement-change` slash command" in validate
    assert "repository preflight" in validate
    assert "review only, or no modifications" in validate
    assert "propose targeted fixes and do not apply them" in validate
    assert "preserve unrelated staged, unstaged, and untracked" in validate
    assert "without asking the user to request it again" in validate
    assert "not-applicable** only with a concrete reason" in validate or "not-applicable only with a concrete reason" in validate
    assert "same failing check returns without material progress" in validate
    assert "Do not change tests so they pass by dropping the expected behavior" in validate
    assert "An execution error is not a code finding" in validate
    assert "A partial review is not passed" in validate
    assert "no bugs is not evidence that acceptance criteria passed" in validate
    assert "Static contract tests in this plugin do not prove that Bugbot was invoked" in validate
    assert "do not prove that a validator agent was invoked" in validate
    assert "ready for the developer to deliver" in validate
    assert "does not commit" in validate
    assert "what each check actually demonstrates" in validate
    assert "Passing mocks do not prove deployed integration" in validate
    assert "Do not generate a new end-to-end suite" in validate
    assert "e2e-environment.md" in validate
    assert "pre-existing failure with baseline evidence" in validate
    assert "new independent `validator` delegation" in validate or "new independent validator delegation" in validate
    assert "changed dependency manifests, public contracts, migrations" in validate
    assert "prior evidence matrix" in validate
    assert "every acceptance criterion" in validate
    assert "Do not treat a delta-only result as complete validation" in validate
    assert "independent validation pending" in validate
    assert "does not evaluate its own conclusions" in validate
    assert "when a second evidence pass reduces uncertainty" not in validate
    assert "this chat does not evaluate its own conclusions" in implement
    assert "requirement-snapshot.md" in implement
    assert "architecture-decisions.md" in implement
    assert "Copy each binding clause exactly" in implement
    assert "Extract with `--repository-id` and `--root`" in implement
    assert "Qualify each decision id with the persisted repository ID" in implement
    assert "is unsupported, or its navigation link is missing" in implement
    assert "work-record.md" in implement
    assert "characterization of unprotected existing behavior" in implement
    assert "model-evaluation.md" in implement
    assert "closeout-validate" in validate
    assert "snapshot-compare" in validate
    assert "architecture-decisions.md" in validate
    assert "Extract with `--repository-id` and `--root`" in validate
    assert "clause-changed" in validate
    assert "An unreadable or unsupported architecture source is `not-compared`" in validate
    assert "requirement-snapshot.md" in validate
    assert "work-record.md" in validate
    assert "approved evaluation contract" in validate
    assert "does not inherit this chat" in validate or "Do not assume the independent validator inherits" in validate
    assert "optional Jira comment" in validate
    assert "artifacts/tickets" not in validate
    assert "If you must rely on coordinator-supplied snapshot text" in validator_agent
    assert "approved constraint" in validator_agent
    assert "architecture decision sources directly" in validator_agent
    assert "Copy each binding clause exactly" in validator_agent
    assert "owning repository id and authorized root" in validator_agent
    assert "model-evaluation.md" in validator_agent
    assert "Do not assume you inherited the coordinator" in validator_agent
    assert "only when the change affects model" in validator_agent
    assert "approved evaluation contract" in validator_agent

    assert "material new decision" in risk
    assert "Presence of Terraform or IAM" in risk
    assert "is not enough" in risk
    assert "Do not use this reviewer as a substitute for Bugbot" in risk
    assert "Request an independent `implementation-reviewer` assessment before validation" not in risk

    assert "execution-error" in evidence
    assert "without asking the user to request it again" in evidence
    assert "used only with a concrete reason" in evidence
    assert "A launch of Bugbot in another chat does not count" in evidence
    assert "This plugin cannot invoke Bugbot programmatically" not in evidence
    assert "Passing mocks do not prove deployed integration" in evidence

    assert "does not prove behavior it replaced with a fake" in verification
    assert "A separate QA item does not remove" in verification
    assert "Do not impose a mocking library" in verification
    assert "Do not ask for cloud credentials" in verification
    assert "Do not create a verification-plan file" in verification
    assert "does not own independent validation or Bugbot" in verification
    assert "Independent validation pending does not apply to an implementation-only run" in verification
    assert "An implementation-only close-out is not delivery-ready validation" in verification
    assert "inspected revision and uncommitted state" in verification
    assert "Name covered scope and limitations" in verification
    assert "Characterization of existing behavior" in verification
    assert "Do not freeze a known bug as an approved requirement" in verification
    assert "closeout-validate" in verification
    assert "Do not call a failure pre-existing without evidence" in verification
    assert "Do not limit the check to failures a Jira field listed verbatim" in verification
    assert "even if the user did not name those files" in verification
    assert "Do not claim the change broke nothing outside that scope" in verification
    assert "even if the user did not name those files" in implement
    assert "Do not add a new journey, a first suite, or a framework" in implement
    assert "before modifying or executing" in implement
    assert "including this baseline" in implement
    assert "only when an existing end-to-end spec must change" not in implement

    assert "Approach review mode" in reviewer
    assert "Scaffolding review mode" in reviewer
    assert "Default implementation review" in reviewer
    assert "does not replace scaffolding review mode" in reviewer
    assert "Do not invent a code review when no new implementation exists" in reviewer
    assert "must be resolved before the affected scope is edited" in reviewer

    assert "The implementer's summary is not proof" in validator_agent
    assert "verified**, **failed**, **pending**, or **not-verifiable" in validator_agent or "verified, failed, pending, or not-verifiable" in validator_agent
    assert "Do not launch Bugbot" in validator_agent
    assert "end-to-end environment" in validator_agent
    assert "Do not modify code, tests, requirements" in validator_agent
    assert "dependency manifests, public contracts, migrations" in validator_agent
    assert "even if no acceptance criterion names them" in validator_agent
    assert "When a shared file changed" in validator_agent
    assert "inspected revision and local changes" in validator_agent
    assert "checks that did not run" in validator_agent
    assert "covered scope and limitations" in validator_agent
    assert "prior evidence matrix" in validator_agent
    assert "Cover every acceptance criterion" in validator_agent

    assert "only authorized continuous-flow exception" in composition
    assert "`/implement-change` continuing into `/validate-change`" in composition
    assert "No other skill pair is started this way" in composition
    assert "stay handoffs" in composition
    assert "Do not generalize this exception" in composition
    assert "create-e2e-tests` is never started this way" in composition
    assert "always dispatches an independent `validator`" in composition
    assert "A self-check in the implementing chat is not independent validation" in composition
    assert "dispatches an independent `implementation-reviewer`" in composition
    assert "A self-check in the scaffolding chat is not independent review" in composition
    assert "A paragraph claiming a review ran is not the review" in composition
    assert "Writing `BUGBOT.md` is not the Bugbot run" in composition
    assert "Naming another skill or showing its slash command does not execute it." in (
        ROOT / "references" / "skill-composition.md"
    ).read_text(encoding="utf-8")

    for scenario in (
        "Implement-change DEV subtasks from instruction without extra confirmation",
        "Implement-change asks only when DEV and QA cannot be distinguished",
        "Implement-change skips approach review when the refinement still covers the approach",
        "Implement-change approach review runs before code for a material new decision",
        "Implement-change then validate-change authorized continuation",
        "Implement-change close-out does not invent validator or Bugbot status",
        "Plugin discovery in Cursor",
        "Implement-change continues into validate-change in Cursor",
        "Validate-change in-run fix stays in authorized functional scope",
        "Validate-change stops when the same failure shows no progress",
        "Validate-change Bugbot records the code it actually reviewed",
        "Validate-change always dispatches an independent validator",
        "Validate-change reports independent validation pending when delegation is unavailable",
        "Validate-change fix starts a new independent review of the delta",
        "Implement-change blocking or unavailable approach review prevents affected edits",
        "Validate-change standalone run preserves unrelated changes",
        "Validate-change review-only never edits",
        "Validate-change code changes trigger Bugbot by default",
        "Unrelated skill transitions remain handoffs",
        "Implement-change records a test baseline before edits",
        "Implement-change approach names real versus replaced components",
        "Implement-change still adds development tests when a QA item exists",
        "Implement-change does not call a failure pre-existing without evidence",
        "Validate-change treats passing fakes as insufficient for client composition",
        "Validate-change inspects manifests, contracts, and shared files even when no criterion names them",
        "Validate-change classifies failures instead of only rerunning the author suite",
        "Requirement snapshot ignores assignee and sprint",
        "Requirement drift blocks ready-to-deliver",
        "Implement-change adds characterization tests for unprotected behavior",
        "Approved NFR outside the AC heading are still evaluated",
        "Initial scaffold with approved architectural choices",
        "Existing architecture documentation reused",
        "Significant refinement decision versus routine implementation detail",
        "Requirement or design conflict with an accepted decision",
        "Changed approved architecture decision",
        "Multi-repo shared decision without duplication",
        "Architecture source inaccessible during validation",
        "Homonymous ADR ids in two repositories",
        "Existing criterion identifiers are preserved",
        "Validate-change invokes closeout-validate before claiming ready",
        "Validate-change offers an optional Jira comment after the result",
        "Model evaluation loads only when the change affects a model",
        "Create-e2e-tests discovers the environment before assuming one",
        "Create-e2e-tests distinguishes environment classes",
        "Create-e2e-tests does not force browser tests on a service without UI",
        "Create-e2e-tests remote execution needs an authorized target",
        "Validate-change runs existing E2E but does not generate a suite",
        "Implement-change updates existing E2E without named files",
        "Implement-change hands off new E2E authorship",
        "Implement-change loads the E2E environment contract before running existing coverage",
    ):
        assert scenario in manual, scenario


def test_create_e2e_tests_contract_has_required_language() -> None:
    """Structural markers only. Does not prove the agent discovered a
    consumer environment or executed a browser journey."""
    skill = " ".join(
        (ROOT / ".cursor" / "skills" / "create-e2e-tests" / "SKILL.md")
        .read_text(encoding="utf-8")
        .split()
    )
    environment = " ".join(
        (ROOT / "references" / "e2e-environment.md").read_text(encoding="utf-8").split()
    )
    composition = (ROOT / "references" / "skill-composition.md").read_text(
        encoding="utf-8"
    )

    assert "e2e-environment.md" in skill
    assert "Discover the environment before assuming one" in skill
    assert "locally executable application" in skill
    assert "simulated backend" in skill
    assert "Playwright is a candidate" in skill
    assert "Do not force browser tests onto a service with no UI" in skill
    assert "Creating a test is not the same as a successful execution" in skill
    assert "does not run this skill" in skill
    assert "Do not run against production by default" in skill
    assert "A test-runner container is not the application stack" in skill

    assert "Do not assume a local application" in environment
    assert "A configuration file does not prove" in environment
    assert "webServer" in environment
    assert "Do not invent selectors" in environment
    assert "Having a URL, credentials, or access does not" in environment
    assert "Do not install Docker" in environment
    assert "does not start `/create-e2e-tests`" in environment
    assert "independent validator in `/validate-change`" in environment
    assert "create-e2e-tests` is never started this way" in composition
    assert "This skill owns new journeys" in skill
    assert "may update an existing end-to-end spec" in environment
    assert "locally invoked runner" in environment
    assert "only when an existing end-to-end spec must change" not in environment


def test_canvas_review_is_the_closing_view() -> None:
    canvas = " ".join(
        (ROOT / "references" / "canvas-review.md").read_text(encoding="utf-8").split()
    )
    sync = " ".join(
        (ROOT / ".cursor" / "skills" / "sync-context" / "SKILL.md")
        .read_text(encoding="utf-8")
        .split()
    )
    assert "sync-context-result.canvas.tsx" in canvas
    assert "plan-work-result.canvas.tsx" in canvas
    assert "not a second source of truth" in canvas
    assert "Cursor agents cannot open a Canvas today" not in canvas
    assert "illustrative, descriptive, kebab-case name, not a required literal filename" in canvas
    assert "genuinely benefits from a visual, interactive, or structured view" in canvas
    assert "do not open or refresh a Canvas just to report that nothing changed" in canvas
    assert "Stage 7 is still shown" in sync
    assert "canvas-review.md" in sync


def test_manual_evaluation_covers_context_quality_scenarios() -> None:
    manual = " ".join(
        (ROOT / "MANUAL_EVALUATION.md").read_text(encoding="utf-8").split()
    )
    assert "nine quality dimensions" in manual
    for scenario in (
        "Small single-file utility or library module",
        "REST/HTTP API service with an external integration",
        "Event-driven or asynchronous background worker",
        "Frontend or UI application module",
        "Infrastructure-as-code or Terraform repository",
        "Monorepo with several independent packages",
        "Multi-repository engagement",
        "Repository with stale or misleading prior context",
        "Repository with a security- or payment-sensitive module",
        "Repository with heavy persistence and several external integrations",
    ):
        assert scenario in manual
    for regression in (
        "Shallow service context",
        "False completeness",
        "Length gaming",
        "Honest unknown must beat invented behavior",
    ):
        assert regression in manual
    for hardening in (
        "A. Behaviorful single-module service",
        "B. Truly trivial repository",
        "C. Rich architecture preservation",
        "D. Secret safety",
        "E. Evidence catalog",
        "F. Honest partial coverage",
        "Material architecture details",
        "empty `## Modules` table",
        "Reviewer unavailable",
        "Empty structural context",
        "Evidence catalog missing",
        "Evidence exists but no local paths",
        "REST/backend service",
    ):
        assert hardening in manual


def test_legacy_aidlc_migration_contract_is_specific() -> None:
    legacy = " ".join(
        (ROOT / ".cursor/skills/sync-context/references/legacy-migration.md")
        .read_text(encoding="utf-8")
        .split()
    )
    skill = (ROOT / ".cursor/skills/sync-context/SKILL.md").read_text(encoding="utf-8")
    manual = (ROOT / "MANUAL_EVALUATION.md").read_text(encoding="utf-8")
    for phrase in (
        "Known legacy AI-DLC installation",
        "This detection does not classify repository role.",
        "detect_legacy_aidlc_installation",
        "resolve_legacy_provenance",
        "legacy_architecture_prompt_required",
        "legacy_supporting_evidence",
        "legacy_inventory_fingerprint",
        "legacy_inventory_needs_approval",
        "legacy_baseline_comparison",
        "inspection-unavailable",
        "historical_content_blocks_checkout_deletion",
        "classify_legacy_ci_workflow",
        "legacy_standard_file_treatment",
        "retain-active-coordinator",
        "does not publish to Jira",
        "not a copy of the global map",
        "If Jira cannot be inspected, report that verification as unavailable",
    ):
        assert phrase in legacy
    assert "Known legacy AI-DLC installation" in skill
    assert "The Python helpers do not execute this skill." in manual


def test_scaffold_project_contract_has_required_language() -> None:
    skill = " ".join(
        (ROOT / ".cursor" / "skills" / "scaffold-project" / "SKILL.md")
        .read_text(encoding="utf-8")
        .split()
    )
    foundation = " ".join(
        (
            ROOT
            / ".cursor"
            / "skills"
            / "scaffold-project"
            / "references"
            / "foundation-and-review.md"
        )
        .read_text(encoding="utf-8")
        .split()
    )
    reviewer = " ".join(
        (ROOT / "agents" / "implementation-reviewer.md").read_text(encoding="utf-8").split()
    )
    manual = (ROOT / "MANUAL_EVALUATION.md").read_text(encoding="utf-8")
    for phrase in (
        "directory without a Git root",
        "Git repository without a remote",
        "established identity",
        "Never fabricate a remote",
        "do not initialize Git to satisfy context validation",
        "whether HEAD resolves to a commit",
        "no-commit",
        "If it returns false",
        "Once, before applying the approved change set",
        "do not compare the evolving source tree",
        "approved writes are expected",
        "must still be absent",
        "already applied",
        "do not claim the writes were atomic",
        "minimal entrypoint",
        "safe example values",
        "A library does not need an application server",
        "documentation-only foundation",
        "Do not run it blindly",
        "narrowly scoped edit",
        "validate_generated_context",
        "mechanically valid context",
        "source-supported prose",
        "not executable",
        "implementation-reviewer",
        "documented review skip",
        "do not label a self-review as independent",
        "A generated file tree alone does not prove the foundation works",
        "Review completion does not replace executable validation",
        "references/foundation-and-review.md",
        "architecture-decisions.md",
        "Before identifying a stack, establish the product's purpose",
        "references/product-purpose.md",
        "allow an explicit generic-starter choice instead of inventing a purpose",
        "untracked-tree",
        "not merely a sibling repository confirmed as part of one product",
        "Confirming product membership for a new, separate sibling repository never adopts",
        "Open the proposal with the confirmed purpose summary",
        "whether it is user-selected, a verified constraint, or a recommendation that still needs approval",
        "Give the reviewer the confirmed purpose and the scaffolding boundary",
        "When the requested outcome includes real business behavior beyond a technical foundation",
        "/plan-work",
        "Resolve the project's repository organization",
        "Do not assume that having a frontend, a backend, and infrastructure by itself requires separate repositories",
        "do not ask again",
        "This skill scaffolds one destination safely per run",
        "Creating a project directory is not creating a Git repository",
        "separate from repository organization",
        "do not claim a deferred or not-yet-created folder is ready to open",
        "do not introduce a Cloud Agent environment or claim it controls cloud repository cloning",
        "which repositories or directories already exist versus which this run will create",
        "destination_freshness",
        "untracked-tree",
    ):
        assert phrase in skill, phrase
    for phrase in (
        "Directory without a Git root",
        "Git repository without a remote",
        "Established identity",
        "minimum index and module navigation links",
        "Do not start `/sync-context` to finish that handoff",
        "report partial completion",
        "content_fingerprint",
        "stable_repository_id",
        "no-commit",
        "Record that revision only when it resolves",
        "expected unborn HEAD",
        "broken or inaccessible",
        "Do not classify that working tree as a directory without Git",
        "Do not ask for a new one merely because no remote exists",
        "Evaluate each proposed `Related repository` entry",
        "referenced repository's canonical remote",
        "payments-api",
        "Defer only the entry whose target remote cannot be established",
        "proposal_is_current",
        "do not compare the evolving source tree",
        "Creating an approved source file changes `content_fingerprint`",
        "must still be absent",
        "already applied",
        "do not claim the writes were atomic",
        "Mechanically valid",
        "Source-supported prose",
        "Not executable",
        "documented review skip",
        "general-purpose independent review",
        "missing entrypoint",
        "Untracked tree inside an enclosing Git root",
        "`untracked-tree` kind",
        "Confirmed new module of an existing monorepo",
        "never inferred from location alone",
        "not merely a sibling repository confirmed as part of one product",
        "it only governs `Related repository` entries",
        "does not grant this destination the enclosing repository's identity",
        "Never run `git init`, stage files, or otherwise modify the enclosing repository",
        "does not use the enclosing repository's exclude rules",
        "A genuinely empty destination still has an empty fingerprint",
        "report freshness as unresolved",
        "destination_freshness",
        "The scope kind `untracked-tree` is not the kind `unversioned`",
        "explicitly named shared file",
        "Membership in the monorepo does not authorize an arbitrary edit at the repository root",
        "Repository organization and workspace",
        "track three distinct sets",
        "state that limit instead of writing files across several repository roots in one pass",
        "is never itself proof that a Git repository exists there",
        "this section does not restate them",
    ):
        assert phrase in foundation, phrase
    templates = (
        ROOT
        / ".cursor"
        / "skills"
        / "sync-context"
        / "references"
        / "context-templates.md"
    ).read_text(encoding="utf-8")
    assert "Baseline and fingerprint: `<git revision, no-commit, or unversioned>`" in templates
    assert "Do not put `no-commit` on a tree" in templates
    purpose = " ".join(
        (
            ROOT
            / ".cursor"
            / "skills"
            / "scaffold-project"
            / "references"
            / "product-purpose.md"
        )
        .read_text(encoding="utf-8")
        .split()
    )
    for phrase in (
        "what is being built, and what problem it solves",
        "human users and their roles, or system and API consumers",
        "Reuse a fact already supplied",
        "Do not infer authentication, a database, a payment flow, an AI agent, a queue, or infrastructure merely from a broad category",
        "allow that choice",
        "a technical foundation",
        "a navigable prototype",
        "a working business feature",
        "hand off to `/plan-work`",
        "Do not require Jira access or a complete business model",
        "a technology the user explicitly selected",
        "a recommendation that still needs approval",
        "Do not claim an earlier run invented a stack merely because its transcript is incomplete",
        "Do not add a second reviewer",
    ):
        assert phrase in purpose, phrase
    assert "Scaffolding review mode" in reviewer
    assert "Do not modify code, tests, Jira, Git state" in reviewer
    assert "missing entrypoint" in reviewer
    assert "Do not request speculative architecture" in reviewer
    assert "the confirmed product purpose and the scaffolding boundary" in reviewer
    assert "a backend or datastore generated for a purpose stated as static-only" in reviewer
    assert reviewer.count("Do not modify code, tests, Jira, Git state") >= 1
    for scenario in (
        "Empty directory without a Git root",
        "Existing Git repository without a remote",
        "Git working tree without commits and without a remote",
        "Git working tree without commits but with a configured remote",
        "New project without a remote referencing a confirmed sibling",
        "Referenced repository whose remote is unavailable",
        "Existing persisted repository identity remains unchanged",
        "Bounded addition to an existing monorepo",
        "Approved creation then an approved manifest edit",
        "External edit before the manifest write",
        "Path expected to be absent already exists",
        "Partial apply reported honestly",
        "Independent reviewer unavailable",
        "Real defect caught during review",
        "Scaffold-project always dispatches independent reviewers",
        "Scaffold-project code changes trigger Bugbot by default",
        "Scaffold-project does not skip Bugbot after reviewer findings",
        "Generic product request with no detail",
        "Detailed request already supplies the facts",
        "Explicitly generic starter",
        "Static website does not gain a backend",
        "Standalone folder inside an unrelated parent Git repository",
        "Explicitly requested new module inside an existing monorepo",
        "New module plus an approved root workspace manifest",
        "Organization already specified",
        "Organization unspecified",
        "Existing multi-repo product offers a workspace",
        "New multi-repo product separates directories from Git setup",
        "Monorepo does not require a workspace",
        "Fresh scaffold with approved Bugbot setup",
        "Declined setup without repeated questions",
        "Existing BUGBOT.md preserved",
        "Insufficient evidence for useful rules",
        "Reviewer source fix followed by context refresh",
        "Independent delegation or Canvas unavailable",
        "New module added without dropping existing monorepo index entries",
        "Scaffold offers a pull-request template independently",
        "Existing pull-request template is preserved",
        "Unknown Git host defers a pull-request template",
        "GitLab remote does not write a GitHub template path",
        "Bitbucket Cloud offers `.bitbucket/pull_request_template.md`",
        "GitHub path containing gitlab is not GitLab",
        "Bitbucket Server host stays unknown",
        "Sync-context still detects set B without always loading those contracts",
        "Sync-context declined policy does not silence another policy in the same repository",
        "Declined pull-request template is not re-asked in the same run",
        "Sync-context can offer a pull-request template when source is unchanged",
    ):
        assert scenario in manual, scenario


def test_plan_work_story_model_separates_semantics_from_rendering() -> None:
    """Structural markers only. Does not prove agent behavior, publication
    quality, or Product Owner judgment."""
    plan_dir = ROOT / ".cursor" / "skills" / "plan-work" / "references"

    def flat(name: str) -> str:
        return " ".join((plan_dir / name).read_text(encoding="utf-8").split())

    story = flat("single-story.md")
    template = flat("jira-story-template.md")

    for marker in (
        "Testing and validation expectations",
        "must not introduce a new required behavior",
        "Omit Testing entirely",
        "refine-story",
    ):
        assert marker in story, marker
    for marker in (
        "Validation Notes",
        "must not introduce new product behavior",
        "reader-facing placeholders",
        "never count as completed or approved requirements",
    ):
        assert marker in template, marker

    for marker in (
        "Story-specific goals and metrics",
        "exception, not the default",
        "Do not infer, derive, or invent a metric",
    ):
        assert marker in story, marker
    assert "omit-empty-optional-sections" in template

    for marker in (
        "Open questions and ambiguity",
        "user-facing",
        "cannot access",
    ):
        assert marker in story, marker
    assert "order-history" not in story.lower()

    for marker in (
        "Design reference",
        "Do not invent a design reference",
        "do not claim inspection",
        "universal blocker",
        "project-level Figma URL",
    ):
        assert marker in story, marker
    for marker in (
        "Design / References",
        "Do not discover, infer, or inspect",
    ):
        assert marker in template, marker
    assert "Story-specific design" in flat("update-existing.md")

    for marker in (
        "Semantic precedence",
        "Do not silently decide",
    ):
        assert marker in story, marker

    for marker in (
        "does not define it",
        "information loss",
        "Scope / Out of Scope",
        "Do not invent scope or exclusions",
    ):
        assert marker in template, marker
    assert "must survive that publication" in story
    assert "empty state versus error state" in story

    for marker in (
        "do not block independent review",
        "Do not run a universal questionnaire",
        "must not be asked twice",
        "confirmed, assumed, or proposed",
        "ready to implement",
    ):
        assert marker in story, marker
    for marker in (
        "confirmed absent",
        "Never publish operational disclaimers",
        "Identified and writable",
        "Exists but not writable",
        "approved destination for acceptance criteria",
    ):
        assert marker in template, marker

    manual = (ROOT / "MANUAL_EVALUATION.md").read_text(encoding="utf-8")
    for scenario in (
        "Plan-work Validation Notes placeholder when they only restate ACs",
        "Plan-work valid extra validation scenario",
        "Plan-work Testing cannot introduce new behavior",
        "Plan-work Goals placeholder without a metric",
        "Plan-work explicit Story-level metric preserved",
        "Plan-work ambiguous status surfaces an Open Question",
        "Plan-work ambiguous unauthenticated access uses evidence then asks",
        "Plan-work Story-specific design reference included",
        "Plan-work project-level Figma is not copied into the Story",
        "Plan-work design versus AC conflict is surfaced",
        "Plan-work approved scope exclusions survive the Jira payload",
        "Plan-work existing Story-specific design link survives update-existing",
        "Plan-work supplied design link is not described as inspected without access",
        "Project-rule declined policy does not suppress another policy in the same repository",
        "Plan-work AC field available is not duplicated in Description",
        "Plan-work confirmed missing AC field uses Description fallback",
        "Plan-work inaccessible AC metadata is not treated as absent",
        "Plan-work AC field exists but is not writable",
        "Plan-work custom template still carries every AC",
        "Plan-work review runs with open product questions",
        "Plan-work reviewer Blocker leaves the item blocked",
        "Refine-story AC field exists but is not writable",
        "Plan-work does not re-ask a decision already answered on another Story",
        "Plan-work independent review findings are visible to the Product Owner",
    ):
        assert scenario in manual, scenario


def test_project_rule_decisions_are_keyed_by_repository_and_policy() -> None:
    """Structural markers only. Does not prove the agent looks up persisted
    Markdown or that renaming a rule file is handled at runtime."""
    project_rules = (
        ROOT
        / ".cursor"
        / "skills"
        / "sync-context"
        / "references"
        / "project-rules.md"
    ).read_text(encoding="utf-8")
    artifact_home = (
        ROOT
        / ".cursor"
        / "skills"
        / "sync-context"
        / "references"
        / "artifact-home.md"
    ).read_text(encoding="utf-8")
    foundation = (
        ROOT
        / ".cursor"
        / "skills"
        / "scaffold-project"
        / "references"
        / "foundation-and-review.md"
    ).read_text(encoding="utf-8")

    for phrase in (
        "## Project rule decisions",
        "stable repository ID, stable policy slug",
        "`Rule` is optional metadata",
        "different policy slug",
    ):
        assert phrase in project_rules, phrase

    assert "stable policy" in artifact_home and "slug" in artifact_home
    assert "## Project rule decisions" in artifact_home
    assert "## Pull request template decisions" in artifact_home

    assert "stable repository ID, stable policy slug" in foundation
    pr_template = (
        ROOT
        / ".cursor"
        / "skills"
        / "sync-context"
        / "references"
        / "pull-request-template.md"
    ).read_text(encoding="utf-8")
    assert "Identity is the stable repository ID" in pr_template
    assert "not a project-rule slug" in pr_template


def test_scaffold_project_completes_its_own_review_configuration() -> None:
    """Scaffold-project reuses Bugbot/project-rule/context-review contracts
    by reference instead of inventing a second setup flow or a second
    reviewer, and makes the final-validation ordering explicit."""
    skill = (
        ROOT / ".cursor" / "skills" / "scaffold-project" / "SKILL.md"
    ).read_text(encoding="utf-8")
    foundation = (
        ROOT
        / ".cursor"
        / "skills"
        / "scaffold-project"
        / "references"
        / "foundation-and-review.md"
    ).read_text(encoding="utf-8")
    canvas = (ROOT / "references" / "canvas-review.md").read_text(encoding="utf-8")

    for phrase in (
        "bugbot-configuration.md",
        "project-rules.md",
        "review-handoff.md",
        "repository review configuration",
        "independent context review",
        "finalization order",
        "the user should not need to run `sync-context` immediately after this skill",
        "context-reviewer",
        "after steps 10 and 11, not before them",
        "The stored `Fingerprint:` value is `content_fingerprint` of the declared scope, not `destination_freshness`",
        "pull-request template status (created, unchanged, declined, not applicable, or deferred)",
        "Do not assume GitHub",
        "pull-request-template.md",
        "project-rule status (created, unchanged, declined, not applicable, or deferred)",
        "Bugbot review guidance status (created, unchanged, declined, or deferred)",
        "Start a new independent `implementation-reviewer` delegation",
        "Start a new independent `context-reviewer` delegation",
        "attempt the real supported Bugbot invocation",
        "do not prove that a reviewer agent was invoked",
        "do not prove that Bugbot was invoked",
        "Bugbot review of the generated code",
        "A paragraph in this chat claiming a review ran is not the review",
        "Do not treat writing `BUGBOT.md`, or explaining that it is later guidance, as a substitute for attempting Bugbot",
        "Independent scaffolding and context reviews are not Bugbot",
        "recompute the fingerprint and re-read the destination instead of reusing the read from before steps 10–11 ran",
        "step 11's result stays valid only when the refresh was mechanical",
    ):
        assert phrase in skill, phrase
    assert "Bugbot setup" not in skill

    for phrase in (
        "## Repository review configuration",
        "## Independent context review",
        "## Finalization order",
        "Do not freeze a placeholder's current response as a rule",
        "Record that outcome as `deferred`",
        "is different from an explicit `declined`",
        "does not install, enable, or configure the Bugbot service",
        "## Scaffold Bugbot review",
        "Writing `BUGBOT.md` is not a Bugbot review",
        "attempt the real supported Bugbot invocation",
        "Start a new independent `implementation-reviewer` delegation",
        "Start a new independent `context-reviewer` delegation",
        "A generated web app, API, infrastructure, or multi-component foundation is not that skip",
        "Do not treat writing `BUGBOT.md`, or explaining that it is later guidance, as a substitute for attempting Bugbot",
        "Independent scaffolding and context reviews are not Bugbot",
        "A paragraph in this chat claiming a review ran is not the review",
        "do not treat it as a reason to skip Bugbot",
        "is not excluded from `content_fingerprint`",
        "The persisted `Fingerprint:` field is `content_fingerprint` of the declared scope",
        "Do not store `destination_freshness` in `Fingerprint:`",
        "The reviewer may still read dependencies, consumers, and relevant configuration inside the authorized scope",
        "Do not rescan an unrelated repository",
        "Do not \"fix\" a stale fingerprint by replacing the stored hash",
        "Do not widen `EXCLUDED_PARTS` or `GENERATED_FILENAMES`",
        "validate_generated_context` once more, against the final files on disk",
        "This run's own approved writes in (a), (c), and (d) are expected inputs to (e)",
        "Mechanical versus semantic refresh",
        "the `context-reviewer` result from (c) stays valid",
        "Run one targeted `context-reviewer` follow-up on just that changed content",
        "This proposal is its own change set, prepared after steps 8–11 already wrote and reviewed other files",
        "Do not reuse the fingerprint read before steps 10–11 ran",
        "pull-request-template.md",
        "Do not assume GitHub",
        "If the host is unknown, record `deferred`",
        "approved pull-request template",
    ):
        assert phrase in foundation, phrase

    assert "`content_fingerprint` or `destination_freshness`" not in foundation
    assert "## scaffold-project" in canvas
    assert "Bugbot review of the generated code: passed, failed, pending, not-applicable, or unavailable" in canvas
    assert "architecture-decision record: created, linked to an existing location, unchanged, or not applicable" in canvas
    assert "Bugbot review guidance: created, unchanged, declined, or deferred" in canvas
    assert "project rules: created, unchanged, declined, not applicable, or deferred" in canvas
    assert "pull-request template: created, unchanged, declined, not applicable, or deferred" in canvas
    assert "Bugbot setup" not in canvas


def test_manual_evaluation_and_shared_contracts_exist() -> None:
    assert (ROOT / "MANUAL_EVALUATION.md").is_file()
    for filename in (
        "repository-preflight.md",
        "jira-integration.md",
        "skill-composition.md",
        "response-style.md",
        "context-retrieval.md",
        "project-onboarding.md",
        "approval-contract.md",
        "canvas-review.md",
        "verification-evidence.md",
        "e2e-environment.md",
        "work-record.md",
        "requirement-snapshot.md",
        "architecture-decisions.md",
        "criterion-ids.md",
        "model-evaluation.md",
    ):
        assert (ROOT / "references" / filename).is_file()
    assert not (ROOT / ".cursor" / "skills" / "plan-work" / "references" / "approval-contract.md").exists()
    work_record = " ".join(
        (ROOT / "references" / "work-record.md").read_text(encoding="utf-8").split()
    )
    assert "Do not create `artifacts/tickets/<ID>/`" in work_record
    assert "Markdown Story mirrors" in work_record
    snapshot = " ".join(
        (ROOT / "references" / "requirement-snapshot.md").read_text(encoding="utf-8").split()
    )
    assert "does not prove who approved" in snapshot
    assert "snapshot-compare" in snapshot
    assert "source_complete" in snapshot
    assert "Incomplete recovery never equals unchanged" in snapshot
    architecture = " ".join(
        (ROOT / "references" / "architecture-decisions.md").read_text(encoding="utf-8").split()
    )
    assert "Binding clause" in architecture
    assert "Do not use `relevant_decisions`" in architecture
    assert "web/ADR-001" in architecture
    assert "Do not add this file to `EXCLUDED_PARTS`" in architecture
    assert "--root" in architecture
    assert "unsupported" in architecture
    assert "Do not fall back to a basename" in architecture
    assert "same approved change set" in architecture
    assert "Do not start `/sync-context`" in architecture
    assert "Do not scan for an unlinked file" in architecture
    retrieval = " ".join(
        (ROOT / "references" / "context-retrieval.md").read_text(encoding="utf-8").split()
    )
    assert "treat architecture recovery as incomplete" in retrieval
    assert "do not scan for an unlinked file as a substitute" in retrieval
    manual = " ".join((ROOT / "MANUAL_EVALUATION.md").read_text(encoding="utf-8").split())
    assert "Refine writes a linked architecture record a later session can load" in manual
    assert "Static contract tests do not prove live agent execution" in manual
    ids = " ".join(
        (ROOT / "references" / "criterion-ids.md").read_text(encoding="utf-8").split()
    )
    assert "Do not create a parallel catalog in Git" in ids
    model = " ".join(
        (ROOT / "references" / "model-evaluation.md").read_text(encoding="utf-8").split()
    )
    assert "Load this reference only when" in model
    assert "must not execute models" not in model
    assert "Authorized evaluations may run" in model
    assert "need authorization" in model


def test_architecture_decision_write_to_retrieval_handoff_is_documented() -> None:
    """Static coverage for refine → linked record → later implement/validate.

    This does not prove live agent execution. It only checks that the
    plugin documents the same-change-set navigation-link handoff.
    """
    architecture = " ".join(
        (ROOT / "references" / "architecture-decisions.md").read_text(encoding="utf-8").split()
    )
    retrieval = " ".join(
        (ROOT / "references" / "context-retrieval.md").read_text(encoding="utf-8").split()
    )
    refine = " ".join(
        (ROOT / ".cursor" / "skills" / "refine-story" / "SKILL.md")
        .read_text(encoding="utf-8")
        .split()
    )
    foundation = " ".join(
        (
            ROOT
            / ".cursor"
            / "skills"
            / "scaffold-project"
            / "references"
            / "foundation-and-review.md"
        )
        .read_text(encoding="utf-8")
        .split()
    )
    implement = " ".join(
        (ROOT / ".cursor" / "skills" / "implement-change" / "SKILL.md")
        .read_text(encoding="utf-8")
        .split()
    )
    validate = " ".join(
        (ROOT / ".cursor" / "skills" / "validate-change" / "SKILL.md")
        .read_text(encoding="utf-8")
        .split()
    )
    manual = " ".join((ROOT / "MANUAL_EVALUATION.md").read_text(encoding="utf-8").split())
    assert "same approved change set adds the minimum navigation link" in architecture
    assert "Do not start `/sync-context` to finish that handoff" in architecture
    assert "Do not scan for an unlinked file as a substitute" in architecture
    assert "treat architecture recovery as incomplete" in retrieval
    assert "do not scan for an unlinked file as a substitute" in retrieval
    assert "minimum index and module navigation-link edits" in refine
    assert "Do not start `/sync-context` to finish that handoff" in refine
    assert "minimum index and module navigation links" in foundation
    assert "Extract with `--repository-id` and `--root`" in implement
    assert "navigation link is missing" in implement
    assert "unreadable or unsupported architecture source" in validate
    assert "Refine writes a linked architecture record a later session can load" in manual
    assert "Static contract tests do not prove live agent execution" in manual


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
        test_architecture_discovery_contract_has_required_language,
        test_context_review_fixture_documents_expected_findings,
        test_release_workflow_files_exist,
        test_project_onboarding_is_conditionally_referenced,
        test_plan_work_contract_has_required_language,
        test_plan_work_story_model_separates_semantics_from_rendering,
        test_refine_story_contract_has_required_language,
        test_implement_and_validate_change_contract_has_required_language,
        test_create_e2e_tests_contract_has_required_language,
        test_scaffold_project_contract_has_required_language,
        test_project_rule_decisions_are_keyed_by_repository_and_policy,
        test_scaffold_project_completes_its_own_review_configuration,
        test_canvas_review_is_the_closing_view,
        test_manual_evaluation_covers_context_quality_scenarios,
        test_legacy_aidlc_migration_contract_is_specific,
        test_manual_evaluation_and_shared_contracts_exist,
        test_architecture_decision_write_to_retrieval_handoff_is_documented,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
