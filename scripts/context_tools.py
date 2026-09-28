#!/usr/bin/env python3
"""Deterministic helpers for AI-DLC repository context.

These helpers support skill-directed discovery. They do not scan, write, or
choose repositories on their own.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
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
