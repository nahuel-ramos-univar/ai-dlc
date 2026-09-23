"""Structural checks for plugin layout and local references, not runtime behavior."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
EXPECTED_SKILLS = {
    "sync-context",
    "plan-work",
    "refine-story",
    "implement-change",
    "validate-change",
    "resolve-defect",
    "deliver-change",
    "check-governance",
}
EXPECTED_AGENTS = {
    "product-reviewer",
    "refinement-reviewer",
    "implementer",
    "implementation-reviewer",
    "validator",
    "governance-reviewer",
}
READONLY_AGENTS = EXPECTED_AGENTS - {"implementer"}
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
    for component in ("skills", "agents"):
        relative_path = Path(manifest[component])
        assert not relative_path.is_absolute()
        resolved = ROOT / relative_path
        assert resolved.is_dir()
        assert_within_root(resolved)


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
        assert metadata["name"] == path.parent.name
        assert metadata["description"]
        assert metadata["disable-model-invocation"] is True
        assert metadata["name"] not in names
        names.add(metadata["name"])
    assert names == EXPECTED_SKILLS


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
    for path in ROOT.rglob("*.md"):
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
    for skill_name in EXPECTED_SKILLS:
        skill = ROOT / ".cursor" / "skills" / skill_name / "SKILL.md"
        assert "../../../references/response-style.md" in skill.read_text(
            encoding="utf-8"
        )


def test_context_retrieval_contract_is_wired() -> None:
    retrieval = ROOT / "references" / "context-retrieval.md"
    assert retrieval.is_file()
    for skill_name in EXPECTED_SKILLS - {"sync-context"}:
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
    assert "<module-root>/AIDLC_CONTEXT.md" in generation
    assert "aidlc-docs/context/<repo-id>/<module-id>.md" in generation
    assert "replace any character outside `[a-z0-9]`" in generation
    assert "<consumer-root>/.cursor/BUGBOT.md" in generation
    assert "Never hash an absolute checkout path" in generation
    assert "Do not write absolute local checkout paths" in generation
    assert "do not write `aidlc-docs/` at a parent folder" in generation
    assert "Create `.ai-dlc-config.md`" in bugbot
    assert "## Context decisions" in bugbot
    assert "meaningful review boundary" in bugbot
    assert "Review only changed lines" in bugbot
    assert "Prefer silence over speculation" in bugbot
    assert "generated, vendor, build, coverage, lockfile, or fixture" in bugbot
    for scenario in (
        "Single-module repository",
        "Monorepo",
        "Multi-repository workspace",
    ):
        assert scenario in generation
    assert "Ask once per repository" in bugbot
    assert "declined" in bugbot


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
        test_team_marketplace_indexes_this_plugin,
        test_skill_frontmatter_and_unique_names,
        test_agent_frontmatter_and_readonly_boundaries,
        test_local_markdown_references_resolve,
        test_every_skill_uses_compact_response_style,
        test_context_retrieval_contract_is_wired,
        test_context_generation_contract_has_required_examples,
        test_manual_evaluation_and_shared_contracts_exist,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
