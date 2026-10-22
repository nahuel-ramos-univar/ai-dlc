"""Checks for the AI-DLC explorer snapshot generator and refresh hook."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_aidlc_explorer import (  # noqa: E402
    extract_headings,
    extract_links,
    freshness_errors,
    generate,
    payload_paths,
    should_refresh_path,
    source_hash,
)


def test_headings_include_fenced_h1_to_h3_and_skip_h4() -> None:
    text = "\n".join(
        [
            "# Title",
            "```markdown",
            "## Inside fence",
            "#### Skipped",
            "```",
            "### Real h3",
        ]
    )
    assert extract_headings(text) == [
        {"text": "Title", "line": 1},
        {"text": "Inside fence", "line": 3},
        {"text": "Real h3", "line": 6},
    ]


def test_links_keep_indexed_relative_targets_including_fenced_ones() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        skill = root / "skill.md"
        target = root / "kept.md"
        ignored = root / "ignored.md"
        skill.write_text(
            "[kept](kept.md) [web](https://example.com) `see [also](kept.md#frag)` "
            "and ```see [fenced](kept.md) and [skip](ignored.md)```",
            encoding="utf-8",
        )
        target.write_text("# Kept\n", encoding="utf-8")
        ignored.write_text("# Ignored\n", encoding="utf-8")
        links = extract_links(skill, skill.read_text(encoding="utf-8"), root, {"kept.md"})
        assert links == ["kept.md"]


def test_source_hash_is_sha256_prefix() -> None:
    assert source_hash("hello") == "2cf24dba5fb0"


def test_hook_filters_plugin_source_and_skips_the_explorer() -> None:
    assert should_refresh_path(ROOT / ".cursor" / "skills" / "plan-work" / "SKILL.md", ROOT)
    assert should_refresh_path(ROOT / "references" / "architecture-decisions.md", ROOT)
    assert should_refresh_path(ROOT / ".cursor-plugin" / "plugin.json", ROOT)
    assert not should_refresh_path(ROOT / "documentation" / "aidlc-explorer.html", ROOT)
    assert not should_refresh_path(ROOT / ".cursor" / "hooks" / "refresh-aidlc-explorer.py", ROOT)
    assert payload_paths({"file_path": "README.md"}) == ["README.md"]
    assert payload_paths({"filePath": "agents/implementer.md"}) == ["agents/implementer.md"]


def _mini_plugin(root: Path) -> None:
    (root / ".cursor-plugin").mkdir()
    (root / ".cursor-plugin" / "plugin.json").write_text(
        '{\n  "name": "demo",\n  "version": "1.2.3"\n}\n',
        encoding="utf-8",
    )
    skill_dir = root / ".cursor" / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo skill.\n---\n\n"
        "# Demo skill\n\nSee [readme](../../../README.md).\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Demo package\n\nHello.\n", encoding="utf-8")
    html_dir = root / "documentation"
    html_dir.mkdir()
    atlas = {
        "meta": {
            "commit": "old",
            "version": "0.0.1",
            "date": "1 January 2020",
            "tests": {},
            "scope": "fixture",
        },
        "skills": [
            {
                "id": "demo-skill",
                "group": "Foundation",
                "title": "Curated title",
                "summary": "Keep this summary.",
                "inputs": ["input"],
                "outputs": ["output"],
                "states": ["one"],
                "agents": [],
                "reads": ["read"],
                "writes": "write",
                "gotcha": "gotcha",
                "example": "/demo-skill example",
                "source": ".cursor/skills/demo-skill/SKILL.md",
                "words": 0,
                "chars": 0,
                "links": [],
                "refWords": 0,
                "sourceHash": "stale",
            }
        ],
        "nodes": [
            {
                "id": "README.md",
                "kind": "package",
                "name": "Demo package",
                "summary": "Curated readme summary.",
                "words": 0,
                "chars": 0,
                "lines": 0,
                "links": [],
                "headings": [],
                "source": "stale",
                "inbound": [],
            }
        ],
        "improvements": [{"priority": "P0", "title": "Keep me"}],
        "sources": [{"name": "Keep source"}],
    }
    (html_dir / "aidlc-explorer.html").write_text(
        "<html>"
        '<script id="atlas-data" type="application/json">'
        + json.dumps(atlas)
        + "</script></html>",
        encoding="utf-8",
    )


def test_generator_refreshes_live_fields_and_preserves_curated_copy() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        _mini_plugin(root)
        html_path = root / "documentation" / "aidlc-explorer.html"
        assert generate(root, html_path) is True
        atlas = json.loads(
            html_path.read_text(encoding="utf-8").split(
                '<script id="atlas-data" type="application/json">', 1
            )[1].split("</script>", 1)[0]
        )
        skill = atlas["skills"][0]
        assert skill["title"] == "Curated title"
        assert skill["summary"] == "Keep this summary."
        assert skill["example"] == "/demo-skill example"
        assert skill["sourceHash"] != "stale"
        assert skill["links"] == ["README.md"]
        assert atlas["meta"]["version"] == "1.2.3"
        assert atlas["improvements"] == [{"priority": "P0", "title": "Keep me"}]
        assert atlas["sources"] == [{"name": "Keep source"}]
        readme = next(node for node in atlas["nodes"] if node["id"] == "README.md")
        assert readme["source"] == "# Demo package\n\nHello.\n"
        assert readme["summary"] == "Curated readme summary."
        assert generate(root, html_path) is False


def test_check_reports_a_stale_package_version() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        _mini_plugin(root)
        html_path = root / "documentation" / "aidlc-explorer.html"
        stale = freshness_errors(root, html_path)
        assert any("version" in error for error in stale)
        generate(root, html_path)
        assert freshness_errors(root, html_path) == []


def test_checked_in_explorer_matches_plugin_source() -> None:
    errors = freshness_errors(ROOT)
    assert errors == [], "\n".join(errors)


if __name__ == "__main__":
    tests = [
        test_headings_include_fenced_h1_to_h3_and_skip_h4,
        test_links_keep_indexed_relative_targets_including_fenced_ones,
        test_source_hash_is_sha256_prefix,
        test_hook_filters_plugin_source_and_skips_the_explorer,
        test_generator_refreshes_live_fields_and_preserves_curated_copy,
        test_check_reports_a_stale_package_version,
        test_checked_in_explorer_matches_plugin_source,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
