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
from urllib.parse import urlsplit

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
PROJECT_REFERENCE_HEADING = "## Project references"
PROJECT_REFERENCE_FIELDS = (
    "Jira site",
    "Jira project",
    "Jira board",
    "Figma reference",
    "Figma role",
)
FIGMA_ROLES = frozenset({"approved-design", "design-system", "inspiration"})
# Looser than LABELED_FIELD_PATTERN on purpose: it matches a recognized field
# name whether or not its value is in the canonical backtick format, so a
# malformed or duplicated occurrence of a *recognized* field is never
# invisible to duplicate/malformed detection the way it would be if only
# the canonical pattern were used to find candidates.
PROJECT_REFERENCE_LINE_PATTERN = re.compile(r"^-\s+([^:`]+):\s*(.*)$")
CANONICAL_VALUE_PATTERN = re.compile(r"^`([^`]*)`$")


@dataclass(frozen=True)
class RepositoryScope:
    requested_path: Path
    git_root: Path | None
    kind: str
    enclosing_git_root: Path | None = None


class GitDiscoveryError(RuntimeError):
    """A recognizable Git checkout could not be queried.

    This is distinct from a genuinely unversioned tree. Callers must not
    replace it with a filesystem walk that ignores `.gitignore`.
    """


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


def bugbot_reprompt_allowed(decision: str, same_run: bool) -> bool:
    """Decide whether a recorded Bugbot decision may be re-proposed now.

    `decision` is the value recorded under `## Bugbot decisions` in
    `bugbot-configuration.md`: `"approved"`, `"declined"`, or `"deferred"`.
    A `declined` decision is never re-proposed by this helper; only an
    explicit user request to reconsider does that, and that request is a
    separate action outside this function. A `deferred` decision is not
    re-proposed within the same run, but may be re-proposed on a later run.
    An `approved` decision needs no reprompt; apply the existing approval
    instead of asking again. Any other value is treated as no decision on
    record, so a prompt is allowed.
    """
    if decision == "declined":
        return False
    if decision == "deferred":
        return not same_run
    if decision == "approved":
        return False
    return True


def diff_module_sources(recorded: list[str], current: list[str]) -> dict[str, tuple[str, ...]]:
    """Compare recorded module source paths with the paths found now.

    Returns `added`, `removed`, and `unchanged`, each a sorted tuple of
    normalized repository-relative paths. A rename is reported as one
    removal plus one addition; this helper does not guess that two
    different paths are the same module.
    """

    def normalize(path: str) -> str:
        return path.strip().removeprefix("./")

    previous = {normalize(path) for path in recorded}
    found = {normalize(path) for path in current}
    return {
        "added": tuple(sorted(found - previous)),
        "removed": tuple(sorted(previous - found)),
        "unchanged": tuple(sorted(previous & found)),
    }


def scope_verification_status(available: list[bool]) -> str:
    """Summarize whether every requested scope could actually be checked.

    `"complete"` only when every scope was available. Any unavailable scope
    is `"partial"` when something else was available, or `"unavailable"`
    when nothing was. An empty request is `"unavailable"`: there is nothing
    to call current. This never returns a status that means "up to date."
    """
    if not available or not any(available):
        return "unavailable"
    if all(available):
        return "complete"
    return "partial"


def resolve_placement(persisted: str | None) -> str:
    """Return `distributed` or `adopted-coordinator` from persisted config.

    Missing config stays distributed. A recorded value outside those two
    modes is a conflict and raises; callers must surface it instead of
    picking a destination. A repository or folder name is not an input:
    this function cannot adopt a coordinator from a name.
    """
    if persisted is None or persisted == "":
        return "distributed"
    if persisted in {"distributed", "adopted-coordinator"}:
        return persisted
    raise ValueError(f"conflicting placement value: {persisted!r}")


def module_context_destination(placement: str, repository_id: str, module_id: str) -> str:
    """Return the context path required by the resolved placement mode.

    Adopted-coordinator mode always returns
    `aidlc-docs/context/<repo-id>/<module-id>.md`. Source-repository
    writability is intentionally not an argument: it must not move that
    file back into the source repository. Distributed mode returns the
    colocated `AIDLC_CONTEXT.md` name; the caller places it at the approved
    module root.
    """
    mode = resolve_placement(placement)
    if not REPOSITORY_ID_PATTERN.fullmatch(repository_id):
        raise ValueError("repository ID must match [a-z0-9-]")
    if not REPOSITORY_ID_PATTERN.fullmatch(module_id):
        raise ValueError("module ID must match [a-z0-9-]")
    if mode == "adopted-coordinator":
        return f"aidlc-docs/context/{repository_id}/{module_id}.md"
    return "AIDLC_CONTEXT.md"


def proposal_is_current(
    proposed_source_fingerprint: str,
    current_source_fingerprint: str,
    proposed_destination: str | None,
    current_destination: str | None,
) -> bool:
    """True only when source evidence and the destination are still the proposal's inputs.

    A newer source fingerprint or a destination edited after the proposal was
    prepared makes the proposal stale. The caller must recalculate and ask
    again before writing. `None` matches only `None`, so a file that
    appeared or disappeared since the proposal is also stale.
    """
    return (
        proposed_source_fingerprint == current_source_fingerprint
        and proposed_destination == current_destination
    )


def unrelated_rules_preserved(existing: list[str], approved_writes: list[str]) -> tuple[str, ...]:
    """Return existing rule paths that an approved write set must leave untouched."""
    approved = set(approved_writes)
    return tuple(path for path in existing if path not in approved)


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


GITMODULES_PATH_PATTERN = re.compile(r"^\s*path\s*=\s*(.+?)\s*$")


def is_declared_submodule(path: Path, scope_root: Path) -> bool:
    """True when `path` is registered as a submodule in `scope_root/.gitmodules`.

    A nested `.git` marker alone (what `is_nested_git_root` checks) does not
    distinguish a declared Git submodule from a stray nested checkout that
    happens to sit inside the scope. Only a path actually listed in
    `.gitmodules` is a real submodule; anything else nested is an ordinary
    nested repository and must not be reported as "submodule unavailable."
    """
    gitmodules = Path(scope_root) / ".gitmodules"
    if not gitmodules.is_file():
        return False
    try:
        relative = Path(path).resolve().relative_to(Path(scope_root).resolve()).as_posix()
    except ValueError:
        return False
    try:
        lines = gitmodules.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return False
    for line in lines:
        match = GITMODULES_PATH_PATTERN.match(line)
        if match and match.group(1) == relative:
            return True
    return False


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


def _nearest_git_marker(scope: Path) -> Path | None:
    """Return the nearest `.git` file or directory at or above `scope`.

    Walks parents of the resolved scope, so a nested module finds the
    checkout that contains it, and an explicitly selected symlink scope root
    is judged by the tree it points at. A `.git` file (a linked worktree or
    submodule) counts the same as a `.git` directory. Returns `None` only
    when no marker exists: that is a genuinely unversioned tree.
    """
    try:
        current = scope.resolve()
    except OSError:
        current = Path(scope)
    while True:
        marker = current / ".git"
        try:
            recognizable = marker.is_symlink() or marker.exists()
        except OSError:
            recognizable = False
        if recognizable:
            return marker
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _git_root_and_relative_scope(scope: Path) -> tuple[Path, str] | None:
    """Return `(resolved git root, scope's root-relative POSIX path)`.

    Returns `None` only for a genuinely unversioned tree: no `.git` marker
    at or above `scope`. A recognizable checkout whose `git rev-parse` fails
    raises `GitDiscoveryError` instead of looking like an unversioned tree.
    Returning `""` for the relative path means `scope` is the Git root itself.
    """
    root_output = git_output(scope, "rev-parse", "--show-toplevel")
    if root_output is None:
        if _nearest_git_marker(scope) is not None:
            raise GitDiscoveryError(
                "Git metadata is present, but `git rev-parse --show-toplevel` "
                f"failed for {scope}. Refusing to scan this checkout as an "
                "unversioned tree."
            )
        return None
    git_root = Path(root_output).resolve()
    resolved_scope = scope.resolve()
    try:
        relative = resolved_scope.relative_to(git_root).as_posix()
    except ValueError:
        raise GitDiscoveryError(
            f"Git reported {git_root} as the toplevel, but {scope} does not "
            "resolve inside it. Refusing to scan this checkout as an unversioned tree."
        ) from None
    return git_root, ("" if relative == "." else relative)


def _run_git_ls_files(git_root: Path, pathspec: str, *extra_args: str) -> list[str]:
    """Run `git ls-files` and return NUL-delimited repository-relative paths.

    Raises `RuntimeError` on a non-zero exit so a real Git failure for a
    Git-backed scope is reported, never silently replaced by the filesystem
    walk used for unversioned trees.
    """
    args = ["ls-files", "-z", *extra_args, "--", pathspec or "."]
    result = subprocess.run(
        ["git", *args],
        cwd=git_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed in {git_root}: {stderr}")
    return [chunk.decode("utf-8") for chunk in result.stdout.split(b"\0") if chunk]


def _git_scoped_relative_paths(scope: Path) -> list[str] | None:
    """Return paths relative to `scope`, discovered through Git.

    Combines every tracked file (`git ls-files`) with every untracked file
    `.gitignore` (and other standard excludes) does not exclude (`git
    ls-files --others --exclude-standard`), both restricted to `scope`. A
    tracked file is always included even if a later-added ignore pattern
    would exclude it if it were untracked; only untracked-and-ignored files
    are left out. Returns `None` when `scope` is not inside a Git working
    tree, so the caller falls back to a filesystem walk for a genuinely
    unversioned tree.
    """
    located = _git_root_and_relative_scope(scope)
    if located is None:
        return None
    git_root, relative_scope = located
    tracked = _run_git_ls_files(git_root, relative_scope)
    untracked = _run_git_ls_files(git_root, relative_scope, "--others", "--exclude-standard")
    prefix = f"{relative_scope}/" if relative_scope else ""
    paths: list[str] = []
    for repo_relative in (*tracked, *untracked):
        if prefix:
            if repo_relative.startswith(prefix):
                paths.append(repo_relative[len(prefix) :])
            # else: outside the requested scope; the pathspec should prevent
            # this, but never let an out-of-scope path enter the hash.
        else:
            paths.append(repo_relative)
    return paths


def _blocked_by_nested_symlink(path: Path, scope: Path) -> bool:
    """True when `path` is reached through a nested symlink or leaves `scope`.

    The scope root may itself be a symlink; that link is the selected root
    and is not treated as nested. Every component from the scope down to the
    file is checked before the file is read. A component that is a symlink,
    or a resolved file that does not stay inside the resolved scope, is
    excluded.
    """
    try:
        parts = path.relative_to(scope).parts
    except ValueError:
        return True
    current = scope
    for part in parts:
        current = current / part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    try:
        current.resolve().relative_to(scope.resolve())
    except (OSError, ValueError):
        return True
    return False


def _nested_git_root_between(path: Path, scope: Path) -> bool:
    """True when a directory strictly between `scope` and `path` is a nested Git root.

    Git itself does not expand the contents of an embedded repository that
    is not a declared submodule, so this is defense in depth rather than the
    primary exclusion mechanism for the Git-backed discovery path.
    """
    current = path.parent
    while True:
        if is_nested_git_root(current, scope):
            return True
        if current == scope:
            return False
        parent = current.parent
        if parent == current:
            return False
        current = parent


def iter_fingerprint_files(scope_root: Path) -> list[Path]:
    """Return sorted regular files for a declared source scope.

    For a Git-backed scope, files are discovered through Git: every tracked
    path plus every untracked path `.gitignore` does not exclude. An
    ignored-and-untracked file never enters the hash, and a tracked file is
    never dropped merely because a later ignore rule would exclude it if it
    were untracked. A Git query failure for a Git-backed scope raises
    (`RuntimeError`); it is never silently replaced by the filesystem walk.

    For a genuinely unversioned tree, files are discovered with a filesystem
    walk instead. Generated context and common cache/build directories are
    pruned. Nested Git repositories are skipped so a parent hash does not mix
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

    git_relative_paths = _git_scoped_relative_paths(scope)
    if git_relative_paths is not None:
        files: list[Path] = []
        for relative in git_relative_paths:
            path = scope / relative
            if _blocked_by_nested_symlink(path, scope) or not path.is_file():
                continue
            if is_excluded(path, scope) or _nested_git_root_between(path, scope):
                continue
            files.append(path)
        return sorted(files, key=lambda item: item.relative_to(scope).as_posix())

    files = []
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
    """SHA-256 over NUL-delimited relative path and file-content hashes.

    This is a working-tree snapshot: each included file's content hash comes
    from `path.read_bytes()`, the bytes currently on disk. It never reads the
    Git index (staged content) separately. When a file's staged content
    differs from its current working-tree content, this fingerprint reflects
    only the working tree; call `staged_working_tree_divergence` to report
    that difference, never fold it into this value or its description.
    """
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


def staged_working_tree_divergence(scope_root: Path) -> tuple[str, ...]:
    """Return paths, relative to `scope_root`, staged differently than on disk.

    `content_fingerprint` only ever hashes working-tree bytes; it has no
    visibility into the Git index. This helper reports, separately, which
    files currently staged for commit have working-tree content that
    differs from what is staged (`git diff --name-only`, scoped to
    `scope_root`). An empty tuple means Git checked and found no divergence,
    or the tree is unversioned. A recognizable checkout whose `git diff`
    fails raises `GitDiscoveryError`: that comparison is unavailable, and
    an empty tuple must not stand in for the failure. This is reporting
    only: it does not change the fingerprint and must never be folded into
    it or its freshness comparison.
    """
    scope = Path(scope_root)
    if not scope.exists() or not scope.is_dir():
        return ()
    located = _git_root_and_relative_scope(scope)
    if located is None:
        return ()
    git_root, relative_scope = located
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", relative_scope or "."],
        cwd=git_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise GitDiscoveryError(
            "Git metadata is present, but `git diff --name-only` failed for "
            f"{scope}. The staged-versus-working-tree comparison is "
            "unavailable; this is not an empty difference list."
        )
    prefix = f"{relative_scope}/" if relative_scope else ""
    paths: list[str] = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        if prefix:
            if line.startswith(prefix):
                paths.append(line[len(prefix) :])
        else:
            paths.append(line)
    return tuple(sorted(paths))


def classify_fingerprint_change(recorded: str | None, current: str) -> str:
    """Classify a recorded fingerprint against a freshly computed one.

    Returns `"unavailable"` when no prior fingerprint was recorded (first-time
    generation, or a missing/incompatible baseline) — rediscovery is needed,
    not a no-change claim. Returns `"unchanged"` when the recorded and
    current values match exactly: a sync may stop without rewriting
    documents, creating a Canvas, or asking for approval. Returns `"changed"`
    otherwise, meaning a proposal is needed. This helper only compares the
    two strings it receives; it does not read files or decide what counts as
    the relevant scope.
    """
    if not recorded:
        return "unavailable"
    return "unchanged" if recorded == current else "changed"


def context_sync_outcome(
    context_change: str,
    bugbot_pending: bool,
    project_rule_pending: bool,
    legacy_cleanup_pending: bool,
    project_reference_pending: bool = False,
) -> str:
    """Combine the three change sets into Stage 2's reachable outcome.

    `context_change` is `classify_fingerprint_change`'s result for the
    source-document part of change set A: it compares the content
    fingerprint of examined source paths, and generated configuration (for
    example `## Project references`) never enters that fingerprint. An
    unchanged source fingerprint is not the same thing as "all of change
    set A is unchanged" — a pending, user-requested `## Project references`
    update (a different Jira board, a different Figma reference) is also
    part of set A, and it does not require regenerating module context,
    rewriting repository prose, or touching a timestamp. Pass that pending
    state explicitly as `project_reference_pending`; callers derive it from
    comparing the current confirmed configuration against what the user is
    now requesting, not from `classify_fingerprint_change`.

    `bugbot_pending`, `project_rule_pending`, and `legacy_cleanup_pending`
    report whether change sets B and C each still have actionable,
    not-already-declined work; callers derive these from
    `bugbot_reprompt_allowed` and the recorded Bugbot/project-rule/legacy
    decisions, not from re-scanning the repository. A declined or
    already-applied proposal is not pending work in any of these inputs.

    Returns `"no_relevant_changes"` only when the source fingerprint is
    `"unchanged"`, no project-reference update is pending, and no other set
    has pending work: a full no-op, with no write and no new approval
    question. Returns `"context_current_migration_pending"` when the source
    fingerprint is `"unchanged"`, no project-reference update is pending,
    but set B or C still has pending work: an unchanged source must never
    make that pending work unreachable. Returns `"relevant_updates_found"`
    for every other combination, including an `"unavailable"` or `"changed"`
    source fingerprint, or a pending project-reference update on its own —
    a configuration-only proposal is reachable even when the source
    fingerprint is `"unchanged"`.
    """
    source_unchanged = context_change == "unchanged" and not project_reference_pending
    other_sets_pending = bugbot_pending or project_rule_pending or legacy_cleanup_pending
    if source_unchanged and not other_sets_pending:
        return "no_relevant_changes"
    if source_unchanged and other_sets_pending:
        return "context_current_migration_pending"
    return "relevant_updates_found"


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


def _read_candidate_or_document(
    path: Path, candidate_content: dict[Path, str] | None
) -> tuple[str | None, str | None]:
    """Read `path` from a candidate-content mapping first, then from disk.

    `candidate_content` maps a document's intended final absolute path to
    its proposed text, for a document not yet written there. A path present
    in the mapping (checked both as given and resolved, so the caller does
    not have to normalize keys) is read from the mapping even when a stale
    file already exists on disk at that path, so validation reflects the
    proposal rather than the file it would replace. This function only
    reads; presence in the mapping never authorizes a write.
    """
    if candidate_content:
        if path in candidate_content:
            return candidate_content[path], None
        try:
            resolved = path.resolve()
        except OSError:
            resolved = None
        if resolved is not None and resolved in candidate_content:
            return candidate_content[resolved], None
    return read_text_document(path)


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
    resolved: Path,
    resolved_roots: dict[str, Path],
    *,
    require_file: bool = False,
    candidate_paths: frozenset[Path] = frozenset(),
) -> str:
    root = _best_matching_root(resolved, resolved_roots)
    if root is None:
        return "unresolvable"
    if not root.is_dir():
        return "unavailable"
    try:
        if resolved.is_symlink():
            return "unresolvable"
    except OSError:
        return "unresolvable"
    is_candidate = resolved in candidate_paths
    if resolved.exists():
        if require_file and not resolved.is_file():
            return "not_a_file"
        return "ok"
    if is_candidate:
        return "ok"
    return "missing"


def classify_markdown_target(
    document_path: Path,
    target: str,
    authorized_roots: dict[str, Path],
    *,
    require_file: bool = False,
    candidate_paths: frozenset[Path] = frozenset(),
) -> str:
    """Classify one Markdown link target against authorized roots.

    `require_file` is for context documents, which must be regular files.
    Source scopes and other existing paths may be directories.

    `candidate_paths` is an optional set of resolved absolute paths for
    documents proposed but not yet written at their intended final
    location (see `validate_generated_context`'s `candidate_content`). A
    target resolving to one of those paths is treated as present even
    though nothing exists there on disk yet; it still must fall inside an
    authorized, available root to avoid "unresolvable" or "unavailable".
    """
    if "://" in target or target.startswith("#"):
        return "external"
    local_path = target.split("#", 1)[0]
    if not local_path:
        return "external"
    resolved = (document_path.parent / local_path).resolve()
    return _classify_local_target(
        resolved,
        _resolve_roots(authorized_roots),
        require_file=require_file,
        candidate_paths=candidate_paths,
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


@dataclass(frozen=True)
class LiveSection:
    """One live section, or why it is not an unambiguous match.

    `status` is "ok", "missing", or "ambiguous". "ambiguous" means the same
    heading appears more than once outside fenced examples. Callers must not
    read `lines` unless status is "ok".
    """

    status: str
    lines: tuple[str, ...] = ()


def find_live_section(markdown_text: str, heading: str) -> LiveSection:
    """Find the unique live section under `heading`.

    Fenced backtick and tilde examples are ignored. A second live heading
    with the same text is ambiguous even when the two sections match.
    """
    heading_level = len(heading) - len(heading.lstrip("#"))
    lines = _live_lines(markdown_text)
    starts = [index for index, line in enumerate(lines) if line.strip() == heading]
    if not starts:
        return LiveSection("missing")
    if len(starts) > 1:
        return LiveSection("ambiguous")
    section: list[str] = []
    for line in lines[starts[0] + 1 :]:
        heading_match = HEADING_PATTERN.match(line.strip())
        if heading_match and len(heading_match.group(1)) <= heading_level:
            break
        section.append(line)
    return LiveSection("ok", tuple(section))


def _section_lines(markdown_text: str, heading: str) -> list[str] | None:
    """Return the live lines of the first section under `heading`, or None.

    Heading discovery ignores fenced examples. The section stops at the next
    live heading of the same or higher level. Canonical validation must use
    `find_live_section` instead, so a duplicate heading is not silently
    reduced to this first match.
    """
    heading_level = len(heading) - len(heading.lstrip("#"))
    lines = _live_lines(markdown_text)
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading)
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


@dataclass(frozen=True)
class ProjectReferences:
    """Confirmed project references, or why they cannot be read.

    `status` is "ok", "missing", "ambiguous", or "invalid". "missing" means
    the section is absent, which is valid. "ok" holds only the supported
    fields that have a value. This result does not say whether a host
    integration verified the link.
    """

    status: str
    values: dict[str, str]
    detail: str = ""


def _recognized_project_reference_occurrences(lines: list[str]) -> dict[str, list[str]]:
    """Group each recognized field name's raw, unparsed value by occurrence.

    This looks past the canonical backtick format on purpose. A recognized
    field name written without backticks, or repeated with a mix of
    canonical and malformed values, must still be visible here so duplicate
    and malformed detection can see it. An unrecognized field name (not in
    `PROJECT_REFERENCE_FIELDS`) is ignored, so unrelated human-authored
    lines in the same section are preserved and never flagged.
    """
    occurrences: dict[str, list[str]] = {}
    for line in lines:
        match = PROJECT_REFERENCE_LINE_PATTERN.match(line.strip())
        if match is None:
            continue
        name = match.group(1).strip()
        if name not in PROJECT_REFERENCE_FIELDS:
            continue
        occurrences.setdefault(name, []).append(match.group(2).strip())
    return occurrences


def _hostname_only_problem(value: str) -> str | None:
    """Return why `value` is not a bare hostname (optionally with a port), or None."""
    if not value or any(char.isspace() or ord(char) < 0x20 for char in value):
        return "must be a host only, with no whitespace or control characters"
    if "://" in value:
        return "must be a host only, with no scheme"
    if "@" in value:
        return "must be a host only, with no embedded credentials"
    if "/" in value or "?" in value or "#" in value:
        return "must be a host only, with no path, query, or fragment"
    try:
        parsed = urlsplit(f"//{value}")
    except ValueError as error:
        return f"could not be parsed as a host: {error}"
    if not parsed.hostname:
        return "must be a host only, and this is not a valid hostname"
    try:
        parsed.port
    except ValueError:
        return "must be a host only, and this has a malformed port"
    if parsed.netloc != value:
        return "must be a host only, optionally with a port"
    return None


def _absolute_http_url_problem(value: str) -> str | None:
    """Return why `value` is not a safe absolute http(s) URL, or None.

    This validates syntax only: scheme, credentials, and hostname shape. It
    never performs a network call, and a syntactically valid result here
    does not mean the host is reachable, the resource exists, or the user
    has permission to read it.
    """
    if not value or any(char.isspace() or ord(char) < 0x20 for char in value):
        return "must not be empty or contain whitespace or control characters"
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        return f"could not be parsed as a URL: {error}"
    if parsed.scheme not in ("http", "https"):
        return "must be an absolute http or https URL"
    if parsed.username or parsed.password:
        return "must not include embedded credentials"
    if not parsed.hostname:
        return "must include a host"
    try:
        parsed.port
    except ValueError:
        return "has a malformed port"
    return None


def _project_reference_syntax_problems(values: dict[str, str]) -> list[str]:
    """Validate recognized, canonically-formatted field values.

    Called only after duplicate and malformed-format detection has already
    passed, so each field here has exactly one canonical occurrence.
    """
    problems: list[str] = []
    site = values.get("Jira site")
    if site is not None:
        problem = _hostname_only_problem(site)
        if problem:
            problems.append(f"Jira site {problem}")
    project = values.get("Jira project")
    if project is not None and (
        "://" in project or "/" in project or any(char.isspace() for char in project)
    ):
        problems.append("Jira project must be a project key")
    board = values.get("Jira board")
    if board is not None:
        problem = _absolute_http_url_problem(board)
        if problem:
            problems.append(f"Jira board {problem}")
    figma_reference = values.get("Figma reference")
    if figma_reference is not None:
        problem = _absolute_http_url_problem(figma_reference)
        if problem:
            problems.append(f"Figma reference {problem}")
    role = values.get("Figma role")
    if role is not None and role not in FIGMA_ROLES:
        problems.append("Figma role is not recognized")
    if role is not None and "Figma reference" not in values:
        problems.append("Figma role is set without a Figma reference")
    return problems


def parse_project_references(markdown_text: str) -> ProjectReferences:
    """Read `## Project references` without touching `## Context identities`.

    A missing section is "missing", not an error. Two live copies of the
    heading are "ambiguous". A recognized field name repeated — even with a
    mix of canonical and malformed values — is "ambiguous": callers must
    not pick one. A recognized field name whose value is not in the
    canonical backtick format is "invalid", not silently ignored: a
    malformed value must never be mistaken for an absent one. An
    unrecognized Figma role, a Jira site that is not a bare host, an
    unsafe or non-http(s) board/Figma URL, or a role without a reference is
    also "invalid".

    `values` is populated only when `status` is "ok". Every other status —
    including "invalid" — reports an empty `values`, the same as "missing"
    and "ambiguous": a rejected field must never be mistaken for a
    confirmed one by a caller that only checks whether a key is present.
    Read `detail` to see which field, and why, when `status` is "invalid".
    """
    section = find_live_section(markdown_text, PROJECT_REFERENCE_HEADING)
    if section.status != "ok":
        return ProjectReferences(section.status, {})

    occurrences = _recognized_project_reference_occurrences(list(section.lines))
    duplicates = sorted(name for name, raw in occurrences.items() if len(raw) > 1)
    if duplicates:
        return ProjectReferences(
            "ambiguous", {}, f"duplicate project reference fields: {duplicates}"
        )

    values: dict[str, str] = {}
    malformed: list[str] = []
    for name, raw_values in occurrences.items():
        raw = raw_values[0]
        canonical = CANONICAL_VALUE_PATTERN.match(raw)
        if canonical is None:
            malformed.append(f"{name} is not in the canonical `` `value` `` format")
            continue
        value = canonical.group(1).strip()
        if value:
            values[name] = value
    if malformed:
        return ProjectReferences("invalid", {}, "; ".join(malformed))

    problems = _project_reference_syntax_problems(values)
    if problems:
        return ProjectReferences("invalid", {}, "; ".join(problems))
    return ProjectReferences("ok", values)


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
    values match, when a well-formed field coexists with a malformed one,
    when the metadata heading is duplicated inside the generated block, or
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

    identity_section = find_live_section(block.text, "## Identity and scope")
    scope_section = find_live_section(block.text, "## Scope")
    if identity_section.status == "ambiguous":
        return FingerprintField("ambiguous")
    if identity_section.status == "ok":
        section = list(identity_section.lines)
    elif scope_section.status == "ambiguous":
        return FingerprintField("ambiguous")
    elif scope_section.status == "ok":
        section = list(scope_section.lines)
    else:
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


def _reference_check(
    name: str, status: str, ok_detail: str, *, mandatory_local: bool = False
) -> ValidationCheck:
    """Map a link classification to a validation check.

    `mandatory_local` is only for a module row's Context target, which must
    be a local readable document. A URL or same-document anchor fails that
    check. Ordinary documentation and evidence links keep the default:
    external references stay not_applicable and are not fetched.
    """
    if status == "ok":
        return ValidationCheck(name, "passed", ok_detail)
    if status == "external":
        if mandatory_local:
            return ValidationCheck(
                name,
                "failed",
                "context target must be a local readable document, not a URL or anchor",
            )
        return ValidationCheck(name, "not_applicable", "external or anchor reference")
    if status in {"unavailable", "unresolved"}:
        return ValidationCheck(name, "unresolved", f"reference status: {status}")
    return ValidationCheck(name, "failed", f"reference status: {status}")


def _budget_from_text(name: str, text: str, max_lines: int) -> ValidationCheck:
    lines = len(text.splitlines())
    if lines <= max_lines:
        return ValidationCheck(name, "passed", f"{lines} lines (budget {max_lines})")
    return ValidationCheck(name, "failed", f"{lines} lines exceeds budget {max_lines}")


def _structure_from_text(name: str, text: str, required_heading: str) -> ValidationCheck:
    block = parse_generated_block(text)
    if block.status != "ok":
        return ValidationCheck(name, "failed", f"generated block status: {block.status}")
    found = find_live_section(block.text, required_heading)
    if found.status == "missing":
        return ValidationCheck(
            name,
            "failed",
            f"missing required heading {required_heading!r} inside the generated block",
        )
    if found.status == "ambiguous":
        return ValidationCheck(
            name,
            "failed",
            f"duplicate heading {required_heading!r} inside the generated block",
        )
    return ValidationCheck(name, "passed", f"markers and {required_heading!r} present")


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
    found = find_live_section(block.text, "## Scope")
    if found.status == "ambiguous":
        return IndexIdentity("unresolved", detail="duplicate ## Scope inside the generated block")
    if found.status != "ok":
        return IndexIdentity("unresolved", detail="missing ## Scope inside the generated block")
    fields = parse_labeled_fields(list(found.lines))
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
    except (OSError, GitDiscoveryError, RuntimeError) as error:
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
    candidate_content: dict[Path, str] | None = None,
    candidate_paths: frozenset[Path] = frozenset(),
) -> list[ValidationCheck]:
    """Budget, structure, identity, freshness, and evidence for one module document.

    `candidate_content` lets `module_path` be read from a proposed-content
    mapping instead of disk, so a module document can be validated at its
    intended final path before it is actually written there.
    """
    checks: list[ValidationCheck] = []

    text, error = _read_candidate_or_document(module_path, candidate_content)
    identity_name = f"modules:identity:{label}"
    fingerprint_name = f"modules:fingerprint:{label}"
    if error or text is None:
        detail = error or f"{module_path} is not readable"
        status = "failed" if error and "not a regular file" in error else "unresolved"
        checks.append(ValidationCheck(f"modules:budget:{label}", status, detail))
        checks.append(ValidationCheck(f"modules:structure:{label}", status, detail))
        checks.append(ValidationCheck(identity_name, status, detail))
        checks.append(ValidationCheck(fingerprint_name, "unresolved", detail))
        return checks

    checks.append(_budget_from_text(f"modules:budget:{label}", text, module_budget))
    checks.append(
        _structure_from_text(f"modules:structure:{label}", text, "## Identity and scope")
    )

    block = parse_generated_block(text)
    found = find_live_section(block.text, "## Identity and scope") if block.status == "ok" else None
    if found is not None and found.status == "ambiguous":
        checks.append(
            ValidationCheck(
                identity_name,
                "failed",
                "duplicate ## Identity and scope inside the generated block",
            )
        )
        checks.append(
            ValidationCheck(
                fingerprint_name,
                "unresolved",
                "identity section is ambiguous, so freshness was not compared",
            )
        )
    else:
        section = list(found.lines) if found is not None and found.status == "ok" else None
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
            status = classify_markdown_target(
                module_path, value, authorized_roots, candidate_paths=candidate_paths
            )
            checks.append(_reference_check(f"{evidence_name}:{value}", status, "evidence link resolves"))
        elif kind == "cross":
            repo_id, _, relative = value.partition(":")
            status = resolve_source_path(repo_id, relative, authorized_roots)
            checks.append(_reference_check(f"{evidence_name}:{value}", status, "evidence path exists"))
        else:
            status = resolve_source_path(repository_id, value, authorized_roots)
            checks.append(_reference_check(f"{evidence_name}:{value}", status, "evidence path exists"))
    return checks


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _candidate_destination_problem(path: Path, authorized_roots: dict[str, Path]) -> str | None:
    """Return why `path` cannot be a candidate destination, or None.

    Read-only. A missing final file, and missing parent directories under an
    existing authorized root, are allowed so first-time generation can be
    checked before those files exist. An existing destination must be a
    regular file. A symlink component, a directory, a file occupying a parent
    directory, or a resolved path outside every authorized root is rejected.
    """
    roots = [Path(root).resolve() for root in authorized_roots.values()]
    given = Path(path)
    if not given.is_absolute():
        given = (Path.cwd() / given)
    current = Path(given.anchor)
    parts = given.parts[1:]
    for index, part in enumerate(parts):
        current = current / part
        is_last = index == len(parts) - 1
        try:
            is_link = current.is_symlink()
        except OSError as error:
            return f"candidate destination is not readable: {error.strerror}"
        if is_link:
            try:
                link_target = current.resolve()
            except OSError as error:
                return f"candidate destination cannot be resolved: {error.strerror}"
            # A symlink above an authorized root is part of the machine path
            # (for example /var -> /private/var). A symlink inside the
            # destination, including one that escapes the root, is rejected.
            if any(_is_inside(root, link_target) or root == link_target for root in roots):
                pass
            else:
                return "candidate destination includes a symlink"
        if not current.exists():
            if not current.parent.is_dir():
                return "candidate destination has a parent that is not a directory"
            break
        if is_last:
            if current.is_dir():
                return "candidate destination is a directory"
            if not current.is_file():
                return "candidate destination is not a regular file"
        elif not current.is_dir():
            return "candidate destination has a parent that is not a directory"
    try:
        resolved = given.resolve()
    except OSError as error:
        return f"candidate destination cannot be resolved: {error.strerror}"
    if not any(_is_inside(resolved, root) for root in roots):
        return "candidate destination is outside every authorized root"
    return None


def _prepare_candidate_content(
    candidate_content: dict[Path, str], authorized_roots: dict[str, Path]
) -> tuple[dict[Path, str], str | None]:
    """Normalize candidate paths and reject unsafe or conflicting destinations.

    Two different keys that resolve to one destination are a conflict, even
    when their text matches. The returned mapping is keyed by the resolved
    path. This function does not write.
    """
    normalized: dict[Path, str] = {}
    origins: dict[Path, Path] = {}
    for key, text in candidate_content.items():
        problem = _candidate_destination_problem(Path(key), authorized_roots)
        if problem:
            return {}, f"{key}: {problem}"
        try:
            resolved = Path(key).resolve()
        except OSError as error:
            return {}, f"{key}: candidate destination cannot be resolved: {error.strerror}"
        previous = origins.get(resolved)
        if previous is not None and previous != Path(key):
            return {}, (
                f"candidate paths {previous} and {key} resolve to the same destination"
            )
        origins[resolved] = Path(key)
        normalized[resolved] = text
    return normalized, None


def validate_generated_context(
    index_path: Path,
    authorized_roots: dict[str, Path],
    index_repository_id: str | None = None,
    index_budget: int = 150,
    module_budget: int = 300,
    candidate_content: dict[Path, str] | None = None,
) -> list[ValidationCheck]:
    """Run every deterministic check against one generated context index.

    This function is read-only: it never writes, moves, or deletes a
    document. `authorized_roots` maps each repository ID this validation run
    is allowed to touch to that repository's root path. It is explicit
    workspace configuration, never guessed from the filesystem, and the
    number of roots does not decide whether the index is multi-repository.

    `candidate_content` is an optional, minimal mapping from a document's
    intended final absolute path to its proposed text, for a proposal that
    has not been written there yet (`{final_absolute_path: proposed_text}`).
    When `index_path` or a linked module's resolved path is a key in this
    mapping, that text is validated as if it already existed at that path,
    and links between mapped candidates resolve against their intended final
    locations. Unmapped targets still fall back to the real file on disk.
    This is not a general-purpose virtual filesystem: it only changes what
    text is read for the specific paths supplied, it does not change where
    `authorized_roots` says writes are allowed, and presence in this mapping
    never authorizes writing it — that approval step is unaffected and
    happens later, in Stage 5/6 of the `sync-context` workflow.

    Index identity comes from canonical `## Scope` metadata inside the one
    generated block. A supplied `index_repository_id` must match that
    metadata. Only `Index: multi-repository` may omit a repository-wide
    fingerprint. Module freshness is still checked in that mode.

    A passing result never proves an Unknown is accurate, that a described
    dependency is correct, or that a claim is well-supported. Those
    judgments belong to independent review (`context-reviewer`).
    """
    candidate_content = dict(candidate_content) if candidate_content else {}
    if candidate_content:
        candidate_content, problem = _prepare_candidate_content(
            candidate_content, authorized_roots
        )
        if problem:
            return [ValidationCheck("candidates:destination", "failed", problem)]
    candidate_paths: frozenset[Path] = frozenset(candidate_content)

    if index_path in candidate_content or index_path.resolve() in candidate_content:
        text, error = _read_candidate_or_document(index_path, candidate_content)
    else:
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
    modules_section = find_live_section(generated, "## Modules")
    if modules_section.status == "ambiguous":
        checks.append(
            ValidationCheck(
                "modules:table",
                "failed",
                "duplicate ## Modules section inside the generated block",
            )
        )
        return checks
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
                index_path,
                resolved_target,
                authorized_roots,
                require_file=True,
                candidate_paths=candidate_paths,
            )
            check_name = f"modules:link:{resolved_target}"
            checks.append(
                _reference_check(check_name, status, "link resolves", mandatory_local=True)
            )
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
                    candidate_content=candidate_content,
                    candidate_paths=candidate_paths,
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

    `--candidate FINAL_PATH=STAGED_FILE` (repeatable) validates a proposal
    before it is written: `STAGED_FILE` is a real file on disk holding the
    proposed text (for example a temporary staging copy), and `FINAL_PATH`
    is the absolute path the proposal would occupy once applied. Pass
    `FINAL_PATH` as `index_path` itself to validate a brand-new index that
    does not exist on disk yet. This reads `STAGED_FILE`'s content only; it
    never writes to `FINAL_PATH`.

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
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        metavar="FINAL_PATH=STAGED_FILE",
        help="validate STAGED_FILE's text as if already written at FINAL_PATH, repeatable",
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

    candidate_content: dict[Path, str] = {}
    for entry in args.candidate:
        if "=" not in entry:
            print(f"error: --candidate must be FINAL_PATH=STAGED_FILE, got {entry!r}", file=sys.stderr)
            return 2
        final_path, _, staged_file = entry.partition("=")
        try:
            candidate_content[Path(final_path)] = Path(staged_file).read_text(encoding="utf-8")
        except OSError as error:
            print(f"error: cannot read --candidate staged file {staged_file!r}: {error}", file=sys.stderr)
            return 2

    checks = validate_generated_context(
        args.index_path,
        authorized_roots,
        index_repository_id=args.index_repository_id,
        index_budget=args.index_budget,
        module_budget=args.module_budget,
        candidate_content=candidate_content or None,
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
