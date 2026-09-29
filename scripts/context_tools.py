#!/usr/bin/env python3
"""Deterministic helpers for AI-DLC repository context.

These helpers support skill-directed discovery. They do not scan, write, or
choose repositories on their own.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

EXCLUDED_PARTS = {
    ".git",
    "aidlc-docs",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".cache",
}
GENERATED_FILENAMES = {"aidlc_context.md", ".ai-dlc-config.md"}
SECRET_FILENAMES = {".env", "id_rsa", "id_ed25519"}
ENV_TEMPLATE_FILENAMES = {".env.example", ".env.sample", ".env.template", ".env.dist"}
REPOSITORY_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class RepositoryScope:
    requested_path: Path
    git_root: Path | None
    kind: str
    enclosing_git_root: Path | None = None


def git_output(path: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def classify_repository_scope(requested_path: Path) -> RepositoryScope:
    """Classify a requested directory without modifying Git state."""
    requested = requested_path.resolve()
    root_output = git_output(requested, "rev-parse", "--show-toplevel")
    if root_output is None:
        return RepositoryScope(requested, None, "unversioned")

    root = Path(root_output).resolve()
    if requested == root:
        return RepositoryScope(requested, root, "git-root", root)

    relative = requested.relative_to(root).as_posix()
    tracked = git_output(root, "ls-files", "--", relative)
    if tracked:
        return RepositoryScope(requested, root, "nested-tracked", root)
    return RepositoryScope(requested, None, "untracked-tree", root)


def normalize_remote(remote: str) -> str | None:
    """Normalize known equivalent GitHub SSH and HTTPS remote forms."""
    remote = remote.strip()
    remote = re.sub(r"^[a-z]+://[^@/]+@", "https://", remote)
    github_ssh = re.fullmatch(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?", remote)
    github_https = re.fullmatch(
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?", remote
    )
    match = github_ssh or github_https
    if match:
        return f"github.com/{match.group(1)}/{match.group(2)}"
    return None


def stable_repository_id(
    persisted_id: str | None, canonical_remote: str | None, fallback_id: str | None
) -> str:
    """Prefer persisted identity; only derive when no identity exists."""
    if persisted_id:
        if not REPOSITORY_ID_PATTERN.fullmatch(persisted_id):
            raise ValueError("persisted repository ID must match [a-z0-9-]")
        return persisted_id
    candidate = canonical_remote or fallback_id
    if not candidate:
        raise ValueError("repository identity needs a persisted ID or verified remote")
    slug = re.sub(r"[^a-z0-9]+", "-", candidate.lower()).strip("-")
    if not slug:
        raise ValueError("repository identity is empty after normalization")
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


def detect_repository_id_collision(
    repo_id: str, canonical_identity: str, occupied: dict[str, str]
) -> str | None:
    """Return the occupying identity when repo_id is already claimed."""
    owner = occupied.get(repo_id)
    if owner is None or owner == canonical_identity:
        return None
    return owner


def is_generated_artifact(path: Path) -> bool:
    filename = path.name.lower()
    if filename in GENERATED_FILENAMES:
        return True
    return path.name == "BUGBOT.md" and path.parent.name == ".cursor"


def is_nested_git_root(path: Path, scope_root: Path) -> bool:
    """True when path is a nested Git repository inside the declared scope."""
    if path == scope_root:
        return False
    git_marker = path / ".git"
    return git_marker.exists()


def is_secret_env_file(filename: str) -> bool:
    if filename in ENV_TEMPLATE_FILENAMES:
        return False
    return filename == ".env" or filename.startswith(".env.")


def is_excluded(path: Path, scope_root: Path) -> bool:
    relative = path.relative_to(scope_root)
    filename = path.name.lower()
    return (
        any(part in EXCLUDED_PARTS for part in relative.parts)
        or is_generated_artifact(path)
        or filename in SECRET_FILENAMES
        or is_secret_env_file(filename)
        or filename.endswith((".pem", ".key", ".p12", ".pfx"))
    )


def _raise_walk_error(error: OSError) -> None:
    raise error


def iter_fingerprint_files(scope_root: Path) -> list[Path]:
    """Return sorted regular files for a declared source scope.

    Generated context and common cache/build directories are pruned during the
    walk. Nested Git repositories are skipped so a parent hash does not mix
    checkouts. Nested directory and file symlinks are skipped so content
    outside the approved root cannot enter the hash. A symlink scope root is
    walked as the declared source. Missing, non-directory, or unreadable
    scopes raise instead of hashing an empty tree.
    """
    scope = Path(scope_root)
    if not scope.exists():
        raise FileNotFoundError(f"fingerprint scope does not exist: {scope}")
    if not scope.is_dir():
        raise NotADirectoryError(f"fingerprint scope is not a directory: {scope}")
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(
        scope, followlinks=False, onerror=_raise_walk_error
    ):
        current = Path(dirpath)
        nested_symlink = current.is_symlink() and current.resolve() != scope.resolve()
        if nested_symlink or is_nested_git_root(current, scope):
            dirnames[:] = []
            continue
        dirnames[:] = [
            name
            for name in dirnames
            if name not in EXCLUDED_PARTS
            and not (current / name).is_symlink()
            and not is_nested_git_root(current / name, scope)
        ]
        for name in filenames:
            path = current / name
            if path.is_symlink() or not path.is_file() or is_excluded(path, scope):
                continue
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(scope).as_posix())


def content_fingerprint(scope_root: Path) -> tuple[str, tuple[str, ...]]:
    """SHA-256 over NUL-delimited relative path and file-content hashes."""
    digest = hashlib.sha256()
    relative_paths: list[str] = []
    scope = Path(scope_root)
    for path in iter_fingerprint_files(scope):
        relative = path.relative_to(scope).as_posix()
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_hash.encode("ascii"))
        digest.update(b"\0")
        relative_paths.append(relative)
    return digest.hexdigest()[:16], tuple(relative_paths)


def document_metrics(path: Path) -> tuple[int, int]:
    """Return line count and an approximate context cost (characters / 4)."""
    text = path.read_text(encoding="utf-8")
    return len(text.splitlines()), (len(text) + 3) // 4


def is_writable_directory(path: Path) -> bool:
    """Best-effort check; callers must not claim this proves authorization."""
    return os.access(path, os.W_OK)


# --- Deterministic validation for generated context -----------------------
#
# These checks confirm measurable properties of generated documents. A
# passing result never proves an Unknown is accurate, that a described
# dependency is correct, or that a claim is well-supported. Those judgments
# belong to independent review, not to this module.
#
# Every multi-repository check below takes an explicit `authorized_roots`
# mapping (repository ID -> that repository's root path) supplied by the
# caller. This module never guesses which directories are authorized from
# the filesystem; a reference resolving outside every mapped root is
# rejected, never silently accepted as if the whole filesystem were in
# scope. `authorized_roots` holds machine-local absolute paths only in
# runtime memory; callers must not write those absolute paths into portable
# generated context.

MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEX16_TOKEN_PATTERN = re.compile(r"`([0-9a-f]{16})`")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s")
SEPARATOR_CELL_PATTERN = re.compile(r"^:?-+:?$")
FINGERPRINT_FIELD_PATTERN = re.compile(r"^-\s*Fingerprint:\s*`([0-9a-f]{16})`\s*$")
BASELINE_AND_FINGERPRINT_FIELD_PATTERN = re.compile(
    r"^-\s*Baseline and fingerprint:\s*`[^`]+`\s*/\s*`([0-9a-f]{16})`\s*$"
)
LABELED_FIELD_PATTERN = re.compile(r"^-\s+([^:`]+):\s+`([^`]*)`\s*$")
GENERATED_START_PATTERN = re.compile(r"^<!--\s*AI-DLC:generated:start\s*-->$")
GENERATED_END_PATTERN = re.compile(r"^<!--\s*AI-DLC:generated:end\s*-->$")
EVIDENCE_LINK_PATTERN = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)\s*$")
EVIDENCE_PATH_PATTERN = re.compile(r"^- `([^`]+)`\s*$")
CROSS_REPO_PATH_PATTERN = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*):(.+)$")
PATH_EXTENSIONS = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
)


def check_document_budget(path: Path, max_lines: int = 300) -> bool:
    """True when the document's line count is within the declared budget."""
    lines, _ = document_metrics(path)
    return lines <= max_lines


def _resolve_roots(authorized_roots: dict[str, Path]) -> dict[str, Path]:
    return {repo_id: Path(root).resolve() for repo_id, root in authorized_roots.items()}


def _best_matching_root(resolved: Path, resolved_roots: dict[str, Path]) -> Path | None:
    """Return the most specific authorized root containing `resolved`, if any."""
    best: Path | None = None
    for root in resolved_roots.values():
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if best is None or len(root.parts) > len(best.parts):
            best = root
    return best


def read_text_document(path: Path) -> tuple[str | None, str | None]:
    """Read a context document as UTF-8 text.

    Returns `(text, None)` for a regular file. Returns `(None, detail)` for
    an expected failure: missing path, directory or other non-file, invalid
    encoding, or a permission error. Other exceptions propagate.
    """
    if not path.exists():
        return None, f"{path} does not exist"
    if not path.is_file():
        return None, f"{path} is not a regular file"
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return None, f"{path} is not valid UTF-8 text"
    except IsADirectoryError:
        return None, f"{path} is not a regular file"
    except PermissionError as error:
        return None, f"{path} is not readable: {error.strerror}"
    except FileNotFoundError:
        return None, f"{path} does not exist"


def _classify_local_target(
    resolved: Path, resolved_roots: dict[str, Path], *, require_file: bool = False
) -> str:
    root = _best_matching_root(resolved, resolved_roots)
    if root is None:
        return "unresolvable"
    if not root.is_dir():
        return "unavailable"
    if not resolved.exists():
        return "missing"
    if require_file and not resolved.is_file():
        return "not_a_file"
    return "ok"


def classify_markdown_target(
    document_path: Path,
    target: str,
    authorized_roots: dict[str, Path],
    *,
    require_file: bool = False,
) -> str:
    """Classify one Markdown link target against authorized roots.

    `require_file` is for context documents, which must be regular files.
    Source scopes and other existing paths may be directories.
    """
    if "://" in target or target.startswith("#"):
        return "external"
    local_path = target.split("#", 1)[0]
    if not local_path:
        return "external"
    resolved = (document_path.parent / local_path).resolve()
    return _classify_local_target(
        resolved, _resolve_roots(authorized_roots), require_file=require_file
    )


def resolve_markdown_links(
    markdown_path: Path, authorized_roots: dict[str, Path]
) -> dict[str, str]:
    """Classify each local Markdown link in `markdown_path`.

    `authorized_roots` maps a repository ID to that repository's root path;
    it must be explicit workspace configuration, never guessed from the
    filesystem or expanded to the whole filesystem. Status is one of:

    - "ok": the target exists inside an authorized, available root. A
      directory can be "ok" here; context documents use `require_file`.
    - "missing": the target's owning authorized root is available, but the
      target does not exist there.
    - "unavailable": the target falls under a configured root that is not
      (or is no longer) an accessible directory.
    - "unresolvable": the target, after resolving symlinks and `..`
      segments, does not fall under any authorized root. This is a hard
      rejection of parent-directory traversal and symlink escape, not a
      permissive fallback to the whole filesystem.
    - "not_a_file": only when a caller requires a regular file and the
      target exists as something else, such as a directory.
    - "external": a URL or a same-document anchor, not verified here.

    An unavailable, unresolvable, or external reference is never reported as
    "ok".
    """
    text = markdown_path.read_text(encoding="utf-8")
    statuses: dict[str, str] = {}
    for target in MARKDOWN_LINK_PATTERN.findall(text):
        statuses[target] = classify_markdown_target(markdown_path, target, authorized_roots)
    return statuses


def resolve_source_path(
    repository_id: str, relative_path: str, authorized_roots: dict[str, Path]
) -> str:
    """Classify one declared (repository_id, relative_path) source entry.

    The path is resolved against its own owning repository's root, never
    against an unrelated artifact home. Returns one of:

    - "ok": the repository is available and the path exists there.
    - "missing": the repository is available but the path does not exist.
    - "unavailable": `repository_id` is a known authorized root, but that
      root is not an accessible directory.
    - "unresolved": `repository_id` is not in `authorized_roots` at all
      (unresolved repository identity) -- this is not the same as a missing
      file, and must not be reported as passing.
    - "unresolvable": the path escapes its owning repository root after
      resolving `..` segments and symlinks. Arbitrary parent-directory
      traversal is rejected, never silently followed to a sibling location.
    """
    root = authorized_roots.get(repository_id)
    if root is None:
        return "unresolved"
    root_resolved = Path(root).resolve()
    if not root_resolved.is_dir():
        return "unavailable"
    candidate = (root_resolved / relative_path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return "unresolvable"
    return "ok" if candidate.exists() else "missing"


def find_stale_source_paths(
    entries: list[tuple[str, str]], authorized_roots: dict[str, Path]
) -> dict[tuple[str, str], str]:
    """Classify declared (repository_id, relative_path) source entries.

    Returns only the entries that are not "ok", mapped to the reason:
    "missing", "unavailable", "unresolved", or "unresolvable". An empty
    result means every declared source path resolved cleanly; it does not by
    itself mean the surrounding prose is accurate.
    """
    problems: dict[tuple[str, str], str] = {}
    for entry in entries:
        status = resolve_source_path(entry[0], entry[1], authorized_roots)
        if status != "ok":
            problems[entry] = status
    return problems


def find_duplicate_values(values: list[str]) -> list[str]:
    """Return values that occur more than once, in first-seen order."""
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    duplicates: list[str] = []
    for value in values:
        if counts[value] > 1 and value not in duplicates:
            duplicates.append(value)
    return duplicates


def find_duplicate_identities(
    module_ids: list[str], repository_ids: list[str] | None = None
) -> list[tuple[str, str]]:
    """Return duplicate (repository_id, module_id) pairs.

    Two different repositories may both declare a module named `api`; that
    is not a duplicate. When `repository_ids` is None, every module belongs
    to one unambiguous repository (the single-repository case) and
    duplicates are detected on `module_id` alone. When provided,
    `repository_ids` must align positionally with `module_ids`.
    """
    if repository_ids is None:
        pairs = [("", module_id) for module_id in module_ids]
    else:
        if len(repository_ids) != len(module_ids):
            raise ValueError("repository_ids must align positionally with module_ids")
        pairs = list(zip(repository_ids, module_ids))
    counts: dict[tuple[str, str], int] = {}
    for pair in pairs:
        counts[pair] = counts.get(pair, 0) + 1
    duplicates: list[tuple[str, str]] = []
    for pair in pairs:
        if counts[pair] > 1 and pair not in duplicates:
            duplicates.append(pair)
    return duplicates


def _link_target(cell: str) -> str:
    match = MARKDOWN_LINK_PATTERN.search(cell)
    return match.group(1) if match else cell


def find_duplicate_context_targets(
    context_cells: list[str], markdown_path: Path
) -> list[Path]:
    """Return resolved Context-column targets shared by more than one row.

    Two entries that spell the same file differently (for example
    `apps/web/AIDLC_CONTEXT.md` and `./apps/web/AIDLC_CONTEXT.md`) still
    collide once resolved. External URLs and anchors are ignored; they are
    never a duplicate generated-context output.
    """
    resolved: list[Path] = []
    for cell in context_cells:
        target = _link_target(cell)
        if "://" in target or target.startswith("#") or not target:
            continue
        resolved.append((markdown_path.parent / target.split("#", 1)[0]).resolve())
    counts: dict[Path, int] = {}
    for path in resolved:
        counts[path] = counts.get(path, 0) + 1
    duplicates: list[Path] = []
    for path in resolved:
        if counts[path] > 1 and path not in duplicates:
            duplicates.append(path)
    return duplicates


@dataclass(frozen=True)
class TableColumn:
    """Result of extracting one column from a generated Markdown table.

    `status` is one of:

    - "ok": a well-formed table was found; `values` holds that column's
      cells, in row order. `values` may be empty for a valid, deliberately
      empty table.
    - "missing_section": the requested heading does not appear at all.
    - "missing_table": the heading exists, but no table appears before the
      next heading of the same or higher level.
    - "malformed_table": a table-like block was found, but its separator row
      is invalid or a data row's cell count does not match the header. A
      malformed row is reported this way rather than silently dropped.
    - "missing_column": the table is well-formed, but `column` is not one of
      its headers.

    Only "ok" values are safe to treat as the document's actual data; every
    other status means the column could not be read and must not be treated
    as an empty-but-valid result.
    """

    status: str
    values: tuple[str, ...] = ()


def _split_row(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip("|").split("|")]


def _open_fence(line: str) -> tuple[str, int] | None:
    """Return the fence character and length when `line` opens a fence."""
    match = re.match(r"^(```+|~~~+)(.*)$", line.strip())
    if match is None:
        return None
    marker, rest = match.group(1), match.group(2)
    if marker[0] == "`" and "`" in rest:
        return None
    return marker[0], len(marker)


def _closes_fence(line: str, fence: tuple[str, int]) -> bool:
    character, length = fence
    return re.fullmatch(rf"{re.escape(character)}{{{length},}}", line.strip()) is not None


def _live_lines(markdown_text: str) -> list[str]:
    """Drop fenced examples, tracking fences from the start of the document.

    A heading or table inside a backtick or tilde fence is not live content.
    The fence state starts before the first heading, so an example that
    appears earlier cannot hide or replace a later real section.
    """
    live: list[str] = []
    fence: tuple[str, int] | None = None
    for line in markdown_text.splitlines():
        if fence is None:
            opened = _open_fence(line)
            if opened is not None:
                fence = opened
                continue
            live.append(line)
        elif _closes_fence(line, fence):
            fence = None
    return live


def _section_lines(markdown_text: str, heading: str) -> list[str] | None:
    """Return the live lines of the section under `heading`, or None if absent.

    Heading discovery ignores fenced examples. The section stops at the next
    live heading of the same or higher level.
    """
    heading_level = len(heading) - len(heading.lstrip("#"))
    lines = _live_lines(markdown_text)
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return None
    section: list[str] = []
    for line in lines[start + 1 :]:
        heading_match = HEADING_PATTERN.match(line.strip())
        if heading_match and len(heading_match.group(1)) <= heading_level:
            break
        section.append(line)
    return section


@dataclass(frozen=True)
class GeneratedBlock:
    """One unambiguous `AI-DLC:generated` region, or why it could not be read."""

    status: str
    text: str = ""


def parse_generated_block(markdown_text: str) -> GeneratedBlock:
    """Return the single generated block, ignoring markers inside fences.

    `status` is "ok", "missing", "malformed", or "ambiguous". Missing,
    unclosed, nested, or repeated blocks are rejected. This function does
    not fall back to treating the rest of the document as generated content.
    """
    fence: tuple[str, int] | None = None
    blocks: list[list[str]] = []
    current: list[str] | None = None
    malformed = False
    for line in markdown_text.splitlines():
        if fence is not None:
            if _closes_fence(line, fence):
                fence = None
            continue
        opened = _open_fence(line)
        if opened is not None:
            fence = opened
            continue
        stripped = line.strip()
        if GENERATED_START_PATTERN.match(stripped):
            if current is not None:
                malformed = True
            current = []
            continue
        if GENERATED_END_PATTERN.match(stripped):
            if current is None:
                malformed = True
            else:
                blocks.append(current)
                current = None
            continue
        if current is not None:
            current.append(line)
    if current is not None or malformed:
        return GeneratedBlock("malformed")
    if not blocks:
        return GeneratedBlock("missing")
    if len(blocks) > 1:
        return GeneratedBlock("ambiguous")
    return GeneratedBlock("ok", "\n".join(blocks[0]))


@dataclass(frozen=True)
class LabeledFields:
    """Unique backtick fields from one metadata section."""

    status: str
    values: dict[str, str]
    detail: str = ""


def parse_labeled_fields(section: list[str]) -> LabeledFields:
    """Read labeled backtick fields. Duplicate names are ambiguous."""
    found: dict[str, list[str]] = {}
    for line in section:
        match = LABELED_FIELD_PATTERN.match(line.strip())
        if match is None:
            continue
        found.setdefault(match.group(1).strip(), []).append(match.group(2).strip())
    duplicates = [name for name, values in found.items() if len(values) > 1]
    if duplicates:
        return LabeledFields("ambiguous", {}, f"duplicate metadata fields: {duplicates}")
    return LabeledFields("ok", {name: values[0] for name, values in found.items()})


def extract_table_column(markdown_text: str, heading: str, column: str) -> TableColumn:
    """Read `column` from the first table directly under `heading`.

    Parsing is section-aware for this repository's generated format: it
    stops at the next heading of the same or higher level, so a missing
    table under `heading` never falls through into a different section's
    table. Fenced code examples are ignored, so a documented example table
    is never mistaken for live data.
    """
    section = _section_lines(markdown_text, heading)
    if section is None:
        return TableColumn("missing_section")

    table_lines: list[str] = []
    for line in section:
        stripped = line.strip()
        if stripped.startswith("|"):
            table_lines.append(stripped)
        elif table_lines:
            break

    if not table_lines:
        return TableColumn("missing_table")
    if len(table_lines) < 2:
        return TableColumn("malformed_table")

    headers = _split_row(table_lines[0])
    separator = _split_row(table_lines[1])
    if len(separator) != len(headers) or not all(
        SEPARATOR_CELL_PATTERN.match(cell) for cell in separator
    ):
        return TableColumn("malformed_table")
    if column not in headers:
        return TableColumn("missing_column")

    index = headers.index(column)
    values: list[str] = []
    for row in table_lines[2:]:
        cells = _split_row(row)
        if len(cells) != len(headers):
            return TableColumn("malformed_table")
        values.append(cells[index].strip("`"))
    return TableColumn("ok", tuple(values))


@dataclass(frozen=True)
class FingerprintField:
    """Result of reading the canonical fingerprint field from a document.

    `status` is one of "ok", "missing", "malformed", or "ambiguous". Only
    "ok" carries a usable `value`.
    """

    status: str
    value: str | None = None


def parse_recorded_fingerprint(markdown_text: str) -> FingerprintField:
    """Extract the canonical recorded fingerprint from a generated document.

    Only two field shapes count as canonical, both defined by
    `context-templates.md`: a standalone `- Fingerprint: `<16 hex>`` line (a
    repository index, under `## Scope`) or a combined
    `- Baseline and fingerprint: `<git revision>` / `<16 hex>`` line (a
    module or fallback document, under `## Identity and scope`). The field
    must appear inside the document's `<!-- AI-DLC:generated:start -->` /
    `-end -->` block and inside that specific metadata section. A
    human-authored note elsewhere in the document, a fenced-code example, or
    any other mention of the word "fingerprint" is ignored. A 40-character
    Git revision on the same line is never mistaken for the 16-character
    fingerprint, because it does not match the 16-hex-character shape.

    Returns "missing" when the generated block or metadata section is absent,
    or when that section has no canonical fingerprint field. Returns
    "malformed" when a fingerprint field line does not match either canonical
    shape, or when the generated markers themselves are malformed. Returns
    "ambiguous" when more than one canonical field is present, even if the
    values match, when a well-formed field coexists with a malformed one, or
    when more than one generated block exists. A line that merely contains
    the word "fingerprint" or "fingerprinted" is not a field. Never falls
    back to text outside the generated block, and never silently prefers one
    candidate over another.
    """
    block = parse_generated_block(markdown_text)
    if block.status == "missing":
        return FingerprintField("missing")
    if block.status != "ok":
        return FingerprintField("ambiguous" if block.status == "ambiguous" else "malformed")

    section = _section_lines(block.text, "## Identity and scope")
    if section is None:
        section = _section_lines(block.text, "## Scope")
    if section is None:
        return FingerprintField("missing")

    candidates: list[str] = []
    malformed = False
    for line in section:
        stripped = line.strip()
        lower = stripped.lower()
        if not (
            lower.startswith("- fingerprint:") or lower.startswith("- baseline and fingerprint:")
        ):
            continue
        match = FINGERPRINT_FIELD_PATTERN.match(stripped) or (
            BASELINE_AND_FINGERPRINT_FIELD_PATTERN.match(stripped)
        )
        if match:
            candidates.append(match.group(1))
        else:
            malformed = True

    if not candidates and not malformed:
        return FingerprintField("missing")
    if malformed:
        return FingerprintField("malformed" if not candidates else "ambiguous")
    if len(candidates) > 1:
        return FingerprintField("ambiguous")
    return FingerprintField("ok", candidates[0])


@dataclass(frozen=True)
class ValidationCheck:
    """One deterministic validation result.

    `status` is one of "passed", "failed", "unresolved", or
    "not_applicable". "unresolved" means the check could not be completed
    (missing configuration, an inaccessible repository, or a parsing
    failure) and must never be treated as passing.
    """

    name: str
    status: str
    detail: str


def _reference_check(name: str, status: str, ok_detail: str) -> ValidationCheck:
    if status == "ok":
        return ValidationCheck(name, "passed", ok_detail)
    if status == "external":
        return ValidationCheck(name, "not_applicable", "external or anchor reference")
    if status in {"unavailable", "unresolved"}:
        return ValidationCheck(name, "unresolved", f"reference status: {status}")
    return ValidationCheck(name, "failed", f"reference status: {status}")


def _budget_from_text(name: str, text: str, max_lines: int) -> ValidationCheck:
    lines = len(text.splitlines())
    if lines <= max_lines:
        return ValidationCheck(name, "passed", f"{lines} lines (budget {max_lines})")
    return ValidationCheck(name, "failed", f"{lines} lines exceeds budget {max_lines}")


def _budget_check(name: str, path: Path, max_lines: int) -> ValidationCheck:
    text, error = read_text_document(path)
    if error or text is None:
        status = "failed" if error and "not a regular file" in error else "unresolved"
        return ValidationCheck(name, status, error or f"{path} is not readable")
    return _budget_from_text(name, text, max_lines)


def _structure_from_text(name: str, text: str, required_heading: str) -> ValidationCheck:
    block = parse_generated_block(text)
    if block.status != "ok":
        return ValidationCheck(name, "failed", f"generated block status: {block.status}")
    if _section_lines(block.text, required_heading) is None:
        return ValidationCheck(
            name,
            "failed",
            f"missing required heading {required_heading!r} inside the generated block",
        )
    return ValidationCheck(name, "passed", f"markers and {required_heading!r} present")


def _structure_check(name: str, path: Path, required_heading: str) -> ValidationCheck:
    text, error = read_text_document(path)
    if error or text is None:
        status = "failed" if error and "not a regular file" in error else "unresolved"
        return ValidationCheck(name, status, error or f"{path} is not readable")
    return _structure_from_text(name, text, required_heading)


@dataclass(frozen=True)
class IndexIdentity:
    """How a repository index declares its own scope."""

    kind: str
    repository_id: str | None = None
    detail: str = ""


def resolve_index_identity(markdown_text: str, supplied_id: str | None) -> IndexIdentity:
    """Read index identity from generated `## Scope` metadata.

    A single `Repository ID`, with or without `Index: single-repository`,
    is a single-repository index. `Index: multi-repository` with no
    repository ID is an engagement index. Omitted arguments and the number
    of authorized roots are not used. A supplied ID must match the document.
    """
    block = parse_generated_block(markdown_text)
    if block.status != "ok":
        return IndexIdentity("unresolved", detail=f"generated block status: {block.status}")
    section = _section_lines(block.text, "## Scope")
    if section is None:
        return IndexIdentity("unresolved", detail="missing ## Scope inside the generated block")
    fields = parse_labeled_fields(section)
    if fields.status != "ok":
        return IndexIdentity("unresolved", detail=fields.detail)

    index_kind = fields.values.get("Index")
    repository_id = fields.values.get("Repository ID") or None
    if index_kind not in (None, "single-repository", "multi-repository"):
        return IndexIdentity("unresolved", detail=f"Index value {index_kind!r} is not recognized")
    if index_kind == "multi-repository":
        if repository_id is not None:
            return IndexIdentity(
                "conflict",
                detail="multi-repository index also declares a Repository ID",
            )
        if supplied_id is not None:
            return IndexIdentity(
                "conflict",
                detail=(
                    f"supplied index repository {supplied_id!r} conflicts with "
                    "declared multi-repository index"
                ),
            )
        return IndexIdentity("multi", detail="declared multi-repository engagement index")
    if not repository_id:
        return IndexIdentity(
            "unresolved",
            detail="single-repository index is missing Repository ID",
        )
    if supplied_id is not None and supplied_id != repository_id:
        return IndexIdentity(
            "conflict",
            repository_id=repository_id,
            detail=f"supplied index repository {supplied_id!r} != declared {repository_id!r}",
        )
    return IndexIdentity("single", repository_id=repository_id, detail="declared single-repository index")


def _resolved_inside(root: Path, relative_path: str) -> Path | None:
    candidate = (root.resolve() / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _is_evidence_path(value: str) -> bool:
    if "/" in value:
        return True
    return value.endswith(PATH_EXTENSIONS)


def _evidence_items(section: list[str]) -> list[tuple[str, str]]:
    """Return parseable evidence references, skipping symbol names and prose."""
    items: list[tuple[str, str]] = []
    for line in section:
        stripped = line.strip()
        link = EVIDENCE_LINK_PATTERN.match(stripped)
        if link:
            items.append(("link", link.group(1)))
            continue
        path = EVIDENCE_PATH_PATTERN.match(stripped)
        if path is None:
            continue
        value = path.group(1).strip()
        cross = CROSS_REPO_PATH_PATTERN.fullmatch(value)
        if cross and _is_evidence_path(cross.group(2)):
            items.append(("cross", value))
        elif _is_evidence_path(value):
            items.append(("repo-path", value))
    return items


def _compare_fingerprint(name: str, recorded: str, scope: Path) -> ValidationCheck:
    try:
        current, _ = content_fingerprint(scope)
    except OSError as error:
        return ValidationCheck(name, "unresolved", str(error))
    if current == recorded:
        return ValidationCheck(name, "passed", "fingerprint matches declared source")
    return ValidationCheck(name, "failed", f"recorded {recorded!r} != current {current!r}")


def _module_document_checks(
    label: str,
    module_path: Path,
    repository_id: str | None,
    module_id: str | None,
    source_path: str | None,
    authorized_roots: dict[str, Path],
    module_budget: int,
) -> list[ValidationCheck]:
    """Budget, structure, identity, freshness, and evidence for one module document."""
    checks: list[ValidationCheck] = []
    checks.append(_budget_check(f"modules:budget:{label}", module_path, module_budget))
    checks.append(_structure_check(f"modules:structure:{label}", module_path, "## Identity and scope"))

    text, error = read_text_document(module_path)
    identity_name = f"modules:identity:{label}"
    fingerprint_name = f"modules:fingerprint:{label}"
    if error or text is None:
        detail = error or f"{module_path} is not readable"
        status = "failed" if error and "not a regular file" in error else "unresolved"
        checks.append(ValidationCheck(identity_name, status, detail))
        checks.append(ValidationCheck(fingerprint_name, "unresolved", detail))
        return checks

    block = parse_generated_block(text)
    section = _section_lines(block.text, "## Identity and scope") if block.status == "ok" else None
    fields = parse_labeled_fields(section) if section is not None else None
    if block.status != "ok" or section is None or fields is None or fields.status != "ok":
        detail = "module metadata is missing or ambiguous"
        if fields is not None and fields.status != "ok":
            detail = fields.detail
        elif block.status != "ok":
            detail = f"generated block status: {block.status}"
        checks.append(ValidationCheck(identity_name, "unresolved", detail))
        checks.append(ValidationCheck(fingerprint_name, "unresolved", detail))
    else:
        declared_repo = fields.values.get("Repository ID") or ""
        declared_module = fields.values.get("Module ID") or ""
        declared_source = fields.values.get("Source") or ""
        conflicts: list[str] = []
        blocked: list[str] = []
        if not repository_id:
            blocked.append("index row has no repository identity")
        elif declared_repo != repository_id:
            conflicts.append(f"Repository ID {declared_repo!r} != index {repository_id!r}")
        if not module_id:
            blocked.append("index row has no module ID")
        elif declared_module != module_id:
            conflicts.append(f"Module ID {declared_module!r} != index {module_id!r}")
        if not source_path or not declared_source:
            blocked.append("source scope is missing from the index row or the module document")
        root = authorized_roots.get(repository_id) if repository_id else None
        agreed_scope: Path | None = None
        if source_path and declared_source:
            if root is None:
                blocked.append(f"repository {repository_id!r} is not in authorized_roots")
            elif not Path(root).resolve().is_dir():
                blocked.append(f"repository {repository_id!r} root is not accessible")
            else:
                index_scope = _resolved_inside(Path(root), source_path)
                document_scope = _resolved_inside(Path(root), declared_source)
                if index_scope is None or document_scope is None:
                    conflicts.append("declared source path escapes its repository root")
                elif index_scope != document_scope:
                    conflicts.append(f"Source {declared_source!r} != index {source_path!r}")
                else:
                    agreed_scope = index_scope
        if conflicts:
            checks.append(ValidationCheck(identity_name, "failed", "; ".join(conflicts)))
            checks.append(
                ValidationCheck(
                    fingerprint_name,
                    "unresolved",
                    "freshness is compared only after repository, module, and source agree",
                )
            )
        elif blocked:
            checks.append(ValidationCheck(identity_name, "unresolved", "; ".join(blocked)))
            checks.append(
                ValidationCheck(
                    fingerprint_name,
                    "unresolved",
                    "freshness is compared only after repository, module, and source agree",
                )
            )
        else:
            checks.append(ValidationCheck(identity_name, "passed", "repository, module, and source agree"))
            fingerprint_field = parse_recorded_fingerprint(text)
            if fingerprint_field.status != "ok" or fingerprint_field.value is None or agreed_scope is None:
                checks.append(
                    ValidationCheck(
                        fingerprint_name,
                        "unresolved",
                        f"fingerprint field status: {fingerprint_field.status}",
                    )
                )
            else:
                checks.append(_compare_fingerprint(fingerprint_name, fingerprint_field.value, agreed_scope))

    evidence_name = f"modules:evidence:{label}"
    if text is None or block.status != "ok":
        checks.append(ValidationCheck(evidence_name, "unresolved", "module document has no generated block"))
        return checks
    evidence_section = _section_lines(block.text, "## Evidence and existing docs")
    if evidence_section is None:
        checks.append(ValidationCheck(evidence_name, "not_applicable", "no evidence section was declared"))
        return checks
    items = _evidence_items(evidence_section)
    if not items:
        checks.append(ValidationCheck(evidence_name, "passed", "no path references declared"))
        return checks
    if not repository_id:
        checks.append(
            ValidationCheck(
                evidence_name,
                "unresolved",
                "evidence paths need the row repository identity and it is not established",
            )
        )
        return checks
    for kind, value in items:
        if kind == "link":
            status = classify_markdown_target(module_path, value, authorized_roots)
            checks.append(_reference_check(f"{evidence_name}:{value}", status, "evidence link resolves"))
        elif kind == "cross":
            repo_id, _, relative = value.partition(":")
            status = resolve_source_path(repo_id, relative, authorized_roots)
            checks.append(_reference_check(f"{evidence_name}:{value}", status, "evidence path exists"))
        else:
            status = resolve_source_path(repository_id, value, authorized_roots)
            checks.append(_reference_check(f"{evidence_name}:{value}", status, "evidence path exists"))
    return checks


def validate_generated_context(
    index_path: Path,
    authorized_roots: dict[str, Path],
    index_repository_id: str | None = None,
    index_budget: int = 150,
    module_budget: int = 300,
) -> list[ValidationCheck]:
    """Run every deterministic check against one generated context index.

    This function is read-only: it never writes, moves, or deletes a
    document. `authorized_roots` maps each repository ID this validation run
    is allowed to touch to that repository's root path. It is explicit
    workspace configuration, never guessed from the filesystem, and the
    number of roots does not decide whether the index is multi-repository.

    Index identity comes from canonical `## Scope` metadata inside the one
    generated block. A supplied `index_repository_id` must match that
    metadata. Only `Index: multi-repository` may omit a repository-wide
    fingerprint. Module freshness is still checked in that mode.

    A passing result never proves an Unknown is accurate, that a described
    dependency is correct, or that a claim is well-supported. Those
    judgments belong to independent review (`context-reviewer`).
    """
    if not index_path.exists():
        return [ValidationCheck("index:exists", "unresolved", f"{index_path} does not exist")]
    text, error = read_text_document(index_path)
    if error or text is None:
        status = "failed" if error and "not a regular file" in error else "unresolved"
        return [ValidationCheck("index:readable", status, error or f"{index_path} is not readable")]

    checks: list[ValidationCheck] = [
        _budget_from_text("index:budget", text, index_budget),
        _structure_from_text("index:structure", text, "## Scope"),
    ]
    identity = resolve_index_identity(text, index_repository_id)
    if identity.kind == "single":
        checks.append(ValidationCheck("index:identity", "passed", identity.detail))
        fingerprint_field = parse_recorded_fingerprint(text)
        if fingerprint_field.status != "ok" or fingerprint_field.value is None:
            checks.append(
                ValidationCheck(
                    "index:fingerprint",
                    "unresolved",
                    f"fingerprint field status: {fingerprint_field.status}",
                )
            )
        else:
            root = authorized_roots.get(identity.repository_id or "")
            if root is None:
                checks.append(
                    ValidationCheck(
                        "index:fingerprint",
                        "unresolved",
                        f"repository {identity.repository_id!r} is not in authorized_roots",
                    )
                )
            elif not Path(root).resolve().is_dir():
                checks.append(
                    ValidationCheck(
                        "index:fingerprint",
                        "unresolved",
                        f"repository {identity.repository_id!r} root is not accessible",
                    )
                )
            else:
                checks.append(
                    _compare_fingerprint("index:fingerprint", fingerprint_field.value, Path(root))
                )
    elif identity.kind == "multi":
        checks.append(ValidationCheck("index:identity", "passed", identity.detail))
        checks.append(
            ValidationCheck(
                "index:fingerprint",
                "not_applicable",
                "a declared multi-repository engagement index has no single-repository fingerprint",
            )
        )
    elif identity.kind == "conflict":
        checks.append(ValidationCheck("index:identity", "failed", identity.detail))
        checks.append(
            ValidationCheck("index:fingerprint", "unresolved", "index identity conflicts; freshness was not compared")
        )
    else:
        checks.append(ValidationCheck("index:identity", "unresolved", identity.detail))
        checks.append(
            ValidationCheck(
                "index:fingerprint",
                "unresolved",
                "index identity is unresolved, so freshness was not compared",
            )
        )

    block = parse_generated_block(text)
    if block.status != "ok":
        checks.append(
            ValidationCheck("modules:table", "unresolved", f"generated block status: {block.status}")
        )
        return checks
    generated = block.text
    module_ids = extract_table_column(generated, "## Modules", "Module")
    sources = extract_table_column(generated, "## Modules", "Source")
    contexts = extract_table_column(generated, "## Modules", "Context")
    repositories = extract_table_column(generated, "## Modules", "Repository")

    if module_ids.status != "ok":
        checks.append(
            ValidationCheck("modules:table", "unresolved", f"Modules table status: {module_ids.status}")
        )
        return checks
    checks.append(ValidationCheck("modules:table", "passed", f"{len(module_ids.values)} module rows"))

    row_repository_ids: list[str] | None
    if repositories.status == "ok":
        row_repository_ids = list(repositories.values)
        if identity.kind == "single":
            mismatches = [value for value in row_repository_ids if value != identity.repository_id]
            if mismatches:
                checks.append(
                    ValidationCheck(
                        "modules:repository-identity",
                        "failed",
                        f"Repository column conflicts with declared repository {identity.repository_id!r}",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        "modules:repository-identity",
                        "passed",
                        "Repository column matches the declared repository",
                    )
                )
        elif identity.kind == "multi":
            checks.append(
                ValidationCheck("modules:repository-identity", "passed", "repository identity is declared per row")
            )
        else:
            checks.append(
                ValidationCheck(
                    "modules:repository-identity",
                    "unresolved",
                    "Repository column is present, but the index identity is not established",
                )
            )
    elif identity.kind == "single" and identity.repository_id:
        row_repository_ids = [identity.repository_id] * len(module_ids.values)
        checks.append(
            ValidationCheck(
                "modules:repository-identity",
                "passed",
                "single-repository identity applies to every row",
            )
        )
    elif identity.kind == "multi":
        row_repository_ids = None
        checks.append(
            ValidationCheck(
                "modules:repository-identity",
                "unresolved",
                "multi-repository index has no readable Repository column; "
                "repository identity cannot be assigned without guessing",
            )
        )
    else:
        row_repository_ids = None
        checks.append(
            ValidationCheck(
                "modules:repository-identity",
                "unresolved",
                "no Repository column and no unambiguous repository identity",
            )
        )

    if row_repository_ids is not None:
        duplicate_identities = find_duplicate_identities(list(module_ids.values), row_repository_ids)
        if duplicate_identities:
            checks.append(
                ValidationCheck(
                    "modules:duplicate-identity",
                    "failed",
                    f"duplicate (repository, module) pairs: {duplicate_identities}",
                )
            )
        else:
            checks.append(ValidationCheck("modules:duplicate-identity", "passed", "no duplicate identities"))

    if contexts.status == "ok":
        duplicate_targets = find_duplicate_context_targets(list(contexts.values), index_path)
        if duplicate_targets:
            checks.append(
                ValidationCheck(
                    "modules:duplicate-context-target",
                    "failed",
                    f"duplicate resolved context targets: {duplicate_targets}",
                )
            )
        else:
            checks.append(
                ValidationCheck("modules:duplicate-context-target", "passed", "no duplicate targets")
            )
        for row_index, target in enumerate(contexts.values):
            resolved_target = _link_target(target)
            status = classify_markdown_target(
                index_path, resolved_target, authorized_roots, require_file=True
            )
            check_name = f"modules:link:{resolved_target}"
            checks.append(_reference_check(check_name, status, "link resolves"))
            if status != "ok":
                continue
            module_path = (index_path.parent / resolved_target.split("#", 1)[0]).resolve()
            repository_id = row_repository_ids[row_index] if row_repository_ids else None
            source_path = sources.values[row_index] if sources.status == "ok" else None
            checks.extend(
                _module_document_checks(
                    resolved_target,
                    module_path,
                    repository_id,
                    module_ids.values[row_index],
                    source_path,
                    authorized_roots,
                    module_budget,
                )
            )
    else:
        checks.append(
            ValidationCheck("modules:context-column", "unresolved", f"Context column status: {contexts.status}")
        )

    if sources.status == "ok" and row_repository_ids is not None:
        entries = list(zip(row_repository_ids, sources.values))
        problems = find_stale_source_paths(entries, authorized_roots)
        for entry in entries:
            check_name = f"modules:source:{entry[0]}:{entry[1]}"
            status = problems.get(entry, "ok")
            checks.append(_reference_check(check_name, status, "source path exists"))
    elif sources.status != "ok":
        checks.append(
            ValidationCheck("modules:source-column", "unresolved", f"Source column status: {sources.status}")
        )

    return checks

def cli_validate(argv: list[str]) -> int:
    """Command-line entry point: `context_tools.py validate ...`.

    Run from the plugin's own installation, for example:
    `python3 <plugin-root>/scripts/context_tools.py validate <index-path>
    --root <repo-id>=<repo-root> [--root ...] [--index-repository-id <id>]`.
    Do not assume this script lives in the target repository's current
    working directory; it lives inside the installed plugin.

    Exit code 1 means at least one check failed. That takes precedence when
    failed and unresolved checks are both present. Exit code 2 means no
    check failed, but at least one is unresolved, or the arguments are
    invalid. Exit code 0 means every check passed or was not applicable.
    An incomplete run never returns 0.
    """
    parser = argparse.ArgumentParser(prog="context_tools.py validate")
    parser.add_argument("index_path", type=Path)
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        metavar="REPO_ID=PATH",
        help="authorized repository root, repeatable",
    )
    parser.add_argument("--index-repository-id", default=None)
    parser.add_argument("--index-budget", type=int, default=150)
    parser.add_argument("--module-budget", type=int, default=300)
    args = parser.parse_args(argv)

    authorized_roots: dict[str, Path] = {}
    for entry in args.root:
        if "=" not in entry:
            print(f"error: --root must be REPO_ID=PATH, got {entry!r}", file=sys.stderr)
            return 2
        repo_id, _, path = entry.partition("=")
        authorized_roots[repo_id] = Path(path)

    checks = validate_generated_context(
        args.index_path,
        authorized_roots,
        index_repository_id=args.index_repository_id,
        index_budget=args.index_budget,
        module_budget=args.module_budget,
    )

    failed = [c for c in checks if c.status == "failed"]
    unresolved = [c for c in checks if c.status == "unresolved"]
    for check in checks:
        print(f"{check.status:14} {check.name:40} {check.detail}")

    if failed:
        return 1
    if unresolved:
        return 2
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        raise SystemExit(cli_validate(sys.argv[2:]))
    print("usage: context_tools.py validate <index-path> --root ID=PATH [...]", file=sys.stderr)
    raise SystemExit(2)
