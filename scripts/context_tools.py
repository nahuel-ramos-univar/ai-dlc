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
GENERATED_BLOCK_PATTERN = re.compile(
    r"<!--\s*AI-DLC:generated:start\s*-->(.*?)<!--\s*AI-DLC:generated:end\s*-->",
    re.DOTALL,
)
FINGERPRINT_FIELD_PATTERN = re.compile(r"^-\s*Fingerprint:\s*`([0-9a-f]{16})`\s*$")
BASELINE_AND_FINGERPRINT_FIELD_PATTERN = re.compile(
    r"^-\s*Baseline and fingerprint:\s*`[^`]+`\s*/\s*`([0-9a-f]{16})`\s*$"
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


def resolve_markdown_links(
    markdown_path: Path, authorized_roots: dict[str, Path]
) -> dict[str, str]:
    """Classify each local Markdown link in `markdown_path`.

    `authorized_roots` maps a repository ID to that repository's root path;
    it must be explicit workspace configuration, never guessed from the
    filesystem or expanded to the whole filesystem. Status is one of:

    - "ok": the target exists inside an authorized, available root.
    - "missing": the target's owning authorized root is available, but the
      target does not exist there.
    - "unavailable": the target falls under a configured root that is not
      (or is no longer) an accessible directory.
    - "unresolvable": the target, after resolving symlinks and `..`
      segments, does not fall under any authorized root. This is a hard
      rejection of parent-directory traversal and symlink escape, not a
      permissive fallback to the whole filesystem.
    - "external": a URL or a same-document anchor, not verified here.

    An unavailable, unresolvable, or external reference is never reported as
    "ok".
    """
    text = markdown_path.read_text(encoding="utf-8")
    resolved_roots = _resolve_roots(authorized_roots)
    statuses: dict[str, str] = {}
    for target in MARKDOWN_LINK_PATTERN.findall(text):
        if "://" in target or target.startswith("#"):
            statuses[target] = "external"
            continue
        local_path = target.split("#", 1)[0]
        if not local_path:
            statuses[target] = "external"
            continue
        resolved = (markdown_path.parent / local_path).resolve()
        root = _best_matching_root(resolved, resolved_roots)
        if root is None:
            statuses[target] = "unresolvable"
        elif not root.is_dir():
            statuses[target] = "unavailable"
        else:
            statuses[target] = "ok" if resolved.exists() else "missing"
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


def _section_lines(markdown_text: str, heading: str) -> list[str] | None:
    """Return the raw lines of the section under `heading`, or None if absent.

    Bounded by the next heading of the same or higher level. Lines inside a
    fenced code block are dropped, so a documented example is never read as
    live content.
    """
    heading_level = len(heading) - len(heading.lstrip("#"))
    lines = markdown_text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return None
    section: list[str] = []
    in_fence = False
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading_match = HEADING_PATTERN.match(stripped)
        if heading_match and len(heading_match.group(1)) <= heading_level:
            break
        section.append(line)
    return section


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

    Returns "missing" when no metadata section or no fingerprint-labeled
    line is found there, "malformed" when a fingerprint-labeled line does
    not match either canonical shape, and "ambiguous" when more than one
    differing candidate is found, or when a well-formed field coexists with
    a malformed one on another line. Never silently prefers one candidate
    over another.
    """
    block_match = GENERATED_BLOCK_PATTERN.search(markdown_text)
    block = block_match.group(1) if block_match else markdown_text

    section = _section_lines(block, "## Identity and scope")
    if section is None:
        section = _section_lines(block, "## Scope")
    if section is None:
        return FingerprintField("missing")

    candidates: list[str] = []
    malformed = False
    for line in section:
        stripped = line.strip()
        if "fingerprint" not in stripped.lower():
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
    if len(set(candidates)) > 1:
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


def _budget_check(name: str, path: Path, max_lines: int) -> ValidationCheck:
    if not path.exists():
        return ValidationCheck(name, "unresolved", f"{path} does not exist")
    lines, _ = document_metrics(path)
    if lines <= max_lines:
        return ValidationCheck(name, "passed", f"{lines} lines (budget {max_lines})")
    return ValidationCheck(name, "failed", f"{lines} lines exceeds budget {max_lines}")


def _structure_check(name: str, path: Path, required_heading: str) -> ValidationCheck:
    if not path.exists():
        return ValidationCheck(name, "unresolved", f"{path} does not exist")
    text = path.read_text(encoding="utf-8")
    if GENERATED_BLOCK_PATTERN.search(text) is None:
        return ValidationCheck(name, "failed", "missing AI-DLC:generated markers")
    if _section_lines(text, required_heading) is None:
        return ValidationCheck(name, "failed", f"missing required heading {required_heading!r}")
    return ValidationCheck(name, "passed", f"markers and {required_heading!r} present")


def _module_fingerprint_check(
    label: str,
    module_path: Path,
    repository_id: str | None,
    source_path: str | None,
    authorized_roots: dict[str, Path],
) -> ValidationCheck:
    name = f"modules:fingerprint:{label}"
    if not module_path.exists():
        return ValidationCheck(name, "unresolved", f"{module_path} does not exist")
    fingerprint_field = parse_recorded_fingerprint(module_path.read_text(encoding="utf-8"))
    if fingerprint_field.status != "ok":
        return ValidationCheck(name, "unresolved", f"fingerprint field status: {fingerprint_field.status}")
    if repository_id is None or source_path is None:
        return ValidationCheck(name, "not_applicable", "repository or source path unknown for this row")
    root = authorized_roots.get(repository_id)
    if root is None:
        return ValidationCheck(name, "unresolved", f"repository {repository_id!r} is not in authorized_roots")
    root_resolved = Path(root).resolve()
    if not root_resolved.is_dir():
        return ValidationCheck(name, "unresolved", f"repository {repository_id!r} root is not accessible")
    scope = (root_resolved / source_path).resolve()
    try:
        scope.relative_to(root_resolved)
    except ValueError:
        return ValidationCheck(name, "unresolved", "declared source path escapes its repository root")
    try:
        current, _ = content_fingerprint(scope)
    except OSError as error:
        return ValidationCheck(name, "unresolved", str(error))
    if current == fingerprint_field.value:
        return ValidationCheck(name, "passed", "fingerprint matches declared source")
    return ValidationCheck(name, "failed", f"recorded {fingerprint_field.value!r} != current {current!r}")


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
    is allowed to touch to that repository's root path; it must be explicit
    workspace configuration supplied by the caller, never guessed from the
    filesystem. `index_repository_id` is the repository ID this index's own
    `## Scope` section declares; leave it `None` only for a true
    multi-repository engagement index that declares repository identity per
    row in the Modules table instead.

    A passing result never proves an Unknown is accurate, that a described
    dependency is correct, or that a claim is well-supported; those
    judgments belong to independent review (`context-reviewer`), not to
    this function.
    """
    checks: list[ValidationCheck] = []

    if not index_path.exists():
        return [ValidationCheck("index:exists", "unresolved", f"{index_path} does not exist")]

    checks.append(_budget_check("index:budget", index_path, index_budget))
    checks.append(_structure_check("index:structure", index_path, "## Scope"))

    if index_repository_id is None:
        # A true multi-repository engagement index has no single owning
        # repository, so it has no one-repository fingerprint to compare.
        # This is expected shape, not a problem, so it is not_applicable
        # rather than unresolved.
        checks.append(
            ValidationCheck(
                "index:fingerprint",
                "not_applicable",
                "no index_repository_id; a multi-repository engagement index "
                "has no single-repository fingerprint to compare",
            )
        )
    else:
        fingerprint_field = parse_recorded_fingerprint(index_path.read_text(encoding="utf-8"))
        if fingerprint_field.status != "ok":
            checks.append(
                ValidationCheck(
                    "index:fingerprint",
                    "unresolved",
                    f"fingerprint field status: {fingerprint_field.status}",
                )
            )
        else:
            root = authorized_roots.get(index_repository_id)
            if root is None:
                checks.append(
                    ValidationCheck(
                        "index:fingerprint",
                        "unresolved",
                        f"repository {index_repository_id!r} is not in authorized_roots",
                    )
                )
            else:
                try:
                    current, _ = content_fingerprint(root)
                except OSError as error:
                    checks.append(ValidationCheck("index:fingerprint", "unresolved", str(error)))
                else:
                    if current == fingerprint_field.value:
                        checks.append(ValidationCheck("index:fingerprint", "passed", "fingerprint matches"))
                    else:
                        checks.append(
                            ValidationCheck(
                                "index:fingerprint",
                                "failed",
                                f"recorded {fingerprint_field.value!r} != current {current!r}",
                            )
                        )

    text = index_path.read_text(encoding="utf-8")
    module_ids = extract_table_column(text, "## Modules", "Module")
    sources = extract_table_column(text, "## Modules", "Source")
    contexts = extract_table_column(text, "## Modules", "Context")
    repositories = extract_table_column(text, "## Modules", "Repository")

    if module_ids.status != "ok":
        checks.append(
            ValidationCheck("modules:table", "unresolved", f"Modules table status: {module_ids.status}")
        )
        return checks
    checks.append(ValidationCheck("modules:table", "passed", f"{len(module_ids.values)} module rows"))

    if len(authorized_roots) > 1 and repositories.status != "ok":
        checks.append(
            ValidationCheck(
                "modules:repository-identity",
                "unresolved",
                "multi-repository scope but the Modules table has no readable "
                "Repository column; repository identity cannot be assigned "
                "without guessing",
            )
        )
        row_repository_ids: list[str] | None = None
    elif repositories.status == "ok":
        row_repository_ids = list(repositories.values)
    elif index_repository_id is not None:
        row_repository_ids = [index_repository_id] * len(module_ids.values)
    else:
        row_repository_ids = None
        checks.append(
            ValidationCheck(
                "modules:repository-identity",
                "unresolved",
                "no Repository column and no index_repository_id was supplied",
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
            checks.append(
                ValidationCheck("modules:duplicate-identity", "passed", "no duplicate identities")
            )

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

        link_statuses = resolve_markdown_links(index_path, authorized_roots)
        for row_index, target in enumerate(contexts.values):
            resolved_target = _link_target(target)
            status = link_statuses.get(resolved_target, "unresolved")
            check_name = f"modules:link:{resolved_target}"
            if status == "ok":
                checks.append(ValidationCheck(check_name, "passed", "link resolves"))
                module_path = (index_path.parent / resolved_target.split("#", 1)[0]).resolve()
                checks.append(_budget_check(f"modules:budget:{resolved_target}", module_path, module_budget))
                checks.append(
                    _structure_check(
                        f"modules:structure:{resolved_target}", module_path, "## Identity and scope"
                    )
                )
                checks.append(
                    _module_fingerprint_check(
                        resolved_target,
                        module_path,
                        row_repository_ids[row_index] if row_repository_ids else None,
                        sources.values[row_index] if sources.status == "ok" else None,
                        authorized_roots,
                    )
                )
            elif status == "external":
                checks.append(ValidationCheck(check_name, "not_applicable", "external or anchor link"))
            else:
                checks.append(ValidationCheck(check_name, "failed", f"link status: {status}"))
    else:
        checks.append(
            ValidationCheck("modules:context-column", "unresolved", f"Context column status: {contexts.status}")
        )

    if sources.status == "ok" and row_repository_ids is not None:
        entries = list(zip(row_repository_ids, sources.values))
        problems = find_stale_source_paths(entries, authorized_roots)
        for entry in entries:
            check_name = f"modules:source:{entry[0]}:{entry[1]}"
            if entry in problems:
                checks.append(ValidationCheck(check_name, "failed", f"source path status: {problems[entry]}"))
            else:
                checks.append(ValidationCheck(check_name, "passed", "source path exists"))
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
