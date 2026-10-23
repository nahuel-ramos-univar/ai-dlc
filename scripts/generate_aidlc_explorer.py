#!/usr/bin/env python3
"""Refresh the live snapshot inside documentation/aidlc-explorer.html.

The HTML shell, skill cards, improvements, and research notes stay curated.
This script rewrites #atlas-data so node sources, links, hashes, package
version, and test counts match the plugin files on disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ATLAS_OPEN = '<script id="atlas-data" type="application/json">'
ATLAS_CLOSE = "</script>"
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
TEST_DEF_RE = re.compile(r"^def test_", re.MULTILINE)
TEST_COUNTS = (
    ("Skill contracts", "tests/skill_contracts.py"),
    ("Release contracts", "tests/release_contracts.py"),
    ("Context tools", "tests/context_tools_tests.py"),
    ("Explorer snapshot", "tests/aidlc_explorer_tests.py"),
    ("Host observation", "tests/host_observation_tests.py"),
)
SKILL_ORDER = (
    "sync-context",
    "scaffold-project",
    "plan-work",
    "refine-story",
    "implement-change",
    "validate-change",
    "create-e2e-tests",
)
SKILL_GROUPS = {
    "sync-context": "Foundation",
    "scaffold-project": "Foundation",
    "plan-work": "Product",
    "refine-story": "Engineering",
    "implement-change": "Engineering",
    "validate-change": "Assurance",
    "create-e2e-tests": "Assurance",
}
CURATED_SKILL_FIELDS = (
    "group",
    "title",
    "summary",
    "inputs",
    "outputs",
    "states",
    "agents",
    "reads",
    "writes",
    "gotcha",
    "example",
)
REFRESH_PREFIXES = (
    ".cursor/skills/",
    "agents/",
    "references/",
    "rules/",
    ".cursor-plugin/",
)
REFRESH_FILES = {
    "README.md",
    "MANUAL_EVALUATION.md",
    "tests/skill_contracts.py",
    "tests/release_contracts.py",
    "tests/context_tools_tests.py",
    "tests/aidlc_explorer_tests.py",
    "tests/host_observation_tests.py",
    "scripts/generate_aidlc_explorer.py",
}
SKIP_PREFIXES = (
    "documentation/",
    ".cursor/hooks/",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_html(root: Path) -> Path:
    return root / "documentation" / "aidlc-explorer.html"


def git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "uncommitted"
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else "uncommitted"


def today_label() -> str:
    current = date.today()
    return f"{current.day} {current.strftime('%B')} {current.year}"


def line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def extract_headings(text: str) -> list[dict[str, object]]:
    headings: list[dict[str, object]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        match = HEADING_RE.match(line)
        if match:
            headings.append({"text": match.group(2).strip(), "line": index})
    return headings


def first_h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def parse_frontmatter_fields(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    values: dict[str, str] = {}
    for line in parts[1].splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        values[key.strip()] = value.strip()
    return values


def extract_links(path: Path, text: str, root: Path, indexed: set[str]) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    root_resolved = root.resolve()
    for raw in LINK_RE.findall(text):
        target = raw.strip().strip("<>").split()[0].strip("\"'")
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = target.split("#", 1)[0]
        if not target:
            continue
        destination = (path.parent / target).resolve()
        try:
            relative = destination.relative_to(root_resolved).as_posix()
        except ValueError:
            continue
        if relative not in indexed or relative in seen:
            continue
        seen.add(relative)
        links.append(relative)
    return links


def discover_source_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    skills = root / ".cursor" / "skills"
    if skills.is_dir():
        paths.extend(sorted(skills.glob("*/SKILL.md")))
        paths.extend(sorted(skills.glob("*/references/*.md")))
    for folder, pattern in (
        ("agents", "*.md"),
        ("references", "*.md"),
        ("rules", "*.mdc"),
    ):
        directory = root / folder
        if directory.is_dir():
            paths.extend(sorted(directory.glob(pattern)))
    for extra in (".cursor-plugin/plugin.json", "README.md", "MANUAL_EVALUATION.md"):
        candidate = root / extra
        if candidate.is_file():
            paths.append(candidate)
    return paths


def node_kind(relative: str) -> str:
    if relative.endswith("/SKILL.md") and relative.startswith(".cursor/skills/"):
        return "skill"
    if relative.startswith("agents/") and relative.endswith(".md"):
        return "agent"
    if relative.startswith("rules/") and relative.endswith(".mdc"):
        return "rule"
    if relative in {".cursor-plugin/plugin.json", "README.md", "MANUAL_EVALUATION.md"}:
        return "package"
    return "reference"


def node_name(relative: str, text: str) -> str:
    heading = first_h1(text)
    if heading:
        return heading
    return Path(relative).stem


def node_summary(relative: str, text: str, previous: dict[str, object] | None) -> str:
    if previous and isinstance(previous.get("summary"), str) and previous["summary"]:
        return str(previous["summary"])
    fields = parse_frontmatter_fields(text)
    if fields.get("description"):
        return fields["description"]
    return node_name(relative, text)


def count_tests(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label, relative in TEST_COUNTS:
        path = root / relative
        if path.is_file():
            counts[label] = len(TEST_DEF_RE.findall(path.read_text(encoding="utf-8")))
    return counts


def plugin_version(root: Path) -> str:
    manifest = json.loads((root / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise SystemExit("plugin.json is missing a version string")
    return version


def relative_posix(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def should_refresh_path(path: Path, root: Path) -> bool:
    relative = relative_posix(path, root)
    if relative is None:
        return False
    if any(relative == prefix.rstrip("/") or relative.startswith(prefix) for prefix in SKIP_PREFIXES):
        return False
    if relative in REFRESH_FILES:
        return True
    return any(relative.startswith(prefix) for prefix in REFRESH_PREFIXES)


def payload_paths(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return []
    values: list[object] = []
    for key in ("file_path", "filePath", "path", "uri"):
        if key in payload:
            values.append(payload[key])
    files = payload.get("files")
    if isinstance(files, list):
        values.extend(files)
    paths: list[str] = []
    for value in values:
        if isinstance(value, str) and value:
            paths.append(value)
        elif isinstance(value, dict):
            nested = value.get("path") or value.get("file_path") or value.get("filePath")
            if isinstance(nested, str) and nested:
                paths.append(nested)
    return paths


def load_atlas(html: str) -> dict[str, object]:
    start = html.find(ATLAS_OPEN)
    end = html.find(ATLAS_CLOSE, start + len(ATLAS_OPEN)) if start >= 0 else -1
    if start < 0 or end < 0:
        raise SystemExit("documentation/aidlc-explorer.html is missing #atlas-data")
    return json.loads(html[start + len(ATLAS_OPEN) : end])


def embed_atlas(html: str, atlas: dict[str, object]) -> str:
    start = html.find(ATLAS_OPEN)
    end = html.find(ATLAS_CLOSE, start + len(ATLAS_OPEN)) if start >= 0 else -1
    if start < 0 or end < 0:
        raise SystemExit("documentation/aidlc-explorer.html is missing #atlas-data")
    blob = json.dumps(atlas, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("<", "\\u003c")
    return html[: start + len(ATLAS_OPEN)] + blob + html[end:]


def empty_skill(skill_id: str, source: str, text: str) -> dict[str, object]:
    fields = parse_frontmatter_fields(text)
    title = first_h1(text) or skill_id
    return {
        "id": skill_id,
        "group": SKILL_GROUPS.get(skill_id, "Lifecycle"),
        "title": title,
        "summary": fields.get("description") or title,
        "inputs": [],
        "outputs": [],
        "states": [],
        "agents": [],
        "reads": [],
        "writes": "",
        "gotcha": "",
        "example": f"/{skill_id}",
        "source": source,
        "words": 0,
        "chars": 0,
        "links": [],
        "refWords": 0,
        "sourceHash": "",
    }


def refresh_skill(
    previous: dict[str, object] | None,
    skill_id: str,
    source: str,
    text: str,
    links: list[str],
    word_counts: dict[str, int],
) -> dict[str, object]:
    skill = empty_skill(skill_id, source, text)
    if previous:
        for field in CURATED_SKILL_FIELDS:
            if field in previous:
                skill[field] = previous[field]
    skill["source"] = source
    skill["words"] = len(text.split())
    skill["chars"] = len(text)
    skill["links"] = links
    skill["refWords"] = sum(word_counts.get(link, 0) for link in links)
    skill["sourceHash"] = source_hash(text)
    return skill


def build_atlas(root: Path, existing: dict[str, object]) -> dict[str, object]:
    paths = discover_source_paths(root)
    indexed = {path.resolve().relative_to(root.resolve()).as_posix() for path in paths}
    previous_nodes = {
        str(node["id"]): node
        for node in existing.get("nodes", [])
        if isinstance(node, dict) and "id" in node
    }
    nodes: list[dict[str, object]] = []
    texts: dict[str, str] = {}
    word_counts: dict[str, int] = {}
    for path in paths:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        text = path.read_text(encoding="utf-8")
        texts[relative] = text
        word_counts[relative] = len(text.split())
        previous = previous_nodes.get(relative)
        nodes.append(
            {
                "id": relative,
                "kind": node_kind(relative),
                "name": node_name(relative, text),
                "summary": node_summary(relative, text, previous),
                "words": word_counts[relative],
                "chars": len(text),
                "lines": line_count(text),
                "links": [],
                "headings": extract_headings(text),
                "source": text,
                "inbound": [],
            }
        )
    nodes.sort(key=lambda node: str(node["id"]))
    by_id = {str(node["id"]): node for node in nodes}
    for node in nodes:
        node["links"] = extract_links(
            root / str(node["id"]),
            texts[str(node["id"])],
            root,
            indexed,
        )
    inbound: dict[str, list[str]] = {str(node["id"]): [] for node in nodes}
    for node in nodes:
        source_id = str(node["id"])
        for link in node["links"]:
            if link in inbound and source_id not in inbound[link]:
                inbound[link].append(source_id)
    for node in nodes:
        node["inbound"] = inbound[str(node["id"])]

    previous_skills = {
        str(skill["id"]): skill
        for skill in existing.get("skills", [])
        if isinstance(skill, dict) and "id" in skill
    }
    skill_ids = [relative.split("/")[2] for relative in indexed if relative.endswith("/SKILL.md")]
    ordered_ids = [skill_id for skill_id in SKILL_ORDER if skill_id in skill_ids]
    ordered_ids.extend(sorted(skill_id for skill_id in skill_ids if skill_id not in ordered_ids))
    skills: list[dict[str, object]] = []
    for skill_id in ordered_ids:
        source = f".cursor/skills/{skill_id}/SKILL.md"
        node = by_id[source]
        skills.append(
            refresh_skill(
                previous_skills.get(skill_id),
                skill_id,
                source,
                texts[source],
                list(node["links"]),
                word_counts,
            )
        )

    previous_meta = existing.get("meta") if isinstance(existing.get("meta"), dict) else {}
    atlas = {
        "meta": {
            "commit": git_commit(root),
            "version": plugin_version(root),
            "date": today_label(),
            "tests": count_tests(root),
            "scope": previous_meta.get(
                "scope",
                "Static source audit + official documentation research. No live Cursor/Claude/Codex workflow or token trace was supplied.",
            ),
        },
        "skills": skills,
        "nodes": nodes,
        "improvements": existing.get("improvements", []),
        "sources": existing.get("sources", []),
    }
    return atlas


def live_snapshot(atlas: dict[str, object]) -> dict[str, object]:
    skills = []
    for skill in atlas.get("skills", []):
        if not isinstance(skill, dict):
            continue
        skills.append(
            {
                "id": skill.get("id"),
                "source": skill.get("source"),
                "words": skill.get("words"),
                "chars": skill.get("chars"),
                "links": skill.get("links"),
                "refWords": skill.get("refWords"),
                "sourceHash": skill.get("sourceHash"),
            }
        )
    nodes = []
    for node in atlas.get("nodes", []):
        if not isinstance(node, dict):
            continue
        nodes.append(
            {
                "id": node.get("id"),
                "kind": node.get("kind"),
                "name": node.get("name"),
                "words": node.get("words"),
                "chars": node.get("chars"),
                "lines": node.get("lines"),
                "links": node.get("links"),
                "headings": node.get("headings"),
                "source": node.get("source"),
                "inbound": node.get("inbound"),
            }
        )
    meta = atlas.get("meta") if isinstance(atlas.get("meta"), dict) else {}
    return {
        "version": meta.get("version"),
        "tests": meta.get("tests"),
        "skills": skills,
        "nodes": nodes,
    }


def freshness_errors(root: Path, html_path: Path | None = None) -> list[str]:
    html_path = html_path or default_html(root)
    existing = load_atlas(html_path.read_text(encoding="utf-8"))
    expected = live_snapshot(build_atlas(root, existing))
    actual = live_snapshot(existing)
    errors: list[str] = []
    if actual["version"] != expected["version"]:
        errors.append(
            f"explorer version {actual['version']!r} != plugin.json {expected['version']!r}"
        )
    if actual["tests"] != expected["tests"]:
        errors.append(f"explorer tests {actual['tests']!r} != {expected['tests']!r}")
    if actual["skills"] != expected["skills"]:
        errors.append("explorer skill metrics do not match SKILL.md files")
    if actual["nodes"] != expected["nodes"]:
        errors.append("explorer node snapshot does not match plugin source files")
    return errors


def generate(root: Path, html_path: Path | None = None) -> bool:
    html_path = html_path or default_html(root)
    html = html_path.read_text(encoding="utf-8")
    existing = load_atlas(html)
    atlas = build_atlas(root, existing)
    if live_snapshot(existing) == live_snapshot(atlas):
        atlas["meta"]["date"] = existing.get("meta", {}).get("date", atlas["meta"]["date"])
        atlas["meta"]["commit"] = existing.get("meta", {}).get("commit", atlas["meta"]["commit"])
        if json.dumps(existing, sort_keys=True) == json.dumps(atlas, sort_keys=True):
            return False
    html_path.write_text(embed_atlas(html, atlas), encoding="utf-8")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--html", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = (args.root or repo_root()).resolve()
    html_path = args.html.resolve() if args.html else default_html(root)
    if args.check:
        errors = freshness_errors(root, html_path)
        if errors:
            print("Explorer snapshot is stale:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            print(
                "Refresh with: python3 scripts/generate_aidlc_explorer.py",
                file=sys.stderr,
            )
            return 1
        print("Explorer snapshot matches plugin source")
        return 0
    changed = generate(root, html_path)
    print("Updated" if changed else "Already current", html_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
