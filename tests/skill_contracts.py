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
    assert "freshness fingerprint" in refresh
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

    # Bugbot: the reviewer must not run or assume a standalone duplicate search.
    assert "duplicate candidates" not in reviewer
    assert "Do not search Jira for duplicates" in reviewer
    assert "not evidence that no duplicates exist" in reviewer
    assert "Do not pass a duplicate-candidates list" in product_review

    # Section 9: local plan approval never implies Jira mutation approval.
    assert "is never, by itself, approval to mutate Jira" in skill

    # Story description template: Markdown, offered once, acceptance
    # criteria stay out of the description body.
    assert "jira-story-template.md" in skill
    assert "## Planning template" in skill
    assert "decision_reprompt_allowed" in skill
    assert "Do not copy them into the description" in skill
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
    assert "plain-language relationship between draft identifiers" in flat("references/approval-contract.md")
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
    assert "Offer the template only when preparing the Jira publication payload" in story_template_flat
    assert "before a User Story description is drafted" not in story_template_flat
    single_story = flat("references/single-story.md")
    assert "Do not fill or offer" in single_story
    assert "When a Jira description is needed, fill the approved shape" not in single_story
    assert "Author the description in Markdown" in story_template_flat
    assert "Acceptance criteria are not part of the description" in story_template_flat
    assert "#### 📋 Description" in story_template
    assert "h4." not in story_template
    assert "|| Question ||" not in story_template
    assert "Do not hand-write Jira wiki markup" in jira
    assert "write acceptance criteria only in that field" in jira

    # Closing review uses the host Canvas capability when available, with an
    # equivalent chat fallback when the host cannot open one -- never a
    # hardcoded claim about which hosts can or cannot open a Canvas.
    assert "canvas-review.md" in skill
    assert "use the host Canvas capability when available" in skill
    assert "Cursor agents cannot open a Canvas today" not in skill


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


def test_manual_evaluation_and_shared_contracts_exist() -> None:
    assert (ROOT / "MANUAL_EVALUATION.md").is_file()
    for filename in (
        "repository-preflight.md",
        "jira-integration.md",
        "skill-composition.md",
        "response-style.md",
        "context-retrieval.md",
        "project-onboarding.md",
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
        test_architecture_discovery_contract_has_required_language,
        test_context_review_fixture_documents_expected_findings,
        test_release_workflow_files_exist,
        test_project_onboarding_is_conditionally_referenced,
        test_plan_work_contract_has_required_language,
        test_canvas_review_is_the_closing_view,
        test_manual_evaluation_covers_context_quality_scenarios,
        test_legacy_aidlc_migration_contract_is_specific,
        test_manual_evaluation_and_shared_contracts_exist,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
